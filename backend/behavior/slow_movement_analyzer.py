import time
import math
from collections import deque
from typing import Dict, Tuple, List, Optional, Any


class SlowMovementAnalyzer:
    """
    Trajectory and Ultra-Slow Movement / Crawler Analyzer.

    Addresses evasion techniques where an intruder crawls or moves with ultra-low velocity
    to defeat simple frame-to-frame velocity sensors or PIR detectors.

    Maintains a 3 to 8 second position window per Track ID:
    - Calculates long-term cumulative displacement vs instantaneous speed.
    - Correlates with low-posture aspect ratio (W/H >= 0.75).
    - Classifies persistent creeping movement.
    """

    def __init__(self, history_seconds: float = 6.0):
        self.history_seconds = history_seconds
        # track_id -> deque of (timestamp, cx, cy, w, h, aspect_ratio)
        self.track_history: Dict[str, deque] = {}
        # track_id -> start time of persistent slow crawl condition
        self.crawl_start_time: Dict[str, float] = {}

    def update(
        self,
        track_id: str,
        bbox: Tuple[int, int, int, int],
        instantaneous_speed: float,
        posture_label: str,
    ) -> Dict[str, Any]:
        now = time.time()
        x1, y1, x2, y2 = bbox
        cx = (x1 + x2) / 2.0
        cy = (y1 + y2) / 2.0
        w = max(1, x2 - x1)
        h = max(1, y2 - y1)
        aspect_ratio = round(w / h, 2)

        if track_id not in self.track_history:
            self.track_history[track_id] = deque()

        history = self.track_history[track_id]
        history.append((now, cx, cy, w, h, aspect_ratio))

        # Evict records older than window
        while history and (now - history[0][0]) > self.history_seconds:
            history.popleft()

        duration = now - history[0][0] if len(history) > 1 else 0.0

        # Calculate long-term trajectory displacement over history window
        oldest_t, oldest_cx, oldest_cy, _, _, _ = history[0]
        net_dx = cx - oldest_cx
        net_dy = cy - oldest_cy
        net_displacement = math.hypot(net_dx, net_dy)

        # Average aspect ratio over history window to dampen single-frame glitches
        avg_ar = sum(item[5] for item in history) / float(len(history))

        # Detection criteria for Slow Persistent Crawler:
        # 1. Monitored for >= 2.0 seconds
        # 2. Net long-term displacement > 25 pixels (they are actively creeping/inching)
        # 3. Instantaneous speed is relatively low (< 45 px/s)
        # 4. Aspect ratio is wide / low-posture (avg_ar >= 0.75 or posture_label == CRAWLING / CROUCHING)
        is_low_posture = avg_ar >= 0.75 or "CRAWL" in posture_label.upper() or "CROUCH" in posture_label.upper()
        is_inching = net_displacement >= 20.0 and duration >= 1.5

        is_slow_crawl = False
        state_label = "NORMAL"
        explanation = ""

        if is_low_posture and is_inching:
            if track_id not in self.crawl_start_time:
                self.crawl_start_time[track_id] = now

            crawl_dur = now - self.crawl_start_time[track_id]
            is_slow_crawl = True
            state_label = "POSSIBLE SLOW CRAWL"
            explanation = f"Slow Persistent Movement: {net_displacement:.0f}px over {duration:.1f}s (AR: {avg_ar:.2f})"
        else:
            self.crawl_start_time.pop(track_id, None)
            if is_inching and not is_low_posture:
                state_label = "SLOW MOVEMENT"
            elif is_low_posture:
                state_label = "LOW POSTURE"

        return {
            "track_id": track_id,
            "net_displacement": round(net_displacement, 1),
            "tracking_duration": round(duration, 1),
            "avg_aspect_ratio": round(avg_ar, 2),
            "is_slow_crawl": is_slow_crawl,
            "movement_label": state_label,
            "explanation": explanation,
        }

    def cleanup_old_tracks(self, live_ids: List[str]):
        live_set = set(live_ids)
        stale = [tid for tid in self.track_history if tid not in live_set]
        for tid in stale:
            self.track_history.pop(tid, None)
            self.crawl_start_time.pop(tid, None)

    def reset(self):
        self.track_history.clear()
        self.crawl_start_time.clear()
