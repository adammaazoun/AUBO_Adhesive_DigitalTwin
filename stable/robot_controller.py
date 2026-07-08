import socket
import time
import json
import threading
import math
# ── Robot Hardware Configuration ──────────────────────────
ROBOT_IP           = "192.168.239.128"
ROBOT_PORT         = 30004
AUBO_OK            = 0
AUBO_BUSY          = 2
AUBO_ALREADY_THERE = 13

# ── Unity Configuration ───────────────────────────────────
UNITY_IP   = "127.0.0.1"
UNITY_PORT = 9999
PYTHON_LISTEN_PORT = 9998

unity_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Global state for shared socket and thread safety
robot_socket = None
socket_lock = threading.Lock()

# ── PERSISTENT LIVE PARAMETER CACHE ────────────────────────
current_speed_fraction = 1.0  # Scales the baseline 0.2 (200mm/s)
current_acc            = 0.6  # Default acceleration
current_blend_radius   = 0.002 # Default blend radius (2mm)

belt_position_m = 0.0
belt_position_lock = threading.Lock()
_last_encoder_time = 0.0
# ── Belt ack signaling ─────────────────────────────────────
# Set whenever Unity reports the belt has physically stopped after a
# BELT_STOP_AFTER command. The pipeline orchestrator blocks on this.
belt_stopped_event = threading.Event()


def send_to_unity(message):
    try:
        unity_socket.sendto(message.encode(), (UNITY_IP, UNITY_PORT))
    except Exception as e:
        print(f"[UNITY] Failed to send: {e}")

# Compensates for the physical shift when the glue-station stop distance
# was changed. Applied along the belt's travel axis before the robot moves.
STATION_OFFSET_X_M = 0.055  # adjust sign/axis to match your rig
STATION_OFFSET_Y_M = 0.0

STATION_ROTATION_DEG = 5


def _apply_station_offset(segments):
    shifted = []
    for seg in segments:
        new_seg = dict(seg)
        for key in ("start", "end", "via", "center"):
            if key in seg and seg[key] is not None:
                pt = dict(seg[key])
                pt["X"] = pt["X"] + STATION_OFFSET_X_M * 1000.0  # segments are in mm
                pt["Y"] = pt["Y"] + STATION_OFFSET_Y_M * 1000.0
                new_seg[key] = pt
        shifted.append(new_seg)
    return shifted

def belt_run():
    """Tell Unity to run the conveyor continuously."""
    send_to_unity("BELT_RUN")


def belt_stop_after(distance_m):
    """Tell Unity to keep running the belt until it has advanced
    `distance_m` further, then stop. Unity will ack with BELT_STOPPED
    on the PYTHON_LISTEN_PORT once it actually halts."""
    belt_stopped_event.clear()
    send_to_unity(f"BELT_STOP_AFTER:{distance_m}")


def wait_for_belt_stopped(timeout=15.0):
    """Blocks until Unity's BELT_STOPPED ack arrives. Raises on timeout."""
    if not belt_stopped_event.wait(timeout=timeout):
        raise RuntimeError("Timed out waiting for BELT_STOPPED ack from Unity.")

def belt_stop():
    send_to_unity("BELT_STOP")

def rpc(s, method, params=[]):
    msg = json.dumps({"jsonrpc": "2.0", "method": method, "params": params, "id": 1})
    with socket_lock:
        s.sendall(msg.encode())
        data = b""
        while True:
            data += s.recv(4096)
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                continue


def rpc_with_retry(s, method, params, retries=200, retry_delay=0.02):
    for _ in range(retries):
        resp = rpc(s, method, params)
        if "error" in resp:
            raise RuntimeError(f"{method} RPC error: {resp['error']}")
        result = resp.get("result", -1)
        if result in (AUBO_OK, AUBO_ALREADY_THERE):
            return resp
        elif result == AUBO_BUSY:
            time.sleep(retry_delay)
            continue
        else:
            raise RuntimeError(f"{method} unexpected response: {resp}")
    raise RuntimeError(f"{method} timed out on BUSY")


def wait_motion_complete(s, timeout=120, skip_if_idle=False):
    deadline = time.time() + timeout
    time.sleep(0.15)
    while time.time() < deadline:
        if rpc(s, "rob1.MotionControl.getExecId").get("result", -1) >= 0:
            break
        time.sleep(0.02)
    else:
        if skip_if_idle: return
        raise RuntimeError("Timeout: motion never started")

    while time.time() < deadline:
        if rpc(s, "rob1.MotionControl.getExecId").get("result", -1) == -1:
            return
        time.sleep(0.02)
    raise RuntimeError("Timeout: motion never completed")


