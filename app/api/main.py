from fastapi import FastAPI, Depends, HTTPException, status, Request, UploadFile, File, APIRouter, Form
from fastapi.security import OAuth2PasswordRequestForm
from app.core.security import API_KEY
from fastapi import WebSocket
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import cv2
import threading
import base64
import numpy as np
import asyncio
import sys
import os
import time
import json
from datetime import datetime, timedelta
import statistics
from app.core.logger import logger

import joblib
from automation.robot_controller import RobotController
from vision.object_detector import ObjectDetector
from app.core.config import (
    API_HOST, API_PORT, CAMERA_INDEX, SIMULATION_MODE, MODELS_DIR, YOLO_MODEL_PATH, DEBUG
)
from app.db.session import init_db, log_incident, get_incident_history as db_get_incident_history
from fastapi.staticfiles import StaticFiles
from app.core.security import get_api_key

app = FastAPI(
    title="Fire Fighting Robot API",
    description="API for Fire Fighting Humanoid Robot Control and Monitoring",
    version="1.0.0",
    docs_url="/api/docs" if DEBUG else None,  # Disable docs in production
    redoc_url="/api/redoc" if DEBUG else None
)

# Security-conscious CORS configuration
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],  # Specify exact methods
    allow_headers=["Content-Type", "Authorization", "X-API-Key"],
)

# Mount the dashboard directory to serve static files
# Define the absolute path to the dashboard directory
dashboard_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "dashboard")
app.mount("/dashboard", StaticFiles(directory=dashboard_dir), name="dashboard")

# Load the trained model and label encoder
try:
    model = joblib.load(os.path.join(MODELS_DIR, "fire_severity_model.pkl"))
    label_encoder = joblib.load(os.path.join(MODELS_DIR, "label_encoder.pkl"))
    logger.info("Model and label encoder loaded successfully.")
except FileNotFoundError:
    logger.warning("Model or label encoder not found. Running without prediction capabilities.")
    model = None
    label_encoder = None
except Exception as e:
    logger.error(f"Error loading model or label encoder: {e}")
    model = None
    label_encoder = None


# Initialize robot controller and fire detection
object_detector = ObjectDetector(model_path=YOLO_MODEL_PATH)
patrol_waypoints = [[10, 10], [10, 40], [40, 40], [40, 10]]
robot_controller = RobotController(object_detector=object_detector, patrol_waypoints=patrol_waypoints)

class SimulatedVideoCapture:
    def isOpened(self):
        return True
    def read(self):
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        return True, frame

if SIMULATION_MODE:
    video_capture = SimulatedVideoCapture()
    logger.info("Simulation mode enabled: using simulated video input.")
else:
    video_capture = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_DSHOW)
    if not video_capture.isOpened():
        logger.error("Could not open video device")

frame_lock = threading.Lock()
current_frame = None

def safe_read_frame(video_capture: cv2.VideoCapture, frame_lock: threading.Lock) -> np.ndarray | None:
    try:
        ret, frame = video_capture.read()
        if not ret:
            return None
        with frame_lock:
            return frame.copy()
    except Exception as e:
        logger.warning(f"Error reading frame: {e}")
        return None

def capture_frames():
    global current_frame
    while True:
        frame = safe_read_frame(video_capture, frame_lock)
        if frame is not None:
            current_frame = frame
        time.sleep(0.03) # Limit capture rate

capture_thread = threading.Thread(target=capture_frames)
capture_thread.daemon = True
capture_thread.start()

def generate_mjpeg():
    while True:
        with frame_lock:
            if current_frame is None:
                time.sleep(0.1)
                continue
            try:
                robot_controller.update_vision_data(current_frame)
                detected_objects = object_detector.detect_objects(current_frame)
                frame_with_visuals = object_detector.draw_boxes(current_frame, detected_objects)
                
                # Draw the fire segmentation mask if a fire is detected
                fire_detections = [obj for obj in detected_objects if obj['class_name'] == 'fire']
                if fire_detections:
                    fire_mask = robot_controller.fire_segmentation.get_fire_mask(current_frame, fire_detections[0]['bounding_box'])
                    frame_with_visuals = robot_controller.fire_segmentation.draw_segmentation_mask(frame_with_visuals, fire_mask)

                ret, jpeg = cv2.imencode('.jpg', frame_with_visuals)
                if not ret:
                    continue
                frame_bytes = jpeg.tobytes()
            except Exception as e:
                logger.error(f"MJPEG encoding error: {e}")
                continue
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        time.sleep(0.1)

