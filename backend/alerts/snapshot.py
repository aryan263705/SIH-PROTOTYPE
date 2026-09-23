import cv2
import datetime
import numpy as np
from pathlib import Path
from typing import Tuple, Optional, List
from backend.config import SNAPSHOTS_DIR

def capture_evidence_snapshot(
    frame,
    person_id: str,
    bbox: Tuple[int, int, int, int],
    alert_type: str,
    score: float,
    border_line: Optional[Tuple[Tuple[float, float], Tuple[float, float]]] = None,
    roi_polygon: Optional[List[Tuple[float, float]]] = None,
    extra_lines: Optional[List[str]] = None
) -> str:
    """
    Annotates and saves an evidence snapshot to disk, including active Virtual Border Line
    and Polygon Restricted Zone overlay so the breach is unambiguously visible.
    """
    snapshot_copy = frame.copy()
    h, w = snapshot_copy.shape[:2]
    
    x1, y1, x2, y2 = bbox
    x1, y1 = max(0, int(x1)), max(0, int(y1))
    x2, y2 = min(w - 1, int(x2)), min(h - 1, int(y2))

    # 1. Overlay Polygon Restricted Zone (ROI) if present
    if roi_polygon and len(roi_polygon) >= 3:
        roi_pts = np.array([[int(p[0] * w), int(p[1] * h)] for p in roi_polygon], dtype=np.int32)
        roi_overlay = snapshot_copy.copy()
        cv2.fillPoly(roi_overlay, [roi_pts], (0, 0, 180))
        # 25% alpha blend
        cv2.addWeighted(roi_overlay, 0.25, snapshot_copy, 0.75, 0, snapshot_copy)
        cv2.polylines(snapshot_copy, [roi_pts], True, (0, 50, 255), 2, cv2.LINE_AA)
        
        # Centroid for label
        cx_roi = int(np.mean(roi_pts[:, 0]))
        cy_roi = int(np.mean(roi_pts[:, 1]))
        cv2.putText(snapshot_copy, "[RESTRICTED ZONE]", (cx_roi - 70, cy_roi), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 200, 255), 1, cv2.LINE_AA)

    # 2. Overlay Virtual Border Line if present
    if border_line:
        p1 = (int(border_line[0][0] * w), int(border_line[0][1] * h))
        p2 = (int(border_line[1][0] * w), int(border_line[1][1] * h))
        cv2.line(snapshot_copy, p1, p2, (0, 180, 255), 3, cv2.LINE_AA)
        # Endpoints
        cv2.circle(snapshot_copy, p1, 5, (0, 255, 255), -1)
        cv2.circle(snapshot_copy, p2, 5, (0, 255, 255), -1)
        
        # Label along line
        mid_x = (p1[0] + p2[0]) // 2
        mid_y = (p1[1] + p2[1]) // 2
        cv2.putText(snapshot_copy, "[VIRTUAL BORDER]", (mid_x - 60, max(20, mid_y - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1, cv2.LINE_AA)

    # 3. Draw alert bounding box (Vibrant Crimson Red)
    cv2.rectangle(snapshot_copy, (x1, y1), (x2, y2), (0, 0, 235), 3)
    
    # Corner brackets for tactical surveillance look
    corner_len = min(25, (x2 - x1) // 3, (y2 - y1) // 3)
    cv2.line(snapshot_copy, (x1, y1), (x1 + corner_len, y1), (0, 255, 255), 3)
    cv2.line(snapshot_copy, (x1, y1), (x1, y1 + corner_len), (0, 255, 255), 3)
    cv2.line(snapshot_copy, (x2, y1), (x2 - corner_len, y1), (0, 255, 255), 3)
    cv2.line(snapshot_copy, (x2, y1), (x2, y1 + corner_len), (0, 255, 255), 3)
    cv2.line(snapshot_copy, (x1, y2), (x1 + corner_len, y2), (0, 255, 255), 3)
    cv2.line(snapshot_copy, (x1, y2), (x1, y1 - corner_len), (0, 255, 255), 3)
    cv2.line(snapshot_copy, (x2, y2), (x2 - corner_len, y2), (0, 255, 255), 3)
    cv2.line(snapshot_copy, (x2, y2), (x2, y2 - corner_len), (0, 255, 255), 3)

    # 4. Draw tracking contact point (bottom-center of bounding box)
    anchor_pt = ((x1 + x2) // 2, y2)
    cv2.circle(snapshot_copy, anchor_pt, 6, (0, 255, 255), -1)
    cv2.circle(snapshot_copy, anchor_pt, 2, (0, 0, 0), -1)
    cv2.putText(snapshot_copy, "TRACK POINT", (anchor_pt[0] - 38, min(h - 10, anchor_pt[1] + 16)), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 255, 255), 1, cv2.LINE_AA)

    # 5. Top HUD Evidence Banner
    banner_height = 50
    cv2.rectangle(snapshot_copy, (0, 0), (w, banner_height), (15, 23, 42), -1)
    cv2.line(snapshot_copy, (0, banner_height), (w, banner_height), (0, 0, 220), 2)
    
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    header_text = f"EVIDENCE CAPTURE | {alert_type.upper()} | SCORE: {score:.1f}%"
    cv2.putText(
        snapshot_copy,
        header_text,
        (16, 32),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (0, 50, 255),
        2,
        cv2.LINE_AA
    )
    cv2.putText(
        snapshot_copy,
        f"TIME: {now_str}",
        (w - 230, 32),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (200, 200, 200),
        1,
        cv2.LINE_AA
    )
    
    # 6. Target Tag above box
    tag_text = f"TARGET: #{person_id}"
    tag_size = cv2.getTextSize(tag_text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
    tag_y1 = max(banner_height + 10, y1 - tag_size[1] - 8)
    cv2.rectangle(
        snapshot_copy,
        (x1, tag_y1),
        (x1 + tag_size[0] + 10, tag_y1 + tag_size[1] + 8),
        (0, 0, 200),
        -1
    )
    cv2.putText(
        snapshot_copy,
        tag_text,
        (x1 + 5, tag_y1 + tag_size[1] + 3),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (255, 255, 255),
        2,
        cv2.LINE_AA
    )
    
    # Extra explainability lines
    if extra_lines:
        y_off = banner_height + 18
        for line in extra_lines[:4]:
            cv2.putText(snapshot_copy, str(line), (16, y_off), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (220, 220, 220), 1, cv2.LINE_AA)
            y_off += 18

    # 7. Save to disk
    timestamp_file = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
    safe_pid = str(person_id).replace("#", "")
    filename = f"alert_{timestamp_file}_person_{safe_pid}.jpg"
    filepath = SNAPSHOTS_DIR / filename
    
    cv2.imwrite(str(filepath), snapshot_copy)
    return filename
