"""Reference client a fire-fighting robot runs to connect to FireOps Cloud.

Usage:
    FIREOPS_URL=http://localhost:8000 FIREOPS_DEVICE_KEY=fod_... python robot_client.py

Replace `read_sensors()` and `execute()` with calls into the robot's real
hardware layer (e.g. automation/sensor_manager.py and automation/robot_controller.py).
Uses only the standard library so it runs on constrained onboard computers.
"""
from __future__ import annotations

import json
import os
import random
import time
import urllib.error
import urllib.request
from collections import deque

URL = os.getenv("FIREOPS_URL", "http://localhost:8000").rstrip("/")
KEY = os.getenv("FIREOPS_DEVICE_KEY", "")
INTERVAL = float(os.getenv("FIREOPS_INTERVAL", "2"))


class FireOpsDevice:
    def __init__(self, url: str, key: str) -> None:
        self.url, self.key = url, key
        self.backlog: deque[dict] = deque(maxlen=500)  # buffered while offline

    def _req(self, method: str, path: str, body=None):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(self.url + path, data=data, method=method,
                                     headers={"X-Device-Key": self.key, "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read() or b"null")

    def send(self, sample: dict) -> dict | None:
        sample = {**sample, "ts": time.time()}
        try:
            if self.backlog:
                self.backlog.append(sample)
                batch = list(self.backlog)
                self._req("POST", "/api/device/telemetry/batch", batch)
                self.backlog.clear()
                return None
            return self._req("POST", "/api/device/telemetry", sample)
        except (urllib.error.URLError, TimeoutError) as exc:
            if not self.backlog or self.backlog[-1] is not sample:
                self.backlog.append(sample)
            print(f"offline, buffered {len(self.backlog)} samples ({exc})")
            return None

    def poll_commands(self) -> list[dict]:
        try:
            return self._req("GET", "/api/device/commands")
        except (urllib.error.URLError, TimeoutError):
            return []

    def ack(self, command_id: int, status: str, result: dict | None = None) -> None:
        self._req("POST", f"/api/device/commands/{command_id}/ack", {"status": status, "result": result})


def read_sensors() -> dict:
    """Stub: replace with real sensor reads."""
    return {"temperature": round(random.gauss(26, 0.5), 2), "smoke": round(abs(random.gauss(15, 3)), 1),
            "gas": round(abs(random.gauss(50, 5)), 1), "humidity": round(random.gauss(47, 1), 1),
            "flame": False, "battery": 87.0, "water_level": 96.0, "motor_temp": 41.0, "x": 20.0, "y": 15.0}


def execute(cmd: dict) -> tuple[str, dict]:
    """Stub: dispatch to the motion / suppression controllers."""
    print(f"executing {cmd['kind']} {cmd['params']}")
    return "completed", {"note": "stub executor"}


def main() -> None:
    if not KEY:
        raise SystemExit("Set FIREOPS_DEVICE_KEY to the key shown when the robot was registered")
    dev = FireOpsDevice(URL, KEY)
    while True:
        res = dev.send(read_sensors())
        if res:
            print(f"risk={res['risk_score']:.3f} severity={res['severity']} status={res['status']}")
        for cmd in dev.poll_commands():
            status, result = execute(cmd)
            dev.ack(cmd["id"], status, result)
        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()
