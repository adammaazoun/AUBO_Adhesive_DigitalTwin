import cv2
import numpy as np
from cv2 import aruco
import json
import urllib.request
import time 
from config import *
from geometry import segmentize, warp_contour
import robot_controller
import debug_stream

# ── Global Vision & Calibration State ─────────────────────
STREAM_URL = "http://localhost:55000/"
H_MATRIX = None
OUTER_MN = None
OUTER_RNG = None
REF_OUTER_NORM = None
PIECE_W_MM = None
PIECE_H_MM = None
PIECE_RATIO = None
REF_HU = None
MARKER_PIXEL_CORNERS = None   # cached ArUco tag corners, masked out every frame
BOARD_POLY_PX = None          # cached board polygon in pixels, for area_in_range
BOARD_MASK = None 

# ── Matching tolerances (ported from the working detect_shape.py) ──
MIN_AREA               = 2000
ASPECT_TOLERANCE       = 0.30   # ±30%, matches the script that worked
SHAPE_MATCH_THRESHOLD  = 100.0   # starting value — your piece scored ~8-25 there
AREA_RANGE_LOW         = 0.40   # expected_px * 0.40 .. expected_px * 1.40
AREA_RANGE_HIGH        = 1.40
MARKER_MASK_MARGIN     = 15

def detect_piece_geometry_best_of(n=5, delay=0.03):
    best_segments, best_score, best_pos = None, float("inf"), None
    for i in range(n):
        pos_at_capture = robot_controller.get_belt_position()
        segments, score = detect_piece_geometry()
        if segments is not None and score < best_score:
            best_segments, best_score, best_pos = segments, score, pos_at_capture
        time.sleep(delay)
    return best_segments, best_score, best_pos

def load_reference_data():
    global PIECE_W_MM, PIECE_H_MM, PIECE_RATIO, REF_HU, OUTER_MN, OUTER_RNG, REF_OUTER_NORM
    with open(PIECE_DATA_JSON) as f:
        piece_data = json.load(f)

    PIECE_W_MM = piece_data["piece_width_mm"]
    PIECE_H_MM = piece_data["piece_height_mm"]
    PIECE_RATIO = max(PIECE_W_MM, PIECE_H_MM) / min(PIECE_W_MM, PIECE_H_MM)

    def segments_to_points(segments, n_arc=20):
        pts = []
        for seg in segments:
            if seg["type"] == "line":
                pts.append([seg["start"]["X"], seg["start"]["Y"]])
            elif seg["type"] == "arc":
                cx, cy = seg["center"]["X"], seg["center"]["Y"]
                r, sx, sy = seg["radius_mm"], seg["start"]["X"], seg["start"]["Y"]
                ex, ey, vx, vy = seg["end"]["X"], seg["end"]["Y"], seg["via"]["X"], seg["via"]["Y"]
                a_s  = np.arctan2(sy-cy, sx-cx)
                a_en = (np.arctan2(ey-cy, ex-cx) - a_s) % (2*np.pi)
                a_vn = (np.arctan2(vy-cy, vx-cx) - a_s) % (2*np.pi)
                angs = (np.linspace(a_s, a_s+a_en, n_arc) if a_vn <= a_en else np.linspace(a_s, a_s-(2*np.pi-a_en), n_arc))
                for a in angs[:-1]:
                    pts.append([cx + r*np.cos(a), cy + r*np.sin(a)])
        return np.array(pts, dtype=np.float32)

    outer_pts = segments_to_points(piece_data["outer_glue_segments"])
    OUTER_MN  = outer_pts.min(axis=0)
    outer_mx  = outer_pts.max(axis=0)
    OUTER_RNG = outer_mx - OUTER_MN
    OUTER_RNG[OUTER_RNG == 0] = 1

    REF_OUTER_NORM = (outer_pts - OUTER_MN) / OUTER_RNG
    _ref_px = (REF_OUTER_NORM * np.array([500, 600])).astype(np.int32).reshape(-1, 1, 2)
    REF_HU  = cv2.HuMoments(cv2.moments(_ref_px)).flatten()


import threading

