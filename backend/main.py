"""DriveGuard AI backend: FastAPI app, camera pipeline, WebSocket stream."""

import asyncio
import base64
import threading
import time
from collections import Counter
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import cv2
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

import database
from alert_system import AlertSystem
from risk_engine import RiskEngine

SEND_INTERVAL_SECONDS = 0.1  # max 10 FPS to the frontend
JPEG_QUALITY = 60


class SessionStats:
    """In-memory accumulator for the currently active driving session."""

    def __init__(self, session_id):
        self.session_id = session_id
        self.start_monotonic = time.monotonic()
        self.risk_sum = 0.0
        self.risk_count = 0
        self.peak_risk = 0.0
        self.peak_risk_timestamp = None
        self.emotion_counts = Counter()
        self.caution_alerts = 0
        self.danger_alerts = 0

    def record(self, risk_result, dominant_emotion):
        score = risk_result["risk_score"]
        self.risk_sum += score
        self.risk_count += 1
        if score > self.peak_risk:
            self.peak_risk = score
            self.peak_risk_timestamp = risk_result["timestamp"]
        self.emotion_counts[dominant_emotion] += 1

    def record_alert(self, status):
        if status == "caution":
            self.caution_alerts += 1
        elif status == "danger":
            self.danger_alerts += 1

    def summary(self):
        avg = self.risk_sum / self.risk_count if self.risk_count else 0.0
        dominant = (
            self.emotion_counts.most_common(1)[0][0]
            if self.emotion_counts
            else "neutral"
        )
        return {
            "total_drive_seconds": round(time.monotonic() - self.start_monotonic, 1),
            "total_alerts": self.caution_alerts + self.danger_alerts,
            "caution_alerts": self.caution_alerts,
            "danger_alerts": self.danger_alerts,
            "avg_risk_score": round(avg, 1),
            "peak_risk_score": self.peak_risk,
            "peak_risk_timestamp": self.peak_risk_timestamp,
            "dominant_emotion": dominant,
        }


