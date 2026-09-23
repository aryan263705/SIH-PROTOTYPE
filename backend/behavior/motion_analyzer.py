import time
import math
from typing import Dict, Tuple, List, Optional, Any
from collections import deque

class TrackHistory:
    def __init__(self, maxlen: int = 30):
        self.positions: deque = deque(maxlen=maxlen)  # (x, y, timestamp)
        self.movement_state: str = "STATIONARY"
        self.relative_speed: float = 0.0
        self.direction: str = "NONE"
        self.created_at: float = time.time()

    def add_point(self, x: float, y: float):
        now = time.time()
        self.positions.append((x, y, now))
        self._update_kinematics()

    def _update_kinematics(self):
        if len(self.positions) < 3:
            self.movement_state = "STATIONARY"
            self.relative_speed = 0.0
            self.direction = "NONE"
            return

        # Calculate displacement over last ~0.5 to 1.0 seconds
        first_x, first_y, first_t = self.positions[0]
        last_x, last_y, last_t = self.positions[-1]
        
        dt = max(0.001, last_t - first_t)
        dx = last_x - first_x
        dy = last_y - first_y
        dist = math.hypot(dx, dy)
        
        # Pixels per second
        speed = dist / dt
        self.relative_speed = round(speed, 1)

        # Movement state heuristic
        if speed < 15.0:
            self.movement_state = "STATIONARY"
        elif speed < 45.0:
            self.movement_state = "SLOW MOVEMENT"
        elif speed < 150.0:
            self.movement_state = "WALKING"
        else:
            self.movement_state = "RAPID MOVEMENT"

        # Direction calculation
        if dist > 15:
            angle = math.degrees(math.atan2(-dy, dx))  # Standard Cartesian (0 is East, 90 is North)
            if -45 <= angle < 45:
                self.direction = "EAST"
            elif 45 <= angle < 135:
                self.direction = "NORTH"
            elif -135 <= angle < -45:
                self.direction = "SOUTH"
            else:
                self.direction = "WEST"
        else:
            self.direction = "STATIONARY"

class MotionAnalyzer:
    def __init__(self):
        self.tracks: Dict[str, TrackHistory] = {}

    def update(self, person_id: str, bbox: Tuple[int, int, int, int]) -> Dict[str, Any]:
        """
        bbox: (x1, y1, x2, y2)
        returns motion info dictionary
        """
        x1, y1, x2, y2 = bbox
        cx = (x1 + x2) / 2.0
        cy = (y1 + y2) / 2.0
        
        if person_id not in self.tracks:
            self.tracks[person_id] = TrackHistory()

        track = self.tracks[person_id]
        track.add_point(cx, cy)
        
        return {
            "movement_state": track.movement_state,
            "relative_speed": track.relative_speed,
            "direction": track.direction,
            "duration": round(time.time() - track.created_at, 1)
        }

    def cleanup_old_tracks(self, active_ids: List[str]):
        """Remove tracks no longer in active detections for a period"""
        stale_keys = [k for k in self.tracks if k not in active_ids]
        # Keep recent ones briefly or prune
        for k in stale_keys:
            if time.time() - self.tracks[k].positions[-1][2] > 2.5:
                del self.tracks[k]
