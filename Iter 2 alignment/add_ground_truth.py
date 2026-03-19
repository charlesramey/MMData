"""
Add ground truth manual alignment column (and error column) to an obstacle
anchors CSV.

Usage
-----
    python add_ground_truth.py <obstacle_type>

Examples
--------
    python add_ground_truth.py Tunnel
    python add_ground_truth.py Flat
    python add_ground_truth.py Aframe

The script:
  1. Reads all CSVs in ../Ground Truth Manual Alignments/
  2. Extracts rows whose Directory matches *_<obstacle_type>_*
  3. Writes the GT Offset_ms into a 'GT_Offset_ms' column in the anchors CSV
  4. Adds 'Error_ms' = Offset_ms - GT_Offset_ms

Anchors CSV is resolved automatically:
    Tunnel  -> Tunnel Motion Onset Frames.csv
    Flat    -> Flat Motion Onset Frames.csv
    Aframe  -> Aframe Apex Frames.csv
"""

import os
import sys
import glob

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
GT_DIR = os.path.join(HERE, '..', 'Ground Truth Manual Alignments')

ANCHORS_CSV = {
    'tunnel': os.path.join(HERE, 'Tunnel Motion Onset Frames.csv'),
    'flat':   os.path.join(HERE, 'Flat Motion Onset Frames.csv'),
    'aframe': os.path.join(HERE, 'Aframe Apex Frames.csv'),
}


def load_ground_truth(obstacle_type):
    """Return a dict mapping folder name -> GT Offset_ms for the given obstacle."""
    pattern = f'*_{obstacle_type}_*'
    gt = {}
    for csv_path in glob.glob(os.path.join(GT_DIR, '*.csv')):
        df = pd.read_csv(csv_path)
        if 'Directory' not in df.columns or 'Offset_ms' not in df.columns:
            print(f"  SKIP (unexpected columns): {os.path.basename(csv_path)}")
            continue
        mask = df['Directory'].str.contains(f'_{obstacle_type}_', case=False, na=False)
        matches = df[mask]
        for _, row in matches.iterrows():
            folder = row['Directory']
            if folder in gt:
                print(f"  WARN: duplicate GT entry for {folder}, keeping first")
                continue
            gt[folder] = row['Offset_ms']
        if matches.shape[0]:
            print(f"  {os.path.basename(csv_path)}: {matches.shape[0]} {obstacle_type} entries")
    return gt


def main():
    if len(sys.argv) < 2:
        print("Usage: python add_ground_truth.py <obstacle_type>")
        print("  obstacle_type: Tunnel, Flat, or Aframe")
        sys.exit(1)

    obstacle_type = sys.argv[1]
    key = obstacle_type.lower()

    if key not in ANCHORS_CSV:
        print(f"Unknown obstacle type '{obstacle_type}'. Choose from: Tunnel, Flat, Aframe")
        sys.exit(1)

    anchors_path = ANCHORS_CSV[key]
    if not os.path.exists(anchors_path):
        print(f"Anchors CSV not found: {anchors_path}")
        sys.exit(1)

    print(f"Loading ground truth for obstacle type: {obstacle_type}")
    gt = load_ground_truth(obstacle_type)
    print(f"  Total GT entries found: {len(gt)}")

    df = pd.read_csv(anchors_path)

    df['GT_Offset_ms'] = df['Folder'].map(gt)
    df['Error_ms'] = df['Offset_ms'] - df['GT_Offset_ms']

    df.to_csv(anchors_path, index=False)
    print(f"\nUpdated: {anchors_path}")

    filled = df['GT_Offset_ms'].notna().sum()
    print(f"  GT_Offset_ms filled: {filled} / {len(df)} rows")

    errors = df[df['Error_ms'].notna()][['Folder', 'Offset_ms', 'GT_Offset_ms', 'Error_ms']]
    if not errors.empty:
        print(f"\n{'Folder':<30} {'Offset_ms':>10} {'GT_Offset_ms':>13} {'Error_ms':>10}")
        print("-" * 68)
        for _, r in errors.iterrows():
            print(f"{r['Folder']:<30} {r['Offset_ms']:>10.1f} {r['GT_Offset_ms']:>13.1f} {r['Error_ms']:>10.1f}")
        mae = errors['Error_ms'].abs().mean()
        print(f"\nMean absolute error: {mae:.1f} ms")


if __name__ == '__main__':
    main()
