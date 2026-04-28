import cv2
import numpy as np
import os
import threading
import time
from flask import Flask, Response, render_template_string
from detection import CustomObjectDetector  # your existing class
from collections import Counter

# ----------------------------------------------------------------------
# Global variables shared between the detection thread and Flask
# ----------------------------------------------------------------------
frame_lock = threading.Lock()
current_frame = None          # holds the latest annotated frame (as JPEG bytes)
fps = 0
detection_count = 0

# ----------------------------------------------------------------------
# Detection thread
# ----------------------------------------------------------------------
def detection_loop(detector, camera_index):
    global current_frame, fps, detection_count

    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        print(f"Error: Cannot open camera {camera_index}")
        return

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    print("Detection thread started. Processing frames...")

    frame_count = 0
    start_time = time.time()

    while True:
        ret, frame_bgr = cap.read()
        if not ret:
            print("Failed to grab frame")
            break

        # Preprocess
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        resized = cv2.resize(frame_rgb, (detector.input_width, detector.input_height))
        preprocessed = np.expand_dims(resized, axis=0).astype(np.uint8)

        # Inference
        raw_results = detector.run_inference(preprocessed)

        # Postprocess
        detections = detector.postprocess(raw_results, frame_bgr)

        # --- Filter out too-large detections ---
        img_h, img_w = frame_bgr.shape[:2]
        max_allowed_area = 0.9 * img_w * img_h
        valid_detections = []
        for det in detections:
            xmin, ymin, xmax, ymax = det['bbox']
            box_area = (xmax - xmin) * (ymax - ymin)
            if box_area < max_allowed_area:
                valid_detections.append(det)

        # --- Get unique class names ---
        detected_classes = sorted(set(det['label'] for det in valid_detections))
        detection_count = len(valid_detections)  # still keep total count if needed elsewhere

        # Build a readable string
        if detected_classes:
            detected_str = "Detected: " + ", ".join(detected_classes)
        else:
            detected_str = "Detected: None"

        # --- Draw only text overlays (no boxes) ---
        cv2.putText(frame_bgr, f"FPS: {fps:.1f}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)
        cv2.putText(frame_bgr, detected_str, (10, 70),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

        # --- FPS calculation ---
        frame_count += 1
        elapsed = time.time() - start_time
        if elapsed >= 1.0:
            fps = frame_count / elapsed
            frame_count = 0
            start_time = time.time()

        # Encode frame as JPEG for streaming
        ret_jpeg, jpeg_buffer = cv2.imencode('.jpg', frame_bgr)
        if not ret_jpeg:
            continue

        with frame_lock:
            current_frame = jpeg_buffer.tobytes()

    cap.release()
    print("Detection thread stopped.")

# ----------------------------------------------------------------------
# Flask app for streaming
# ----------------------------------------------------------------------
app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Live Hailo Detection</title>
</head>
<body>
    <h1>Live Camera with AI Detection</h1>
    <img src="{{ url_for('video_feed') }}" width="800" />
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

def generate_frames():
    """Generator that yields JPEG frames for MJPEG streaming."""
    global current_frame
    while True:
        with frame_lock:
            if current_frame is None:
                continue
            frame_data = current_frame
        # Yield in multipart format
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_data + b'\r\n')
        # Small delay to control CPU usage
        time.sleep(0.03)

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------
if __name__ == '__main__':
    # Paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    HEF_PATH = os.path.join(script_dir, "beach_robot.hef")
    LABELS_PATH = os.path.join(script_dir, "beach_robot_labels.json")

    if not os.path.exists(HEF_PATH) or not os.path.exists(LABELS_PATH):
        print("Error: Model or labels file not found.")
        exit(1)

    # Initialize detector
    print("Initializing Hailo detector...")
    detector = CustomObjectDetector(HEF_PATH, LABELS_PATH, conf_threshold=0.1)

    # Find camera index (same logic as before)
    def find_camera_index():
        import subprocess
        try:
            result = subprocess.run(['v4l2-ctl', '--list-devices'],
                                    capture_output=True, text=True)
            print("v4l2 devices:\n", result.stdout)
        except:
            pass
        for i in range(10):   # scan first 10 indices
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                ret, _ = cap.read()
                cap.release()
                if ret:
                    print(f"Using camera index {i}")
                    return i
        return None

    cam_idx = find_camera_index()
    if cam_idx is None:
        print("No camera found.")
        exit(1)

    # Start the detection thread
    thread = threading.Thread(target=detection_loop, args=(detector, cam_idx), daemon=True)
    thread.start()

    # Give the thread a moment to open the camera
    time.sleep(1)

    # Start Flask server
    print("Starting web server on http://0.0.0.0:5000")
    app.run(host='0.0.0.0', port=5000, threaded=True)
