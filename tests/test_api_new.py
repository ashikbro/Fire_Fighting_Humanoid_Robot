import os

os.environ['DISABLE_CAMERA_THREAD'] = 'true'

import pytest
import json
from werkzeug.security import generate_password_hash
from src.api import app, check_auth, USERS

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_api_status(client):
    response = client.get('/api/v1/status')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'gps' in data
    assert 'fire_severity' in data
    assert 'fire_location' in data

def test_api_health_in_simulation(client, monkeypatch):
    monkeypatch.setattr('src.api.SIMULATION_MODE', True)
    response = client.get('/api/v1/health')
    assert response.status_code == 200
    assert response.json['status'] == 'ok'
    assert response.json['simulation_mode'] is True

def test_api_move_valid_command(client):
    commands = [
        'move_forward', 'move_backward', 'turn_left', 'turn_right',
        'stop', 'activate_water_pump', 'deactivate_water_pump',
        'activate_extinguisher', 'deactivate_extinguisher',
        'start_auto_patrol', 'stop_auto_patrol'
    ]
    for cmd in commands:
        response = client.post('/api/v1/move', json={'command': cmd})
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'success'
        assert data['command'] == cmd

def test_api_move_invalid_command(client):
    response = client.post('/api/v1/move', json={'command': 'invalid_command'})
    assert response.status_code == 400
    data = json.loads(response.data)
    assert 'error' in data

def test_vision_detection_no_file(client):
    response = client.post('/api/v1/vision_detection')
    assert response.status_code == 400
    data = json.loads(response.data)
    assert 'error' in data

def test_hashed_authentication():
    USERS['test-user'] = {
        'password_hash': generate_password_hash('correct-password'),
        'role': 'operator',
    }
    assert check_auth('test-user', 'correct-password')
    assert not check_auth('test-user', 'wrong-password')
    USERS.pop('test-user')

# Additional tests for vision_detection with file upload can be added if needed