class _MJPEGStream:
    def __init__(self, url):
        self.url = url
        self._frame = None
        self._lock = threading.Lock()
        self._running = False
        self._thread = None

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._reader, daemon=True)
        self._thread.start()

    def _reader(self):
        while self._running:
            try:
                stream = urllib.request.urlopen(self.url, timeout=5)
                buf = bytes()
                while self._running:
                    buf += stream.read(4096)
                    a = buf.find(b'\xff\xd8')
                    b = buf.find(b'\xff\xd9')
                    if a != -1 and b != -1:
                        jpg = buf[a:b+2]
                        buf = buf[b+2:]   # keep only leftover bytes, don't grow forever
                        img = cv2.imdecode(np.frombuffer(jpg, dtype=np.uint8), cv2.IMREAD_COLOR)
                        if img is not None:
                            with self._lock:
                                self._frame = img
            except Exception as e:
                print(f"[MJPEG] stream error: {e}, reconnecting...")
                time.sleep(0.5)

    def get_frame(self):
        with self._lock:
            return None if self._frame is None else self._frame.copy()


_stream = _MJPEGStream(STREAM_URL)


def grab_single_frame():
    """Returns the most recently decoded frame from the persistent MJPEG
    connection. Near-instant — no per-call HTTP round trip / buffering
    delay, which is what was causing the belt to visibly overshoot the
    detection point during continuous polling."""
    if not _stream._running:
        _stream.start()
        # give the reader a moment to get its first frame on cold start
        for _ in range(50):
            f = _stream.get_frame()
            if f is not None:
                return f
            time.sleep(0.05)
    frame = _stream.get_frame()
    if frame is None:
        raise RuntimeError("No frame available yet from MJPEG stream.")
    return frame

def init_homography():
    global H_MATRIX, MARKER_PIXEL_CORNERS, BOARD_POLY_PX, BOARD_MASK
    print("Connecting to Unity MJPEG stream for ArUco scale initialization...")
    
    frame = grab_single_frame()
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    aruco_dict = aruco.getPredefinedDictionary(aruco.DICT_4X4_50)
    aruco_params = aruco.DetectorParameters()
    aruco_params.cornerRefinementMethod = aruco.CORNER_REFINE_SUBPIX
    detector = aruco.ArucoDetector(aruco_dict, aruco_params)

    corners_list, ids, _ = detector.detectMarkers(gray)
    if ids is None or len(ids) < 4:
        raise RuntimeError("Initialization Failed: Matrix requires 4 visible ArUco markers!")

    pixel_pts, robot_pts, marker_corners_used = [], [], []
    for i, mid in enumerate(ids.flatten().tolist()):
        if mid not in ROBOT_CORNERS: continue
        pixel_pts.append(corners_list[i][0].mean(axis=0))
        robot_pts.append(ROBOT_CORNERS[mid])
        marker_corners_used.append(corners_list[i][0])

    MARKER_PIXEL_CORNERS = marker_corners_used

    H_MATRIX, _ = cv2.findHomography(np.array(pixel_pts, dtype=np.float32),
                                     np.array(robot_pts, dtype=np.float32), cv2.RANSAC, 5.0)

    # Cache the board polygon in pixel space once — used every frame by
    # area_in_range() to compute the expected piece footprint. This is the
    # trick from detect_shape.py that keeps the board-outline contour from
    # ever being accepted: its area will be wildly outside the expected range.
    order = ["top_left", "top_right", "bottom_right", "bottom_left"]
    BOARD_POLY_PX = np.array([[int(v) for v in r2px(*PAPER_CORNERS_ROBOT[k])] for k in order], dtype=np.int32)

    # Cache the board mask (fillPoly + erode + marker masking) once here,
    # instead of rebuilding it every frame in both detect_piece_geometry()
    # and get_piece_centroid_px(). Board/camera are static after calibration.
    raw_mask = np.where(cv2.fillPoly(np.zeros(gray.shape, np.uint8), [BOARD_POLY_PX], 255) > 0,
                         np.uint8(255), np.uint8(0))
    BOARD_MASK = cv2.erode(raw_mask, np.ones((30, 30), np.uint8), iterations=1)
    BOARD_MASK = _mask_out_markers(BOARD_MASK)

    print(f"Homography Matrix successfully locked from Unity scale! ✅ ({len(marker_corners_used)} markers cached for masking)")


def px2r(px, py):
    r = cv2.perspectiveTransform(np.array([[[float(px),float(py)]]], dtype=np.float32), H_MATRIX)
    return float(r[0][0][0]), float(r[0][0][1])


def r2px(rx, ry):
    return cv2.perspectiveTransform(np.array([[[rx, ry]]], dtype=np.float32), np.linalg.inv(H_MATRIX))[0][0]


