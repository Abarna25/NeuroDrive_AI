# 🛡️ DriveGuard AI

Real-time **Driver Cognitive State Monitor**: a webcam/dashcam feed is analyzed by
three computer-vision modules — **drowsiness**, **aggression**, and **emotion** —
whose outputs are blended into a unified 0–100 risk score, streamed live to a
React dashboard with audio + visual alerts and per-session reporting.

## Architecture

```
                ┌────────────────────────── backend (Python / FastAPI, :8000) ─────────────────────────┐
                │                                                                                       │
 ┌─────────┐    │  ┌──────────────┐      ┌────────────────────────────────┐     ┌──────────────┐        │
 │ Webcam  │───►│  │ Capture      │─────►│ ThreadPoolExecutor (3 workers) │────►│ RiskEngine   │        │
 └─────────┘    │  │ thread       │      │  ├─ DrowsinessDetector         │     │ 0.40 drowsy  │        │
                │  │ (cv2)        │      │  │   MediaPipe FaceMesh        │     │ 0.35 emotion │        │
                │  └──────────────┘      │  │   EAR·MAR·PERCLOS·head-nod  │     │ 0.25 aggro   │        │
                │                        │  ├─ EmotionDetector            │     └──────┬───────┘        │
                │                        │  │   DeepFace (every 5 frames) │            │                │
                │                        │  └─ AggressionDetector         │     ┌──────▼───────┐        │
                │                        │      Farneback optical flow    │     │ AlertSystem  │        │
                │                        │      YOLOv8n tailgating        │     │ pyttsx3 TTS  │        │
                │                        │      MiDaS depth (optional)    │     │ 10s cooldown │        │
                │                        └────────────────────────────────┘     └──────┬───────┘        │
                │                                                                      │                │
                │      ┌───────────────┐        ┌────────────────────┐          ┌──────▼───────┐        │
                │      │ WebSocket     │◄───────│ latest-result slot │          │ SQLite       │        │
                │      │ /ws/stream    │        │ (composite JPEG +  │          │ (SQLAlchemy) │        │
                │      │ ≤10 FPS JSON  │        │  module metrics)   │          │ sessions +   │        │
                │      └──────┬────────┘        └────────────────────┘          │ alert_events │        │
                └─────────────┼─────────────────────────────────────────────────┴──────────────┴────────┘
                              │
                ┌─────────────▼────────── frontend (React + TS + Vite + Tailwind, :5173) ────────┐
                │  VideoFeed · RiskGauge · RiskChart · ModuleStatus · AlertLog · SessionSummary  │
                └─────────────────────────────────────────────────────────────────────────────────┘
```

## Setup

### Prerequisites
- **Python 3.11** (mediapipe 0.10.14 does not support 3.12+)
- **Node.js 18+**
- A webcam
- Internet access **for first run only** (model weight downloads — see below)

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows   (source .venv/bin/activate on macOS/Linux)
pip install -r requirements.txt
python main.py                  # serves on http://localhost:8000
```

On first startup the backend downloads model weights and caches them locally:
- `yolov8n.pt` (~6 MB, saved next to `main.py`)
- MiDaS_small via `torch.hub` (~80 MB, cached in `~/.cache/torch`)
- DeepFace emotion weights (~5 MB, cached in `~/.deepface`)

After that everything runs **fully offline** — there are no runtime API calls.

Model loading takes 20–60 s; poll `GET /health` until `models_loaded: true`.

### Frontend

```bash
cd frontend
npm install
npm run dev                     # serves on http://localhost:5173
```

Open http://localhost:5173, wait for the LIVE badge, then click **Start Session**.

### Tests

```bash
cd backend
.venv\Scripts\python -m pytest tests/test_logic.py            # fast: risk/alert/db/math
.venv\Scripts\python -m pytest tests/test_smoke_detectors.py  # slow: loads all CV models
```

## API

| Endpoint | Method | Purpose |
|---|---|---|
| `/ws/stream` | WS | Live JSON stream: risk score, module metrics, base64 JPEG frame (≤10 FPS) |
| `/session/start` | POST | Create a session, returns `{ session_id }` |
| `/session/end/{id}` | POST | End session, returns summary stats |
| `/session/{id}/alerts` | GET | All alert events for a session |
| `/health` | GET | `{ status, models_loaded }` |

## How scoring works

- **Drowsiness (weight 0.40)** — eyes closed (EAR < 0.25) +0.4 · PERCLOS > 70 %
  over 3 s +0.35 · yawn (MAR > 0.6, 3+ frames) +0.15 · head nod (pitch > 20°) +0.10
- **Emotion (weight 0.35)** — DeepFace dominant emotion mapped to a risk weight
  (angry 1.0 → happy 0.0), exponentially smoothed (0.7 previous / 0.3 new)
- **Aggression (weight 0.25)** — optical-flow magnitude (up to 0.4) · tailgating
  vehicle bbox +0.35 · MiDaS depth proximity +0.25

Risk = weighted sum × 100 → **0–30 safe · 31–60 caution · 61–100 danger**.
Entering caution/danger fires a spoken alert (10 s cooldown) and logs to SQLite.

## Graceful degradation

| Failure | Behavior |
|---|---|
| No face in frame | Neutral drowsiness/emotion values, no crash |
| DeepFace fails on a frame | Last known emotion is reused |
| MiDaS can't download | Depth check disabled; YOLO + optical flow still run |
| YOLO can't download | Vehicle detection disabled; optical flow still runs |
| TTS engine fails | Alert still shows in dashboard; audio silently skipped |
| Webcam missing | WebSocket sends a clear error message shown in the UI |

## Troubleshooting

**"Webcam not found"** — close other apps using the camera (Zoom, Teams,
browser tabs); check Windows Settings → Privacy → Camera → allow desktop apps.
If your camera is not device 0, change `cv2.VideoCapture(0)` in
`backend/main.py`.

**Model download failures on first run** — the backend needs internet once.
Behind a proxy, set `HTTPS_PROXY` before starting. You can pre-download
`yolov8n.pt` from the Ultralytics release page and drop it in `backend/`.

**Port already in use** — something else is on 8000/5173. Either stop it
(`netstat -ano | findstr :8000` then kill the PID) or change the port in
`backend/main.py` and `frontend/src/types.ts` (`API_BASE`/`WS_URL`), plus
`frontend/vite.config.ts` for 5173.

**mediapipe install fails** — you're likely on Python 3.12+. Install Python
3.11 and recreate the venv.

**Dashboard stuck on "Connecting"** — backend still loading models; check
`GET http://localhost:8000/health`. The frontend retries every 3 s (max 5
retries) — refresh the page after the backend is up.

**Very low FPS** — everything runs on CPU. Close background apps; the pipeline
already throttles DeepFace (every 5th frame) and YOLO/MiDaS (every 3rd frame).

**No alert audio** — pyttsx3 uses Windows SAPI5; check system volume and
default output device. Alerts still appear in the Alert Log regardless.
