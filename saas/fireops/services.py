"""Core domain logic shared by the HTTP API and the built-in fleet simulator."""
from __future__ import annotations

import json
import sqlite3
import time
from typing import Any

from . import analytics
from .config import PLANS
from .db import audit, now, row, rows
from .notifier import emit
from .realtime import hub

OFFLINE_AFTER_SECONDS = 30
ANOMALY_EVENT_COOLDOWN = 60  # seconds between anomaly notifications per robot
_last_anomaly_event: dict[int, float] = {}
TELEMETRY_FIELDS = ["temperature", "smoke", "gas", "humidity", "flame", "battery",
                    "water_level", "motor_temp", "x", "y"]


class QuotaExceeded(Exception):
    pass


def period_key(ts: float | None = None) -> str:
    return time.strftime("%Y-%m", time.gmtime(ts or time.time()))


def plan_for(conn: sqlite3.Connection, org_id: int) -> dict:
    org = conn.execute("SELECT plan FROM orgs WHERE id=?", (org_id,)).fetchone()
    return {"id": org["plan"], **PLANS[org["plan"]]}


def robot_public(r: dict) -> dict:
    out = {k: v for k, v in r.items() if k != "api_key_hash"}
    if out.get("last_telemetry"):
        out["last_telemetry"] = json.loads(out["last_telemetry"])
    if not out.get("last_seen") or time.time() - out["last_seen"] > OFFLINE_AFTER_SECONDS:
        out["status"] = "offline"
    return out


class EventBuffer:
    """Collect realtime/webhook events during a transaction; flush after commit."""

    def __init__(self, org_id: int) -> None:
        self.org_id = org_id
        self.items: list[tuple[str, dict, bool]] = []

    def add(self, event: str, data: dict, webhook: bool = False) -> None:
        self.items.append((event, data, webhook))

    def flush(self) -> None:
        for event, data, webhook in self.items:
            hub.publish(self.org_id, event, data)
            if webhook:
                emit(self.org_id, event, data)
        self.items.clear()


def add_incident_event(conn, incident_id: int, kind: str, message: str, user_id: int | None = None) -> None:
    conn.execute("INSERT INTO incident_events (incident_id, ts, kind, message, user_id) VALUES (?,?,?,?,?)",
                 (incident_id, now(), kind, message, user_id))


def open_or_update_incident(conn, events: EventBuffer, org_id: int, robot: dict, severity: str,
                            title: str, source: str, risk: float, x, y, note: str) -> dict:
    existing = conn.execute(
        "SELECT * FROM incidents WHERE org_id=? AND robot_id=? AND status!='resolved' "
        "ORDER BY created_at DESC LIMIT 1", (org_id, robot["id"])).fetchone()
    if existing:
        inc = dict(existing)
        changed = False
        if analytics.SEVERITY_RANK[severity] > analytics.SEVERITY_RANK[inc["severity"]]:
            conn.execute("UPDATE incidents SET severity=?, title=? WHERE id=?", (severity, title, inc["id"]))
            add_incident_event(conn, inc["id"], "escalated", f"Escalated {inc['severity']} -> {severity}: {note}")
            inc.update(severity=severity, title=title)
            changed = True
        if risk > inc["peak_risk"]:
            conn.execute("UPDATE incidents SET peak_risk=?, x=?, y=? WHERE id=?", (risk, x, y, inc["id"]))
            inc.update(peak_risk=risk, x=x, y=y)
        if changed:
            events.add("incident.escalated", inc, webhook=True)
        return inc
    cur = conn.execute(
        "INSERT INTO incidents (org_id, robot_id, title, severity, status, source, peak_risk, x, y, created_at) "
        "VALUES (?,?,?,?, 'open', ?,?,?,?,?)",
        (org_id, robot["id"], title, severity, source, risk, x, y, now()))
    add_incident_event(conn, cur.lastrowid, "opened", note)
    inc = row(conn.execute("SELECT * FROM incidents WHERE id=?", (cur.lastrowid,)).fetchone())
    inc["robot_name"] = robot["name"]
    events.add("incident.opened", inc, webhook=True)
    return inc


