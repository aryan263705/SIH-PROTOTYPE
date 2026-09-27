import os
import cv2
import time
import json
import asyncio
import threading
import numpy as np
from typing import Optional, List, Dict, Any, Tuple

from fastapi import FastAPI, UploadFile, File, Form, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel

from backend.config import config, SNAPSHOTS_DIR, DEMO_VIDEOS_DIR
from backend.camera.stream_manager import StreamManager
from backend.detection.detector import PersonDetectorTracker
from backend.behavior.motion_analyzer import MotionAnalyzer
from backend.behavior.posture_heuristic import PostureHeuristic
from backend.behavior.boundary_analyzer import BoundaryAnalyzer
from backend.behavior.motion_gate import DualScaleMotionGate
from backend.behavior.slow_movement_analyzer import SlowMovementAnalyzer
from backend.behavior.tamper_detector import CameraTamperDetector
from backend.alerts.alert_engine import AlertEngine
from backend.alerts.replay_buffer import RollingEventReplayBuffer, REPLAYS_DIR
from backend.telemetry.edge_health import EdgeHealthMonitor
from backend.storage.db import get_recent_events, clear_events
from backend.pipeline import TrackMemory, analyze_frame, empty_telemetry

app = FastAPI(
    title="AI Border Surveillance Video Analytics",
    description="Smart India Hackathon SIH26187 Virtual Border Prototype API",
    version="3.0.0"
)

@app.on_event("startup")
def startup_event():
    print("[System] Initializing surveillance stream manager on startup...", flush=True)
    src_path = str(config.webcam_index) if config.source_type == "webcam" else (
        config.mobile_url if config.source_type == "mobile" else config.demo_video_filename
    )
    stream_manager.start(config.source_type, src_path)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/snapshots", StaticFiles(directory=str(SNAPSHOTS_DIR)), name="snapshots")
app.mount("/replays", StaticFiles(directory=str(REPLAYS_DIR)), name="replays")

stream_manager = StreamManager()
detector = PersonDetectorTracker(model_name=config.model_name)
motion_analyzer = MotionAnalyzer()
posture_heuristic = PostureHeuristic(
    aspect_ratio_thresh=config.aspect_ratio_threshold,
    score_thresh=config.posture_score_threshold
)
boundary_analyzer = BoundaryAnalyzer()
motion_gate = DualScaleMotionGate()
slow_movement_analyzer = SlowMovementAnalyzer()
tamper_detector = CameraTamperDetector()
replay_buffer = RollingEventReplayBuffer(max_seconds=30.0, target_fps=12.0)
alert_engine = AlertEngine(replay_buffer=replay_buffer)
edge_health = EdgeHealthMonitor()
track_memory = TrackMemory(timeout_seconds=config.track_lost_seconds)

pipeline_running = True
show_motion_roi = False
latest_annotated_jpeg = None
frame_lock = threading.Lock()
ws_lock = threading.Lock()
pending_ws_alerts: List[Dict[str, Any]] = []

current_telemetry = empty_telemetry(stream_manager.get_status(), detector.ai_online, detector.error_message)
current_telemetry["border_line"] = boundary_analyzer.border_line
current_telemetry["border_defined"] = boundary_analyzer.border_line is not None

active_websockets: List[WebSocket] = []


def _blank_standby_frame(message: str, detail: str = "") -> np.ndarray:
    blank = np.zeros((480, 640, 3), dtype=np.uint8)
    cv2.putText(blank, message, (70, 210), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (180, 180, 180), 2)
    cv2.putText(blank, "PERSONS DETECTED: 0", (70, 250), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (80, 200, 120), 1)
    cv2.putText(blank, "THREAT LEVEL: NORMAL", (70, 280), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (80, 200, 120), 1)
    if detail:
        cv2.putText(blank, detail[:70], (70, 320), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (70, 70, 180), 1)
    return blank


