"""
Teeter-specific IMU anchor detection.

Two strategies are supported:

1. Small dogs:
   - Find a prolonged low-acceleration interval while the dog is relatively
     stationary on the teeter as it tilts.
   - Find the first clear acceleration peak after that interval.
   - Return the left base, peak, and right base of that first peak.
   - These correspond approximately to:
       about_to_jump_off, stepped_off, hind_legs_leave_teeter

2. Large dogs:
   - Use the filtered pressure signal.
   - Find the sharpest dip-and-rise pattern in pressure, which corresponds to
     the dog climbing the teeter, the teeter tilting, and then the dog
     descending/offloading.
   - Return the point on that pressure rise where it stops increasing further
     and begins to plateau or drop slightly.
"""

import json

import numpy as np
from scipy.signal import find_peaks

from obstacle_aligner import ObstacleAligner


KNOWN_SMALL_DOGS = {"Arya", "Vivi"}
KNOWN_LARGE_DOGS = {"Sass", "Tigger", "Zazu"}


def _contiguous_regions(mask):
    """Return inclusive (start, end) runs of True values."""
    indices = np.flatnonzero(mask)
    if len(indices) == 0:
        return []

    splits = np.where(np.diff(indices) > 1)[0] + 1
    groups = np.split(indices, splits)
    return [(int(group[0]), int(group[-1])) for group in groups]


