"""
Jump-specific IMU anchor detection.

Heuristic:
- The jump produces a broad trough in the filtered IMU magnitude.
- The launch anchor is the last peak before the trough.
- The mid-air anchor is the trough minimum.
- The first-contact anchor is the first post-trough minimum on the rise
  toward the next peak.
- The gathered anchor is the first peak after the trough.
"""

import numpy as np
from scipy.signal import find_peaks

from obstacle_aligner import ObstacleAligner

DEFAULT_ANCHOR_WEIGHTS = {
    "launch": 1.0,
    "midair": 0.0,
    "first_contact": 0.7,
    "gathered": 1.0,
}


def _contiguous_regions(mask):
    """Return inclusive (start, end) runs of True values."""
    indices = np.flatnonzero(mask)
    if len(indices) == 0:
        return []

    splits = np.where(np.diff(indices) > 1)[0] + 1
    groups = np.split(indices, splits)
    return [(int(group[0]), int(group[-1])) for group in groups]


class JumpAligner(ObstacleAligner):
    """Detect jump-related IMU anchor points from a trimmed repetition."""

    def __init__(self, data_dir, prefer_trimmed=True):
        super().__init__(data_dir, prefer_trimmed=prefer_trimmed)

    def jump_signal(self):
        """Return the 1-D filtered signal used for jump anchor detection.

        We average filtered accel and gyro magnitudes because the example
        plots show a shared trough/peak structure in both channels.
        """
        amag = self.df["Amag_F"].to_numpy()
        gmag = self.df["Gmag_F"].to_numpy()
        return (amag + gmag) / 2.0

    def detect_jump_imu_anchors(
        self,
        low_quantile=0.20,
        min_trough_s=0.15,
        peak_distance_s=0.18,
        peak_prominence_scale=0.18,
    ):
        """Detect launch, midair, first-contact, and gathered IMU anchors.

        Returns
        -------
        dict
            Includes sample indices and times in seconds relative to the
            original IMU start.
        """
        retry_params = [
            (low_quantile, min_trough_s),
            (low_quantile, 0.12),
            (0.25, 0.12),
            (0.30, 0.10),
        ]

        last_error = None
        for retry_low_quantile, retry_min_trough_s in retry_params:
            try:
                return self._detect_jump_imu_anchors_once(
                    low_quantile=retry_low_quantile,
                    min_trough_s=retry_min_trough_s,
                    peak_distance_s=peak_distance_s,
                    peak_prominence_scale=peak_prominence_scale,
                )
            except ValueError as exc:
                last_error = exc

        raise last_error

    def _detect_jump_imu_anchors_once(
        self,
        low_quantile,
        min_trough_s,
        peak_distance_s,
        peak_prominence_scale,
    ):
        """Run one trough-and-peaks pass with a fixed parameter set."""
        signal = self.jump_signal()
        time_s = self.df["Relative_Time_s"].to_numpy()
        fs = self.fs

        low_threshold = float(np.quantile(signal, low_quantile))
        min_trough_len = max(3, int(round(fs * min_trough_s)))
        peak_distance = max(1, int(round(fs * peak_distance_s)))
        prominence = max(0.15, float(np.std(signal) * peak_prominence_scale))

        peaks, _ = find_peaks(
            signal,
            distance=peak_distance,
            prominence=prominence,
        )
        if len(peaks) < 2:
            raise ValueError(
                f"Expected at least 2 peaks in jump IMU signal, found {len(peaks)}"
            )

        trough_regions = [
            region
            for region in _contiguous_regions(signal <= low_threshold)
            if (region[1] - region[0] + 1) >= min_trough_len
        ]
        if not trough_regions:
            raise ValueError("Could not find a broad low-magnitude trough for jump.")

        best_candidate = None
        for start, end in trough_regions:
            left_peaks = peaks[peaks < start]
            right_peaks = peaks[peaks > end]
            if len(left_peaks) == 0 or len(right_peaks) == 0:
                continue

            launch_idx = int(left_peaks[-1])
            gathered_idx = int(right_peaks[0])

            trough_mean = float(signal[start:end + 1].mean())
            trough_width = end - start + 1
            flank_height = float(signal[launch_idx] + signal[gathered_idx])

            # Lower trough is better; wider trough is better; stronger flanking
            # peaks are better.
            score = (trough_mean, -trough_width, -flank_height)
            if best_candidate is None or score < best_candidate[0]:
                best_candidate = (score, start, end, launch_idx, gathered_idx)

        if best_candidate is None:
            raise ValueError("Found low regions, but none had peaks on both sides.")

        _, trough_start, trough_end, launch_idx, gathered_idx = best_candidate

        midair_idx = int(np.argmin(signal[trough_start:trough_end + 1]) + trough_start)
        first_contact_idx = int(
            np.argmin(signal[trough_end:gathered_idx + 1]) + trough_end
        )

        def anchor(index):
            relative_time_s = float(time_s[index])
            return {
                "index": int(index),
                "time_s_trimmed": relative_time_s,
                "time_s": relative_time_s + self.trim_offset_s,
            }

        return {
            "signal_name": "0.5 * (Amag_F + Gmag_F)",
            "low_threshold": low_threshold,
            "trough_start_index": int(trough_start),
            "trough_end_index": int(trough_end),
            "trough_start_time_s_trimmed": float(time_s[trough_start]),
            "trough_end_time_s_trimmed": float(time_s[trough_end]),
            "launch": anchor(launch_idx),
            "midair": anchor(midair_idx),
            "first_contact": anchor(first_contact_idx),
            "gathered": anchor(gathered_idx),
        }

    def align(self, anchor_name="midair", video_anchor_frame=None):
        """Compute offset from a chosen video anchor frame to its IMU anchor.

        Parameters
        ----------
        anchor_name : str
            One of 'launch', 'midair', 'first_contact', 'gathered'.
        video_anchor_frame : int
            Frame number of the chosen visual anchor.
        """
        if video_anchor_frame is None:
            raise ValueError("video_anchor_frame is required for jump alignment.")

        anchors = self.detect_jump_imu_anchors()
        if anchor_name not in anchors:
            raise ValueError(f"Unknown jump anchor '{anchor_name}'")

        video_ms = self.frame_to_ms(video_anchor_frame)
        imu_ms = anchors[anchor_name]["time_s"] * 1000.0
        offset_ms = imu_ms - video_ms

        return {
            "offset_ms": offset_ms,
            "confidence": 0.75,
            "anchor_name": anchor_name,
            "video_anchor_frame": int(video_anchor_frame),
            "imu_anchor_index": anchors[anchor_name]["index"],
            "imu_anchor_time_s": anchors[anchor_name]["time_s"],
            "anchors": anchors,
        }

    def align_weighted(self, video_anchor_frames, anchor_weights=None):
        """Estimate one global offset from multiple jump anchors.

        Parameters
        ----------
        video_anchor_frames : dict
            Mapping from anchor name to video frame number.
        anchor_weights : dict or None
            Optional per-anchor weights. Defaults to:
            launch=1.0, midair=0.0, first_contact=0.7, gathered=1.0

        Returns
        -------
        dict
            Weighted least-squares estimate of a single offset.
        """
        anchors = self.detect_jump_imu_anchors()
        weights = dict(DEFAULT_ANCHOR_WEIGHTS)
        if anchor_weights is not None:
            weights.update(anchor_weights)

        rows = []
        for anchor_name, frame_num in video_anchor_frames.items():
            if anchor_name not in anchors:
                raise ValueError(f"Unknown jump anchor '{anchor_name}'")

            weight = float(weights.get(anchor_name, 0.0))
            video_ms = self.frame_to_ms(int(frame_num))
            imu_ms = anchors[anchor_name]["time_s"] * 1000.0
            rows.append(
                {
                    "anchor_name": anchor_name,
                    "video_anchor_frame": int(frame_num),
                    "video_time_ms": float(video_ms),
                    "imu_anchor_index": anchors[anchor_name]["index"],
                    "imu_anchor_time_s": anchors[anchor_name]["time_s"],
                    "imu_time_ms": float(imu_ms),
                    "offset_ms": float(imu_ms - video_ms),
                    "weight": weight,
                }
            )

        active_rows = [row for row in rows if row["weight"] > 0]
        if not active_rows:
            raise ValueError("Need at least one anchor with positive weight.")

        weight_sum = float(sum(row["weight"] for row in active_rows))
        offset_ms = sum(
            row["weight"] * row["offset_ms"] for row in active_rows
        ) / weight_sum

        for row in rows:
            row["residual_ms"] = float(row["offset_ms"] - offset_ms)

        weighted_sse = sum(
            row["weight"] * (row["residual_ms"] ** 2) for row in active_rows
        )
        weighted_rmse_ms = float(np.sqrt(weighted_sse / weight_sum))

        return {
            "offset_ms": float(offset_ms),
            "confidence": 0.75,
            "model": "t_imu_ms = t_video_ms + offset_ms",
            "weights": weights,
            "weighted_rmse_ms": weighted_rmse_ms,
            "anchors": anchors,
            "anchor_rows": rows,
        }


