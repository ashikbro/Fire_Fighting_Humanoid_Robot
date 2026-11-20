"""Incidents, alert rules, analytics, webhooks, billing, audit log and demo mode."""
from __future__ import annotations

import secrets
import time
from collections import Counter

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from .. import analytics
from ..config import PLANS
from ..db import audit, get_conn, now, row, rows
from ..deps import CurrentUser, current_user, require
from ..notifier import deliver, emit
from ..realtime import hub
from ..services import EventBuffer, add_incident_event, plan_for, queue_command, robot_public

router = APIRouter(prefix="/api", tags=["operations"])


class IncidentIn(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    severity: str = Field(pattern="^(low|medium|high|critical)$")
    robot_id: int | None = None
    x: float | None = None
    y: float | None = None


class IncidentPatch(BaseModel):
    status: str | None = Field(default=None, pattern="^(open|acknowledged|resolved)$")
    severity: str | None = Field(default=None, pattern="^(low|medium|high|critical)$")
    assignee_id: int | None = None
    note: str | None = Field(default=None, max_length=2000)


class DispatchIn(BaseModel):
    robot_ids: list[int] | None = None
    count: int = Field(default=2, ge=1, le=20)


class RuleIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    metric: str
    op: str = Field(pattern="^(>|>=|<|<=|==)$")
    threshold: float
    severity: str = Field(pattern="^(low|medium|high|critical)$")
    enabled: bool = True


class WebhookIn(BaseModel):
    url: str = Field(pattern=r"^https?://", max_length=500)
    events: str = "*"


class PlanIn(BaseModel):
    plan: str


class SimIn(BaseModel):
    enabled: bool


# ---------------------------------------------------------------- incidents
def _incident(conn, org_id: int, incident_id: int) -> dict:
    inc = row(conn.execute("SELECT i.*, r.name AS robot_name, u.name AS assignee_name FROM incidents i "
                           "LEFT JOIN robots r ON r.id=i.robot_id LEFT JOIN users u ON u.id=i.assignee_id "
                           "WHERE i.id=? AND i.org_id=?", (incident_id, org_id)).fetchone())
    if not inc:
        raise HTTPException(404, "Incident not found")
    return inc


@router.get("/incidents")
def list_incidents(status: str | None = Query(None, pattern="^(open|acknowledged|resolved|active)$"),
                   limit: int = Query(100, le=1000), user: CurrentUser = Depends(current_user)):
    sql = ("SELECT i.*, r.name AS robot_name, u.name AS assignee_name FROM incidents i "
           "LEFT JOIN robots r ON r.id=i.robot_id LEFT JOIN users u ON u.id=i.assignee_id WHERE i.org_id=?")
    params: list = [user.org_id]
    if status == "active":
        sql += " AND i.status!='resolved'"
    elif status:
        sql += " AND i.status=?"
        params.append(status)
    with get_conn() as conn:
        return rows(conn.execute(sql + " ORDER BY i.created_at DESC LIMIT ?", (*params, limit)).fetchall())


@router.post("/incidents", status_code=201)
def create_incident(body: IncidentIn, user: CurrentUser = Depends(require("operator"))):
    events = EventBuffer(user.org_id)
    with get_conn() as conn:
        if body.robot_id is not None and not conn.execute(
                "SELECT 1 FROM robots WHERE id=? AND org_id=?", (body.robot_id, user.org_id)).fetchone():
            raise HTTPException(404, "Robot not found")
        iid = conn.execute(
            "INSERT INTO incidents (org_id, robot_id, title, severity, status, source, x, y, created_at) "
            "VALUES (?,?,?,?, 'open', 'manual', ?,?,?)",
            (user.org_id, body.robot_id, body.title, body.severity, body.x, body.y, now())).lastrowid
        add_incident_event(conn, iid, "opened", f"Reported manually by {user.name}", user.id)
        audit(conn, user.org_id, user.id, "incident.created", {"incident_id": iid})
        inc = _incident(conn, user.org_id, iid)
    events.add("incident.opened", inc, webhook=True)
    events.flush()
    return inc


@router.get("/incidents/{incident_id}")
def get_incident(incident_id: int, user: CurrentUser = Depends(current_user)):
    with get_conn() as conn:
        inc = _incident(conn, user.org_id, incident_id)
        inc["timeline"] = rows(conn.execute(
            "SELECT e.*, u.name AS user_name FROM incident_events e LEFT JOIN users u ON u.id=e.user_id "
            "WHERE incident_id=? ORDER BY ts", (incident_id,)).fetchall())
    return inc


@router.patch("/incidents/{incident_id}")
def update_incident(incident_id: int, body: IncidentPatch, user: CurrentUser = Depends(require("operator"))):
    events = EventBuffer(user.org_id)
    with get_conn() as conn:
        inc = _incident(conn, user.org_id, incident_id)
        if body.status and body.status != inc["status"]:
            ts = now()
            if body.status == "acknowledged":
                conn.execute("UPDATE incidents SET status=?, acknowledged_at=COALESCE(acknowledged_at, ?) "
                             "WHERE id=?", (body.status, ts, incident_id))
            elif body.status == "resolved":
                conn.execute("UPDATE incidents SET status=?, acknowledged_at=COALESCE(acknowledged_at, ?), "
                             "resolved_at=? WHERE id=?", (body.status, ts, ts, incident_id))
            else:
                conn.execute("UPDATE incidents SET status='open', resolved_at=NULL WHERE id=?", (incident_id,))
            add_incident_event(conn, incident_id, body.status, f"{user.name} marked incident {body.status}", user.id)
        if body.severity and body.severity != inc["severity"]:
            conn.execute("UPDATE incidents SET severity=? WHERE id=?", (body.severity, incident_id))
            add_incident_event(conn, incident_id, "severity",
                               f"{user.name} changed severity {inc['severity']} -> {body.severity}", user.id)
        if body.assignee_id is not None:
            a = conn.execute("SELECT name FROM users WHERE id=? AND org_id=?",
                             (body.assignee_id, user.org_id)).fetchone()
            if not a:
                raise HTTPException(404, "Assignee not found")
            conn.execute("UPDATE incidents SET assignee_id=? WHERE id=?", (body.assignee_id, incident_id))
            add_incident_event(conn, incident_id, "assigned", f"Assigned to {a['name']}", user.id)
        if body.note:
            add_incident_event(conn, incident_id, "note", body.note, user.id)
        audit(conn, user.org_id, user.id, "incident.updated",
              {"incident_id": incident_id, **body.model_dump(exclude_none=True)})
        inc = _incident(conn, user.org_id, incident_id)
    events.add("incident.updated", inc, webhook=body.status is not None)
    events.flush()
    return inc


@router.post("/incidents/{incident_id}/dispatch")
def dispatch(incident_id: int, body: DispatchIn, user: CurrentUser = Depends(require("operator"))):
    """Send the nearest available robots to an incident and order suppression on arrival."""
    events = EventBuffer(user.org_id)
    with get_conn() as conn:
        inc = _incident(conn, user.org_id, incident_id)
        if inc["x"] is None or inc["y"] is None:
            raise HTTPException(422, "Incident has no location")
        robots = [robot_public(r) for r in rows(conn.execute(
            "SELECT * FROM robots WHERE org_id=?", (user.org_id,)).fetchall())]
        if body.robot_ids:
            chosen = [r for r in robots if r["id"] in set(body.robot_ids)]
        else:
            def score(r):
                t = r.get("last_telemetry") or {}
                if r["status"] == "offline" or t.get("x") is None:
                    return None
                dist = ((t["x"] - inc["x"]) ** 2 + (t["y"] - inc["y"]) ** 2) ** 0.5
                # Prefer close robots with charge and water.
                penalty = max(0, 30 - (t.get("battery") or 0)) * 2 + max(0, 30 - (t.get("water_level") or 0)) * 2
                return dist + penalty
            ranked = sorted(((score(r), r) for r in robots if score(r) is not None), key=lambda p: p[0])
            chosen = [r for _, r in ranked[: body.count]]
        if not chosen:
            raise HTTPException(409, "No available robots to dispatch")
        cmds = []
        for r in chosen:
            cmds.append(queue_command(conn, events, user.org_id, r["id"], "move_to",
                                      {"x": inc["x"], "y": inc["y"], "incident_id": incident_id}, user.id))
            cmds.append(queue_command(conn, events, user.org_id, r["id"], "suppress",
                                      {"incident_id": incident_id, "agent": "water"}, user.id))
        names = ", ".join(r["name"] for r in chosen)
        add_incident_event(conn, incident_id, "dispatched", f"{user.name} dispatched {names}", user.id)
        if inc["status"] == "open":
            conn.execute("UPDATE incidents SET status='acknowledged', acknowledged_at=? WHERE id=?",
                         (now(), incident_id))
    events.add("incident.updated", {"id": incident_id})
    events.flush()
    return {"dispatched": [r["id"] for r in chosen], "commands": cmds}


# ---------------------------------------------------------------- alert rules
@router.get("/rules")
def list_rules(user: CurrentUser = Depends(current_user)):
    with get_conn() as conn:
        return rows(conn.execute("SELECT * FROM alert_rules WHERE org_id=? ORDER BY id", (user.org_id,)).fetchall())


@router.post("/rules", status_code=201)
def create_rule(body: RuleIn, user: CurrentUser = Depends(require("admin"))):
    if body.metric not in analytics.METRICS:
        raise HTTPException(422, f"metric must be one of {analytics.METRICS}")
    with get_conn() as conn:
        rid = conn.execute("INSERT INTO alert_rules (org_id, name, metric, op, threshold, severity, enabled, "
                           "created_at) VALUES (?,?,?,?,?,?,?,?)",
                           (user.org_id, body.name, body.metric, body.op, body.threshold, body.severity,
                            int(body.enabled), now())).lastrowid
        audit(conn, user.org_id, user.id, "rule.created", body.model_dump())
        return row(conn.execute("SELECT * FROM alert_rules WHERE id=?", (rid,)).fetchone())


@router.put("/rules/{rule_id}")
def update_rule(rule_id: int, body: RuleIn, user: CurrentUser = Depends(require("admin"))):
    if body.metric not in analytics.METRICS:
        raise HTTPException(422, f"metric must be one of {analytics.METRICS}")
    with get_conn() as conn:
        cur = conn.execute("UPDATE alert_rules SET name=?, metric=?, op=?, threshold=?, severity=?, enabled=? "
                           "WHERE id=? AND org_id=?", (body.name, body.metric, body.op, body.threshold,
                                                       body.severity, int(body.enabled), rule_id, user.org_id))
        if cur.rowcount == 0:
            raise HTTPException(404, "Rule not found")
        audit(conn, user.org_id, user.id, "rule.updated", {"rule_id": rule_id, **body.model_dump()})
        return row(conn.execute("SELECT * FROM alert_rules WHERE id=?", (rule_id,)).fetchone())


@router.delete("/rules/{rule_id}")
def delete_rule(rule_id: int, user: CurrentUser = Depends(require("admin"))):
    with get_conn() as conn:
        if conn.execute("DELETE FROM alert_rules WHERE id=? AND org_id=?", (rule_id, user.org_id)).rowcount == 0:
            raise HTTPException(404, "Rule not found")
        audit(conn, user.org_id, user.id, "rule.deleted", {"rule_id": rule_id})
    return {"ok": True}


# ---------------------------------------------------------------- analytics
@router.get("/analytics/overview")
def overview(hours: float = Query(24, gt=0, le=24 * 90), user: CurrentUser = Depends(current_user)):
    since = time.time() - hours * 3600
    with get_conn() as conn:
        robots = [robot_public(r) for r in rows(conn.execute(
            "SELECT * FROM robots WHERE org_id=?", (user.org_id,)).fetchall())]
        incs = rows(conn.execute("SELECT * FROM incidents WHERE org_id=? AND created_at>=?",
                                 (user.org_id, since)).fetchall())
        active = conn.execute("SELECT severity, COUNT(*) c FROM incidents WHERE org_id=? AND status!='resolved' "
                              "GROUP BY severity", (user.org_id,)).fetchall()
        bucket = max(60, int(hours * 3600 / 48))
        series = rows(conn.execute(
            "SELECT CAST(ts / ? AS INTEGER) * ? AS bucket, AVG(risk_score) avg_risk, MAX(risk_score) max_risk, "
            "AVG(temperature) avg_temp, COUNT(*) samples FROM telemetry WHERE org_id=? AND ts>=? "
            "GROUP BY bucket ORDER BY bucket", (bucket, bucket, user.org_id, since)).fetchall())
        samples = conn.execute("SELECT COUNT(*) FROM telemetry WHERE org_id=? AND ts>=?",
                               (user.org_id, since)).fetchone()[0]
        usage = conn.execute("SELECT telemetry_count FROM usage WHERE org_id=? AND period=?",
                             (user.org_id, time.strftime("%Y-%m", time.gmtime()))).fetchone()
        plan = plan_for(conn, user.org_id)
    mtta = [i["acknowledged_at"] - i["created_at"] for i in incs if i["acknowledged_at"]]
    mttr = [i["resolved_at"] - i["created_at"] for i in incs if i["resolved_at"]]
    status_counts = Counter(r["status"] for r in robots)
    online = [r for r in robots if r["status"] != "offline"]
    return {
        "robots": {"total": len(robots), "by_status": dict(status_counts),
                   "avg_battery": round(sum((r["last_telemetry"] or {}).get("battery") or 0 for r in online)
                                        / len(online), 1) if online else None,
                   "max_risk": max((r["risk_score"] for r in online), default=0)},
        "incidents": {"created": len(incs), "active_by_severity": {a["severity"]: a["c"] for a in active},
                      "by_source": dict(Counter(i["source"] for i in incs)),
                      "mtta_seconds": round(sum(mtta) / len(mtta), 1) if mtta else None,
                      "mttr_seconds": round(sum(mttr) / len(mttr), 1) if mttr else None,
                      "p90_mttr_seconds": round(analytics.percentile(mttr, 0.9), 1) if mttr else None},
        "telemetry": {"samples": samples, "series": series, "bucket_seconds": bucket},
        "usage": {"period_count": usage[0] if usage else 0, "quota": plan["telemetry_per_month"]},
        "live_clients": hub.client_count(user.org_id),
    }


@router.get("/analytics/heatmap")
def heatmap(hours: float = Query(24, gt=0, le=24 * 90), cell: float = Query(5, gt=0, le=100),
            user: CurrentUser = Depends(current_user)):
    """Peak fire risk per spatial grid cell, for hotspot maps."""
    with get_conn() as conn:
        cells = rows(conn.execute(
            "SELECT CAST(x / ? AS INTEGER) cx, CAST(y / ? AS INTEGER) cy, MAX(risk_score) risk, COUNT(*) n "
            "FROM telemetry WHERE org_id=? AND ts>=? AND x IS NOT NULL AND y IS NOT NULL GROUP BY cx, cy",
            (cell, cell, user.org_id, time.time() - hours * 3600)).fetchall())
    return {"cell": cell, "cells": cells}


@router.post("/analytics/predict")
def predict(body: dict, user: CurrentUser = Depends(current_user)):
    """What-if tool: score arbitrary sensor values without storing them."""
    score = analytics.risk_score(body)
    return {"risk_score": score, "severity": analytics.severity_for(score),
            "explanation": analytics.explain_risk(body)}


# ---------------------------------------------------------------- webhooks
@router.get("/webhooks")
def list_webhooks(user: CurrentUser = Depends(require("admin"))):
    with get_conn() as conn:
        return rows(conn.execute("SELECT * FROM webhooks WHERE org_id=? ORDER BY id", (user.org_id,)).fetchall())


@router.post("/webhooks", status_code=201)
def create_webhook(body: WebhookIn, user: CurrentUser = Depends(require("admin"))):
    with get_conn() as conn:
        if not plan_for(conn, user.org_id)["webhooks"]:
            raise HTTPException(402, "Webhooks require the Pro plan or higher")
        wid = conn.execute("INSERT INTO webhooks (org_id, url, secret, events, created_at) VALUES (?,?,?,?,?)",
                           (user.org_id, body.url, "whsec_" + secrets.token_urlsafe(24), body.events,
                            now())).lastrowid
        audit(conn, user.org_id, user.id, "webhook.created", {"url": body.url})
        return row(conn.execute("SELECT * FROM webhooks WHERE id=?", (wid,)).fetchone())


@router.post("/webhooks/{webhook_id}/test")
def test_webhook(webhook_id: int, user: CurrentUser = Depends(require("admin"))):
    with get_conn() as conn:
        h = row(conn.execute("SELECT * FROM webhooks WHERE id=? AND org_id=?",
                             (webhook_id, user.org_id)).fetchone())
    if not h:
        raise HTTPException(404, "Webhook not found")
    status = deliver(h["url"], h["secret"], "ping", {"message": "FireOps test delivery"})
    with get_conn() as conn:
        conn.execute("UPDATE webhooks SET last_status=? WHERE id=?", (status, webhook_id))
    return {"status": status}


@router.delete("/webhooks/{webhook_id}")
def delete_webhook(webhook_id: int, user: CurrentUser = Depends(require("admin"))):
    with get_conn() as conn:
        if conn.execute("DELETE FROM webhooks WHERE id=? AND org_id=?", (webhook_id, user.org_id)).rowcount == 0:
            raise HTTPException(404, "Webhook not found")
        audit(conn, user.org_id, user.id, "webhook.deleted", {"webhook_id": webhook_id})
    return {"ok": True}


# ---------------------------------------------------------------- billing / org
@router.get("/billing/plans")
def plans():
    return [{"id": k, **v} for k, v in PLANS.items()]


@router.post("/billing/plan")
def change_plan(body: PlanIn, user: CurrentUser = Depends(require("admin"))):
    """Switch plan. Wire this to a payment provider's checkout in production."""
    if body.plan not in PLANS:
        raise HTTPException(422, "Unknown plan")
    with get_conn() as conn:
        n = conn.execute("SELECT COUNT(*) FROM robots WHERE org_id=?", (user.org_id,)).fetchone()[0]
        if n > PLANS[body.plan]["max_robots"]:
            raise HTTPException(409, f"Remove robots first: {n} registered, plan allows {PLANS[body.plan]['max_robots']}")
        conn.execute("UPDATE orgs SET plan=? WHERE id=?", (body.plan, user.org_id))
        audit(conn, user.org_id, user.id, "billing.plan_changed", {"plan": body.plan})
        emit(user.org_id, "billing.plan_changed", {"plan": body.plan})
        return plan_for(conn, user.org_id)


@router.post("/org/simulator")
def toggle_simulator(body: SimIn, user: CurrentUser = Depends(require("admin"))):
    with get_conn() as conn:
        conn.execute("UPDATE orgs SET simulator_enabled=? WHERE id=?", (int(body.enabled), user.org_id))
        audit(conn, user.org_id, user.id, "simulator.toggled", {"enabled": body.enabled})
    return {"enabled": body.enabled}


@router.get("/audit")
def audit_log(limit: int = Query(200, le=2000), user: CurrentUser = Depends(require("admin"))):
    with get_conn() as conn:
        return rows(conn.execute("SELECT a.*, u.name AS user_name FROM audit_log a LEFT JOIN users u "
                                 "ON u.id=a.user_id WHERE a.org_id=? ORDER BY a.id DESC LIMIT ?",
                                 (user.org_id, limit)).fetchall())
