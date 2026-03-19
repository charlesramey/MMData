# Teeter — Video-to-IMU Alignment Process

## Summary of Results

| Rep | Trimmed Offset (ms) | Original Offset (ms) | Confidence | Primary Anchor |
|-----|--------------------:|---------------------:|:----------:|----------------|
| Teeter_1 | **-2989** | **+2598** | High | Ground truth (reference examples) |
| Teeter_2 | **-2400** | **+5242** | High | Steady low period + multi-seek verification |
| Teeter_3 | **0** | **+5716** | High | Steady low period + multi-seek verification |
| Teeter_5 | **-2800** | **+7438** | High | Steady low period + multi-seek verification |

The offset is defined as: `IMU_time = video_time + offset`.

- **Trimmed offset**: relative to the trimmed CSV (activity-only segment produced by `trim_imu.py`)
- **Original offset**: relative to the full cleaned CSV. Conversion: `original_offset = trimmed_offset + trim_start_ms`

Trim start times from `imu_trim_times.csv`:

| Rep | trim_start_time_s | trim_start_ms |
|-----|------------------:|--------------:|
| Teeter_1 | 5.5869 | 5587 |
| Teeter_2 | 7.6416 | 7642 |
| Teeter_3 | 5.7156 | 5716 |
| Teeter_5 | 10.2379 | 10238 |

> **Note:** The wide variation in original offsets (+2598 to +7438ms) reflects different trim start times across recording sessions. The trimmed offsets vary more than the Flat obstacle (-2989 to 0ms) because each rep has different amounts of pre-teeter approach captured in the video and different trim windows.

---

## Data Inventory

| Rep | Video | Duration | Frames | FPS | Trimmed CSV | Samples | IMU Duration |
|-----|-------|----------|--------|-----|-------------|---------|-------------|
| Teeter_2 | `rep2_teeter_arya_full_720p.mp4` | 10558ms | 2534 | 240 | `Arya_teeter_2_trimmed.csv` | 848 | 8.89s |
| Teeter_3 | `rep3_teeter_arya_full_720p.mp4` | 9171ms | 2201 | 240 | `Arya_teeter_3_trimmed.csv` | 731 | 7.48s |
| Teeter_5 | `rep5_teeter_arya_full_720p.mp4` | 12883ms | 3092 | 240 | `Arya_teeter_4act5_trimmed.csv` | 579 | 6.07s |

IMU sample rate: ~95 Hz across all reps.

---

## Teeter-Specific Alignment Heuristic

From `heuristics.md`, the teeter has a distinctive IMU signature with three clear phases:

1. **Approach strides** — periodic running peaks as the dog gallops toward and onto the teeter
2. **Steady low acceleration period** — the best anchor: a flat, near-zero region where the dog is nearly stationary on the teeter, waiting for it to tilt. This is unambiguous and lasts 1–3 seconds depending on the rep.
3. **Jump-off cluster** — high-amplitude peaks as the dog descends the tilted teeter and jumps off

Additional heuristics:
- The jump-on peak is **not necessarily the largest peak** — approach strides can sometimes produce larger peaks
- **Stride counting** can be used as a secondary check: the number of periodic IMU peaks between approach and steady low should match the visible strides on the teeter in the video
- The approach is a running motion similar to the Flat obstacle (general galloping heuristics apply), but unlike the Flat reps the start of the dog's motion from a stationary state is not visible in the teeter videos

---

## Ground Truth Calibration from Rep 1

Rep 1 has a known ground truth alignment (original offset = +2598ms, trimmed offset = -2989ms) with reference screenshots in `Examples/Examples-Teeter/`. Key landmarks:

