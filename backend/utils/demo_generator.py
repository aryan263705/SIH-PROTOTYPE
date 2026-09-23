import cv2
import numpy as np
import os
from pathlib import Path
from backend.config import DEMO_VIDEOS_DIR, config

def generate_synthetic_demo_video(output_filename: str = "border_patrol_demo.mp4"):
    """
    Presentation demo (640x480 @ 15 FPS) using the SAME real YOLO pipeline later.

    Phase 0: empty scene (no person)
    Phase 1: person enters and walks in the safe zone (above the 65% virtual border)
    Phase 2: person approaches the virtual border (still no alert)
    Phase 3: person crosses into the restricted zone and remains there
    """
    output_path = DEMO_VIDEOS_DIR / output_filename

    width, height = 640, 480
    fps = 15
    duration_secs = 28
    total_frames = fps * duration_secs
    border_y = int(config.boundary_position * height)

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))

    base_bg = np.zeros((height, width, 3), dtype=np.uint8)
    for y in range(210):
        intensity = int(22 + (y / 210.0) * 30)
        base_bg[y, :] = [intensity, int(intensity * 0.92), int(intensity * 0.75)]
    for y in range(210, height):
        intensity = int(32 + ((y - 210) / 270.0) * 28)
        base_bg[y, :] = [int(intensity * 0.85), intensity, int(intensity * 1.05)]

    for x in range(25, width + 30, 65):
        cv2.line(base_bg, (x, 150), (x, 310), (60, 65, 70), 3)
        cv2.circle(base_bg, (x, 150), 3, (80, 85, 90), -1)
    for y in [165, 195, 225, 255, 285]:
        for x in range(0, width, 14):
            cv2.line(base_bg, (x, y), (x + 12, y + (2 if (x // 14) % 2 == 0 else -2)), (75, 80, 85), 1)

    for x in range(0, width, 30):
        cv2.line(base_bg, (x, border_y), (x + 16, border_y), (20, 180, 220), 2)

    person_crop = None
    try:
        import ultralytics
        p_asset = os.path.join(os.path.dirname(ultralytics.__file__), "assets", "bus.jpg")
        bus_img = cv2.imread(p_asset)
        if bus_img is not None:
            person_crop = bus_img[235:735, 45:240]
    except Exception:
        person_crop = None

    if person_crop is None:
        person_crop = np.zeros((160, 62, 3), dtype=np.uint8)
        person_crop[:] = (40, 60, 180)
        cv2.circle(person_crop, (31, 22), 14, (60, 90, 220), -1)

    for f_idx in range(total_frames):
        frame = base_bg.copy()
        cv2.putText(frame, "CAM-04 PERIMETER WEST [SECTOR B-7]", (18, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (0, 255, 180), 1, cv2.LINE_AA)
        cv2.putText(frame, f"REC [LIVE] F#{f_idx:04d}", (width - 170, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 100, 255), 1, cv2.LINE_AA)

        # Empty for first ~4 seconds
        if f_idx >= 60:
            sprite = cv2.resize(person_crop, (62, 160))
            sh, sw = sprite.shape[:2]
            t = (f_idx - 60) / float(max(1, total_frames - 60))
            # Walk from upper (safe) area downward across the 65% line
            px = int(220 + t * 40)
            start_y = 70
            end_y = min(height - sh - 8, border_y + 40)
            py = int(start_y + t * (end_y - start_y))
            walk_bob = int(abs(np.sin(f_idx * 0.35)) * 4)
            cur_y = max(0, py - walk_bob)
            if cur_y + sh < height and 0 <= px and px + sw < width:
                frame[cur_y:cur_y + sh, px:px + sw] = sprite

        writer.write(frame)

    writer.release()
    print(f"[Demo Generator] Calibrated demo video generated at {output_path}")
    return str(output_path)

if __name__ == "__main__":
    generate_synthetic_demo_video()
