# NeuroDrive AI - Setup and Usage Guide

This guide provides step-by-step instructions on how to set up, run, and use the NeuroDrive AI project.

## 1. Prerequisites

Before you begin, ensure you have the following installed on your system:
- **Python 3.11** (Required: MediaPipe 0.10.14 does not support Python 3.12+)
- **Node.js 18+** (For the React frontend)
- A working **Webcam** or **Dashcam** connected to your computer
- **Internet access** (Required only for the first run to download ML model weights)

## 2. Backend Setup (FastAPI & Python)

The backend handles the camera feed, computer vision models, and WebSocket streaming.

1. **Open a terminal** and navigate to the backend directory:
   ```bash
   cd backend
   ```
2. **Create a virtual environment**:
   ```bash
   python -m venv .venv
   ```
3. **Activate the virtual environment**:
   - **Windows**:
     ```bash
     .venv\Scripts\activate
     ```
   - **macOS / Linux**:
     ```bash
     source .venv/bin/activate
     ```
4. **Install the required dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
5. **Run the backend server**:
   ```bash
   python main.py
   ```
   *The server will start on `http://localhost:8000`.*

> **First Run Note:** On the first startup, the backend will download necessary model weights (YOLOv8, MiDaS, DeepFace). This requires an internet connection and might take a minute or two. Subsequent runs will be completely offline and much faster. 
> Wait until you see `[neurodrive] all models loaded` in the console before starting the frontend session.

## 3. Frontend Setup (React & Vite)

The frontend provides the real-time dashboard, risk gauge, and alert logs.

1. **Open a new terminal window** (keep the backend running) and navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. **Install Node.js dependencies**:
   ```bash
   npm install
   ```
3. **Start the development server**:
   ```bash
   npm run dev
   ```
   *The frontend will start on `http://localhost:5173`.*

## 4. Usage Instructions

1. **Open the Dashboard**: Open your web browser and go to [http://localhost:5173](http://localhost:5173).
2. **Verify Connection**: Wait for the "LIVE" badge to appear, indicating that the frontend has successfully connected to the backend via WebSockets.
3. **Start a Session**: Click the **Start Session** button on the dashboard.
4. **Monitoring**:
   - The system will activate your webcam and start analyzing the feed.
   - You will see real-time updates on the **Risk Gauge**, **Module Statuses** (Drowsiness, Emotion, Aggression), and the composite **Risk Chart**.
   - If the system detects high risk (e.g., drowsiness or aggression), it will trigger visual alerts on the dashboard and spoken audio alerts.
5. **End Session**: Click the **End Session** button to stop monitoring. A summary of the session will be generated and saved.

## Troubleshooting

- **Webcam not found**: Ensure no other applications (like Zoom or Teams) are using the camera. Check your OS privacy settings to allow desktop apps to access the camera.
- **Port already in use**: If ports `8000` or `5173` are in use, you will need to stop the conflicting service or change the ports in both `backend/main.py` and `frontend/vite.config.ts`.
- **"Connecting" stuck on dashboard**: Make sure the backend has fully loaded all AI models. You can check the backend health by visiting `http://localhost:8000/health` in your browser.
