import os
import sys
import time
import shutil
import sqlite3
import numpy as np
import cv2
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

from backend.config import config, SNAPSHOTS_DIR, DATABASE_PATH, DEMO_VIDEOS_DIR
from backend.detection.detector import PersonDetectorTracker
from backend.behavior.motion_analyzer import MotionAnalyzer
from backend.behavior.posture_heuristic import PostureHeuristic
from backend.behavior.boundary_analyzer import BoundaryAnalyzer
from backend.alerts.alert_engine import AlertEngine
from backend.pipeline import TrackMemory, analyze_frame, empty_telemetry
from backend.storage.db import get_recent_events, clear_events
from backend.camera.stream_manager import StreamManager


def test_1_camera_empty():
    print("\n--- TEST 1: Camera Empty ---")
    clear_events()
    detector = PersonDetectorTracker(model_name="models/yolov8n.pt")
    motion = MotionAnalyzer()
    posture = PostureHeuristic()
    boundary = BoundaryAnalyzer()
    engine = AlertEngine()
    mem = TrackMemory()

    blank = np.zeros((480, 640, 3), dtype=np.uint8)
    processed, analysis, alerts = analyze_frame(blank, detector, motion, posture, boundary, engine, mem)

    assert analysis["persons_detected"] == 0, f"Expected 0 persons, got {analysis['persons_detected']}"
    assert analysis["active_alerts_count"] == 0, f"Expected 0 alerts, got {analysis['active_alerts_count']}"
    assert analysis["threat_level"] == "NORMAL", f"Expected NORMAL, got {analysis['threat_level']}"
    assert analysis["threat_score"] is None, f"Expected None score, got {analysis['threat_score']}"
    assert len(alerts) == 0, f"Expected 0 new alerts, got {len(alerts)}"
    assert len(get_recent_events()) == 0, "Expected 0 events in database"
    print("PASS: Empty camera produces 0 persons, 0 alerts, NORMAL threat level, and 0 events.")


def test_2_and_3_person_safe_zone_and_approaching():
    print("\n--- TEST 2 & 3: Person in Safe Zone and Approaching ---")
    clear_events()
    detector = PersonDetectorTracker(model_name="models/yolov8n.pt")
    motion = MotionAnalyzer()
    posture = PostureHeuristic()
    boundary = BoundaryAnalyzer()
    boundary.set_boundary_position(0.65, "top_to_bottom")  # boundary at y = 312
    engine = AlertEngine()
    mem = TrackMemory()

    # Synthetic detections in safe zone (y = 120, well above 312)
    # Simulate detector returning 1 real person
    class MockDetector:
        def __init__(self):
            self.ai_online = True
            self.error_message = ""
            self.y = 120

        def detect_and_track(self, frame, conf_thresh=0.45):
            h, w = frame.shape[:2]
            return [{
                "track_id": "01",
                "bbox": (200, int(self.y), 260, int(self.y + 120)),
                "confidence": 88.5,
                "class_name": "person",
                "center": (230.0, float(self.y + 60))
            }]

    mock_det = MockDetector()
    frame = np.zeros((480, 640, 3), dtype=np.uint8)

    # Step 1: In safe zone (y = 100, cy = 160)
    mock_det.y = 100
    for _ in range(5):
        processed, analysis, alerts = analyze_frame(frame, mock_det, motion, posture, boundary, engine, mem)
        time.sleep(0.02)

    assert analysis["persons_detected"] == 1, f"Expected 1 person, got {analysis['persons_detected']}"
    assert analysis["threat_level"] in ("NORMAL", "OBSERVATION"), f"Expected NORMAL or OBSERVATION in safe zone, got {analysis['threat_level']}"
    assert analysis["active_alerts_count"] == 0, f"Expected 0 alerts, got {analysis['active_alerts_count']}"
    assert len(alerts) == 0, "No alerts should fire in safe zone"
    print("PASS: Person in safe zone has OBSERVATION/NORMAL status, 0 alerts, and no intrusion.")

    # Step 2: Approaching border (moving towards 312, cy = 270)
    mock_det.y = 200
    for _ in range(5):
        processed, analysis, alerts = analyze_frame(frame, mock_det, motion, posture, boundary, engine, mem)
        mock_det.y += 3
        time.sleep(0.02)

    assert analysis["threat_level"] == "SUSPICIOUS", f"Expected SUSPICIOUS approaching border, got {analysis['threat_level']}"
    assert "Approaching Border" in analysis["threat_reason"] or "Activity" in analysis["threat_reason"], f"Unexpected reason: {analysis['threat_reason']}"
    assert analysis["active_alerts_count"] == 0, "Approaching border must NOT trigger an alert"
    assert len(alerts) == 0, "Approaching border must NOT create an alert event"
    print("PASS: Person approaching border enters SUSPICIOUS status without generating an alert.")


