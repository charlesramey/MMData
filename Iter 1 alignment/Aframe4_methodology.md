# Aframe_4 Alignment Methodology — Step by Step

## Data Inventory

- **Video**: `rep4_aframe_arya_full_720p.mp4` — 5304ms long, 240fps, 1273 frames
- **IMU**: `Arya_aframe_4_cleaned.csv` — 1296 samples over 11.68 seconds, ~111 Hz sample rate
- **Key observation**: The IMU recording (11.68s) is more than double the video length (5.30s). This is the largest time mismatch of the three reps, suggesting the largest offset.

## Step 1: Exploring the video timeline

Generated screenshots at evenly-spaced intervals across the whole video with offset=0. Screenshots saved to `alignment_screenshots/Aframe_4_explore/`.

### What the video shows

| Video time | What's visible |
|------------|----------------|
| **500ms** | Empty scene — aframe obstacle in a gym, no dog, no handler. Same camera angle. |
| **1500ms** | Still empty — no movement. |
| **2500ms** | **First sign of action** — handler crouching/visible on the far left edge, dog may be entering frame. |
| **3500ms** | **Dog galloping** — dog clearly running toward the aframe, handler alongside. Similar to Aframe_2 and 3 at this phase. |
| **4500ms** | **Dog on the aframe** — dog appears to be on the aframe slope or near the apex. Handler running behind. |
| **5000ms** | **Past the aframe** — dog on the downslope or departing. Very near end of video (5304ms total). |

**Key conclusion**: Activity starts around **2500-3000ms** in the video. The aframe interaction window is roughly **3500-5000ms**. The video is the shortest of the three reps.

### What the IMU shows

The IMU signal for Aframe_4 has some unusual features:
- **0.076s**: A spurious blip right at the start (sensor handling/startup artifact)
- **0-6.5s**: Long quiet period — much longer than the other reps
- **~6.8-8.1s**: Activity builds — approach strides leading to the biggest peak
- **~8.1-8.6s**: The main event — the biggest peaks (jump-on at 8.1s)
- **~8.6-9.4s**: Gap — apex traverse
- **~9.4-11.0s**: Jump-off cluster and post-aframe running

### Key insight

Video activity starts ~3.0s, IMU activity starts ~6.8s (ignoring the spurious 0.075s onset). This suggested a **positive offset of roughly 3.5-4.5s** — the largest of the three reps.

**Note on activity onset**: The programmatic onset detection reported 0.075s because of the startup blip, which was misleading. The *real* activity onset was around 6.8s, identified by examining the wide-window IMU plot.

## Step 2: IMU signal exploration (wide-window view)

Generated a wide-window IMU plot (10s window, +4000ms offset). Screenshot saved to `alignment_screenshots/Aframe_4_wide_imu.png`.

The signal is distinctive: a very long quiet period (0-6.5s), then a concentrated burst of activity (6.8-11.0s). The main event cluster is pushed late in the recording compared to the other reps.

## Step 3: Programmatic activity onset detection

```
IMU activity onset (filtered accel > 0.2): 0.075s  ← misleading (startup artifact)
Real activity onset (visual inspection): ~6.8s
Peak filtered accel: 2.99 at t=8.101s
```

Offset estimate using the real onset:
```
estimated_offset ≈ real_IMU_onset - video_onset ≈ 6.8s - 3.0s ≈ 3.8s
```

Search range: **+2500ms to +5500ms**, centered on ~4000ms.

## Step 4: Coarse offset sweep

Swept offsets from +2500ms to +5500ms in 500ms steps, all at seek=3500ms (dog galloping toward aframe). Screenshots saved to `alignment_screenshots/Aframe_4_coarse/`.

| Offset | Cursor at IMU time | Where cursor lands |
|--------|--------------------|--------------------|
| **+2500ms** | 6.0s | Before any real activity — quiet zone |
| **+3000ms** | 6.5s | At the very beginning of activity |
| **+3500ms** | 7.0s | In the early approach strides |
| **+4000ms** | 7.5s | Deeper into approach strides |
| **+4500ms** | 8.0s | Near the biggest peak (jump-on) |
| **+5000ms** | 8.5s | Past the biggest peak, in settling zone |
| **+5500ms** | 9.0s | In the gap/apex zone, past the main event |

### Reasoning

At 3500ms, the dog is mid-gallop approaching the aframe. The cursor should be in the approach stride zone.

- **+2500 to +3000**: Too low — cursor is in the quiet zone
- **+4500 to +5500**: Too high — cursor is at/past the jump-on peak
- **+3500 to +4500**: Plausible — cursor is among approach strides

Narrowed candidates to **+3500 to +4500**.

## Step 5: Programmatic peak detection

Used `imu_peak_detection.py`. The structure for Aframe_4:

