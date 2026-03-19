"""
Base class for obstacle-specific video-to-IMU alignment.

Each obstacle type (Aframe, Teeter, Flat, etc.) subclasses ObstacleAligner
and implements its own align() method using obstacle-specific heuristics.
"""

import os
import sys
from abc import ABC, abstractmethod

import cv2
import numpy as np
import pandas as pd

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
for _extra_path in (
    os.path.join(_ROOT, 'Tools'),
    os.path.join(_ROOT, 'MMData Tools'),
):
    if _extra_path not in sys.path:
        sys.path.insert(0, _extra_path)

from preprocessing import preprocess_imu
from mmdata_utils import find_video_csv_pair


class ObstacleAligner(ABC):
    """Abstract base for aligning a video to IMU data for a single repetition.

    Parameters
    ----------
    data_dir : str
        Path to a repetition folder (e.g. 720sync/Derby_Aframe_1/) containing
        one video file and one cleaned IMU CSV.
    prefer_trimmed : bool
        If True, prefer *_trimmed.csv over *_cleaned.csv.
    """

    _HERE = os.path.dirname(os.path.abspath(__file__))
    TRIM_TIMES_CSV = (
        os.path.join(_HERE, 'imu_trim_times.csv')
        if os.path.exists(os.path.join(_HERE, 'imu_trim_times.csv'))
        else os.path.join(_HERE, '..', 'Tools', 'imu_trim_times.csv')
    )

    def __init__(self, data_dir, prefer_trimmed=False):
        self.data_dir = data_dir
        self.rep_name = os.path.basename(os.path.normpath(data_dir))
        self.prefer_trimmed = prefer_trimmed

        video_path, csv_path = find_video_csv_pair(data_dir, prefer_trimmed=prefer_trimmed)
        if not video_path or not csv_path:
            raise FileNotFoundError(f"Could not find video/CSV pair in {data_dir}")

        self.video_path = video_path
        self.csv_path = csv_path
        self.using_trimmed = '_trimmed.csv' in csv_path

        # Preprocess IMU
        try:
            self.df = preprocess_imu(csv_path)
        except ValueError:
            fallback_csv = None
            if self.using_trimmed:
                candidate = csv_path.replace('_trimmed.csv', '_cleaned.csv')
                if candidate != csv_path and os.path.exists(candidate):
                    fallback_csv = candidate
            if fallback_csv is None:
                raise

            self.csv_path = fallback_csv
            self.using_trimmed = False
            self.df = preprocess_imu(fallback_csv)

        self.fs = self.df.attrs['fs']

        # Trim offset: time (s) from original IMU start to trimmed start
        self.trim_offset_s = 0.0
        if self.using_trimmed:
            self.trim_offset_s = self._lookup_trim_offset()

        # Video metadata
        cap = cv2.VideoCapture(video_path)
        self.video_fps = cap.get(cv2.CAP_PROP_FPS)
        self.total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.video_duration_ms = (self.total_frames / self.video_fps) * 1000
        cap.release()

    def _lookup_trim_offset(self):
        """Look up trim_start_time_s for this rep from imu_trim_times.csv."""
        if not os.path.exists(self.TRIM_TIMES_CSV):
            return 0.0
        df = pd.read_csv(self.TRIM_TIMES_CSV)
        row = df.loc[df['Repetition'] == self.rep_name]
        if row.empty:
            return 0.0
        return float(row.iloc[0]['trim_start_time_s'])

    @abstractmethod
    def align(self):
        """Find the best time offset (ms) to align video to IMU.

        Returns
        -------
        dict with at least:
            offset_ms : float
                The offset such that imu_time = video_time + offset_ms.
            confidence : float
                A score in [0, 1] indicating alignment confidence.
        """
        ...

    def frame_to_ms(self, frame_num):
        """Convert a video frame number to milliseconds."""
        return (frame_num / self.video_fps) * 1000

    def ms_to_frame(self, ms):
        """Convert milliseconds to the nearest video frame number."""
        return int(round((ms / 1000) * self.video_fps))

    def imu_time_at(self, video_ms, offset_ms):
        """Return the IMU time (s) corresponding to a video time + offset."""
        return (video_ms + offset_ms) / 1000.0
