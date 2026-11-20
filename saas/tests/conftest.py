import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["FIREOPS_SIMULATOR"] = "0"


@pytest.fixture()
def client(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from fireops.config import settings
    monkeypatch.setattr(settings, "database_path", str(tmp_path / "test.db"))
    monkeypatch.setattr(settings, "enable_simulator", False)
    from fireops.main import app
    with TestClient(app) as c:
        yield c


def signup(client, email="admin@acme.io", org="Acme Fire"):
    r = client.post("/api/auth/signup", json={"org_name": org, "name": "Admin", "email": email,
                                              "password": "supersecret"})
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def make_robot(client, headers, name="R1"):
    r = client.post("/api/robots", json={"name": name}, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


CALM = dict(temperature=24, smoke=10, gas=40, humidity=48, flame=False, battery=90, water_level=95,
            motor_temp=40, x=10, y=10)
FIRE = dict(temperature=88, smoke=320, gas=390, humidity=18, flame=True, battery=80, water_level=90,
            motor_temp=45, x=30, y=20)