if __name__ == "__main__":
    import json
    import sys

    if len(sys.argv) < 2:
        print(
            "Usage: python jump_aligner.py <data_dir> "
            "[anchor_name video_anchor_frame]\n"
            "   or: python jump_aligner.py <data_dir> multi "
            "launch=<frame> first_contact=<frame> gathered=<frame>"
        )
        sys.exit(1)

    data_dir = sys.argv[1]
    aligner = JumpAligner(data_dir, prefer_trimmed=True)

    if len(sys.argv) == 2:
        result = aligner.detect_jump_imu_anchors()
        print(json.dumps(result, indent=2))
    elif sys.argv[2] == "multi":
        video_anchor_frames = {}
        for arg in sys.argv[3:]:
            if "=" not in arg:
                raise ValueError(
                    "Multi-anchor arguments must look like launch=1430"
                )
            anchor_name, frame_num = arg.split("=", 1)
            video_anchor_frames[anchor_name] = int(frame_num)

        result = aligner.align_weighted(video_anchor_frames=video_anchor_frames)
        print(json.dumps(result, indent=2))
    else:
        anchor_name = sys.argv[2]
        video_anchor_frame = int(sys.argv[3])
        result = aligner.align(anchor_name=anchor_name, video_anchor_frame=video_anchor_frame)
        print(json.dumps(result, indent=2))
