"""
Get full data inventory for a video-IMU data pair: video info, IMU info,
activity onset, and peak detection.

Usage:
    python data_inventory.py <data_dir>

Example:
    python data_inventory.py "Arya Aframe/Arya_Aframe_2"
"""
import sys
import cv2

sys.path.insert(0, '.')
from mmdata_utils import find_video_csv_pair
from imu_activity_onset import detect_onset
from imu_peak_detection import detect_peaks, print_peaks


def inventory(data_dir):
    video_path, csv_path = find_video_csv_pair(data_dir)
    if not video_path or not csv_path:
        print(f"Error: Could not find video/CSV pair in {data_dir}")
        return

    # Video info
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration_ms = frames / fps * 1000
    cap.release()

    print(f"=== Data Inventory: {data_dir} ===")
    print(f"\nVideo: {video_path}")
    print(f"  Duration: {duration_ms:.0f}ms, {fps:.0f}fps, {frames} frames")

    # IMU info + onset
    onset = detect_onset(csv_path)
    if onset:
        print(f"\nIMU: {csv_path}")
        print(f"  Duration: {onset['imu_duration']:.2f}s ({onset['n_samples']} samples, ~{onset['sample_rate']:.0f} Hz)")
        print(f"  Activity onset: {onset['onset_time']:.3f}s")
        print(f"  Peak filtered accel: {onset['peak_val']:.2f} at t={onset['peak_time']:.3f}s")

    # Peak detection
    result = detect_peaks(csv_path)
    if result:
        print()
        print_peaks(result)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    for data_dir in sys.argv[1:]:
        inventory(data_dir)
        print()
