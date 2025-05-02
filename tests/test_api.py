import pytest
from fastapi.testclient import TestClient
from src.api import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_predict_valid_input():
    payload = {
        "temperature": 50.0,
        "smoke_density": 100.0,
        "gas_level": 300.0,
        "humidity": 40.0
    }
    response = client.post("/predict", json=payload)
    assert response.status_code == 200
    assert "fire_severity" in response.json()

def test_predict_invalid_input():
    payload = {
        "temperature": "hot",
        "smoke_density": 100.0,
        "gas_level": 300.0,
        "humidity": 40.0
    }
    response = client.post("/predict", json=payload)
    assert response.status_code == 422  # Unprocessable Entity due to validation error
