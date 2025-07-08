from fastapi import FastAPI, HTTPException, UploadFile, File
from pydantic import BaseModel, Field
import numpy as np
import logging
from src.sensor_vision_fusion import SensorVisionFusionModel
from PIL import Image
import io

app = FastAPI(title="Fire Severity Prediction API")

class SensorData(BaseModel):
    temperature: float = Field(..., example=25.0)
    smoke_density: float = Field(..., example=100.0)
    gas_level: float = Field(..., example=50.0)
    humidity: float = Field(..., example=30.0)

fusion_model = SensorVisionFusionModel()

@app.post("/predict")
async def predict_fire_severity(sensor_data: SensorData, image: UploadFile = File(None)):
    try:
        vision_image = None
        if image is not None:
            contents = await image.read()
            pil_image = Image.open(io.BytesIO(contents)).convert("RGB")
            vision_image = np.array(pil_image)
        severity = fusion_model.predict(sensor_data.dict(), vision_image)
        return {"fire_severity": severity}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
