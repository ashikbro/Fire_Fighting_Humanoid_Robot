from fireops import analytics
from tests.conftest import CALM, FIRE


def test_risk_score_separates_calm_and_fire():
    assert analytics.risk_score(CALM) < 0.1
    assert analytics.risk_score(FIRE) > 0.9
    assert analytics.severity_for(analytics.risk_score(CALM)) == "low"
    assert analytics.severity_for(analytics.risk_score(FIRE)) == "critical"


def test_risk_is_monotonic_in_temperature_and_smoke():
    base = dict(CALM)
    scores = [analytics.risk_score({**base, "temperature": t}) for t in (20, 40, 60, 80)]
    assert scores == sorted(scores)
    scores = [analytics.risk_score({**base, "smoke": s}) for s in (0, 100, 200, 300)]
    assert scores == sorted(scores)


def test_explain_risk_ranks_dominant_feature_first():
    exp = analytics.explain_risk({**CALM, "temperature": 120})
    assert exp[0]["feature"] == "temperature"


def test_anomaly_detection_flags_spike_and_ignores_noise():
    hist = [{**CALM, "temperature": 24 + (i % 3) * 0.2} for i in range(30)]
    assert analytics.zscore_anomalies(hist, {**CALM, "temperature": 24.3}) == []
    hits = analytics.zscore_anomalies(hist, {**CALM, "temperature": 55})
    assert [h["metric"] for h in hits] == ["temperature"]


def test_anomaly_needs_enough_history():
    hist = [CALM] * 5
    assert analytics.zscore_anomalies(hist, {**CALM, "temperature": 90}) == []


def test_maintenance_forecast_battery_eta():
    # 1% per minute drain from 60% -> reaches 10% in ~50 minutes after the last point (50%)
    hist = [{"ts": i * 60.0, "battery": 60 - i, "motor_temp": 50 + i, "water_level": 15} for i in range(11)]
    f = analytics.maintenance_forecast(hist, now_ts=600)
    assert abs(f["battery_drain_per_hour"] - 60) < 0.01
    assert abs(f["battery_eta_minutes"] - 40) < 0.1
    assert f["motor_temp_trend_per_hour"] > 0
    assert any("water" in r.lower() for r in f["recommendations"])
    assert 0 <= f["health_score"] < 100


def test_maintenance_forecast_ignores_short_windows():
    hist = [{"ts": i * 0.1, "battery": 60 - i, "motor_temp": 50} for i in range(10)]
    assert analytics.maintenance_forecast(hist, 1)["battery_eta_minutes"] is None


def test_rules_and_percentile():
    rules = [{"metric": "gas", "op": ">=", "threshold": 300, "enabled": 1},
             {"metric": "battery", "op": "<", "threshold": 20, "enabled": 0}]
    assert analytics.evaluate_rules(rules, {"gas": 310, "battery": 5}) == [rules[0]]
    assert analytics.percentile([1, 2, 3, 4], 0.5) == 2.5
    assert analytics.percentile([], 0.9) is None