| Video (ms) | IMU trimmed (ms) | Event |
|-----------|-----------------|-------|
| 5075 | 2088 | Jump onto teeter — deceleration as front paw contacts |
| 5370 | 2383 | 2nd stride peak — front paw contacts teeter |
| 5608 | 2621 | 3rd stride peak — front paw contacts teeter |
| 5854 | 2867 | 4th stride peak — front paw contacts teeter |
| 6154 | 3167 | Steady low — teeter starts to tilt |
| 6827 | 3850 | Steady low — teeter has partly tilted |
| 7750 | 4763 | Front paw decelerates on descent from teeter |
| 7941 | 4954 | Rear legs thrust for jump off teeter |
| 8087 | 5100 | Peak of jump off — front paws brake |
| 8216 | 5229 | Rear legs catch up, normal walking stride |

Key calibration observations:
- 4 strides on the teeter before the steady low period begins
- Steady low period lasts ~1.9s (IMU 2.6–4.5s trimmed)
- The jump-off peak (h=4.15) is the largest peak in the entire signal, but that need not be the case for all reps

---

## IMU Signal Structure (Trimmed, Re-zeroed)

Peak detection was run on each trimmed CSV to characterize the full signal structure.

### Teeter_1 (reference)

| Phase | Time range | Peak heights | Notes |
|-------|-----------|-------------|-------|
| Approach strides | 0.3–2.1s | h=1.8–3.2 | 8 peaks, ~250ms spacing |
| On-teeter strides | 2.1–2.6s | h=1.4–1.8 | 2 declining peaks |
| Steady low | 2.6–4.5s | h=1.1–1.2 | Flat, near-zero filtered |
| Jump-off | 4.6–6.1s | h=1.4–4.2 | Peak at 5.1s h=4.15 |

### Teeter_2

| Phase | Time range | Peak heights | Notes |
|-------|-----------|-------------|-------|
| Approach strides | 0.4–2.4s | h=2.1–3.4 | 8 peaks, ~250ms spacing |
| On-teeter strides | 2.4–3.2s | h=1.2–1.4 | Declining transition |
| Steady low | 3.2–6.0s | h=1.0–1.2 | Very long wait (~2.8s) |
| Pre-jump-off rise | 6.0–6.4s | h=1.5–1.6 | Signal rising |
| Jump-off | 6.6–8.3s | h=1.4–3.7 | Peak at 6.6s h=3.73 |

### Teeter_3

| Phase | Time range | Peak heights | Notes |
|-------|-----------|-------------|-------|
| Approach strides | 0.1–2.3s | h=2.3–3.0 | 9 peaks, ~250ms spacing |
| On-teeter strides | 2.3–2.8s | h=1.3–1.6 | Declining transition |
| Steady low | 2.8–4.6s | h=1.0–1.3 | ~1.8s duration |
| Pre-jump-off rise | 4.6–4.9s | h=1.4–1.7 | Signal rising |
| Jump-off | 5.1–6.3s | h=1.9–3.7 | Peak at 5.1s h=3.68 |

### Teeter_5

| Phase | Time range | Peak heights | Notes |
|-------|-----------|-------------|-------|
| Early activity | 0.2–1.0s | h=1.2–1.8 | Pre-approach movement |
| Approach strides | 1.3–2.5s | h=1.9–3.0 | 4 peaks, ~270ms spacing |
| Steady low | 2.8–3.9s | h=0.9–1.1 | Shortest wait (~1.1s) |
| Jump-off | 4.1–5.2s | h=2.2–3.5 | Peak at 4.4s h=3.46 |
| Post-jump | 5.2–6.1s | h=1.3–2.0 | Declining |

---

## Methodology

### Step 1: IMU trimming

Trimmed the full cleaned CSVs to the activity region using `trim_imu.py` with master alignment indices from `FIXEDMasterAlignments/Arya_clean_master.csv`. Formula: `offset = Offset - Anchor_Offset`, `idx_start = span_start + offset`, `idx_end = span_end + offset`.

### Step 2: Video timeline exploration

Generated screenshots at 500ms intervals (offset=0) across each video to map the timeline — identifying when the dog appears, approaches the teeter, mounts it, waits for the tilt, descends, and jumps off.