def pt_to_robot(pt_dict, M):
    x_norm = (pt_dict["X"] - OUTER_MN[0]) / OUTER_RNG[0]
    y_norm = (pt_dict["Y"] - OUTER_MN[1]) / OUTER_RNG[1]
    pw = M @ np.array([x_norm, y_norm, 1.0], dtype=np.float32)   # affine: no perspective divide
    rx, ry = px2r(pw[0], pw[1])
    return {"X": round(rx, 2), "Y": round(ry, 2), "Z": round(pt_dict["Z"], 2)}


def _mask_out_markers(mask):
    if not MARKER_PIXEL_CORNERS:
        return mask
    for mc in MARKER_PIXEL_CORNERS:
        poly = mc.astype(np.int32).reshape(-1, 1, 2)
        cv2.fillPoly(mask, [poly], 0)
    return cv2.erode(mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (MARKER_MASK_MARGIN, MARKER_MASK_MARGIN)), iterations=1)
def _aspect_ratio_ok(cnt):
    hull = cv2.convexHull(cnt)
    rect = cv2.minAreaRect(hull)
    w, h = rect[1]

    if w == 0 or h == 0:
        print("[ASPECT] Degenerate rect (w or h == 0) -> rejected")
        return False, float("inf")  # never None — keeps downstream f"{ratio_dev:.3f}" safe

    ratio = max(w, h) / min(w, h)
    dev = abs(ratio - PIECE_RATIO) / PIECE_RATIO

    print(f"[ASPECT] w={w:.1f} h={h:.1f} ratio={ratio:.3f} ref={PIECE_RATIO:.3f} dev={dev:.3f}")

    return dev < ASPECT_TOLERANCE, dev


def _area_in_range(area_px):
    tl = np.array(PAPER_CORNERS_ROBOT["top_left"])
    tr = np.array(PAPER_CORNERS_ROBOT["top_right"])
    bl = np.array(PAPER_CORNERS_ROBOT["bottom_left"])

    board_w_mm = np.linalg.norm(tr - tl)   # distance top_left -> top_right, any axis
    board_h_mm = np.linalg.norm(bl - tl)   # distance top_left -> bottom_left, any axis
    board_area_mm = board_w_mm * board_h_mm

    board_area_px = cv2.contourArea(BOARD_POLY_PX.astype(np.float32))
    piece_area_mm = PIECE_W_MM * PIECE_H_MM

    expected_px = board_area_px * (piece_area_mm / board_area_mm)
    lo, hi = AREA_RANGE_LOW * expected_px, AREA_RANGE_HIGH * expected_px
    return (lo < area_px < hi), expected_px

def _shape_match_score(cnt):
    hu = cv2.HuMoments(cv2.moments(cnt)).flatten()
    eps = 1e-10
    return float(np.sum(np.abs(
        np.sign(REF_HU) * np.log10(np.abs(REF_HU) + eps) -
        np.sign(hu)     * np.log10(np.abs(hu)     + eps)
    )))


