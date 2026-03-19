Iterate over each folder in @"720sync" with name starting "_Tunnel_"
In each such folder, find the video named like @"repn_tunnel_dog_full_720p.mp4", (where n is some integer). 
The dog is stationary for a period of time at the beginning of the video, followed by the first onset of motion. We need to find the frame number where the pose of the dog is at the peak of its first leap. 
See examples of pairs of images of the dog starting stationary, and then just starting its first stride (in @Examples-Tunnel-V2pytho):

// Arya_stationary.png to Arya_starting stride.png
// Goose_stationary.png to Goose_starting stride.png
// Izzy_stationary.png to Izzy_starting stride.png

Take screenshots of the video at different frame numbers (you may use the tool @view_video_frame.py if helpful) to return the frame number where the pose of the dog indicates the first onset of motion.  Ignore the human. save the screenshot for the resulting frame number.
If helpful, you could crop a rectangular region of interest from the video, focussing on the dog.

Important notes to avoid common mistakes:
1. Before zooming in on a candidate region, always do a coarse scan of the full video first. The handler may adjust posture early on (e.g. standing up from a crouch, shifting weight) without actually launching the dog. After such adjustments, the handler and dog often settle back into a stationary waiting position for an extended period before the actual launch. Do not confuse these preparatory adjustments with the true motion onset.
2. The handler often does a "lead-out" — walking or running ahead while the dog holds a sit-stay. The handler may be in full motion for many frames before the dog breaks its stay. Focus exclusively on when the DOG starts moving, not the handler. Track the dog's position on the turf across frames; if the dog's body hasn't displaced from its spot, it hasn't started moving yet, regardless of what the handler is doing.
3. The true motion onset is when the dog begins directed forward locomotion toward the obstacle — not just any small positional shift or weight adjustment.
4. In some videos, like in Zazu_Tunnel_1, there may be a false start: the dog starts to move but misses the tunnel and returns back to its start position to start the activity afresh. We need the frame indicating the motion onset on the succesful fresh (second) start, and we need to reject the frames in the duration of its false start.
5. The dog's position in frame varies between dogs and reps — always view a full (uncropped) frame first to locate the dog before choosing a crop region. Do not reuse crop coordinates from a different rep without verifying.

