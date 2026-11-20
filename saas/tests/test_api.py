from tests.conftest import CALM, FIRE, make_robot, signup


def dev(key):
    return {"X-Device-Key": key}


def test_signup_login_and_me(client):
    h = signup(client)
    me = client.get("/api/auth/me", headers=h).json()
    assert me["user"]["role"] == "admin" and me["plan"]["id"] == "free"
    assert client.post("/api/auth/login", json={"email": "admin@acme.io", "password": "wrong-pass"}).status_code == 401
    assert client.post("/api/auth/login", json={"email": "ADMIN@acme.io", "password": "supersecret"}).status_code == 200
    assert client.post("/api/auth/signup", json={"org_name": "Other", "name": "Y", "email": "admin@acme.io",
                                                 "password": "supersecret"}).status_code == 409
    assert client.get("/api/robots").status_code == 401
    # default alert rules are provisioned
    assert len(client.get("/api/rules", headers=h).json()) == 3


def test_tenant_isolation(client):
    a = signup(client, "a@a.io", "Org A")
    b = signup(client, "b@b.io", "Org B")
    robot = make_robot(client, a)
    assert client.get(f"/api/robots/{robot['id']}", headers=b).status_code == 404
    assert client.get("/api/robots", headers=b).json() == []
    client.post("/api/device/telemetry", json=FIRE, headers=dev(robot["api_key"]))
    assert client.get("/api/incidents", headers=b).json() == []
    assert len(client.get("/api/incidents", headers=a).json()) == 1


def test_device_key_auth_and_rotation(client):
    h = signup(client)
    robot = make_robot(client, h)
    assert "api_key" not in client.get(f"/api/robots/{robot['id']}", headers=h).json()
    assert client.post("/api/device/telemetry", json=CALM, headers=dev("fod_bogus")).status_code == 401
    assert client.post("/api/device/telemetry", json=CALM, headers=dev(robot["api_key"])).status_code == 202
    new = client.post(f"/api/robots/{robot['id']}/rotate-key", headers=h).json()["api_key"]
    assert client.post("/api/device/telemetry", json=CALM, headers=dev(robot["api_key"])).status_code == 401
    assert client.get("/api/device/whoami", headers=dev(new)).json()["id"] == robot["id"]


def test_fire_creates_single_incident_and_escalates(client):
    h = signup(client)
    robot = make_robot(client, h)
    key = robot["api_key"]
    r = client.post("/api/device/telemetry", json=CALM, headers=dev(key)).json()
    assert r["severity"] == "low" and r["incident_id"] is None
    high = {**FIRE, "temperature": 60, "smoke": 150, "gas": 100, "flame": False, "humidity": 40}
    r1 = client.post("/api/device/telemetry", json=high, headers=dev(key)).json()
    assert r1["severity"] in ("medium", "high")
    r2 = client.post("/api/device/telemetry", json=FIRE, headers=dev(key)).json()
    assert r2["severity"] == "critical" and r2["status"] == "engaged"
    r3 = client.post("/api/device/telemetry", json=FIRE, headers=dev(key)).json()
    assert r3["incident_id"] == r2["incident_id"]  # deduplicated
    incs = client.get("/api/incidents?status=active", headers=h).json()
    assert len(incs) == 1 and incs[0]["severity"] == "critical"
    detail = client.get(f"/api/incidents/{incs[0]['id']}", headers=h).json()
    assert detail["timeline"][0]["kind"] == "opened"


def test_incident_lifecycle_and_metrics(client):
    h = signup(client)
    robot = make_robot(client, h)
    iid = client.post("/api/device/telemetry", json=FIRE, headers=dev(robot["api_key"])).json()["incident_id"]
    me = client.get("/api/auth/me", headers=h).json()["user"]
    client.patch(f"/api/incidents/{iid}", json={"status": "acknowledged", "assignee_id": me["id"],
                                                "note": "crew en route"}, headers=h)
    inc = client.patch(f"/api/incidents/{iid}", json={"status": "resolved"}, headers=h).json()
    assert inc["status"] == "resolved" and inc["assignee_name"] == "Admin"
    kinds = [e["kind"] for e in client.get(f"/api/incidents/{iid}", headers=h).json()["timeline"]]
    assert kinds == ["opened", "acknowledged", "assigned", "note", "resolved"]
    ov = client.get("/api/analytics/overview", headers=h).json()
    assert ov["incidents"]["mttr_seconds"] is not None and ov["telemetry"]["samples"] == 1


