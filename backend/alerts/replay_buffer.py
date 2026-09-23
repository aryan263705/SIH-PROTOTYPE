import os
import time
import datetime
import threading
from collections import deque
from pathlib import Path
from typing import Optional, List, Tuple
import cv2
import numpy as np

from backend.config import SNAPSHOTS_DIR

REPLAYS_DIR = SNAPSHOTS_DIR / "replays"
REPLAYS_DIR.mkdir(parents=True, exist_ok=True)


class RollingEventReplayBuffer:
    """
    Lightweight Rolling Forensic Replay Buffer.

    Maintains ~30 seconds of rolling video in memory as compressed JPEGs (~15MB RAM).
    When an intrusion or confirmed alert fires:
    - Extracts pre-event frames (~8s before trigger)
    - Captures post-event frames (~5s after trigger)
    - Exports a standalone H.264/MP4 forensic clip into snapshots/replays/
    - Exposes the clip URL to the command-center for one-click operator playback.
    """

    def __init__(self, max_seconds: float = 30.0, target_fps: float = 12.0):
        self.max_seconds = max_seconds
        self.target_fps = target_fps
        self.max_frames = int(max_seconds * target_fps)
        # deque of (timestamp, jpeg_bytes, w, h)
        self.buffer = deque(maxlen=self.max_frames)
        self.lock = threading.Lock()
        self.last_append_time = 0.0

    def push_frame(self, frame: np.ndarray):
        now = time.time()
        # Rate-limit to target FPS to preserve memory and CPU
        if now - self.last_append_time < (1.0 / self.target_fps):
            return

        self.last_append_time = now
        h, w = frame.shape[:2]
        _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 72])
        with self.lock:
            self.buffer.append((now, buf.tobytes(), w, h))

    def trigger_replay_export(
        self,
        person_id: str,
        event_name: str,
        pre_seconds: float = 8.0,
        post_seconds: float = 4.0,
    ) -> str:
        """
        Saves pre-event window immediately, schedules brief post-event capture,
        and compiles into an MP4 clip.
        """
        now = time.time()
        start_t = now - pre_seconds

        with self.lock:
            pre_frames = [item for item in self.buffer if item[0] >= start_t]

        timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_event = "".join(c if c.isalnum() else "_" for c in event_name).lower()
        filename = f"replay_{timestamp_str}_p{person_id}_{safe_event}.mp4"
        rel_path = f"replays/{filename}"
        output_path = REPLAYS_DIR / filename

        # Export in background thread to avoid blocking the real-time analytics loop
        def export_worker():
            # Wait for post_seconds while new frames arrive in buffer
            time.sleep(post_seconds)
            with self.lock:
                all_frames = [item for item in self.buffer if item[0] >= start_t]

            if not all_frames:
                all_frames = pre_frames

            if not all_frames:
                return

            w, h = all_frames[0][2], all_frames[0][3]
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            writer = cv2.VideoWriter(str(output_path), fourcc, self.target_fps, (w, h))

            for t, jpeg_bytes, fw, fh in all_frames:
                nparr = np.frombuffer(jpeg_bytes, np.uint8)
                f = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                if f is not None:
                    # Overlay timestamp watermark on replay
                    t_str = datetime.datetime.fromtimestamp(t).strftime("%H:%M:%S.%f")[:-4]
                    cv2.putText(
                        f,
                        f"FORENSIC REPLAY | T: {t_str} | TARGET #{person_id}",
                        (14, 24),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.45,
                        (0, 215, 255),
                        1,
                        cv2.LINE_AA,
                    )
                    writer.write(f)

            writer.release()

            # Transcode to universal browser-compatible H.264 (Chrome, Edge, Safari, Firefox)
            try:
                import imageio_ffmpeg
                import subprocess
                ffmpeg_bin = imageio_ffmpeg.get_ffmpeg_exe()
                h264_tmp = output_path.with_suffix(".tmp_h264.mp4")
                cmd = [
                    ffmpeg_bin,
                    "-y",
                    "-i", str(output_path),
                    "-c:v", "libx264",
                    "-pix_fmt", "yuv420p",
                    "-movflags", "+faststart",
                    "-preset", "ultrafast",
                    "-crf", "23",
                    str(h264_tmp)
                ]
                res = subprocess.run(cmd, capture_output=True, timeout=15)
                if res.returncode == 0 and h264_tmp.exists() and h264_tmp.stat().st_size > 0:
                    h264_tmp.replace(output_path)
            except Exception as ex:
                print(f"[Replay Buffer] H.264 web transcode warning: {ex}")

            print(f"[Replay Buffer] Successfully exported forensic event clip: {output_path}")

        threading.Thread(target=export_worker, daemon=True).start()
        return rel_path

    def clear(self):
        with self.lock:
            self.buffer.clear()
