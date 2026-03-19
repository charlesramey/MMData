This file provides guidance to Gemini when working with code in this repository.

## Project Overview
Tool for automated time-synchronization of video to IMU sensor data for dog agility sport recordings.

## Development Workflow
If more theoretical project context is needed, read the theoretical background of this repo, in research_context.md.
See dataset_summary_720sync.txt for information on dogs x obstacles x reps for which we need to perform alignment.
For each obstacle we are building an aligner class, for example aframe_aligner or tunnel_aligner, all of which inherit from obstacle_aligner. The aligner specifies the method for aligning the video-imu pair using one or more anchor features in the video and corresponding points in the IMU stream.
Visual anchor feature detection:
1. For detecting video anchor features we use instructions like in "Find motion onset.md", which detects the first onset of dog motion in the video, if visible. For all visual anchor feature detection use your own intelligence and do not rely on image processing scripts (for ex. using opencv) to analyze the images.
2. The visual anchor frame numbers are populated in the second column of a csv for that obstacle, for example "Tunnel Motion Onset Frames.csv" (first column is the name of the folder containing the rep).
3. Do not look at "Ground Truth Manual Alignments" at any point in visual anchor feature detection.
IMU point detection:
1. Each IMU stream is trimmed to focus on the region of activity, so "trimmed" csv files are used for all our analyses rather than full (prefer_trimmed=true in obstacle_aligner)
2. We can use reusable scripts to detect points of interest in the numeric imu stream, corresponding to the visual anchor features. For example, motion onset in the video is to be aligned to the "trim start time".
Offset calcualtion:
1. Obstacle-specific logic in the aligner class specifies how to determine the offset based on the visual anchor frame and imu point detected
2. The computed imu point, and resulting offset are populated in subsequent columns of the csv for the obstacle, for ex. "Tunnel Motion Onset Frames.csv"
Comparison with Ground Truth Manual Alignments:
1. This is the only step where we can access the ground truth alignments for comparison. Populate the manual alignments where available using the respective files and rows in "Ground Truth Manual Alignments"
2. Calculate the error as (offset_ms - ground truth offset)