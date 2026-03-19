Find the 4 visual jump-anchor frames for jump reps under `720sync`.

For each jump rep folder:
- Open the video named like `repn_jump_dog_full_720p.mp4`.
- The dog is stationary at first, then completes the jump moving from right to left.
- Ignore the human.
- Save full-frame screenshots for the chosen anchor frames inside the same rep folder.
- If helpful, you may inspect a crop after first checking the full frame, but do not rely on a crop alone.

The 4 anchors, in order, are:
1. `launch`
2. `midair`
3. `first ground contact`
4. `four legs drawn in after jump`

Use the example images in `Examples/Examples - Jump`.

Examples grouped by dog:

Arya
- `Arya_at launch of jump.png`
- `Arya_midair in jump.png`
- `Arya_first contact with ground after jump.png`
- `Arya_four legs drawn in after jump.png`

Goose
- `Goose_about to launch into jump.png`
- `Goose_at launch of jump.png`
- `Goose_midair in jump.png`
- `Goose_first contact with ground after jump.png`
- `Goose_four legs drawn in after jump.png`

Izzy
- `Izzy_about to launch into jump.png`
- `Izzy_at launch of jump.png`
- `Izzy_midair in jump.png`
- `Izzy_first contact with ground after jump.png`
- `Izzy_four legs drawn in after jump.png`

Tigger
- `Tigger_jump_firstground_contact_frame.png`
- `Tigger_jump_four_legs_drawn_in_after_jump_frame.png`

Interpret the anchors as follows:

`launch`
- Choose the compressed pre-takeoff frame.
- Prefer a pose like `Izzy_about to launch into jump` or `Arya_at launch of jump`.
- The best frame usually has all 4 legs drawn in and the body compressed just before lift-off.
- Do not choose the later frame where the front legs are already clearly in the air unless the pre-liftoff posture is genuinely unclear.

`midair`
- Choose the frame where the dog is hovering directly above the jump obstacle.
- Prefer the frame where the body is close to horizontal.
- Do not choose just any airborne frame.

`first ground contact`
- Choose the later landing-side frame where the front paws are actually bearing weight on the turf.
- The body should usually be pitched downward relative to `midair`.
- Do not choose an earlier frame where the dog is merely descending or just about to touch.

`four legs drawn in after jump`
- Choose the later post-landing recollection frame for the next stride.
- Wait until the initial landing response is over and the dog has re-collected.
- Do not choose the first slight leg tuck immediately after landing.

Important notes to avoid common mistakes:

1. Always inspect a full frame first.
- Dog position varies between reps.
- Do not reuse a crop region from another rep without verifying.

2. The jump direction is fixed in these videos.
- The dog always crosses the jump from right to left.
- `launch` and `midair` must be on the right side of the obstacle.
- `first ground contact` and `four legs drawn in after jump` must be on the left side of the obstacle.

3. Use obstacle-side sanity checks.
- If `launch` or `midair` are already on the left of the jump, they are wrong.
- If `first ground contact` or `four legs drawn in after jump` are still on the right of the jump, they are wrong.
- Many bad picks come from choosing all 4 frames before the dog has actually crossed the bar.

4. Anchor frame numbers must increase.
- The order must be:
  `launch < midair < first ground contact < four legs drawn in after jump`

5. Do not pick an earlier running stride as `launch`.
- A launch frame can still be too early even if it is on the correct side of the obstacle.
- The launch should happen close to the obstacle, not near the far right edge of the frame at the beginning of motion.
- After the chosen `launch` frame, the dog should proceed directly into the jump sequence.
- If the dog still completes another clear spread-and-regather stride before the actual jump, the launch is too early and should be moved later.

6. Prefer the earlier compressed launch posture over the already-airborne posture.
- `Izzy_about to launch into jump` is a better launch model than `Izzy_at launch of jump`.
- `Arya_at launch of jump` is also a good example.
- This was especially important in the later Zazu and Vivi corrections.

7. `midair` should be centered over the obstacle.
- The dog may be airborne for a range of frames, but the target frame is the one where the body is close to horizontal and hovering above the jump.
- A frame is too early if the dog is still clearly rising on the approach side.
- A frame is too late if the dog is already well onto the landing side and angled downward.

8. `first ground contact` and `midair` should look meaningfully different.
- `midair` should look level and suspended over the bar.
- `first ground contact` should happen later on the landing side, with the front paws down and supporting weight.
- If `first ground contact` looks almost the same as `midair` except slightly lower, it is probably too early.

9. The landing-side anchors are commonly chosen too early.
- For `first ground contact`, wait for clear turf-bearing contact.
- For `four legs drawn in after jump`, wait even later, after the landing response.
- In the Tigger example, `first ground contact` is around frame `1389` and the gathered post-landing stride is around frame `1411`.

10. Check the spacing of the landing-side pair.
- A reliable sequence is:
  `midair -> first ground contact -> landing/support -> four legs drawn in after jump`
- If `first ground contact` and `four legs drawn in after jump` are very close together, or if the gathered frame still looks like part of the same landing impact, the gathered frame is too early.

11. Known failure pattern from Arya and Zazu corrections.
- `launch` was often chosen too early from the first visible stride on the right.
- `midair` was sometimes chosen while the dog was low or still rising rather than centered above the bar.
- `first ground contact` and `four legs drawn in after jump` were sometimes chosen before the dog had truly crossed to the landing side.

Helpful reference frame ranges from corrected reps:
- `Arya_Jump_1`: `launch 1640`, `midair` roughly `1640-1735`, `first ground contact 1735`, `gathered 1750`
- `Vivi_Jump_1`: `launch 570`, `midair` roughly `580-660`, `first ground contact 660`, `gathered 678`
- `Zazu_Jump_1`: `launch 1630`, `midair` roughly `1630-1750`, `first ground contact 1750`, `gathered 1780`
- `Tigger_Jump_2`: `first ground contact` around `1389`, `gathered` around `1411`

Output:
- Save screenshots in the rep folder using names consistent with:
  - `dog_jump_n_at_launch_frame_<frame>.jpg`
  - `dog_jump_n_midair_frame_<frame>.jpg`
  - `dog_jump_n_first_ground_contact_frame_<frame>.jpg`
  - `dog_jump_n_four_legs_drawn_in_after_jump_frame_<frame>.jpg`
