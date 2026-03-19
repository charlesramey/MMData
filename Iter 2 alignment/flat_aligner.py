"""
Flat-specific video-to-IMU alignment.

Heuristic: the dog's motion onset frame (first directed forward locomotion)
corresponds to the IMU trim start time. No IMU peak detection is performed —
the offset is computed directly from the known onset frame and trim offset.
"""

import os

import pandas as pd

from obstacle_aligner import ObstacleAligner

MOTION_ONSET_CSV = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                'Flat Motion Onset Frames.csv')


class FlatAligner(ObstacleAligner):
    """Align a flat repetition using the motion-onset-to-trim-start heuristic.

    Parameters
    ----------
    data_dir : str
        Path to a repetition folder (e.g. 720sync/Arya_Flat_1/).
    motion_onset_frame : int or None
        Video frame number where the dog begins directed forward locomotion.
        If None, attempts to read from Flat Motion Onset Frames.csv.
    prefer_trimmed : bool
        If True, prefer *_trimmed.csv over *_cleaned.csv.
    """

    def __init__(self, data_dir, motion_onset_frame=None, prefer_trimmed=True):
        super().__init__(data_dir, prefer_trimmed=prefer_trimmed)
        self.motion_onset_frame = motion_onset_frame or self._detect_motion_onset_frame()

    def _detect_motion_onset_frame(self):
        """Look up the motion onset frame from Flat Motion Onset Frames.csv."""
        if not os.path.exists(MOTION_ONSET_CSV):
            return None
        df = pd.read_csv(MOTION_ONSET_CSV)
        row = df.loc[df['Folder'] == self.rep_name]
        if row.empty:
            return None
        n = int(row.iloc[0]['Motion_Onset_Frame'])
        return n if n > 0 else None

    def align(self):
        """Compute the offset aligning the motion onset frame to the IMU trim start.

        The IMU trim start corresponds to time 0 in a trimmed CSV, or
        trim_offset_s in the original (untrimmed) stream. The video motion
        onset frame is matched to this anchor.

        Returns
        -------
        dict
            offset_ms : float
                Offset such that imu_time = video_time + offset_ms.
            confidence : float
                Always 1.0 (the anchor is manually verified).
            motion_onset_frame : int
                Video frame used as anchor.
            imu_anchor_time_s : float
                IMU time (relative to original start) of the anchor point.
        """
        if self.motion_onset_frame is None:
            raise ValueError(
                f"No motion onset frame for {self.rep_name}. "
                "Provide motion_onset_frame or add an entry to "
                "Flat Motion Onset Frames.csv."
            )

        onset_video_ms = self.frame_to_ms(self.motion_onset_frame)
        imu_anchor_time_s = self.trim_offset_s          # 0.0 if not trimmed
        imu_anchor_ms = imu_anchor_time_s * 1000

        offset_ms = imu_anchor_ms - onset_video_ms

        return {
            'offset_ms': offset_ms,
            'confidence': 1.0,
            'motion_onset_frame': self.motion_onset_frame,
            'imu_anchor_time_s': imu_anchor_time_s,
        }


if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print("Usage: python flat_aligner.py <data_dir> [motion_onset_frame]")
        sys.exit(1)

    data_dir = sys.argv[1]
    onset = int(sys.argv[2]) if len(sys.argv) > 2 else None
    aligner = FlatAligner(data_dir, motion_onset_frame=onset)
    result = aligner.align()

    print(f"\n{aligner.rep_name}")
    print(f"  Motion onset frame: {result['motion_onset_frame']}")
    print(f"  IMU anchor time:    {result['imu_anchor_time_s']:.3f}s")
    print(f"  Offset:             {result['offset_ms']:+.1f} ms")
    print(f"  Confidence:         {result['confidence']:.2f}")
