import threading
import time
import queue

from stream_detection import CameraDetector
from motor import MotorController
from app import create_app
from shared_state import robot_state

def camera_loop(stop_event, command_queue):
    detector = CameraDetector
    while not stop_event.is_set():
        result = detector.detect()
        if result:
            command_queue.put(result)
        time.sleep(0.05)

def motor_worker(stop_event, command_queue):
    motor = MotorController()
    while not stop_event.is_set():
        try:
            cmd = command_queue.get(timeout=0.5)
            motor.execute(cmd)
        except queue.Empty:
            pass   # no new command

def flask_thread(stop_event):
    app = create_app()   # your Flask app, may use shared_state
    # Run Flask's server, but block until stop_event is set
    # We use a separate thread for the server
    from werkzeug.serving import make_server
    server = make_server('0.0.0.0', 5000, app)
    server.serve_forever()

def main():
    stop_event = threading.Event()
    command_queue = queue.Queue()

    threads = [
        threading.Thread(target=camera_loop, args=(stop_event, command_queue), daemon=True),
        threading.Thread(target=motor_worker, args=(stop_event, command_queue), daemon=True),
        threading.Thread(target=flask_thread, args=(stop_event,), daemon=True),
    ]

    for t in threads:
        t.start()

    try:
        # Keep main thread alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Shutting down...")
        stop_event.set()
        # Let threads finish (daemon threads will exit when main ends)
        for t in threads:
            t.join(timeout=2)

if __name__ == "__main__":
    main()
