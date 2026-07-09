import importlib
import sys
import threading
import types

import pytest


class DummyFireDetection:
    def __init__(self):
        self.last_sensor_data = None

    def predict_fire_severity(self, sensor_data):
        self.last_sensor_data = sensor_data
        return "Moderate"


class DummyRobotController:
    def __init__(self):
        self.fire_detector = DummyFireDetection()
        self.current_fire_severity = None
        self.fire_location = None
        self.auto_patrol_enabled = False
        noop = lambda *args, **kwargs: None
        self.actuators = types.SimpleNamespace(
            move_forward=noop,
            move_backward=noop,
            turn_left=noop,
            turn_right=noop,
            stop=noop,
            activate_water_pump=noop,
            deactivate_water_pump=noop,
            activate_extinguisher=noop,
            deactivate_extinguisher=noop,
        )


@pytest.fixture
def client(monkeypatch):
    fake_cv2 = types.SimpleNamespace(
        VideoCapture=lambda *args, **kwargs: types.SimpleNamespace(
            isOpened=lambda: True,
            read=lambda: (False, None),
        ),
        IMREAD_COLOR=1,
        FONT_HERSHEY_SIMPLEX=0,
        imdecode=lambda *args, **kwargs: None,
        imencode=lambda *args, **kwargs: (True, b""),
        rectangle=lambda *args, **kwargs: None,
        putText=lambda *args, **kwargs: None,
    )
    fake_numpy = types.SimpleNamespace(
        frombuffer=lambda *args, **kwargs: b"",
        uint8=0,
    )
    fake_robot_controller_module = types.SimpleNamespace(RobotController=DummyRobotController)
    fake_fire_detection_module = types.SimpleNamespace(FireDetection=object)

    class DummyThread:
        daemon = False

        def __init__(self, *args, **kwargs):
            pass

        def start(self):
            pass

    monkeypatch.setattr(threading, "Thread", DummyThread)
    monkeypatch.setitem(sys.modules, "cv2", fake_cv2)
    monkeypatch.setitem(sys.modules, "numpy", fake_numpy)
    monkeypatch.setitem(sys.modules, "automation.robot_controller", fake_robot_controller_module)
    monkeypatch.setitem(sys.modules, "vision_fire_detection.fire_detection", fake_fire_detection_module)

    sys.modules.pop("src.api", None)
    api_module = importlib.import_module("src.api")
    api_module.app.config["TESTING"] = True
    with api_module.app.test_client() as test_client:
        yield test_client, api_module


def test_predict_accepts_snake_case(client):
    test_client, api_module = client
    payload = {
        "temperature": 55.0,
        "smoke_density": 120.0,
        "gas_level": 450.0,
        "humidity": 25.0,
    }
    response = test_client.post("/predict", json=payload)

    assert response.status_code == 200
    assert response.get_json() == {"fire_severity": "Moderate"}
    assert api_module.fire_detection.last_sensor_data == {
        "Temperature": 55.0,
        "SmokeDensity": 120.0,
        "GasLevel": 450.0,
        "Humidity": 25.0,
    }


def test_predict_accepts_pascal_case(client):
    test_client, api_module = client
    payload = {
        "Temperature": 45.0,
        "SmokeDensity": 80.0,
        "GasLevel": 300.0,
        "Humidity": 40.0,
    }
    response = test_client.post("/predict", json=payload)

    assert response.status_code == 200
    assert response.get_json() == {"fire_severity": "Moderate"}
    assert api_module.fire_detection.last_sensor_data == payload


def test_predict_rejects_missing_fields(client):
    test_client, _ = client
    payload = {
        "temperature": 45.0,
        "smoke_density": 80.0,
        "humidity": 40.0,
    }
    response = test_client.post("/predict", json=payload)

    assert response.status_code == 400
    assert "error" in response.get_json()
