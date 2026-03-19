# Video-to-IMU Alignment Process

## Summary of Results (Revised — Apex Dip Anchor)

| Data Pair      | Best Offset (ms) | Confidence   | Key Anchor Point                                   |
|----------------|-------------------|--------------|-----------------------------------------------------|
| Arya_Aframe_2  | **+2750**         | High         | Apex dip at IMU 8.147s <-> video 5397ms (frame 1295) |
| Arya_Aframe_3  | **+1050**         | High         | Apex dip at IMU 5.640s <-> video 4590ms (frame 1102) |
| Arya_Aframe_4  | **+4500**         | Medium-High  | Apex dip at IMU 9.004s <-> video 4504ms (frame 1081) |

The offset is defined as: `IMU_time = video_time + offset`. A positive offset means the IMU recording started before the video. All videos are 240fps.

### Previous results (Run 1 — Jump-on Peak Anchor)

| Data Pair      | Best Offset (ms) | Confidence   | Key Anchor Point                                   |
|----------------|-------------------|--------------|-----------------------------------------------------|
| Arya_Aframe_2  | +2500             | High         | Jump-on peak at IMU 7.08s <-> video 4576ms (frame 1098) |
| Arya_Aframe_3  | +1200             | High         | Jump-on peak at IMU 4.99s <-> video 3791ms (frame 910)  |
| Arya_Aframe_4  | +4200             | Medium-High  | Jump-on peak at IMU 8.10s <-> video 3901ms (frame 936)  |