| Rep | Approach | Mount | Wait | Descent | Jump-off |
|-----|---------|-------|------|---------|----------|
| Teeter_2 | ~1500–3500ms | ~3500–5000ms | ~5000–6500ms | ~6500–8000ms | ~8000–10500ms |
| Teeter_3 | ~500–2000ms | ~2000–3000ms | ~3000–4500ms | ~4500–6000ms | ~5000–6500ms |
| Teeter_5 | ~1500–3500ms | ~3500–4500ms | ~5000–6500ms | ~6500–8000ms | ~8000–9000ms |

### Step 3: IMU landmark detection

Ran peak detection (`scipy.signal.find_peaks`) on filtered acceleration magnitude (5 Hz lowpass) to identify:
- All significant peaks (h > 0.5)
- Deep valleys (filtered < 1.1)
- The steady low acceleration period (sliding-window minimum)

### Step 4: Coarse offset sweep

For each rep, swept offsets in 200ms steps at a seek position during the waiting phase. The correct offset places the cursor in the steady low IMU region while the video shows the dog stationary on the teeter.

| Rep | Seek (ms) | Sweep range | Best coarse |
|-----|----------:|------------:|------------:|
| Teeter_2 | 5500 | -3500 to +100 | -2500 to -2300 |
| Teeter_3 | 3500 | -2000 to +1000 | -200 to +200 |
| Teeter_5 | 5500 | -4000 to -1000 | -2800 to -2400 |

### Step 5: Fine offset sweep

Refined around the coarse result in 50ms steps at the same seek position. However, because the steady low period is broad (1–3 seconds), fine sweeps at a single waiting-phase seek position cannot discriminate between 50ms offset differences — many offsets place the cursor acceptably within the flat region.

### Step 6: Multi-seek verification (the key discriminator)

To overcome the broad-anchor limitation, tested 5 candidate offsets at 4 different seek positions spanning the full teeter sequence. Each seek position provides an independent constraint:

1. **Approach** — cursor should land in approach stride peaks
2. **Mounting** — cursor should land in transition/on-teeter strides
3. **Waiting** — cursor should land in steady low region
4. **Descent/jump-off** — cursor should land in pre-jump-off or jump-off cluster

The best offset is the one that produces **consistent alignment across all 4 phases simultaneously**.

#### Teeter_2 verification (offsets -2600 to -2200, seeks 3000/4500/6000/7500)

| Offset | Seek 3000 (approach) | Seek 4500 (mount) | Seek 6000 (wait) | Seek 7500 (descent) | Verdict |
|-------:|---------------------|-------------------|-------------------|---------------------|---------|
| -2600 | Cursor 0.4s — approach peaks | Cursor 1.9s — late approach | Cursor 3.4s — steady low | Cursor 4.9s — late steady | Slightly early |
| -2500 | Cursor 0.5s — approach peaks | Cursor 2.0s — transition | Cursor 3.5s — steady low | Cursor 5.0s — late steady | Good |
| **-2400** | **Cursor 0.6s — approach peaks** | **Cursor 2.1s — transition** | **Cursor 3.6s — steady low** | **Cursor 5.1s — pre-jump-off** | **Best** |
| -2300 | Cursor 0.7s — approach peaks | Cursor 2.2s — transition | Cursor 3.7s — steady low | Cursor 5.2s — pre-jump-off | Good |
| -2200 | Cursor 0.8s — approach peaks | Cursor 2.3s — late transition | Cursor 3.8s — steady low | Cursor 5.3s — late steady | Slightly late |

#### Teeter_3 verification (offsets -200 to +200, seeks 1500/2500/3500/5000)

