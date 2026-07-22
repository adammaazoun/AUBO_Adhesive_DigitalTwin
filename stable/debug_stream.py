import cv2
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

_lock = threading.Lock()
_latest_jpeg = None
_server = None

def publish_frame(img):
    """Call this with a BGR numpy image any time you want it visible
    on the debug feed. Cheap — just re-encodes and stores the latest jpeg."""
    global _latest_jpeg
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 80])
    if ok:
        with _lock:
            _latest_jpeg = buf.tobytes()

class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass  # silence per-request logging spam

    def do_GET(self):
        if self.path != "/":
            self.send_response(404)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Age", "0")
        self.send_header("Cache-Control", "no-cache, private")
        self.send_header("Pragma", "no-cache")
        self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=FRAME")
        self.end_headers()
        try:
            while True:
                with _lock:
                    frame = _latest_jpeg
                if frame is not None:
                    self.wfile.write(b"--FRAME\r\n")
                    self.send_header("Content-Type", "image/jpeg")
                    self.send_header("Content-Length", str(len(frame)))
                    self.end_headers()
                    self.wfile.write(frame)
                    self.wfile.write(b"\r\n")
                time.sleep(0.05)  # ~20fps cap
        except (BrokenPipeError, ConnectionResetError):
            pass

def start(port=8095):
    global _server
    if _server is not None:
        return
    _server = ThreadingHTTPServer(("0.0.0.0", port), _Handler)
    threading.Thread(target=_server.serve_forever, daemon=True).start()
    print(f"[DEBUG_STREAM] Live debug feed at http://localhost:{port}/")