def test_custom_rule_triggers_incident(client):
    h = signup(client)
    robot = make_robot(client, h)
    r = client.post("/api/rules", json={"name": "Low battery", "metric": "battery", "op": "<", "threshold": 20,
                                        "severity": "medium"}, headers=h)
    assert r.status_code == 201
    assert client.post("/api/rules", json={"name": "x", "metric": "nope", "op": "<", "threshold": 1,
                                           "severity": "low"}, headers=h).status_code == 422
    res = client.post("/api/device/telemetry", json={**CALM, "battery": 8}, headers=dev(robot["api_key"])).json()
    assert res["incident_id"] is not None and res["status"] == "low_battery"
    inc = client.get(f"/api/incidents/{res['incident_id']}", headers=h).json()
    assert inc["source"] == "alert_rule"


def test_commands_roundtrip_and_dispatch(client):
    h = signup(client)
    r1, r2 = make_robot(client, h, "Near"), make_robot(client, h, "Far")
    client.post("/api/device/telemetry", json={**CALM, "x": 28, "y": 20}, headers=dev(r1["api_key"]))
    client.post("/api/device/telemetry", json={**CALM, "x": 90, "y": 55}, headers=dev(r2["api_key"]))
    iid = client.post("/api/incidents", json={"title": "Warehouse smoke", "severity": "high", "x": 30, "y": 20},
                      headers=h).json()["id"]
    d = client.post(f"/api/incidents/{iid}/dispatch", json={"count": 1}, headers=h).json()
    assert d["dispatched"] == [r1["id"]]
    cmds = client.get("/api/device/commands", headers=dev(r1["api_key"])).json()
    assert [c["kind"] for c in cmds] == ["move_to", "suppress"] and cmds[0]["params"]["x"] == 30
    assert client.get("/api/device/commands", headers=dev(r1["api_key"])).json() == []  # delivered once
    ack = client.post(f"/api/device/commands/{cmds[0]['id']}/ack", json={"status": "completed", "result": {"ok": 1}},
                      headers=dev(r1["api_key"])).json()
    assert ack["status"] == "completed" and ack["result"] == {"ok": 1}
    # another robot cannot ack someone else's command
    assert client.post(f"/api/device/commands/{cmds[1]['id']}/ack", json={"status": "completed"},
                       headers=dev(r2["api_key"])).status_code == 404
    assert client.get(f"/api/incidents/{iid}", headers=h).json()["status"] == "acknowledged"
    assert client.post(f"/api/robots/{r1['id']}/commands", json={"kind": "self_destruct"},
                       headers=h).status_code == 422


def test_rbac(client):
    h = signup(client)
    for role in ("viewer", "operator"):
        client.post("/api/team", json={"name": role, "email": f"{role}@acme.io", "password": "password123",
                                       "role": role}, headers=h)
    tok = {r: {"Authorization": "Bearer " + client.post("/api/auth/login", json={
        "email": f"{r}@acme.io", "password": "password123"}).json()["access_token"]} for r in ("viewer", "operator")}
    robot = make_robot(client, h)
    assert client.post("/api/robots", json={"name": "x"}, headers=tok["operator"]).status_code == 403
    assert client.post(f"/api/robots/{robot['id']}/commands", json={"kind": "halt"},
                       headers=tok["viewer"]).status_code == 403
    assert client.post(f"/api/robots/{robot['id']}/commands", json={"kind": "halt"},
                       headers=tok["operator"]).status_code == 201
    assert client.get("/api/audit", headers=tok["operator"]).status_code == 403
    actions = [a["action"] for a in client.get("/api/audit", headers=h).json()]
    assert "command.queued" in actions and "user.invited" in actions


