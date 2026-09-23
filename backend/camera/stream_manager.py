import cv2
import time
import os
import threading
from pathlib import Path
from typing import Optional, Tuple
import numpy as np
from backend.config import DEMO_VIDEOS_DIR

# Suppress noisy OpenCV C++ backend logging on Windows
os.environ["OPENCV_VIDEOIO_PRIORITY_MSMF"] = "0"
# Set 4-second timeout for OpenCV FFMPEG network captures (RTSP/HTTP mobile streams)
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "timeout;4000000"

class StreamManager:
    def __init__(self):
        self.source_type: str = "webcam"  # "demo", "webcam", "mobile"
        self.source_path: str = "0"
        self.cap: Optional[cv2.VideoCapture] = None
        
        self.is_running: bool = False
        self.thread: Optional[threading.Thread] = None
        self.lock = threading.Lock()
        
        self.latest_frame: Optional[np.ndarray] = None
        self.status: str = "OFFLINE"  # "ONLINE", "CONNECTING", "ERROR", "OFFLINE"
        self.error_message: str = ""
        self.fps: float = 0.0
        self.frame_count: int = 0
        self.last_fps_time: float = time.time()
        self.is_demo_looping: bool = True

    def start(self, source_type: str = "webcam", source_path: str = ""):
        with self.lock:
            # Normalize paths for robust idempotency
            norm_source = str(source_path).strip() if source_path is not None else ""
            if source_type == "webcam" and not norm_source:
                norm_source = "0"
            curr_source = str(self.source_path).strip() if self.source_path is not None else ""
            if self.source_type == "webcam" and not curr_source:
                curr_source = "0"

            # Idempotency: if already running or connecting with the exact same source, do NOT restart the camera driver
            if (
                self.is_running
                and self.source_type == source_type
                and curr_source == norm_source
                and self.status in ("ONLINE", "CONNECTING")
            ):
                print(f"[StreamManager] Stream already active with source '{source_type}' ({norm_source}). Reusing active capture.", flush=True)
                return

            if self.is_running:
                self._stop_capture()

            self.source_type = source_type
            self.source_path = norm_source
            self.status = "CONNECTING"
            self.error_message = ""
            self.latest_frame = None
            self.is_running = True
            
        time.sleep(0.25)  # Allow Windows hardware driver to fully release before re-opening
        self.thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.thread.start()

    def stop(self):
        with self.lock:
            self._stop_capture()

    def _stop_capture(self):
        self.is_running = False
        if self.cap is not None:
            try:
                self.cap.release()
            except Exception:
                pass
            self.cap = None
        self.latest_frame = None
        self.status = "OFFLINE"

    def _get_capture_device(self) -> Tuple[Optional[cv2.VideoCapture], str]:
        """Resolves capture device based on source type with robust error protection and backend validation."""
        try:
            if self.source_type == "webcam":
                index = 0
                if self.source_path and str(self.source_path).isdigit():
                    index = int(self.source_path)

                # On Windows, try cv2.CAP_DSHOW first and verify frame read
                candidate_backends = [cv2.CAP_DSHOW, cv2.CAP_ANY]
                cap = None
                for backend in candidate_backends:
                    c = None
                    try:
                        c = cv2.VideoCapture(index, backend) if backend != cv2.CAP_ANY else cv2.VideoCapture(index)
                        if c is not None and c.isOpened():
                            c.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                            c.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                            ok, test_frame = c.read()
                            if ok and test_frame is not None and test_frame.size > 0:
                                cap = c
                                print(f"[StreamManager] Successfully initialized Webcam (index {index}) with backend {backend}.")
                                break
                            else:
                                c.release()
                    except (Exception, cv2.error, BaseException) as ex:
                        print(f"[StreamManager] Webcam backend probe failed: {ex}")
                        if c is not None:
                            try:
                                c.release()
                            except Exception:
                                pass
                        time.sleep(0.15)

                # If index 0 failed, try index 1 with DSHOW
                if cap is None and index == 0:
                    c = None
                    try:
                        c = cv2.VideoCapture(1, cv2.CAP_DSHOW)
                        if c is not None and c.isOpened():
                            c.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                            c.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                            ok, test_frame = c.read()
                            if ok and test_frame is not None and test_frame.size > 0:
                                cap = c
                                print(f"[StreamManager] Successfully initialized Webcam (index 1) with CAP_DSHOW.")
                            else:
                                c.release()
                    except (Exception, cv2.error, BaseException):
                        if c is not None:
                            try:
                                c.release()
                            except Exception:
                                pass

                if not cap or not cap.isOpened():
                    return None, f"Laptop Webcam (index {index}) not delivering frames. Ensure camera privacy shutter is open or switch to Demo Mode."
                return cap, ""

            elif self.source_type == "mobile":
                if not self.source_path:
                    return None, "Mobile camera stream URL is empty. Please enter e.g. http://192.168.1.10:8080/video"
                cap = cv2.VideoCapture(self.source_path)
                if not cap or not cap.isOpened():
                    return None, f"Unable to connect to mobile stream at '{self.source_path}'. Verify phone and laptop are on same Wi-Fi."
                return cap, ""

            else:  # demo video
                demo_file = DEMO_VIDEOS_DIR / (self.source_path if self.source_path else "border_patrol_demo.mp4")
                if not demo_file.exists():
                    mp4_files = list(DEMO_VIDEOS_DIR.glob("*.mp4"))
                    if mp4_files:
                        demo_file = mp4_files[0]
                    else:
                        return None, f"Demo video '{demo_file.name}' not found in demo/videos directory."
                
                cap = cv2.VideoCapture(str(demo_file))
                if not cap or not cap.isOpened():
                    return None, f"Could not open demo video file at {demo_file}"
                return cap, ""
        except Exception as ex:
            return None, f"Camera device initialization error: {str(ex)}"

    def _capture_loop(self):
        reconnect_attempts = 0
        
        while self.is_running:
            try:
                cap, err = self._get_capture_device()
                if cap is None:
                    with self.lock:
                        self.latest_frame = None
                        self.status = "ERROR"
                        self.error_message = (err or "Connection failed.") + " Attempting to reconnect..."
                    reconnect_attempts += 1
                    time.sleep(min(3.0, 1.0 + reconnect_attempts * 0.4))
                    continue

                self.cap = cap
                with self.lock:
                    self.status = "ONLINE"
                    self.error_message = ""
                reconnect_attempts = 0
                
                fps_counter = 0
                fps_timer = time.time()
                frame_delay = 0.033 if self.source_type == "demo" else 0.001
                consecutive_failures = 0

                while self.is_running:
                    ret, frame = cap.read()
                    if not ret or frame is None or frame.size == 0:
                        consecutive_failures += 1
                        if consecutive_failures < 8:
                            time.sleep(0.04)
                            continue
                        else:
                            if self.source_type == "demo" and self.is_demo_looping:
                                # Seamless loop demo video
                                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                                consecutive_failures = 0
                                time.sleep(0.05)
                                continue
                            else:
                                with self.lock:
                                    self.latest_frame = None
                                    self.status = "RECONNECTING"
                                    self.error_message = "CAMERA CONNECTION LOST. Attempting to reconnect..."
                                break

                    consecutive_failures = 0
                    with self.lock:
                        self.latest_frame = frame

                    # FPS calculation
                    fps_counter += 1
                    now = time.time()
                    if now - fps_timer >= 1.0:
                        self.fps = round(fps_counter / (now - fps_timer), 1)
                        fps_counter = 0
                        fps_timer = now

                    if self.source_type == "demo":
                        time.sleep(frame_delay)

                try:
                    cap.release()
                except Exception:
                    pass
                self.cap = None

                if self.is_running:
                    time.sleep(1.0)
            except Exception as e:
                print(f"[StreamManager] Stream loop exception: {e}")
                with self.lock:
                    self.latest_frame = None
                    self.status = "ERROR"
                    self.error_message = f"CAMERA CONNECTION LOST. Attempting to reconnect... ({e})"
                time.sleep(1.5)
                reconnect_attempts += 1

    def get_latest_frame(self) -> Optional[np.ndarray]:
        with self.lock:
            if self.status == "ONLINE" and self.latest_frame is not None:
                return self.latest_frame.copy()
            return None

    def get_status(self) -> dict:
        with self.lock:
            return {
                "source_type": self.source_type,
                "source_path": self.source_path,
                "status": self.status,
                "error_message": self.error_message,
                "fps": self.fps,
                "is_running": self.is_running
            }
