from flask import Flask, Response, request, jsonify, Blueprint
import cv2
import threading
import base64
import numpy as np
import sys
import os
from dotenv import load_dotenv
import time
from functools import wraps
import json
from datetime import datetime
import statistics

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from automation.robot_controller import RobotController
from vision_fire_detection.fire_detection import FireDetection
import logging

# Load environment variables from .env file
load_dotenv()

API_HOST = os.getenv('API_HOST', '127.0.0.1')
API_PORT = int(os.getenv('API_PORT', 5000))
DEBUG = os.getenv('DEBUG', 'False').lower() in ('true', '1', 'yes')
CAMERA_INDEX = int(os.getenv('CAMERA_INDEX', 0))
SIMULATION_MODE = os.getenv('SIMULATION_MODE', 'False').lower() in ('true', '1', 'yes')
CAPTURE_POLL_INTERVAL_SEC = float(os.getenv('CAPTURE_POLL_INTERVAL_SEC', 0.01))
MJPEG_STREAM_FPS = max(float(os.getenv('MJPEG_STREAM_FPS', 10.0)), 0.1)

app = Flask(__name__)

# Initialize robot controller and fire detection
robot_controller = RobotController()
fire_detection = robot_controller.fire_detector

class SimulatedVideoCapture:
    def isOpened(self):
        return True
    def read(self):
        # Return a blank image or a test pattern
        import numpy as np
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        return True, frame

# Video capture object (using camera index from env or simulation)
if SIMULATION_MODE:
    video_capture = SimulatedVideoCapture()
    logging.info("Simulation mode enabled: using simulated video input.")
else:
    video_capture = cv2.VideoCapture(CAMERA_INDEX)
    if not video_capture.isOpened():
        logging.error("Could not open video device")

# Lock for thread-safe frame access
frame_lock = threading.Lock()
frame_ready = threading.Condition(frame_lock)
current_frame = None

def safe_read_frame(video_capture, frame_lock):
    try:
        ret, frame = video_capture.read()
        if not ret:
            return None
        with frame_lock:
            return frame.copy()
    except Exception as e:
        logging.error(f"Error reading frame: {e}")
        return None

def capture_frames():
    global current_frame
    while True:
        frame = safe_read_frame(video_capture, frame_lock)
        if frame is not None:
            with frame_ready:
                current_frame = frame
                frame_ready.notify_all()
        time.sleep(CAPTURE_POLL_INTERVAL_SEC)

# Start frame capture thread
capture_thread = threading.Thread(target=capture_frames)
capture_thread.daemon = True
capture_thread.start()

def generate_mjpeg():
    frame_interval_sec = 1.0 / MJPEG_STREAM_FPS
    last_sent = 0.0
    while True:
        with frame_ready:
            while current_frame is None:
                frame_ready.wait(timeout=frame_interval_sec)
            frame = current_frame.copy()
        now = time.perf_counter()
        elapsed = now - last_sent
        if elapsed < frame_interval_sec:
            time.sleep(frame_interval_sec - elapsed)
        last_sent = time.perf_counter()
        try:
            ret, jpeg = cv2.imencode('.jpg', frame)
            if not ret:
                continue
            frame_bytes = jpeg.tobytes()
        except Exception as e:
            logging.error(f"MJPEG encoding error: {e}")
            continue
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