class StreamManager:
    """Owns the models, the camera capture thread, and the latest pipeline result."""

    def __init__(self):
        self.models_ready = False
        self.model_load_error = None
        self.drowsiness = None
        self.aggression = None
        self.emotion = None
        self.risk_engine = RiskEngine()
        self.alert_system = AlertSystem()

        self.executor = None
        self.capture_thread = None
        self.capture_running = False
        self.camera_error = None

        self._latest_lock = threading.Lock()
        self._latest_payload = None

        self._client_lock = threading.Lock()
        self.client_count = 0

        self._session_lock = threading.Lock()
        self.session_stats = None

    # ── model loading ────────────────────────────────────────────────

    def load_models(self):
        """Load all detectors once at startup (called from a background thread)."""
        from concurrent.futures import ThreadPoolExecutor

        from modules import AggressionDetector, DrowsinessDetector, EmotionDetector

        try:
            self.drowsiness = DrowsinessDetector()
            self.emotion = EmotionDetector()
            self.aggression = AggressionDetector()
            self.executor = ThreadPoolExecutor(max_workers=3)
            self.models_ready = True
            print("[driveguard] all models loaded")
        except Exception as exc:  # noqa: BLE001
            self.model_load_error = str(exc)
            print(f"[driveguard] model loading failed: {exc}")

    # ── session lifecycle ────────────────────────────────────────────

    def begin_session(self):
        session_id = database.start_session()
        with self._session_lock:
            self.session_stats = SessionStats(session_id)
        return session_id

    def finish_session(self, session_id):
        with self._session_lock:
            stats = self.session_stats
            if stats is not None and stats.session_id == session_id:
                self.session_stats = None
            else:
                stats = None

        if stats is not None:
            summary = stats.summary()
        else:
            # Session not active in memory (e.g. backend restarted): rebuild
            # what we can from the alert rows.
            alerts = database.get_session_alerts(session_id)
            summary = {
                "total_drive_seconds": 0.0,
                "total_alerts": len(alerts),
                "caution_alerts": sum(1 for a in alerts if a["alert_type"] == "caution"),
                "danger_alerts": sum(1 for a in alerts if a["alert_type"] == "danger"),
                "avg_risk_score": round(
                    sum(a["risk_score"] for a in alerts) / len(alerts), 1
                )
                if alerts
                else 0.0,
                "peak_risk_score": max((a["risk_score"] for a in alerts), default=0.0),
                "peak_risk_timestamp": None,
                "dominant_emotion": "neutral",
            }

        row = database.end_session(session_id, summary)
        if row is None:
            return None
        summary["session_id"] = session_id
        summary["start_time"] = row["start_time"]
        summary["end_time"] = row["end_time"]
        return summary

    # ── capture pipeline ─────────────────────────────────────────────

    def client_connected(self):
        with self._client_lock:
            self.client_count += 1
            if self.capture_thread is None or not self.capture_thread.is_alive():
                self.camera_error = None
                self.capture_running = True
                self.capture_thread = threading.Thread(
                    target=self._capture_loop, daemon=True
                )
                self.capture_thread.start()

    def client_disconnected(self):
        with self._client_lock:
            self.client_count = max(0, self.client_count - 1)
            if self.client_count == 0:
                self.capture_running = False

    def _capture_loop(self):
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            cap.release()
            self.camera_error = (
                "Webcam not found. Check that a camera is connected, not in use "
                "by another application, and that camera permissions are enabled."
            )
            self.capture_running = False
            print(f"[driveguard] {self.camera_error}")
            return

        print("[driveguard] camera opened, pipeline running")
        try:
            while self.capture_running:
                ok, frame = cap.read()
                if not ok or frame is None:
                    time.sleep(0.05)
                    continue
                try:
                    payload = self._process_frame(frame)
                except Exception as exc:  # noqa: BLE001 - a bad frame must not kill the loop
                    print(f"[driveguard] frame processing failed: {exc}")
                    continue
                with self._latest_lock:
                    self._latest_payload = payload
        finally:
            cap.release()
            print("[driveguard] camera released")

    def _process_frame(self, frame):
        # The three detectors run concurrently; each works on the read-only
        # original and draws only on its own internal copy.
        f_drowsy = self.executor.submit(self.drowsiness.process, frame)
        f_emotion = self.executor.submit(self.emotion.process, frame)
        f_aggression = self.executor.submit(self.aggression.process, frame)
        d = f_drowsy.result()
        e = f_emotion.result()
        a = f_aggression.result()

        risk = self.risk_engine.compute(d["score"], e["score"], a["score"])
        alert = self.alert_system.check_and_alert(risk)

        with self._session_lock:
            stats = self.session_stats
        if stats is not None:
            stats.record(risk, e["dominant_emotion"])
            if alert["alert_triggered"]:
                stats.record_alert(risk["status"])
                database.log_alert(
                    stats.session_id,
                    risk,
                    {
                        "drowsiness_score": d["score"],
                        "aggression_score": a["score"],
                        "emotion_score": e["score"],
                        "dominant_emotion": e["dominant_emotion"],
                        "ear_value": d["ear"],
                    },
                )

        # Composite overlay: all three modules draw onto one shared frame.
        composite = frame.copy()
        self.drowsiness.annotate(composite)
        self.aggression.annotate(composite)
        self.emotion.annotate(composite)
        ok, jpeg = cv2.imencode(".jpg", composite, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
        frame_b64 = base64.b64encode(jpeg.tobytes()).decode("ascii") if ok else ""

        return {
            "risk_score": risk["risk_score"],
            "status": risk["status"],
            "color": risk["color"],
            "drowsiness": {
                "score": d["score"],
                "ear": d["ear"],
                "is_drowsy": d["is_drowsy"],
                "is_yawning": d["is_yawning"],
                "is_nodding": d["is_nodding"],
                "perclos": d["perclos"],
            },
            "emotion": {
                "score": e["score"],
                "dominant_emotion": e["dominant_emotion"],
                "confidence": e["confidence"],
            },
            "aggression": {
                "score": a["score"],
                "flow_magnitude": a["flow_magnitude"],
                "is_tailgating": a["is_tailgating"],
                "vehicle_distance": a["vehicle_distance"],
            },
            "alert": {
                "triggered": alert["alert_triggered"],
                "message": alert["alert_message"],
            },
            "frame": frame_b64,
            "timestamp": risk["timestamp"],
        }

    def latest_payload(self):
        with self._latest_lock:
            return self._latest_payload


manager = StreamManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    database.init_db()
    # Model loading takes tens of seconds (TF + torch); do it off the event
    # loop so /health responds immediately with models_loaded=false.
    threading.Thread(target=manager.load_models, daemon=True).start()
    yield
    manager.capture_running = False
    manager.alert_system.shutdown()


app = FastAPI(title="DriveGuard AI", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok", "models_loaded": manager.models_ready}


@app.post("/session/start")
async def session_start():
    return {"session_id": manager.begin_session()}


@app.post("/session/end/{session_id}")
async def session_end(session_id: str):
    summary = manager.finish_session(session_id)
    if summary is None:
        return {"error": f"session {session_id} not found"}
    return summary


@app.get("/session/{session_id}/alerts")
async def session_alerts(session_id: str):
    return {"alerts": database.get_session_alerts(session_id)}


@app.websocket("/ws/stream")
async def ws_stream(websocket: WebSocket):
    await websocket.accept()

    while not manager.models_ready:
        if manager.model_load_error:
            await websocket.send_json(
                {"error": f"Model loading failed: {manager.model_load_error}"}
            )
            await websocket.close()
            return
        await websocket.send_json({"status_message": "loading models..."})
        await asyncio.sleep(1.0)

    manager.client_connected()
    try:
        last_sent = None
        while True:
            if manager.camera_error:
                await websocket.send_json({"error": manager.camera_error})
                await websocket.close()
                return
            payload = manager.latest_payload()
            if payload is not None and payload is not last_sent:
                await websocket.send_json(payload)
                last_sent = payload
            await asyncio.sleep(SEND_INTERVAL_SECONDS)
    except WebSocketDisconnect:
        pass
    finally:
        manager.client_disconnected()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