def test_4_brief_crossing_cancellation():
    print("\n--- TEST 4: Brief Crossing Cancelled Before 2.0s Persistence ---")
    clear_events()
    motion = MotionAnalyzer()
    posture = PostureHeuristic()
    boundary = BoundaryAnalyzer()
    boundary.set_boundary_position(0.65, "top_to_bottom")  # boundary at y = 312
    engine = AlertEngine()
    mem = TrackMemory()

    class MockDetector:
        def __init__(self):
            self.ai_online = True
            self.error_message = ""
            self.y = 150

        def detect_and_track(self, frame, conf_thresh=0.45):
            return [{
                "track_id": "01",
                "bbox": (200, int(self.y), 260, int(self.y + 120)),
                "confidence": 90.0,
                "class_name": "person",
                "center": (230.0, float(self.y + 60))
            }]

    mock_det = MockDetector()
    frame = np.zeros((480, 640, 3), dtype=np.uint8)

    # 1. Establish track in safe zone (cy = 210 < 312)
    mock_det.y = 150
    for _ in range(5):
        analyze_frame(frame, mock_det, motion, posture, boundary, engine, mem)
        time.sleep(0.02)

    # 2. Brief step across line (cy = 330 > 312) for only 0.2 seconds
    mock_det.y = 270
    for _ in range(3):
        analyze_frame(frame, mock_det, motion, posture, boundary, engine, mem)
        time.sleep(0.05)

    # 3. Person steps back outside (cy = 210 < 312)
    mock_det.y = 150
    processed, analysis, alerts = analyze_frame(frame, mock_det, motion, posture, boundary, engine, mem)

    assert len(alerts) == 0, "Brief crossing under persistence threshold must not generate an alert"
    assert analysis["active_alerts_count"] == 0, "Active alerts must be 0 after returning outside"
    assert len(get_recent_events()) == 0, "No event should be logged for cancelled brief crossing"
    print("PASS: Brief crossing below persistence threshold successfully cancelled with 0 alerts.")


