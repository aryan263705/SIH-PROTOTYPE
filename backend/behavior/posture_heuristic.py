from typing import Tuple, Dict, Any

class PostureHeuristic:
    def __init__(self, aspect_ratio_thresh: float = 0.85, score_thresh: float = 65.0):
        self.aspect_ratio_thresh = aspect_ratio_thresh
        self.score_thresh = score_thresh

    def analyze(
        self,
        bbox: Tuple[int, int, int, int],
        frame_shape: Tuple[int, int],
        movement_state: str = "NORMAL"
    ) -> Dict[str, Any]:
        """
        Prototype geometry heuristic. A person merely appearing is NOT suspicious.
        Walking upright remains NORMAL.
        """
        h_frame, w_frame = frame_shape
        x1, y1, x2, y2 = bbox

        box_w = max(1.0, float(x2 - x1))
        box_h = max(1.0, float(y2 - y1))
        ar = box_w / box_h
        relative_height = box_h / max(1.0, float(h_frame))
        bottom_y_norm = float(y2) / max(1.0, float(h_frame))

        if ar <= 0.55:
            raw_score = (ar / 0.55) * 20.0
            label = "NORMAL"
        elif ar <= self.aspect_ratio_thresh:
            t = (ar - 0.55) / max(0.01, (self.aspect_ratio_thresh - 0.55))
            raw_score = 20.0 + t * 30.0
            label = "NORMAL"
        else:
            t = min(1.0, (ar - self.aspect_ratio_thresh) / 0.40)
            raw_score = 55.0 + t * 35.0
            label = "LOW POSTURE"

        if bottom_y_norm > 0.60 and relative_height < 0.32 and ar > 0.80:
            raw_score += 12.0
            label = "POSSIBLE CRAWLING"

        if ar > 0.90 and movement_state in ["SLOW MOVEMENT", "STATIONARY"]:
            raw_score += 8.0
            if label == "LOW POSTURE":
                label = "POSSIBLE CRAWLING"

        behavior_score = round(min(100.0, max(0.0, raw_score)), 1)

        # Walking / upright people must not be flagged suspicious
        is_suspicious = behavior_score >= self.score_thresh and ar >= self.aspect_ratio_thresh

        if not is_suspicious:
            if movement_state == "WALKING":
                label = "WALKING"
            elif movement_state == "SLOW MOVEMENT":
                label = "SLOW MOVEMENT"
            elif ar <= self.aspect_ratio_thresh:
                label = "NORMAL"

        if is_suspicious and ar >= 0.95:
            label = "POSSIBLE CRAWLING"
        elif is_suspicious:
            label = "LOW POSTURE"

        return {
            "posture_label": label,
            "behavior_score": behavior_score,
            "aspect_ratio": round(ar, 2),
            "is_suspicious": is_suspicious,
            "box_dims": (int(box_w), int(box_h))
        }
