import time
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

from backend.config import config
from backend.alerts.alert_engine import compute_threat_score, get_factor_breakdown


class TrackMemory:
    """Holds recently seen tracks so they persist smoothly across brief occlusions."""

    def __init__(self, timeout_seconds: float = 2.5, grace_seconds: float = 1.2):
        self.timeout_seconds = timeout_seconds
        self.grace_seconds = grace_seconds
        self.records: Dict[str, Dict[str, Any]] = {}

    def update(self, detections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        now = time.time()
        seen = set()
        for det in detections:
            tid = det["track_id"]
            seen.add(tid)
            self.records[tid] = {
                "detection": det,
                "last_seen": now,
                "status": "ACTIVE",
            }

        expired = []
        for tid, rec in self.records.items():
            if tid in seen:
                continue
            time_since = now - rec["last_seen"]
            if time_since > self.timeout_seconds:
                expired.append(tid)
            elif time_since > self.grace_seconds:
                rec["status"] = "LOST"
            else:
                # Still within brief occlusion/motion-gate grace period — keep ACTIVE
                rec["status"] = "ACTIVE"

        for tid in expired:
            del self.records[tid]

        return detections

    def active_ids(self) -> List[str]:
        return [tid for tid, rec in self.records.items() if rec["status"] == "ACTIVE"]

    def active_detections(self) -> List[Dict[str, Any]]:
        return [rec["detection"] for rec in self.records.values() if rec["status"] == "ACTIVE"]

    def display_tracks(self) -> List[Dict[str, Any]]:
        out = []
        for tid, rec in self.records.items():
            item = dict(rec["detection"])
            item["track_status"] = rec["status"]
            out.append(item)
        return out

    def reset(self):
        self.records.clear()


def empty_telemetry(stream_status: Dict[str, Any], ai_online: bool, ai_error: str = "") -> Dict[str, Any]:
    camera_online = stream_status.get("status") == "ONLINE"
    reconnecting = stream_status.get("status") in ("RECONNECTING", "ERROR", "CONNECTING")
    return {
        "camera_online": camera_online,
        "ai_online": ai_online,
        "tracking_active": False,
        "tracking_status": "READY",
        "fps": 0.0 if not camera_online else stream_status.get("fps", 0.0),
        "persons_detected": 0,
        "active_alerts_count": 0,
        "threat_level": "NORMAL",
        "threat_score": None,
        "threat_reason": "No person currently detected",
        "source_type": stream_status.get("source_type", ""),
        "source_status": stream_status.get("status", "OFFLINE"),
        "error_message": stream_status.get("error_message", "") or ai_error,
        "camera_message": (
            "CAMERA CONNECTION LOST. Attempting to reconnect..."
            if reconnecting and not camera_online
            else ("CAMERA ONLINE" if camera_online else "CAMERA OFFLINE")
        ),
        "border_defined": True,
        "roi_defined": False,
        "boundary_position": config.boundary_position,
        "monitored_direction": config.monitored_direction,
        "border_line": None,
        "roi_polygon": [],
        "persons": [],
        "persistence_seconds": config.persistence_seconds,
        "motion_metrics": {
            "frames_received": 0,
            "frames_analyzed": 0,
            "frames_sent_to_yolo": 0,
            "frames_skipped": 0,
            "ai_processing_pct": 0.0,
            "compute_saved_pct": 100.0,
            "motion_score": 0.0,
            "fast_motion_score": 0.0,
            "slow_motion_score": 0.0,
            "roi_active": False,
            "motion_roi": None,
        },
        "motion_roi": None,
        "roi_active": False,
        "show_motion_roi": False,
        "tamper_detected": False,
        "tamper_reason": "",
        "factor_breakdown": [],
        "edge_health": {
            "node_id": "EDGE-SURVEILLANCE-NODE-01",
            "node_label": "SOFTWARE EDGE NODE",
            "status": "ONLINE",
            "last_heartbeat_ago": 0.0,
            "latency_ms": 1.0,
        },
        "telemetry_bandwidth": {
            "node_mode": "EDGE-LOCAL ANALYTICS",
            "telemetry_payload_bytes": 1840,
            "telemetry_payload_kb": 1.8,
            "evidence_snapshot_bytes": 0,
            "evidence_snapshot_kb": 0.0,
            "bandwidth_reduction_pct": 99.4,
            "video_transport": "LOCAL EDGE (NO CONTINUOUS CLOUD UPLINK)",
        },
    }


def analyze_frame(
    frame: np.ndarray,
    detector,
    motion_analyzer,
    posture_heuristic,
    boundary_analyzer,
    alert_engine,
    track_memory: TrackMemory,
    motion_gate: Optional[Any] = None,
    slow_movement_analyzer: Optional[Any] = None,
    tamper_detector: Optional[Any] = None,
    replay_buffer: Optional[Any] = None,
    precomputed_detections: Optional[List[Dict[str, Any]]] = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any], List[Dict[str, Any]]]:
    h, w = frame.shape[:2]

    # 1. Rolling Replay Buffer: store latest frame in rolling memory window
    if replay_buffer is not None:
        replay_buffer.push_frame(frame)

    # 2. Camera Sabotage / Tamper Detection
    tamper_detected = False
    tamper_reason = ""
    if tamper_detector is not None:
        tamper_detected, tamper_reason, _ = tamper_detector.evaluate(frame)

    # 3. Dual-Scale Motion Gating & Dynamic ROI Optimization
    should_run_yolo = True
    motion_roi = None
    motion_metrics = {}
    if motion_gate is not None:
        active_count = len(track_memory.active_ids())
        should_run_yolo, motion_roi, motion_metrics = motion_gate.process(
            frame, active_target_count=active_count
        )

    # 4. Person Detection & Tracking. Browser frames may provide detections
    # already computed by their isolated browser inference path.
    if precomputed_detections is not None:
        detections = precomputed_detections
        track_memory.update(detections)
    elif should_run_yolo:
        detections = detector.detect_and_track(frame, conf_thresh=config.confidence_threshold)
        track_memory.update(detections)
    else:
        # On static frames where YOLO is gated, smoothly preserve active tracks
        detections = track_memory.active_detections()
        track_memory.update([])

    live_ids = [d["track_id"] for d in detections]
    motion_analyzer.cleanup_old_tracks(live_ids)
    boundary_analyzer.cleanup_old_tracks(live_ids)
    if slow_movement_analyzer is not None:
        slow_movement_analyzer.cleanup_old_tracks(live_ids)

    processed_persons: List[Dict[str, Any]] = []
    new_alerts: List[Dict[str, Any]] = []
    any_suspicious = False
    any_alert = False
    top_score = 0.0
    top_reasons: List[str] = []

    for det in detections:
        tid = det["track_id"]
        bbox = det["bbox"]
        conf = det["confidence"]

        motion = motion_analyzer.update(tid, bbox)
        posture = posture_heuristic.analyze(bbox, (h, w), motion["movement_state"])
        boundary = boundary_analyzer.check_boundary_status(tid, bbox, (h, w))

        slow_meta = {}
        if slow_movement_analyzer is not None:
            slow_meta = slow_movement_analyzer.update(
                tid, bbox, motion["relative_speed"], posture["posture_label"]
            )

        alert = alert_engine.evaluate(
            frame=frame,
            person_id=tid,
            bbox=bbox,
            confidence=conf,
            posture_data=posture,
            motion_data=motion,
            boundary_data=boundary,
            border_line=boundary_analyzer.border_line,
            roi_polygon=boundary_analyzer.roi_polygon,
            slow_movement_data=slow_meta,
        )
        if alert:
            new_alerts.append(alert)
            any_alert = True

        state = alert_engine.track_states.get(tid)
        has_alerted = bool(state.has_alerted_crossing or state.has_alerted_posture) if state else False
        crossing_pending = bool(state.crossing_start_time is not None and not state.has_alerted_crossing) if state else False

        in_restricted = bool(boundary.get("in_restricted"))
        approaching = bool(boundary.get("approaching"))
        is_slow_crawl = bool(slow_meta.get("is_slow_crawl"))
        is_suspicious = bool(posture.get("is_suspicious")) or is_slow_crawl
        unusual = motion["movement_state"] in ("RAPID MOVEMENT",)

        score, reasons = compute_threat_score(
            crossed_or_restricted=in_restricted or bool(boundary.get("crossed_border")),
            approaching=approaching,
            is_suspicious_posture=is_suspicious,
            unusual_movement=unusual,
            persistence_ok=has_alerted,
            has_alerted=has_alerted,
            is_slow_crawl=is_slow_crawl,
        )

        if is_slow_crawl and slow_meta.get("explanation"):
            reasons.append(slow_meta["explanation"])

        if crossing_pending and not has_alerted:
            persist_sec = round(state.crossing_persistence(), 1)
            reasons = [f"Boundary Crossed — Verifying Persistence ({persist_sec}s / {config.persistence_seconds}s)"]
            any_suspicious = True

        if has_alerted:
            any_alert = True
        elif approaching or is_suspicious or crossing_pending:
            any_suspicious = True

        if score > top_score:
            top_score = score
            top_reasons = reasons

        x1, y1, x2, y2 = bbox
        display_posture = "POSSIBLE SLOW CRAWL" if is_slow_crawl else posture["posture_label"]

        processed_persons.append({
            "track_id": tid,
            "bbox": bbox,
            "norm_bbox": [
                round(x1 / w, 4),
                round(y1 / h, 4),
                round(x2 / w, 4),
                round(y2 / h, 4),
            ],
            "confidence": conf,
            "center": det.get("center"),
            "movement_state": motion["movement_state"],
            "relative_speed": motion["relative_speed"],
            "direction": motion["direction"],
            "posture_label": display_posture,
            "behavior_score": score if (has_alerted or any_suspicious) else 0.0,
            "aspect_ratio": posture["aspect_ratio"],
            "is_suspicious": is_suspicious,
            "is_slow_crawl": is_slow_crawl,
            "crossed_border": bool(boundary.get("crossed_border")),
            "in_roi": bool(boundary.get("in_roi")),
            "in_restricted": in_restricted,
            "approaching": approaching,
            "side_of_border": boundary.get("side_of_border"),
            "crossing_direction": boundary.get("crossing_direction"),
            "track_status": "ACTIVE",
            "threat_reasons": reasons,
            "anchor_norm": boundary.get("anchor_norm"),
            "has_alerted": has_alerted,
            "crossing_pending": crossing_pending,
        })

    # Include recently lost tracks for display in target history, but without alert evaluation
    live_set = set(live_ids)
    for rec in track_memory.display_tracks():
        if rec["track_id"] in live_set:
            continue
        if rec.get("track_status") == "LOST":
            x1, y1, x2, y2 = rec["bbox"]
            processed_persons.append({
                "track_id": rec["track_id"],
                "bbox": rec["bbox"],
                "norm_bbox": [
                    round(x1 / w, 4),
                    round(y1 / h, 4),
                    round(x2 / w, 4),
                    round(y2 / h, 4),
                ],
                "confidence": rec.get("confidence", 0),
                "center": rec.get("center"),
                "movement_state": "LOST",
                "relative_speed": 0,
                "direction": "NONE",
                "posture_label": "LOST",
                "behavior_score": 0,
                "aspect_ratio": 0,
                "is_suspicious": False,
                "is_slow_crawl": False,
                "crossed_border": False,
                "in_roi": False,
                "in_restricted": False,
                "approaching": False,
                "side_of_border": "OUTSIDE",
                "crossing_direction": "",
                "track_status": "LOST",
                "threat_reasons": [],
                "has_alerted": False,
                "crossing_pending": False,
            })

    alert_engine.sync_with_live_tracks(live_set)
    active_alerts = alert_engine.get_active_alerts()
    if active_alerts:
        any_alert = True

    # 4-Tier Threat States: NORMAL -> OBSERVATION -> SUSPICIOUS -> ALERT
    if len(detections) == 0:
        threat_level = "NORMAL"
        threat_score: Optional[float] = None
        threat_reason = "No person currently detected"
    elif any_alert:
        threat_level = "ALERT"
        threat_score = top_score if top_score > 0 else 88.0
        threat_reason = " + ".join(top_reasons) if top_reasons else "Virtual Boundary Crossed"
    elif any_suspicious:
        threat_level = "SUSPICIOUS"
        threat_score = top_score if top_score > 0 else 25.0
        threat_reason = " + ".join(top_reasons) if top_reasons else "Activity Detected"
    else:
        # Person detected, but completely within safe zone and walking normally
        threat_level = "OBSERVATION"
        threat_score = 10.0
        threat_reason = "Target under observation — perimeter secure"

    factor_breakdown = get_factor_breakdown(
        person_detected=len(detections) > 0,
        crossed_or_restricted=any(p.get("in_restricted") or p.get("crossed_border") for p in processed_persons),
        approaching=any(p.get("approaching") for p in processed_persons),
        is_suspicious_posture=any(p.get("is_suspicious") for p in processed_persons),
        is_slow_crawl=any(p.get("is_slow_crawl") for p in processed_persons),
        persistence_verified=any(p.get("has_alerted") for p in processed_persons),
    )

    return processed_persons, {
        "threat_level": threat_level,
        "threat_score": threat_score,
        "threat_reason": threat_reason,
        "persons_detected": len(detections),
        "active_alerts_count": len(active_alerts),
        "motion_metrics": motion_metrics,
        "motion_roi": motion_roi,
        "tamper_detected": tamper_detected,
        "tamper_reason": tamper_reason,
        "factor_breakdown": factor_breakdown,
    }, new_alerts
