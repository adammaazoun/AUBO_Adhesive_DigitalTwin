import threading
import queue
import time

import vision_detector
import robot_controller

# Distance (m) the belt travels from "piece centered under camera" to
# "piece sitting at the glue station" — matches ConveyorBelt.RunThenStopAfter.
STOP_AFTER_METERS = 0.05

# How often the scanner polls the camera for a centered piece.
POLL_INTERVAL = 0.05

# How long to wait for Unity's BELT_STOPPED ack before giving up.
BELT_STOP_ACK_TIMEOUT = 30.0

# Once a piece is captured, require its centroid to drift this far from
# center before the scanner will consider a *new* piece.
RECAPTURE_CLEAR_PX = 120

# If the encoder hasn't reported in this long, something's wrong with the
# Unity link — refuse to trust position-based distance math.
ENCODER_STALE_SEC = 1.0

_stop_flag = threading.Event()

# Queue of detected pieces: (segments, score, centered_belt_position_m)
_piece_queue = queue.Queue()


def _scanner_loop():
    """Runs continuously for the lifetime of the pipeline, regardless of
    belt/robot state. Records the belt's ACTUAL position (from Unity's
    encoder broadcast) at the instant a piece is centered — not a
    timestamp — so later distance math is exact regardless of how long
    detection or gluing takes."""
    captured_and_waiting_to_clear = False

    while not _stop_flag.is_set():
        result = vision_detector.get_piece_centroid_px()

        if result is None:
            captured_and_waiting_to_clear = False
            time.sleep(POLL_INTERVAL)
            continue

        cx, cy, w, h = result
        dx = abs(cx - w / 2)

        if captured_and_waiting_to_clear:
            if dx > RECAPTURE_CLEAR_PX:
                captured_and_waiting_to_clear = False
            time.sleep(POLL_INTERVAL)
            continue

        if dx < 80:  # widen while calibrating, tighten once stable
            if robot_controller.get_belt_position_freshness() > ENCODER_STALE_SEC:
                print("[SCANNER] WARNING: belt encoder reading is stale — skipping capture "
                      "until Unity link recovers.")
                time.sleep(POLL_INTERVAL)
                continue

            centered_position = robot_controller.get_belt_position()
            print(f"[SCANNER] centroid=({cx:.0f},{cy:.0f}) dx={dx:.0f} "
                  f"belt_pos={centered_position:.4f}m — capturing geometry")
            captured_and_waiting_to_clear = True

            segments, score, capture_pos = vision_detector.detect_piece_geometry_best_of()
            if segments is not None:
                drift_m = capture_pos - centered_position   # >=0, how far belt moved during best-of sampling
                segments = _shift_segments(segments, dx_mm=-drift_m * 1000.0)
                _piece_queue.put((segments, score, centered_position))
                print(f"[SCANNER] Queued piece (score={score:.2f}). Queue size={_piece_queue.qsize()}")
            else:
                print("[SCANNER] Piece centered but no confident geometry found — not queued.")

        time.sleep(POLL_INTERVAL)


def run_pipeline():
    """Continuous glue loop. The scanner never stops watching the camera.
    This loop pulls the next detected piece, computes exactly how far the
    belt has ACTUALLY moved since that piece was centered (via the Unity
    encoder), and commits belt_stop_after with only the true remaining
    distance."""
    print("[PIPELINE] Starting. Belt running continuously. Scanner starting.")
    robot_controller.belt_run()

    scanner_thread = threading.Thread(target=_scanner_loop, daemon=True)
    scanner_thread.start()

    piece_num = 0

    while not _stop_flag.is_set():
        try:
            segments, score, centered_position = _piece_queue.get(timeout=0.5)
        except queue.Empty:
            continue

        if robot_controller.get_belt_position_freshness() > ENCODER_STALE_SEC:
            print("[PIPELINE] WARNING: belt encoder stale when trying to commit stop — aborting this cycle.")
            continue

        current_position = robot_controller.get_belt_position()
        already_traveled = current_position - centered_position
        remaining = STOP_AFTER_METERS - already_traveled

        # if remaining < 0:
        #     print(f"[PIPELINE] WARNING: piece (score={score:.2f}) already overshot the glue station "
        #           f"by {-remaining*1000:.1f}mm (measured via encoder) — skipping this piece.")
        #     continue

        print(f"[PIPELINE] Piece ready (score={score:.2f}). Belt has moved {already_traveled*1000:.1f}mm "
              f"since centering — committing remaining {remaining*1000:.1f}mm.")
        try:
            robot_controller.belt_stop_after(remaining)
            robot_controller.wait_for_belt_stopped(timeout=BELT_STOP_ACK_TIMEOUT)
        except RuntimeError as e:
            print(f"[PIPELINE] {e} — aborting cycle.")
            continue

        piece_num += 1
        print(f"[PIPELINE] Gluing piece {piece_num} (score={score:.2f})...")
        try:
            robot_controller.execute_robot_path(segments, speed=0.05, acc=1.0)
            print(f"[PIPELINE] Piece {piece_num} glued successfully.")
        except Exception as robot_err:
            print(f"[PIPELINE] Robot error on piece {piece_num}: {robot_err}")

        robot_controller.belt_run()

    print("[PIPELINE] Stopped.")


def stop_pipeline():
    _stop_flag.set()
    robot_controller.belt_stop()
    

def _shift_segments(segments, dx_mm=0.0, dy_mm=0.0):
    shifted = []
    for seg in segments:
        new_seg = dict(seg)
        for key in ("start", "end", "via", "center"):
            if key in seg and seg[key] is not None:
                pt = dict(seg[key])
                pt["X"] = pt["X"] + dx_mm
                pt["Y"] = pt["Y"] + dy_mm
                new_seg[key] = pt
        shifted.append(new_seg)
    return shifted