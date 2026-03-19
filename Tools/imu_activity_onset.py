"""
Detect IMU activity onset and peak for a given CSV file.

Usage:
    python imu_activity_onset.py <csv_path> [threshold]

Example:
    python imu_activity_onset.py "Arya Aframe/Arya_Aframe_2/Arya_aframe_2_cleaned.csv" 0.2
"""
import sys
import numpy as np

sys.path.insert(0, '.')
from MMData import load_data, apply_lowpass


def detect_onset(csv_path, threshold=0.2, lowpass_hz=5.0):
    df, err = load_data(csv_path)
    if df is None:
        print(f"Error loading {csv_path}: {err}")
        return None, None

    mag = np.sqrt(df['Ax']**2 + df['Ay']**2 + df['Az']**2)
    mag = (mag - np.mean(mag)) / np.std(mag)
    diffs = np.diff(df['Relative_Time_s'])
    fs = 1.0 / np.mean(diffs) if len(diffs) > 0 else 100.0
    amag_f = apply_lowpass(mag, lowpass_hz, fs)

    t = df['Relative_Time_s'].values

    # Activity onset: first time filtered accel exceeds threshold
    onset_idx = np.where(amag_f > threshold)[0]
    onset_time = t[onset_idx[0]] if len(onset_idx) > 0 else None

    # Peak of filtered signal
    peak_idx = np.argmax(amag_f)
    peak_time = t[peak_idx]
    peak_val = amag_f[peak_idx]

    return {
        'onset_time': onset_time,
        'peak_time': peak_time,
        'peak_val': peak_val,
        'imu_duration': t[-1],
        'sample_rate': fs,
        'n_samples': len(df),
    }


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    csv_path = sys.argv[1]
    threshold = float(sys.argv[2]) if len(sys.argv) > 2 else 0.2

    result = detect_onset(csv_path, threshold)
    if result:
        print(f"CSV: {csv_path}")
        print(f"IMU duration: {result['imu_duration']:.2f}s ({result['n_samples']} samples, ~{result['sample_rate']:.0f} Hz)")
        print(f"Activity onset (filtered accel > {threshold}): {result['onset_time']:.3f}s")
        print(f"Peak filtered accel: {result['peak_val']:.2f} at t={result['peak_time']:.3f}s")
