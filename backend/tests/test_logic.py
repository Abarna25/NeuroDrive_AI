"""Unit tests for the pure-logic parts: risk engine, alerts, database, EAR/MAR math."""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from alert_system import AlertSystem
from risk_engine import RiskEngine


# ── risk engine ──────────────────────────────────────────────────────


def test_risk_weights():
    engine = RiskEngine()
    result = engine.compute(1.0, 1.0, 1.0)
    assert result["risk_score"] == 100.0
    result = RiskEngine().compute(1.0, 0.0, 0.0)
    assert result["risk_score"] == 40.0
    result = RiskEngine().compute(0.0, 1.0, 0.0)
    assert result["risk_score"] == 35.0
    result = RiskEngine().compute(0.0, 0.0, 1.0)
    assert result["risk_score"] == 25.0


def test_risk_levels():
    engine = RiskEngine()
    assert engine.compute(0.0, 0.0, 0.0)["status"] == "safe"
    assert engine.compute(0.75, 0.0, 0.0)["status"] == "safe"  # 30.0 -> safe
    assert engine.compute(0.8, 0.0, 0.0)["status"] == "caution"  # 32.0
    r = RiskEngine().compute(1.0, 0.5, 0.2)  # 40 + 17.5 + 5 = 62.5
    assert r["risk_score"] == 62.5
    assert r["status"] == "danger"
    assert r["color"] == "red"


def test_should_alert_on_transition_only():
    engine = RiskEngine()
    assert engine.compute(0.0, 0.0, 0.0)["should_alert"] is False  # safe
    assert engine.compute(1.0, 0.0, 0.0)["should_alert"] is True  # safe -> caution
    assert engine.compute(1.0, 0.0, 0.0)["should_alert"] is False  # stays caution
    assert engine.compute(1.0, 1.0, 1.0)["should_alert"] is True  # caution -> danger
    assert engine.compute(1.0, 1.0, 1.0)["should_alert"] is False  # stays danger
    assert engine.compute(0.0, 0.0, 0.0)["should_alert"] is False  # danger -> safe


def test_timestamp_iso():
    ts = RiskEngine().compute(0, 0, 0)["timestamp"]
    from datetime import datetime

    datetime.fromisoformat(ts)  # raises if malformed


# ── alert system ─────────────────────────────────────────────────────


def _risk(status, should_alert=True):
    return {"status": status, "should_alert": should_alert, "risk_score": 50.0}


def test_alert_fires_on_should_alert():
    alerts = AlertSystem()
    out = alerts.check_and_alert(_risk("caution"))
    assert out["alert_triggered"] is True
    assert "focused" in out["alert_message"]
    alerts.shutdown()


def test_alert_respects_cooldown():
    alerts = AlertSystem()
    assert alerts.check_and_alert(_risk("danger"))["alert_triggered"] is True
    # Same alert again inside 10s window is suppressed.
    assert alerts.check_and_alert(_risk("danger"))["alert_triggered"] is False
    # A different message is not suppressed.
    assert alerts.check_and_alert(_risk("caution"))["alert_triggered"] is True
    alerts.shutdown()


def test_alert_cooldown_expires():
    alerts = AlertSystem()
    assert alerts.check_and_alert(_risk("danger"))["alert_triggered"] is True
    alerts.last_alert_time = time.monotonic() - 11.0
    assert alerts.check_and_alert(_risk("danger"))["alert_triggered"] is True
    alerts.shutdown()


def test_no_alert_when_safe_or_not_flagged():
    alerts = AlertSystem()
    assert alerts.check_and_alert(_risk("safe"))["alert_triggered"] is False
    assert alerts.check_and_alert(_risk("danger", should_alert=False))["alert_triggered"] is False
    alerts.shutdown()


# ── database ─────────────────────────────────────────────────────────


def test_database_roundtrip():
    import database

    database.init_db()
    session_id = database.start_session()
    assert database.get_session(session_id)["end_time"] is None

    risk = {
        "timestamp": "2026-07-12T00:00:00+00:00",
        "status": "danger",
        "risk_score": 72.5,
    }
    database.log_alert(
        session_id,
        risk,
        {
            "drowsiness_score": 0.9,
            "aggression_score": 0.3,
            "emotion_score": 0.7,
            "dominant_emotion": "angry",
            "ear_value": 0.18,
        },
    )
    alerts = database.get_session_alerts(session_id)
    assert len(alerts) == 1
    assert alerts[0]["alert_type"] == "danger"
    assert alerts[0]["ear_value"] == 0.18

    summary = database.end_session(
        session_id,
        {
            "total_alerts": 1,
            "avg_risk_score": 40.2,
            "peak_risk_score": 72.5,
            "dominant_emotion": "angry",
        },
    )
    assert summary["total_alerts"] == 1
    assert summary["end_time"] is not None
    assert database.end_session("nonexistent", {}) is None


# ── EAR / MAR math (imports mediapipe transitively) ──────────────────


def test_ear_math():
    from modules.drowsiness import eye_aspect_ratio

    # Open eye: vertical gaps 2.0, horizontal 4.0 -> EAR = (2+2)/(2*4) = 0.5
    eye = [(0, 0), (1, -1), (3, -1), (4, 0), (3, 1), (1, 1)]
    assert abs(eye_aspect_ratio(eye) - 0.5) < 1e-9
    # Closed eye: no vertical gap -> EAR = 0
    eye_closed = [(0, 0), (1, 0), (3, 0), (4, 0), (3, 0), (1, 0)]
    assert eye_aspect_ratio(eye_closed) == 0.0


def test_mar_math():
    from modules.drowsiness import mouth_aspect_ratio

    # Wide-open mouth: vertical 3, horizontal 4 -> MAR 0.75 (> 0.6 yawn threshold)
    assert abs(mouth_aspect_ratio((2, 0), (2, 3), (0, 1.5), (4, 1.5)) - 0.75) < 1e-9
    # Closed mouth
    assert mouth_aspect_ratio((2, 1), (2, 1), (0, 1), (4, 1)) == 0.0
