# AI-Based Intelligent Video Analytics for Border Surveillance

**Smart India Hackathon Project**  
**Problem Statement ID:** SIH26187  
**Team Name:** AI Avengers  
**Classification:** Restricted Border Perimeter Monitoring Prototype  

---

## 1. Overview

This prototype demonstrates how existing CCTV infrastructure (or simulated edge cameras such as mobile phones) can be augmented with real-time autonomous edge AI to detect, track, and analyze human behavior along border perimeters.

The system features real-time **Person Detection**, **ByteTrack Persistent Tracking**, **Kinematics & Movement Analysis**, and a computer-vision heuristic for **Crawling / Low-Posture Breach Detection** with **Temporal Persistence Alert Filtering** and **Forensic Evidence Snapshots**.

```text
CAMERA / VIDEO STREAM
         ↓
    OPEN_CV DECODE
         ↓
  MOTION PRE-FILTER
         ↓
YOLOv8 PERSON DETECTION
         ↓
   BYTETRACK RE-ID
         ↓
 KINEMATICS ANALYSIS
         ↓
   POSTURE HEURISTIC (Aspect Ratio w/h + Ground Plane)
         ↓
TEMPORAL ALERT ENGINE (Persistence Check)
         ↓
EVIDENCE CAPTURE (Annotated Snapshot + SQLite Audit Log)
         ↓
COMMAND CENTER DASHBOARD (React + Tailwind HUD)
```

---

## 2. Core Implemented Features

### Live Camera & Video Ingestion
* **Mobile Phone Camera:** Stream live video from any phone running an IP camera application over Wi-Fi (`http://PHONE_IP:PORT/video`).
* **Laptop Webcam:** Fallback to device camera (index `0`) for instant testing.
* **Prerecorded / Demo Mode:** Looping surveillance video featuring normal walking transitioning into crawling intrusion for presentations.
* **Custom MP4 Upload:** Upload any surveillance video directly from the dashboard.

### Computer Vision & AI Analytics
* **YOLOv8 Person Detection:** Lightweight nano model (`yolov8n.pt`) filtered to class `person` for maximum real-time edge frame rates.
* **ByteTrack Persistent Re-ID:** Assigns persistent IDs (`#01`, `#02`, etc.) to tracked targets across frame occlusions.
* **Kinematics Analysis:** Measures displacement over time to determine movement state (`STATIONARY`, `WALKING`, `SLOW MOVEMENT`, `RAPID MOVEMENT`) and heading direction.
* **Crawling / Low-Posture Detection:** Practical aspect-ratio heuristic ($AR = \frac{\text{width}}{\text{height}}$). Standard upright human ($AR \approx 0.35 - 0.50$); crouching or crawling ($AR \ge 0.85 - 1.10$). Combined with vertical ground proximity to calculate a continuous **0–100% Behavior Score**.
* **False Alert Reduction:** Multi-frame temporal persistence engine prevents single-frame glitches from firing alerts. Behavior must persist for a configurable duration (default: $2.0$ seconds).
* **Alert Engine:** Categorizes threats into `🚨 POSSIBLE INTRUSION`, `⚠️ SUSPICIOUS MOVEMENT`, and `⚠️ LOW POSTURE`.
* **Automated Evidence Snapshots:** Full-resolution frames annotated with tactical bounding boxes, target IDs, behavior scores, and timestamps saved to disk (`snapshots/`).
* **SQLite Audit Log:** Structured local storage for incidents, telemetry, and forensic reviews.

### Command Center Dashboard
* Dark tactical surveillance theme with real-time indicators: `● CAMERA ONLINE`, `● AI ENGINE ONLINE`, `● TRACKING ACTIVE`.
* Live video feed with tactical corner crosshairs, target bounding boxes, and posture tags.
* Threat level badge: `NORMAL` (Green), `⚠️ SUSPICIOUS` (Amber), `🚨 ALERT` (Red).
* Interactive Alert Ticker and Evidence Inspection Modal.
* Filterable Incident History table.
* On-the-fly sensitivity tuning sliders (Posture Threshold, Persistence Duration, YOLO Confidence).
* Dedicated **System Architecture** visualizer.

---

## 3. Technology Stack

* **AI & Vision:** Python 3.13, OpenCV 5.0, Ultralytics YOLOv8, PyTorch, ByteTrack
* **Backend:** FastAPI, Uvicorn, SQLite3, NumPy
* **Frontend:** React 19, Vite, Tailwind CSS v4, Lucide React Icons

---

## 4. Quick Start

### Prerequisites
* **Python:** 3.10+ (Python 3.13 supported)
* **Node.js:** v18+ and `npm`

