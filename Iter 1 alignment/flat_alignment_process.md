# Flat Running — Video-to-IMU Alignment Process

## Summary of Results

| Rep | Trimmed Offset (ms) | Original Offset (ms) | Confidence | Primary Anchor |
|-----|--------------------:|---------------------:|:----------:|----------------|
| Flat_1 | **-4800** | **+25852** | High | Ground truth (reference examples) |
| Flat_2 | **-4850** | **+8315** | High | First stride peak aligned to first IMU running peak |
| Flat_3 | **-5050** | **+6835** | High | First stride peak aligned to first IMU running peak |
| Flat_4 | **-5250** | **+6712** | High | First stride peak aligned to first IMU running peak |
| Flat_5 | **-2600** | **+3891** | High | First stride peak aligned to first IMU running peak (Bout 2) |
| Flat_6 | **-5150** | **+18** | High | First stride peak aligned to first IMU running peak |

The offset is defined as: `IMU_time = video_time + offset`.

- **Trimmed offset**: relative to the trimmed CSV (activity-only segment produced by `trim_imu.py`)
- **Original offset**: relative to the full cleaned CSV. Conversion: `original_offset = trimmed_offset + trim_start_ms`

Trim start times from `imu_trim_times.csv`:

| Rep | trim_start_time_s | trim_start_ms |
|-----|------------------:|--------------:|
| Flat_1 | 30.6521 | 30652 |
| Flat_2 | 13.1653 | 13165 |
| Flat_3 | 11.8848 | 11885 |
| Flat_4 | 11.9621 | 11962 |
| Flat_5 | 6.4914 | 6491 |
| Flat_6 | 5.1675 | 5168 |

> **Note:** The wide variation in original offsets (+18 to +25852ms) is due to different trim start times across reps (different recording sessions). The trimmed offsets (-4850 to -5250 for reps 2/3/4/6) are tightly clustered around the rep 1 ground truth of -4800ms, providing cross-validation.

> **Note on Flat_5:** This rep has a two-bout IMU structure. Bout 1 (~0.3–2.8s trimmed time) corresponds to irrelevant initial movement. Bout 2 (~3.5–6.0s) is the actual flat run. The trimmed offset of -2600ms is consequently less negative than other reps because the dog onset in the video is later (~6100ms) and the relevant IMU activity starts later in the trimmed window.

---

## Data Inventory

| Rep | Video | Duration | Frames | FPS | Trimmed CSV | Samples | IMU Duration |
|-----|-------|----------|--------|-----|-------------|---------|-------------|
| Flat_2 | `rep2_flat_Arya_full_720p.mp4` | 9175ms | 2202 | 240 | `Arya_flat_2_trimmed.csv` | 476 | 4.99s |
| Flat_3 | `rep3_flat_Arya_full_720p.mp4` | 8825ms | 2118 | 240 | `Arya_flat_3_trimmed.csv` | 428 | 4.49s |
| Flat_4 | `rep4_flat_Arya_full_720p.mp4` | 8975ms | 2154 | 240 | `Arya_flat_4_trimmed.csv` | 639 | 6.71s |
| Flat_5 | `rep5_flat_Arya_full_720p.mp4` | 9233ms | 2216 | 240 | `Arya_flat_5_trimmed.csv` | 570 | 6.01s |
| Flat_6 | `rep6_flat_Arya_full_720p.mp4` | 9512ms | 2283 | 240 | `Arya_flat_6_trimmed.csv` | 477 | 5.00s |

IMU sample rate: ~95 Hz across all reps.

---

## Flat-Specific Alignment Heuristic

Unlike the Aframe obstacle (where the apex dip provides a distinct structural anchor), Flat running alignment relies on the **activity onset heuristic** from `heuristics.md`:

> Since the dog is stationary before starting to run, and the stationary dog is visible in the video frame, we align the start of feet movement to the start of the first rising edge of periodic running-like motion in the IMU reading.