@app.get("/")
def read_root():
    return {"message": "Fire Fighting Humanoid Robot API is running."}
@app.get('/video')
def video_feed() -> StreamingResponse:
    return StreamingResponse(generate_mjpeg(), media_type='multipart/x-mixed-replace; boundary=frame')

api_v1 = APIRouter()

@api_v1.post('/move')
async def api_move(request: Request, api_key: str = Depends(get_api_key)) -> dict:
    data = await request.json()
    if not data or 'command' not in data:
        raise HTTPException(status_code=400, detail="Missing command")
    command = data['command']
    speed = data.get('speed', 1.0)
    angle = data.get('angle', 90)

    try:
        if command == 'forward':
            # Improved movement logic
            current_pose = robot_controller.slam.get_pose()
            angle_rad = np.deg2rad(current_pose[2])
            if command == 'forward':
                robot_controller.set_navigation_goal(current_pose[0] + np.cos(angle_rad), current_pose[1] + np.sin(angle_rad))
            elif command == 'backward':
                robot_controller.set_navigation_goal(current_pose[0] - np.cos(angle_rad), current_pose[1] - np.sin(angle_rad))
            elif command == 'left':
                robot_controller.set_navigation_goal(current_pose[0] - np.sin(angle_rad), current_pose[1] + np.cos(angle_rad))
            elif command == 'right':
                robot_controller.set_navigation_goal(current_pose[0] + np.sin(angle_rad), current_pose[1] - np.cos(angle_rad))
            robot_controller.navigation.navigate()
        elif command == 'start_auto_patrol':
            robot_controller.auto_patrol_enabled = True
            logger.info("Auto-Patrol mode started via API.")
        elif command == 'stop_auto_patrol':
            robot_controller.auto_patrol_enabled = False
            robot_controller.navigation.goal_position = None
            logger.info("Auto-Patrol mode stopped via API.")
        else:
            raise HTTPException(status_code=400, detail="Unknown command")
        return {'status': 'success', 'command': command}
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error executing command {command}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_v1.get('/status')
def api_status() -> dict:
    # TODO: Replace with actual GPS data from a sensor
    gps_location = {'latitude': 37.7749, 'longitude': -122.4194}
    person_detected = any(obj['class_name'] == 'person' for obj in object_detector.detect_objects(current_frame) if current_frame is not None)
    status = {
        'gps': gps_location,
        'fire_severity': robot_controller.current_fire_severity,
        'fire_location': robot_controller.fire_location,
        'person_detected': person_detected
    }
    return status