def test_plan_limits_and_upgrade(client):
    h = signup(client)
    for i in range(3):
        make_robot(client, h, f"R{i}")
    assert client.post("/api/robots", json={"name": "R4"}, headers=h).status_code == 402
    assert client.post("/api/webhooks", json={"url": "https://example.com/h"}, headers=h).status_code == 402
    assert client.post("/api/billing/plan", json={"plan": "pro"}, headers=h).json()["id"] == "pro"
    assert client.post("/api/robots", json={"name": "R4"}, headers=h).status_code == 201
    assert client.post("/api/webhooks", json={"url": "https://example.com/h"}, headers=h).status_code == 201
    assert client.post("/api/billing/plan", json={"plan": "free"}, headers=h).status_code == 409


def test_telemetry_quota(client, monkeypatch):
    from fireops import config
    monkeypatch.setitem(config.PLANS["free"], "telemetry_per_month", 2)
    h = signup(client)
    key = make_robot(client, h)["api_key"]
    assert client.post("/api/device/telemetry", json=CALM, headers=dev(key)).status_code == 202
    assert client.post("/api/device/telemetry", json=CALM, headers=dev(key)).status_code == 202
    assert client.post("/api/device/telemetry", json=CALM, headers=dev(key)).status_code == 429


def test_batch_csv_heatmap_and_predict(client):
    h = signup(client)
    robot = make_robot(client, h)
    import time
    now = time.time()
    batch = [{**CALM, "ts": now - 30 + i, "x": 10 + i} for i in range(20)]
    r = client.post("/api/device/telemetry/batch", json=batch, headers=dev(robot["api_key"]))
    assert r.status_code == 202 and r.json()["accepted"] == 20
    csv = client.get("/api/telemetry/export.csv", headers=h)
    assert csv.status_code == 200 and csv.text.count("\n") == 21 and csv.text.startswith("timestamp_utc,robot")
    heat = client.get("/api/analytics/heatmap?cell=5", headers=h).json()
    assert sum(c["n"] for c in heat["cells"]) == 20
    p = client.post("/api/analytics/predict", json=FIRE, headers=h).json()
    assert p["severity"] == "critical" and p["explanation"]
    tel = client.get(f"/api/robots/{robot['id']}/telemetry?minutes=5", headers=h).json()
    assert len(tel) == 20 and tel[0]["ts"] < tel[-1]["ts"]


def test_websocket_receives_live_events(client):
    h = signup(client)
    token = h["Authorization"].split()[1]
    robot = make_robot(client, h)
    with client.websocket_connect(f"/ws?token={token}") as ws:
        client.post("/api/device/telemetry", json=FIRE, headers=dev(robot["api_key"]))
        events = [ws.receive_json()["event"] for _ in range(2)]
    assert "incident.opened" in events and "telemetry" in events


def test_simulator_tick_generates_telemetry(client):
    from fireops.simulator import Simulator, seed_demo
    h = signup(client)
    me = client.get("/api/auth/me", headers=h).json()
    out = seed_demo(me["org"]["id"], me["user"]["id"])
    assert len(out["created_robot_ids"]) == 3  # free plan cap
    sim = Simulator(interval=1.0)
    sim.ignite(me["org"]["id"], 50, 30, 0.9)
    for _ in range(3):
        sim.tick()
    robots = client.get("/api/robots", headers=h).json()
    assert all(r["status"] != "offline" for r in robots)
    rid = robots[0]["id"]
    client.post(f"/api/robots/{rid}/commands", json={"kind": "scan"}, headers=h)
    sim.tick(); sim.tick()
    cmd = client.get(f"/api/commands?robot_id={rid}", headers=h).json()[0]
    assert cmd["status"] == "completed" and cmd["result"]["fires_detected"] >= 1


def test_frontend_served(client):
    r = client.get("/")
    assert r.status_code == 200 and "FireOps" in r.text
    assert client.get("/static/app.js").status_code == 200
    assert client.get("/api/health").json()["status"] == "ok"