The key anchor is the **first stride peak**: the first clear peak in the periodic running pattern in the IMU, aligned to the video frame showing the dog completing its first full galloping stride (front paw contacting the ground after the first thrust).

### Critical distinction: dog onset vs handler onset

The handler typically begins moving 1–3 seconds before the dog in these recordings. Activity onset must reference the **dog's first movement**, not the handler's. This was the primary correction applied across iterations (see [Corrections Applied](#corrections-applied)).

### Two-camera view

The Flat recordings show two camera views side by side. The dog gradually disappears from the first camera view (right) and appears in the second (left) as it progresses from start to end of its run, with a brief overlap period visible at the edges of both views.

---

## Methodology

### Step 0: Ground truth calibration from Rep 1

Rep 1 has a known ground truth alignment (trimmed offset = -4800ms, original offset = +25800ms) with reference screenshots in `Examples/Examples-Flat/`. These were studied to calibrate the alignment approach:

| Video time | IMU time | Dog pose |
|-----------|---------|----------|
| 4933ms | 53ms | Stationary before run |
| 5145ms | 265ms | First small leap forward with front paws |
| 5404ms | 524ms | At peak of first stride (front paw contact) |

Key calibration takeaways:
- Dog onset occurs at **~5.1s** in the rep 1 video — much later than the handler's first visible movement
- The first IMU running peak corresponds to the first stride where the front paw contacts the ground after the initial gallop thrust
- The dog remains fully stationary until ~5.1s even though the handler may be moving earlier

### Step 1: Dog onset detection

Generated screenshots at 200ms intervals across the video to identify the precise moment of the dog's **first movement** (not the handler's). Screenshots saved to `onset_wide/` subdirectories.

Per-rep onset estimates (calibrated against rep 1 examples):

| Rep | Dog onset (ms) | Notes |
|-----|---------------:|-------|
| Flat_2 | ~4900 | Dog begins first forward movement |
| Flat_3 | ~5000 | Dog begins first forward movement |
| Flat_4 | ~5500 | Dog begins first forward movement (later than reps 2/3/6) |
| Flat_5 | ~6100 | Dog begins first forward movement (latest onset) |
| Flat_6 | ~4900 | Dog begins first forward movement |

### Step 2: Coarse offset sweep

For each rep, selected a seek position approximately 300ms after the dog onset (to capture the first stride peak), then swept offsets in 200ms steps to find which offset places the IMU cursor on the first running peak.

| Rep | Seek anchor (ms) | Coarse sweep range | Best coarse offset |
|-----|------------------:|-------------------:|-------------------:|
| Flat_2 | 5200 | -6000 to -3000 | -4800 |
| Flat_3 | 5300 | -6200 to -3800 | -5000 |
| Flat_4 | 5800 | -6400 to -4000 | -5200 |
| Flat_5 | 6400 | -3200 to -1800 | -2600 |
| Flat_6 | 5200 | -6400 to -4000 | -5200 |

Screenshots saved to `coarse_v2/` (and `coarse_v2_supp/` for Flat_5).

### Step 3: Fine offset sweep

Refined around the coarse result in 50ms steps, checking alignment of the first stride peak. At each offset, verified that:
1. The IMU cursor lands on the first clear running peak
2. The video frame shows the dog at the corresponding stride phase (front paw contacting ground)

| Rep | Fine sweep range | Best fine offset | IMU cursor position |
|-----|------------------:|------------------:|---------------------|
| Flat_2 | -5200 to -4600 | **-4850** | 0.35s (first peak) |
| Flat_3 | -5400 to -4800 | **-5050** | 0.25s (first peak) |
| Flat_4 | -5600 to -5000 | **-5250** | 0.55s (first peak) |
| Flat_5 | -2800 to -2400 | **-2600** | 3.80s (first peak, Bout 2) |
| Flat_6 | -5400 to -4800 | **-5150** | 0.05s (first peak) |

Screenshots saved to `fine_v2/` subdirectories.

### Step 4: Multi-seek verification

Verified each offset at 4 different video seek positions spanning the full running sequence. For each seek position, checked that the IMU cursor position was consistent with the dog's visible stride phase using the general galloping heuristic (rear leg thrust = peak base, front leg contact = peak maximum, airborne = deceleration).

All 5 reps were verified **CONSISTENT** across all seek positions.

Screenshots saved to `verify_v2/` subdirectories.

---

## Corrections Applied

Three iterations of alignment were performed, with corrections applied between iterations based on user feedback documented in `corrections.md`.

### Iteration 1 (initial)

Used uniform onset times (~800ms) and assumed handler movement onset equated to dog movement onset. Results were far too early.

**Correction (Iter2 in corrections.md):** "Activity onset detection in the video should reference the movement of the dog and not the handler. Your initial onset detection for the videos is much too early. Also don't necessarily assume the same activity onset time in all reps."

### Iteration 2 (first correction)

Applied per-rep onset detection but still estimated dog onset 1–2 seconds too early (1000–4700ms range), confusing early handler movement with dog movement.

**Correction (Iter3 in corrections.md):** "Your onset estimates are still much too early for all reps. they are a bit better for reps 4 and 5. for context, the 'golden' ground truth alignment for rep1, which is the source of example screenshots, is about +25.8s i.e. the video starts 25.8s after the full imu stream"

### Iteration 3 (final — v2)

Calibrated against rep 1 ground truth examples, which showed dog onset at ~5.1s video time. Re-examined all reps with this calibration, yielding onset estimates of 4900–6100ms. Trimmed offsets (-4850 to -5250 for reps 2/3/4/6) closely match the rep 1 ground truth of -4800ms, providing strong cross-validation.

---

## Flat_5 — Two-Bout IMU Structure

Flat_5 required special handling due to its IMU signal structure:

- **Bout 1 (~0.3–2.8s trimmed time):** A cluster of peaks corresponding to some initial movement that is not the actual flat run. This bout is irrelevant for alignment.
- **Quiet gap (~2.8–3.5s):** Period of low activity between bouts.
- **Bout 2 (~3.5–6.0s trimmed time):** The actual flat running sequence, with the characteristic periodic stride pattern.

The coarse sweep for Flat_5 required a separate, less negative offset range (-3200 to -1800ms) compared to other reps (-6400 to -3000ms) because the relevant IMU activity (Bout 2) starts later in the trimmed window. The final offset of -2600ms places the IMU cursor in Bout 2 where the stride pattern aligns with the dog's visible running motion.

---

## Screenshots

All screenshots are in `alignment_screenshots/Arya/Arya_Flat/Arya_Flat_{N}/`.

### Final iteration (v2) — used for results

| Subdirectory | Contents |
|-------------|----------|
| `onset_wide/` | Dog onset detection screenshots (200ms steps, wide range) |
| `coarse_v2/` | Coarse offset sweep (200ms steps) |
| `coarse_v2_supp/` | Supplemental coarse sweep for Flat_5 (extended range) |
| `fine_v2/` | Fine offset sweep (50ms steps) |
| `verify_v2/` | Multi-seek verification (4 positions per rep) |

---

## Offset Formula Reference

The GUI (MMData.py) uses: `IMU_time = video_time + offset`

- **Positive offset** → IMU recording started before the video
- **Negative offset** → Video recording started before the IMU

For trimmed CSVs (where `load_data()` re-zeros timestamps from 0):
- `trimmed_offset = original_offset - trim_start_ms`
- `original_offset = trimmed_offset + trim_start_ms`

Verification with rep 1 ground truth:
- Trimmed offset: -4800ms
- trim_start: 30652ms
- Original offset: -4800 + 30652 = +25852ms ≈ +25800ms (user-reported ground truth) ✓
