from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Literal
import logging
import time
import random

app = FastAPI(title="FireBot Control API")

# Simulated sensor and robot status data
robot_status = {
    "temperature": 42,
    "flame_detected": True,
    "flame_confidence": 0.87,
    "gas_level": 320,
    "power_consumption": 24,
    "battery_status": 78,
    "location": "Building A, Floor 3",
    "ai_model_status": "Running",
    "ai_model_version": "v2.1.5",
    "system_uptime": "12:45:32",
    "movement_mode": "Auto",
    "speed": 50,
}

class MoveCommand(BaseModel):
    direction: Literal["forward", "backward", "left", "right", "stop"]
    speed: int  # 0-100

class ControlCommand(BaseModel):
    action: Literal["activate_extinguisher", "restart_ai", "reboot"]

@app.get("/sensor_data")
def get_sensor_data():
    # Simulate sensor data updates
    robot_status["temperature"] = random.randint(30, 50)
    robot_status["flame_confidence"] = round(random.uniform(0.7, 0.95), 2)
    robot_status["gas_level"] = random.randint(200, 400)
    robot_status["power_consumption"] = random.randint(20, 30)
    robot_status["battery_status"] = max(0, robot_status["battery_status"] - 1)
    # Simulate system uptime increment
    h, m, s = map(int, robot_status["system_uptime"].split(":"))
    s += 3
    if s >= 60:
        s -= 60
        m += 1
    if m >= 60:
        m -= 60
        h += 1
    robot_status["system_uptime"] = f"{h:02d}:{m:02d}:{s:02d}"
    return robot_status

@app.post("/move")
def move_robot(cmd: MoveCommand):
    logging.info(f"Received move command: {cmd.direction} at speed {cmd.speed}")
    # Here, integrate with actual robot control logic
    return {"message": f"Moving {cmd.direction} at speed {cmd.speed}%"}

@app.post("/control")
def control_robot(cmd: ControlCommand):
    logging.info(f"Received control command: {cmd.action}")
    # Here, integrate with actual control logic
    if cmd.action == "activate_extinguisher":
        # Simulate extinguisher activation
        return {"message": "Extinguisher activated"}
    elif cmd.action == "restart_ai":
        return {"message": "AI system restarting"}
    elif cmd.action == "reboot":
        return {"message": "System rebooting"}
    else:
        raise HTTPException(status_code=400, detail="Invalid control action")