@api_v1.post('/vision_detection')
async def vision_detection(file: UploadFile = File(...), api_key: str = Depends(get_api_key)) -> dict:
    try:
        file_bytes = await file.read()
        npimg = np.frombuffer(file_bytes, np.uint8)
        img = cv2.imdecode(npimg, cv2.IMREAD_COLOR)
        
        detected_objects = object_detector.detect_objects(img)
        
        fire_detected = any(obj['class_name'] == 'fire' for obj in detected_objects)
        person_detected = any(obj['class_name'] == 'person' for obj in detected_objects)

        if fire_detected:
            log_incident('fire_detected', severity='Unknown', location=(0,0))
        
        if person_detected:
            log_incident('person_detected', location=(0,0))

        img_with_boxes = object_detector.draw_boxes(img, detected_objects)
        ret, jpeg = cv2.imencode('.jpg', img_with_boxes)
        if not ret:
            raise HTTPException(status_code=500, detail="Failed to encode image")
        image_with_detections = base64.b64encode(jpeg.tobytes()).decode('utf-8')

        return {
            'fire_detected': fire_detected,
            'person_detected': person_detected,
            'objects': detected_objects,
            'image_with_detections': image_with_detections
        }
    except Exception as e:
        logger.error(f"Error in vision_detection: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_v1.get('/incident_history')
def get_incident_history() -> list:
    return db_get_incident_history()

@api_v1.get('/predictive_trends')
def get_predictive_trends() -> dict:
    from collections import Counter, defaultdict
    from sklearn.linear_model import LinearRegression

    history = db_get_incident_history()
    
    if not history:
        return {
            'incidents_per_day': {},
            'avg_severity_per_day': {},
            'forecast': {}
        }

    date_counts = Counter()
    severity_map = defaultdict(list)
    for entry in history:
        if entry.get('timestamp'):
            date = datetime.strptime(entry['timestamp'][:10], '%Y-%m-%d')
            date_counts[date] += 1
            if entry.get('severity') and entry['severity'] != 'Unknown':
                severity_map[date].append(entry['severity'])

    # Prepare data for linear regression
    X = np.array([d.toordinal() for d in date_counts.keys()]).reshape(-1, 1)
    y = np.array(list(date_counts.values()))

    # Train the model
    model = LinearRegression()
    model.fit(X, y)

    # Forecast for the next 7 days
    last_day = max(date_counts.keys())
    future_dates_ord = np.array([(last_day + timedelta(days=i)).toordinal() for i in range(1, 8)]).reshape(-1, 1)
    forecast = model.predict(future_dates_ord)

    # Format the forecast
    forecast_dict = {
        (last_day + timedelta(days=i)).strftime('%Y-%m-%d'): round(f, 2)
        for i, f in enumerate(forecast, 1)
    }

    severity_levels = {'Low': 1, 'Medium': 2, 'High': 3}
    avg_severity = {}
    for date, severities in severity_map.items():
        nums = [severity_levels.get(s, 0) for s in severities]
        avg_severity[date.strftime('%Y-%m-%d')] = statistics.mean(nums) if nums else 0
    
    return {
        'incidents_per_day': {d.strftime('%Y-%m-%d'): v for d, v in date_counts.items()},
        'avg_severity_per_day': avg_severity,
        'forecast': forecast_dict
    }


@api_v1.post('/cloud/report_event')
async def cloud_report_event(request: Request, api_key: str = Depends(get_api_key)) -> dict:
    event = await request.json()
    logger.info(f"Reporting event to cloud: {event}")
    return {'status': 'reported', 'event': event}

@api_v1.post('/cloud/notify')
async def cloud_notify(request: Request, api_key: str = Depends(get_api_key)) -> dict:
    notification = await request.json()
    logger.info(f"Sending cloud notification: {notification}")
    return {'status': 'notified', 'notification': notification}

@api_v1.get('/cloud/robots')
def cloud_robots() -> dict:
    robots = [
        {'id': 'robot1', 'status': 'active'},
        {'id': 'robot2', 'status': 'idle'}
    ]
    return {'robots': robots}

@api_v1.get('/latest_heatmap')
def get_latest_heatmap() -> dict:
    # In a real application, this would return the path to the latest heatmap image
    return {"url": "https://via.placeholder.com/640x480.png?text=Heatmap+Not+Available"}

@api_v1.post('/simulation/toggle')
async def toggle_simulation(request: Request, api_key: str = Depends(get_api_key)) -> dict:
    data = await request.json()
    enabled = data.get('enabled', False)
    logger.info(f"Simulation mode set to: {enabled}")
    return {'simulation_mode': enabled, 'note': 'Set SIMULATION_MODE env var and restart for effect.'}

def self_heal():
    if not video_capture.isOpened():
        logger.warning("Video stream lost. Attempting recovery...")
        try:
            if SIMULATION_MODE:
                globals()['video_capture'] = SimulatedVideoCapture()
            else:
                globals()['video_capture'] = cv2.VideoCapture(CAMERA_INDEX)
            if video_capture.isOpened():
                logger.info("Video stream recovered.")
            else:
                logger.error("Video stream recovery failed.")
        except Exception as e:
            logger.error(f"Self-healing failed: {e}")

@api_v1.post('/self_heal')
def api_self_heal(api_key: str = Depends(get_api_key)) -> dict:
    self_heal()
    return {'status': 'self-heal attempted'}

from app.api.connection_manager import manager

async def broadcast_status():
    while True:
        await manager.broadcast(json.dumps(api_status()))
        await asyncio.sleep(5)

@app.on_event("startup")
async def startup_event():
    init_db()
    asyncio.create_task(broadcast_status())

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        manager.disconnect(websocket)

app.include_router(api_v1, prefix="/api/v1")

@app.post("/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    # This is a placeholder for a real authentication system.
    # In a production environment, you would validate the user against a database.
    # For this project, we will rely on the API key for security.
    if form_data.username == "admin" and form_data.password == "admin":
        return {"access_token": API_KEY, "token_type": "bearer"}
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect username or password",
        headers={"WWW-Authenticate": "Bearer"},
    )