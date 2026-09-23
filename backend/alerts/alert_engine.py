import time
import datetime
from typing import Dict, List, Optional, Any, Tuple, Set
from backend.alerts.snapshot import capture_evidence_snapshot
from backend.storage.db import log_event
from backend.config import config


class TrackAlertState:
    def __init__(self, person_id: str):
        self.person_id = person_id
        self.was_ever_outside: bool = False
        self.has_crossed: bool = False
        self.crossing_start_time: Optional[float] = None
        self.suspicious_start_time: Optional[float] = None
        self.last_alert_time: float = 0.0
        self.last_alert_type: str = ""
        self.has_alerted_crossing: bool = False
        self.has_alerted_posture: bool = False

    def update_boundary(self, is_outside: bool, in_restricted: bool, crossed_edge: bool):
        now = time.time()
        if is_outside:
            self.was_ever_outside = True
            # When outside, cancel pending crossing and allow re-alert if they cross again
            self.crossing_start_time = None
            self.has_crossed = False
            self.has_alerted_crossing = False
        elif crossed_edge or (in_restricted and self.was_ever_outside and not self.has_crossed):
            # An actual line-crossing from OUTSIDE into RESTRICTED
            self.has_crossed = True
            if self.crossing_start_time is None:
                self.crossing_start_time = now
        elif not in_restricted:
            self.crossing_start_time = None
            self.has_crossed = False

    def crossing_persistence(self) -> float:
        if self.crossing_start_time is None:
            return 0.0
        return max(0.0, time.time() - self.crossing_start_time)

    def register_suspicious(self, is_suspicious: bool):
        now = time.time()
        if is_suspicious:
            if self.suspicious_start_time is None:
                self.suspicious_start_time = now
        else:
            self.suspicious_start_time = None
            self.has_alerted_posture = False

    def suspicious_duration(self) -> float:
        if self.suspicious_start_time is None:
            return 0.0
        return max(0.0, time.time() - self.suspicious_start_time)


def compute_threat_score(
    crossed_or_restricted: bool,
    approaching: bool,
    is_suspicious_posture: bool,
    unusual_movement: bool,
    persistence_ok: bool,
    has_alerted: bool = False,
    is_slow_crawl: bool = False,
) -> Tuple[float, List[str]]:
    """
    Explainable threat scoring. Zero unless a real person condition exists.
    Transparent rule-based breakdown for SIH jury presentation.
    """
    score = 0.0
    reasons: List[str] = []

    if approaching:
        score += 25.0
        reasons.append("Approaching Border")
    if unusual_movement:
        score += 15.0
        reasons.append("Unusual Movement")
    if is_slow_crawl:
        score += 35.0 if persistence_ok else 25.0
        reasons.append("Slow Persistent Crawl" if persistence_ok else "Ultra-Slow Inching Movement")
    elif is_suspicious_posture:
        score += 35.0 if persistence_ok else 25.0
        reasons.append("Persistent Low Posture" if persistence_ok else "Low Posture")

    if crossed_or_restricted:
        if persistence_ok or has_alerted:
            score += 50.0
            reasons.append("Virtual Boundary Crossed")
        else:
            score += 25.0
            reasons.append("Boundary Crossing Pending Verification")

    if score == 0.0:
        return 0.0, []
    return round(min(100.0, score), 1), reasons


def get_factor_breakdown(
    person_detected: bool,
    crossed_or_restricted: bool,
    approaching: bool,
    is_suspicious_posture: bool,
    is_slow_crawl: bool,
    persistence_verified: bool
) -> List[Dict[str, Any]]:
    return [
        {"factor": "Person Detected & Tracked", "active": person_detected, "weight": 10},
        {"factor": "Approaching Virtual Border", "active": approaching, "weight": 25},
        {"factor": "Low Posture / Crouched", "active": is_suspicious_posture, "weight": 25},
        {"factor": "Ultra-Slow Crawl Trajectory", "active": is_slow_crawl, "weight": 30},
        {"factor": "Boundary Line Crossed", "active": crossed_or_restricted, "weight": 50},
        {"factor": "Temporal Persistence (2.0s) Verified", "active": persistence_verified, "weight": 20},
    ]