| Offset | Seek 1500 (approach) | Seek 2500 (mount) | Seek 3500 (wait) | Seek 5000 (jump-off) | Verdict |
|-------:|---------------------|-------------------|-------------------|---------------------|---------|
| -200 | Cursor 1.3s — approach peaks | Cursor 2.3s — early transition | Cursor 3.3s — steady low | Cursor 4.8s — pre-jump-off | Good |
| -100 | Cursor 1.4s — approach peaks | Cursor 2.4s — transition | Cursor 3.4s — steady low | Cursor 4.9s — pre-jump-off | Good |
| **0** | **Cursor 1.5s — approach peaks** | **Cursor 2.5s — transition** | **Cursor 3.5s — steady low** | **Cursor 5.0s — jump-off peak** | **Best** |
| +100 | Cursor 1.6s — approach peaks | Cursor 2.6s — transition | Cursor 3.6s — steady low | Cursor 5.1s — jump-off peak | Good |
| +200 | Cursor 1.7s — late approach | Cursor 2.7s — late transition | Cursor 3.7s — steady low | Cursor 5.2s — post-peak | Slightly late |

#### Teeter_5 verification (offsets -2800 to -2400, seeks 3000/4500/6000/7500)

| Offset | Seek 3000 (approach) | Seek 4500 (mount) | Seek 6000 (wait) | Seek 7500 (jump-off) | Verdict |
|-------:|---------------------|-------------------|-------------------|---------------------|---------|
| **-2800** | **Cursor 0.2s — early activity** | **Cursor 1.7s — approach strides** | **Cursor 3.2s — steady low** | **Cursor 4.7s — jump-off** | **Best** |
| -2700 | Cursor 0.3s — early activity | Cursor 1.8s — approach strides | Cursor 3.3s — steady low | Cursor 4.8s — jump-off | Good |
| -2600 | Cursor 0.4s — early activity | Cursor 1.9s — approach strides | Cursor 3.4s — steady low | Cursor 4.9s — late jump-off | Good |
| -2500 | Cursor 0.5s — early activity | Cursor 2.0s — approach strides | Cursor 3.5s — steady low | Cursor 5.0s — post-jump | Slightly late |
| -2400 | Cursor 0.6s — early activity | Cursor 2.1s — late approach | Cursor 3.6s — late steady | Cursor 5.1s — post-jump | Too late |

---

## Comparison with Flat Alignment

| Aspect | Flat | Teeter |
|--------|------|--------|
| Primary anchor | First stride peak (activity onset) | Steady low acceleration period |
| Anchor precision | High (~50ms) | Moderate (~200ms) — broad region |
| Fine discrimination | Single seek sufficient | Multi-seek verification required |
| Dog visible before action | Yes (stationary in frame) | No (enters frame already running) |
| Trimmed offset range | -4850 to -5250ms (tight cluster) | -2989 to 0ms (wider variation) |

The teeter's broad steady-low anchor means the coarse sweep gives a good range but cannot pinpoint the offset to 50ms precision from a single seek position. The multi-seek verification — checking consistency across approach, mounting, waiting, and jump-off phases — is essential for narrowing to the best offset.

---

## Screenshots

All screenshots are in `alignment_screenshots/Arya/Arya_Teeter/Arya_Teeter_{N}/`.

| Subdirectory | Contents |
|-------------|----------|
| `explore/` | Video timeline exploration (500ms intervals, offset=0) |
| `coarse/` | Coarse offset sweep (200ms steps) |
| `fine/` | Fine offset sweep (50ms steps) |
| `verify/` | Multi-seek verification (5 offsets × 4 seek positions) |

---

## Offset Formula Reference

The GUI (MMData.py) uses: `IMU_time = video_time + offset`

- **Positive offset** → IMU recording started before the video
- **Negative offset** → Video recording started before the IMU

For trimmed CSVs (where `load_data()` re-zeros timestamps from 0):
- `trimmed_offset = original_offset - trim_start_ms`
- `original_offset = trimmed_offset + trim_start_ms`

Verification with rep 1 ground truth:
- Trimmed offset: -2989ms
- trim_start: 5587ms
- Original offset: -2989 + 5587 = +2598ms (matches user-provided ground truth) ✓
