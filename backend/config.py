import os
from pathlib import Path
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent.parent
SNAPSHOTS_DIR = BASE_DIR / "snapshots"
DEMO_VIDEOS_DIR = BASE_DIR / "demo" / "videos"
MODELS_DIR = BASE_DIR / "models"
DATABASE_PATH = BASE_DIR / "border_surveillance.db"

SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
DEMO_VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
MODELS_DIR.mkdir(parents=True, exist_ok=True)

class PipelineConfig(BaseModel):
    source_type: str = "webcam"  # "demo", "webcam", "mobile"
    mobile_url: str = ""
    webcam_index: int = 0
    demo_video_filename: str = "border_patrol_demo.mp4"

    # Inference config (High-Accuracy YOLOv8s with 512px resolution)
    model_name: str = "yolov8s.pt"
    confidence_threshold: float = 0.25
    target_classes: list[int] = [0]  # 0 is 'person' in COCO
    inference_imgsz: int = 512

    # Tracking
    tracker_type: str = "bytetrack.yaml"
    track_lost_seconds: float = 2.5

    # Behavior & Posture heuristic
    aspect_ratio_threshold: float = 0.85  # w/h > 0.85 triggers low-posture warning
    posture_score_threshold: float = 65.0  # 0 to 100
    movement_speed_threshold_stationary: float = 2.5
    movement_speed_threshold_walking: float = 12.0

    # Virtual border (normalized 0-1). Horizontal line for MVP.
    boundary_position: float = 0.65
    monitored_direction: str = "top_to_bottom"  # top_to_bottom | bottom_to_top
    approach_band: float = 0.18

    # Alert persistence
    persistence_seconds: float = 2.0  # Condition must persist before an alert
    alert_cooldown_seconds: float = 12.0  # Cooldown between identical alerts

config = PipelineConfig()
