"""Sites, robots, telemetry queries, commands, and the device-facing API."""
from __future__ import annotations

import csv
import io
import json
import time

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from .. import analytics
from ..db import audit, get_conn, now, row, rows
from ..deps import CurrentUser, current_robot, current_user, require
from ..security import new_device_key
from ..services import (EventBuffer, QuotaExceeded, command_public, ingest, plan_for, queue_command,
                        robot_public)

router = APIRouter(prefix="/api", tags=["fleet"])
device = APIRouter(prefix="/api/device", tags=["device"])

COMMAND_KINDS = {"move_to", "suppress", "return_to_base", "patrol", "halt", "scan"}


class SiteIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    width: float = Field(default=100, gt=0, le=10_000)
    height: float = Field(default=60, gt=0, le=10_000)


class RobotIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    model: str = Field(default="FFHR-1", max_length=50)
    site_id: int | None = None


class TelemetryIn(BaseModel):
    temperature: float | None = Field(default=None, ge=-50, le=1500)
    smoke: float | None = Field(default=None, ge=0, le=100_000)
    gas: float | None = Field(default=None, ge=0, le=100_000)
    humidity: float | None = Field(default=None, ge=0, le=100)
    flame: bool | int | None = None
    battery: float | None = Field(default=None, ge=0, le=100)
    water_level: float | None = Field(default=None, ge=0, le=100)
    motor_temp: float | None = Field(default=None, ge=-50, le=300)
    x: float | None = None
    y: float | None = None
    ts: float | None = None


class CommandIn(BaseModel):
    kind: str
    params: dict = Field(default_factory=dict)


class CommandAck(BaseModel):
    status: str = Field(pattern="^(completed|failed|in_progress)$")
    result: dict | None = None


def _get_robot(conn, org_id: int, robot_id: int) -> dict:
    r = row(conn.execute("SELECT * FROM robots WHERE id=? AND org_id=?", (robot_id, org_id)).fetchone())
    if not r:
        raise HTTPException(404, "Robot not found")
    return r


# ---------------------------------------------------------------- sites
@router.get("/sites")
def list_sites(user: CurrentUser = Depends(current_user)):
    with get_conn() as conn:
        return rows(conn.execute("SELECT * FROM sites WHERE org_id=? ORDER BY id", (user.org_id,)).fetchall())


@router.post("/sites", status_code=201)
def create_site(body: SiteIn, user: CurrentUser = Depends(require("admin"))):
    with get_conn() as conn:
        sid = conn.execute("INSERT INTO sites (org_id, name, width, height, created_at) VALUES (?,?,?,?,?)",
                           (user.org_id, body.name, body.width, body.height, now())).lastrowid
        audit(conn, user.org_id, user.id, "site.created", body.model_dump())
        return row(conn.execute("SELECT * FROM sites WHERE id=?", (sid,)).fetchone())


# ---------------------------------------------------------------- robots
@router.get("/robots")
def list_robots(user: CurrentUser = Depends(current_user)):
    with get_conn() as conn:
        rs = rows(conn.execute("SELECT * FROM robots WHERE org_id=? ORDER BY id", (user.org_id,)).fetchall())
    return [robot_public(r) for r in rs]


@router.post("/robots", status_code=201)
def create_robot(body: RobotIn, user: CurrentUser = Depends(require("admin"))):
    with get_conn() as conn:
        plan = plan_for(conn, user.org_id)
        count = conn.execute("SELECT COUNT(*) FROM robots WHERE org_id=?", (user.org_id,)).fetchone()[0]
        if count >= plan["max_robots"]:
            raise HTTPException(402, f"Plan '{plan['id']}' allows {plan['max_robots']} robots. Upgrade to add more.")
        if body.site_id is not None and not conn.execute(
                "SELECT 1 FROM sites WHERE id=? AND org_id=?", (body.site_id, user.org_id)).fetchone():
            raise HTTPException(404, "Site not found")
        site_id = body.site_id or (conn.execute("SELECT id FROM sites WHERE org_id=? ORDER BY id LIMIT 1",
                                                (user.org_id,)).fetchone() or [None])[0]
        key, key_hash, prefix = new_device_key()
        rid = conn.execute(
            "INSERT INTO robots (org_id, site_id, name, model, api_key_hash, api_key_prefix, created_at) "
            "VALUES (?,?,?,?,?,?,?)", (user.org_id, site_id, body.name, body.model, key_hash, prefix, now())).lastrowid
        audit(conn, user.org_id, user.id, "robot.created", {"robot_id": rid, "name": body.name})
        r = robot_public(row(conn.execute("SELECT * FROM robots WHERE id=?", (rid,)).fetchone()))
    r["api_key"] = key  # shown exactly once
    return r


