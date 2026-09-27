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
    source_type: str = "webcam"
    mobile_url: str = ""
    webcam_index: int = 0
    demo_video_filename: str = "border_patrol_demo.mp4"

    # Use the model already included in the repository by default.
    model_name: str = "yolov8n.pt"
    confidence_threshold: float = 0.25
    target_classes: list[int] = [0]
    inference_imgsz: int = 640

    tracker_type: str = "bytetrack.yaml"
    track_lost_seconds: float = 2.5

    aspect_ratio_threshold: float = 0.85
    posture_score_threshold: float = 65.0
    movement_speed_threshold_stationary: float = 2.5
    movement_speed_threshold_walking: float = 12.0

    boundary_position: float = 0.65
    monitored_direction: str = "top_to_bottom"
    approach_band: float = 0.18

    persistence_seconds: float = 2.0
    alert_cooldown_seconds: float = 12.0

config = PipelineConfig()
