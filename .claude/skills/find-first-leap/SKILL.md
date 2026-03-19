---
name: find-first-leap
description: Find the video frame where a dog reaches the peak of its first leap, using a coarse-to-fine visual scan of video frames. Use when asked to find first leap, first jump, or peak airborne frame in agility videos.
argument-hint: <folder-pattern> [--examples-dir <path>] [--crop x1 y1 x2 y2]
allowed-tools: Read, Glob, Grep, Bash(python3 *), Bash(ls *), Bash(mkdir *)
---

# Find First Leap Frame

Find the frame number where a dog is at the peak of its first leap in an agility video.

## Inputs

- `$0` — Folder glob pattern under `720sync/` (e.g. `Derby_Tunnel_*`, `Arya_Flat_*`)
- `$1` (optional) — `--examples-dir <path>` to a folder with reference images of stationary vs first-leap poses
- `$2` (optional) — `--crop x1 y1 x2 y2` pixel region to crop for close-up views (default: `50 150 550 450`)

If no arguments given, ask the user which folders to scan.

## Reference Examples

If an examples directory is provided or exists at `Examples - Tunnel/` (or similar `Examples-<Obstacle>/`), read the cropped first-leap images first to understand what "peak of first leap" looks like:
- Dog is fully airborne, all four paws off the ground
- Body stretched horizontally in a gallop stride
- Maximum vertical elevation relative to preceding/following frames

## Automated detection (preferred for batch processing)

For large batches (>5 folders), use the automation script:

```bash
python .claude/skills/find-first-leap/scripts/auto_detect_first_leap.py \
    "720sync/*_Tunnel_*" \
    --save-frames \
    --output-csv "Tunnel First Leap Frames.csv"
```

The script uses a three-phase pipeline:
1. **Motion detection** — frame differencing to find when the dog starts running
2. **Vertical motion analysis** — tracks the vertical centroid of motion; the first leap peak = first local minimum in y-position (highest off ground)
3. **Per-frame refinement** — ±15 frame window around the estimate, selecting the frame with the lowest vertical centroid

## Manual procedure (for small batches or verification)

For each matching folder under `720sync/`:

### Step 1 — Video metadata
Find the `.mp4` file, get total frames and FPS using:
```python
cap = cv2.VideoCapture(path); total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)); fps = cap.get(cv2.CAP_PROP_FPS)
```

### Step 2 — Coarse scan (every 100 frames)
Extract and save frames every 100 to a temp directory. View them to identify:
- The **last stationary frame** (dog standing still)
- The **first clearly-running frame** (dog in full gallop)
This narrows the leap region to a ~200-frame window.

### Step 3 — Fine scan (every 20 frames)
Extract frames every 20 within the identified window. Use cropped versions (focusing on the dog) to better see limb positions. Narrow to a ~60-frame window around the first visible airborne moment.

### Step 4 — Superfine scan (every 3-5 frames)
Extract cropped frames every 3-5 in the narrowed window. Identify the ~10-frame region where the dog appears most elevated/extended.

### Step 5 — Per-frame scan
Extract every single frame in the ~10-frame candidate region. Select the frame where:
- The dog's body is at **maximum horizontal extension**
- All four paws appear **off the ground**
- The dog's centre of mass is at its **highest point**

### Step 6 — Save result
Save the full (uncropped) frame to the source folder as:
```
frame_<N>_first_leap.png
```

Use `cv2.imwrite()` in a python3 one-liner or use `find_first_leap_frame.py --frame <N>`.

## Frame extraction helper

Use inline Python for frame extraction. Pattern:
```python
import cv2, os
cap = cv2.VideoCapture(video_path)
cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
ret, frame = cap.read()
if ret:
    # Full frame
    cv2.imwrite(out_path, frame)
    # Cropped (adjust region as needed for each video)
    cropped = frame[y1:y2, x1:x2]
    cv2.imwrite(crop_path, cropped)
cap.release()
```

Save intermediate scan frames to `/tmp/<rep_name>_scan/` to avoid cluttering the repo.

## Tips
- At 240fps, a single gallop stride spans ~15-25 frames
- The dog typically transitions: stationary → walk → trot → gallop. The "first leap" is the first gallop stride where the dog is fully airborne.
- Ignore the human handler — focus only on the dog's pose
- If the crop region doesn't capture the dog well (e.g. dog is in a different part of the frame), adjust the crop coordinates
- Process multiple folders in parallel when possible (extract all coarse scans at once, then review together)

## Output
For each folder, report:
- Folder name
- Selected frame number
- Saved file path
