# Aframe_2 Alignment Methodology — Step by Step

## Data Inventory

- **Video**: `rep2_aframe_arya_full_720p.mp4` — 6092ms long, 240fps, 1462 frames
- **IMU**: `Arya_aframe_2_cleaned.csv` — 1164 samples over 10.33 seconds, ~113 Hz sample rate
- **Key observation**: The IMU recording (10.33s) is significantly longer than the video (6.09s). This immediately told us that the two didn't start at the same time — there's some offset between them.

## Step 1: Exploring the video timeline

Generated screenshots at evenly-spaced intervals (every 500ms) across the whole video with offset=0, just to map out *what happens in the video*. Screenshots saved to `alignment_screenshots/Aframe_2_explore/`.

### What the video shows

| Video time | What's visible |
|------------|----------------|
| **500ms** | Empty scene — just the aframe obstacle in a gym, no dog, no handler. The camera is low, looking across a green turf floor at the aframe. |
| **1500ms** | Still empty — same static shot, no movement. |
| **2500ms** | Still empty — nothing has changed. The dog hasn't appeared yet. |
| **3500ms** | **First sign of action** — on the far left edge, you can just barely see a person (handler) starting to appear. The dog is either out of frame or just entering. |
| **4500ms** | **Full action** — the dog is clearly at the aframe, appears to be on or near the base of the aframe, with the handler running alongside. This is clearly the approach/jump-on phase. |
| **5500ms** | **Past the aframe** — the dog appears to be on the downslope or past the aframe. The handler is visible to the left. |

**Key conclusion from the video**: The interesting action (dog approaching and interacting with the aframe) happens in a narrow window from roughly **3500-5500ms**. The first ~3 seconds of video are dead time with nothing happening.

### What the IMU shows (visible on the right side of each screenshot)

Even at offset=0 (which we knew was wrong), the IMU signal shape is visible. The cursor moves through the IMU timeline as the video progresses:

- **0-5s IMU time**: Mostly flat/quiet — the dog isn't doing much
- **~6-7s IMU time**: A cluster of increasing activity (rhythmic peaks from approach gallop)
- **~7-8s IMU time**: The biggest spikes — this is the aframe interaction
- **~8-10s IMU time**: More activity (post-aframe running, then quieter)

### Key insight from Step 1

The video has activity starting around **3.5-4.0s**, while the IMU has its main activity cluster around **6-8s**. This immediately suggested a **positive offset of roughly 2-4 seconds** — the IMU recording started 2-4 seconds before the video recording. The exact value was what the rest of the methodology was about nailing down.

## Step 2: IMU signal exploration (wide-window view)

Generated a wide-window IMU plot (10s window, arbitrary +2000ms offset) to see the full signal shape across the entire recording. Screenshot saved to `alignment_screenshots/Aframe_2_wide_imu.png`.

### What the IMU signal shows

- **0-5.5s**: Essentially quiet. The filtered signals are near zero. There's a brief blip around 0.5s (maybe the sensor being handled/started) but nothing sustained.
- **~5.5-6.5s**: Activity begins — the signal rises with rhythmic bumps. These are the **approach running strides** (the dog galloping toward the aframe).
- **~6.5-8.5s**: The **main event** — the signal has its highest peaks here. There's a very tall spike (around 7s) which would be the jump-on, then some activity through 8.5s.
- **~8.5-10.3s**: Another cluster of peaks — likely **post-aframe running** and possibly the jump-off.

## Step 3: Programmatic activity onset detection

Rather than eyeballing when activity starts, computed it numerically using `imu_activity_onset.py` (filtered accel magnitude > 0.2 threshold):

```
IMU activity onset (filtered accel > 0.2): 5.933s
Peak filtered accel: 2.97 at t=7.076s
```

Combined with the video observation that the dog first appears around 3.5-4.0s, this gave an initial offset estimate:

