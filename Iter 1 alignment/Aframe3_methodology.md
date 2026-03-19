# Aframe_3 Alignment Methodology — Step by Step

## Data Inventory

- **Video**: `rep3_aframe_arya_full_720p.mp4` — 5708ms long, 240fps, 1370 frames
- **IMU**: `Arya_aframe_3_cleaned.csv` — 1051 samples over 9.13 seconds, ~115 Hz sample rate
- **Key observation**: The IMU recording (9.13s) is longer than the video (5.71s), but the gap is smaller than Aframe_2's (3.4s vs 4.2s). This suggested a smaller offset.

## Step 1: Exploring the video timeline

Generated screenshots at evenly-spaced intervals (every ~1000ms) across the whole video with offset=0. Screenshots saved to `alignment_screenshots/Aframe_3_explore/`.

### What the video shows

| Video time | What's visible |
|------------|----------------|
| **500ms** | Empty scene — aframe obstacle in a gym, no dog, no handler. Same camera angle as Aframe_2. |
| **1500ms** | Still empty — no movement. |
| **2500ms** | **First sign of action** — handler visible on the far left, appearing to move toward the aframe. Dog may be just entering frame. Earlier activity onset than Aframe_2. |
| **3500ms** | **Dog galloping** — the dog is clearly running toward the aframe, handler alongside. Mid-approach. |
| **4500ms** | **Dog on/past the aframe** — the dog appears to be on the aframe slope or past it, handler behind. |
| **5200ms** | **Past the aframe** — dog on the downslope or departing. Near end of video. |

**Key conclusion**: Activity starts around **2500ms** in the video — about 1 second earlier than Aframe_2. The aframe interaction window is roughly **3500-5000ms**.

### What the IMU shows

- **0-3.5s**: Mostly quiet with minor fluctuations
- **~3.5-5.5s**: Activity begins — rhythmic approach strides, building to large peaks around 5.0s
- **~5.5-7.0s**: The main event — biggest peaks here (jump-on around 5.0s, then gap, then jump-off cluster around 6.5-7.0s)
- **~7.0-9.1s**: Post-aframe activity, tapering off

### Key insight

Video activity starts ~2.5s, IMU activity starts ~3.8s. This suggested a **positive offset of roughly 1.0-1.5s** — much smaller than Aframe_2's ~2.5s offset.

## Step 2: IMU signal exploration (wide-window view)

Generated a wide-window IMU plot (10s window). Screenshot saved to `alignment_screenshots/Aframe_3_wide_imu.png`.

The IMU signal for Aframe_3 is more compact than Aframe_2 — the entire active period fits within ~3.5s to ~8.5s, with the main event cluster around 5-7s.

## Step 3: Programmatic activity onset detection

```
IMU activity onset (filtered accel > 0.2): 3.793s
Peak filtered accel: 2.61 at t=6.816s
```

Offset estimate:
```
estimated_offset ≈ IMU_onset - video_onset ≈ 3.8s - 2.5s ≈ 1.3s
```

Search range: **-1000ms to +2000ms**, centered on ~1200ms.

## Step 4: Coarse offset sweep

Swept offsets from -1000ms to +2000ms in 500ms steps, all at seek=3500ms (dog galloping toward aframe). Screenshots saved to `alignment_screenshots/Aframe_3_coarse/`.

| Offset | Cursor at IMU time | Where cursor lands |
|--------|--------------------|--------------------|
| **-1000ms** | 2.5s | Well before any activity — quiet zone |
| **-500ms** | 3.0s | Still quiet |
| **0ms** | 3.5s | Just at the edge of activity onset |
| **+500ms** | 4.0s | In the early approach strides |
| **+1000ms** | 4.5s | In the middle of approach strides — rhythmic peaks |
| **+1500ms** | 5.0s | Near the first big peak (jump-on region) |
| **+2000ms** | 5.5s | Past the first big peak cluster |

### Reasoning

At 3500ms, the dog is mid-gallop approaching the aframe. The cursor should be in the **approach stride zone**, not in the quiet zone or at the jump-on peak.

- **-1000 to 0**: Too low — cursor is in quiet zone or barely at onset
- **+1500 to +2000**: Too high — cursor is at/past the jump-on peaks
- **+500 to +1000**: Plausible — cursor lands among approach strides

This narrowed candidates to **+500 to +1500**, but as with Aframe_2, the thumbnails were too small to precisely distinguish between offsets.

## Step 5: Programmatic peak detection

Used `imu_peak_detection.py` to identify all peaks. The structure for Aframe_3:

