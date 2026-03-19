"""
Aframe-specific video-to-IMU alignment.

Heuristic: the dog jumping over the A-frame apex is briefly airborne,
producing a near-zero dip in accelerometer magnitude. This dip sits
between two large peaks (jump onto and jump off the A-frame).

The aligner matches the known apex video frame to the IMU dip between
the two largest peaks.
"""

import os

import numpy as np
import pandas as pd
from scipy.signal import find_peaks

from obstacle_aligner import ObstacleAligner

APEX_FRAMES_CSV = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               'Aframe Apex Frames.csv')


class AframeAligner(ObstacleAligner):
    """Align an A-frame repetition using the apex-dip anchor.

    Parameters
    ----------
    data_dir : str
        Path to a repetition folder (e.g. 720sync/Derby_Aframe_1/).
    apex_frame : int or None
        Video frame number where the dog is at the A-frame apex.
        If None, attempts to read from a frame_*_apex.png file in data_dir.
    prefer_trimmed : bool
        If True, prefer *_trimmed.csv over *_cleaned.csv.
    """

    def __init__(self, data_dir, apex_frame=None, prefer_trimmed=False):
        super().__init__(data_dir, prefer_trimmed=prefer_trimmed)
        self.apex_frame = apex_frame or self._detect_apex_frame()

    def _detect_apex_frame(self):
        """Look up the apex frame number from Aframe Apex Frames.csv."""
        if not os.path.exists(APEX_FRAMES_CSV):
            return None
        df = pd.read_csv(APEX_FRAMES_CSV)
        row = df.loc[df['Folder'] == self.rep_name]
        if row.empty:
            return None
        n = int(row.iloc[0]['Apex Frame'])
        return n if n > 0 else None

    def find_apex_dip(self, signal='imu'):
        """Find the IMU time (s) of the apex dip.

        When using a trimmed CSV, the returned time is relative to the
        *original* (untrimmed) IMU stream, adjusted by trim_offset_s.

        Parameters
        ----------
        signal : str
            'imu' — find the dip between the two tallest accel peaks.
            'pressure' — find the global minimum in the filtered pressure curve.

        Returns
        -------
        dip_time_s : float
            IMU time in seconds of the apex dip (relative to original IMU start).
        dip_index : int
            DataFrame row index of the dip within the loaded CSV.
        """
        time_s = self.df['Relative_Time_s'].values

        if signal == 'pressure':
            if 'Pressure_F' not in self.df.columns:
                raise ValueError("No Pressure data available in this CSV.")
            pressure = self.df['Pressure_F'].values
            dip_index = int(np.argmin(pressure))
            return time_s[dip_index] + self.trim_offset_s, dip_index

        # signal == 'imu'
        amag = self.df['Amag_F'].values

        # Find prominent peaks in filtered accel magnitude
        peak_indices, _ = find_peaks(
            amag,
            height=np.std(amag) * 0.5,
            distance=int(self.fs * 0.3),
            prominence=np.std(amag) * 0.3,
        )

        if len(peak_indices) < 2:
            raise ValueError(
                f"Expected at least 2 peaks for A-frame, found {len(peak_indices)}"
            )

        # Sort peaks by height (descending) and take the two tallest
        heights = amag[peak_indices]
        top2_order = np.argsort(heights)[-2:]
        # Ensure they're in temporal order
        top2 = sorted(peak_indices[top2_order])
        left_peak, right_peak = top2[0], top2[1]

        # Find the minimum between these two peaks (the apex dip)
        valley = amag[left_peak:right_peak + 1]
        dip_local = np.argmin(valley)
        dip_index = left_peak + dip_local

        return time_s[dip_index] + self.trim_offset_s, dip_index

    def align(self, signal='imu'):
        """Compute the offset aligning the apex video frame to the IMU dip.

        Parameters
        ----------
        signal : str
            'imu' or 'pressure' — passed to find_apex_dip().

        Returns
        -------
        dict
            offset_ms : float
                Offset such that imu_time = video_time + offset_ms.
            confidence : float
                Confidence score in [0, 1].
            apex_frame : int
                Video frame used as anchor.
            dip_time_s : float
                IMU time of the apex dip (relative to original IMU start).
            dip_index : int
                DataFrame row index of the dip.
        """
        if self.apex_frame is None:
            raise ValueError(
                f"No apex frame for {self.rep_name}. "
                "Provide apex_frame or add a frame_*_apex.png file."
            )

        apex_video_ms = self.frame_to_ms(self.apex_frame)
        dip_time_s, dip_index = self.find_apex_dip(signal=signal)
        dip_time_ms = dip_time_s * 1000

        offset_ms = dip_time_ms - apex_video_ms

        # Confidence depends on signal type
        if signal == 'pressure':
            pressure = self.df['Pressure_F'].values
            p_range = pressure.max() - pressure.min()
            dip_val = pressure[dip_index]
            confidence = float((pressure.max() - dip_val) / p_range) if p_range > 0 else 0.0
        else:
            # IMU: lower accel at dip relative to flanking peaks = better
            amag = self.df['Amag_F'].values
            peak_indices, _ = find_peaks(
                amag,
                height=np.std(amag) * 0.5,
                distance=int(self.fs * 0.3),
            )
            if len(peak_indices) >= 2:
                heights = amag[peak_indices]
                top2_heights = np.sort(heights)[-2:]
                mean_peak = np.mean(top2_heights)
                dip_val = amag[dip_index]
                if mean_peak > 0:
                    confidence = float(np.clip(1.0 - dip_val / mean_peak, 0, 1))
                else:
                    confidence = 0.0
            else:
                confidence = 0.0

        return {
            'offset_ms': offset_ms,
            'confidence': confidence,
            'apex_frame': self.apex_frame,
            'dip_time_s': dip_time_s,
            'dip_index': dip_index,
        }


if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print("Usage: python aframe_aligner.py <data_dir> [apex_frame]")
        sys.exit(1)

    data_dir = sys.argv[1]
    apex = int(sys.argv[2]) if len(sys.argv) > 2 else None
    aligner = AframeAligner(data_dir, apex_frame=apex)
    result = aligner.align()

    print(f"\n{aligner.rep_name}")
    print(f"  Apex frame:   {result['apex_frame']}")
    print(f"  IMU dip at:   {result['dip_time_s']:.3f}s (row {result['dip_index']})")
    print(f"  Offset:       {result['offset_ms']:+.1f} ms")
    print(f"  Confidence:   {result['confidence']:.2f}")
