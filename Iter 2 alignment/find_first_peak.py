"""
Find the first significant periodic peak in an IMU signal.

Given a trimmed IMU CSV, computes the filtered accelerometer magnitude
and identifies the first peak that is part of the periodic stride pattern,
ignoring small noisy peaks that may precede it.

Usage
-----
    python find_first_peak.py <csv_path> [--signal amag|gmag] [--threshold 0.3] [--plot]

Algorithm
---------
1. Preprocess the IMU data (magnitude + Butterworth low-pass filter).
2. Find all peaks in the filtered signal using scipy.signal.find_peaks
   with a minimum distance based on expected stride frequency.
3. Compute peak prominences to distinguish real stride peaks from noise.
4. Set a significance threshold as a fraction of the median prominence
   of the top peaks (the periodic stride peaks dominate the signal).
5. The first peak whose prominence exceeds this threshold is reported.
"""

import argparse
import sys

import numpy as np
from scipy.signal import find_peaks, peak_prominences

from preprocessing import preprocess_imu


def find_first_significant_peak(signal, fs, min_stride_hz=2.0, max_stride_hz=12.0,
                                 threshold_frac=0.3):
    """Find the index of the first significant periodic peak.

    Parameters
    ----------
    signal : array-like
        The 1-D signal (e.g. filtered accel magnitude).
    fs : float
        Sampling frequency in Hz.
    min_stride_hz : float
        Minimum expected stride frequency — sets the max allowed distance
        between consecutive peaks.
    max_stride_hz : float
        Maximum expected stride frequency — sets the min required distance
        between peaks.
    threshold_frac : float
        Fraction of the median top-peak prominence used as the significance
        cutoff. Lower values are more sensitive; higher values are stricter.

    Returns
    -------
    dict with keys:
        'peak_idx'    : int   — sample index of the first significant peak
        'peak_time_s' : float — time in seconds (relative to signal start)
        'all_peaks'   : array — indices of all detected peaks
        'prominences' : array — prominence of each detected peak
        'threshold'   : float — the computed prominence threshold
    """
    signal = np.asarray(signal)

    # Min distance between peaks (samples) based on max stride frequency
    min_distance = max(1, int(fs / max_stride_hz))

    # Find all peaks with minimum distance constraint
    peaks, _ = find_peaks(signal, distance=min_distance)

    if len(peaks) == 0:
        raise ValueError("No peaks found in the signal.")

    # Compute prominences for each peak
    prominences, _, _ = peak_prominences(signal, peaks)

    # Determine significance threshold from the top peaks.
    # Use the top 25% of peaks by prominence to estimate the "periodic" level,
    # then set the threshold as a fraction of their median prominence.
    n_top = max(1, len(prominences) // 4)
    top_proms = np.sort(prominences)[-n_top:]
    median_top = np.median(top_proms)
    threshold = threshold_frac * median_top

    # First peak whose prominence exceeds the threshold
    significant_mask = prominences >= threshold
    if not np.any(significant_mask):
        raise ValueError("No peaks exceed the significance threshold.")

    first_idx = np.argmax(significant_mask)  # first True
    peak_sample = peaks[first_idx]
    peak_time = peak_sample / fs

    return {
        'peak_idx': int(peak_sample),
        'peak_time_s': peak_time,
        'all_peaks': peaks,
        'prominences': prominences,
        'threshold': threshold,
    }


def main():
    parser = argparse.ArgumentParser(
        description='Find the first significant periodic peak in IMU data.')
    parser.add_argument('csv_path', help='Path to the trimmed IMU CSV file')
    parser.add_argument('--signal', choices=['amag', 'gmag'], default='amag',
                        help='Which magnitude signal to analyse (default: amag)')
    parser.add_argument('--threshold', type=float, default=0.3,
                        help='Prominence threshold as fraction of top-peak median (default: 0.3)')
    parser.add_argument('--plot', action='store_true',
                        help='Show a matplotlib plot with the result')
    args = parser.parse_args()

    # Preprocess
    df = preprocess_imu(args.csv_path)
    fs = df.attrs['fs']

    col = 'Amag_F' if args.signal == 'amag' else 'Gmag_F'
    signal = df[col].values
    time_s = df['Relative_Time_s'].values

    # Find first significant peak
    result = find_first_significant_peak(signal, fs, threshold_frac=args.threshold)

    peak_abs_time = df['Timestamp'].iloc[result['peak_idx']]
    print(f"Signal:    {col}")
    print(f"Fs:        {fs:.1f} Hz")
    print(f"Threshold: {result['threshold']:.4f} (prominence)")
    print(f"Total peaks found: {len(result['all_peaks'])}")
    print(f"First significant peak:")
    print(f"  Sample index:  {result['peak_idx']}")
    print(f"  Relative time: {result['peak_time_s']:.4f} s")
    print(f"  Absolute time: {peak_abs_time:.6f}")
    print(f"  Signal value:  {signal[result['peak_idx']]:.4f}")

    if args.plot:
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(14, 5))
        ax.plot(time_s, signal, label=col, linewidth=0.8)

        # Mark all peaks
        all_p = result['all_peaks']
        ax.plot(time_s[all_p], signal[all_p], 'x', color='grey', alpha=0.5,
                markersize=5, label='All peaks')

        # Mark significant peaks
        sig_mask = result['prominences'] >= result['threshold']
        sig_peaks = all_p[sig_mask]
        ax.plot(time_s[sig_peaks], signal[sig_peaks], 'rv', markersize=8,
                label='Significant peaks')

        # Highlight the first significant peak
        fp = result['peak_idx']
        ax.axvline(time_s[fp], color='white', linewidth=2, linestyle='--',
                   label=f'First significant peak ({result["peak_time_s"]:.3f}s)')
        ax.plot(time_s[fp], signal[fp], 'w*', markersize=15, zorder=5)

        ax.set_xlabel('Time (s)')
        ax.set_ylabel(col)
        ax.set_title('First Significant Peak Detection')
        ax.legend(loc='upper right')
        ax.set_facecolor('#1a1a2e')
        fig.patch.set_facecolor('#16213e')
        ax.tick_params(colors='white')
        ax.xaxis.label.set_color('white')
        ax.yaxis.label.set_color('white')
        ax.title.set_color('white')
        ax.legend(facecolor='#1a1a2e', edgecolor='white', labelcolor='white')
        plt.tight_layout()
        plt.show()


if __name__ == '__main__':
    main()
