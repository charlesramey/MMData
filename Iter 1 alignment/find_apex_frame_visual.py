"""
Find the apex frame using the same progressive visual-narrowing algorithm
that was used manually: extract frames at decreasing intervals, review
each pass to narrow the search range, then save the final result.

Pass structure (mirrors the manual procedure):
  Pass 1: Coarse scan   — every 50 frames across the full video
  Pass 2: Medium scan   — every 20 frames in the candidate region
  Pass 3: Fine scan     — every 5 frames in the narrowed region
  Pass 4: Frame-by-frame — every frame in a tight window

At each pass, extracted frames are saved to a subdirectory for review.
The script selects the best candidate at each pass using a background-
subtraction scoring heuristic (proxy for visual inspection), then
narrows the search window for the next pass.

Uses search_video_frames.py for frame extraction and saving.

Usage:
  python find_apex_frame_visual.py <video_path> [--label apex] [--output-dir /tmp/apex_search]

Prints the resulting frame number and saves a screenshot next to the video.
"""

import argparse
import os
import sys
import shutil
import cv2
import numpy as np
from search_video_frames import extract_frames, save_frame, get_video_info


# ---------------------------------------------------------------------------
# Scoring helpers (proxy for visual inspection)
# ---------------------------------------------------------------------------

def _prepare_background(video_path):
    """Read frame 0 as the background (empty scene, no dog)."""
    cap = cv2.VideoCapture(video_path)
    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
    ret, bg = cap.read()
    cap.release()
    if not ret:
        print("Error: could not read background frame")
        sys.exit(1)
    bg_gray = cv2.cvtColor(bg, cv2.COLOR_BGR2GRAY)
    bg_gray = cv2.GaussianBlur(bg_gray, (21, 21), 0)
    return bg, bg_gray


def _detect_apex_position(bg_frame):
    """Find the A-frame apex (x, y) from the background frame."""
    gray = cv2.cvtColor(bg_frame, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    h, w = edges.shape
    col_start, col_end = w // 4, 3 * w // 4
    center = edges[:, col_start:col_end]
    rows = np.where(center.any(axis=1))[0]
    if len(rows) == 0:
        return w // 2, h // 3
    apex_y = int(rows[0])
    cols = np.where(center[apex_y] > 0)[0]
    apex_x = int(np.mean(cols)) + col_start
    return apex_x, apex_y


def _build_roi(apex_x, apex_y, h, w):
    """Build the region of interest around the apex for scoring."""
    roi_top = max(0, apex_y - int(h * 0.20))
    roi_bot = min(h, apex_y + int(h * 0.10))
    roi_left = max(0, apex_x - int(w * 0.18))
    roi_right = min(w, apex_x + int(w * 0.18))
    return roi_top, roi_bot, roi_left, roi_right


def _score_image(image_path, bg_gray, apex_x, roi_bounds):
    """Score a single extracted frame image. Higher = more dog mass near apex."""
    frame = cv2.imread(image_path)
    if frame is None:
        return 0.0
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (21, 21), 0)

    roi_top, roi_bot, roi_left, roi_right = roi_bounds
    diff = cv2.absdiff(bg_gray, gray)
    _, thresh = cv2.threshold(diff, 30, 255, cv2.THRESH_BINARY)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)

    roi = thresh[roi_top:roi_bot, roi_left:roi_right]
    fg = np.sum(roi > 0)
    if fg < 20:
        return 0.0

    xs = np.where(roi.any(axis=0))[0]
    if len(xs) == 0:
        return 0.0
    centroid_x = np.mean(xs) + roi_left
    h, w = bg_gray.shape
    offset = abs(centroid_x - apex_x) / w
    return max(fg * (1.0 - 2.0 * offset), 0.0)


def _best_in_pass(extracted, bg_gray, apex_x, roi_bounds, pass_name):
    """Pick the best frame from extracted list, print scores."""
    scores = []
    for frame_num, path in extracted:
        sc = _score_image(path, bg_gray, apex_x, roi_bounds)
        scores.append((frame_num, sc))

    scores.sort(key=lambda x: -x[1])
    best_frame, best_score = scores[0]

    # Show top candidates
    print(f"\n  {pass_name} — top candidates:")
    for f, sc in scores[:5]:
        marker = " <<<" if f == best_frame else ""
        print(f"    Frame {f:>5d}  score={sc:>8.0f}{marker}")

    return best_frame


# ---------------------------------------------------------------------------
# Main search procedure
# ---------------------------------------------------------------------------

PASSES = [
    # (name,       step, window_radius)
    ("Pass 1: coarse (step=50)",    50, None),   # full video
    ("Pass 2: medium (step=20)",    20, 150),    # ±150 around best
    ("Pass 3: fine (step=5)",        5,  50),    # ±50 around best
    ("Pass 4: frame-by-frame",       1,  15),    # ±15 around best
]


def find_apex_frame_visual(video_path, label="apex", output_dir="/tmp/apex_search"):
    fps, total = get_video_info(video_path)
    print(f"\nVideo: {video_path}")
    print(f"FPS: {fps}, Total frames: {total}, Duration: {total/fps:.2f}s")

    # Prepare scoring context
    bg_frame, bg_gray = _prepare_background(video_path)
    apex_x, apex_y = _detect_apex_position(bg_frame)
    h, w = bg_gray.shape
    roi_bounds = _build_roi(apex_x, apex_y, h, w)
    print(f"A-frame apex at ({apex_x}, {apex_y}), ROI: {roi_bounds}")

    # Clean output directory
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)

    best_frame = 0
    search_start = 0
    search_end = total - 1

    for pass_name, step, window in PASSES:
        if window is not None:
            search_start = max(0, best_frame - window)
            search_end = min(total - 1, best_frame + window)

        pass_dir = os.path.join(output_dir, pass_name.split(":")[0].strip().replace(" ", "_"))
        print(f"\n{'='*60}")
        print(f"{pass_name}  [frames {search_start}..{search_end}]")
        print(f"{'='*60}")

        extracted = extract_frames(video_path, pass_dir, search_start, search_end, step)

        if not extracted:
            print("  No frames extracted, keeping previous best")
            continue

        best_frame = _best_in_pass(extracted, bg_gray, apex_x, roi_bounds, pass_name)
        print(f"\n  >>> Best frame this pass: {best_frame}")

    # Save final result
    print(f"\n{'='*60}")
    print(f"RESULT: apex frame = {best_frame}")
    print(f"{'='*60}")
    out_path = save_frame(video_path, best_frame, label)
    return best_frame, out_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Find the apex frame via progressive visual-narrowing search."
    )
    parser.add_argument("video", help="Path to video file")
    parser.add_argument("--label", default="apex",
                        help="Label for saved screenshot (default: apex)")
    parser.add_argument("--output-dir", default="/tmp/apex_search",
                        help="Directory for intermediate frame extractions")
    args = parser.parse_args()

    find_apex_frame_visual(args.video, args.label, args.output_dir)
