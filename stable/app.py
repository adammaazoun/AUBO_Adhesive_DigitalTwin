from flask import Flask, jsonify
import threading
import debug_stream
import vision_detector
import robot_controller
import pipeline
import config
app = Flask(__name__)
_pipeline_thread = None


@app.route('/start', methods=['GET'])
def start():
    global _pipeline_thread

    if vision_detector.H_MATRIX is None:
        return jsonify({"status": "error", "message": "Service uncalibrated"}), 500

    if _pipeline_thread is not None and _pipeline_thread.is_alive():
        return jsonify({"status": "already_running"}), 200

    pipeline._stop_flag.clear()
    _pipeline_thread = threading.Thread(target=pipeline.run_pipeline, daemon=True)
    _pipeline_thread.start()
    return jsonify({"status": "started"})


@app.route('/stop', methods=['GET'])
def stop():
    pipeline.stop_pipeline()
    return jsonify({"status": "stopping"})


@app.route('/status', methods=['GET'])
def status():
    running = _pipeline_thread is not None and _pipeline_thread.is_alive()
    return jsonify({"pipeline_running": running})


if __name__ == '__main__':
    vision_detector.load_reference_data()
    vision_detector.init_homography()
    if config.DEBUG:
        debug_stream.start(port=8095)

    # threaded=True: /stop and /status need to be servable while the
    # pipeline thread is blocking on belt/robot calls.
    app.run(host='0.0.0.0', port=5001, debug=False, threaded=True)
