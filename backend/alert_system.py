"""Audio alerts via pyttsx3, spoken from a dedicated worker thread."""

import queue
import threading
import time

ALERT_MESSAGES = {
    "caution": "Warning: Please stay focused while driving.",
    "danger": "Alert! High risk detected. Please pull over safely.",
}

ALERT_COOLDOWN_SECONDS = 10.0


class AlertSystem:
    def __init__(self):
        self.last_alert_time = 0.0
        self.last_alert_message = ""
        self._speech_queue = queue.Queue()
        self._worker = threading.Thread(target=self._speech_loop, daemon=True)
        self._worker.start()

    def _speech_loop(self):
        """Own the pyttsx3 engine on one thread; it is not thread-safe."""
        while True:
            message = self._speech_queue.get()
            if message is None:
                return
            try:
                import pyttsx3

                # A fresh engine per utterance avoids the "run loop already
                # started" failure mode after repeated runAndWait() calls.
                engine = pyttsx3.init()
                engine.say(message)
                engine.runAndWait()
                engine.stop()
            except Exception as exc:  # noqa: BLE001 - audio must never crash the pipeline
                print(f"[alert] TTS failed: {exc}")

    def check_and_alert(self, risk_result):
        status = risk_result.get("status", "safe")
        if not risk_result.get("should_alert") or status not in ALERT_MESSAGES:
            return {"alert_triggered": False, "alert_message": ""}

        message = ALERT_MESSAGES[status]
        now = time.monotonic()
        if message == self.last_alert_message and now - self.last_alert_time < ALERT_COOLDOWN_SECONDS:
            return {"alert_triggered": False, "alert_message": ""}

        self.last_alert_time = now
        self.last_alert_message = message
        self._speech_queue.put(message)
        return {"alert_triggered": True, "alert_message": message}

    def shutdown(self):
        self._speech_queue.put(None)
