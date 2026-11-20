"""Built-in fleet simulator ("demo mode").

For every organisation with the simulator enabled it drives each robot through
a physically plausible loop: patrol, drain battery, react to randomly ignited
fires, execute queued commands (move_to / suppress / return_to_base / halt)
and stream telemetry through the exact same ingest pipeline real robots use.
"""
from __future__ import annotations

import json
import logging
import math
import random
import threading
import time
from dataclasses import dataclass, field

from .config import settings
from .db import get_conn, now, rows
from .services import QuotaExceeded, ingest

log = logging.getLogger("fireops.simulator")


@dataclass
class Fire:
    x: float
    y: float
    intensity: float  # 0..1


@dataclass
class SimRobot:
    x: float
    y: float
    battery: float = 100.0
    water: float = 100.0
    motor: float = 38.0
    target: tuple[float, float] | None = None
    mode: str = "patrol"
    active_cmd: dict | None = None
    base: tuple[float, float] = (5.0, 5.0)


@dataclass
class OrgWorld:
    width: float = 100.0
    height: float = 60.0
    fires: list[Fire] = field(default_factory=list)
    robots: dict[int, SimRobot] = field(default_factory=dict)


class Simulator:
    def __init__(self, interval: float) -> None:
        self.interval = interval
        self.worlds: dict[int, OrgWorld] = {}
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.rng = random.Random()

    # ------------------------------------------------------------ lifecycle
    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="fireops-simulator", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                self.tick()
            except Exception:
                log.exception("simulator tick failed")
            self._stop.wait(self.interval)

    # ------------------------------------------------------------ world
    def ignite(self, org_id: int, x: float | None = None, y: float | None = None, intensity: float = 0.5) -> Fire:
        w = self.worlds.setdefault(org_id, OrgWorld())
        f = Fire(x if x is not None else self.rng.uniform(15, w.width - 5),
                 y if y is not None else self.rng.uniform(10, w.height - 5), intensity)
        w.fires.append(f)
        return f

    def _exposure(self, w: OrgWorld, x: float, y: float) -> float:
        e = 0.0
        for f in w.fires:
            d = math.hypot(f.x - x, f.y - y)
            e += f.intensity * math.exp(-d / 9.0)
        return min(e, 1.5)

    def tick(self) -> None:
        with get_conn() as conn:
            orgs = rows(conn.execute("SELECT o.id, s.width, s.height FROM orgs o LEFT JOIN sites s ON s.id = "
                                     "(SELECT MIN(id) FROM sites WHERE org_id=o.id) WHERE o.simulator_enabled=1"))
        for org in orgs:
            self._tick_org(org["id"], org["width"] or 100.0, org["height"] or 60.0)

    def _tick_org(self, org_id: int, width: float, height: float) -> None:
        w = self.worlds.setdefault(org_id, OrgWorld())
        w.width, w.height = width, height
        dt = self.interval
        # Fires grow slowly unless suppressed; occasionally a new one ignites.
        for f in w.fires:
            f.intensity = min(1.0, f.intensity + 0.004 * dt)
        w.fires = [f for f in w.fires if f.intensity > 0.03]
        if not w.fires and self.rng.random() < 0.012 * dt:
            self.ignite(org_id, intensity=0.25)

        with get_conn() as conn:
            robots = rows(conn.execute("SELECT * FROM robots WHERE org_id=?", (org_id,)).fetchall())
            pending = rows(conn.execute(
                "SELECT * FROM commands WHERE org_id=? AND status IN ('queued','delivered','in_progress') "
                "ORDER BY id", (org_id,)).fetchall())
        by_robot: dict[int, list[dict]] = {}
        for c in pending:
            by_robot.setdefault(c["robot_id"], []).append(c)

        for r in robots:
            sr = w.robots.get(r["id"])
            if sr is None:
                sr = SimRobot(x=self.rng.uniform(5, width - 5), y=self.rng.uniform(5, height - 5),
                              battery=self.rng.uniform(70, 100), base=(4.0, 4.0 + 6 * (r["id"] % 8)))
                w.robots[r["id"]] = sr
            self._apply_commands(r, sr, by_robot.get(r["id"], []), w)
            self._step(sr, w, dt)
            exposure = self._exposure(w, sr.x, sr.y)
            t = {
                "temperature": round(23 + 70 * exposure + self.rng.gauss(0, 0.6), 2),
                "smoke": round(max(0.0, 12 + 320 * exposure + self.rng.gauss(0, 3)), 1),
                "gas": round(max(0.0, 40 + 380 * exposure * 0.9 + self.rng.gauss(0, 4)), 1),
                "humidity": round(max(5.0, 48 - 30 * exposure + self.rng.gauss(0, 1)), 1),
                "flame": 1 if exposure > 0.55 else 0,
                "battery": round(sr.battery, 2),
                "water_level": round(sr.water, 1),
                "motor_temp": round(sr.motor + self.rng.gauss(0, 0.3), 2),
                "x": round(sr.x, 2), "y": round(sr.y, 2),
            }
            try:
                with get_conn() as conn:
                    res = ingest(conn, r, t)
                res["events"].flush()
            except QuotaExceeded:
                return

    def _apply_commands(self, r: dict, sr: SimRobot, cmds: list[dict], w: OrgWorld) -> None:
        for c in cmds:
            if c["status"] in ("queued", "delivered") and (sr.active_cmd is None or sr.active_cmd["id"] != c["id"]):
                if sr.active_cmd is not None and sr.active_cmd["id"] < c["id"] and c["kind"] not in ("halt",
                                                                                                    "return_to_base"):
                    continue  # finish current command first (FIFO), except overrides
                params = json.loads(c["params"] or "{}")
                sr.active_cmd = c
                if c["kind"] == "move_to":
                    sr.target, sr.mode = (float(params["x"]), float(params["y"])), "moving"
                elif c["kind"] == "return_to_base":
                    sr.target, sr.mode = sr.base, "returning"
                elif c["kind"] == "halt":
                    sr.target, sr.mode = None, "halted"
                elif c["kind"] == "suppress":
                    sr.mode = "suppressing"
                elif c["kind"] == "patrol":
                    sr.target, sr.mode = None, "patrol"
                elif c["kind"] == "scan":
                    sr.mode = "scanning"
                self._set_cmd(c["id"], "in_progress")
                break

    def _set_cmd(self, cid: int, status: str, result: dict | None = None) -> None:
        with get_conn() as conn:
            conn.execute("UPDATE commands SET status=?, result=COALESCE(?, result), "
                         "delivered_at=COALESCE(delivered_at, ?), completed_at=? WHERE id=?",
                         (status, json.dumps(result) if result else None, now(),
                          now() if status in ("completed", "failed") else None, cid))

    def _finish(self, sr: SimRobot, ok: bool = True, **result) -> None:
        if sr.active_cmd:
            self._set_cmd(sr.active_cmd["id"], "completed" if ok else "failed", result or None)
        sr.active_cmd = None

    def _step(self, sr: SimRobot, w: OrgWorld, dt: float) -> None:
        speed = 3.0 * dt
        moving = False
        if sr.mode in ("moving", "returning") and sr.target:
            dx, dy = sr.target[0] - sr.x, sr.target[1] - sr.y
            d = math.hypot(dx, dy)
            if d <= speed:
                sr.x, sr.y = sr.target
                if sr.mode == "returning":
                    sr.battery = min(100.0, sr.battery + 25)
                    sr.water = 100.0
                sr.mode = "idle"
                self._finish(sr, position=[round(sr.x, 1), round(sr.y, 1)])
            else:
                sr.x += dx / d * speed
                sr.y += dy / d * speed
                moving = True
        elif sr.mode == "suppressing":
            near = [f for f in w.fires if math.hypot(f.x - sr.x, f.y - sr.y) < 12]
            if sr.water <= 0:
                sr.mode = "idle"
                self._finish(sr, ok=False, reason="water tank empty")
            elif not near:
                sr.mode = "idle"
                self._finish(sr, extinguished=True)
            else:
                for f in near:
                    f.intensity -= 0.06 * dt
                sr.water = max(0.0, sr.water - 1.5 * dt)
        elif sr.mode == "scanning":
            sr.mode = "idle"
            self._finish(sr, fires_detected=len(w.fires))
        elif sr.mode == "patrol":
            if sr.target is None or math.hypot(sr.target[0] - sr.x, sr.target[1] - sr.y) < 1:
                sr.target = (self.rng.uniform(5, w.width - 5), self.rng.uniform(5, w.height - 5))
            dx, dy = sr.target[0] - sr.x, sr.target[1] - sr.y
            d = math.hypot(dx, dy) or 1
            step = min(d, speed * 0.4)
            sr.x += dx / d * step
            sr.y += dy / d * step
            moving = True
        elif sr.mode == "idle" and sr.active_cmd is None:
            sr.mode = "patrol"
        sr.battery = max(0.0, sr.battery - (0.05 if moving else 0.015) * dt * (2 if sr.mode == "suppressing" else 1))
        target_motor = 70 if sr.mode == "suppressing" else 52 if moving else 36
        sr.motor += (target_motor - sr.motor) * 0.05 * dt
        if sr.battery < 12 and sr.mode not in ("returning",):
            sr.target, sr.mode = sr.base, "returning"