```
estimated_offset ≈ IMU_onset - video_onset ≈ 5.9s - 3.8s ≈ 2.1s
```

This narrowed the search range to roughly **+500ms to +3500ms**, centered on ~2000ms. The coarse sweep in the next step would explore this range systematically.

## Step 4: Coarse offset sweep

Swept offsets from +500ms to +3500ms in 500ms steps, all at seek=4200ms (where the dog is galloping toward the aframe, not yet at the base). Screenshots saved to `alignment_screenshots/Aframe_2_coarse/`.

The red cursor on the IMU plot shifts rightward as the offset increases:

| Offset | Cursor at IMU time | Where cursor lands on IMU signal |
|--------|-------------------|----------------------------------|
| **+500ms** | 4.7s | Well before any activity — flat/quiet zone |
| **+1000ms** | 5.2s | Still in the quiet zone, just before activity begins |
| **+1500ms** | 5.7s | Right at the edge of where activity starts — the first small bumps |
| **+2000ms** | 6.2s | In the rising approach strides — cursor is among the rhythmic gallop peaks |
| **+2500ms** | 6.7s | Deeper into the approach strides, near the transition to the big peaks |
| **+3000ms** | 7.2s | On or just past the biggest peak (the jump-on spike) |
| **+3500ms** | 7.7s | Past the big peak, in the post-jump-on zone |

### Reasoning

The video at 4200ms shows the dog mid-gallop, approaching the aframe but **not yet jumping on**. So the IMU cursor should be landing on **approach stride peaks**, not on the biggest peak or in the quiet zone.

- **+500 to +1000**: Too low — cursor is in the quiet zone but the dog is clearly running
- **+3000 to +3500**: Too high — cursor is at/past the jump-on peak but the dog hasn't reached the aframe yet
- **+1500 to +2500**: Plausible range — cursor is among the approach stride peaks

### The problem with the coarse sweep

This narrowed the candidate range from +500–3500 down to roughly **+1500 to +2500**, but couldn't pin it down more precisely. The thumbnails were small, and the cursor position relative to specific peaks was hard to read at this resolution. This limitation led to finer sweeps and eventually the reverse-mapping breakthrough.

## Step 5: Fine offset sweep

Narrowed to the +1000–3000 range and tested at 250ms steps, at seek=4900ms (further into the aframe interaction — the dog is on the aframe slope at this point). Screenshots saved to `alignment_screenshots/Aframe_2_fine/`.

| Offset | Cursor at IMU time | Where cursor lands |
|--------|--------------------|--------------------|
| **+1000ms** | 5.9s | Just at the start of approach strides — too early for "on the aframe" |
| **+1500ms** | 6.4s | In the middle of approach strides — still looks like galloping not aframe contact |
| **+2000ms** | 6.9s | Near the top of the approach strides, just before the biggest peak |
| **+2250ms** | 7.15s | Very close to the biggest peak |
| **+2500ms** | 7.4s | Just past the biggest peak — in the post-jump-on zone (on the aframe) |
| **+3000ms** | 7.9s | Further past, in the dip/apex zone |

### Reasoning

The dog at 4900ms is clearly past the jump-on moment — she's on the aframe slope, not mid-leap. So the cursor should be **past the biggest peak** (the jump-on), somewhere in the settling/on-aframe zone. That pointed to **+2500 or higher**. But the cursor positions were hard to read precisely against the small IMU plot — couldn't tell if the cursor was before, on, or after a specific peak.

## Step 6: Multi-point verification

To get more constraints, checked multiple video moments simultaneously against different offsets. Three video moments (4400ms, 4900ms, 5400ms) crossed with four offsets (+1500, +1750, +2000, +2250). Screenshots saved to `alignment_screenshots/Aframe_2_verify/`.