class AlertEngine:
    def __init__(self, replay_buffer=None):
        self.track_states: Dict[str, TrackAlertState] = {}
        self.active_alerts: List[Dict[str, Any]] = []
        self.replay_buffer = replay_buffer

    def evaluate(
        self,
        frame,
        person_id: str,
        bbox: Tuple[int, int, int, int],
        confidence: float,
        posture_data: Dict[str, Any],
        motion_data: Dict[str, Any],
        boundary_data: Optional[Dict[str, Any]] = None,
        border_line: Optional[Tuple[Tuple[float, float], Tuple[float, float]]] = None,
        roi_polygon: Optional[List[Tuple[float, float]]] = None,
        slow_movement_data: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Detection alone never alerts.
        A confirmed alert requires a real person AND a persisted suspicious condition
        (validated boundary crossing with 2s persistence in restricted zone, persistent low posture, or slow crawling).
        """
        if person_id is None:
            return None

        now = time.time()
        if person_id not in self.track_states:
            self.track_states[person_id] = TrackAlertState(person_id)

        state = self.track_states[person_id]
        is_slow_crawl = bool(slow_movement_data and slow_movement_data.get("is_slow_crawl"))
        is_suspicious = bool(posture_data.get("is_suspicious")) or is_slow_crawl
        posture_label = posture_data.get("posture_label", "NORMAL")
        if is_slow_crawl:
            posture_label = "POSSIBLE SLOW CRAWL"
        movement_state = motion_data.get("movement_state", "NORMAL")

        boundary_data = boundary_data or {}
        side_of_border = boundary_data.get("side_of_border", "OUTSIDE")
        is_outside = side_of_border == "OUTSIDE"
        in_restricted = bool(boundary_data.get("in_restricted"))
        in_roi = bool(boundary_data.get("in_roi"))
        crossed_edge = bool(boundary_data.get("crossed_border"))
        approaching = bool(boundary_data.get("approaching"))
        crossing_direction = boundary_data.get("crossing_direction", "OUTSIDE → RESTRICTED ZONE")

        # Update crossing and persistence state
        state.update_boundary(is_outside=is_outside, in_restricted=in_restricted or in_roi, crossed_edge=crossed_edge)
        state.register_suspicious(is_suspicious)

        crossing_dur = state.crossing_persistence()
        suspicious_dur = state.suspicious_duration()
        unusual = movement_state in ("RAPID MOVEMENT",)

        # Persistence check: must remain for configured duration (e.g. 2.0s)
        crossing_ready = (
            (in_restricted or in_roi)
            and (state.has_crossed or in_roi)
            and crossing_dur >= config.persistence_seconds
            and not state.has_alerted_crossing
        )

        posture_ready = (
            is_suspicious
            and suspicious_dur >= config.persistence_seconds
            and not state.has_alerted_posture
            and not crossing_ready
        )

        threat_score, reasons = compute_threat_score(
            crossed_or_restricted=in_restricted or in_roi,
            approaching=approaching,
            is_suspicious_posture=is_suspicious,
            unusual_movement=unusual,
            persistence_ok=crossing_ready or posture_ready,
            has_alerted=state.has_alerted_crossing or state.has_alerted_posture,
            is_slow_crawl=is_slow_crawl,
        )

        alert_type = None
        severity = "LOW"

        if crossing_ready:
            alert_type = "POSSIBLE INTRUSION"
            severity = "CRITICAL"
        elif posture_ready:
            if is_slow_crawl or "CRAWL" in posture_label.upper():
                alert_type = "POSSIBLE CRAWLING"
            else:
                alert_type = "LOW POSTURE"
            severity = "HIGH"

        cooldown_ok = (now - state.last_alert_time) >= config.alert_cooldown_seconds
        if not alert_type or not cooldown_ok:
            return None

        state.last_alert_time = now
        state.last_alert_type = alert_type
        if crossing_ready:
            state.has_alerted_crossing = True
        if posture_ready:
            state.has_alerted_posture = True

        if crossing_ready:
            event_name = "BOUNDARY_CROSSING"
            reason_text = "Virtual Boundary Crossed"
        else:
            event_name = alert_type.replace(" ", "_")
            reason_text = " + ".join(reasons) if reasons else posture_label

        persist_shown = round(crossing_dur if crossing_ready else suspicious_dur, 1)

        snapshot_filename = capture_evidence_snapshot(
            frame=frame,
            person_id=person_id,
            bbox=bbox,
            alert_type=alert_type,
            score=threat_score,
            border_line=border_line,
            roi_polygon=roi_polygon,
            extra_lines=[
                f"Reason: {reason_text}",
                f"Direction: {crossing_direction}",
                f"Persistence: {persist_shown}s | Conf: {confidence:.0f}%",
            ]
        )

        # Trigger rolling replay buffer export if available
        replay_filename = None
        if self.replay_buffer:
            try:
                replay_filename = self.replay_buffer.trigger_replay_export(
                    person_id=person_id,
                    event_name=event_name,
                )
            except Exception as e:
                print(f"[Alert Engine] Error generating replay: {e}")

        details = (
            f"Event: {event_name} | Reason: {reason_text} | "
            f"Direction: {crossing_direction} | Persistence: {persist_shown}s | "
            f"Conf: {confidence:.0f}% | Posture: {posture_label} | Motion: {movement_state}"
        )
        if replay_filename:
            details += f" | Replay: {replay_filename}"

        db_id = log_event(
            person_id=person_id,
            event_type=event_name,
            score=threat_score,
            status="ACTIVE",
            snapshot_path=snapshot_filename,
            details=details
        )

        alert_payload = {
            "id": db_id,
            "type": "ALERT",
            "timestamp": datetime.datetime.now().strftime("%H:%M:%S"),
            "date": datetime.datetime.now().strftime("%Y-%m-%d"),
            "person_id": person_id,
            "confidence": round(confidence, 1),
            "alert_type": alert_type,
            "event": event_name,
            "severity": severity,
            "behavior_score": threat_score,
            "score": threat_score,
            "status": "ACTIVE",
            "snapshot": snapshot_filename,
            "replay": replay_filename,
            "persistence_seconds": persist_shown,
            "movement": movement_state,
            "reason": reason_text,
            "reasons": reasons,
            "direction": crossing_direction,
            "details": details
        }

        self.active_alerts.insert(0, alert_payload)
        if len(self.active_alerts) > 50:
            self.active_alerts.pop()

        return alert_payload

    def sync_with_live_tracks(self, live_ids: Set[str]):
        """Active alerts require a live person. Empty camera => 0 active alerts."""
        if not live_ids:
            self.active_alerts = []
            self.track_states.clear()
            return

        self.active_alerts = [
            a for a in self.active_alerts
            if str(a.get("person_id")) in live_ids
        ]
        stale = [k for k in self.track_states if k not in live_ids]
        for k in stale:
            del self.track_states[k]

    def get_active_alerts(self) -> List[Dict[str, Any]]:
        return self.active_alerts

    def clear_active_alerts(self):
        self.active_alerts.clear()
        self.track_states.clear()
