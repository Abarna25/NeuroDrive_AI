"""Smoke tests for the CV detectors: run on synthetic frames, verify the
result schema and no-crash behavior when no face/vehicle is visible.

These load the full model stack (MediaPipe, TF/DeepFace, YOLO, MiDaS) and may
download weights on first run — expect the first execution to be slow.
"""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _noise_frame():
    rng = np.random.default_rng(42)
    return rng.integers(0, 255, size=(480, 640, 3), dtype=np.uint8)


def _black_frame():
    return np.zeros((480, 640, 3), dtype=np.uint8)


def test_drowsiness_schema_and_no_face():
    from modules.drowsiness import DrowsinessDetector

    det = DrowsinessDetector()
    for frame in (_noise_frame(), _black_frame()):
        out = det.process(frame)
        assert set(out) == {
            "score", "ear", "mar", "is_drowsy", "is_yawning",
            "is_nodding", "perclos", "annotated_frame",
        }
        assert 0.0 <= out["score"] <= 1.0
        assert out["annotated_frame"].shape == frame.shape
    det.close()


def test_emotion_schema_and_bad_frames():
    from modules.emotion import EmotionDetector

    det = EmotionDetector()
    for frame in (_noise_frame(), _black_frame(), _noise_frame()):
        out = det.process(frame)
        assert set(out) == {
            "score", "dominant_emotion", "confidence", "all_emotions", "annotated_frame",
        }
        assert 0.0 <= out["score"] <= 1.0
        assert isinstance(out["all_emotions"], dict)


def test_aggression_schema_and_flow():
    from modules.aggression import AggressionDetector

    det = AggressionDetector()
    frames = [_black_frame(), _noise_frame(), _black_frame(), _noise_frame()]
    for frame in frames:
        out = det.process(frame)
        assert set(out) == {
            "score", "flow_magnitude", "is_tailgating",
            "vehicle_distance", "annotated_frame",
        }
        assert 0.0 <= out["score"] <= 1.0
        assert out["vehicle_distance"] in ("safe", "close", "critical")
    # Alternating black/noise frames produce large optical flow.
    assert out["flow_magnitude"] > 0.0