def ingest(conn: sqlite3.Connection, robot: dict, payload: dict[str, Any], ts: float | None = None) -> dict:
    """Store one telemetry sample and run the full analytics/incident pipeline.

    Returns a summary with the computed risk and an EventBuffer the caller must
    flush once the transaction is committed.
    """
    org_id = robot["org_id"]
    ts = ts or now()
    events = EventBuffer(org_id)

    plan = plan_for(conn, org_id)
    period = period_key(ts)
    conn.execute("INSERT INTO usage (org_id, period, telemetry_count) VALUES (?,?,0) "
                 "ON CONFLICT(org_id, period) DO NOTHING", (org_id, period))
    used = conn.execute("SELECT telemetry_count FROM usage WHERE org_id=? AND period=?",
                        (org_id, period)).fetchone()[0]
    if used >= plan["telemetry_per_month"]:
        raise QuotaExceeded(f"Monthly telemetry quota of {plan['telemetry_per_month']} reached for plan {plan['id']}")
    conn.execute("UPDATE usage SET telemetry_count = telemetry_count + 1 WHERE org_id=? AND period=?",
                 (org_id, period))

    t = {k: payload.get(k) for k in TELEMETRY_FIELDS}
    t["flame"] = 1 if t.get("flame") else 0
    score = analytics.risk_score(t)
    severity = analytics.severity_for(score)
    t["risk_score"] = score

    history = rows(conn.execute(
        "SELECT ts, temperature, smoke, gas, motor_temp, battery, water_level FROM telemetry "
        "WHERE robot_id=? ORDER BY ts DESC LIMIT 60", (robot["id"],)).fetchall())[::-1]

    conn.execute(
        "INSERT INTO telemetry (org_id, robot_id, ts, temperature, smoke, gas, humidity, flame, battery, "
        "water_level, motor_temp, x, y, risk_score, severity) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (org_id, robot["id"], ts, t["temperature"], t["smoke"], t["gas"], t["humidity"], t["flame"],
         t["battery"], t["water_level"], t["motor_temp"], t["x"], t["y"], score, severity))

    has_open = conn.execute("SELECT 1 FROM incidents WHERE robot_id=? AND status!='resolved' LIMIT 1",
                            (robot["id"],)).fetchone() is not None
    status = "online"
    if t["battery"] is not None and t["battery"] < 15:
        status = "low_battery"
    if severity in ("high", "critical") or (has_open and t["flame"]):
        status = "engaged"
    conn.execute("UPDATE robots SET last_seen=?, last_telemetry=?, risk_score=?, status=? WHERE id=?",
                 (ts, json.dumps(t), score, status, robot["id"]))

    incident = None
    if severity in ("high", "critical"):
        top = analytics.explain_risk(t)[0]["feature"]
        incident = open_or_update_incident(
            conn, events, org_id, robot, severity,
            f"{severity.title()} fire risk detected by {robot['name']}", "risk_model", score,
            t["x"], t["y"], f"Risk {score:.2f} (driver: {top}, temp {t['temperature']}C, smoke {t['smoke']}ppm)")

    rules = rows(conn.execute("SELECT * FROM alert_rules WHERE org_id=? AND enabled=1", (org_id,)).fetchall())
    for rule in analytics.evaluate_rules(rules, t):
        incident = open_or_update_incident(
            conn, events, org_id, robot, rule["severity"], f"Rule '{rule['name']}' triggered on {robot['name']}",
            "alert_rule", score, t["x"], t["y"],
            f"{rule['metric']} {rule['op']} {rule['threshold']} (value {t[rule['metric']]})")

    anomalies = analytics.zscore_anomalies(history, t)
    if anomalies:
        desc = ", ".join(f"{a['metric']}={a['value']} (baseline {a['baseline']}, z={a['z']})" for a in anomalies)
        if incident is None and not has_open:
            incident = open_or_update_incident(
                conn, events, org_id, robot, "medium", f"Sensor anomaly on {robot['name']}", "anomaly",
                score, t["x"], t["y"], desc)
        if ts - _last_anomaly_event.get(robot["id"], 0) >= ANOMALY_EVENT_COOLDOWN:
            _last_anomaly_event[robot["id"]] = ts
            events.add("anomaly", {"robot_id": robot["id"], "robot_name": robot["name"], "anomalies": anomalies})

    events.add("telemetry", {"robot_id": robot["id"], "robot_name": robot["name"], "ts": ts,
                             "status": status, **t, "severity": severity})
    return {"risk_score": score, "severity": severity, "status": status, "anomalies": anomalies,
            "incident_id": incident["id"] if incident else None, "events": events}


def queue_command(conn, events: EventBuffer, org_id: int, robot_id: int, kind: str, params: dict,
                  user_id: int | None) -> dict:
    cur = conn.execute(
        "INSERT INTO commands (org_id, robot_id, kind, params, status, issued_by, created_at) "
        "VALUES (?,?,?,?, 'queued', ?, ?)", (org_id, robot_id, kind, json.dumps(params), user_id, now()))
    cmd = command_public(row(conn.execute("SELECT * FROM commands WHERE id=?", (cur.lastrowid,)).fetchone()))
    audit(conn, org_id, user_id, "command.queued", {"robot_id": robot_id, "kind": kind, "params": params})
    events.add("command", cmd)
    return cmd


def command_public(c: dict) -> dict:
    c = dict(c)
    c["params"] = json.loads(c["params"] or "{}")
    if c.get("result"):
        try:
            c["result"] = json.loads(c["result"])
        except ValueError:
            pass
    return c
