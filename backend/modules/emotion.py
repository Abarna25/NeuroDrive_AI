"""Emotion classification via DeepFace, throttled to every 5th frame with smoothing."""

import cv2

EMOTION_RISK_WEIGHTS = {
    "angry": 1.0,
    "fear": 0.7,
    "disgust": 0.6,
    "sad": 0.3,
    "surprise": 0.2,
    "neutral": 0.05,
    "happy": 0.0,
}

ANALYZE_FRAME_INTERVAL = 5
SMOOTHING_PREV_WEIGHT = 0.7
SMOOTHING_NEW_WEIGHT = 0.3


class EmotionDetector:
    def __init__(self):
        # Import here so the (heavy) TensorFlow stack loads at detector
        # construction time, matching load-at-startup model policy.
        from deepface import DeepFace

        self.deepface = DeepFace
        self.frame_count = 0
        self.score = 0.0
        self.dominant_emotion = "neutral"
        self.confidence = 0.0
        self.all_emotions = {e: 0.0 for e in EMOTION_RISK_WEIGHTS}
        self.face_region = None  # (x, y, w, h) from the last successful analysis

    def _analyze(self, frame):
        try:
            results = self.deepface.analyze(
                frame,
                actions=["emotion"],
                enforce_detection=False,
                silent=True,
            )
            result = results[0] if isinstance(results, list) else results
            emotions = result.get("emotion", {})
            dominant = result.get("dominant_emotion", "neutral")
            if dominant not in EMOTION_RISK_WEIGHTS:
                dominant = "neutral"

            self.dominant_emotion = dominant
            self.confidence = round(float(emotions.get(dominant, 0.0)), 1)
            self.all_emotions = {
                e: round(float(p) / 100.0, 4) for e, p in emotions.items()
            }

            region = result.get("region") or {}
            if region.get("w", 0) > 0 and region.get("h", 0) > 0:
                self.face_region = (
                    int(region["x"]),
                    int(region["y"]),
                    int(region["w"]),
                    int(region["h"]),
                )
            else:
                self.face_region = None

            new_score = EMOTION_RISK_WEIGHTS[dominant]
            self.score = (
                SMOOTHING_PREV_WEIGHT * self.score + SMOOTHING_NEW_WEIGHT * new_score
            )
        except Exception as exc:  # noqa: BLE001 - keep last known emotion on failure
            print(f"[emotion] DeepFace analysis failed, using last result: {exc}")

    def process(self, frame):
        self.frame_count += 1
        if self.frame_count % ANALYZE_FRAME_INTERVAL == 1:
            self._analyze(frame)

        annotated = frame.copy()
        self.annotate(annotated)

        return {
            "score": round(self.score, 3),
            "dominant_emotion": self.dominant_emotion,
            "confidence": self.confidence,
            "all_emotions": dict(self.all_emotions),
            "annotated_frame": annotated,
        }

    def annotate(self, frame):
        """Draw the last face box and emotion label onto `frame` in place."""
        if self.face_region is None:
            return
        x, y, w, h = self.face_region
        cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 160, 60), 2)
        cv2.putText(
            frame,
            f"{self.dominant_emotion} {self.confidence:.0f}%",
            (x, max(y - 8, 12)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (255, 160, 60),
            1,
            cv2.LINE_AA,
        )
