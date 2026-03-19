"""
Find the first-leap frame in a video using a coarse-to-fine visual scan.

Usage
-----
    python find_first_leap_frame.py <data_dir> [--crop x1 y1 x2 y2]
                                                [--coarse-step 100]
                                                [--fine-step 20]
                                                [--superfine-step 3]

The script extracts frames at decreasing step sizes so a human (or
vision model) can visually identify the frame where the dog reaches the
peak of its first leap.

It saves:
  - coarse/, fine/, superfine/  — subdirectories of numbered PNGs
    (both full-frame and cropped) for visual review.
  - frame_<N>_first_leap.png    — the final selected frame saved
    into <data_dir> once the user confirms.
"""

import argparse
import os
import sys

import cv2


def find_video(data_dir):
    """Return the first .mp4 file found in data_dir."""
    for f in sorted(os.listdir(data_dir)):
        if f.lower().endswith('.mp4'):
            return os.path.join(data_dir, f)
    return None


def extract_frames(video_path, frame_range, out_dir, crop=None):
    """Extract frames from video_path and save to out_dir.

    Parameters
    ----------
    video_path : str
    frame_range : iterable of int
    out_dir : str
    crop : tuple (x1, y1, x2, y2) or None
        If provided, also saves a *_crop.png version.
    """
    os.makedirs(out_dir, exist_ok=True)
    cap = cv2.VideoCapture(video_path)
    for f in frame_range:
        cap.set(cv2.CAP_PROP_POS_FRAMES, f)
        ret, frame = cap.read()
        if not ret:
            continue
        cv2.imwrite(os.path.join(out_dir, f'frame_{f}.png'), frame)
        if crop:
            x1, y1, x2, y2 = crop
            cropped = frame[y1:y2, x1:x2]
            cv2.imwrite(os.path.join(out_dir, f'frame_{f}_crop.png'), cropped)
    cap.release()


def main():
    parser = argparse.ArgumentParser(
        description='Find the first-leap frame via coarse-to-fine visual scan.')
    parser.add_argument('data_dir', help='Path to the repetition folder containing a .mp4')
    parser.add_argument('--crop', nargs=4, type=int, metavar=('X1', 'Y1', 'X2', 'Y2'),
                        default=None,
                        help='Crop region (x1 y1 x2 y2) for zoomed views. '
                             'Default: left-centre region (50 150 550 450)')
    parser.add_argument('--coarse-step', type=int, default=100,
                        help='Frame step for coarse scan (default: 100)')
    parser.add_argument('--fine-step', type=int, default=20,
                        help='Frame step for fine scan (default: 20)')
    parser.add_argument('--superfine-step', type=int, default=3,
                        help='Frame step for superfine scan (default: 3)')
    parser.add_argument('--frame', type=int, default=None,
                        help='If already known, just save this frame as the result')
    args = parser.parse_args()

    data_dir = args.data_dir
    video_path = find_video(data_dir)
    if not video_path:
        print(f'No .mp4 found in {data_dir}')
        sys.exit(1)

    cap = cv2.VideoCapture(video_path)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    cap.release()
    print(f'Video: {video_path}')
    print(f'  {total_frames} frames, {fps} fps, {total_frames / fps:.1f}s')

    crop = tuple(args.crop) if args.crop else (50, 150, 550, 450)

    # If frame is already known, just save it
    if args.frame is not None:
        cap = cv2.VideoCapture(video_path)
        cap.set(cv2.CAP_PROP_POS_FRAMES, args.frame)
        ret, frame = cap.read()
        cap.release()
        if ret:
            out = os.path.join(data_dir, f'frame_{args.frame}_first_leap.png')
            cv2.imwrite(out, frame)
            print(f'Saved {out}')
        else:
            print(f'ERROR: could not read frame {args.frame}')
        return

    scan_dir = os.path.join(data_dir, '_leap_scan')

    # Step 1: Coarse scan
    print(f'\n--- Coarse scan (step {args.coarse_step}) ---')
    coarse_dir = os.path.join(scan_dir, 'coarse')
    extract_frames(video_path, range(0, total_frames, args.coarse_step),
                   coarse_dir, crop=crop)
    print(f'  Saved to {coarse_dir}/')

    # Prompt for range
    try:
        start = int(input('  Enter approximate start frame of leap region: '))
        end = int(input('  Enter approximate end frame of leap region: '))
    except (ValueError, EOFError):
        print('Invalid input. Exiting.')
        sys.exit(1)

    # Step 2: Fine scan
    print(f'\n--- Fine scan (step {args.fine_step}) ---')
    fine_dir = os.path.join(scan_dir, 'fine')
    extract_frames(video_path, range(start, end + 1, args.fine_step),
                   fine_dir, crop=crop)
    print(f'  Saved to {fine_dir}/')

    try:
        start2 = int(input('  Narrow start frame: '))
        end2 = int(input('  Narrow end frame: '))
    except (ValueError, EOFError):
        print('Invalid input. Exiting.')
        sys.exit(1)

    # Step 3: Superfine scan
    print(f'\n--- Superfine scan (step {args.superfine_step}) ---')
    superfine_dir = os.path.join(scan_dir, 'superfine')
    extract_frames(video_path, range(start2, end2 + 1, args.superfine_step),
                   superfine_dir, crop=crop)
    print(f'  Saved to {superfine_dir}/')

    try:
        peak = int(input('  Enter the peak first-leap frame number: '))
    except (ValueError, EOFError):
        print('Invalid input. Exiting.')
        sys.exit(1)

    # Save result
    cap = cv2.VideoCapture(video_path)
    cap.set(cv2.CAP_PROP_POS_FRAMES, peak)
    ret, frame = cap.read()
    cap.release()
    if ret:
        out = os.path.join(data_dir, f'frame_{peak}_first_leap.png')
        cv2.imwrite(out, frame)
        print(f'\nSaved {out}')
    else:
        print(f'ERROR: could not read frame {peak}')


if __name__ == '__main__':
    main()
