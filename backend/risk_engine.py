"""Unified risk scoring: weighted blend of the three module scores."""

from datetime import datetime, timezone

DROWSINESS_WEIGHT = 0.40
EMOTION_WEIGHT = 0.35
AGGRESSION_WEIGHT = 0.25


class RiskEngine:
    def __init__(self):
        self.previous_status = "safe"

    @staticmethod
    def _classify(risk_score):
        if risk_score <= 30:
            return "safe", "green"
        if risk_score <= 60:
            return "caution", "yellow"
        return "danger", "red"

    def compute(self, drowsiness_score, emotion_score, aggression_score):
        raw = (
            drowsiness_score * DROWSINESS_WEIGHT
            + emotion_score * EMOTION_WEIGHT
            + aggression_score * AGGRESSION_WEIGHT
        )
        risk_score = round(raw * 100, 1)
        status, color = self._classify(risk_score)

        should_alert = status != self.previous_status and status in ("caution", "danger")
        self.previous_status = status

        return {
            "risk_score": risk_score,
            "status": status,
            "color": color,
            "should_alert": should_alert,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