@app.route('/video_feed')
def video_feed():
    return Response(generate_mjpeg(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

api_v1 = Blueprint('api_v1', __name__)

def profile(func):
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        end = time.perf_counter()
        logging.info(f"[PROFILE] {func.__name__} executed in {end - start:.4f} seconds")
        return result
    return wrapper

USERS = {}
with open(os.path.join(os.path.dirname(__file__), '..', 'users.txt')) as f:
    for line in f:
        if line.strip():
            username, password, role = line.strip().split(':')
            USERS[username] = {'password': password, 'role': role}

def check_auth(username, password):
    user = USERS.get(username)
    return user and user['password'] == password

def get_role(username):
    user = USERS.get(username)
    return user['role'] if user else None

def requires_role(required_role):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            auth = request.authorization
            if not auth or not check_auth(auth.username, auth.password):
                return jsonify({'error': 'Authentication required'}), 401
            user_role = get_role(auth.username)
            if user_role != required_role and user_role != 'admin':
                return jsonify({'error': 'Insufficient permissions'}), 403
            return f(*args, **kwargs)
        return decorated
    return decorator

def log_incident(event, severity=None, location=None):
    entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "event": event,
        "severity": severity,
        "location": location
    }
    with open(os.path.join(os.path.dirname(__file__), '..', 'incident_history.log'), 'a') as f:
        f.write(json.dumps(entry) + '\n')

@api_v1.route('/move', methods=['POST'])
@profile
def api_move():
    data = request.json
    if not data or 'command' not in data:
        return jsonify({'error': 'Missing command'}), 400
    command = data['command']
    speed = data.get('speed', 1.0)
    angle = data.get('angle', 90)

    try:
        if command == 'move_forward':
            robot_controller.actuators.move_forward(speed)
        elif command == 'move_backward':
            robot_controller.actuators.move_backward(speed)
        elif command == 'turn_left':
            robot_controller.actuators.turn_left(angle)
        elif command == 'turn_right':
            robot_controller.actuators.turn_right(angle)
        elif command == 'stop':
            robot_controller.actuators.stop()
        elif command == 'activate_water_pump':
            robot_controller.actuators.activate_water_pump()
        elif command == 'deactivate_water_pump':
            robot_controller.actuators.deactivate_water_pump()
        elif command == 'activate_extinguisher':
            robot_controller.actuators.activate_extinguisher()
        elif command == 'deactivate_extinguisher':
            robot_controller.actuators.deactivate_extinguisher()
        elif command == 'start_auto_patrol':
            robot_controller.auto_patrol_enabled = True
            logging.info("Auto-Patrol mode started via API.")
        elif command == 'stop_auto_patrol':
            robot_controller.auto_patrol_enabled = False
            robot_controller.actuators.stop()
            logging.info("Auto-Patrol mode stopped via API.")
        else:
            return jsonify({'error': 'Unknown command'}), 400
        return jsonify({'status': 'success', 'command': command})
    except Exception as e:
        logging.error(f"Error executing command {command}: {e}")
        return jsonify({'error': str(e)}), 500

@api_v1.route('/status')
def api_status():
    # Placeholder GPS coordinates and status
    gps_location = {
        'latitude': 37.7749,
        'longitude': -122.4194
    }
    status = {
        'gps': gps_location,
        'fire_severity': robot_controller.current_fire_severity,
        'fire_location': robot_controller.fire_location
    }
    return jsonify(status)

@api_v1.route('/vision_detection', methods=['POST'])
@profile
def vision_detection():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    try:
        file_bytes = file.read()
        npimg = np.frombuffer(file_bytes, np.uint8)
        img = cv2.imdecode(npimg, cv2.IMREAD_COLOR)
        fire_detected = fire_detection.detect_fire(img)
        if fire_detected:
            log_incident('fire_detected', severity='Unknown', location=[0,0])
        objects = fire_detection.detect_objects(img)

        # Draw detection boxes on image
        for det in objects:
            x, y, w, h = det['box']
            cv2.rectangle(img, (x, y), (x + w, y + h), (255, 0, 0), 2)
            label = f"{det['class_name']}: {det['confidence']:.2f}"
            cv2.putText(img, label, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)

        # Encode image with detections to base64
        ret, jpeg = cv2.imencode('.jpg', img)
        if not ret:
            return jsonify({'error': 'Failed to encode image'}), 500
        image_with_detections = base64.b64encode(jpeg.tobytes()).decode('utf-8')

        return jsonify({
            'fire_detected': fire_detected,
            'objects': objects,
            'image_with_detections': image_with_detections
        })
    except Exception as e:
        logging.error(f"Error in vision_detection: {e}")
        return jsonify({'error': str(e)}), 500

@api_v1.route('/incident_history')
@requires_role('admin')
def get_incident_history():
    history = []
    with open(os.path.join(os.path.dirname(__file__), '..', 'incident_history.log')) as f:
        for line in f:
            history.append(json.loads(line))
    return jsonify(history)

@api_v1.route('/predictive_trends')
@requires_role('admin')
def get_predictive_trends():
    # Simple trend: count incidents per day and average severity
    from collections import Counter, defaultdict
    import datetime
    history = []
    with open(os.path.join(os.path.dirname(__file__), '..', 'incident_history.log')) as f:
        for line in f:
            history.append(json.loads(line))
    # Group by date
    date_counts = Counter()
    severity_map = defaultdict(list)
    for entry in history:
        if entry['timestamp']:
            date = entry['timestamp'][:10]
            date_counts[date] += 1
            if entry['severity'] and entry['severity'] != 'Unknown':
                severity_map[date].append(entry['severity'])
    # Convert severity to numeric for averaging (Low=1, Medium=2, High=3)
    severity_levels = {'Low': 1, 'Medium': 2, 'High': 3}
    avg_severity = {}
    for date, severities in severity_map.items():
        nums = [severity_levels.get(s, 0) for s in severities]
        avg_severity[date] = statistics.mean(nums) if nums else 0
    return jsonify({
        'incidents_per_day': dict(date_counts),
        'avg_severity_per_day': avg_severity
    })

@api_v1.route('/admin_only')
@requires_role('admin')
def admin_only():
    return jsonify({'message': 'Admin access granted'})

@api_v1.route('/cloud/report_event', methods=['POST'])
@requires_role('operator')
def cloud_report_event():
    # Placeholder: send event to cloud (e.g., AWS, Azure, GCP)
    event = request.json
    # Here you would integrate with cloud SDKs/APIs
    logging.info(f"Reporting event to cloud: {event}")
    return jsonify({'status': 'reported', 'event': event})

@api_v1.route('/cloud/notify', methods=['POST'])
@requires_role('admin')
def cloud_notify():
    # Placeholder: send notification to remote users
    notification = request.json
    # Integrate with cloud notification services (SNS, FCM, etc.)
    logging.info(f"Sending cloud notification: {notification}")
    return jsonify({'status': 'notified', 'notification': notification})

@api_v1.route('/cloud/robots', methods=['GET'])
@requires_role('admin')
def cloud_robots():
    # Placeholder: return list of robots for multi-robot coordination
    robots = [
        {'id': 'robot1', 'status': 'active'},
        {'id': 'robot2', 'status': 'idle'}
    ]
    return jsonify({'robots': robots})

@api_v1.route('/simulation/toggle', methods=['POST'])
@requires_role('admin')
def toggle_simulation():
    # This would require a restart in real deployment, but here we just log
    enabled = request.json.get('enabled', False)
    logging.info(f"Simulation mode set to: {enabled}")
    return jsonify({'simulation_mode': enabled, 'note': 'Set SIMULATION_MODE env var and restart for effect.'})

def self_heal():
    # Example: check video stream, try to recover if failed
    if not video_capture.isOpened():
        logging.warning("Video stream lost. Attempting recovery...")
        try:
            if SIMULATION_MODE:
                globals()['video_capture'] = SimulatedVideoCapture()
            else:
                globals()['video_capture'] = cv2.VideoCapture(CAMERA_INDEX)
            if video_capture.isOpened():
                logging.info("Video stream recovered.")
            else:
                logging.error("Video stream recovery failed.")
        except Exception as e:
            logging.error(f"Self-healing failed: {e}")

@api_v1.route('/self_heal', methods=['POST'])
@requires_role('admin')
def api_self_heal():
    self_heal()
    return jsonify({'status': 'self-heal attempted'})

# Register blueprint with version prefix
app.register_blueprint(api_v1, url_prefix='/api/v1')

if __name__ == "__main__":
    app.run(host=API_HOST, port=API_PORT, debug=DEBUG)
