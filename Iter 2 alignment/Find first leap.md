Iterate over each folder in @"720sync" with name starting "Derby_Tunnel_"
In each such folder, find the video named like @"repn_aframe_derby_full_720p.mp4", (where n is some integer). 
The dog is stationary for a period of time at the beginning of the video, and then takes a first leap. We need to find the frame number where the pose of the dog is at the peak of its first leap. 
See examples of pairs of images of the dog starting staionary, and then mid-air, at the peak of its first leap (in @Examples-Tunnel):

// Arya_stationary.png to Arya_first leap.png
// Goose_stationary.png to Goose_first leap.png
// Izzy_stationary.png to Izzy_first leap.png

Take screenshots of the video at different frame numbers (you may use the tool @view_video_frame.py if helpful) to return the frame number where the pose of the dog relative is closest to the peak of its first leap.  Ignore the human. save the screenshot for the resulting frame number.   
If helpful, you could crop a rectangular region of interest from the video, focussing on the dog. For example, for every image in @Examples-Tunnel like Izzy_first leap, there is a corresponding cropped image focussing on the region of interest called Izzy_first leap_cropped. List of all cropped image examples below:
// Arya_stationary_cropped.png
// Arya_first leap_cropped.png
// Goose_stationary_cropped.png
// Goose_first leap_cropped.png
// Izzy_stationary_cropped.png
// Izzy_first leap_cropped.png