@router.get("/robots/{robot_id}")
def get_robot(robot_id: int, user: CurrentUser = Depends(current_user)):
    with get_conn() as conn:
        r = robot_public(_get_robot(conn, user.org_id, robot_id))
        hist = rows(conn.execute(
            "SELECT ts, battery, motor_temp, water_level FROM telemetry WHERE robot_id=? ORDER BY ts DESC LIMIT 120",
            (robot_id,)).fetchall())[::-1]
    r["maintenance"] = analytics.maintenance_forecast(hist, time.time())
    if r.get("last_telemetry"):
        r["risk_explanation"] = analytics.explain_risk(r["last_telemetry"])
    return r


@router.post("/robots/{robot_id}/rotate-key")
def rotate_key(robot_id: int, user: CurrentUser = Depends(require("admin"))):
    with get_conn() as conn:
        _get_robot(conn, user.org_id, robot_id)
        key, key_hash, prefix = new_device_key()
        conn.execute("UPDATE robots SET api_key_hash=?, api_key_prefix=? WHERE id=?", (key_hash, prefix, robot_id))
        audit(conn, user.org_id, user.id, "robot.key_rotated", {"robot_id": robot_id})
    return {"api_key": key, "api_key_prefix": prefix}


@router.delete("/robots/{robot_id}")
def delete_robot(robot_id: int, user: CurrentUser = Depends(require("admin"))):
    with get_conn() as conn:
        r = _get_robot(conn, user.org_id, robot_id)
        conn.execute("DELETE FROM robots WHERE id=?", (robot_id,))
        audit(conn, user.org_id, user.id, "robot.deleted", {"robot_id": robot_id, "name": r["name"]})
    return {"ok": True}


@router.get("/robots/{robot_id}/telemetry")
def robot_telemetry(robot_id: int, minutes: float = Query(60, gt=0, le=60 * 24 * 30),
                    limit: int = Query(500, gt=0, le=5000), user: CurrentUser = Depends(current_user)):
    with get_conn() as conn:
        _get_robot(conn, user.org_id, robot_id)
        data = rows(conn.execute(
            "SELECT * FROM telemetry WHERE robot_id=? AND ts>=? ORDER BY ts DESC LIMIT ?",
            (robot_id, time.time() - minutes * 60, limit)).fetchall())
    return data[::-1]


@router.get("/telemetry/export.csv")
def export_csv(minutes: float = Query(60 * 24, gt=0, le=60 * 24 * 90), robot_id: int | None = None,
               user: CurrentUser = Depends(current_user)):
    sql = ("SELECT t.ts, r.name AS robot, t.temperature, t.smoke, t.gas, t.humidity, t.flame, t.battery, "
           "t.water_level, t.motor_temp, t.x, t.y, t.risk_score, t.severity FROM telemetry t "
           "JOIN robots r ON r.id=t.robot_id WHERE t.org_id=? AND t.ts>=?")
    params: list = [user.org_id, time.time() - minutes * 60]
    if robot_id is not None:
        sql += " AND t.robot_id=?"
        params.append(robot_id)
    with get_conn() as conn:
        data = conn.execute(sql + " ORDER BY t.ts", params).fetchall()
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["timestamp_utc", "robot", "temperature", "smoke", "gas", "humidity", "flame", "battery",
                "water_level", "motor_temp", "x", "y", "risk_score", "severity"])
    for d in data:
        w.writerow([time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(d["ts"])), *list(d)[1:]])
    buf.seek(0)
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=fireops-telemetry.csv"})


