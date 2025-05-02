from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import joblib
import numpy as np
import os
import logging

app = FastAPI(title="Fire Severity Prediction API")

class SensorData(BaseModel):
    temperature: float = Field(..., ge=-50, le=100, description="Temperature in Celsius")
    smoke_density: float = Field(..., ge=0, le=1000, description="Smoke density level")
    gas_level: float = Field(..., ge=0, le=1000, description="Gas level")
    humidity: float = Field(..., ge=0, le=100, description="Humidity percentage")

# Load model and label encoder from models directory
model_path = os.path.join(os.path.dirname(__file__), '..', 'models', 'fire_severity_model.pkl')
encoder_path = os.path.join(os.path.dirname(__file__), '..', 'models', 'label_encoder.pkl')

model = joblib.load(model_path)
label_encoder = joblib.load(encoder_path)

@app.get("/")
def read_root():
    return {"message": "Fire Severity Prediction API is running."}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.post("/predict")
def predict_fire_severity(data: SensorData):
    try:
        # Compute engineered features
        temp_smoke_interaction = data.temperature * data.smoke_density
        gas_humidity_interaction = data.gas_level * data.humidity
        temp_squared = data.temperature ** 2
        smoke_squared = data.smoke_density ** 2
        gas_squared = data.gas_level ** 2
        humidity_squared = data.humidity ** 2

        # Construct feature array with 10 features
        features = np.array([[
            data.temperature,
            data.smoke_density,
            data.gas_level,
            data.humidity,
            temp_smoke_interaction,
            gas_humidity_interaction,
            temp_squared,
            smoke_squared,
            gas_squared,
            humidity_squared
        ]])

        prediction = model.predict(features)
        severity = label_encoder.inverse_transform(prediction)[0]
        if severity not in label_encoder.classes_:
            severity = "Unknown"
        return {"fire_severity": severity}
    except Exception as e:
        logging.error(f"Prediction error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
