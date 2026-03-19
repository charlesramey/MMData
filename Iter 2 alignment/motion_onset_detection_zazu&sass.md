# Motion Onset Detection — All Tunnel Reps

## Method

Coarse-to-fine visual scan of each video at 240 fps / 720p:

1. **Coarse scan** — full frames every 100 frames to identify the overall video structure (positioning phase, lead-out, motion onset region)
2. **Fine scan** — left-side crops every 50 frames to locate the handler/dog and narrow down the transition window
3. **Finer scan** — every 10 frames around the candidate region, cropped tightly on the dog
4. **Per-frame scan** — single-frame resolution to pinpoint the exact onset

Focus was exclusively on the **dog's** body displacement, ignoring handler motion (lead-out pattern).

---

## Results

| Rep | Motion Onset Frame | Notes |
|-----|-------------------|-------|
| Sass_Tunnel_1 | 1310 | Clear lead-out; dog breaks stay and launches |
| Sass_Tunnel_2 | 1270 | Clear lead-out; dog breaks stay and launches |
| Sass_Tunnel_3 | 1405 | Lead-out; dog positioned near back-left wall. Transition from sitting to forward launch around 1400–1410 |
| Zazu_Tunnel_1 | 2792 | **False start** ~frames 800–1600, dog repositioned. Second lead-out ~2600, successful onset at 2792 |
| Zazu_Tunnel_2 | 1226 | Lead-out; dog sitting near wall, launches ~1225–1230 |
| Zazu_Tunnel_3 | 1012 | Lead-out; dog sitting, launches ~1010–1015 |
| Tigger_Tunnel_1 | 1088 | Lead-out; dog in down-stay, rises and launches ~1080–1092 |
| Tigger_Tunnel_2 | 2042 | Very long lead-out (~1600 frames); dog in down-stay, rises ~2040–2050 |
| Tigger_Tunnel_3 | 1140 | Lead-out; dog sitting near wall, body elongates ~1135–1150 |
| Vivi_Tunnel_1 | 1382 | No lead-out — handler runs with dog. Dog separates at ~1380 |
| Vivi_Tunnel_2 | 1150 | No lead-out — handler crouches then runs with dog. Dog separates at ~1150 |
| Vivi_Tunnel_3 | 1518 | No lead-out — handler crouches then runs with dog. Dog separates at ~1515 |

---

## Per-Rep Analysis

### Sass_Tunnel_1
- Dog and handler positioned on the left side of the facility
- Handler does a lead-out starting ~800, walking ahead while dog holds sit-stay
- Dog breaks stay at ~1310, launching into a forward sprint

### Sass_Tunnel_2
- Similar lead-out pattern
- Handler walks ahead ~700–900, dog holds position
- Dog breaks stay at ~1270

### Sass_Tunnel_3
- Dog positioned near back-left wall, small in frame
- Handler does lead-out; dog holds sit-stay for extended period
- Dog's body begins shifting from upright sitting to forward stretch at ~1400
- Clear forward launch by frame 1410
- Onset marked at 1405

### Zazu_Tunnel_1 (false start)
- Frames 0–600: Handler and dog entering and positioning
- Frames 600–800: Dog and handler together, initial positioning
- Frames ~800–1200: Dog appears to move (false start — dog misses tunnel)
- Frames ~1400–1600: Handler returns dog to start position, repositions
- Frames 2000–2500: Handler repositions dog for second attempt
- Frames 2600–2750: Handler does second lead-out, dog holds sit-stay
- Frame 2792: Dog breaks stay, begins directed forward locomotion (successful start)

### Zazu_Tunnel_2
- Frames 200–600: Handler positioning dog (bending over, placing)
- Frames 800–1000: Handler does lead-out, dog sitting near wall
- Frame 1220: Dog still sitting
- Frame 1226: Dog begins shifting from upright to forward-leaning
- Frame 1232+: Dog in full forward sprint

