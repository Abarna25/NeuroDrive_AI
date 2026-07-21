"""Drowsiness detection via MediaPipe FaceMesh: EAR, MAR (yawn), head nod, PERCLOS."""

import math
from collections import deque

import cv2
import mediapipe as mp
import numpy as np
from scipy.spatial import distance as dist

LEFT_EYE_INDICES = [33, 160, 158, 133, 153, 144]
RIGHT_EYE_INDICES = [362, 385, 387, 263, 373, 380]

MOUTH_TOP = 13
MOUTH_BOTTOM = 14
MOUTH_LEFT = 61
MOUTH_RIGHT = 291

NOSE_TIP = 1
CHIN = 152
FOREHEAD = 10

EAR_THRESHOLD = 0.25
MAR_THRESHOLD = 0.6
YAWN_MIN_FRAMES = 3
PITCH_THRESHOLD_DEG = 20.0
PERCLOS_BUFFER_SIZE = 90  # 3 seconds at 30 fps
PERCLOS_DROWSY_RATIO = 0.70


def eye_aspect_ratio(eye_points):
    A = dist.euclidean(eye_points[1], eye_points[5])
    B = dist.euclidean(eye_points[2], eye_points[4])
    C = dist.euclidean(eye_points[0], eye_points[3])
    if C == 0:
        return 0.0
    return (A + B) / (2.0 * C)


def mouth_aspect_ratio(top, bottom, left, right):
    vertical = dist.euclidean(top, bottom)
    horizontal = dist.euclidean(left, right)
    if horizontal == 0:
        return 0.0
    return vertical / horizontal


class DrowsinessDetector:
    def __init__(self):
        self.face_mesh = mp.solutions.face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self.ear_buffer = deque(maxlen=PERCLOS_BUFFER_SIZE)
        self.yawn_frame_count = 0
        self.last_result = self._empty_result()
        # Drawing state for annotate(): pixel coords of the last detected landmarks.
        self._draw_state = None

    def _empty_result(self):
        return {
            "score": 0.0,
            "ear": 0.0,
            "mar": 0.0,
            "is_drowsy": False,
            "is_yawning": False,
            "is_nodding": False,
            "perclos": 0.0,
        }

    def _pitch_degrees(self, landmarks):
        """Head pitch from the face's vertical axis (forehead -> chin).

        MediaPipe z grows away from the camera; when the head nods forward the
        chin swings toward the camera relative to the forehead, tilting the
        axis out of the image plane.
        """
        fh = landmarks[FOREHEAD]
        ch = landmarks[CHIN]
        dy = ch.y - fh.y
        dz = ch.z - fh.z
        if dy == 0:
            return 90.0
        return abs(math.degrees(math.atan2(dz, dy)))

    def process(self, frame):
        h, w = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(rgb)

        annotated = frame.copy()

        if not results.multi_face_landmarks:
            # No face: report neutral values, treat eyes as open for PERCLOS.
            self.ear_buffer.append(False)
            self.yawn_frame_count = 0
            self._draw_state = None
            result = self._empty_result()
            result["perclos"] = self._perclos_pct()
            result["annotated_frame"] = annotated
            self.last_result = {k: v for k, v in result.items() if k != "annotated_frame"}
            return result

        landmarks = results.multi_face_landmarks[0].landmark

        def px(idx):
            lm = landmarks[idx]
            return (lm.x * w, lm.y * h)

        left_eye = [px(i) for i in LEFT_EYE_INDICES]
        right_eye = [px(i) for i in RIGHT_EYE_INDICES]
        ear = (eye_aspect_ratio(left_eye) + eye_aspect_ratio(right_eye)) / 2.0

        mar = mouth_aspect_ratio(px(MOUTH_TOP), px(MOUTH_BOTTOM), px(MOUTH_LEFT), px(MOUTH_RIGHT))

        pitch = self._pitch_degrees(landmarks)
        is_nodding = pitch > PITCH_THRESHOLD_DEG

        eyes_closed = ear < EAR_THRESHOLD
        self.ear_buffer.append(eyes_closed)
        perclos = self._perclos_pct()
        perclos_flag = (
            len(self.ear_buffer) == PERCLOS_BUFFER_SIZE
            and perclos > PERCLOS_DROWSY_RATIO * 100
        )

        if mar > MAR_THRESHOLD:
            self.yawn_frame_count += 1
        else:
            self.yawn_frame_count = 0
        is_yawning = self.yawn_frame_count >= YAWN_MIN_FRAMES

        score = 0.0
        if eyes_closed:
            score += 0.4
        if perclos_flag:
            score += 0.35
        if is_yawning:
            score += 0.15
        if is_nodding:
            score += 0.10
        score = min(score, 1.0)

        is_drowsy = eyes_closed or perclos_flag

        self._draw_state = {
            "left_eye": np.array(left_eye, dtype=np.int32),
            "right_eye": np.array(right_eye, dtype=np.int32),
            "mouth": np.array(
                [px(MOUTH_LEFT), px(MOUTH_TOP), px(MOUTH_RIGHT), px(MOUTH_BOTTOM)],
                dtype=np.int32,
            ),
            "ear": ear,
            "mar": mar,
            "perclos": perclos,
            "is_drowsy": is_drowsy,
        }
        self.annotate(annotated)

        result = {
            "score": round(score, 3),
            "ear": round(ear, 3),
            "mar": round(mar, 3),
            "is_drowsy": is_drowsy,
            "is_yawning": is_yawning,
            "is_nodding": is_nodding,
            "perclos": round(perclos, 1),
            "annotated_frame": annotated,
        }
        self.last_result = {k: v for k, v in result.items() if k != "annotated_frame"}
        return result

    def _perclos_pct(self):
        if not self.ear_buffer:
            return 0.0
        return 100.0 * sum(self.ear_buffer) / len(self.ear_buffer)

    def annotate(self, frame):
        """Draw the last detected eye/mouth landmarks and metrics onto `frame` in place."""
        if self._draw_state is None:
            return
        s = self._draw_state
        color = (0, 0, 255) if s["is_drowsy"] else (0, 255, 0)
        cv2.polylines(frame, [s["left_eye"]], isClosed=True, color=color, thickness=1)
        cv2.polylines(frame, [s["right_eye"]], isClosed=True, color=color, thickness=1)
        cv2.polylines(frame, [s["mouth"]], isClosed=True, color=(255, 200, 0), thickness=1)
        cv2.putText(
            frame,
            f"EAR {s['ear']:.2f}  MAR {s['mar']:.2f}  PERCLOS {s['perclos']:.0f}%",
            (10, frame.shape[0] - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (240, 240, 240),
            1,
            cv2.LINE_AA,
        )

    def close(self):
        self.face_mesh.close()