**At seek=4400ms** (dog approaching the aframe base, about to jump on):
- The cursor should land on the **rising approach strides**, just before the biggest peak
- At +1500: cursor ~5.9s — barely into the active zone, feels too early
- At +2000: cursor ~6.4s — in the approach strides, plausible
- At +2250: cursor ~6.65s — deeper into approach, also plausible

**At seek=4900ms** (dog on the aframe slope, post-jump-on):
- The cursor should land **just past** the biggest peak
- At +1500: cursor ~6.4s — in approach strides, too early for on-aframe
- At +2000: cursor ~6.9s — near the big peak, borderline
- At +2250: cursor ~7.15s — on/near the biggest peak

**At seek=5400ms** (dog near apex or on downslope):
- The cursor should land in the **dip zone** between the two big peaks (the near-zero zone when the dog is airborne over the apex)
- At +1500: cursor ~6.9s — still in the approach/peak zone, too early
- At +2250: cursor ~7.65s — in the post-peak settling zone

### Verdict from multi-point verification

The offsets +2000 to +2250 looked most plausible — they placed all three video moments in roughly the right IMU neighborhood. But still couldn't be precise. The fundamental problem was trying to **read where the cursor falls relative to specific peaks on a small plot**, and the resolution wasn't enough to distinguish between offsets 250ms apart.

**This is exactly what motivated the next step** — instead of staring at cursor positions on small plots, flip the problem: start from known IMU peak times and compute what video frame they should correspond to.

## Step 7: Programmatic peak detection

Used `scipy.signal.find_peaks` (saved as `imu_peak_detection.py`) to programmatically identify every significant peak in the filtered IMU signal at two thresholds: height > 0.3 for all activity, height > 1.5 for big events.

### Peak structure

The peaks fall into clear clusters:

```
APPROACH STRIDES (5.98s - 6.68s):
  5.984s  h=0.44   (first faint stride)
  6.185s  h=0.99   (stride 1)
  6.427s  h=1.52   (stride 2)
  6.679s  h=1.36   (stride 3)
  Inter-peak spacing: 200-251ms (~4.3 Hz = galloping dog) ✓

AFRAME INTERACTION (7.08s - 7.58s):
  7.076s  h=2.97   ← BIGGEST PEAK — this is the jump-on
  7.320s  h=1.75   (on-aframe impact / climbing)
  7.582s  h=0.61   (settling on aframe)

GAP (7.58s - 8.28s):
  ~700ms of low activity — dog traversing the apex (near-weightless)

JUMP-OFF CLUSTER (8.28s - 8.95s):
  8.284s  h=0.50
  8.525s  h=1.86
  8.769s  h=2.26   ← jump-off peak

POST-AFRAME (9.25s+):
  9.251s  h=2.66   (landing/running away)
  9.491s  h=1.81
```

### Key observations

- The **biggest peak at 7.076s** (h=2.97) had to be the jump-on moment — the most violent acceleration event in the aframe sequence (rear legs thrusting the dog up onto the obstacle).
- The approach stride spacing of ~231ms (~4.3 Hz) was consistent with a galloping border collie, confirming these really were running strides and not noise.
- The "peak → gap → peak" structure (7.08s → 7.58–8.28s gap → 8.53s) matches the expected aframe signature: jump-on, traverse apex (near-weightless), jump-off.

The question was now: **what video time does 7.076s correspond to?** That depended on the offset: `video_time = 7076ms - offset`. The reverse mapping step would answer this directly.

## Step 8: Reverse mapping from IMU peaks (the breakthrough)

Instead of "pick an offset, look at cursor on plot," flipped the problem: **start from the biggest IMU peak (7.076s), compute the implied video time for several candidate offsets, and check whether the dog's pose matches**.

For each candidate offset: `video_time = 7076 - offset`. Screenshots saved to `alignment_screenshots/Aframe_2_peakmatch/`, named as `peak7076_offset{X}_vid{Y}.png`.