def test_5_and_6_validated_crossing_and_cooldown():
    print("\n--- TEST 5 & 6: Validated Crossing & Alert De-duplication Cooldown ---")
    clear_events()
    motion = MotionAnalyzer()
    posture = PostureHeuristic()
    boundary = BoundaryAnalyzer()
    boundary.set_boundary_position(0.65, "top_to_bottom")  # boundary at y = 312
    engine = AlertEngine()
    mem = TrackMemory()

    class MockDetector:
        def __init__(self):
            self.ai_online = True
            self.error_message = ""
            self.y = 150

        def detect_and_track(self, frame, conf_thresh=0.45):
            return [{
                "track_id": "01",
                "bbox": (200, int(self.y), 260, int(self.y + 120)),
                "confidence": 92.0,
                "class_name": "person",
                "center": (230.0, float(self.y + 60))
            }]

    mock_det = MockDetector()
    frame = np.zeros((480, 640, 3), dtype=np.uint8)

    # 1. Establish track in safe zone (cy = 210 < 312)
    mock_det.y = 150
    for _ in range(5):
        analyze_frame(frame, mock_det, motion, posture, boundary, engine, mem)
        time.sleep(0.02)

    # 2. Cross boundary into restricted zone (cy = 340 > 312)
    mock_det.y = 280
    config.persistence_seconds = 1.0  # Set to 1.0s for rapid test execution

    alert_fired = False
    start_t = time.time()
    generated_alerts = []

    while time.time() - start_t < 1.8:
        processed, analysis, new_alerts = analyze_frame(frame, mock_det, motion, posture, boundary, engine, mem)
        if new_alerts:
            generated_alerts.extend(new_alerts)
            alert_fired = True
        time.sleep(0.08)

    assert alert_fired, "A confirmed boundary crossing after persistence threshold MUST generate an alert"
    assert len(generated_alerts) == 1, f"Expected exactly 1 alert (no spam), got {len(generated_alerts)}"
    
    alert = generated_alerts[0]
    assert alert["person_id"] == "01", f"Expected person_id '01', got {alert['person_id']}"
    assert alert["event"] == "BOUNDARY_CROSSING", f"Expected BOUNDARY_CROSSING, got {alert['event']}"
    assert alert["alert_type"] == "POSSIBLE INTRUSION", f"Expected POSSIBLE INTRUSION, got {alert['alert_type']}"
    assert "OUTSIDE" in alert["direction"], f"Expected direction containing OUTSIDE, got {alert['direction']}"
    assert alert["confidence"] == 92.0, f"Expected confidence 92.0, got {alert['confidence']}"
    
    # Check evidence snapshot on disk
    snapshot_file = SNAPSHOTS_DIR / alert["snapshot"]
    assert snapshot_file.exists(), f"Snapshot file {snapshot_file} does not exist"
    
    # Check DB event
    db_events = get_recent_events()
    assert len(db_events) == 1, f"Expected 1 event in database, got {len(db_events)}"
    assert db_events[0]["person_id"] == "01"

    # Test 6: Verify no alert spam over subsequent frames while remaining in restricted zone
    more_alerts = []
    for _ in range(10):
        processed, analysis, new_alerts = analyze_frame(frame, mock_det, motion, posture, boundary, engine, mem)
        more_alerts.extend(new_alerts)
        time.sleep(0.05)

    assert len(more_alerts) == 0, f"Alert cooldown failed! Received duplicate alerts: {len(more_alerts)}"
    print("PASS: Validated boundary crossing generated exactly 1 alert, snapshot file, and no duplicate alert spam.")


def test_7_person_leaves_frame():
    print("\n--- TEST 7: Person Leaves Frame ---")
    clear_events()
    motion = MotionAnalyzer()
    posture = PostureHeuristic()
    boundary = BoundaryAnalyzer()
    engine = AlertEngine()
    mem = TrackMemory(timeout_seconds=0.3)

    class MockDetector:
        def __init__(self):
            self.ai_online = True
            self.error_message = ""
            self.active = True

        def detect_and_track(self, frame, conf_thresh=0.45):
            if not self.active:
                return []
            return [{
                "track_id": "01",
                "bbox": (200, 150, 260, 270),
                "confidence": 90.0,
                "class_name": "person",
                "center": (230.0, 210.0)
            }]

    mock_det = MockDetector()
    frame = np.zeros((480, 640, 3), dtype=np.uint8)

    # 1. Person in frame
    analyze_frame(frame, mock_det, motion, posture, boundary, engine, mem)
    time.sleep(0.05)

    # 2. Person leaves frame
    mock_det.active = False
    processed, analysis, alerts = analyze_frame(frame, mock_det, motion, posture, boundary, engine, mem)
    assert analysis["persons_detected"] == 0, "Persons detected must be 0 immediately"
    assert analysis["threat_level"] == "NORMAL", "Threat level must be NORMAL when empty"

    # Wait for memory prune (timeout 0.3s)
    time.sleep(0.4)
    processed, analysis, alerts = analyze_frame(frame, mock_det, motion, posture, boundary, engine, mem)
    active_tracks = [p for p in processed if p["track_status"] != "LOST"]
    assert len(active_tracks) == 0, "No active tracks should exist after timeout"
    print("PASS: Person leaving frame prunes target and returns threat status to NORMAL.")


