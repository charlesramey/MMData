import os
import argparse
from mmdata_utils import find_video_csv_pair, ensure_audio_extracted

def process_directory(root_dir):
    print(f"Scanning {root_dir}...")

    # Walk through the directory tree
    for root, dirs, files in os.walk(root_dir):
        # We are looking for directories that contain a video/csv pair.
        # The logic in find_video_csv_pair scans a single directory (not recursive).
        # So we can just call it on 'root'.

        video_path, _ = find_video_csv_pair(root)

        if video_path:
            # Check if wav exists
            wav_path = os.path.splitext(video_path)[0] + ".wav"
            if not os.path.exists(wav_path):
                print(f"Processing: {video_path}")
                result = ensure_audio_extracted(video_path)
                if result:
                    print(f"  -> Extracted: {os.path.basename(result)}")
                else:
                    print(f"  -> Failed to extract audio")
            else:
                print(f"Skipping (already exists): {os.path.basename(video_path)}")

def main():
    parser = argparse.ArgumentParser(description="Batch extract audio from videos in MMData directories.")
    parser.add_argument("root_dir", help="Root directory to scan recursively.")
    args = parser.parse_args()

    if not os.path.exists(args.root_dir):
        print(f"Error: Directory '{args.root_dir}' does not exist.")
        return

    process_directory(args.root_dir)
    print("Batch processing complete.")

if __name__ == "__main__":
    main()