### Zazu_Tunnel_3
- Frames 200–600: Handler positioning dog
- Frames 800–1000: Handler does lead-out
- Frame 1008: Dog still sitting
- Frame 1012: Dog begins directed forward locomotion
- Frame 1017+: Dog running

### Tigger_Tunnel_1
- Dog in a down-stay (lying flat) near the wall
- Handler does lead-out starting ~800
- Dog lying flat through 1060, begins rising at ~1076–1080
- Body elongates into forward sprint by 1092
- Onset marked at 1088

### Tigger_Tunnel_2
- Very long lead-out — dog holds down-stay for ~1600 frames
- Dog lying flat near wall through frame 2000
- Dog begins rising at ~2036–2040, launching forward by 2048
- Onset marked at 2042

### Tigger_Tunnel_3
- Dog sitting near wall on the right side of frame (different camera position)
- Handler does lead-out starting ~800
- Dog sitting through 1130, body elongating by 1140
- Clear forward displacement by 1150–1160
- Onset marked at 1140

### Vivi_Tunnel_1
- **No lead-out** — handler crouches with dog, then both launch together
- Handler crouched with dog at feet through ~1360
- Handler rises and starts running at ~1370
- Dog separates from handler and begins directed forward motion at ~1382
- Onset marked at 1382

### Vivi_Tunnel_2
- Same pattern: handler crouches with dog, both launch together
- Handler crouched through ~1110
- Handler rising at ~1130, dog separating at ~1148–1152
- Onset marked at 1150

### Vivi_Tunnel_3
- Same pattern: handler crouches with dog, both launch together
- Handler crouched through ~1490
- Handler rising at ~1505, dog separating at ~1515
- Onset marked at 1518

---

## Screenshots

Motion onset screenshots saved at:
- `/tmp/tunnel_motion_onset/Sass_Tunnel_1/motion_onset_1310.png`
- `/tmp/tunnel_motion_onset/Sass_Tunnel_2/motion_onset_1270.png`
- `/tmp/tunnel_motion_onset/Sass_Tunnel_3/motion_onset_1405.png`
- `/tmp/tunnel_motion_onset/Zazu_Tunnel_1/motion_onset_2792.png`
- `/tmp/tunnel_motion_onset/Zazu_Tunnel_2/motion_onset_1226.png`
- `/tmp/tunnel_motion_onset/Zazu_Tunnel_3/motion_onset_1012.png`
- `/tmp/tunnel_motion_onset/Tigger_Tunnel_1/motion_onset_1088.png`
- `/tmp/tunnel_motion_onset/Tigger_Tunnel_2/motion_onset_2042.png`
- `/tmp/tunnel_motion_onset/Tigger_Tunnel_3/motion_onset_1140.png`
- `/tmp/tunnel_motion_onset/Vivi_Tunnel_1/motion_onset_1382.png`
- `/tmp/tunnel_motion_onset/Vivi_Tunnel_2/motion_onset_1150.png`
- `/tmp/tunnel_motion_onset/Vivi_Tunnel_3/motion_onset_1518.png`

## Common Patterns Observed

- **Lead-out**: All reps show the handler walking/running ahead 200–500+ frames before the dog breaks its sit-stay
- **Sass reps**: Dog is lighter colored (easier to spot), onset frames cluster around 1270–1405
- **Zazu reps**: Dark-colored dog, harder to distinguish against the dark turf. Onset frames cluster around 1012–1226 (excluding the false start in Tunnel_1)
- **Zazu_Tunnel_1 false start**: The only rep with a false start. The dog moved briefly but was brought back and repositioned, adding ~1500 frames before the successful second attempt
- **Tigger reps**: Dog uses a down-stay (lying flat), not a sit-stay. Onset involves rising from a down before launching. Lead-out durations vary widely (Tunnel_2 has an exceptionally long ~1600-frame lead-out)
- **Vivi reps**: No lead-out pattern — handler crouches with the dog and they launch together. The dog is small, making it harder to distinguish from the handler until it separates. Need to track when the dog's body displaces from the handler's position, not when the handler starts moving