def test_8_camera_disconnect_and_reconnect():
    print("\n--- TEST 8: Camera Disconnect & Reconnect ---")
    sm = StreamManager()
    # Check initially offline
    assert sm.get_latest_frame() is None, "Frame must be None when offline"
    status = sm.get_status()
    assert status["status"] == "OFFLINE"
    
    # Try invalid mobile stream URL
    sm.start("mobile", "http://127.0.0.1:9999/video")
    time.sleep(0.5)
    frame = sm.get_latest_frame()
    assert frame is None, "Frame must be None on unreachable stream"
    assert sm.status in ("ERROR", "CONNECTING"), f"Expected ERROR or CONNECTING, got {sm.status}"
    sm.stop()
    assert sm.status == "OFFLINE"
    print("PASS: Disconnected camera returns None frame, offline status, and handles disconnect without crashing.")


def test_9_two_real_people():
    print("\n--- TEST 9: Two Real People ---")
    clear_events()
    motion = MotionAnalyzer()
    posture = PostureHeuristic()
    boundary = BoundaryAnalyzer()
    engine = AlertEngine()
    mem = TrackMemory()

    class MockDetector:
        def __init__(self):
            self.ai_online = True
            self.error_message = ""

        def detect_and_track(self, frame, conf_thresh=0.45):
            return [
                {
                    "track_id": "01",
                    "bbox": (100, 150, 160, 270),
                    "confidence": 91.0,
                    "class_name": "person",
                    "center": (130.0, 210.0)
                },
                {
                    "track_id": "02",
                    "bbox": (300, 160, 360, 280),
                    "confidence": 89.5,
                    "class_name": "person",
                    "center": (330.0, 220.0)
                }
            ]

    mock_det = MockDetector()
    frame = np.zeros((480, 640, 3), dtype=np.uint8)

    processed, analysis, alerts = analyze_frame(frame, mock_det, motion, posture, boundary, engine, mem)
    assert analysis["persons_detected"] == 2, f"Expected 2 persons, got {analysis['persons_detected']}"
    assert len(processed) == 2, f"Expected 2 processed tracks, got {len(processed)}"
    ids = {p["track_id"] for p in processed}
    assert ids == {"01", "02"}, f"Expected IDs {{'01', '02'}}, got {ids}"
    assert analysis["threat_level"] in ("NORMAL", "OBSERVATION"), f"Both in safe zone, threat must be NORMAL or OBSERVATION, got {analysis['threat_level']}"
    print("PASS: Two real people assigned distinct IDs and tracked independently with 0 false alerts.")


def test_10_demo_video_end_to_end():
    print("\n--- TEST 10: Demo Video Presentation Flow (Real YOLO + ByteTrack) ---")
    clear_events()
    config.persistence_seconds = 2.0
    config.boundary_position = 0.65
    
    detector = PersonDetectorTracker(model_name="models/yolov8n.pt")
    motion = MotionAnalyzer()
    posture = PostureHeuristic()
    boundary = BoundaryAnalyzer()
    boundary.set_boundary_position(0.65, "top_to_bottom")
    engine = AlertEngine()
    mem = TrackMemory()

    demo_path = DEMO_VIDEOS_DIR / "border_patrol_demo.mp4"
    assert demo_path.exists(), f"Demo video {demo_path} does not exist"

    cap = cv2.VideoCapture(str(demo_path))
    assert cap.isOpened(), "Could not open demo video"

    frame_count = 0
    empty_frames = 0
    safe_zone_frames = 0
    approaching_frames = 0
    alert_frames = 0
    alerts_captured = []

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frame_count += 1
        processed, analysis, new_alerts = analyze_frame(frame, detector, motion, posture, boundary, engine, mem)
        if new_alerts:
            alerts_captured.extend(new_alerts)

        if analysis["persons_detected"] == 0:
            empty_frames += 1
        elif analysis["threat_level"] in ("NORMAL", "OBSERVATION"):
            safe_zone_frames += 1
        elif analysis["threat_level"] == "SUSPICIOUS":
            approaching_frames += 1
        elif analysis["threat_level"] == "ALERT":
            alert_frames += 1

    cap.release()

    print(f"Total Frames Processed: {frame_count}")
    print(f"Empty Frames: {empty_frames}")
    print(f"Safe Zone Frames (NORMAL/OBSERVATION): {safe_zone_frames}")
    print(f"Approaching / Verifying Frames (SUSPICIOUS): {approaching_frames}")
    print(f"Breach Frames (ALERT): {alert_frames}")
    print(f"Total Alerts Fired: {len(alerts_captured)}")

    assert empty_frames >= 40, f"Expected at least 40 empty frames at start, got {empty_frames}"
    assert safe_zone_frames >= 50, f"Expected safe zone normal frames, got {safe_zone_frames}"
    assert approaching_frames >= 10, f"Expected approaching frames, got {approaching_frames}"
    assert alert_frames >= 20, f"Expected alert frames after crossing, got {alert_frames}"
    assert len(alerts_captured) == 1, f"Expected exactly 1 alert across entire demo video, got {len(alerts_captured)}"

    print("PASS: End-to-End Demo Video successfully runs all presentation scenes with real YOLO and ByteTrack!")


