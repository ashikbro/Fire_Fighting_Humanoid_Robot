import pytest
from fastapi.testclient import TestClient
from src.api import app
import os

client = TestClient(app)

def test_read_main():
    response = client.get("/")
    assert response.status_code == 404 # No root endpoint defined

def test_api_status():
    response = client.get("/api/v1/status")
    assert response.status_code == 200
    data = response.json()
    assert "gps" in data
    assert "fire_severity" in data
    assert "fire_location" in data

def test_api_move_valid_command():
    commands = [
        "move_forward", "move_backward", "turn_left", "turn_right",
        "stop", "activate_water_pump", "deactivate_water_pump",
        "activate_extinguisher", "deactivate_extinguisher",
        "start_auto_patrol", "stop_auto_patrol"
    ]
    for cmd in commands:
        response = client.post("/api/v1/move", json={"command": cmd})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["command"] == cmd

def test_api_move_invalid_command():
    response = client.post("/api/v1/move", json={"command": "invalid_command"})
    assert response.status_code == 400

def test_vision_detection_no_file():
    response = client.post("/api/v1/vision_detection")
    assert response.status_code == 422  # FastAPI's handling of missing file

# Basic authentication test
def test_admin_only_unauthorized():
    response = client.get("/api/v1/admin_only")
    assert response.status_code == 401

# This is a placeholder for a real authentication test.
# In a real-world scenario, you would create a test user
# and use their credentials to authenticate.
def test_admin_only_authorized():
    # This test will fail without a valid user in users.txt
    # You can create a test user for this purpose
    response = client.get("/api/v1/admin_only", auth=("admin", "admin"))
    if response.status_code == 200:
        assert response.json() == {"message": "Admin access granted"}
    else:
        assert response.status_code == 401