simulator = Simulator(settings.simulator_interval)


def seed_demo(org_id: int, user_id: int | None) -> dict:
    """Register demo robots (within plan limits) and turn the simulator on."""
    from .config import PLANS
    from .db import audit
    from .security import new_device_key
    names = ["Ember Hawk", "Iron Tide", "Blaze Warden", "Torrent", "Phoenix", "Aegis"]
    created = []
    with get_conn() as conn:
        plan = PLANS[conn.execute("SELECT plan FROM orgs WHERE id=?", (org_id,)).fetchone()[0]]
        have = conn.execute("SELECT COUNT(*) FROM robots WHERE org_id=?", (org_id,)).fetchone()[0]
        site = conn.execute("SELECT id FROM sites WHERE org_id=? ORDER BY id LIMIT 1", (org_id,)).fetchone()
        for name in names[: max(0, min(len(names), plan["max_robots"]) - have)]:
            _, key_hash, prefix = new_device_key()
            rid = conn.execute("INSERT INTO robots (org_id, site_id, name, model, api_key_hash, api_key_prefix, "
                               "created_at) VALUES (?,?,?,?,?,?,?)",
                               (org_id, site[0] if site else None, name, "FFHR-2", key_hash, prefix, now())).lastrowid
            created.append(rid)
        conn.execute("UPDATE orgs SET simulator_enabled=1 WHERE id=?", (org_id,))
        audit(conn, org_id, user_id, "demo.seeded", {"robots": created})
    return {"created_robot_ids": created, "simulator_enabled": True}
