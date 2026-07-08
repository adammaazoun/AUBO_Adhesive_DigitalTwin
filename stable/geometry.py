# ── geometry.py ───────────────────────────────────────────
import numpy as np
import cv2
from config import ARC_EPSILON_PX, LINE_TOL_MM, ARC_RMSE_MM, MIN_ARC_DEG

def xyz(pt, z):
    return {"X": round(float(pt[0]), 2),
            "Y": round(float(pt[1]), 2),
            "Z": round(float(z),    2)}

def fit_circle(pts):
    if len(pts) < 3: return None
    x, y = pts[:,0], pts[:,1]
    A    = np.column_stack([2*x, 2*y, np.ones(len(pts))])
    sol, *_ = np.linalg.lstsq(A, x*x + y*y, rcond=None)
    cx, cy, c = sol
    r_sq = cx*cx + cy*cy + c
    if r_sq <= 0: return None
    r    = float(np.sqrt(r_sq))
    rmse = float(np.sqrt(np.mean((np.sqrt((x-cx)**2+(y-cy)**2)-r)**2)))
    return float(cx), float(cy), r, rmse

def line_max_err(pts, a, b):
    ab = b - a; n = np.linalg.norm(ab)
    if n < 1e-9: return float(np.max(np.linalg.norm(pts-a, axis=1)))
    return float(np.max(np.abs((pts[:,0]-a[0])*ab[1]-(pts[:,1]-a[1])*ab[0])/n))

def segmentize(contour_px, contour_r, z):
    """Convert contour to line/arc segments matching piece_data.json format."""
    n = len(contour_r)
    if n < 6: return []

    # Full-circle check
    fc = fit_circle(contour_r)
    if fc:
        cx, cy, r, rmse = fc
        radii = np.sqrt((contour_r[:,0]-cx)**2 + (contour_r[:,1]-cy)**2)
        perim = float(np.sum(np.linalg.norm(
            np.diff(np.vstack([contour_r, contour_r[0]]), axis=0), axis=1)))
        if (rmse < ARC_RMSE_MM
                and np.std(radii)/max(np.mean(radii),1e-6) < 0.025
                and abs(perim - 2*np.pi*r)/max(2*np.pi*r,1e-6) < 0.15):
            q1, q2, q3 = n//4, n//2, 3*n//4
            c_pt = np.array([cx, cy])
            return [
                {"type":"arc","start":xyz(contour_r[0],z),"end":xyz(contour_r[q2],z),
                 "via":xyz(contour_r[q1],z),"center":xyz(c_pt,z),
                 "radius_mm":round(r,4),"sweep_deg":180.0},
                {"type":"arc","start":xyz(contour_r[q2],z),"end":xyz(contour_r[0],z),
                 "via":xyz(contour_r[q3],z),"center":xyz(c_pt,z),
                 "radius_mm":round(r,4),"sweep_deg":180.0},
            ]

    approx  = cv2.approxPolyDP(contour_px.reshape(-1,1,2), ARC_EPSILON_PX, True)
    anchors = sorted(set(
        int(np.argmin(np.linalg.norm(contour_px - p, axis=1)))
        for p in approx[:,0,:]
    ))
    if len(anchors) < 3:
        anchors = list(range(0, n, max(1, n//8)))

    segs = []
    for i in range(len(anchors)):
        i0  = anchors[i]
        i1  = anchors[(i+1) % len(anchors)]
        sub = (contour_r[i0:i1+1] if i0 <= i1
               else np.vstack([contour_r[i0:], contour_r[:i1+1]]))
        if len(sub) < 3: continue

        s, e  = sub[0], sub[-1]
        lerr  = line_max_err(sub, s, e)
        cf    = fit_circle(sub)
        is_arc = False
        if cf:
            cx, cy, radius, rmse = cf
            angs   = np.unwrap(np.arctan2(sub[:,1]-cy, sub[:,0]-cx))
            sweep  = float(abs(np.degrees(angs[-1] - angs[0])))
            is_arc = (rmse < ARC_RMSE_MM and sweep >= MIN_ARC_DEG and lerr > LINE_TOL_MM)

        if is_arc:
            mid = sub[len(sub)//2]
            segs.append({
                "type":      "arc",
                "start":     xyz(s, z),
                "end":       xyz(e, z),
                "via":       xyz(mid, z),
                "center":    xyz(np.array([cx, cy]), z),
                "radius_mm": round(float(radius), 4),
                "sweep_deg": round(sweep, 1)
            })
        else:
            segs.append({"type":"line","start":xyz(s,z),"end":xyz(e,z)})
    return segs

def warp_contour(norm_pts, stable_box, src_segments=None, piece_w=None, piece_h=None):
    """
    If piece_w/piece_h provided, use physical mm scaling from piece_data
    so inner contour maps correctly relative to outer bounds.
    """
    sy  = stable_box[np.argsort(stable_box[:,1])]
    top = sy[:2][np.argsort(sy[:2,0])]
    bot = sy[2:][np.argsort(sy[2:,0])]
    # TL, TR, BR, BL in pixel space
    TL, TR, BR, BL = top[0], top[1], bot[1], bot[0]

    dst = np.array([TL, TR, BR, BL], dtype=np.float32)
    src = np.array([[0,0],[1,0],[1,1],[0,1]], dtype=np.float32)
    M   = cv2.getPerspectiveTransform(src, dst)

    ph  = np.concatenate([norm_pts.astype(np.float32),
                          np.ones((len(norm_pts),1))], axis=1)
    w   = (M @ ph.T).T
    return (w[:,:2] / w[:,2:3]).astype(np.float32)