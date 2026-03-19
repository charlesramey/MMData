# Heuristics 
These are guidelines used to visually align video to real IMU data, based on known motion characteristics of the dogs and some specific properties of each obstacle.

## General 
Since we only need to find a single time offset between the video and IMU streams, it is sufficient to obtain a single (or few) high-confidence indicator(s) of alignment between the two, which we will do using heuristics that are both general to dog motion and specific to each obstacle. We are interested in returning the most high-probability alignment offset, which best matches all heuristics.

The general heuristic is derived from what the pattern of the IMU should look like with the motion/ stride of the dog. When performing a galloping gait, a dog is reaching out with her front legs, catching up with the rear while contracting her body and then thrusting with the rear to extend the body again. We expect the large peaks in the IMU graph to start growing at the thrusts from the rear legs (i.e. the base of a peak corresponds to when the rear legs are just starting to thrust). At the end of the thrust stroke with the rear legs, the meaximum of a peak is reached, after which the dog stops accelerating further. 
When the front legs start touching the ground a smaller peak can start as the body leans forward with the neck and the rear legs catch up with the front. Anytime the dog is in free fall (a jump with all 4 legs off the ground), the IMU should read close to 0 for the duration of the jump. 
See examples in the `Examples/Examples-General/` folder for visual alignment guides, particularly focusing on the dog's pose and the corresponding position indicator (white line) on the IMU plot:
- `Rear legs about to thrust off.png` — base of a peak, rear legs beginning thrust
- `Max thrust stroke of rear legs reached.png` — peak maximum, end of rear leg thrust
- `Launched in mid-air after rear leg thrust stroke.png` — dog airborne after thrust. Acceleration is decreasing.
- `First contact of front legs with ground after gallop.png` — dog continues to decelerate
- `Second contact of rear leg with ground after gallop.png` — end of the decelaration - and start of a smaller peak
- 'Max of smaller peak as rear legs catch up.png'

For every obstacle, use the relevant per-obstacle heuristics below for coarse alignment. Then, also verify fine alignment using this general heuristic of the rising and falling edges of the peaks roughly coinciding with rear legs thrusting and front legs landing, respectively, through the running motion.

In some obstacles, the dog may completely miss the obstacle and return to the start to retry. In this case, we can associate the failed attempts with some IMU peaks corresponding to running to the obstacle and running back to the start. However, we can primarily fallback to the motion characteristics of the retry segment to align the video to the IMU sequence, which should be similar to other reps.

## Obstacle specific
### Aframe
Jump over apex corresponds to near-0 reading. High peaks on the left and right correspond to jumping onto, and off, the Aframe.

See examples in `Examples/Examples-Aframe/`, particularly focusing on the dog's pose and the corresponding position indicator (white line) on the IMU plot: 
- `Start of jump to Aframe.png` - base of a large IMU peak
- `Peak acceleration in jump to Aframe-rear legs about to lift off.png` - max of IMU peak
- `Right before small jump over Aframe apex.png` - Acceleration is about to become very small for a time period as the dog is briefly airborne
- `In Jump over Aframe apex.png` - Dog in jump
- `First contact on downslope after jump over apex.png` - Acceleration magnitude is about to rise again
- `About to jump off Aframe.png` - Base of peak as Rear legs about to thrust
- `Peak acceleration in jump off Aframe - rear legs about to lift off.png` - Peak acceleration reached as the end of the rear legs' thrust stroke is reached
- `Mid air in jump off Aframe.png` - Accleration is decreasing right after the rear legs have lifted off
- `First contact after jump off Aframe.png` - Acceleration still decreasing
- `Second leg contact after jump off Aframe.png` - Min of peak

### Flat
Since the dog is stationary before starting to run, and importantly, the stationary dog is visible in the video frame, we can align the start of feet movement to the start of the first rising edge of periodic running-like motion in the IMU reading. This differs from some other obstacle videos where the dog may only become visible in the frame after it has already started running (and thus the first IMU peak should have already elapsed). Note the recordings of Flat running show two camera views side by side. The dog gradually disappears from the first camera view (right) and appears in the second (left) as it progresses from the start to the end of its run, with a brief overlap period in between when it is visible at the edges of both views.

See examples in `Examples/Examples-Flat/`, particularly focusing on the dog's pose and the corresponding position indicator (red dot) on the IMU plot:
- `Stationary before run.png` - dog still before run
- `First small leap forward with front paws.png` - start of first movement forward with front feet; acceleration rises
- `Start of thrust with rear legs.png` - start of a second rising phase in the accleration as rear legs start to thrust
- `Reaching Peak of acceleration before front legs contact ground.png` - front legs about to contact the ground and brake the rise of acceleration to its peak
- `At peak of acceleration when front paw contacts ground.png` - front paw contacts ground; at peak
- `Rear legs caught up and starting to thrust for second stroke.png` - after front legs contact ground and rear legs draw in, the rear legs are now ready to start the second thrust
- `Reaching second peak of acceleration before front legs contact ground.png` - similar to first stride, front legs about to contact the ground to brake the rising acceleration
- `At second peak acceleration when front paw contacts ground.png` - front paw contacts ground; at second peak 
- `Rear legs caught up and at start of thrust for third stroke.png` - rear legs have drawn in and are ready to start third thrust
- `At third peak as front paw contacts ground.png` - front paw contacts ground; at second peak  

### Teeter
The best anchor is a steady low acceleration period in the middle of the teeter when the dog is nearly stationary with respect to the teeter, waiting for the teeter to tilt - this corresponds to a near-0, flat segment in the IMU curve. Similar to the Aframe, high peaks on the left and right correspond to jumping onto, and off, the teeter (but note, the peaks corresponding to the jumps need not always be highest). Because of the inability to definitively identify the largest peaks as the jumps, another heuristic that can be helpful is matching the number of strides made by the dog in the video, vs. the number of periodic peaks seen in the IMU data, for a given candidate offset. The lead upto the teeter is a running motion very similar to the Flat obstacle, except for the teeters we can't see the start of the dog's motion from a stationary state, unlike the Flat reps. Thus the same heuristics from 'General' above apply in identifying strides. Heuristics more specific to interaction with the teeter are listed below.
See examples in `Examples/Examples-Teeter/`, particularly focusing on the dog's pose and the corresponding position indicator (red dot) on the IMU plot:
- `jump onto teeter - deceleration starts as front paw contacts teeter.png` - note this isn't necessarily the largest peak.
- `Peak of second stride- front paw contacts teeter.png` - front paws making contact act to brake the second stride
- `Peak of third stride- front paw contacts teeter.png` - front paws making contact act to brake the third stride
- `Peak of fourth stride- front paw contacts teeter.png` - front paws making contact act to brake the fourth stride
- `Dog in steady low acceleration period as teeter starts to tilt.png` - the dog's position wrt the teeter will stay fixed for some period of time as the teeter tilts. The acceleration stays at a low steady value.
- `Dog still in steady low acceleration period as teeter has partly tilted.png` - teeter has partially tilted to become horizontal, and dog's acceleration is still the same level
- `front paw contact acts to decelerate dog on the descent from teeter.png` - teeter has fully tilted and dog is descending down the teeter, using its front paws to brake its forward motion
- `Rear legs start to thrust for jump off teeter.png` - base of peak where rear legs are about to thrust for the jump off the teeter
- `Peak of jump off teeter - Front paws act to brake the jump.png` - front paws make contact with ground, braking from the peak of the jump-off motion
- `Rear legs catch up to proceed with normal walking stride (to be followed by rear legs thrusting).png` - the start of rear legs thrusting for a normal stride.