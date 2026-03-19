"""
Preprocess IMU CSV data using the same pipeline as MMData.py.

Usage:
    from preprocessing import preprocess_imu
    df = preprocess_imu("path/to/imu.csv")

The returned DataFrame contains original columns plus:
    Relative_Time_s, Relative_Time_ms  - timestamps relative to first sample
    Amag_raw       - accelerometer magnitude (z-scored)
    Gmag_raw       - gyroscope magnitude (z-scored)
    Amag_F         - accel magnitude after 5 Hz low-pass filter
    Gmag_F         - gyro magnitude after 5 Hz low-pass filter
    Pressure_F     - pressure after 2 Hz low-pass (if Pressure column exists)
    Pressure_scaled - pressure min-max scaled to accel range (if Pressure column exists)
    fs             - estimated sampling frequency (stored as df.attrs['fs'])
"""

import sys
import numpy as np
import pandas as pd
from scipy.signal import butter, filtfilt


def apply_lowpass(data, cutoff, fs, order=4):
    nyquist = 0.5 * fs
    normal_cutoff = cutoff / nyquist
    if normal_cutoff >= 1:
        normal_cutoff = 0.99
    b, a = butter(order, normal_cutoff, btype='low', analog=False)
    return filtfilt(b, a, data)


def preprocess_imu(csv_path):
    """Load and preprocess an IMU CSV file.

    Returns the preprocessed DataFrame, or raises on error.
    """
    df = pd.read_csv(csv_path)
    if df.empty:
        raise ValueError("CSV file is empty.")
    if 'Timestamp' not in df.columns or 'Ax' not in df.columns:
        raise ValueError("'Timestamp' or 'Ax' column not found in CSV.")

    # Relative timestamps
    df['Relative_Time_s'] = df['Timestamp'] - df['Timestamp'].iloc[0]
    df['Relative_Time_ms'] = df['Relative_Time_s'] * 1000

    # Sampling frequency
    diffs = np.diff(df['Relative_Time_s'])
    fs = 1.0 / np.mean(diffs) if len(diffs) > 0 else 100.0
    df.attrs['fs'] = fs

    # Accelerometer magnitude (z-scored)
    amag = np.sqrt(df['Ax']**2 + df['Ay']**2 + df['Az']**2)
    df['Amag_raw'] = (amag - np.mean(amag)) / np.std(amag)

    # Gyroscope magnitude (z-scored)
    gmag = np.sqrt(df['Gx']**2 + df['Gy']**2 + df['Gz']**2)
    df['Gmag_raw'] = (gmag - np.mean(gmag)) / np.std(gmag)

    # Low-pass filtered signals
    df['Amag_F'] = apply_lowpass(df['Amag_raw'].values, 5.0, fs)
    df['Gmag_F'] = apply_lowpass(df['Gmag_raw'].values, 5.0, fs)

    # Pressure (if present)
    if 'Pressure' in df.columns:
        df['Pressure_F'] = apply_lowpass(df['Pressure'].values, 2.0, fs)
        p = df['Pressure_F'].values
        if p.max() > p.min():
            df['Pressure_scaled'] = (p - p.min()) / (p.max() - p.min()) * df['Amag_raw'].max()
        else:
            df['Pressure_scaled'] = p

    return df


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python preprocessing.py <csv_path>")
        sys.exit(1)
    df = preprocess_imu(sys.argv[1])
    print(f"Loaded {len(df)} samples, fs={df.attrs['fs']:.1f} Hz")
    print(f"Columns: {list(df.columns)}")
    print(df[['Relative_Time_s', 'Amag_raw', 'Amag_F', 'Gmag_raw', 'Gmag_F']].describe())