class TeeterAligner(ObstacleAligner):
    """Detect teeter-related IMU anchor points from a repetition folder."""

    def __init__(self, data_dir, prefer_trimmed=True, strategy="auto"):
        super().__init__(data_dir, prefer_trimmed=prefer_trimmed)
        self.strategy = self._resolve_strategy(strategy)

    def _resolve_strategy(self, strategy):
        if strategy in {"small", "large"}:
            return strategy
        if strategy != "auto":
            raise ValueError("strategy must be one of: auto, small, large")

        dog_name = self.rep_name.split("_", 1)[0]
        if dog_name in KNOWN_SMALL_DOGS:
            return "small"
        if dog_name in KNOWN_LARGE_DOGS:
            return "large"

        raise ValueError(
            f"Could not infer teeter strategy for '{self.rep_name}'. "
            "Pass strategy='small' or strategy='large'."
        )

    def teeter_signal(self):
        """Return the filtered acceleration magnitude used for teeter anchors."""
        return self.df["Amag_F"].to_numpy()

    def pressure_signal(self):
        """Return the filtered/scaled pressure signal used for large dogs."""
        if "Pressure_scaled" in self.df.columns:
            return self.df["Pressure_scaled"].to_numpy()
        return self.df["Pressure_F"].to_numpy()

    def detect_teeter_imu_anchors(
        self,
        low_quantile=0.25,
        min_low_s=0.25,
        peak_distance_s=0.12,
        peak_prominence_scale=0.20,
        right_base_window_s=0.45,
        lowest_search_pad_s=0.12,
    ):
        """Dispatch to the configured teeter detection strategy with retries."""
        retry_params = [
            (low_quantile, min_low_s),
            (0.30, 0.20),
            (0.35, 0.18),
            (0.40, 0.15),
        ]

        last_error = None
        for retry_low_quantile, retry_min_low_s in retry_params:
            try:
                if self.strategy == "small":
                    return self._detect_small_dog_anchors(
                        low_quantile=retry_low_quantile,
                        min_low_s=retry_min_low_s,
                        peak_distance_s=peak_distance_s,
                        peak_prominence_scale=peak_prominence_scale,
                        right_base_window_s=right_base_window_s,
                    )

                return self._detect_large_dog_anchor(
                    low_quantile=retry_low_quantile,
                    min_low_s=retry_min_low_s,
                    lowest_search_pad_s=lowest_search_pad_s,
                )
            except ValueError as exc:
                last_error = exc

        raise last_error

    def _anchor(self, index, time_s):
        relative_time_s = float(time_s[index])
        return {
            "index": int(index),
            "time_s_trimmed": relative_time_s,
            "time_s": relative_time_s + self.trim_offset_s,
        }

    def _low_regions(self, signal, low_quantile, min_low_s):
        fs = self.fs
        low_threshold = float(np.quantile(signal, low_quantile))
        min_len = max(3, int(round(fs * min_low_s)))
        regions = [
            region
            for region in _contiguous_regions(signal <= low_threshold)
            if (region[1] - region[0] + 1) >= min_len
        ]
        return low_threshold, regions

    def _best_low_region(self, signal, peaks, regions):
        """Pick the low region that best matches a prolonged lull before a rebound."""
        best = None
        for start, end in regions:
            post_peaks = peaks[peaks > end]
            if len(post_peaks) == 0:
                continue

            first_peak = int(post_peaks[0])
            low_mean = float(signal[start:end + 1].mean())
            low_width = end - start + 1
            rebound_height = float(signal[first_peak] - low_mean)
            score = (-low_width, -rebound_height, low_mean)
            if best is None or score < best[0]:
                best = (score, start, end, first_peak)

        if best is None:
            raise ValueError("Found low regions, but none were followed by a peak.")

        _, start, end, first_peak = best
        return start, end, first_peak

    def _detect_small_dog_anchors(
        self,
        low_quantile,
        min_low_s,
        peak_distance_s,
        peak_prominence_scale,
        right_base_window_s,
    ):
        """Detect left base, peak, and right base of the first post-low peak."""
        signal = self.teeter_signal()
        time_s = self.df["Relative_Time_s"].to_numpy()
        fs = self.fs

        low_threshold, low_regions = self._low_regions(signal, low_quantile, min_low_s)
        if not low_regions:
            raise ValueError("Could not find a prolonged low-acceleration teeter period.")

        prominence = max(0.08, float(np.std(signal) * peak_prominence_scale))
        peak_distance = max(1, int(round(fs * peak_distance_s)))
        peaks, peak_props = find_peaks(
            signal,
            distance=peak_distance,
            prominence=prominence,
        )
        if len(peaks) == 0:
            raise ValueError("Could not find a post-low teeter acceleration peak.")

        low_start, low_end, peak_idx = self._best_low_region(signal, peaks, low_regions)

        # Left base: minimum from the end of the low period through the selected peak.
        left_start = low_end
        left_base_idx = int(np.argmin(signal[left_start:peak_idx + 1]) + left_start)

        # Right base: first local minimum after the peak; fallback to the minimum
        # in a short post-peak window if an explicit minimum is absent.
        minima, _ = find_peaks(-signal, distance=max(1, peak_distance // 2))
        right_minima = minima[minima > peak_idx]
        if len(right_minima) > 0:
            right_base_idx = int(right_minima[0])
        else:
            right_window = max(3, int(round(fs * right_base_window_s)))
            search_end = min(len(signal), peak_idx + right_window)
            right_base_idx = int(np.argmin(signal[peak_idx:search_end]) + peak_idx)

        # Ensure the right base belongs to the first post-low peak neighborhood.
        next_peaks = peaks[peaks > peak_idx]
        if len(next_peaks) > 0 and right_base_idx > int(next_peaks[0]):
            next_peak_idx = int(next_peaks[0])
            right_base_idx = int(
                np.argmin(signal[peak_idx:next_peak_idx + 1]) + peak_idx
            )

        return {
            "strategy": "small",
            "signal_name": "Amag_F",
            "low_threshold": low_threshold,
            "low_region_start_index": int(low_start),
            "low_region_end_index": int(low_end),
            "low_region_start_time_s_trimmed": float(time_s[low_start]),
            "low_region_end_time_s_trimmed": float(time_s[low_end]),
            "about_to_jump_off": self._anchor(left_base_idx, time_s),
            "stepped_off": self._anchor(int(peak_idx), time_s),
            "hind_legs_leave_teeter": self._anchor(right_base_idx, time_s),
        }

    def _detect_large_dog_anchor(
        self,
        low_quantile,
        min_low_s,
        lowest_search_pad_s,
    ):
        """Detect the pressure-rise plateau after the teeter-related pressure dip."""
        signal = self.pressure_signal()
        time_s = self.df["Relative_Time_s"].to_numpy()
        fs = self.fs

        low_threshold, low_regions = self._low_regions(signal, low_quantile, min_low_s)
        if not low_regions:
            raise ValueError("Could not find a prolonged low-pressure teeter period.")

        peak_distance = max(1, int(round(fs * 0.12)))
        prominence = max(0.05, float(np.std(signal) * 0.12))
        maxima, _ = find_peaks(signal, distance=peak_distance, prominence=prominence)

        if len(maxima) < 2:
            raise ValueError("Could not find enough pressure peaks for teeter alignment.")

        stride_signal = 0.5 * (
            self.df["Amag_F"].to_numpy() + self.df["Gmag_F"].to_numpy()
        )
        stride_prominence = max(0.08, float(np.std(stride_signal) * 0.15))
        stride_peaks, stride_props = find_peaks(
            stride_signal,
            distance=peak_distance,
            prominence=stride_prominence,
        )
        stride_peak_indices = np.asarray(stride_peaks, dtype=int)
        stride_prominences = np.asarray(
            stride_props.get("prominences", np.zeros(len(stride_peak_indices))),
            dtype=float,
        )

        def stride_activity_score(start_idx, end_idx):
            mask = (stride_peak_indices >= start_idx) & (stride_peak_indices <= end_idx)
            if not np.any(mask):
                return 0.0
            return float(np.sum(stride_prominences[mask]))

        def local_left_peak(valley_idx, low_start):
            search_pad = max(int(round(fs * 0.60)), valley_idx - low_start)
            search_start = max(0, valley_idx - search_pad)
            if search_start >= valley_idx:
                return None
            return int(np.argmax(signal[search_start:valley_idx]) + search_start)

        def first_plateau_after_rise(valley_idx, right_peak_idx):
            segment = signal[valley_idx:right_peak_idx + 1]
            if len(segment) <= 2:
                return int(right_peak_idx)

            local_max = float(np.max(segment))
            tol = max(0.02, 0.08 * max(local_max - float(np.min(segment)), 1e-6))
            grad = np.diff(segment)

            for rel_idx in range(1, len(segment) - 1):
                value = float(segment[rel_idx])
                if value < local_max - tol:
                    continue
                future_grad = grad[rel_idx:min(len(grad), rel_idx + 3)]
                if len(future_grad) == 0 or float(np.mean(future_grad)) <= 0:
                    return int(valley_idx + rel_idx)

            return int(right_peak_idx)

        best = None
        for low_start, low_end in low_regions:
            valley_idx = int(np.argmin(signal[low_start:low_end + 1]) + low_start)
            left_maxima = maxima[maxima < valley_idx]
            right_maxima = maxima[maxima > valley_idx]
            if len(right_maxima) == 0:
                continue

            if len(left_maxima) > 0:
                left_peak_idx = int(left_maxima[-1])
            else:
                left_peak_idx = local_left_peak(valley_idx, low_start)
                if left_peak_idx is None:
                    continue
            right_peak_idx = int(right_maxima[0])
            drop = float(signal[left_peak_idx] - signal[valley_idx])
            rise = float(signal[right_peak_idx] - signal[valley_idx])
            if drop <= 0 or rise <= 0:
                continue

            plateau_idx = first_plateau_after_rise(valley_idx, right_peak_idx)
            width = right_peak_idx - left_peak_idx
            stride_score = stride_activity_score(left_peak_idx, right_peak_idx)

            # Favor the sharpest pressure dip-and-rise, with stride activity
            # used only as a tie-breaker.
            score = (
                -(drop + rise),
                width,
                -stride_score,
            )
            if best is None or score < best[0]:
                best = (
                    score,
                    low_start,
                    low_end,
                    valley_idx,
                    left_peak_idx,
                    right_peak_idx,
                    plateau_idx,
                    drop,
                    rise,
                    stride_score,
                )

        if best is None:
            raise ValueError("Could not match a pressure dip-and-rise teeter pattern.")

        (
            _,
            low_start,
            low_end,
            valley_idx,
            left_peak_idx,
            right_peak_idx,
            plateau_idx,
            drop,
            rise,
            stride_score,
        ) = best

        return {
            "strategy": "large",
            "signal_name": "Pressure_scaled" if "Pressure_scaled" in self.df.columns else "Pressure_F",
            "low_threshold": low_threshold,
            "low_region_start_index": int(low_start),
            "low_region_end_index": int(low_end),
            "low_region_start_time_s_trimmed": float(time_s[low_start]),
            "low_region_end_time_s_trimmed": float(time_s[low_end]),
            "pressure_valley": self._anchor(valley_idx, time_s),
            "pressure_left_peak": self._anchor(left_peak_idx, time_s),
            "pressure_right_peak": self._anchor(right_peak_idx, time_s),
            "pressure_drop": float(drop),
            "pressure_rise": float(rise),
            "stride_activity_score": float(stride_score),
            "lowest_point_after_tilt": self._anchor(plateau_idx, time_s),
        }

    def align(self, anchor_name=None, video_anchor_frame=None):
        """Compute a video-to-IMU offset from a chosen teeter anchor frame."""
        if video_anchor_frame is None:
            raise ValueError("video_anchor_frame is required for teeter alignment.")

        anchors = self.detect_teeter_imu_anchors()
        if anchor_name is None:
            anchor_name = (
                "hind_legs_leave_teeter"
                if self.strategy == "small"
                else "lowest_point_after_tilt"
            )
        if anchor_name not in anchors:
            raise ValueError(f"Unknown teeter anchor '{anchor_name}'")

        video_ms = self.frame_to_ms(int(video_anchor_frame))
        imu_ms = anchors[anchor_name]["time_s"] * 1000.0
        offset_ms = imu_ms - video_ms

        return {
            "offset_ms": float(offset_ms),
            "confidence": 0.70 if self.strategy == "small" else 0.65,
            "strategy": self.strategy,
            "anchor_name": anchor_name,
            "video_anchor_frame": int(video_anchor_frame),
            "imu_anchor_index": anchors[anchor_name]["index"],
            "imu_anchor_time_s": anchors[anchor_name]["time_s"],
            "anchors": anchors,
        }

    def align_multi(self, video_anchor_frames):
        """Estimate one offset from one or more teeter anchors.

        For small dogs, averages offsets across any subset of:
        about_to_jump_off, stepped_off, hind_legs_leave_teeter.
        For large dogs, expects lowest_point_after_tilt.
        """
        anchors = self.detect_teeter_imu_anchors()
        rows = []
        for anchor_name, frame_num in video_anchor_frames.items():
            if anchor_name not in anchors:
                raise ValueError(f"Unknown teeter anchor '{anchor_name}'")

            video_ms = self.frame_to_ms(int(frame_num))
            imu_ms = anchors[anchor_name]["time_s"] * 1000.0
            rows.append(
                {
                    "anchor_name": anchor_name,
                    "video_anchor_frame": int(frame_num),
                    "video_time_ms": float(video_ms),
                    "imu_anchor_index": int(anchors[anchor_name]["index"]),
                    "imu_anchor_time_s": float(anchors[anchor_name]["time_s"]),
                    "imu_time_ms": float(imu_ms),
                    "offset_ms": float(imu_ms - video_ms),
                }
            )

        if not rows:
            raise ValueError("Need at least one teeter anchor frame.")

        offset_ms = float(np.mean([row["offset_ms"] for row in rows]))
        for row in rows:
            row["residual_ms"] = float(row["offset_ms"] - offset_ms)
        rmse_ms = float(np.sqrt(np.mean([row["residual_ms"] ** 2 for row in rows])))

        return {
            "offset_ms": offset_ms,
            "confidence": 0.72 if self.strategy == "small" else 0.67,
            "strategy": self.strategy,
            "model": "t_imu_ms = t_video_ms + offset_ms",
            "rmse_ms": rmse_ms,
            "anchor_rows": rows,
            "anchors": anchors,
        }


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print(
            "Usage: python teeter_aligner.py <data_dir> [strategy]\n"
            "   or: python teeter_aligner.py <data_dir> [strategy] "
            "<anchor_name> <video_anchor_frame>"
        )
        sys.exit(1)

    data_dir = sys.argv[1]
    strategy = "auto"
    arg_idx = 2
    if len(sys.argv) > 2 and sys.argv[2] in {"auto", "small", "large"}:
        strategy = sys.argv[2]
        arg_idx = 3

    aligner = TeeterAligner(data_dir, prefer_trimmed=True, strategy=strategy)

    if len(sys.argv) <= arg_idx:
        result = aligner.detect_teeter_imu_anchors()
    elif sys.argv[arg_idx] == "multi":
        video_anchor_frames = {}
        for arg in sys.argv[arg_idx + 1:]:
            if "=" not in arg:
                raise ValueError(
                    "Multi-anchor arguments must look like stepped_off=1990"
                )
            anchor_name, frame_num = arg.split("=", 1)
            video_anchor_frames[anchor_name] = int(frame_num)
        result = aligner.align_multi(video_anchor_frames)
    else:
        anchor_name = sys.argv[arg_idx]
        video_anchor_frame = int(sys.argv[arg_idx + 1])
        result = aligner.align(
            anchor_name=anchor_name,
            video_anchor_frame=video_anchor_frame,
        )

    print(json.dumps(result, indent=2))
