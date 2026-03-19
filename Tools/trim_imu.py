"""
Trim IMU CSV files to obstacle segments using the master alignments CSV.

Computes per-rep row indices from span_start/span_end and the relative
offset between each rep's Offset and Anchor_Offset.

Usage:
    python trim_imu.py <master_csv> <base_dir> [--dry-run]

Example:
    python trim_imu.py FIXEDMasterAlignments/Arya_clean_master.csv "Arya Aframe/"
    python trim_imu.py FIXEDMasterAlignments/Arya_clean_master.csv "Arya Aframe/" --dry-run
"""
import sys
import os
import glob
import pandas as pd


def find_cleaned_csv(rep_dir):
    """Find the *_cleaned.csv file in a repetition directory."""
    matches = glob.glob(os.path.join(rep_dir, "*_cleaned.csv"))
    return matches[0] if matches else None


def trim_imu(master_csv, base_dir, dry_run=False):
    master = pd.read_csv(master_csv)

    rep_dirs = {os.path.basename(d): d for d in glob.glob(os.path.join(base_dir, "*"))}

    for _, row in master.iterrows():
        rep_name = row['Repetition']

        rep_dir = rep_dirs.get(rep_name)
        if rep_dir is None:
            print(f"SKIP {rep_name}: no directory found in {base_dir}")
            continue

        csv_path = find_cleaned_csv(rep_dir)
        if csv_path is None:
            print(f"SKIP {rep_name}: no *_cleaned.csv found in {rep_dir}")
            continue

        df = pd.read_csv(csv_path)
        original_rows = len(df)

        offset = int(row['Offset']) - int(row['Anchor_Offset'])
        idx_start = int(row['span_start']) + offset
        idx_end = int(row['span_end']) + offset

        idx_start = max(0, min(idx_start, len(df) - 1))
        idx_end = max(0, min(idx_end, len(df) - 1))

        if idx_start > idx_end:
            idx_end = idx_start

        segment = df.iloc[idx_start:idx_end + 1].copy()

        out_name = os.path.basename(csv_path).replace("_cleaned.csv", "_trimmed.csv")
        out_path = os.path.join(rep_dir, out_name)

        print(f"{rep_name}: {csv_path}")
        print(f"  offset={offset}, span=[{int(row['span_start'])},{int(row['span_end'])}] -> idx=[{idx_start},{idx_end}]")
        print(f"  {original_rows} rows -> {len(segment)} rows")
        print(f"  -> {out_path}")

        if not dry_run:
            segment.to_csv(out_path, index=False)
            print(f"  SAVED")
        else:
            print(f"  (dry run, not saved)")
        print()


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    master_csv = sys.argv[1]
    base_dir = sys.argv[2]
    dry_run = "--dry-run" in sys.argv

    trim_imu(master_csv, base_dir, dry_run)
