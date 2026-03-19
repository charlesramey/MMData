# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview
Tool for automated time-synchronization of video to IMU sensor data for dog agility sport recordings.

## Development Workflow
If more theoretical project context is needed, read the theoretical background of this repo, in research_context.md.
For heuristics used for aligning the video to IMU data, specific to each obstacle, always read heuristics.md.

**Data pipeline flows through these stages:**

1. Run **MMData.py** — PyQt5 desktop GUI (`SyncPlayer` class) for manually aligning video playback with IMU sensor data. Uses OpenCV for video, matplotlib for signal plots. Logs sync results to `sync_log.csv`.
2. Take screenshots of the video-IMU synchronization, for various offsets tested, for different seek positions of the video as necessary.
3. Report the best offset, per the heuristics defined in heuristics.md

## Running the Tools

```bash

    python MMData.py  
```

