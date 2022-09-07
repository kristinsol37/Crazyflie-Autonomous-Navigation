# Autonomous Intruder Detection Drone Project

Autonomous Intruder Detection Drone Project using a Crazyflie 2.0 and ROS

![image](https://user-images.githubusercontent.com/78739982/188849201-055e8760-7e4b-4de9-9701-4e7d9e1ca295.png)


### Introduction of the Integrated System
This software runs a Crazyflie drone to fly around for a long time and cover a pre-defined environment. It is composed of three main parts, localization, for the drone to be able to localize itself in the map. Perception, using the Crazyflie's camera to detect and position "intruders" or traffic signs and show their position in the map in a visualizing program (RViz). The third part is planning where the drone's position is used to plan a path and execute it so that most of the map is covered and the intruder can be found. These parts had to be integrated together to form a system. 

The base.launch file takes care of the communication between all of the system's nodes, needed to be able to run the brain. The brain (brain.py) executes the exploration of a given map using pose information available with localization. The nodes get/provide information from/to other nodes with subscribers/publishers to specific topics, or with broadcasted/broadcasting transforms (either static or dynamic) from/to the TF tree. By solving different tasks the nodes make it possible for the different parts of the system to communicate and get the information needed to form a functioning system.
    
### Subparts of System
#### Perception
 The neural network-based detector, i.e. the perception system, extracts useful image features, predicts bounding boxes positions, sizes and then classifies based on the detected features. An image from Crazyflie's camera is put into our neural network to check if it can detect a traffic sign. Here the system is informed if an intruder has been dected. For a detection of a sign, the image is cropped to fit a bounding box (from the neural network) of the detection and then compared to the canonical images for matching features. With enough good matches, the matching features' (between the detected and canonical) coordinates are used with solvePnP to return the translation and orientation of the detected traffic sign. The perception system can estimate the 6D pose of detected traffic signs. 

#### Localization
The localization system, makes a transform between the frames map and odometry, using pose information from aruco detections and pre-defined markers in the map. The detections are filtered for outliers before doing any calculations or comparison of map markers. There is one unique marker in the map, and the drone's starting position is so that it starts off by detecting that marker. The rest are non-unique and their pose information is filtered by comparing it to the pose information of the map markers to be able to assign what marker is being detected. 
	
For the odometry transform calculations, it is assumed that the pose of the detected and static marker is the same. The relative difference between these transforms (map $\rightarrow$ static marker and detected marker -> odom) is calculated with matrix multiplication. The resulting difference is the rotation and translation vectors between map and odometry (the map -> odom transform).
       
For the data association of assigning markers, the transform between the detected marker and the static markers, are used looping over all the non-unique markers to find the best match. A pre-defined threshold is used to find a match, for the relative difference of the frames in yaw and then take their distance also into account when looking up the best matching marker. When there is no match, nothing is returned and if many matches are found, the best match is returned.
	
The problem described above is simplified by implementing two different frames, stabilized and footprint (of base link). These frames take care of the drone's pose relative to the odom frame with z, roll, and pitch. With this method, the odom frame is forced to be on the ground plane, only having to take into account x, y, and yaw coordinates (z, roll and pitch set to 0) when implementing the transform and therefore the odom frame having 3DOF relative to the map frame.
	
To be able to use the localization in the brain, which executes the path planning and exploration, a publisher tells the system that it is localized. With the calculations, for the map -> odom transform, a function was defined that uses the publisher to publish a boolean set to True, which is used in the brain to activate the planner. The calculated transform is then used in the Kalman filter, which smooths out the information. A separate node then takes the output from the Kalman filter and publishes the transforms continuously.
The localization system can also use 6D pose information from the perception system. This part is similar to the aruco transform implementation, with a new map -> odom publisher to do the comparison of a detected sign vs the static one read from the map. Filtering was made for the difference in yaw and the translation between the detected sign and the static one for the map -> odom transform being considered good enough to be broadcasted the as the pose information from perception was quite off even though the detection "matched" the map.


#### Planning
The strategy to find intruders, is an implementation of a Next Best View algorithm. With the drone's current position (available by being localized) a new goal point is generated with an explorer. The explorer keeps track of where Crazyflie has already been with an occupancy grid. Based on the information of where Crazyflie has already been and its current position the explorer generates a "next best view" point, a point with as much non-visited area as possible. This goal point is sent to our RRT planner which generates a path to that point. With this method, the drone explores the whole map to find intruders. At every goal point it can reach, the drone takes a 360° yaw rotation to explore everything around every reached point (not every point in the path to that point). The tracking of the visited area is visualized in RViz. When 95% of the map is explored the occupancy grid resets. The explored area is set to 0, and a new exploration trip sets off so that the drone can keep on flying forever, looking for intruders. If Crazyflie loses its localization (not localized) or if the localization is unstable, the drone will not able to reach the goal point due to its pose information being wrong. Therefore it was really important to make the map -> odom transform as stable as possible so the explorer and path planner can work without troubles.
