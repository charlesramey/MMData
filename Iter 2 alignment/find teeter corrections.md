Your estimates for the three anchors are too early in all cases. you may provide the answer accurate to +-5 or even +-10 - precision matters less than accuracy here.
For vivi-teeter-1, the frames for about to jump off, stepped off, hind legs leave teeter are around 1940, 1990, 2019 respectively. The about to jump off frame is the last frame for which all four of the dog's legs are in contact with the teeter, after which the front legs lift off and the body leans forward. The "stepped off" frame shoudl show the front two paws contacting the ground and supporting weight. The "hind legs leave teeter" should show the hind legs in the air or stepped on the ground instead of being on the teeter.

For Sass, your estimates are a good start but note that that region is a false start for jumping off the teeter: several frames later, sass is actually about to jump off at 2300; front legs have stepped off the teeter at 2315 and rear legs have left the teeter by 2350.

------------------------------------------------------------------------------------------------------------------------------------------

Changing our approach to adopt two different strategies for small and large dog size classes:
A. For small dogs like Arya, Vivi, the dog tends to jump off the teeter obstacle:
1. Continue to detect the 3 main frames for "about to jump off", "stepped off", "hind legs leave teeter". 
2. Your estimates for Arya_Teeter_1 and 2 are close. For Arya_Teeter_3 and 5, the estimates are a too early; the dog is still farther behind on the teeter. The actual frames (in that order) for Arya_Teeter+3 are around 8575, 8704, 8825.
3. For Vivi as well, the estimates can be a bit too early. For Teeter_1, your "hind legs leave teeter" frame is actually closer to the actual "about to jump off" frame. The actual frames for Vivi_Teeter_1 (in that order) are around 8066, 8266 and 8412. For Vivi_Teeter_2, they are 4612, 4733, 4970.
See examples for small dogs represented by Arya:
Arya-1 - Dog reached highest point on teeter, just before teeter tilt
Arya-2-Dog on horizontal teeter
Arya-3-Teeter finished tilting, dog facing downwards
Arya-4-Dog about to jump off teeter
Arya-5-Dog stepped off teeter
Arya-6-Hind legs leave teeter

B. For larger dogs like Sass, Tigger, Zazu, the dog is usually already close to being off the teeter once the teeter has tilted.
1. Switch from finding the 3 anchor frames to a single frame which represents the lowest point of the dog's head after the teeter has tilted. This usually corresponds to the point of time where the teeter has just tipped over fully and hit the ground. The dog's front paws may be slightly off the teeter.
2. See examples of large dogs reaching the lowest point:
Delta_lowest point - Frame 6140
Izzy_lowest point - Frame 5450
Tigger_lowest point - Frame 1823
Zazu_lowest point - Frame 9395
Sass_lowest point - Frame 8790




