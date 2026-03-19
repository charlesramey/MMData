"""
Detect all significant peaks in IMU data and analyze stride patterns.

Usage:
    python imu_peak_detection.py <csv_path> [active_region_start]

Example:
    python imu_peak_detection.py "Arya Aframe/Arya_Aframe_2/Arya_aframe_2_cleaned.csv" 5.5
"""
import sys
import numpy as np
from scipy.signal import find_peaks

sys.path.insert(0, '.')
from MMData import load_data, apply_lowpass


def detect_peaks(csv_path, active_start=None, lowpass_hz=5.0, small_threshold=0.3, big_threshold=1.5):
    df, err = load_data(csv_path)
    if df is None:
        print(f"Error loading {csv_path}: {err}")
        return None

    mag = np.sqrt(df['Ax']**2 + df['Ay']**2 + df['Az']**2)
    mag = (mag - np.mean(mag)) / np.std(mag)
    diffs = np.diff(df['Relative_Time_s'])
    fs = 1.0 / np.mean(diffs) if len(diffs) > 0 else 100.0
    amag_f = apply_lowpass(mag, lowpass_hz, fs)
    t = df['Relative_Time_s'].values

    # Find peaks at both thresholds
    peaks_small, props_small = find_peaks(amag_f, height=small_threshold)
    peaks_big, props_big = find_peaks(amag_f, height=big_threshold)

    # Auto-detect active region if not specified
    if active_start is None:
        onset_idx = np.where(amag_f > 0.2)[0]
        active_start = t[onset_idx[0]] - 0.5 if len(onset_idx) > 0 else 0.0

    return {
        't': t,
        'amag_f': amag_f,
        'peaks_small': peaks_small,
        'props_small': props_small,
        'peaks_big': peaks_big,
        'props_big': props_big,
        'active_start': active_start,
    }


def print_peaks(result):
    t = result['t']
    peaks_small = result['peaks_small']
    props_small = result['props_small']
    peaks_big = result['peaks_big']
    props_big = result['props_big']
    active_start = result['active_start']

    print(f'=== All peaks with height > 0.3 (active region, t > {active_start:.1f}s) ===')
    for i, idx in enumerate(peaks_small):
        if t[idx] > active_start:
            print(f'  t={t[idx]:.3f}s  h={props_small["peak_heights"][i]:.2f}')

    print()
    print('=== Big peaks with height > 1.5 ===')
    for i, idx in enumerate(peaks_big):
        print(f'  t={t[idx]:.3f}s  h={props_big["peak_heights"][i]:.2f}')

    # Find the biggest peak
    if len(peaks_big) > 0:
        max_i = np.argmax(props_big['peak_heights'])
        print(f'\nBiggest peak: t={t[peaks_big[max_i]]:.3f}s  h={props_big["peak_heights"][max_i]:.2f}')

    # Approach stride analysis: peaks before the biggest peak
    if len(peaks_big) > 0:
        biggest_time = t[peaks_big[max_i]]
        approach_peaks = [t[idx] for idx in peaks_small if active_start < t[idx] < biggest_time]
        if len(approach_peaks) > 1:
            intervals = np.diff(approach_peaks)
            print(f'\nApproach stride peaks: {[f"{p:.3f}s" for p in approach_peaks]}')
            print(f'Inter-peak intervals: {[f"{iv*1000:.0f}ms" for iv in intervals]}')
            print(f'Mean interval: {np.mean(intervals)*1000:.0f}ms (~{1/np.mean(intervals):.1f} Hz)')


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    csv_path = sys.argv[1]
    active_start = float(sys.argv[2]) if len(sys.argv) > 2 else None

    result = detect_peaks(csv_path, active_start)
    if result:
        print(f"CSV: {csv_path}\n")
        print_peaks(result)
