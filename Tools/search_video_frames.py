"""
Reusable script to search through video frames by extracting screenshots
at configurable intervals, enabling progressive visual narrowing to find
a target frame (e.g. dog apex over A-frame obstacle).

Usage:
  # Step 1: Coarse scan — extract every 50th frame
  python search_video_frames.py <video_path> --start 0 --end 0 --step 50

  # Step 2: Narrow down — extract every 10th frame in a range
  python search_video_frames.py <video_path> --start 900 --end 1100 --step 10

  # Step 3: Fine scan — every frame in a tight range
  python search_video_frames.py <video_path> --start 980 --end 1010 --step 1

  # Step 4: Save final result
  python search_video_frames.py <video_path> --save-frame 995 --label apex

Extracted frames go to a temp directory and are printed for review.
The --save-frame option saves a clean screenshot next to the video file
as frame_<N>_<label>.png and prints the frame number.
"""

import argparse
import os
import sys
import shutil
import cv2


def get_video_info(video_path):
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error: could not open video '{video_path}'")
        sys.exit(1)
    fps = cap.get(cv2.CAP_PROP_FPS)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()
    return fps, total


def extract_frames(video_path, output_dir, start, end, step):
    """Extract frames from start to end (inclusive) at the given step interval."""
    fps, total = get_video_info(video_path)
    if end <= 0:
        end = total - 1
    start = max(0, start)
    end = min(end, total - 1)

    os.makedirs(output_dir, exist_ok=True)

    cap = cv2.VideoCapture(video_path)
    extracted = []
    for f in range(start, end + 1, step):
        cap.set(cv2.CAP_PROP_POS_FRAMES, f)
        ret, frame = cap.read()
        if ret:
            path = os.path.join(output_dir, f"frame_{f:04d}.png")
            cv2.imwrite(path, frame)
            extracted.append((f, path))
    cap.release()

    print(f"\nVideo: {video_path}")
    print(f"FPS: {fps}, Total frames: {total}, Duration: {total/fps:.2f}s")
    print(f"Extracted {len(extracted)} frames (start={start}, end={end}, step={step})")
    print(f"Output directory: {output_dir}")
    for f, path in extracted:
        print(f"  Frame {f:>5d}  ->  {path}")
    return extracted


def save_frame(video_path, frame_num, label="apex"):
    """Save a single clean frame next to the video and print the result."""
    fps, total = get_video_info(video_path)
    frame_num = max(0, min(frame_num, total - 1))

    cap = cv2.VideoCapture(video_path)
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
    ret, frame = cap.read()
    cap.release()

    if not ret:
        print(f"Error reading frame {frame_num}")
        sys.exit(1)

    video_dir = os.path.dirname(os.path.abspath(video_path))
    out_name = f"frame_{frame_num}_{label}.png"
    out_path = os.path.join(video_dir, out_name)
    cv2.imwrite(out_path, frame)

    print(f"\n=== Result ===")
    print(f"Frame number: {frame_num}")
    print(f"Time: {frame_num/fps:.3f}s")
    print(f"Screenshot saved: {out_path}")
    return out_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Search through video frames by extracting screenshots at intervals."
    )
    parser.add_argument("video", help="Path to video file")
    parser.add_argument("--start", type=int, default=0,
                        help="Start frame (default: 0)")
    parser.add_argument("--end", type=int, default=0,
                        help="End frame (default: last frame)")
    parser.add_argument("--step", type=int, default=50,
                        help="Frame step interval (default: 50)")
    parser.add_argument("--output-dir", default="/tmp/frame_search",
                        help="Directory for extracted frames (default: /tmp/frame_search)")
    parser.add_argument("--save-frame", type=int, default=None,
                        help="Save this specific frame and exit")
    parser.add_argument("--label", default="apex",
                        help="Label for saved screenshot filename (default: apex)")
    parser.add_argument("--clean", action="store_true",
                        help="Clean output directory before extracting")

    args = parser.parse_args()

    if args.save_frame is not None:
        save_frame(args.video, args.save_frame, args.label)
    else:
        if args.clean and os.path.exists(args.output_dir):
            shutil.rmtree(args.output_dir)
        extract_frames(args.video, args.output_dir, args.start, args.end, args.step)