def detect_piece_geometry(center_gate_px=150):
    """Runs vision pipeline to find, isolate, and map internal template work-paths.
    Returns (None, None) if no candidate passes area floor, aspect ratio,
    board-relative area range, AND Hu-moment shape threshold."""
    if H_MATRIX is None:
        return None, None

    frame = grab_single_frame()
    debug_img = frame.copy()
    gray  = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(8,8))

    mask = BOARD_MASK

    board = cv2.bitwise_and(gray, gray, mask=mask)
    board[mask==0] = 255
    thresh = cv2.adaptiveThreshold(clahe.apply(cv2.GaussianBlur(board,(7,7),0)), 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 31, 15)

    k_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
    k_open  = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))

    thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, k_close, iterations=3)
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, k_open, iterations=1)

    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    thresh = cv2.morphologyEx(cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, k, iterations=2), cv2.MORPH_OPEN, k, iterations=1)


    contours,_ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    best, best_score = None, float("inf")
    all_candidates = []
    frame_cx = frame.shape[1] / 2.0

    for cnt in contours:
        area = cv2.contourArea(cnt)

        # Layer 0 — only consider contours near the camera-station center.
        # With two pieces close together, a neighboring piece can otherwise
        # win on hu_score alone and silently steal the slot meant for the
        # actually-centered piece.
        M = cv2.moments(cnt)
        if M["m00"] == 0:
            continue
        cnt_cx = M["m10"] / M["m00"]
        if abs(cnt_cx - frame_cx) > center_gate_px:
            continue

        rect = cv2.minAreaRect(cnt)
        box = cv2.boxPoints(rect).astype(int)

        

        # Layer 1 — area floor
        if area < MIN_AREA:
            continue
        ratio_dev = 0.0        
        # # Layer 2 — aspect ratio
        a_ok, ratio_dev = _aspect_ratio_ok(cnt)
        if not a_ok:
            all_candidates.append((cnt, area, ratio_dev, None, None, False))
            print(f"[CANDIDATE] area={area:.0f} ratio_dev={ratio_dev:.3f} -> rejected (aspect)")
            continue

        # Layer 3 — board-relative expected area range (kills board outline, tiny noise, etc.)
        area_ok, expected_px = _area_in_range(area)
        if not area_ok:
            all_candidates.append((cnt, area, ratio_dev, None, expected_px, False))
            print(f"[CANDIDATE] area={area:.0f} expected≈{expected_px:.0f} ratio_dev={ratio_dev:.3f} -> rejected (area range)")
            continue

        # Layer 4 — Hu-moment shape score
        score = _shape_match_score(cnt)
        passes = score < SHAPE_MATCH_THRESHOLD

        all_candidates.append((cnt, area, ratio_dev, score, expected_px, passes))
        print(f"[CANDIDATE] area={area:.0f} expected≈{expected_px:.0f} ratio_dev={ratio_dev:.3f} "
              f"hu_score={score:.2f} (thresh={SHAPE_MATCH_THRESHOLD}) -> {'ACCEPTED' if passes else 'rejected (shape)'}")

        if passes and score < best_score:
            best_score, best = score, cnt
    if DEBUG:
        _build_debug_frame(frame, mask, thresh, all_candidates, best, frame_cx, center_gate_px)
    

    if best is None:
        print("[REJECT] No candidate passed all filters (area / aspect / area-range / shape).")
        return None, None

    p0, p1, p2, p3 = _ordered_box_corners(best)
    src = np.array([[0, 0], [1, 0], [0, 1]], dtype=np.float32)   # only need 3 points
    dst = np.array([p0, p1, p3], dtype=np.float32)

    # getAffineTransform allows independent X/Y scale (needed since the piece
    # isn't square — 147x83mm), unlike estimateAffinePartial2D which forces a
    # single uniform scale and was squashing the long axis. Since box corners
    # come from minAreaRect (an ideal right-angle rectangle, not noisy corner
    # detections), a full affine still introduces zero shear here — it's exactly
    # rotation + independent per-axis scale + translation.
    M = cv2.getAffineTransform(src, dst)
    

    with open(PIECE_DATA_JSON) as f:
        template_segments = json.load(f)["inner_glue_segments"]

    # Debug: overlay the computed path on top of the accepted piece
    if DEBUG:
        path_dbg = frame.copy()
        cv2.drawContours(path_dbg, [best], -1, (0, 255, 255), 2)
        _draw_path_overlay(path_dbg, template_segments, M)
        debug_stream.publish_frame(path_dbg)
    

    out = []
    for seg in template_segments:
        if seg["type"] == "line":
            out.append({"type": "line", "start": pt_to_robot(seg["start"], M), "end": pt_to_robot(seg["end"], M)})
        elif seg["type"] == "arc":
            t_start, t_end, t_via = pt_to_robot(seg["start"], M), pt_to_robot(seg["end"], M), pt_to_robot(seg["via"], M)
            x1, y1, x2, y2, x3, y3 = t_start["X"], t_start["Y"], t_via["X"], t_via["Y"], t_end["X"], t_end["Y"]
            D = 2*(x1*(y2-y3) + x2*(y3-y1) + x3*(y1-y2))
            if abs(D) < 1e-6:
                out.append({"type": "line", "start": t_start, "end": t_end})
                continue
            cx = ((x1**2+y1**2)*(y2-y3) + (x2**2+y2**2)*(y3-y1) + (x3**2+y3**2)*(y1-y2)) / D
            cy = ((x1**2+y1**2)*(x3-x2) + (x2**2+y2**2)*(x1-x3) + (x3**2+y3**2)*(x2-x1)) / D
            radius = float(np.sqrt((x1-cx)**2 + (y1-cy)**2))
            sweep = float(np.degrees(np.arccos(np.clip(np.dot(np.array([x1-cx, y1-cy]), np.array([x3-cx, y3-cy])) / (radius * radius), -1, 1))))
            out.append({"type": "arc", "start": t_start, "end": t_end, "via": t_via, "center": {"X": round(cx,2), "Y": round(cy,2), "Z": t_start["Z"]}, "radius_mm": round(radius, 4), "sweep_deg": round(sweep, 1)})

    return out, best_score