def draw_hud_overlay(
    frame,
    processed_persons,
    threat_level,
    border_line=None,
    roi_polygon=None,
    motion_roi=None,
    show_motion_roi=False,
    tamper_detected=False,
    tamper_reason="",
):
    annotated = frame.copy()
    h, w = annotated.shape[:2]

    # Draw Motion ROI if developer toggle is enabled
    if show_motion_roi and motion_roi:
        rx1, ry1, rx2, ry2 = motion_roi
        cv2.rectangle(annotated, (rx1, ry1), (rx2, ry2), (255, 230, 0), 2)
        cv2.putText(
            annotated,
            "MOTION ROI (EDGE OPTIMIZED)",
            (rx1 + 4, max(20, ry1 - 6)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.42,
            (255, 230, 0),
            1,
            cv2.LINE_AA,
        )

    if roi_polygon and len(roi_polygon) >= 3:
        roi_pts = np.array([[int(p[0] * w), int(p[1] * h)] for p in roi_polygon], dtype=np.int32)
        roi_layer = annotated.copy()
        cv2.fillPoly(roi_layer, [roi_pts], (0, 0, 180))
        cv2.addWeighted(roi_layer, 0.22, annotated, 0.78, 0, annotated)
        cv2.polylines(annotated, [roi_pts], True, (0, 0, 240), 2, cv2.LINE_AA)

    if border_line:
        p1 = (int(border_line[0][0] * w), int(border_line[0][1] * h))
        p2 = (int(border_line[1][0] * w), int(border_line[1][1] * h))
        cv2.line(annotated, p1, p2, (0, 215, 255), 3, cv2.LINE_AA)
        cv2.circle(annotated, p1, 5, (0, 255, 255), -1)
        cv2.circle(annotated, p2, 5, (0, 255, 255), -1)
        mid_x = (p1[0] + p2[0]) // 2
        mid_y = (p1[1] + p2[1]) // 2
        cv2.putText(annotated, "VIRTUAL BORDER LINE", (max(8, mid_x - 90), max(50, mid_y - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1, cv2.LINE_AA)

    live_count = sum(1 for p in processed_persons if p.get("track_status") != "LOST")
    if live_count == 0:
        cv2.putText(annotated, "NO PERSON DETECTED", (18, h - 28), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (160, 160, 160), 1, cv2.LINE_AA)

    # Tamper Alert Banner on camera HUD
    if tamper_detected:
        cv2.rectangle(annotated, (0, 32), (w, 64), (0, 0, 200), -1)
        cv2.putText(annotated, f"TAMPER ALERT: {tamper_reason.upper()}", (20, 54), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2, cv2.LINE_AA)

    bracket_col = (110, 110, 110)
    blen = 20
    cv2.line(annotated, (10, 10), (10 + blen, 10), bracket_col, 2)
    cv2.line(annotated, (10, 10), (10, 10 + blen), bracket_col, 2)
    cv2.line(annotated, (w - 10, 10), (w - 10 - blen, 10), bracket_col, 2)
    cv2.line(annotated, (w - 10, 10), (w - 10, 10 + blen), bracket_col, 2)
    cv2.line(annotated, (10, h - 10), (10 + blen, h - 10), bracket_col, 2)
    cv2.line(annotated, (10, h - 10), (10, h - 10 - blen), bracket_col, 2)
    cv2.line(annotated, (w - 10, h - 10), (w - 10 - blen, h - 10), bracket_col, 2)
    cv2.line(annotated, (w - 10, h - 10), (w - 10, h - 10 - blen), bracket_col, 2)

    bar_color = (15, 23, 42)
    cv2.rectangle(annotated, (0, 0), (w, 32), bar_color, -1)
    threat_color = (0, 200, 80) if threat_level in ("NORMAL", "OBSERVATION") else ((0, 180, 255) if threat_level == "SUSPICIOUS" else (0, 0, 230))
    cv2.circle(annotated, (20, 16), 6, threat_color, -1)
    cv2.putText(annotated, f"STATUS: {threat_level}", (34, 21), cv2.FONT_HERSHEY_SIMPLEX, 0.5, threat_color, 2)
    cv2.putText(annotated, f"PERSONS: {live_count}", (w // 2 - 40, 21), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (220, 220, 220), 1)
    now_str = time.strftime("%H:%M:%S")
    cv2.putText(annotated, f"T: {now_str}", (w - 110, 21), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (180, 180, 180), 1)

    for p in processed_persons:
        # Never draw phantom bounding boxes for tracks that have left the frame
        if p.get("track_status") == "LOST":
            continue

        x1, y1, x2, y2 = p["bbox"]
        tid = p["track_id"]
        posture = p["posture_label"]
        motion = p["movement_state"]
        conf = p["confidence"]
        approaching = p.get("approaching")
        in_restricted = p.get("in_restricted")
        has_alerted = p.get("has_alerted")
        crossing_pending = p.get("crossing_pending")

        if has_alerted:
            box_col = (0, 0, 235)  # Crimson Red
        elif crossing_pending or approaching or p.get("is_suspicious"):
            box_col = (0, 190, 240)  # Amber
        else:
            box_col = (0, 210, 80)  # Emerald Green

        cv2.rectangle(annotated, (x1, y1), (x2, y2), box_col, 2)
        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
        cv2.circle(annotated, (cx, cy), 4, (0, 255, 255), -1)

        prefix = f"PERSON #{tid}"

        if has_alerted:
            zone = "CROSSED INTO RESTRICTED ZONE"
        elif crossing_pending:
            zone = "BOUNDARY CROSSED [VERIFYING]"
        elif approaching:
            zone = "APPROACHING BORDER"
        else:
            zone = f"OUTSIDE ZONE • {motion}"

        label_line1 = f"{prefix}  {conf:.0f}%"
        label_line2 = f"{posture}"
        label_line3 = zone

        tag_bg_h = 48
        tag_y = max(34, y1 - tag_bg_h - 4)
        cv2.rectangle(annotated, (x1, tag_y), (x1 + 230, tag_y + tag_bg_h), (15, 23, 42), -1)
        cv2.rectangle(annotated, (x1, tag_y), (x1 + 230, tag_y + tag_bg_h), box_col, 1)
        cv2.putText(annotated, label_line1, (x1 + 6, tag_y + 14), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255), 1)
        cv2.putText(annotated, label_line2, (x1 + 6, tag_y + 28), cv2.FONT_HERSHEY_SIMPLEX, 0.38, box_col, 1)
        cv2.putText(annotated, label_line3[:34], (x1 + 6, tag_y + 42), cv2.FONT_HERSHEY_SIMPLEX, 0.34, (200, 200, 200), 1)

    return annotated


def _publish_alerts(new_alerts: List[Dict[str, Any]]):
    if not new_alerts:
        return
    with ws_lock:
        pending_ws_alerts.extend(new_alerts)


def analytics_worker():
    global latest_annotated_jpeg, current_telemetry

    print("[AI Worker] Analytics background thread started.")
    fps_timer = time.time()
    fps_count = 0
    calculated_fps = 0.0

    while pipeline_running:
        try:
            frame = stream_manager.get_latest_frame()
            stream_status = stream_manager.get_status()
            edge_health_data = edge_health.beat()

            if frame is None:
                msg = "CAMERA OFFLINE"
                if stream_status.get("status") in ("RECONNECTING", "ERROR", "CONNECTING"):
                    msg = "CAMERA CONNECTION LOST"
                blank = _blank_standby_frame(msg, stream_status.get("error_message") or "No stream")
                _, buf = cv2.imencode(".jpg", blank)
                raw_bytes = buf.tobytes()
                with frame_lock:
                    latest_annotated_jpeg = raw_bytes

                tel = empty_telemetry(stream_status, detector.ai_online, detector.error_message)
                tel["camera_online"] = False
                tel["border_line"] = boundary_analyzer.border_line
                tel["border_defined"] = boundary_analyzer.border_line is not None
                tel["roi_defined"] = len(boundary_analyzer.roi_polygon) >= 3
                tel["roi_polygon"] = boundary_analyzer.roi_polygon
                alert_engine.sync_with_live_tracks(set())
                tel["active_alerts_count"] = 0
                tel["edge_health"] = edge_health_data
                tel["telemetry_bandwidth"] = edge_health.get_bandwidth_summary()
                tel["show_motion_roi"] = show_motion_roi
                current_telemetry = tel
                time.sleep(0.05)
                continue

            processed_persons, analysis, new_alerts = analyze_frame(
                frame,
                detector,
                motion_analyzer,
                posture_heuristic,
                boundary_analyzer,
                alert_engine,
                track_memory,
                motion_gate=motion_gate,
                slow_movement_analyzer=slow_movement_analyzer,
                tamper_detector=tamper_detector,
                replay_buffer=replay_buffer,
            )
            _publish_alerts(new_alerts)

            # Measure evidence size if alert was generated
            for al in new_alerts:
                if al.get("snapshot"):
                    edge_health.measure_evidence_file(SNAPSHOTS_DIR / al["snapshot"])

            threat_level = analysis["threat_level"]
            annotated = draw_hud_overlay(
                frame,
                processed_persons,
                threat_level,
                border_line=boundary_analyzer.border_line,
                roi_polygon=boundary_analyzer.roi_polygon,
                motion_roi=analysis.get("motion_roi"),
                show_motion_roi=show_motion_roi,
                tamper_detected=analysis.get("tamper_detected", False),
                tamper_reason=analysis.get("tamper_reason", ""),
            )

            _, buf = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 80])
            raw_bytes = buf.tobytes()
            with frame_lock:
                latest_annotated_jpeg = raw_bytes

            fps_count += 1
            now = time.time()
            if now - fps_timer >= 1.0:
                calculated_fps = round(fps_count / (now - fps_timer), 1)
                fps_count = 0
                fps_timer = now

            live = analysis["persons_detected"]
            current_telemetry = {
                "camera_online": stream_manager.status == "ONLINE",
                "ai_online": detector.ai_online,
                "tracking_active": live > 0,
                "tracking_status": "TRACKING" if live > 0 else "READY",
                "fps": calculated_fps,
                "persons_detected": live,
                "active_alerts_count": analysis["active_alerts_count"],
                "threat_level": threat_level,
                "threat_score": analysis["threat_score"],
                "threat_reason": analysis["threat_reason"],
                "source_type": stream_manager.source_type,
                "source_status": stream_manager.status,
                "error_message": stream_manager.error_message or detector.error_message,
                "camera_message": "CAMERA ONLINE",
                "border_defined": boundary_analyzer.border_line is not None,
                "roi_defined": len(boundary_analyzer.roi_polygon) >= 3,
                "boundary_position": config.boundary_position,
                "monitored_direction": config.monitored_direction,
                "border_line": boundary_analyzer.border_line,
                "roi_polygon": boundary_analyzer.roi_polygon,
                "persons": processed_persons,
                "persistence_seconds": config.persistence_seconds,
                "motion_metrics": analysis.get("motion_metrics") or motion_gate.get_metrics(),
                "motion_roi": analysis.get("motion_roi"),
                "roi_active": bool(analysis.get("motion_metrics", {}).get("roi_active")),
                "show_motion_roi": show_motion_roi,
                "model_name": getattr(detector, "model_name", "yolov8s.pt"),
                "tamper_detected": analysis.get("tamper_detected", False),
                "tamper_reason": analysis.get("tamper_reason", ""),
                "factor_breakdown": analysis.get("factor_breakdown", []),
                "edge_health": edge_health_data,
                "telemetry_bandwidth": edge_health.get_bandwidth_summary(),
            }
            edge_health.measure_telemetry_packet(current_telemetry)
            time.sleep(0.01)
        except Exception as ex:
            print(f"[AI Worker Error] Exception in analytics loop: {ex}", flush=True)
            time.sleep(0.05)


worker_thread = threading.Thread(target=analytics_worker, daemon=True)
worker_thread.start()


def reset_analytics_state():
    detector.reset_tracker()
    motion_analyzer.tracks.clear()
    boundary_analyzer.track_positions.clear()
    motion_gate.reset()
    slow_movement_analyzer.reset()
    tamper_detector.reset()
    replay_buffer.clear()
    track_memory.reset()
    alert_engine.clear_active_alerts()


class CameraConfigRequest(BaseModel):
    source_type: str
    source_path: Optional[str] = ""


class SensitivityConfigRequest(BaseModel):
    posture_score_threshold: Optional[float] = None
    persistence_seconds: Optional[float] = None
    confidence_threshold: Optional[float] = None
    boundary_position: Optional[float] = None
    monitored_direction: Optional[str] = None


class BorderLineRequest(BaseModel):
    pt1: Optional[Tuple[float, float]] = None
    pt2: Optional[Tuple[float, float]] = None


class RoiPolygonRequest(BaseModel):
    polygon: Optional[List[Tuple[float, float]]] = None


@app.get("/api/status")
def get_status():
    return current_telemetry


@app.post("/api/camera/configure")
def configure_camera(req: CameraConfigRequest):
    config.source_type = req.source_type
    if req.source_path:
        if req.source_type == "mobile":
            config.mobile_url = req.source_path.strip()
        elif req.source_type == "demo":
            config.demo_video_filename = req.source_path
        elif req.source_type == "webcam":
            if str(req.source_path).isdigit():
                config.webcam_index = int(req.source_path)

    reset_analytics_state()
    stream_manager.start(req.source_type, req.source_path or "")
    return {
        "status": "success",
        "message": f"Switched stream source to {req.source_type}",
        "stream": stream_manager.get_status()
    }


@app.post("/api/camera/control")
def camera_control(action: str = Form(...)):
    if action == "start":
        source_path = config.mobile_url if config.source_type == "mobile" else (
            str(config.webcam_index) if config.source_type == "webcam" else config.demo_video_filename
        )
        stream_manager.start(config.source_type, source_path)
        return {"status": "started"}
    elif action == "stop":
        stream_manager.stop()
        reset_analytics_state()
        return {"status": "stopped"}
    return JSONResponse(status_code=400, content={"error": "Invalid action"})


@app.post("/api/zone/border")
def set_border_zone(req: BorderLineRequest):
    if req.pt1 and req.pt2:
        boundary_analyzer.set_border_line(req.pt1, req.pt2)
        return {"status": "defined", "border_line": [req.pt1, req.pt2]}
    else:
        boundary_analyzer.clear_border_line()
        return {"status": "cleared"}


@app.post("/api/zone/roi")
def set_roi_zone(req: RoiPolygonRequest):
    if req.polygon and len(req.polygon) >= 3:
        boundary_analyzer.set_roi_polygon(req.polygon)
        return {"status": "defined", "polygon": req.polygon}
    else:
        boundary_analyzer.clear_roi_polygon()
        return {"status": "cleared"}


@app.post("/api/zone/clear")
def clear_all_zones():
    boundary_analyzer.clear_roi_polygon()
    boundary_analyzer.set_boundary_position(config.boundary_position)
    return {"status": "cleared", "border_line": boundary_analyzer.border_line}


@app.post("/api/reset_demo")
def reset_demo():
    boundary_analyzer.reset()
    alert_engine.clear_active_alerts()
    clear_events()
    detector.reset_tracker()
    track_memory.reset()
    motion_analyzer.tracks.clear()
    return {"status": "success", "message": "Demo state reset completely."}


@app.post("/api/process_frame")
async def process_browser_frame(file: UploadFile = File(...)):
    """Optional fallback. Authoritative live path is the analytics worker + MJPEG feed."""
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if frame is None or frame.size == 0:
        return JSONResponse(status_code=400, content={"error": "Invalid image frame"})

    processed_persons, analysis, new_alerts = analyze_frame(
        frame,
        detector,
        motion_analyzer,
        posture_heuristic,
        boundary_analyzer,
        alert_engine,
        track_memory,
    )
    _publish_alerts(new_alerts)

    return {
        "threat_level": analysis["threat_level"],
        "persons": processed_persons,
        "persons_detected": analysis["persons_detected"],
        "new_alerts": new_alerts,
        "active_alerts_count": analysis["active_alerts_count"],
        "border_line": boundary_analyzer.border_line,
        "roi_polygon": boundary_analyzer.roi_polygon,
        "threat_score": analysis["threat_score"],
        "threat_reason": analysis["threat_reason"],
        "ai_online": detector.ai_online,
        "ai_error": detector.error_message,
        "model_name": detector.model_name,
    }


@app.get("/api/alerts")
def get_alerts():
    return alert_engine.get_active_alerts()


@app.post("/api/alerts/clear")
def clear_alerts():
    alert_engine.clear_active_alerts()
    return {"status": "cleared"}


@app.get("/api/events")
def get_events(limit: int = 50):
    return get_recent_events(limit=limit)


@app.post("/api/events/clear")
def clear_event_history():
    clear_events()
    return {"status": "cleared"}


@app.get("/api/config")
def get_pipeline_config():
    return {
        "source_type": config.source_type,
        "mobile_url": config.mobile_url,
        "webcam_index": config.webcam_index,
        "confidence_threshold": config.confidence_threshold,
        "posture_score_threshold": posture_heuristic.score_thresh,
        "persistence_seconds": config.persistence_seconds,
        "model_name": config.model_name,
        "boundary_position": config.boundary_position,
        "monitored_direction": config.monitored_direction,
        "border_line": boundary_analyzer.border_line,
        "ai_online": detector.ai_online,
        "ai_error": detector.error_message,
    }


@app.post("/api/config")
def update_pipeline_config(req: SensitivityConfigRequest):
    if req.posture_score_threshold is not None:
        posture_heuristic.score_thresh = req.posture_score_threshold
        config.posture_score_threshold = req.posture_score_threshold
    if req.persistence_seconds is not None:
        config.persistence_seconds = req.persistence_seconds
    if req.confidence_threshold is not None:
        config.confidence_threshold = req.confidence_threshold
    if req.boundary_position is not None:
        boundary_analyzer.set_boundary_position(req.boundary_position, req.monitored_direction)
    elif req.monitored_direction is not None:
        boundary_analyzer.set_boundary_position(config.boundary_position, req.monitored_direction)
    return {"status": "updated", "config": get_pipeline_config()}


@app.post("/api/upload_video")
async def upload_video(file: UploadFile = File(...)):
    file_path = DEMO_VIDEOS_DIR / file.filename
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)

    config.demo_video_filename = file.filename
    return {"status": "success", "filename": file.filename}


@app.post("/api/debug/toggle_motion_roi")
def toggle_motion_roi():
    global show_motion_roi
    show_motion_roi = not show_motion_roi
    current_telemetry["show_motion_roi"] = show_motion_roi
    return {"status": "success", "show_motion_roi": show_motion_roi}


class ModelSwitchRequest(BaseModel):
    model_name: str  # "yolov8s.pt" or "yolov8n.pt"


@app.post("/api/model/switch")
def switch_yolo_model(req: ModelSwitchRequest):
    ok = detector.switch_model(req.model_name)
    current_telemetry["model_name"] = detector.model_name
    return {
        "status": "success" if ok else "error",
        "model_name": detector.model_name,
        "ai_online": detector.ai_online,
        "imgsz": config.inference_imgsz,
    }


@app.get("/api/edge/health")
def get_edge_health():
    return {
        "health": edge_health.beat(),
        "bandwidth": edge_health.get_bandwidth_summary(),
        "motion_gating": motion_gate.get_metrics(),
    }


async def mjpeg_generator(request: Request):
    try:
        while not await request.is_disconnected():
            with frame_lock:
                frame_data = latest_annotated_jpeg

            if frame_data is not None:
                yield (b"--frame\r\n"
                       b"Content-Type: image/jpeg\r\n\r\n" + frame_data + b"\r\n")
            await asyncio.sleep(0.033)
    except (asyncio.CancelledError, GeneratorExit):
        pass
    except Exception:
        pass


@app.get("/api/video/feed")
async def video_feed(request: Request):
    return StreamingResponse(
        mjpeg_generator(request),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_websockets.append(websocket)
    try:
        while True:
            outgoing = []
            with ws_lock:
                if pending_ws_alerts:
                    outgoing = list(pending_ws_alerts)
                    pending_ws_alerts.clear()

            payload = {
                "type": "TELEMETRY",
                "telemetry": current_telemetry,
                "recent_alerts": alert_engine.get_active_alerts()[:5],
            }
            await websocket.send_text(json.dumps(payload, default=str))
            for alert in outgoing:
                await websocket.send_text(json.dumps(alert, default=str))
            await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        if websocket in active_websockets:
            active_websockets.remove(websocket)
    except Exception:
        if websocket in active_websockets:
            active_websockets.remove(websocket)