```
APPROACH STRIDES (4.10s - 4.58s):
  4.098s  h=1.06   (stride 1)
  4.343s  h=1.43   (stride 2)
  4.581s  h=1.34   (stride 3)
  Inter-peak spacing: 244ms, 239ms (~4.1 Hz = galloping dog) ✓

JUMP-ON CLUSTER (4.99s - 5.47s):
  4.991s  h=2.23   ← JUMP-ON PEAK
  5.199s  h=1.87   (on-aframe impact)
  5.474s  h=0.52   (settling)

GAP (5.47s - 6.29s):
  ~800ms of low activity — dog traversing the apex

JUMP-OFF CLUSTER (6.29s - 6.82s):
  6.291s  h=0.38
  6.552s  h=1.72
  6.816s  h=2.61   ← BIGGEST PEAK (jump-off)

POST-AFRAME (7.06s+):
  7.060s  h=0.84
  7.309s  h=1.23
  7.614s  h=1.37
```

### Key observations

- Unlike Aframe_2, the **biggest peak** (6.816s, h=2.61) is the **jump-off**, not the jump-on. The jump-on peak (4.991s, h=2.23) is the second-biggest.
- The approach stride spacing (~241ms, ~4.1 Hz) is consistent with galloping, similar to Aframe_2.
- The gap between jump-on settling (5.47s) and jump-off buildup (6.29s) is ~800ms — similar to Aframe_2's ~700ms.

## Step 6: Reverse mapping from IMU peaks

Applied the same breakthrough technique from Aframe_2. Used the jump-on peak at 4.991s as the primary anchor (since this is the most visually distinctive moment — dog at the base thrusting upward).

For offset +1200ms: `video_time = 4991 - 1200 = 3791ms`

At video 3791ms, the dog should be at the aframe base in a jumping posture. This was checked and confirmed — the dog is clearly at the base, body low, thrusting upward. The offset was also cross-validated:

- At offset +1000: `video_time = 4991 - 1000 = 3991ms` — dog would already be on the slope, too late for jump-on
- At offset +1500: `video_time = 4991 - 1500 = 3491ms` — dog would still be mid-gallop, too early for jump-on

**+1200ms was the clear winner** — only offset where the jump-on peak mapped to a frame showing the dog at the aframe base.

## Step 7: Full multi-landmark verification at +1200ms

Verified all landmarks at offset +1200ms (`video_time = imu_time - 1200ms`). Screenshots saved to `alignment_screenshots/Aframe_3_verify/`.

| IMU Landmark | IMU time | Video time | What's in the frame | Match? |
|---|---|---|---|---|
| **Approach stride 1** (h=1.06) | 4.098s | 2898ms | Handler visible on left, dog just entering frame — early approach | Yes |
| **Approach stride 2** (h=1.43) | 4.343s | 3143ms | Dog and handler more visible, dog galloping | Yes |
| **Approach stride 3** (h=1.34) | 4.581s | 3381ms | Dog clearly running, closer to aframe | Yes |
| **Jump-on peak** (h=2.23) | 4.991s | 3791ms | Dog at aframe base, body low, thrusting upward | **Yes — strong match** |
| **On-aframe impact** (h=1.87) | 5.199s | 3999ms | Dog on the aframe upslope, climbing | Yes |
| **Apex zone** (dip) | ~5.800s | 4600ms | Dog near/at the apex, low IMU activity | Yes |

All six landmarks matched. The progression from early approach through jump-on to apex was consistent and convincing.

### Note on jump-off

The jump-off peak at 6.816s maps to video time 5616ms — within the 5708ms video but near the end (92ms margin). The jump-off could be partially verified.

---

## Final Result

| Parameter | Value |
|-----------|-------|
| **Offset** | **+1200ms** |
| **Confidence** | **High** |
| **Primary anchor** | Jump-on peak at IMU 4.991s ↔ video 3791ms (frame 910) |
| **Definition** | `IMU_time = video_time + 1200ms` (IMU started 1.2s before video) |

### Detailed anchor points (frame indices at 240fps)

| Landmark | IMU Time (ms) | Video Time (ms) | Frame | Note |
|----------|---------------|-----------------|-------|------|
| Approach stride 1 | 4098 | 2898 | 696 | |
| Approach stride 2 | 4343 | 3143 | 754 | |
| Approach stride 3 | 4581 | 3381 | 811 | |
| **Jump-on peak** | **4991** | **3791** | **910** | Primary anchor |
| On-aframe impact | 5199 | 3999 | 960 | |
| Apex zone | 5800 | 4600 | 1104 | |
| Jump-off peak | 6816 | 5616 | 1348 | Near end of video |