def test_11_dual_scale_motion_gating():
    print("\n--- TEST 11: Dual-Scale Motion Gating (Edge Compute Optimization) ---")
    from backend.behavior.motion_gate import DualScaleMotionGate
    gate = DualScaleMotionGate(cooldown_frames=1)

    # 1. Feed 15 static blank frames with 0 active targets
    static_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    for _ in range(15):
        should_run, roi, metrics = gate.process(static_frame, active_target_count=0)

    print(f"Frames Received: {metrics['frames_received']}")
    print(f"Frames Skipped: {metrics['frames_skipped']}")
    print(f"Compute Saved: {metrics['compute_saved_pct']}%")

    assert metrics["frames_skipped"] >= 10, f"Expected at least 10 skipped frames, got {metrics['frames_skipped']}"
    assert metrics["compute_saved_pct"] >= 60.0, f"Expected >= 60% compute saved, got {metrics['compute_saved_pct']}%"

    # 2. Inject rapid motion (moving object)
    moving_frame = static_frame.copy()
    cv2.rectangle(moving_frame, (100, 100), (250, 350), (255, 255, 255), -1)
    should_run, roi, metrics = gate.process(moving_frame, active_target_count=0)

    assert should_run, "Motion gate MUST wake up YOLO when motion is detected"
    assert metrics["motion_score"] > 0, "Motion score must be > 0 when pixels change"
    print("PASS: Dual-scale motion gating skipped empty frames and woke pipeline upon motion.")


def test_12_slow_crawler_detection():
    print("\n--- TEST 12: Ultra-Slow Persistent Movement / Crawler Heuristic ---")
    from backend.behavior.slow_movement_analyzer import SlowMovementAnalyzer
    analyzer = SlowMovementAnalyzer(history_seconds=4.0)

    # Simulate flat crawling posture (width 120, height 50 -> AR = 2.4)
    x = 100.0
    y = 200.0
    for i in range(25):
        bbox = (int(x), int(y), int(x + 120), int(y + 50))
        res = analyzer.update(
            track_id="09",
            bbox=bbox,
            instantaneous_speed=12.0,  # Very slow
            posture_label="CRAWLING",
        )
        x += 1.5  # Cumulative displacement creeping forward
        time.sleep(0.08)

    print(f"Net Displacement: {res['net_displacement']}px over {res['tracking_duration']}s")
    print(f"Movement Label: {res['movement_label']}")
    print(f"Is Slow Crawl: {res['is_slow_crawl']}")

    assert res["is_slow_crawl"] or "CRAWL" in res["movement_label"], f"Expected slow crawl detection, got {res}"
    print("PASS: Ultra-slow persistent movement detected with low-posture crawl classification.")