```
SPURIOUS BLIP:
  0.076s  h=0.41   (startup artifact, ignore)

APPROACH STRIDES (6.81s - 7.87s):
  6.807s  h=0.32   (first faint activity)
  7.057s  h=0.48   (pre-approach)
  7.364s  h=0.93   (stride 1)
  7.617s  h=1.60   (stride 2)
  7.868s  h=1.61   (stride 3)
  Inter-peak spacing (strides 1-3): 253ms, 251ms (~4.0 Hz = galloping) ✓

AFRAME INTERACTION (8.10s - 8.59s):
  8.101s  h=2.99   ← BIGGEST PEAK — this is the jump-on
  8.340s  h=2.41   (on-aframe impact)
  8.591s  h=0.85   (settling)

GAP (8.59s - 9.40s):
  ~810ms of low activity — dog traversing the apex

JUMP-OFF CLUSTER (9.40s - 9.88s):
  9.401s  h=0.87
  9.666s  h=2.35
  9.883s  h=2.74   ← jump-off peak

POST-AFRAME (10.10s+):
  10.103s  h=1.47
  10.346s  h=1.29
  10.630s  h=1.70
  10.944s  h=1.70
  11.216s  h=0.87
```

### Key observations

- Like Aframe_2, the **biggest peak** (8.101s, h=2.99) is the **jump-on**. Very similar magnitude to Aframe_2's 2.97.
- The approach stride spacing (~252ms, ~4.0 Hz) matches galloping, consistent across all three reps.
- The apex gap (~810ms) is similar to the other reps (~700-800ms).
- The spurious blip at 0.076s was easily identified as an artifact — it's isolated and doesn't fit the stride pattern.

## Step 6: Reverse mapping from IMU peaks

Used the biggest peak at 8.101s as the primary anchor.

For offset +4200ms: `video_time = 8101 - 4200 = 3901ms`

At video 3901ms, the dog should be at the aframe base in a jumping posture. This was checked — the dog is at the base, body low, about to thrust upward. Cross-validation:

- At offset +3500: `video_time = 8101 - 3500 = 4601ms` — dog would be past the apex, way too late
- At offset +4500: `video_time = 8101 - 4500 = 3601ms` — dog would still be mid-gallop, too early
- At offset +4000: `video_time = 8101 - 4000 = 4101ms` — dog would be on the slope already, slightly too late

**+4200ms was the best fit** — the jump-on peak mapped to the correct visual phase.

## Step 7: Full multi-landmark verification at +4200ms

Verified all landmarks at offset +4200ms (`video_time = imu_time - 4200ms`). Screenshots saved to `alignment_screenshots/Aframe_4_verify/`.

| IMU Landmark | IMU time | Video time | What's in the frame | Match? |
|---|---|---|---|---|
| **Approach stride 1** (h=0.93) | 7.364s | 3164ms | Handler and dog visible, dog approaching from distance | Yes |
| **Approach stride 2** (h=1.60) | 7.617s | 3417ms | Dog galloping, closer to aframe | Yes |
| **Approach stride 3** (h=1.61) | 7.868s | 3668ms | Dog in full gallop, nearly at aframe base | Yes |
| **Jump-on peak** (h=2.99) | 8.101s | 3901ms | Dog at aframe base, body low, thrusting upward | **Yes — strong match** |
| **On-aframe impact** (h=2.41) | 8.340s | 4140ms | Dog on the aframe upslope, climbing | Yes |
| **Apex zone** (dip) | ~9.000s | 4800ms | Dog near the apex, handler behind, low IMU activity | Yes |

All six landmarks matched. The progression was consistent and convincing.

### Note on jump-off and video length limitation

The jump-off peak at 9.883s maps to video time 5683ms — **past the end of the 5304ms video**. This means the jump-off cannot be verified at all in the video. The video ends while the dog is still traversing the apex or beginning the descent. This is the most significant limitation for this rep and is why confidence is slightly lower than the other two.

---

## Final Result

| Parameter | Value |
|-----------|-------|
| **Offset** | **+4200ms** |
| **Confidence** | **Medium-High** |
| **Primary anchor** | Jump-on peak at IMU 8.101s ↔ video 3901ms (frame 936) |
| **Definition** | `IMU_time = video_time + 4200ms` (IMU started 4.2s before video) |

### Why Medium-High (not High) confidence

- All 6 verifiable landmarks matched perfectly
- However, the jump-off peak maps to 5683ms which is **past the video end** (5304ms), so the full aframe sequence cannot be cross-verified
- The reverse-mapping at +4200ms was the best fit, but +4000ms and +4400ms couldn't be fully ruled out at the sub-200ms level without the jump-off anchor

### Detailed anchor points (frame indices at 240fps)

| Landmark | IMU Time (ms) | Video Time (ms) | Frame | Note |
|----------|---------------|-----------------|-------|------|
| Approach stride 1 | 7364 | 3164 | 759 | |
| Approach stride 2 | 7617 | 3417 | 820 | |
| Approach stride 3 | 7868 | 3668 | 880 | |
| **Jump-on peak** | **8101** | **3901** | **936** | Primary anchor |
| On-aframe impact | 8340 | 4140 | 994 | |
| Apex zone | 9000 | 4800 | 1152 | |
| Jump-off peak | 9883 | 5683 | — | **Past video end (5304ms)** |
