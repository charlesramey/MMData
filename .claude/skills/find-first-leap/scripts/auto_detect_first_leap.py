"""
Automated first-leap frame detector for dog agility videos.

Uses a two-phase approach:
1. Motion detection to find when the dog starts running
2. Vertical motion analysis to find the peak of the first leap

Usage
-----
    python auto_detect_first_leap.py <folder_pattern> [--output-csv <path>] [--save-frames]

Examples
--------
    # Detect for all Tunnel folders, save frames and CSV
    python auto_detect_first_leap.py "720sync/*_Tunnel_*" --save-frames --output-csv "Tunnel First Leap Frames.csv"

    # Detect for a single folder
    python auto_detect_first_leap.py "720sync/Derby_Tunnel_1" --save-frames
"""
import argparse
import csv
import glob
import os
import sys

import cv2
import numpy as np
from scipy.signal import find_peaks


def find_video(data_dir):
    """Return the first .mp4 file found in data_dir."""
    for f in sorted(os.listdir(data_dir)):
        if f.lower().endswith('.mp4'):
            return os.path.join(data_dir, f)
    return None


def detect_motion_start(video_path, max_frames=1500, step=10):
    """Find the frame where significant motion begins.

    Uses frame differencing in the dog region to detect when the dog
    transitions from stationary to moving.

    Returns
    -------
    motion_start : int
        Frame number where sustained motion begins.
    """
    cap = cv2.VideoCapture(video_path)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    scan_end = min(total, max_frames)

    prev_gray = None
    motion_scores = []
    frame_nums = []

    for f in range(0, scan_end, step):
        cap.set(cv2.CAP_PROP_POS_FRAMES, f)
        ret, frame = cap.read()
        if not ret:
            break

        h, w = frame.shape[:2]
        roi = frame[int(h * 0.2):int(h * 0.7), int(w * 0.05):int(w * 0.65)]
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)

        if prev_gray is not None:
            diff = cv2.absdiff(gray, prev_gray)
            score = float(np.mean(diff))
            motion_scores.append(score)
            frame_nums.append(f)

        prev_gray = gray

    cap.release()

    if not motion_scores:
        return 0

    scores = np.array(motion_scores)
    n_baseline = min(10, len(scores))
    baseline = np.median(scores[:n_baseline])
    threshold = baseline + 2 * np.std(scores[:n_baseline])

    for i in range(len(scores)):
        if scores[i] > threshold:
            if i + 1 < len(scores) and scores[i + 1] > threshold:
                return frame_nums[i]

    return frame_nums[len(frame_nums) // 3]


def detect_first_leap(video_path, motion_start, search_window=400, coarse_step=5):
    """Find the first leap peak frame using vertical motion analysis.

    Scans from motion_start outward, tracking the vertical centroid of
    frame-to-frame differences. The first leap peak is the first local
    minimum in vertical position (lowest y = highest off ground).

    Parameters
    ----------
    video_path : str
    motion_start : int
        Frame where motion begins (from detect_motion_start).
    search_window : int
        Number of frames after motion_start to search.
    coarse_step : int
        Step size for coarse scan.

    Returns
    -------
    leap_frame : int
        Estimated frame of the first leap peak.
    """
    cap = cv2.VideoCapture(video_path)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    scan_start = max(0, motion_start - 20)
    scan_end = min(total - 1, motion_start + search_window)

    prev_gray = None
    motion_y = []
    motion_mag = []
    frame_indices = []

    for fnum in range(scan_start, scan_end + 1, coarse_step):
        cap.set(cv2.CAP_PROP_POS_FRAMES, fnum)
        ret, frame = cap.read()
        if not ret:
            break

        h, w = frame.shape[:2]
        roi = frame[int(h * 0.25):int(h * 0.75), int(w * 0.05):int(w * 0.65)]
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)

        if prev_gray is not None:
            diff = cv2.absdiff(gray, prev_gray).astype(float)
            threshold = np.percentile(diff, 90)
            mask = diff > threshold

            if mask.sum() > 50:
                ys = np.where(mask)[0]
                weights = diff[mask]
                cy = np.average(ys, weights=weights)
                mag = float(np.sum(weights))
                motion_y.append(cy)
                motion_mag.append(mag)
                frame_indices.append(fnum)
            elif motion_y:
                motion_y.append(motion_y[-1])
                motion_mag.append(0)
                frame_indices.append(fnum)

        prev_gray = gray

    cap.release()

    if len(motion_y) < 10:
        return motion_start + 150

    motion_y = np.array(motion_y)
    motion_mag = np.array(motion_mag)
    frame_indices = np.array(frame_indices)

    # Smooth vertical position
    kernel = np.ones(5) / 5
    smooth_y = np.convolve(motion_y, kernel, mode='same') if len(motion_y) > 5 else motion_y

    # Find when dog is running (sustained high motion)
    mag_threshold = np.percentile(motion_mag, 50)
    running_mask = motion_mag > mag_threshold

    running_start_idx = 0
    for i in range(len(running_mask) - 3):
        if running_mask[i] and running_mask[i + 1] and running_mask[i + 2]:
            running_start_idx = i
            break

    # Find first local minimum in vertical position (= peak height)
    search_region = smooth_y[running_start_idx:]
    search_frames = frame_indices[running_start_idx:]

    inverted = -search_region
    peaks, _ = find_peaks(inverted, distance=3, prominence=2)

    if len(peaks) > 0:
        return int(search_frames[peaks[0]])

    min_idx = np.argmin(search_region)
    return int(search_frames[min_idx])