| Offset | Video time | What the dog is actually doing |
|--------|-----------|-------------------------------|
| **+3500ms** | 3576ms | Dog is barely in frame, far from the aframe — way too early. **No match.** |
| **+3000ms** | 4076ms | Dog is galloping toward the aframe, still several strides away. Not jumping yet. **No match.** |
| **+2500ms** | 4576ms | **Dog is right at the base of the aframe, body low, appearing to thrust upward.** The handler is right alongside. This is exactly what "jump-on peak acceleration" should look like. **Strong match.** |
| **+2000ms** | 5076ms | Dog is already well up on the aframe slope, past the base. Too late for the jump-on moment. **No match.** |
| **+1500ms** | 5576ms | Dog is near or past the apex. Way too late for jump-on. **No match.** |

### Conclusion

**Offset +2500ms was the clear winner.** Only at that offset did the biggest IMU peak line up with the dog at the aframe base in a jumping posture. The other offsets were off by one or more phases of the aframe sequence.

This was the breakthrough — by anchoring on a precisely known IMU time and checking the video content at the implied frame, all the ambiguity from the cursor-reading approach was eliminated.

## Step 9: Full multi-landmark verification at +2500ms

With the offset locked to +2500ms, verified every identified IMU landmark by computing its implied video time (`video_time = imu_time - 2500ms`) and checking the frame. Screenshots saved to `alignment_screenshots/Aframe_2_verify2500/`.

| IMU Landmark | IMU time | Video time | What's in the frame | Match? |
|---|---|---|---|---|
| **Approach stride 1** (h=0.99) | 6.185s | 3685ms | Handler barely visible on far left, dog just entering frame — early approach | Yes — first sign of running activity |
| **Approach stride 2** (h=1.52) | 6.427s | 3927ms | Handler and dog more visible, dog galloping toward aframe | Yes — mid-gallop stride |
| **Approach stride 3** (h=1.36) | 6.679s | 4179ms | Dog clearly galloping, closer to aframe, legs extended in running stride | Yes — late approach stride |
| **Jump-on peak** (h=2.97) | 7.076s | 4576ms | Dog at the aframe base, body low, thrusting upward onto the obstacle | **Yes — perfect match for peak acceleration** |
| **On-aframe impact** (h=1.75) | 7.320s | 4820ms | Dog on the aframe upslope, handler lunging alongside | Yes — post-jump climbing |
| **Apex zone** (dip) | ~7.900s | 5400ms | Dog near/past the apex, handler behind | Yes — low IMU activity matches near-weightless apex traverse |

Every single landmark matched. The approach strides showed progressive approach, the biggest peak nailed the jump-on moment, and the apex zone showed the expected low-activity dip. Six independent checks, all consistent with +2500ms.

### Note on jump-off

The jump-off peak at IMU 8.525s maps to video time 6025ms — only 67ms before the end of the 6092ms video. So the jump-off was barely within the video and couldn't be fully verified visually. All 6 landmarks within the video matched perfectly regardless.

---

## Final Result

| Parameter | Value |
|-----------|-------|
| **Offset** | **+2500ms** |
| **Confidence** | **High** |
| **Primary anchor** | Jump-on peak at IMU 7.076s ↔ video 4576ms (frame 1098) |
| **Definition** | `IMU_time = video_time + 2500ms` (IMU started 2.5s before video) |

### Detailed anchor points (frame indices at 240fps)

| Landmark | IMU Time (ms) | Video Time (ms) | Frame | Note |
|----------|---------------|-----------------|-------|------|
| Approach stride 1 | 6185 | 3685 | 884 | |
| Approach stride 2 | 6427 | 3927 | 942 | |
| Approach stride 3 | 6679 | 4179 | 1003 | |
| **Jump-on peak** | **7076** | **4576** | **1098** | Primary anchor |
| On-aframe impact | 7320 | 4820 | 1157 | |
| Apex zone | 7900 | 5400 | 1296 | |
| Jump-off peak | 8525 | 6025 | 1446 | Near end of video |
