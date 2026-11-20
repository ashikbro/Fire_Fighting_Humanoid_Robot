"""Analytics engine: fire-risk scoring, anomaly detection and predictive maintenance.

Everything here is pure Python and deterministic so it can be unit-tested and
run at ingest time without any ML runtime. The risk model is a calibrated
logistic combination of the same features the original project's
`train_fire_model.py` uses (temperature, smoke, gas, humidity) plus a flame sensor.
"""
from __future__ import annotations

import math
import statistics
from typing import Iterable, Sequence

SEVERITIES = ["low", "medium", "high", "critical"]
SEVERITY_RANK = {s: i for i, s in enumerate(SEVERITIES)}

METRICS = ["temperature", "smoke", "gas", "humidity", "flame", "battery",
           "water_level", "motor_temp", "risk_score"]

# Logistic weights over normalised features. Tuned so that ambient indoor
# conditions (~24C, low smoke, ~45% humidity) score < 0.1 and an active fire
# (> 70C, dense smoke, flame detected) scores > 0.9.
_WEIGHTS = {
    "temperature": 3.2,   # (t - 25) / 40
    "smoke": 2.6,         # smoke / 300 ppm
    "gas": 1.8,           # gas / 400 ppm
    "humidity": -1.2,     # (h - 50) / 30   (dry air raises risk)
    "flame": 2.4,         # binary
}
_BIAS = -4.2


def _features(t: dict) -> dict[str, float]:
    return {
        "temperature": ((t.get("temperature") or 25.0) - 25.0) / 40.0,
        "smoke": (t.get("smoke") or 0.0) / 300.0,
        "gas": (t.get("gas") or 0.0) / 400.0,
        "humidity": ((t.get("humidity") if t.get("humidity") is not None else 50.0) - 50.0) / 30.0,
        "flame": 1.0 if t.get("flame") else 0.0,
    }


def risk_score(t: dict) -> float:
    """Probability-like fire risk in [0, 1]."""
    f = _features(t)
    z = _BIAS + sum(_WEIGHTS[k] * v for k, v in f.items())
    return round(1.0 / (1.0 + math.exp(-z)), 4)


def explain_risk(t: dict) -> list[dict]:
    """Per-feature contribution to the logit, largest first (simple explainability)."""
    f = _features(t)
    contrib = [{"feature": k, "contribution": round(_WEIGHTS[k] * v, 3)} for k, v in f.items()]
    return sorted(contrib, key=lambda c: -abs(c["contribution"]))


def severity_for(score: float) -> str:
    if score >= 0.85:
        return "critical"
    if score >= 0.6:
        return "high"
    if score >= 0.3:
        return "medium"
    return "low"


def zscore_anomalies(history: Sequence[dict], current: dict, metrics: Iterable[str] = (
        "temperature", "smoke", "gas", "motor_temp"), threshold: float = 3.5, min_points: int = 12) -> list[dict]:
    """Flag metrics in `current` that deviate strongly from the robot's own recent baseline.

    Uses a robust z-score (median / MAD) so that a few earlier spikes do not
    mask a new one.
    """
    out = []
    for m in metrics:
        vals = [h[m] for h in history if h.get(m) is not None]
        v = current.get(m)
        if v is None or len(vals) < min_points:
            continue
        med = statistics.median(vals)
        mad = statistics.median(abs(x - med) for x in vals)
        # Floor the spread so a perfectly flat baseline does not yield infinite z.
        mad = max(mad, 0.02 * max(abs(med), 1.0))
        z = 0.6745 * (v - med) / mad
        if abs(z) >= threshold and abs(v - med) > 0.05 * max(abs(med), 1.0):
            out.append({"metric": m, "value": v, "baseline": round(med, 2), "z": round(z, 2)})
    return out


def linear_fit(xs: Sequence[float], ys: Sequence[float]) -> tuple[float, float] | None:
    n = len(xs)
    if n < 2:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    if sxx == 0:
        return None
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx
    return slope, my - slope * mx


def maintenance_forecast(history: Sequence[dict], now_ts: float, min_span_seconds: float = 60) -> dict:
    """Predict battery depletion and motor overheating from recent telemetry.

    `history` is ordered oldest -> newest and contains ts, battery, motor_temp,
    water_level.
    """
    result: dict = {"battery_eta_minutes": None, "battery_drain_per_hour": None,
                    "motor_temp_trend_per_hour": None, "motor_overheat_eta_minutes": None,
                    "water_level": None, "health_score": 100, "recommendations": []}
    if not history:
        return result
    last = history[-1]
    pts = [(h["ts"], h["battery"]) for h in history if h.get("battery") is not None]
    if len(pts) >= 5 and pts[-1][0] - pts[0][0] >= min_span_seconds:
        fit = linear_fit([p[0] for p in pts], [p[1] for p in pts])
        if fit:
            slope, _ = fit
            result["battery_drain_per_hour"] = round(-slope * 3600, 2)
            if slope < 0:
                eta = (pts[-1][1] - 10.0) / (-slope)  # seconds to 10% reserve
                result["battery_eta_minutes"] = max(0, round(eta / 60, 1))
    mts = [(h["ts"], h["motor_temp"]) for h in history if h.get("motor_temp") is not None]
    if len(mts) >= 5 and mts[-1][0] - mts[0][0] >= min_span_seconds:
        fit = linear_fit([p[0] for p in mts], [p[1] for p in mts])
        if fit:
            slope, _ = fit
            result["motor_temp_trend_per_hour"] = round(slope * 3600, 2)
            if slope > 0 and mts[-1][1] < 90:
                result["motor_overheat_eta_minutes"] = round((90 - mts[-1][1]) / slope / 60, 1)
    result["water_level"] = last.get("water_level")

    health = 100.0
    battery = last.get("battery")
    if battery is not None:
        health -= max(0.0, (40 - battery)) * 0.8
        if battery < 20:
            result["recommendations"].append("Return to base for charging")
    eta = result["battery_eta_minutes"]
    if eta is not None and eta < 30:
        result["recommendations"].append(f"Battery reserve reached in ~{eta:.0f} min")
    mt = last.get("motor_temp")
    if mt is not None:
        health -= max(0.0, mt - 60) * 1.2
        if mt >= 75:
            result["recommendations"].append("Motor running hot - reduce duty cycle and inspect cooling")
    wl = last.get("water_level")
    if wl is not None:
        health -= max(0.0, 25 - wl) * 0.6
        if wl < 20:
            result["recommendations"].append("Refill suppression water tank")
    result["health_score"] = int(max(0, min(100, round(health))))
    return result


RULE_OPS = {
    ">": lambda a, b: a > b,
    ">=": lambda a, b: a >= b,
    "<": lambda a, b: a < b,
    "<=": lambda a, b: a <= b,
    "==": lambda a, b: a == b,
}


def evaluate_rules(rules: Sequence[dict], t: dict) -> list[dict]:
    hits = []
    for r in rules:
        if not r.get("enabled", 1):
            continue
        v = t.get(r["metric"])
        if v is None:
            continue
        if RULE_OPS[r["op"]](float(v), float(r["threshold"])):
            hits.append(r)
    return hits


def percentile(values: Sequence[float], p: float) -> float | None:
    if not values:
        return None
    s = sorted(values)
    k = (len(s) - 1) * p
    lo, hi = math.floor(k), math.ceil(k)
    if lo == hi:
        return s[int(k)]
    return s[lo] + (s[hi] - s[lo]) * (k - lo)
