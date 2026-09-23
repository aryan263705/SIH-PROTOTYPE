from typing import List, Tuple, Optional, Dict, Any
from collections import deque
import time

from backend.config import config


def _clamp01(v: float) -> float:
    return max(0.0, min(1.0, float(v)))


def line_y_at_x(norm_x: float, line: Tuple[Tuple[float, float], Tuple[float, float]]) -> float:
    """Interpolate the border's normalized Y at a given normalized X (horizontal-friendly)."""
    a, b = line
    dx = b[0] - a[0]
    if abs(dx) < 1e-6:
        return (a[1] + b[1]) / 2.0
    t = (norm_x - a[0]) / dx
    return a[1] + t * (b[1] - a[1])


class BoundaryAnalyzer:
    def __init__(self):
        # Default configurable horizontal virtual border
        pos = _clamp01(config.boundary_position)
        self.border_line: Optional[Tuple[Tuple[float, float], Tuple[float, float]]] = (
            (0.0, pos),
            (1.0, pos),
        )
        self.roi_polygon: List[Tuple[float, float]] = []
        self.monitored_direction: str = config.monitored_direction

        # Track history: deque of (norm_cx, norm_cy, timestamp)
        self.track_positions: Dict[str, deque] = {}
        self.crossed_edge_at: Dict[str, float] = {}
        self.roi_inside_tracks: Dict[str, float] = {}
        self.was_ever_outside: Dict[str, bool] = {}

    def set_boundary_position(self, position: float, direction: Optional[str] = None):
        pos = _clamp01(position)
        config.boundary_position = pos
        self.border_line = ((0.0, pos), (1.0, pos))
        if direction in ("top_to_bottom", "bottom_to_top"):
            self.monitored_direction = direction
            config.monitored_direction = direction
        self.crossed_edge_at.clear()
        self.was_ever_outside.clear()

    def set_border_line(self, pt1: Tuple[float, float], pt2: Tuple[float, float]):
        self.border_line = (tuple(pt1), tuple(pt2))
        mid_y = (float(pt1[1]) + float(pt2[1])) / 2.0
        config.boundary_position = _clamp01(mid_y)
        self.crossed_edge_at.clear()
        self.was_ever_outside.clear()
        print(f"[Boundary] Virtual border line defined: {self.border_line}")

    def clear_border_line(self):
        self.border_line = None
        self.crossed_edge_at.clear()
        self.was_ever_outside.clear()

    def set_roi_polygon(self, polygon: List[Tuple[float, float]]):
        if len(polygon) >= 3:
            self.roi_polygon = list(polygon)
            print(f"[Boundary] Restricted Zone (ROI) defined with {len(polygon)} vertices.")
        else:
            self.roi_polygon = []

    def clear_roi_polygon(self):
        self.roi_polygon = []
        self.roi_inside_tracks.clear()

    def reset(self):
        pos = _clamp01(config.boundary_position)
        self.border_line = ((0.0, pos), (1.0, pos))
        self.roi_polygon = []
        self.track_positions.clear()
        self.crossed_edge_at.clear()
        self.roi_inside_tracks.clear()
        self.was_ever_outside.clear()

    def _side(self, cy: float, boundary_y: float) -> str:
        if self.monitored_direction == "bottom_to_top":
            return "RESTRICTED" if cy <= boundary_y else "OUTSIDE"
        return "RESTRICTED" if cy >= boundary_y else "OUTSIDE"

    def update_track_point(self, person_id: str, norm_x: float, norm_y: float):
        if person_id not in self.track_positions:
            self.track_positions[person_id] = deque(maxlen=30)
        self.track_positions[person_id].append((norm_x, norm_y, time.time()))

    def check_boundary_status(
        self,
        person_id: str,
        bbox: Tuple[int, int, int, int],
        frame_shape: Tuple[int, int]
    ) -> Dict[str, Any]:
        """
        Uses bounding-box CENTER (not a fake point) for line-crossing.
        Crossing is an edge event: previous side OUTSIDE and current side RESTRICTED.
        """
        h, w = frame_shape
        x1, y1, x2, y2 = bbox

        cx = (x1 + x2) / 2.0
        cy = (y1 + y2) / 2.0
        norm_x = _clamp01(cx / max(1.0, float(w)))
        norm_y = _clamp01(cy / max(1.0, float(h)))

        self.update_track_point(person_id, norm_x, norm_y)
        positions = self.track_positions[person_id]

        crossed_border = False
        approaching = False
        in_restricted = False
        side_of_border = "NONE"
        crossing_direction = ""
        moving_toward_border = False
        now = time.time()

        if self.border_line is not None:
            boundary_y = line_y_at_x(norm_x, self.border_line)
            curr_side = self._side(norm_y, boundary_y)
            side_of_border = curr_side
            in_restricted = curr_side == "RESTRICTED"

            if curr_side == "OUTSIDE":
                self.was_ever_outside[person_id] = True

            crossing_direction = "OUTSIDE → RESTRICTED ZONE"

            if len(positions) >= 2:
                prev_x, prev_y, _ = positions[-2]
                prev_boundary = line_y_at_x(prev_x, self.border_line)
                prev_side = self._side(prev_y, prev_boundary)

                # Actual crossing: was outside, now inside. Not merely near the line.
                if prev_side == "OUTSIDE" and curr_side == "RESTRICTED":
                    last = self.crossed_edge_at.get(person_id, 0.0)
                    if now - last > 0.4:
                        crossed_border = True
                        self.crossed_edge_at[person_id] = now

                dy = norm_y - prev_y
                if self.monitored_direction == "top_to_bottom":
                    moving_toward_border = dy > 0.002
                else:
                    moving_toward_border = dy < -0.002

                dist = abs(norm_y - boundary_y)
                approaching = (
                    curr_side == "OUTSIDE"
                    and moving_toward_border
                    and dist <= config.approach_band
                )

        in_roi = False
        if len(self.roi_polygon) >= 3:
            in_roi = _point_in_polygon((norm_x, norm_y), self.roi_polygon)
            if in_roi:
                if person_id not in self.roi_inside_tracks:
                    self.roi_inside_tracks[person_id] = now
            else:
                self.roi_inside_tracks.pop(person_id, None)

        return {
            "crossed_border": crossed_border,
            "in_roi": in_roi,
            "in_restricted": in_restricted or in_roi,
            "approaching": approaching,
            "anchor_norm": (norm_x, norm_y),
            "center_norm": (round(norm_x, 4), round(norm_y, 4)),
            "side_of_border": side_of_border if side_of_border != "NONE" else ("RESTRICTED" if in_roi else "OUTSIDE"),
            "crossing_direction": crossing_direction if (crossed_border or in_restricted) else (
                "APPROACHING BORDER" if approaching else "OUTSIDE"
            ),
            "was_ever_outside": self.was_ever_outside.get(person_id, False),
            "roi_duration": round(now - self.roi_inside_tracks[person_id], 1) if in_roi and person_id in self.roi_inside_tracks else 0.0
        }

    def cleanup_old_tracks(self, active_ids: List[str]):
        stale_keys = [k for k in self.track_positions if k not in active_ids]
        for k in stale_keys:
            if time.time() - self.track_positions[k][-1][2] > config.track_lost_seconds:
                del self.track_positions[k]
                self.crossed_edge_at.pop(k, None)
                self.roi_inside_tracks.pop(k, None)
                self.was_ever_outside.pop(k, None)


def _point_in_polygon(point: Tuple[float, float], polygon: List[Tuple[float, float]]) -> bool:
    if len(polygon) < 3:
        return False
    x, y = point
    inside = False
    n = len(polygon)
    p1x, p1y = polygon[0]
    for i in range(1, n + 1):
        p2x, p2y = polygon[i % n]
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y
    return inside