def refine_leap_frame(video_path, estimate, window=15):
    """Refine the leap estimate by per-frame analysis in a ±window region.

    Finds the frame where the vertical centroid of motion is lowest
    (dog is highest off ground).

    Returns
    -------
    refined_frame : int
    """
    cap = cv2.VideoCapture(video_path)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    start = max(0, estimate - window)
    end = min(total - 1, estimate + window)

    prev_gray = None
    best_frame = estimate
    best_score = float('inf')

    for fnum in range(start, end + 1):
        cap.set(cv2.CAP_PROP_POS_FRAMES, fnum)
        ret, frame = cap.read()
        if not ret:
            continue

        h, w = frame.shape[:2]
        roi = frame[int(h * 0.2):int(h * 0.75), int(w * 0.05):int(w * 0.65)]
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)

        if prev_gray is not None:
            diff = cv2.absdiff(gray, prev_gray).astype(float)
            threshold = np.percentile(diff, 85)
            mask = diff > threshold

            if mask.sum() > 100:
                ys = np.where(mask)[0]
                weights = diff[mask]
                cy = np.average(ys, weights=weights)

                if cy < best_score:
                    best_score = cy
                    best_frame = fnum

        prev_gray = gray

    cap.release()
    return best_frame


def process_folder(data_dir, save_frame=False):
    """Run the full pipeline on a single folder.

    Returns
    -------
    dict with 'folder', 'frame', 'video_path', 'saved_path'
    """
    rep = os.path.basename(os.path.normpath(data_dir))
    video_path = find_video(data_dir)

    if not video_path:
        return {'folder': rep, 'frame': None, 'error': 'no video found'}

    # Check if already done
    existing = [f for f in os.listdir(data_dir) if 'first_leap' in f and f.endswith('.png')]
    if existing:
        # Extract frame number from filename
        fname = existing[0]
        try:
            frame_num = int(fname.split('_')[1])
            return {'folder': rep, 'frame': frame_num, 'saved_path': os.path.join(data_dir, fname)}
        except (IndexError, ValueError):
            pass

    # Phase 1: detect motion start
    motion_start = detect_motion_start(video_path)

    # Phase 2: coarse leap detection
    estimate = detect_first_leap(video_path, motion_start)

    # Phase 3: per-frame refinement
    refined = refine_leap_frame(video_path, estimate)

    result = {'folder': rep, 'frame': refined, 'video_path': video_path}

    if save_frame:
        cap = cv2.VideoCapture(video_path)
        cap.set(cv2.CAP_PROP_POS_FRAMES, refined)
        ret, frame = cap.read()
        cap.release()

        if ret:
            out_path = os.path.join(data_dir, f'frame_{refined}_first_leap.png')
            cv2.imwrite(out_path, frame)
            result['saved_path'] = out_path

    return result


def main():
    parser = argparse.ArgumentParser(
        description='Automatically detect the first-leap frame in dog agility videos.')
    parser.add_argument('folder_pattern',
                        help='Glob pattern for folders (e.g. "720sync/*_Tunnel_*")')
    parser.add_argument('--output-csv', default=None,
                        help='Path to output CSV file')
    parser.add_argument('--save-frames', action='store_true',
                        help='Save frame_N_first_leap.png into each folder')
    parser.add_argument('--skip-existing', action='store_true', default=True,
                        help='Skip folders that already have a first_leap.png')
    args = parser.parse_args()

    folders = sorted(glob.glob(args.folder_pattern))
    folders = [f for f in folders if os.path.isdir(f)]

    if not folders:
        print(f'No folders matched: {args.folder_pattern}')
        sys.exit(1)

    print(f'Processing {len(folders)} folders...\n')

    results = []
    for folder in folders:
        result = process_folder(folder, save_frame=args.save_frames)
        results.append(result)

        status = f"frame {result['frame']}" if result['frame'] else result.get('error', 'unknown')
        saved = ' (saved)' if 'saved_path' in result else ''
        print(f"  {result['folder']}: {status}{saved}")

    if args.output_csv:
        with open(args.output_csv, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Folder', 'First_Leap_Frame'])
            for r in results:
                if r['frame'] is not None:
                    writer.writerow([r['folder'], r['frame']])
        print(f'\nWrote {len([r for r in results if r["frame"]])} entries to {args.output_csv}')


if __name__ == '__main__':
    main()