def unity_udp_listener():
    """ Listens for UDP messages from Unity: slider parameter adjustments,
    the BELT_STOPPED ack, and belt encoder position updates. """
    global robot_socket, current_speed_fraction, current_acc, current_blend_radius
    global belt_position_m, _last_encoder_time   # <-- BOTH must be declared here

    listen_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    listen_socket.bind(("0.0.0.0", PYTHON_LISTEN_PORT))
    print(f"[UNITY LISTENER] Watching for Unity UDP messages on port {PYTHON_LISTEN_PORT}...")

    while True:
        try:
            data, addr = listen_socket.recvfrom(1024)
            msg = data.decode().strip()

            if msg == "BELT_STOPPED":
                print("[BELT] Received BELT_STOPPED ack from Unity.")
                belt_stopped_event.set()

            elif msg.startswith("ENCODER:"):
                val = float(msg.split(":")[1])
                with belt_position_lock:
                    belt_position_m = val
                    _last_encoder_time = time.time()

            elif msg.startswith("SPEED:"):
                val = float(msg.split(":")[1])
                val = max(0.02, min(val, 2.0))
                if abs(current_speed_fraction - val) > 0.005:
                    current_speed_fraction = val
                    print(f"[CACHE] Speed Fraction updated: {current_speed_fraction * 100:.1f}%")
                    with socket_lock:
                        sock = robot_socket
                    if sock:
                        try:
                            rpc(sock, "rob1.MotionControl.setSpeedFraction", [val])
                        except (OSError, socket.error) as e:
                            print(f"[UNITY LISTENER] Speed-fraction push failed (socket likely closed mid-call): {e}")

            elif msg.startswith("ACC:"):
                val = float(msg.split(":")[1])
                val = max(0.05, min(val, 3.0))
                if abs(current_acc - val) > 0.01:
                    current_acc = val
                    print(f"[CACHE] Path Acceleration updated: {current_acc} m/s^2")

            elif msg.startswith("BLEND:"):
                val = float(msg.split(":")[1])
                val = max(0.0, min(val, 0.05))
                if abs(current_blend_radius - val) > 0.0005:
                    current_blend_radius = val
                    print(f"[CACHE] Blend Radius updated: {current_blend_radius * 1000:.1f} mm")

        except Exception as e:
            print(f"[UNITY LISTENER] Error processing packet: {e}")


# Start the shared listener thread (sliders + belt acks)
_listener_thread = threading.Thread(target=unity_udp_listener, daemon=True)
_listener_thread.start()


def execute_robot_path(segments, speed=0.2, acc=0.6, blend_radius=0.002, start_lift=10.0, end_lift=20.0):
    """Glues one piece that is currently stationary at the glue station.
    Does NOT touch the belt — the caller (pipeline orchestrator) decides
    when to resume continuous motion after this returns."""
    global robot_socket, current_speed_fraction, current_acc, current_blend_radius

    segments = _apply_station_offset(segments)


    speed = 0.2                              # Fixed baseline; Unity speed fraction scales it.
    acc = current_acc
    blend_radius = current_blend_radius

    start_lift_m = float(start_lift) / 1000.0
    end_lift_m = float(end_lift) / 1000.0

    robot_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    robot_socket.settimeout(5.0)
    robot_socket.connect((ROBOT_IP, ROBOT_PORT))

    try:
        print(f"[ROBOT] Starting path logic. Speed: {speed*1000:.0f}mm/s @ {current_speed_fraction*100:.0f}%, Acc: {acc}m/s^2, Blend: {blend_radius*1000:.1f}mm")
        rpc(robot_socket, "rob1.MotionControl.setSpeedFraction", [current_speed_fraction])

        rx, ry, rz = 3.14159, 0.0, 0.0

        first_start = segments[0]["start"]
        sx = float(first_start["X"]) / 1000.0
        sy = float(first_start["Y"]) / 1000.0
        sz = float(first_start["Z"]) / 1000.0

        approach_pose = [sx, sy, sz + start_lift_m, rx, ry, rz]
        rpc_with_retry(robot_socket, "rob1.MotionControl.moveLine", [approach_pose, acc, speed, 0, 0])
        wait_motion_complete(robot_socket, skip_if_idle=True)

        init_pose = [sx, sy, sz, rx, ry, rz]
        rpc_with_retry(robot_socket, "rob1.MotionControl.moveLine", [init_pose, acc, speed, 0, 0])
        wait_motion_complete(robot_socket, skip_if_idle=False)

        send_to_unity("GLUE_ON")

        last_idx = len(segments) - 1
        for i, seg in enumerate(segments):
            br = 0.0 if i == last_idx else float(blend_radius)

            tx = float(seg["end"]["X"]) / 1000.0
            ty = float(seg["end"]["Y"]) / 1000.0
            tz = float(seg["end"]["Z"]) / 1000.0
            end_pose = [tx, ty, tz, rx, ry, rz]

            if seg["type"] == "line":
                rpc_with_retry(robot_socket, "rob1.MotionControl.moveLine", [end_pose, acc, speed, br, 0])
            elif seg["type"] == "arc":
                vx = float(seg["via"]["X"]) / 1000.0
                vy = float(seg["via"]["Y"]) / 1000.0
                vz = float(seg["via"]["Z"]) / 1000.0
                via_pose = [vx, vy, vz, rx, ry, rz]
                rpc_with_retry(robot_socket, "rob1.MotionControl.moveCircle", [via_pose, end_pose, acc, speed, br, 0])

        wait_motion_complete(robot_socket)

        send_to_unity("GLUE_OFF")

        last_end = segments[-1]["end"]
        ex = float(last_end["X"]) / 1000.0
        ey = float(last_end["Y"]) / 1000.0
        ez = float(last_end["Z"]) / 1000.0

        retract_pose = [ex, ey, ez + end_lift_m, rx, ry, rz]
        rpc_with_retry(robot_socket, "rob1.MotionControl.moveLine", [retract_pose, acc, speed, 0, 0])
        wait_motion_complete(robot_socket)
        # NOTE: no CONVEYOR_ADVANCE here anymore — belt resumption is the
        # pipeline orchestrator's job (it calls robot_controller.belt_run()
        # once it's ready for the next cycle).

        print("[ROBOT] Complete execution pathway processed successfully! 🤖💨")

    finally:
        with socket_lock:
            if robot_socket:
                robot_socket.close()
                robot_socket = None
