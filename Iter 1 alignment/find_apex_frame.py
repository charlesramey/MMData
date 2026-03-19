"""
Automatically find the video frame where the dog is jumping over the A-frame apex.

Uses background subtraction against frame 0 (empty scene) to detect the dog,
then finds the frame where the most foreground mass is concentrated at the
highest point near the horizontal center of the A-frame obstacle.

Usage:
  python find_apex_frame.py <video_path> [--label apex]

Prints the resulting frame number and saves a screenshot next to the video
as frame_<N>_<label>.png.
"""

import argparse
import os
import sys
import cv2
import numpy as np
from search_video_frames import save_frame, get_video_info


def find_aframe_apex_position(bg_frame):
    """Estimate the A-frame apex (x, y) from a background frame with no dog.

    Detects the highest edge point in the horizontal center of the frame,
    which corresponds to the top of the A-frame structure.
    """
    gray = cv2.cvtColor(bg_frame, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    h, w = edges.shape

    # Look for the apex in the center half of the frame
    col_start = w // 4
    col_end = 3 * w // 4
    center_edges = edges[:, col_start:col_end]

    # Find the topmost row with edge pixels (= apex of A-frame)
    rows_with_edges = np.where(center_edges.any(axis=1))[0]
    if len(rows_with_edges) == 0:
        # Fallback: assume center of frame
        return w // 2, h // 3

    apex_y = int(rows_with_edges[0])
    edge_cols = np.where(center_edges[apex_y] > 0)[0]
    apex_x = int(np.mean(edge_cols)) + col_start

    return apex_x, apex_y


def score_frame(frame_gray, bg_gray, apex_x, apex_y, roi_bounds):
    """Score a frame by how much foreground mass is near the apex.

    Returns (score, centroid_x, centroid_y) where score is higher when
    the dog's body is centered above the A-frame apex.
    """
    roi_top, roi_bot, roi_left, roi_right = roi_bounds

    diff = cv2.absdiff(bg_gray, frame_gray)
    _, thresh = cv2.threshold(diff, 30, 255, cv2.THRESH_BINARY)

    # Morphological cleanup to reduce noise
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)

    roi = thresh[roi_top:roi_bot, roi_left:roi_right]
    fg_pixels = np.sum(roi > 0)

    if fg_pixels < 20:
        return 0.0, 0, 0

    # Find centroid of foreground in ROI
    ys, xs = np.where(roi > 0)
    centroid_x = np.mean(xs) + roi_left
    centroid_y = np.mean(ys) + roi_top

    # Penalize horizontal distance from apex center
    h, w = bg_gray.shape
    horiz_offset = abs(centroid_x - apex_x) / w
    score = fg_pixels * (1.0 - 2.0 * horiz_offset)

    return max(score, 0.0), centroid_x, centroid_y


def find_apex_frame(video_path, label="apex"):
    fps, total = get_video_info(video_path)
    print(f"\nVideo: {video_path}")
    print(f"FPS: {fps}, Total frames: {total}, Duration: {total/fps:.2f}s")

    cap = cv2.VideoCapture(video_path)

    # Use frame 0 as background (scene with no dog)
    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
    ret, bg_frame = cap.read()
    if not ret:
        print("Error: could not read background frame")
        sys.exit(1)

    bg_gray = cv2.cvtColor(bg_frame, cv2.COLOR_BGR2GRAY)
    bg_gray = cv2.GaussianBlur(bg_gray, (21, 21), 0)
    h, w = bg_gray.shape

    # Locate the A-frame apex in the background
    apex_x, apex_y = find_aframe_apex_position(bg_frame)
    print(f"A-frame apex detected at ({apex_x}, {apex_y})")

    # Define ROI around the apex where the dog would be during the jump.
    # The dog's body extends above and slightly below the apex,
    # and within a horizontal band around the apex center.
    roi_top = max(0, apex_y - int(h * 0.20))
    roi_bot = min(h, apex_y + int(h * 0.10))
    roi_left = max(0, apex_x - int(w * 0.18))
    roi_right = min(w, apex_x + int(w * 0.18))
    roi_bounds = (roi_top, roi_bot, roi_left, roi_right)
    print(f"Search ROI: y=[{roi_top}:{roi_bot}], x=[{roi_left}:{roi_right}]")

    # --- Pass 1: Coarse scan (every 10 frames) ---
    print("\nPass 1: coarse scan (step=10)...")
    coarse_best_score = 0
    coarse_best_frame = 0

    for f in range(0, total, 10):
        cap.set(cv2.CAP_PROP_POS_FRAMES, f)
        ret, frame = cap.read()
        if not ret:
            continue
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)
        sc, _, _ = score_frame(gray, bg_gray, apex_x, apex_y, roi_bounds)
        if sc > coarse_best_score:
            coarse_best_score = sc
            coarse_best_frame = f

    print(f"  Best candidate: frame {coarse_best_frame} (score={coarse_best_score:.0f})")

    # --- Pass 2: Fine scan (every frame in ±30 around coarse best) ---
    fine_start = max(0, coarse_best_frame - 30)
    fine_end = min(total - 1, coarse_best_frame + 30)
    print(f"\nPass 2: fine scan frames [{fine_start}..{fine_end}] (step=1)...")

    fine_best_score = 0
    fine_best_frame = coarse_best_frame

    for f in range(fine_start, fine_end + 1):
        cap.set(cv2.CAP_PROP_POS_FRAMES, f)
        ret, frame = cap.read()
        if not ret:
            continue
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)
        sc, cx, cy = score_frame(gray, bg_gray, apex_x, apex_y, roi_bounds)
        if sc > fine_best_score:
            fine_best_score = sc
            fine_best_frame = f

    cap.release()

    print(f"  Best frame: {fine_best_frame} (score={fine_best_score:.0f})")

    # --- Save result ---
    result_frame = fine_best_frame
    print(f"\n>>> Apex frame number: {result_frame}")
    out_path = save_frame(video_path, result_frame, label)
    return result_frame, out_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Find the frame where the dog jumps over the A-frame apex."
    )
    parser.add_argument("video", help="Path to video file")
    parser.add_argument("--label", default="apex",
                        help="Label for saved screenshot (default: apex)")
    args = parser.parse_args()

    frame_num, path = find_apex_frame(args.video, args.label)
