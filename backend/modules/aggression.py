"""Aggression detection: Farneback optical flow, YOLOv8n tailgating, MiDaS depth."""

from collections import deque

import cv2
import numpy as np

FLOW_AGGRESSIVE_MAGNITUDE = 8.0
FLOW_ROLLING_FRAMES = 30
VEHICLE_CLASS_IDS = {2, 3, 5, 7}  # car, motorcycle, bus, truck
TAILGATE_HEIGHT_RATIO = 0.35
CRITICAL_HEIGHT_RATIO = 0.50
DEPTH_CLOSE_THRESHOLD = 0.75
DETECTION_FRAME_INTERVAL = 3  # run YOLO / MiDaS on every 3rd frame


class AggressionDetector:
    def __init__(self):
        self.prev_gray = None
        self.flow_buffer = deque(maxlen=FLOW_ROLLING_FRAMES)
        self.frame_count = 0

        # Cached detection state, refreshed every DETECTION_FRAME_INTERVAL frames.
        self.last_vehicle_box = None  # (x1, y1, x2, y2)
        self.is_tailgating = False
        self.vehicle_distance = "safe"
        self.depth_close = False

        self.yolo = None
        try:
            from ultralytics import YOLO

            self.yolo = YOLO("yolov8n.pt")
        except Exception as exc:  # noqa: BLE001 - degrade to optical-flow-only
            print(f"[aggression] YOLO unavailable, vehicle detection disabled: {exc}")

        self.midas = None
        self.midas_transform = None
        try:
            import torch

            self.torch = torch
            self.midas = torch.hub.load("intel-isl/MiDaS", "MiDaS_small")
            self.midas.eval()
            transforms = torch.hub.load("intel-isl/MiDaS", "transforms")
            self.midas_transform = transforms.small_transform
        except Exception as exc:  # noqa: BLE001 - depth module is optional
            self.midas = None
            print(f"[aggression] MiDaS unavailable, depth module disabled: {exc}")

    def _optical_flow_magnitude(self, gray):
        if self.prev_gray is None or self.prev_gray.shape != gray.shape:
            self.prev_gray = gray
            return 0.0
        flow = cv2.calcOpticalFlowFarneback(
            self.prev_gray,
            gray,
            None,
            pyr_scale=0.5,
            levels=3,
            winsize=15,
            iterations=3,
            poly_n=5,
            poly_sigma=1.2,
            flags=0,
        )
        self.prev_gray = gray
        magnitude, _ = cv2.cartToPolar(flow[..., 0], flow[..., 1])
        return float(np.mean(magnitude))

    def _detect_vehicle(self, frame):
        """Update cached vehicle box / tailgate flags from a YOLO pass."""
        if self.yolo is None:
            return
        h = frame.shape[0]
        try:
            results = self.yolo(frame, verbose=False)[0]
        except Exception as exc:  # noqa: BLE001
            print(f"[aggression] YOLO inference failed: {exc}")
            return

        best_box = None
        best_area = 0.0
        for box in results.boxes:
            if int(box.cls[0]) not in VEHICLE_CLASS_IDS:
                continue
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            area = (x2 - x1) * (y2 - y1)
            if area > best_area:
                best_area = area
                best_box = (int(x1), int(y1), int(x2), int(y2))

        self.last_vehicle_box = best_box
        if best_box is None:
            self.is_tailgating = False
            self.vehicle_distance = "safe"
            return

        height_ratio = (best_box[3] - best_box[1]) / h
        if height_ratio > CRITICAL_HEIGHT_RATIO:
            self.is_tailgating = True
            self.vehicle_distance = "critical"
        elif height_ratio > TAILGATE_HEIGHT_RATIO:
            self.is_tailgating = True
            self.vehicle_distance = "close"
        else:
            self.is_tailgating = False
            self.vehicle_distance = "safe"

    def _estimate_depth(self, frame):
        """Update depth_close flag from a MiDaS pass over the center-bottom region."""
        if self.midas is None:
            return
        try:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            input_batch = self.midas_transform(rgb)
            with self.torch.no_grad():
                prediction = self.midas(input_batch)
                prediction = self.torch.nn.functional.interpolate(
                    prediction.unsqueeze(1),
                    size=frame.shape[:2],
                    mode="bicubic",
                    align_corners=False,
                ).squeeze()
            depth = prediction.cpu().numpy()
            d_min, d_max = depth.min(), depth.max()
            if d_max - d_min < 1e-6:
                self.depth_close = False
                return
            depth_norm = (depth - d_min) / (d_max - d_min)  # 1.0 = closest
            h, w = depth_norm.shape
            region = depth_norm[int(h * 0.55) : int(h * 0.95), int(w * 0.30) : int(w * 0.70)]
            self.depth_close = float(np.mean(region)) > DEPTH_CLOSE_THRESHOLD
        except Exception as exc:  # noqa: BLE001
            print(f"[aggression] MiDaS inference failed: {exc}")
            self.depth_close = False

    def process(self, frame):
        self.frame_count += 1
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        magnitude = self._optical_flow_magnitude(gray)
        self.flow_buffer.append(magnitude)
        rolling_mean = float(np.mean(self.flow_buffer)) if self.flow_buffer else 0.0

        if self.frame_count % DETECTION_FRAME_INTERVAL == 0 or self.frame_count == 1:
            self._detect_vehicle(frame)
            self._estimate_depth(frame)

        score = min(rolling_mean / 20.0, 0.4)
        if self.is_tailgating:
            score += 0.35
        if self.depth_close:
            score += 0.25
        score = min(score, 1.0)

        annotated = frame.copy()
        self.annotate(annotated)

        return {
            "score": round(score, 3),
            "flow_magnitude": round(rolling_mean, 2),
            "is_tailgating": self.is_tailgating,
            "vehicle_distance": self.vehicle_distance,
            "annotated_frame": annotated,
        }

    def annotate(self, frame):
        """Draw the last vehicle detection onto `frame` in place."""
        if self.last_vehicle_box is None:
            return
        x1, y1, x2, y2 = self.last_vehicle_box
        color = {
            "safe": (0, 255, 0),
            "close": (0, 165, 255),
            "critical": (0, 0, 255),
        }[self.vehicle_distance]
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        cv2.putText(
            frame,
            f"vehicle: {self.vehicle_distance}",
            (x1, max(y1 - 8, 12)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            color,
            1,
            cv2.LINE_AA,
        )