# ---------------------------------------------------------------- commands
@router.get("/commands")
def list_commands(robot_id: int | None = None, limit: int = Query(100, le=1000),
                  user: CurrentUser = Depends(current_user)):
    sql = ("SELECT c.*, r.name AS robot_name FROM commands c JOIN robots r ON r.id=c.robot_id "
           "WHERE c.org_id=?")
    params: list = [user.org_id]
    if robot_id is not None:
        sql += " AND c.robot_id=?"
        params.append(robot_id)
    with get_conn() as conn:
        data = rows(conn.execute(sql + " ORDER BY c.id DESC LIMIT ?", (*params, limit)).fetchall())
    return [command_public(c) for c in data]


@router.post("/robots/{robot_id}/commands", status_code=201)
def send_command(robot_id: int, body: CommandIn, user: CurrentUser = Depends(require("operator"))):
    if body.kind not in COMMAND_KINDS:
        raise HTTPException(422, f"Unknown command. Allowed: {sorted(COMMAND_KINDS)}")
    if body.kind == "move_to" and not {"x", "y"} <= body.params.keys():
        raise HTTPException(422, "move_to requires params.x and params.y")
    events = EventBuffer(user.org_id)
    with get_conn() as conn:
        _get_robot(conn, user.org_id, robot_id)
        cmd = queue_command(conn, events, user.org_id, robot_id, body.kind, body.params, user.id)
    events.flush()
    return cmd


@router.post("/robots/{robot_id}/telemetry", status_code=202)
def operator_telemetry(robot_id: int, body: TelemetryIn, user: CurrentUser = Depends(require("operator"))):
    """Manually inject a reading (e.g. from a handheld sensor) on behalf of a robot."""
    with get_conn() as conn:
        r = _get_robot(conn, user.org_id, robot_id)
    return _ingest(r, body)


# ---------------------------------------------------------------- device API
def _ingest(robot: dict, body: TelemetryIn) -> dict:
    payload = body.model_dump()
    ts = payload.pop("ts", None)
    if ts is not None and abs(ts - time.time()) > 3600:
        raise HTTPException(422, "ts must be within one hour of server time")
    try:
        with get_conn() as conn:
            result = ingest(conn, robot, payload, ts)
    except QuotaExceeded as exc:
        raise HTTPException(429, str(exc))
    result.pop("events").flush()
    return result


@device.post("/telemetry", status_code=202)
def device_telemetry(body: TelemetryIn, robot: dict = Depends(current_robot)):
    return _ingest(robot, body)


@device.post("/telemetry/batch", status_code=202)
def device_telemetry_batch(body: list[TelemetryIn], robot: dict = Depends(current_robot)):
    if len(body) > 500:
        raise HTTPException(413, "At most 500 samples per batch")
    results = [_ingest(robot, b) for b in sorted(body, key=lambda b: b.ts or 0)]
    return {"accepted": len(results), "max_risk": max((r["risk_score"] for r in results), default=0)}


@device.get("/commands")
def device_poll(robot: dict = Depends(current_robot)):
    """Robots poll for queued commands; returned commands are marked delivered."""
    with get_conn() as conn:
        cmds = rows(conn.execute("SELECT * FROM commands WHERE robot_id=? AND status='queued' ORDER BY id",
                                 (robot["id"],)).fetchall())
        if cmds:
            conn.execute(f"UPDATE commands SET status='delivered', delivered_at=? WHERE id IN "
                         f"({','.join('?' * len(cmds))})", (now(), *[c["id"] for c in cmds]))
    for c in cmds:
        c["status"] = "delivered"
    return [command_public(c) for c in cmds]


@device.post("/commands/{command_id}/ack")
def device_ack(command_id: int, body: CommandAck, robot: dict = Depends(current_robot)):
    events = EventBuffer(robot["org_id"])
    with get_conn() as conn:
        c = row(conn.execute("SELECT * FROM commands WHERE id=? AND robot_id=?",
                             (command_id, robot["id"])).fetchone())
        if not c:
            raise HTTPException(404, "Command not found")
        done = now() if body.status in ("completed", "failed") else None
        conn.execute("UPDATE commands SET status=?, result=?, completed_at=? WHERE id=?",
                     (body.status, json.dumps(body.result) if body.result is not None else None, done, command_id))
        c = command_public(row(conn.execute("SELECT * FROM commands WHERE id=?", (command_id,)).fetchone()))
    events.add("command", c)
    events.flush()
    return c


@device.get("/whoami")
def whoami(robot: dict = Depends(current_robot)):
    return {k: robot[k] for k in ("id", "org_id", "name", "model", "site_id")}