def test_13_replay_buffer_export():
    print("\n--- TEST 13: Rolling Event Replay Buffer (30s Forensic Clip) ---")
    from backend.alerts.replay_buffer import RollingEventReplayBuffer, REPLAYS_DIR
    buf = RollingEventReplayBuffer(max_seconds=5.0, target_fps=15.0)

    # Push 20 synthetic frames into rolling memory
    for i in range(20):
        frame = np.zeros((240, 320, 3), dtype=np.uint8)
        cv2.putText(frame, f"FRAME {i}", (40, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        buf.push_frame(frame)
        time.sleep(0.02)

    rel_path = buf.trigger_replay_export("01", "BOUNDARY_CROSSING", pre_seconds=1.0, post_seconds=0.2)
    time.sleep(0.5)  # Wait for background thread to write video

    clip_file = SNAPSHOTS_DIR / rel_path
    print(f"Exported Replay Clip: {clip_file}")
    assert clip_file.exists(), f"Replay file {clip_file} was not written"
    assert clip_file.stat().st_size > 500, f"Replay file too small: {clip_file.stat().st_size} bytes"
    print("PASS: Rolling event replay buffer successfully compiled and exported standalone forensic MP4 clip.")


def test_14_low_bandwidth_telemetry():
    print("\n--- TEST 14: Low-Bandwidth Telemetry & Edge Health ---")
    from backend.telemetry.edge_health import EdgeHealthMonitor
    monitor = EdgeHealthMonitor(node_id="EDGE-SURVEILLANCE-NODE-01")

    heartbeat = monitor.beat()
    assert heartbeat["status"] == "ONLINE"
    assert heartbeat["node_label"] == "SOFTWARE EDGE NODE"

    # Measure telemetry packet size
    sample_payload = {
        "node_id": "EDGE-01",
        "threat_level": "ALERT",
        "persons": [{"track_id": "01", "bbox": [100, 120, 200, 320]}],
        "active_alerts_count": 1,
    }
    byte_size = monitor.measure_telemetry_packet(sample_payload)
    summary = monitor.get_bandwidth_summary()

    print(f"Measured Telemetry Packet: {byte_size} bytes ({summary['telemetry_payload_kb']} KB)")
    print(f"Bandwidth Reduction vs Video Uplink: {summary['bandwidth_reduction_pct']}%")

    assert byte_size < 3000, f"Telemetry payload should be lightweight (< 3 KB), got {byte_size} bytes"
    assert summary["bandwidth_reduction_pct"] > 95.0
    print("PASS: Edge telemetry measured real byte size (< 3 KB) and verified > 95% bandwidth savings.")


def test_15_camera_tamper_detection():
    print("\n--- TEST 15: Camera / Sensor Tamper Detection ---")
    from backend.behavior.tamper_detector import CameraTamperDetector
    detector = CameraTamperDetector(persistence_seconds=0.2)

    # 1. Normal frame
    normal_frame = np.full((120, 160, 3), 128, dtype=np.uint8)
    cv2.putText(normal_frame, "BORDER SCENE", (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
    tampered, reason, _ = detector.evaluate(normal_frame)
    assert not tampered, "Normal frame must not trigger tamper alert"

    # 2. Blacked-out frame (lens covered with tape or spray paint)
    black_frame = np.zeros((120, 160, 3), dtype=np.uint8)
    for _ in range(5):
        tampered, reason, meta = detector.evaluate(black_frame)
        time.sleep(0.06)

    print(f"Tamper Status: {tampered} | Reason: {reason}")
    assert tampered, "Blackout frame persisting > 0.2s MUST trigger tamper alert"
    assert "Occlusion" in reason or "Blackout" in reason
    print("PASS: Camera tamper detector caught lens occlusion/sabotage without false alerts on normal frames.")


if __name__ == "__main__":
    print("==========================================================")
    print("  SIH26187 AI Border Surveillance - Acceptance Test Suite ")
    print("==========================================================")
    test_1_camera_empty()
    test_2_and_3_person_safe_zone_and_approaching()
    test_4_brief_crossing_cancellation()
    test_5_and_6_validated_crossing_and_cooldown()
    test_7_person_leaves_frame()
    test_8_camera_disconnect_and_reconnect()
    test_9_two_real_people()
    test_10_demo_video_end_to_end()
    test_11_dual_scale_motion_gating()
    test_12_slow_crawler_detection()
    test_13_replay_buffer_export()
    test_14_low_bandwidth_telemetry()
    test_15_camera_tamper_detection()
    print("\n==========================================================")
    print("  ALL 15 ACCEPTANCE TESTS PASSED SUCCESSFULLY! (100%)    ")
    print("==========================================================")

