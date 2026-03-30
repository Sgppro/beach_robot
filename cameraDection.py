import cv2
import os
import numpy as np
import subprocess
import time
from detection import CustomObjectDetector

def find_usb_camera_index(max_index=40):
    """
    Find the index of a working USB camera by scanning /dev/video* indices.
    Prints v4l2 device list if available.
    """
    # Try to show v4l2 devices for debugging
    try:
        result = subprocess.run(['v4l2-ctl', '--list-devices'], 
                                capture_output=True, text=True)
        if result.returncode == 0:
            print("v4l2 devices:")
            print(result.stdout)
    except:
        pass

    print("Scanning for camera...")
    for i in range(max_index + 1):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            # Try to read a frame to confirm it's working
            ret, frame = cap.read()
            if ret and frame is not None:
                cap.release()
                print(f"Found working camera at index {i}")
                return i
            cap.release()
    print("No working camera found.")
    return None

def main():
    # --- Paths ---
    script_dir = os.path.dirname(os.path.abspath(__file__))
    HEF_PATH = os.path.join(script_dir, "beach_robot.hef")
    LABELS_PATH = os.path.join(script_dir, "beach_robot_labels.json")

    if not os.path.exists(HEF_PATH) or not os.path.exists(LABELS_PATH):
        print("Error: Model or labels file not found.")
        return

    # --- Initialize Hailo detector ---
    print("Initializing Hailo detector...")
    detector = CustomObjectDetector(HEF_PATH, LABELS_PATH, conf_threshold=0.3)

    # --- Find camera ---
    camera_index = find_usb_camera_index(max_index=40)
    if camera_index is None:
        print("Could not find a working USB camera. Exiting.")
        return

    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        print(f"Error: Could not open camera at index {camera_index}.")
        return

    # Optional: set resolution
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    print(f"Camera opened at index {camera_index}. Starting live inference (headless mode).")
    print("Annotated frames will be saved every 30 frames. Press Ctrl+C to stop.")

    frame_count = 0
    SAVE_EVERY_N_FRAMES = 30   # adjust as needed

    try:
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

            # Draw detections
            for det in detections:
                xmin, ymin, xmax, ymax = det['bbox']
                cv2.rectangle(frame_bgr, (xmin, ymin), (xmax, ymax), (0, 255, 0), 5)
                label = f"{det['label']} {det['score']:.2f}"
                cv2.putText(frame_bgr, label, (xmin, ymin-15),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 3)

            # Save every Nth frame
            if frame_count % SAVE_EVERY_N_FRAMES == 0:
                timestamp = int(time.time())
                filename = f"detection_{timestamp}_{frame_count}.jpg"
                cv2.imwrite(filename, frame_bgr)
                print(f"Saved {filename} with {len(detections)} detections")

            frame_count += 1

    except KeyboardInterrupt:
        print("\nStopped by user")
    finally:
        cap.release()
        print("Camera released.")

if __name__ == "__main__":
    main()