# ── Add this block to vision_detector.py ────────────────────────────────
# Cheap polling check used by the continuous pipeline to know when a piece
# has drifted into the center of the camera frame. This is intentionally
# NOT the full detect_piece_geometry() pipeline (no Hu-moment matching, no
# area-range filtering, no perspective mapping) — it just needs to be fast
# enough to call every ~50ms while the belt is moving.
#
# TUNE THESE FOR YOUR RIG:
#  - CAMERA_CENTER_TOLERANCE_PX: how close to frame-center counts as "centered"
#  - If your belt only moves along one screen axis (likely, since it's a
#    straight conveyor), you probably only need to check that axis (e.g. only
#    cy vs frame center, ignoring cx) rather than both — edit accordingly.

CAMERA_CENTER_TOLERANCE_PX = 20


def get_piece_centroid_px(save_debug=False):
    if H_MATRIX is None:
        return None
    frame = grab_single_frame()
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    mask = BOARD_MASK
    board = cv2.bitwise_and(gray, gray, mask=mask)
    board[mask == 0] = 255
    thresh = cv2.adaptiveThreshold(
        cv2.GaussianBlur(board, (7, 7), 0), 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 31, 15
    )
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8), iterations=2)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    frame_cx = frame.shape[1] / 2.0
    frame_cy = frame.shape[0] / 2.0

    # Multiple pieces can be visible at once — pick the one whose centroid
    # is CLOSEST TO CENTER (i.e. the one currently arriving), not the
    # largest blob, which flickers between different physical pieces.
    best, best_dist = None, float("inf")
    candidates = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < MIN_AREA:
            continue
        M = cv2.moments(cnt)
        if M["m00"] == 0:
            continue
        cx = M["m10"] / M["m00"]
        cy = M["m01"] / M["m00"]
        dist = abs(cx - frame_cx)   # X-axis only — that's the belt's travel axis
        candidates.append((cnt, cx, cy, area))
        if dist < best_dist:
            best_dist = dist
            best = (cx, cy)

    if save_debug:
        dbg = frame.copy()
        for cnt, cx, cy, area in candidates:
            cv2.drawContours(dbg, [cnt], -1, (0, 140, 255), 2)
            cv2.circle(dbg, (int(cx), int(cy)), 5, (0, 140, 255), -1)
        if best is not None:
            cv2.circle(dbg, (int(best[0]), int(best[1])), 8, (0, 255, 0), -1)
        cv2.line(dbg, (int(frame_cx), 0), (int(frame_cx), frame.shape[0]), (255, 0, 0), 1)
        cv2.imwrite("centering_debug.png", dbg)

    if best is None:
        return None
    print("[DETECTOR] centroid check running")
    return (best[0], best[1], frame.shape[1], frame.shape[0])


def is_piece_centered(tolerance_px=CAMERA_CENTER_TOLERANCE_PX):
    """True if a piece is currently within `tolerance_px` of the frame
    center on both axes. Called repeatedly while the belt runs."""
    result = get_piece_centroid_px()
    if result is None:
        return False
    cx, cy, w, h = result
    dx = abs(cx - w / 2.0)
    dy = abs(cy - h / 2.0)
    return dx < tolerance_px and dy < tolerance_px

#debug
def pt_to_px(pt_dict, M):
    x_norm = (pt_dict["X"] - OUTER_MN[0]) / OUTER_RNG[0]
    y_norm = (pt_dict["Y"] - OUTER_MN[1]) / OUTER_RNG[1]
    pw = (M @ np.array([[x_norm, y_norm, 1.0]], dtype=np.float32).T).T
    return (pw[0, 0] / pw[0, 2], pw[0, 1] / pw[0, 2])

