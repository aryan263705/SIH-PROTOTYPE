import time
from typing import Dict, Any, Tuple
import cv2
import numpy as np


class CameraTamperDetector:
    """
    Edge-level Camera & Node Tamper Detection.

    Monitors frame-level optical characteristics to detect physical sabotage:
    - Lens Covering / Occlusion / Spray Paint (severe drop in luminance or texture)
    - Camera Blinding (extreme saturation from high-intensity light source)
    - Deflection / Lens Obscuration (Laplacian texture variance collapse)

    Dampened over a temporal window to eliminate false positives on lighting shifts.
    """

    def __init__(self, persistence_seconds: float = 1.2):
        self.persistence_seconds = persistence_seconds
        self.tamper_start_time: float = 0.0
        self.is_tampered: bool = False
        self.tamper_reason: str = ""

    def evaluate(self, frame: np.ndarray) -> Tuple[bool, str, Dict[str, Any]]:
        now = time.time()
        # Downsample for quick evaluation
        small = cv2.resize(frame, (160, 120))
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)

        mean_luma = float(np.mean(gray))
        laplacian_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())

        # Occlusion criteria:
        # 1. Total Blackout (Covered lens): mean_luma < 6.0
        # 2. Extreme Blinding: mean_luma > 250.0
        # 3. Defocused / Spray-painted: laplacian_var < 5.0 and 15 < mean_luma < 240
        suspicious = False
        reason = ""

        if mean_luma < 6.0:
            suspicious = True
            reason = "Lens Occlusion (Total Blackout)"
        elif mean_luma > 250.0:
            suspicious = True
            reason = "Sensor Blinding (Extreme Saturation)"
        elif laplacian_var < 4.0 and (15.0 < mean_luma < 235.0):
            suspicious = True
            reason = "Optical Deflection / Lens Obscuration"

        if suspicious:
            if self.tamper_start_time == 0.0:
                self.tamper_start_time = now
            elapsed = now - self.tamper_start_time
            if elapsed >= self.persistence_seconds:
                self.is_tampered = True
                self.tamper_reason = reason
        else:
            self.tamper_start_time = 0.0
            self.is_tampered = False
            self.tamper_reason = ""

        return self.is_tampered, self.tamper_reason, {
            "mean_luminance": round(mean_luma, 1),
            "laplacian_variance": round(laplacian_var, 1),
            "tamper_detected": self.is_tampered,
            "tamper_reason": self.tamper_reason,
        }

    def reset(self):
        self.tamper_start_time = 0.0
        self.is_tampered = False
        self.tamper_reason = ""
