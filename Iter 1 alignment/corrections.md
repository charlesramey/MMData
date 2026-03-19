## Aframe:
1. Start of activity of dog in video could precede dog entering the visible frame in the video.
2. Even though jumping on and off the Aframe typically correspond to high IMU peaks, these activities may not necessarily correspond to the largest peaks. Sometimes larger peaks may occur in the approach strides for example.
3. Actually the lowest acceleration dip that is surrounded by larger periodic peaks on both sides in the IMU stream is usually the most reliable anchor for alignment. Ensure that during this motion, the dog is at the apex in the video, and is or is close to being in mid-air. See /Users/DiptiVM1/Projects/MMData/Examples/Examples-Aframe/In Jump over Aframe apex.png for example. You could examine finer offset sweeps in this range if necessary. 

## Flat:
### Iter2:
Activity onset detection in the video should reference the movement of the dog and not the handler. Your initial onset detection for the videos is much too early. Also don't necessarily assume the same activity onset time in all reps.
### Iter3:
Your onset estimates are still much too early for all reps. they are a bit better for reps 4 and 5. for context, the "golden" ground truth alignment for rep1, which is the source of          
example screenshots, is about +25.8s i.e. the video starts 25.8s after the full imu stream   