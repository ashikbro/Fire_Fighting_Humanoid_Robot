import cv2
import numpy as np
from vision_fire_detection.detect_fire_from_image import FireDetector
import os
import logging
from sklearn.preprocessing import StandardScaler
import numpy as np
import time

from vision_fire_detection.object_detection import ObjectDetector

def profile(func):
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        end = time.perf_counter()
        logging.info(f"[PROFILE] {func.__name__} executed in {end - start:.4f} seconds")
        return result
    return wrapper

class FireDetection:
    def __init__(self, method: str = 'color_threshold', enable_object_detection: bool = False) -> None:
        self.method = method
        self.enable_object_detection = enable_object_detection
        if self.method == 'cnn':
            cnn_model_path = os.path.join(os.path.dirname(__file__), 'fire_detection_cnn.h5')
            if not os.path.exists(cnn_model_path):
                logging.warning("CNN fire detector model not found at %s; using color threshold method.", cnn_model_path)
                self.detector = None
                self.method = 'color_threshold'
            else:
                try:
                    from vision_fire_detection.detect_fire_from_image import FireDetector
                    self.detector = FireDetector(cnn_model_path)
                except Exception as exc:
                    logging.warning(
                        "CNN fire detector unavailable (%s); falling back to color threshold method.",
                        exc,
                    )
                    self.detector = None
                    self.method = 'color_threshold'
        else:
            self.detector = None

        # Load fire severity deep learning model
        dl_model_path = os.path.join(os.path.dirname(__file__), '..', 'models', 'fire_severity_model_DeepLearning.h5')
        if not os.path.exists(dl_model_path):
            logging.warning("Fire severity model not found at %s; using sensor-only fallback.", dl_model_path)
            self.severity_model = None
            self.scaler = None
            self.severity_model_loaded = False
        else:
            try:
                from tensorflow.keras.models import load_model
                self.severity_model = load_model(dl_model_path)
                self.scaler = StandardScaler()
                self.severity_model_loaded = True
            except Exception as exc:
                logging.error("Failed to load fire severity model: %s", exc)
                self.severity_model = None
                self.scaler = None
                self.severity_model_loaded = False

        if self.enable_object_detection:
            self.object_detector = ObjectDetector()
        else:
            self.object_detector = None

    @profile
    def detect_fire(self, frame: np.ndarray) -> bool:
        try:
            if self.method == 'cnn' and self.detector is not None:
                return self.detector.detect_fire(frame)
            else:
                hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
                lower_fire = np.array([0, 150, 150])
                upper_fire = np.array([35, 255, 255])
                mask = cv2.inRange(hsv, lower_fire, upper_fire)
                fire_pixels = cv2.countNonZero(mask)
                return fire_pixels > 500
        except Exception as e:
            logging.error(f"Error in detect_fire: {e}")
            return False

    @profile
    def detect_objects(self, frame: np.ndarray) -> list:
        try:
            if self.object_detector:
                return self.object_detector.detect_objects(frame)
            else:
                return []
        except Exception as e:
            logging.error(f"Error in detect_objects: {e}")
            return []

    @profile
    def predict_fire_severity(self, sensor_data: dict) -> str | None:
        if not self.severity_model_loaded:
            logging.warning("Fire severity model not loaded.")
            return None
        try:
            features = np.array([[sensor_data['Temperature'], sensor_data['SmokeDensity'], sensor_data['GasLevel'], sensor_data['Humidity']]])
            features_scaled = self.scaler.fit_transform(features)
            y_pred_prob = self.severity_model.predict(features_scaled)
            y_pred = np.argmax(y_pred_prob, axis=1)
            severity_labels = ['Low', 'Medium', 'High']
            severity = severity_labels[y_pred[0]] if y_pred[0] < len(severity_labels) else "Unknown"
            return severity
        except Exception as e:
            logging.error(f"Error predicting fire severity: {e}")
            return None

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    cap = cv2.VideoCapture(0)  # Use default camera
    if not cap.isOpened():
        logging.error("Error: Could not open video stream.")
        exit()

    # Change method to 'cnn' to use the deep learning model, enable object detection as well
    fire_detector = FireDetection(method='cnn', enable_object_detection=True)

    # Example sensor data for severity prediction (replace with real sensor input)
    example_sensor_data = {
        'Temperature': 35.0,
        'SmokeDensity': 200.0,
        'GasLevel': 50.0,
        'Humidity': 40.0
    }

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        fire_detected = fire_detector.detect_fire(frame)
        if fire_detected:
            logging.info("Fire detected!")
            severity = fire_detector.predict_fire_severity(example_sensor_data)
            if severity:
                logging.info(f"Predicted Fire Severity: {severity}")
        else:
            logging.info("No fire detected.")

        detections = fire_detector.detect_objects(frame)
        for det in detections:
            x, y, w, h = det['box']
            cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)
            label = f"{det['class_name']}: {det['confidence']:.2f}"
            cv2.putText(frame, label, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)

        cv2.imshow("Fire and Object Detection", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