# ── Belt encoder tracking ──────────────────────────────────
# Cumulative belt distance (m) as reported by Unity's ConveyorBelt. This is
# the ground truth for how far the belt has physically moved — used instead
# of a time*speed estimate, which drifts under any scheduling jitter, glue
# duration, or belt speed change.



def get_belt_position():
    """Latest known cumulative belt distance in meters."""
    with belt_position_lock:
        return belt_position_m


def get_belt_position_freshness():
    """Seconds since the last ENCODER packet was received — use this to
    detect a stalled/dropped Unity connection before trusting the reading."""
    with belt_position_lock:
        if _last_encoder_time == 0.0:
            return float("inf")
        return time.time() - _last_encoder_time

STATION_ROTATION_DEG = 0.1
STATION_ROTATION_PIVOT = (117.99, 208.49)  # mm, rotation center — default is
                                            # the piece's own nominal center;
                                            # adjust to match your glue station


def _rotate_point(x, y, deg, pivot):
    if deg == 0.0:
        return x, y
    rad = math.radians(deg)
    cos_a, sin_a = math.cos(rad), math.sin(rad)
    px, py = pivot
    dx, dy = x - px, y - py
    rx = dx * cos_a - dy * sin_a + px
    ry = dx * sin_a + dy * cos_a + py
    return rx, ry


def _apply_station_offset(segments):
    pivot = _segments_centroid(segments)  # computed fresh from this piece's actual path
    shifted = []
    for seg in segments:
        new_seg = dict(seg)
        for key in ("start", "end", "via", "center"):
            if key in seg and seg[key] is not None:
                pt = dict(seg[key])
                rx, ry = _rotate_point(pt["X"], pt["Y"], STATION_ROTATION_DEG, pivot)
                pt["X"] = rx + STATION_OFFSET_X_M * 1000.0
                pt["Y"] = ry + STATION_OFFSET_Y_M * 1000.0
                new_seg[key] = pt
        shifted.append(new_seg)
    return shifted

def _segments_centroid(segments):
    """Computes the bounding-box center (in whatever coordinate space the
    segments are currently in — robot mm, at the point this is called) from
    the actual path being executed, rather than a hardcoded guess. This is
    what STATION_ROTATION_PIVOT should rotate around, since it needs to
    match wherever the piece actually is, not a fixed template value."""
    xs, ys = [], []
    for seg in segments:
        for key in ("start", "end", "via"):
            if key in seg and seg[key] is not None:
                xs.append(seg[key]["X"])
                ys.append(seg[key]["Y"])
    return (min(xs) + max(xs)) / 2.0, (min(ys) + max(ys)) / 2.0