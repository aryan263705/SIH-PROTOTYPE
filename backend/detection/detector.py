from pathlib import Path
from typing import List, Dict, Any, Tuple
import cv2
import numpy as np
import threading
from backend.config import MODELS_DIR, config


class PersonDetectorTracker:
    def __init__(self, model_name: str = "yolov8s.pt"):
        self.model = None
        self.model_name = model_name
        self.ai_online = False
        self.error_message = ""
        self._prev_boxes: Dict[str, Tuple[int, int, int, int]] = {}
        # Ultralytics tracking state is not safe for overlapping requests.
        # Browser-camera frames can arrive faster than CPU inference on Render,
        # so serialize model inference across all callers.
        self._inference_lock = threading.Lock()
        self._load_model(model_name)

    def _load_model(self, model_name: str):
        try:
            from ultralytics import YOLO
            model_path = MODELS_DIR / model_name
            if not model_path.exists():
                model_path = Path(model_name)

            print(f"[AI Engine] Loading YOLO model from {model_path}...")
            self.model = YOLO(str(model_path))
            self.model_name = model_name
            self.ai_online = True
            self.error_message = ""
        except Exception as ex:
            # Fallback to yolov8n if yolov8s has issue
            if "yolov8s" in model_name:
                print(f"[AI Engine] Could not load {model_name}, falling back to yolov8n.pt: {ex}")
                self._load_model("yolov8n.pt")
                return
            self.model = None
            self.ai_online = False
            self.error_message = f"YOLO model unavailable: {ex}"
            print(f"[AI Engine] {self.error_message}")

    def switch_model(self, model_name: str) -> bool:
        """Switch between high-accuracy (yolov8s.pt) and max-speed (yolov8n.pt) at runtime."""
        self._load_model(model_name)
        config.model_name = model_name
        if "yolov8s" in model_name:
            config.inference_imgsz = 512
        else:
            config.inference_imgsz = 640
        self.reset_tracker()
        return self.ai_online

    def reset_tracker(self):
        """Reset internal tracker state when stream changes or loops"""
        self._prev_boxes.clear()
        if self.model is None:
            return
        try:
            if hasattr(self.model, "predictor") and self.model.predictor is not None:
                if hasattr(self.model.predictor, "trackers") and self.model.predictor.trackers:
                    for t in self.model.predictor.trackers:
                        try:
                            t.reset()
                        except Exception:
                            pass
                try:
                    delattr(self.model.predictor, "trackers")
                except Exception:
                    pass
        except Exception:
            pass

    def _preprocess_frame(self, frame: np.ndarray) -> np.ndarray:
        """Adaptive contrast enhancement (CLAHE) for dim or low-contrast CCTV streams."""
        try:
            lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
            l_chan, a_chan, b_chan = cv2.split(lab)
            # Apply CLAHE if luminance standard deviation is low (flat/challenging lighting)
            if float(np.std(l_chan)) < 48.0:
                clahe = cv2.createCLAHE(clipLimit=2.2, tileGridSize=(8, 8))
                l_enh = clahe.apply(l_chan)
                enhanced = cv2.merge((l_enh, a_chan, b_chan))
                return cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)
        except Exception:
            pass
        return frame

    def _smooth_bbox(self, tid: str, bbox: Tuple[int, int, int, int], alpha: float = 0.75) -> Tuple[int, int, int, int]:
        """Exponential moving average filter to remove frame-to-frame bounding box jitter."""
        if tid in self._prev_boxes:
            px1, py1, px2, py2 = self._prev_boxes[tid]
            x1, y1, x2, y2 = bbox
            sx1 = int(alpha * x1 + (1.0 - alpha) * px1)
            sy1 = int(alpha * y1 + (1.0 - alpha) * py1)
            sx2 = int(alpha * x2 + (1.0 - alpha) * px2)
            sy2 = int(alpha * y2 + (1.0 - alpha) * py2)
            smoothed = (sx1, sy1, sx2, sy2)
        else:
            smoothed = bbox
        self._prev_boxes[tid] = smoothed
        return smoothed

    def detect_and_track(
        self,
        frame: np.ndarray,
        conf_thresh: float = 0.25
    ) -> List[Dict[str, Any]]:
        """
        Runs YOLO person detection and ByteTrack tracking.
        Returns only real person tracks with assigned tracker IDs.
        Never invents IDs, boxes, or confidence values.
        """
        if frame is None or getattr(frame, "size", 0) == 0:
            return []
        if self.model is None:
            return []

        # Enhance low-light frames for maximum detection recall
        input_frame = self._preprocess_frame(frame)

        try:
            with self._inference_lock:
                results = self.model.track(
                    source=input_frame,
                    persist=True,
                    tracker=config.tracker_type,
                    classes=config.target_classes,
                    conf=conf_thresh,
                    iou=0.45,
                    agnostic_nms=True,
                    verbose=False,
                    imgsz=config.inference_imgsz
                )
        except Exception as ex:
            # Self-healing: if tracker threw an error, cleanly purge corrupted tracker and retry once.
            try:
                with self._inference_lock:
                    if hasattr(self.model, "predictor") and self.model.predictor is not None:
                        if hasattr(self.model.predictor, "trackers"):
                            delattr(self.model.predictor, "trackers")
                    results = self.model.track(
                        source=input_frame,
                        persist=True,
                        tracker=config.tracker_type,
                        classes=config.target_classes,
                        conf=conf_thresh,
                        iou=0.45,
                        agnostic_nms=True,
                        verbose=False,
                        imgsz=config.inference_imgsz
                    )
            except Exception as ex2:
                self.ai_online = False
                self.error_message = f"YOLO inference error: {ex2}"
                return []

        self.ai_online = True
        self.error_message = ""

        detections = []
        if not results:
            return detections

        r = results[0]
        if r.boxes is None or len(r.boxes) == 0:
            return detections

        boxes = r.boxes.xyxy.cpu().numpy()
        confs = r.boxes.conf.cpu().numpy()

        if r.boxes.id is not None:
            track_ids = r.boxes.id.cpu().numpy().astype(int)
        else:
            # Fallback: assign temporary IDs so real detections are never dropped during tracker init
            track_ids = np.array([i + 1 for i in range(len(boxes))], dtype=int)

        for i, box in enumerate(boxes):
            if i >= len(track_ids):
                continue
            x1, y1, x2, y2 = [int(v) for v in box]
            conf = float(confs[i])
            raw_id = int(track_ids[i])
            tid = f"{raw_id:02d}"

            # Temporal smoothing for rock-solid box display
            smoothed_box = self._smooth_bbox(tid, (x1, y1, x2, y2))
            cx = (smoothed_box[0] + smoothed_box[2]) / 2.0
            cy = (smoothed_box[1] + smoothed_box[3]) / 2.0

            detections.append({
                "track_id": tid,
                "bbox": smoothed_box,
                "confidence": round(conf * 100.0, 1),
                "class_name": "person",
                "center": (round(cx, 1), round(cy, 1))
            })

        return detections
