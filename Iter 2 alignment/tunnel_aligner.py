"""
Tunnel-specific video-to-IMU alignment.

Heuristic: the dog's first significant stride peak in the IMU data
corresponds to the first-leap video frame. The aligner finds the first
prominent periodic peak in the filtered accelerometer magnitude and
matches it to the known first-leap frame from the video.
"""

import os

import numpy as np
import pandas as pd
from scipy.signal import find_peaks, peak_prominences

from obstacle_aligner import ObstacleAligner

FIRST_LEAP_CSV = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              'Tunnel First Leap Frames.csv')


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
    peak_idx : int
        Sample index of the first significant peak.
    all_peaks : ndarray
        Indices of all detected peaks.
    prominences : ndarray
        Prominence of each detected peak.
    threshold : float
        The computed prominence threshold.
    """
    signal = np.asarray(signal)

    # Min distance between peaks (samples) based on max stride frequency
    min_distance = max(1, int(fs / max_stride_hz))

    peaks, _ = find_peaks(signal, distance=min_distance)
    if len(peaks) == 0:
        raise ValueError("No peaks found in the signal.")

    prominences, _, _ = peak_prominences(signal, peaks)

    # Use top 25% of peaks by prominence to estimate the periodic level
    n_top = max(1, len(prominences) // 4)
    top_proms = np.sort(prominences)[-n_top:]
    median_top = np.median(top_proms)
    threshold = threshold_frac * median_top

    significant_mask = prominences >= threshold
    if not np.any(significant_mask):
        raise ValueError("No peaks exceed the significance threshold.")

    first_idx = np.argmax(significant_mask)
    peak_sample = peaks[first_idx]

    return peak_sample, peaks, prominences, threshold


class TunnelAligner(ObstacleAligner):
    """Align a tunnel repetition using the first-stride-peak anchor.

    Parameters
    ----------
    data_dir : str
        Path to a repetition folder (e.g. 720sync/Arya_Tunnel_2/).
    first_leap_frame : int or None
        Video frame number where the dog reaches the peak of its first leap.
        If None, attempts to read from Tunnel First Leap Frames.csv.
    prefer_trimmed : bool
        If True, prefer *_trimmed.csv over *_cleaned.csv.
    threshold_frac : float
        Prominence threshold fraction for first-peak detection (default 0.3).
    """

    def __init__(self, data_dir, first_leap_frame=None, prefer_trimmed=True,
                 threshold_frac=0.3):
        super().__init__(data_dir, prefer_trimmed=prefer_trimmed)
        self.first_leap_frame = first_leap_frame or self._detect_first_leap_frame()
        self.threshold_frac = threshold_frac

    def _detect_first_leap_frame(self):
        """Look up the first-leap frame number from Tunnel First Leap Frames.csv."""
        if not os.path.exists(FIRST_LEAP_CSV):
            return None
        df = pd.read_csv(FIRST_LEAP_CSV)
        row = df.loc[df['Folder'] == self.rep_name]
        if row.empty:
            return None
        n = int(row.iloc[0]['First_Leap_Frame'])
        return n if n > 0 else None

    def find_first_peak(self):
        """Find the IMU time (s) of the first significant stride peak.

        When using a trimmed CSV, the returned time is relative to the
        *original* (untrimmed) IMU stream, adjusted by trim_offset_s.

        Returns
        -------
        peak_time_s : float
            IMU time in seconds of the first significant peak
            (relative to original IMU start).
        peak_index : int
            DataFrame row index of the peak within the loaded CSV.
        """
        amag = self.df['Amag_F'].values

        peak_index, _, _, _ = find_first_significant_peak(
            amag, self.fs, threshold_frac=self.threshold_frac,
        )

        time_s = self.df['Relative_Time_s'].values
        return time_s[peak_index] + self.trim_offset_s, int(peak_index)

    def align(self):
        """Compute the offset aligning the first-leap video frame to the IMU peak.

        Returns
        -------
        dict
            offset_ms : float
                Offset such that imu_time = video_time + offset_ms.
            confidence : float
                Confidence score in [0, 1].
            first_leap_frame : int
                Video frame used as anchor.
            peak_time_s : float
                IMU time of the first significant peak
                (relative to original IMU start).
            peak_index : int
                DataFrame row index of the peak.
        """
        if self.first_leap_frame is None:
            raise ValueError(
                f"No first-leap frame for {self.rep_name}. "
                "Provide first_leap_frame or add an entry to "
                "Tunnel First Leap Frames.csv."
            )

        leap_video_ms = self.frame_to_ms(self.first_leap_frame)
        peak_time_s, peak_index = self.find_first_peak()
        peak_time_ms = peak_time_s * 1000

        offset_ms = peak_time_ms - leap_video_ms

        # Confidence: how prominent is the chosen peak relative to the
        # overall signal. A clear first stride peak well above noise = high.
        amag = self.df['Amag_F'].values
        _, all_peaks, prominences, threshold = find_first_significant_peak(
            amag, self.fs, threshold_frac=self.threshold_frac,
        )
        # Find the prominence of the chosen peak
        peak_pos = np.where(all_peaks == peak_index)[0]
        if len(peak_pos) > 0:
            peak_prom = prominences[peak_pos[0]]
            max_prom = prominences.max()
            confidence = float(np.clip(peak_prom / max_prom, 0, 1))
        else:
            confidence = 0.0

        return {
            'offset_ms': offset_ms,
            'confidence': confidence,
            'first_leap_frame': self.first_leap_frame,
            'peak_time_s': peak_time_s,
            'peak_index': peak_index,
        }


if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print("Usage: python tunnel_aligner.py <data_dir> [first_leap_frame]")
        sys.exit(1)

    data_dir = sys.argv[1]
    leap = int(sys.argv[2]) if len(sys.argv) > 2 else None
    aligner = TunnelAligner(data_dir, first_leap_frame=leap)
    result = aligner.align()

    print(f"\n{aligner.rep_name}")
    print(f"  First leap frame: {result['first_leap_frame']}")
    print(f"  IMU peak at:      {result['peak_time_s']:.3f}s (row {result['peak_index']})")
    print(f"  Offset:           {result['offset_ms']:+.1f} ms")
    print(f"  Confidence:       {result['confidence']:.2f}")
