import os
import joblib
import imufusion
import numpy as np
import pandas as pd
from pathlib import Path
from scipy.stats import mstats
import matplotlib.pyplot as plt
from sklearn.decomposition import PCA
from scipy.signal import butter, filtfilt, spectrogram


class DataPreProcessor:
    def __init__(self, master_dir, sync_dir, n_components=7, use_euler=False, target_fs=100):
        self.master_dir = Path(master_dir)
        self.sync_dir = Path(sync_dir)
        self.use_euler = use_euler
        self.target_fs = target_fs
        
        # Adjust component count: Euler only provides 3 axes (Roll, Pitch, Yaw)
        if self.use_euler:
            self.n_components = min(n_components, 3)
            self.feature_cols = ['Roll', 'Pitch', 'Yaw']
        else:
            self.target_fs = 100
            self.n_components = n_components
            self.feature_cols = ['Ax', 'Ay', 'Az', 'Gx', 'Gy', 'Gz', 'Pressure']

        self.pca = PCA(n_components=self.n_components)
        self.dog_stats = {} 
        
        # Load all master alignment files into a dictionary for quick lookup
        self.master_data = {
            p.stem.split('_')[0]: pd.read_csv(p) 
            for p in self.master_dir.glob("*_master.csv")
        }

    def check_file_integrity(self, file_path, target_hz=100, threshold_seconds=2.0):
        """
        Checks if a CSV file has significant time gaps.
        Returns True if the file is valid, False if it should be skipped.
        """
        try:
            df = pd.read_csv(file_path)
            if df.empty:
                return False

            # 1. Calculate Expected Duration based on Sample Count
            # (Number of rows / 100 samples per second)
            num_samples = len(df)
            expected_duration = num_samples / target_hz

            # 2. Calculate Actual Duration based on Timestamps
            start_ts = df['Timestamp'].iloc[0]
            end_ts = df['Timestamp'].iloc[-1]
            actual_duration = end_ts - start_ts

            # 3. Compute the Difference
            time_diff = abs(actual_duration - expected_duration)

            # if time_diff > threshold_seconds:
            #     print(f"SKIP: {file_path} - Gap Detected: {time_diff:.2f}s difference "
            #           f"(Expected: {expected_duration:.2f}s, Actual: {actual_duration:.2f}s)")
            #     return False
            return True

        except Exception as e:
            print(f"ERROR reading {file_path}: {e}")
            return False

    def _compute_euler_angles(self, df):
        """
        Internal helper to resample and compute unwrapped Euler angles.
        Expects standard CSV structure: Timestamp(0), Accel(1:4), Gyro(4:7).
        """
        seconds = df.iloc[:, 0].values
        accel_raw = df.iloc[:, 1:4].values
        gyro_raw = df.iloc[:, 4:7].values

        # 1. Create uniform time grid for AHRS stability
        t_uniform = np.arange(seconds[0], seconds[-1], 1/self.target_fs)
        
        # 2. Resample raw data to uniform grid
        gyro_u = np.zeros((len(t_uniform), 3))
        accel_u = np.zeros((len(t_uniform), 3))
        for i in range(3):
            gyro_u[:, i] = np.interp(t_uniform, seconds, gyro_raw[:, i])
            accel_u[:, i] = np.interp(t_uniform, seconds, accel_raw[:, i])

        # 3. Initialize and run IMU Fusion
        ahrs = imufusion.Ahrs()
        ahrs.settings = imufusion.AhrsSettings(sample_rate=self.target_fs)
        euler = np.empty((len(t_uniform), 3))

        for i in range(len(t_uniform)):
            ahrs.update_no_magnetometer(gyro_u[i], accel_u[i])
            euler[i] = imufusion.quaternion_to_euler(ahrs.quaternion)

        # 4. Unwrap and convert to degrees for consistency
        euler = np.degrees(np.unwrap(np.radians(euler), axis=0))
        
        return pd.DataFrame({
            'Timestamp': t_uniform, 
            'Roll': euler[:, 0], 
            'Pitch': euler[:, 1], 
            'Yaw': euler[:, 2]
        })

    def get_trial_slice(self, trial_name):
        """Finds and slices a trial, applying Euler transformation if requested."""
        dog_name = trial_name.split('_')[0]
        if dog_name not in self.master_data:
            return None
        master_df = self.master_data[dog_name]
        row = master_df[master_df['Repetition'] == trial_name]
        if row.empty:
            row = master_df[master_df['Repetition'].str.lower() == trial_name.lower()]
        if row.empty:
            return None
        if row.empty:
            return None
        row = row.iloc[0]
        # Locate raw sensor file
        # RECURSIVE SEARCH
        search_pattern = f"{dog_name}/{trial_name}/**/*_cleaned.csv"
        matches = list(self.sync_dir.glob(search_pattern))
        if not matches:
            matches = list(self.sync_dir.glob(f"**/{trial_name}/*_cleaned.csv"))
        if not matches:
            return None
        # Check file integrity (2s gap check)
        if not self.check_file_integrity(matches[0], target_hz=self.target_fs):
            return None
        df = pd.read_csv(matches[0])
        # Determine indices based on master alignment offsets
        offset = int(row['Offset']) - int(row['Anchor_Offset'])
        orig_s = max(0, min(int(row['span_start'] + offset), len(df) - 1))
        orig_e = max(0, min(int(row['span_end'] + offset), len(df) - 1))
        
        # Extract time bounds for resampling-safe slicing
        t_start, t_end = df.iloc[orig_s]['Timestamp'], df.iloc[orig_e]['Timestamp']

        if self.use_euler:
            # Process entire trial to maintain AHRS filter state, then slice by time
            self.feature_cols = ['Roll', 'Pitch', 'Yaw']
            processed_df = self._compute_euler_angles(df)
            # Search the resampled time grid directly — don't assume uniform spacing
            # in the raw data, as drift makes (t - t0) * fs unreliable
            t_grid = processed_df['Timestamp'].values
            idx_s = int(np.searchsorted(t_grid, t_start))
            idx_e = int(np.searchsorted(t_grid, t_end, side='right')) - 1
            idx_s = max(0, idx_s)
            idx_e = min(idx_e, len(processed_df) - 1)
            segment = processed_df.iloc[idx_s : idx_e + 1].copy()
        else:
            segment = df.iloc[orig_s : orig_e + 1].copy()

        # Apply filtering and leveling
        if len(segment) > 10:
            fs = self.target_fs if self.use_euler else (1.0 / np.mean(np.diff(segment['Timestamp'])))
            #print(self.feature_cols)
            segment[self.feature_cols] = apply_lowpass(segment[self.feature_cols].values, 5.0, fs)
            if not self.use_euler:
                segment = self.apply_full_dynamic_leveling(segment)
            return segment
        return None

    def get_all_trial_names(self):
        """Consolidates trial names across all loaded master files."""
        all_trials = []
        for df in self.master_data.values():
            if 'Trial' in df.columns:
                all_trials.extend(df['Trial'].dropna().unique().tolist())
            elif 'Repetition' in df.columns:
                all_trials.extend(df['Repetition'].dropna().unique().tolist())
            else:
                # Robust reconstruction if Trial column is absent
                temp = df['Dog'].astype(str) + "_" + df['Obstacle'].astype(str) + "_" + df['Repetition'].astype(str)
                all_trials.extend(temp.unique().tolist())
        return list(set(all_trials))

    def calculate_dog_stats(self, trial_names):
        """Main entry point for pipeline initialization."""
        unique_dogs = set(t.split('_')[0] for t in trial_names)
        for dog in unique_dogs:
            self.get_dog_stats(dog)
        self.fit_pca(trial_names)

    def get_dog_stats(self, dog_name):
        """Calculates mean/std for normalization."""
        if dog_name in self.dog_stats: 
            return self.dog_stats[dog_name]
        
        all_feats = []
        dog_trials = [t for t in self.get_all_trial_names() if t.startswith(dog_name)]
        for trial in dog_trials:
            seg = self.get_trial_slice(trial)
            if seg is not None:
                all_feats.append(seg[self.feature_cols].values)
                
        if not all_feats: 
            return None
            
        combined = np.vstack(all_feats)
        self.dog_stats[dog_name] = {
            'mean': np.mean(combined, axis=0), 
            'std': np.std(combined, axis=0)
        }
        return self.dog_stats[dog_name]

    def get_normalized_features(self, trial_name):
        """Normalizes segment features using dog-specific stats."""
        segment = self.get_trial_slice(trial_name)
        if segment is None: 
            return None
        stats = self.get_dog_stats(trial_name.split('_')[0])
        if stats is None: 
            return None
        return (segment[self.feature_cols].values - stats['mean']) / (stats['std'] + 1e-6)

    def fit_pca(self, trial_names):
        """Fits the PCA model on normalized features."""
        feats = [self.get_normalized_features(t) for t in trial_names]
        feats = [f for f in feats if f is not None]
        if feats:
            self.pca.fit(np.vstack(feats))

    def transform(self, trial_name, raw=False):
        """Returns PCA-transformed data."""
        norm = self.get_normalized_features(trial_name)
        if norm is None: 
            return None
        return norm if raw else self.pca.transform(norm)

    def apply_full_dynamic_leveling(self, df):
        """Levels raw accelerometer data based on gravity."""
        accel = df[['Ax', 'Ay', 'Az']].values
        R = get_rotation_matrix(np.mean(accel, axis=0))
        df[['Ax', 'Ay', 'Az']] = accel @ R.T
        return df

    def save(self, path="gait_metadata.pkl"):
        """Saves stats, PCA model, and current mode."""
        joblib.dump({
            'stats': self.dog_stats, 
            'pca': self.pca, 
            'euler': self.use_euler
        }, path)

    def load(self, path="gait_metadata.pkl"):
        """Loads saved processor state."""
        data = joblib.load(path)
        self.dog_stats = data['stats']
        self.pca = data['pca']
        self.use_euler = data.get('euler', False)


def get_rotation_matrix(a, b=np.array([0, 0, 1])):
    """Calculates rotation matrix from vector a to vector b."""
    a = a / np.linalg.norm(a)
    v = np.cross(a, b)
    c, s = np.dot(a, b), np.linalg.norm(v)
    if s < 1e-6: return np.eye(3)
    v_skew = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    return np.eye(3) + v_skew + (v_skew @ v_skew) * ((1 - c) / (s ** 2))

def apply_lowpass(data, cutoff, fs, order=4):
    nyquist = 0.5 * fs
    normal_cutoff = cutoff / nyquist
    if normal_cutoff >= 1: normal_cutoff = 0.99
    b, a = butter(order, normal_cutoff, btype='low', analog=False)
    y = filtfilt(b, a, data, axis=0)
    return y