def _draw_path_overlay(dbg, template_segments, M, n_arc=20):
    """Draws the computed glue path (lines + arcs) on the debug frame in
    image-pixel space, using the same warp M used for the real robot path."""
    for seg in template_segments:
        if seg["type"] == "line":
            p1 = pt_to_px(seg["start"], M)
            p2 = pt_to_px(seg["end"], M)
            cv2.line(dbg, (int(p1[0]), int(p1[1])), (int(p2[0]), int(p2[1])), (255, 0, 255), 2)

        elif seg["type"] == "arc":
            # Rebuild the arc's pixel-space points the same way segments_to_points
            # does in template (normalized) space, but transform each sample
            # through M into pixel space, so curvature stays correct after warp.
            cx, cy = seg["center"]["X"], seg["center"]["Y"]
            r = seg["radius_mm"]
            sx, sy = seg["start"]["X"], seg["start"]["Y"]
            ex, ey = seg["end"]["X"], seg["end"]["Y"]
            vx, vy = seg["via"]["X"], seg["via"]["Y"]

            a_s  = np.arctan2(sy - cy, sx - cx)
            a_en = (np.arctan2(ey - cy, ex - cx) - a_s) % (2 * np.pi)
            a_vn = (np.arctan2(vy - cy, vx - cx) - a_s) % (2 * np.pi)
            angs = (np.linspace(a_s, a_s + a_en, n_arc) if a_vn <= a_en
                    else np.linspace(a_s, a_s - (2 * np.pi - a_en), n_arc))

            pts_px = []
            for a in angs:
                px_pt = {"X": cx + r * np.cos(a), "Y": cy + r * np.sin(a)}
                pts_px.append(pt_to_px(px_pt, M))

            for i in range(len(pts_px) - 1):
                p1, p2 = pts_px[i], pts_px[i + 1]
                cv2.line(dbg, (int(p1[0]), int(p1[1])), (int(p2[0]), int(p2[1])), (255, 0, 255), 2)

    # mark start point of the path distinctly
    if template_segments:
        first = template_segments[0]
        p0 = pt_to_px(first["start"], M)
        cv2.circle(dbg, (int(p0[0]), int(p0[1])), 5, (0, 255, 255), -1)


def _build_debug_frame(frame, mask, thresh, candidates, best, frame_cx, center_gate_px):
    """candidates: list of (cnt, area, ratio_dev, score, expected_px, passes)"""
    dbg = frame.copy()

    # show the search-gate band so you can see why off-center pieces get skipped
    cv2.line(dbg, (int(frame_cx - center_gate_px), 0), (int(frame_cx - center_gate_px), dbg.shape[0]), (255, 255, 0), 1)
    cv2.line(dbg, (int(frame_cx + center_gate_px), 0), (int(frame_cx + center_gate_px), dbg.shape[0]), (255, 255, 0), 1)
    cv2.line(dbg, (int(frame_cx), 0), (int(frame_cx), dbg.shape[0]), (255, 0, 0), 1)

    for cnt, area, ratio_dev, score, expected_px, passes in candidates:
        color = (0, 255, 0) if passes else (0, 0, 255)
        cv2.drawContours(dbg, [cnt], -1, color, 2)
        M = cv2.moments(cnt)
        if M["m00"] == 0:
            continue
        cx, cy = int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"])
        label = f"a={area:.0f}"
        if expected_px is not None:
            label += f" exp={expected_px:.0f}"
        if score is not None:
            label += f" hu={score:.1f}"
        cv2.putText(dbg, label, (cx - 40, cy - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)

    if best is not None:
        cv2.drawContours(dbg, [best], -1, (0, 255, 255), 3)

    # small inset of the threshold mask so you can see binarization quality
    thumb = cv2.resize(cv2.cvtColor(thresh, cv2.COLOR_GRAY2BGR), (dbg.shape[1]//4, dbg.shape[0]//4))
    dbg[10:10+thumb.shape[0], 10:10+thumb.shape[1]] = thumb
    cv2.rectangle(dbg, (10,10), (10+thumb.shape[1], 10+thumb.shape[0]), (255,255,255), 1)

    debug_stream.publish_frame(dbg)

def _ordered_box_corners(cnt):
    """
    Orders the 4 minAreaRect corners so they match the template's corner
    sequence (0,0)->(1,0)->(1,1)->(0,1) — edges alternating SHORT,LONG —
    regardless of how far the piece is rotated on the belt.
    """
    rect = cv2.minAreaRect(cv2.convexHull(cnt))
    box = cv2.boxPoints(rect).astype(np.float32)

    def elen(i):
        return np.linalg.norm(box[i] - box[(i + 1) % 4])

    pair_a = (elen(0) + elen(2)) / 2.0
    pair_b = (elen(1) + elen(3)) / 2.0
    rotated = box if pair_a < pair_b else np.roll(box, -1, axis=0)

    opt_a, opt_b = rotated, np.roll(rotated, 2, axis=0)
    score = lambda pts: (pts[0][1], pts[0][0])
    return opt_a if score(opt_a) <= score(opt_b) else opt_b