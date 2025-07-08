import joblib
import numpy as np
import os
import logging
from fastapi import HTTPException
from pydantic import BaseModel, Field

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fire_severity_api")

class SensorData(BaseModel):
    temperature: float = Field(..., ge=-50, le=100, description="Temperature in Celsius")
    smoke_density: float = Field(..., ge=0, le=1000, description="Smoke density level")
    gas_level: float = Field(..., ge=0, le=1000, description="Gas level")
    humidity: float = Field(..., ge=0, le=100, description="Humidity percentage")

# Load legacy model and label encoder from models directory
model_path = os.path.join(os.path.dirname(__file__), '..', 'models', 'fire_severity_model.pkl')
encoder_path = os.path.join(os.path.dirname(__file__), '..', 'models', 'label_encoder.pkl')

model = joblib.load(model_path)
label_encoder = joblib.load(encoder_path)

from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Fire Severity Prediction API is running."}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.post("/predict_legacy")
def predict_fire_severity_legacy(data: SensorData):
    try:
        features = np.array([[data.temperature, data.smoke_density, data.gas_level, data.humidity]])
        prediction = model.predict(features)
        severity = label_encoder.inverse_transform(prediction)[0]
        return {"fire_severity": severity}
    except Exception as e:
        logger.error(f"Prediction error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