> These Run 1 offsets used the biggest IMU peak (jump-on impact) as the primary anchor. See [Run 2 corrections](#run-2-re-alignment-using-apex-dip-anchor) for why the apex dip is a more reliable anchor.

### Detailed Anchor Points (frame indices at 240fps)

**Arya_Aframe_2** (offset +2500ms, 1462 frames total)

| Landmark             | IMU Time (ms) | Video Time (ms) | Frame | Note |
|----------------------|---------------|-----------------|-------|------|
| Approach stride 1    | 6185          | 3685            | 884   |      |
| Approach stride 2    | 6427          | 3927            | 942   |      |
| Approach stride 3    | 6679          | 4179            | 1003  |      |
| **Jump-on peak**     | **7076**      | **4576**        | **1098** | Primary anchor |
| On-aframe impact     | 7320          | 4820            | 1157  |      |
| Apex zone            | 7900          | 5400            | 1296  |      |
| Jump-off peak        | 8525          | 6025            | 1446  | Near end of video |

**Arya_Aframe_3** (offset +1200ms, 1370 frames total)

| Landmark             | IMU Time (ms) | Video Time (ms) | Frame | Note |
|----------------------|---------------|-----------------|-------|------|
| Approach stride 1    | 4098          | 2898            | 696   |      |
| Approach stride 2    | 4343          | 3143            | 754   |      |
| Approach stride 3    | 4581          | 3381            | 811   |      |
| **Jump-on peak**     | **4991**      | **3791**        | **910** | Primary anchor |
| On-aframe impact     | 5199          | 3999            | 960   |      |
| Apex zone            | 5800          | 4600            | 1104  |      |
| Jump-off peak        | 6816          | 5616            | 1348  | Near end of video |

**Arya_Aframe_4** (offset +4200ms, 1273 frames total)

| Landmark             | IMU Time (ms) | Video Time (ms) | Frame | Note |
|----------------------|---------------|-----------------|-------|------|
| Approach stride 1    | 7364          | 3164            | 759   |      |
| Approach stride 2    | 7617          | 3417            | 820   |      |
| Approach stride 3    | 7868          | 3668            | 880   |      |
| **Jump-on peak**     | **8101**      | **3901**        | **936** | Primary anchor |
| On-aframe impact     | 8340          | 4140            | 994   |      |
| Apex zone            | 9000          | 4800            | 1152  |      |
| Jump-off peak        | 9883          | 5683            | --    | Past end of video |

---

## Steps Taken

### 0. Studied reference examples

Before any alignment work, studied all reference images in `Examples/Examples-Aframe/` and `Examples/Examples-General/` to learn what correct alignment looks like — which dog poses correspond to which IMU features (e.g. rear-leg thrust = base of peak, airborne = near-zero, front-leg contact = deceleration). This was the foundation for all subsequent visual judgment calls, informed by the heuristics in `heuristics.md`.

### 1. Built headless screenshot tooling

Added `capture_sync_screenshot()` and `batch_screenshots()` to `MMData.py` so that composite video+IMU screenshots could be generated programmatically without launching the GUI. This was essential for iterating over many offset candidates quickly.

### 2. Explored video timelines

For each of the three data pairs (`Arya_Aframe_2`, `Arya_Aframe_3`, `Arya_Aframe_4`), generated screenshots at evenly-spaced seek positions (500ms, 1500ms, 2500ms, ...) with offset=0 to map out what happens in each video — identifying when the dog appears, approaches the aframe, jumps on, crosses the apex, and jumps off.

### 3. Explored IMU signatures

Generated wide-window IMU plots for each pair to see the full accelerometer and gyroscope signal shape, identifying the characteristic aframe "peak-dip-peak" pattern (large peak for jump-on, near-zero dip for apex jump, large peak for jump-off).

### 4. Programmatic activity onset detection

Computed video duration/FPS, IMU duration/sampling rate, and — critically — the IMU activity onset time using a threshold on filtered accel magnitude (e.g. `filtered > 0.2`). This gave initial offset estimates by comparing when activity begins in each stream:

- Aframe_2: IMU activity ~6.1s, dog appears in video ~4.0s -> rough offset ~2.0s
- Aframe_3: IMU activity ~1.9s, dog appears in video ~2.5s -> rough offset ~-0.5 to +1.0s
- Aframe_4: IMU activity ~7.3s, dog appears in video ~3.0s -> rough offset ~4.3s

This dramatically narrowed the coarse sweep range for each pair.

### 5. Coarse offset sweep

For each pair, swept offsets in 500ms steps around the estimates from step 4:
- Aframe_2: swept +500ms to +3500ms
- Aframe_3: swept -1000ms to +2000ms
- Aframe_4: swept +2500ms to +5500ms

### 6. Fine offset sweep and multi-point verification

Narrowed the offset range and tested at finer granularity (250ms steps). For each candidate offset, checked alignment at multiple video moments — approach strides, jump-on, on-aframe, apex zone, jump-off — to confirm the offset produces consistent matches across the entire aframe sequence, not just a single anchor point.

### 7. Reverse-mapping from IMU peaks (the breakthrough)

The coarse/fine sweeps were hampered by the small-thumbnail problem — it was hard to read the cursor position precisely on the IMU plot. The resolution came from **flipping the problem**:

1. Used `scipy.signal.find_peaks` to programmatically identify all prominent peaks and dips in the IMU data at multiple thresholds (height > 0.3 for running strides, height > 1.5 for jumps)
2. For each candidate offset, computed `video_time = imu_peak_time - offset`
3. Generated a screenshot at that exact video time and checked if the dog's pose matched the expected IMU feature (e.g. rear legs thrusting at the base of aframe = biggest peak)

This eliminated ambiguity entirely — instead of squinting at cursor positions on small plots, each screenshot was anchored precisely on a known IMU landmark.

### 8. Approach stride frequency validation

Extracted all peaks including smaller running-stride peaks and analyzed their inter-peak intervals. The approach running strides showed ~240-250ms spacing (~4 Hz), consistent with a galloping dog. This provided an independent cross-check that:
- The peaks identified as "approach strides" were actually running strides (correct frequency)
- The offset placed these stride peaks at video times where the dog was visibly galloping

---

## Problems Faced and Solutions

### Problem 1: Small video thumbnails made visual inspection difficult

The composite screenshots use a side-by-side layout where the video frame is relatively small. Fine details of the dog's pose (e.g. rear legs vs front legs on ground) were hard to distinguish. The cursor position on the IMU plot was also hard to read precisely.

**Solution:** Generated additional screenshots at finer video time intervals (200ms steps) with a fixed offset to map the video timeline precisely. Also used narrower IMU time windows (3s instead of 5s) to zoom in on the peaks. Ultimately, the reverse-mapping technique (step 7) made this problem moot by anchoring screenshots on known IMU landmarks rather than trying to read cursor positions.

### Problem 2: Multiple candidate peak-dip-peak patterns in IMU data

Some IMU recordings had multiple sequences of activity (approach running, aframe, post-aframe running), making it ambiguous which peak cluster was the actual aframe. For Aframe_2, there were two candidate dip locations between large peaks (at IMU 6.55s and 8.14s).

**Solution:** Used multi-point verification — checked that the offset produced consistent matches not just at the jump-on peak but also at approach strides (rhythmic peaks from gallop) and the apex zone (near-zero dip). The aframe's distinctive "peak -> dip -> peak" pattern is unique compared to normal running strides. Also verified that the approach stride peaks preceding the big peak had the right temporal characteristics for galloping (~250ms spacing).

### Problem 3: Approach stride peaks are similar to each other

During the gallop approach, stride peaks repeat at regular intervals (~250ms), so matching a single stride peak to a video frame could be off by one stride cycle.

**Solution:** Anchored primarily on the strongest, most distinctive feature — the jump-on peak (largest peak in the sequence) and the apex dip (near-zero reading during the brief airborne phase over the apex). These are unambiguous events. Then cross-verified with stride patterns. The stride frequency analysis (step 8) provided additional confidence.

### Problem 4: Video ends before the full aframe sequence completes

For some data pairs (especially Aframe_2 with offset +2500ms), the jump-off peak mapped to video times very near or past the end of the video (e.g. 6025ms in a 6092ms video). This meant the jump-off moment couldn't always be visually verified.

**Solution:** Relied on the jump-on peak and apex dip as the primary anchors, since those were well within the video frame. The jump-off peak was used as a secondary check when visible.

---

## Algorithm (High-Level Pseudo-Code)

```
ALIGN_VIDEO_TO_IMU(video_path, csv_path, obstacle_type):

    # --- Phase 0: Study Reference Examples ---
    # Review known-good alignment examples for this obstacle type
    # Learn which dog poses correspond to which IMU features

    # --- Phase 1: Data Exploration ---
    video_duration, fps = get_video_info(video_path)
    imu_data = load_and_filter_imu(csv_path, lowpass_cutoff=5Hz)
    imu_duration, sample_rate = get_imu_info(imu_data)

    # Sample video frames at regular intervals to map the timeline
    for seek_ms in range(0, video_duration, 500ms):
        frame = extract_frame(video_path, seek_ms)
        # Identify key events: dog appears, approaches obstacle, interacts, departs

    # --- Phase 2: Activity Onset Detection ---
    imu_onset = first_time_where(filtered_accel > threshold)
    video_onset = first_frame_where(dog_visible)
    estimated_offset = imu_onset - video_onset

    # --- Phase 3: IMU Landmark Detection ---
    all_peaks = find_peaks(imu_data.accel_mag_filtered, height=0.3)
    big_peaks = find_peaks(imu_data.accel_mag_filtered, height=1.5)

    # Identify obstacle-specific signature
    if obstacle_type == "aframe":
        # Look for: big_peak (jump-on) -> dip (apex) -> big_peak (jump-off)
        aframe_pattern = find_peak_dip_peak_pattern(big_peaks)
        imu_anchor_time = aframe_pattern.jump_on_peak_time

    # Validate approach strides: check inter-peak interval ~250ms (gallop)
    approach_strides = all_peaks before imu_anchor_time
    assert mean(diff(approach_strides.times)) ≈ 0.25s  # gallop frequency

    # --- Phase 4: Coarse Offset Sweep ---
    coarse_range = (estimated_offset - 2000ms, estimated_offset + 2000ms)
    for offset in range(coarse_range, step=500ms):
        for seek_ms in key_video_moments:
            screenshot = render_composite(video_path, imu_data, seek_ms, offset)
            # Visual check: does dog pose match IMU signal at cursor?

    # --- Phase 5: Reverse Mapping (Breakthrough Technique) ---
    # Instead of sweeping offsets forward, work backwards from IMU peaks
    for offset in candidate_offsets:
        for imu_peak in [jump_on_peak, apex_dip, approach_strides...]:
            video_time = imu_peak.time - offset
            frame = extract_frame(video_path, video_time)
            # Check: does dog pose match expected IMU feature?
            #   - jump_on_peak -> dog at aframe base, rear legs thrusting
            #   - apex_dip -> dog airborne over apex
            #   - approach_stride -> dog in galloping motion

    # --- Phase 6: Multi-Point Cross-Verification ---
    # Verify best offset against ALL heuristics simultaneously:
    score = 0
    for (imu_landmark, expected_pose) in anchor_points:
        video_time = imu_landmark.time - best_offset
        if dog_pose_at(video_time) matches expected_pose:
            score += 1

    return best_offset
```

---

## Run 2: Re-alignment Using Apex Dip Anchor

### Motivation

Three corrections to the Run 1 methodology were identified (documented in `corrections.md`):

1. **Activity onset can precede the dog entering the visible frame** — the dog may be moving (generating IMU signal) before it appears on camera.
2. **Jump on/off peaks are not necessarily the largest peaks** — approach strides can sometimes produce larger accelerometer peaks than the aframe impacts themselves.
3. **The apex dip is the most reliable anchor** — the lowest acceleration dip surrounded by larger periodic peaks on both sides corresponds to the dog crossing the aframe apex in a brief near-free-flight phase. This maps unambiguously to the visual event of the dog being at the apex, mid-air (see `Examples/Examples-Aframe/In Jump over Aframe apex.png`).

### Approach

1. **Trimmed IMU data** to the activity region using master alignment indices from `FIXEDMasterAlignments/Arya_clean_master.csv` via `trim_imu.py`. Formula: `offset = Offset - Anchor_Offset`, `idx_start = span_start + offset`, `idx_end = span_end + offset`.

2. **Ran peak detection** (`imu_peak_detection.py`) on trimmed CSVs to identify the full peak structure. Each rep showed the same pattern:
   - Approach strides (~240-250ms spacing, ~4.0 Hz galloping)
   - Jump-on cluster (1-2 large peaks)
   - **Apex gap** (~1.1-1.4s of low activity)
   - Jump-off cluster (1-2 large peaks)
   - Post-aframe strides

3. **Found the apex dip** — the minimum filtered acceleration value within the gap between the jump-on and jump-off clusters:

   | Rep | Gap (trimmed time) | Apex dip (trimmed) | Apex dip (original) | Filtered value |
   |-----|--------------------|--------------------|---------------------|----------------|
   | Aframe_2 | 1.575 – 2.793s | 2.415s | **8.147s** (8147ms) | -1.14 |
   | Aframe_3 | 1.588 – 2.958s | 2.029s | **5.640s** (5640ms) | -0.82 |
   | Aframe_4 | 1.776 – 2.836s | 2.439s | **9.004s** (9004ms) | -0.96 |

   Conversion: `original_time = trimmed_time + trim_time_offset` where trim_time_offset is 5.732s (rep 2), 3.611s (rep 3), 6.565s (rep 4).

4. **Coarse apex sweep** — for each rep, swept offsets in 500ms steps such that the IMU cursor lands on the apex dip while varying the video frame. Identified the range where the dog is visually on or near the aframe apex.

5. **Fine apex sweep (100ms steps)** — narrowed to the candidate range for each rep.

6. **Ultra-fine apex sweep (50ms steps)** — final refinement around the best candidates. At each offset, checked whether the dog's pose matched the reference apex image (body horizontal at the top of the A-frame, close to mid-air).

### Fine sweep analysis

**Aframe_2** (apex dip at IMU 8147ms, `video_time = 8147 - offset`):

| Offset | Video time | Dog position | Assessment |
|--------|-----------|--------------|------------|
| +2650 | 5497ms | Descending downslope | Past apex |
| +2700 | 5447ms | At/just past apex, front legs reaching down | Slightly past |
| **+2750** | **5397ms** | **Body horizontal at apex top** | **Best match** |
| +2800 | 5347ms | Near apex, body slightly angled up | Approaching |
| +2850 | 5297ms | On upslope, still climbing | Before apex |

**Aframe_3** (apex dip at IMU 5640ms, `video_time = 5640 - offset`):

| Offset | Video time | Dog position | Assessment |
|--------|-----------|--------------|------------|
| +950 | 4690ms | Past apex, on downslope | Past apex |
| +1000 | 4640ms | Near apex, transitioning over | Close |
| **+1050** | **4590ms** | **Body horizontal at apex top** | **Best match** |
| +1100 | 4540ms | Near top, body slightly angled up | Approaching |
| +1150 | 4490ms | On upslope approaching top | Before apex |

**Aframe_4** (apex dip at IMU 9004ms, `video_time = 9004 - offset`):

| Offset | Video time | Dog position | Assessment |
|--------|-----------|--------------|------------|
| +4350 | 4654ms | Past apex, on downslope | Past apex |
| +4400 | 4604ms | Near apex, just past | Slightly past |
| +4450 | 4554ms | At/near apex | Close second |
| **+4500** | **4504ms** | **Body horizontal at apex** | **Best match** |
| +4550 | 4454ms | On upslope near top | Approaching |
| +4600 | 4404ms | On upslope, still climbing | Before apex |

### Comparison with Run 1

| Rep | Run 1 offset (jump-on peak) | Run 2 offset (apex dip) | Change |
|-----|----------------------------|------------------------|--------|
| Aframe_2 | +2500ms | **+2750ms** | +250ms |
| Aframe_3 | +1200ms | **+1050ms** | -150ms |
| Aframe_4 | +4200ms | **+4500ms** | +300ms |

Changes are in the 150-300ms range. The apex dip anchor is expected to be more reliable because:
- The apex dip maps to a single, unambiguous visual event (dog at apex, mid-air)
- Per correction #2, the biggest peak may not always be the jump-on — approach strides can be larger
- The apex dip is structurally isolated (the only deep minimum between the two main peak clusters)

### Confidence

| Rep | Confidence | Reasoning |
|-----|-----------|-----------|
| Aframe_2 | **High** | Clear progression across 50ms steps, apex pose matches reference image, ±50ms precision |
| Aframe_3 | **High** | Clear progression, apex pose identifiable, ±50ms precision |
| Aframe_4 | **Medium-High** | Clear apex match at +4500, but jump-off peak maps to 5683ms — past the video end (5304ms), so the full aframe sequence cannot be cross-verified from the downslope side |

### Screenshots

| Directory | Contents |
|-----------|----------|
| `alignment_screenshots/Aframe_{2,3,4}_apex_sweep/` | Coarse apex sweeps (500ms steps) |
| `alignment_screenshots/Aframe_{2,3,4}_apex_fine/` | Fine apex sweeps (100ms steps) |
| `alignment_screenshots/Aframe_{2,3,4}_apex_fine50/` | Ultra-fine apex sweeps (50ms steps) |

---

## Files Created / Edited

### Edited Files

| File | Changes |
|------|---------|
| `MMData.py` | Added `capture_sync_screenshot()` -- headless function to render composite video+IMU screenshots using matplotlib Agg backend (no GUI dependency). Added `batch_screenshots()` -- convenience wrapper to generate screenshots for multiple (seek, offset) pairs from a data directory. |
| `heuristics.md` | Expanded with detailed general stride heuristics (rear leg thrust = peak base, front leg contact = deceleration) and aframe-specific heuristics with references to example images for each phase of the aframe obstacle. |

### New Files

| File | Purpose |
|------|---------|
| `alignment_process.md` | This document. Records the full alignment methodology, results, problems encountered, and the algorithm used. |

### Directories Used

| Directory | Purpose |
|-----------|---------|
| `Examples/Examples-Aframe/` | Reference screenshots of known-good alignment for the aframe obstacle, showing each phase (jump-on, apex, jump-off) with the correct IMU cursor position. Used as ground truth for heuristic development. |
| `Examples/Examples-General/` | Reference screenshots of known-good alignment for general dog galloping motion, showing stride phases (rear thrust, airborne, front contact) matched to IMU peaks. |
| `Arya Aframe/` | Raw data directory containing three subfolders (`Arya_Aframe_2`, `Arya_Aframe_3`, `Arya_Aframe_4`), each with a video (.mp4) and IMU CSV pair for one aframe repetition. |
| `alignment_screenshots/` | All intermediate and final composite screenshots generated during the offset search process. Organized in subfolders by data pair and search phase (explore, coarse, fine, verify, peakmatch, etc.). |
| `test_screenshots/` | Initial test output from the `batch_screenshots()` function, verifying the tool works correctly before running the full alignment process. |