### Fast Launch (Windows)
Double-click:
1. `run_backend.bat` (Starts FastAPI backend bound to `0.0.0.0:8000`)
2. `run_frontend.bat` (Starts React dashboard on `http://localhost:5173`)

Or run the PowerShell launcher:
```powershell
.\run_prototype.ps1
```
Open **[http://localhost:5173](http://localhost:5173)** in your browser.

---

### Manual Launch

#### Terminal 1 — Backend:
```bash
# Activate virtual environment
.\venv\Scripts\activate

# Install dependencies (if not already installed)
pip install -r requirements.txt

# Start backend server bound to 0.0.0.0 for LAN access
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

#### Terminal 2 — Frontend:
```bash
cd frontend

# Install npm dependencies (if not already installed)
npm install

# Start Vite dev server accessible from LAN
npm run dev -- --host
```
Navigate to **[http://localhost:5173](http://localhost:5173)** on your laptop.

---

## 5. Mobile Dashboard & Camera Access Over Local Wi-Fi (LAN)

The system is configured so you can operate the surveillance dashboard from a mobile phone or another laptop on the same local Wi-Fi network:

1. **Connect to Same Wi-Fi:** Ensure both your laptop and mobile phone are connected to the exact same Wi-Fi network (or connect your phone to your laptop's Mobile Hotspot).
2. **Find Laptop Local IP:** On your laptop, open Command Prompt or PowerShell and run:
   ```cmd
   ipconfig
   ```
   Look for the **IPv4 Address** under your active Wi-Fi adapter (e.g. `192.168.1.105`).
3. **Open Dashboard on Phone:** Open a mobile browser (Chrome/Safari) on your phone and go to:
   ```
   http://<YOUR_LAPTOP_IP>:5173
   ```
   *(Example: `http://192.168.1.105:5173`)*
4. **Mobile Camera Ingestion:**
   * Install an IP camera app on your phone (e.g., *IP Webcam* on Android or *Live-Reporter* on iOS).
   * Start the camera stream in the app (e.g., `http://192.168.1.50:8080/video`).
   * In the dashboard toolbar, select **Mobile Camera (IP Stream)**, enter the URL, and click **CONNECT**.
   * When the camera provides frames, status immediately displays **CAMERA ONLINE**. If disconnected, it safely shows **CAMERA CONNECTION LOST** without generating false alerts.

---

## 6. Configurable Virtual Border & Presentation Demo Scenario

### Virtual Border Line
* **Horizontal Virtual Border Line:** Drawn across the surveillance viewport.
* **Configurable Position:** Move the **Boundary Position** slider in the toolbar (default: **65%**) or click **DEFINE BORDER** to click two custom endpoints.
* **Monitored Direction:** TOP → BOTTOM (Outside is above the boundary line; Restricted Zone is below the line).
* **Core Principles:**
  - **NO PERSON = NO ALERT:** When the camera view is empty, detections = 0, alerts = 0, threat = NORMAL.
  - **PERSON DETECTED ≠ INTRUSION:** A person in the safe zone is tracked with green bounding box and NORMAL status.
  - **APPROACHING BORDER:** As the person approaches the boundary, status becomes SUSPICIOUS (no alert yet).
  - **LINE CROSSING & TEMPORAL PERSISTENCE:** When the person crosses the virtual border into the restricted zone, a 2.0-second persistence timer starts. If the person steps back before 2.0s, the pending alert cancels. Only if the breach persists for 2.0s is a **POSSIBLE INTRUSION** alert generated, evidence snapshot captured, and logged to history.
  - **ALERT COOLDOWN:** Exactly 1 alert is generated per breach—no alert spam every frame.

### 7-Scene SIH Presentation Walkthrough
1. **Scene 1 (Camera Empty):** Camera online, persons detected: 0, active alerts: 0, threat level: NORMAL. Area secure.
2. **Scene 2 (Person Enters):** Person #01 enters in safe zone. YOLO confidence ~85%, tracking active, threat level: NORMAL.
3. **Scene 3 (Approaching Border):** Person #01 approaches the virtual border. Status: APPROACHING BORDER, threat level: SUSPICIOUS, still 0 alerts.
4. **Scene 4 (Border Crossing):** Person crosses the horizontal border into the restricted zone. Status: BOUNDARY CROSSING DETECTED. 2.0-second persistence timer starts.
5. **Scene 5 (Validated Intrusion):** Condition persists for 2.0s. Confirmed alert `🚨 POSSIBLE INTRUSION` fires with explainable threat score (e.g. 88%).
6. **Scene 6 (Forensic Evidence):** Click **View Evidence** on the alert card or in the audit trail to inspect the captured snapshot with tactical overlays.
7. **Scene 7 (Audit Trail):** Event is permanently logged in the Incident Audit Trail table. Alert cooldown prevents duplicate spam.

---

## 7. Camera Input Modes

### Option A: Laptop Webcam
1. Under **SOURCE**, select **Laptop Webcam (Live)**.
2. Status reflects real webcam availability (CAMERA ONLINE / OFFLINE).

### Option B: Mobile Phone Camera
1. Under **SOURCE**, select **Mobile Camera (IP Stream)**.
2. Enter your phone's stream URL and click **CONNECT**.

### Option C: Demo Mode (Guaranteed Offline Presentation)
1. Under **SOURCE**, select **Video File (Demo Mode)**.
2. Runs `border_patrol_demo.mp4` through the exact same real YOLOv8 + ByteTrack pipeline demonstrating all 7 presentation scenes.

---

## 6. Project Structure

```
SIH Prototype/
├── backend/
│   ├── main.py                     # FastAPI application, REST endpoints, MJPEG & WebSockets
│   ├── config.py                   # Central settings, paths, and thresholds
│   ├── camera/
│   │   └── stream_manager.py       # Threaded capture supporting Mobile IP, Webcam, Video
│   ├── detection/
│   │   └── detector.py             # YOLOv8n detector with ByteTrack tracker
│   ├── behavior/
│   │   ├── motion_analyzer.py      # Kinematic speed, displacement, and direction
│   │   └── posture_heuristic.py    # Aspect ratio (w/h), ground proximity, score (0-100)
│   ├── alerts/
│   │   ├── alert_engine.py         # Temporal persistence, threshold checks, cooldown
│   │   └── snapshot.py             # Forensic evidence snapshot generator
│   ├── storage/
│   │   └── db.py                   # SQLite storage for incidents and events
│   └── utils/
│       └── demo_generator.py       # Calibrated demo video generator
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Header.jsx          # Live indicators (Camera, AI, Tracking)
│   │   │   ├── VideoFeed.jsx       # Tactical surveillance player with HUD overlays
│   │   │   ├── StatusPanel.jsx     # System metrics, FPS, threat badges, active tracks
│   │   │   ├── CameraControl.jsx   # Source switcher, mobile IP input, tuning sliders
│   │   │   ├── AlertPanel.jsx      # Real-time alert card feed
│   │   │   ├── SnapshotModal.jsx   # High-resolution evidence viewer
│   │   │   └── EventHistory.jsx    # Filterable incident audit trail
│   │   ├── pages/
│   │   │   ├── Dashboard.jsx       # Main Command Console
│   │   │   └── Architecture.jsx    # 8-stage interactive pipeline visualizer
│   │   └── services/
│   │       └── api.js              # REST client
│   └── package.json
├── demo/
│   └── videos/
│       └── border_patrol_demo.mp4  # Offline presentation video
├── models/
│   └── yolov8n.pt                  # YOLOv8 nano neural network weights
├── snapshots/                      # Captured forensic evidence snapshots
├── requirements.txt
├── run_backend.bat                 # 1-click backend launcher
├── run_frontend.bat                # 1-click frontend launcher
├── run_prototype.ps1               # Unified PowerShell launcher
└── README.md
```

---

## 7. Troubleshooting

| Issue | Cause | Solution |
| :--- | :--- | :--- |
| **Mobile camera fails to connect** | Phone and laptop on different subnets or incorrect URL | Verify phone and laptop are on the same Wi-Fi. Check if URL ends with `/video` (e.g. `http://192.168.1.15:8080/video`). |
| **Webcam not opening** | Camera in use by another app (e.g., Zoom/Teams) | Close other applications accessing the webcam. Ensure Windows camera privacy permissions are enabled. |
| **Low FPS on battery power** | Laptop in power-saver mode | Plug in laptop charger or reduce inference image size in `backend/config.py` (`inference_imgsz = 480`). |
| **False crawling alerts on normal walking** | Threshold set too low or camera angled too high | Increase *Posture Suspicion Trigger* slider to $70\%$ or increase *Alert Persistence* to $3.0\text{s}$ in the dashboard. |

---

## 8. Hackathon Presentation Checklist

- [x] Live camera switching (Mobile Phone $\leftrightarrow$ Webcam $\leftrightarrow$ Demo Video)
- [x] Real-time YOLOv8 person detection with bounding boxes and confidence
- [x] ByteTrack persistent ID tracking
- [x] Kinematics movement classification (`STATIONARY`, `WALKING`, `SLOW MOVEMENT`)
- [x] Aspect-ratio crawling & low-posture detection heuristic
- [x] False alert reduction via multi-frame temporal persistence ($2.0\text{s}$)
- [x] Evidence snapshots captured to disk with forensic metadata
- [x] Live SQLite incident audit trail
- [x] Professional dark command-center UI with 0 fake data
- [x] Dedicated System Architecture visualization page
