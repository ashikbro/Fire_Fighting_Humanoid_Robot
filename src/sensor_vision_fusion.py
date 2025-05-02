import numpy as np
import joblib

class SensorVisionFusionModel:
    def __init__(self, sensor_model_path='models/fire_severity_model.pkl', vision_model_path='vision_fire_detection/fire_detection_model.h5'):
        # Load pre-trained sensor model
        self.sensor_model = joblib.load(sensor_model_path)
        # Placeholder for vision model loading (e.g., keras model)
        self.vision_model_path = vision_model_path
        self.vision_model = None  # Load as needed

    def load_vision_model(self):
        from tensorflow.keras.models import load_model
        self.vision_model = load_model(self.vision_model_path)

    def predict_vision(self, image):
        if self.vision_model is None:
            self.load_vision_model()
        # Preprocess image as required by vision model
        # This is a placeholder
        processed_image = image
        preds = self.vision_model.predict(np.array([processed_image]))
        return preds[0]

    def predict(self, sensor_data, vision_image=None):
        # sensor_data: dict with keys temperature, smoke_density, gas_level, humidity
        sensor_features = np.array([[sensor_data['temperature'], sensor_data['smoke_density'], sensor_data['gas_level'], sensor_data['humidity']]])
        sensor_pred = self.sensor_model.predict_proba(sensor_features)[0][1]  # probability of fire severity class 1

        vision_pred = 0.0
        if vision_image is not None:
            vision_pred = self.predict_vision(vision_image)

        # Simple fusion: weighted average
        fused_score = 0.6 * sensor_pred + 0.4 * vision_pred

        # Threshold to classify fire severity
        if fused_score > 0.7:
            severity = "High"
        elif fused_score > 0.4:
            severity = "Medium"
        else:
            severity = "Low"

        return severity
