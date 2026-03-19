# Alignment Across Anchors

Goal: estimate one global video-to-IMU offset from multiple anchor correspondences without introducing time warping.

Model:

```text
t_imu = t_video + offset
```

This keeps the anchor order and spacing fixed up to a single constant shift. There is no scale term and no non-linear warping.

Recommended approach:
- Use weighted least squares over all anchor pairs.
- Compute one candidate offset per anchor:

```text
offset_k = t_imu,k - t_video,k
```

- Solve for the single offset that minimizes weighted squared error:

```text
min_offset  Σ_k w_k (offset - offset_k)^2
```

- The solution is the weighted mean of the per-anchor offsets:

```text
offset* = (Σ_k w_k offset_k) / (Σ_k w_k)
```

Why this is appropriate here:
- A single offset preserves anchor spacing automatically.
- It is simple, interpretable, and matches the current trimmed-CSV workflow.
- It avoids overfitting that would come from time warping with only a few anchors.

Suggested jump-anchor weighting:
- `launch`: high weight
- `gathered`: high weight
- `first_contact`: slightly lower weight
- `midair`: weight `0`

Reasoning:
- `launch` and `gathered` are tied to sharper flanking peaks and tend to be more stable.
- `first_contact` is useful but can be less sharp.
- `midair` is often broad and ambiguous within the trough, so it should not influence the fitted offset.

If needed later, more flexible forced-alignment families include:
- constrained dynamic time warping
- HMM / Viterbi forced alignment
- segmental alignment with phase-duration constraints

Those are better suited to sequence-level matching or clock drift. For the current jump-anchor problem, weighted least squares with one offset is the right first method.
