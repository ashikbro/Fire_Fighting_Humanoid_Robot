import logging
import numpy as np
from automation.navigation import NavigationController
from automation.slam_module import SLAMModule
from vision.object_detector import ObjectDetector
from vision.thermal_simulation import estimate_temperature_from_frame
from vision.fire_segmentation import FireSegmentation
from automation.fire_suppression import FireSuppression

class RobotController:
    """
    Advanced controller for the firefighting robot, integrating SLAM-based navigation
    and object detection.
    """

    def __init__(self, object_detector: ObjectDetector, patrol_waypoints=None, simulation_mode=True):
        self.slam = SLAMModule()
        self.navigation = NavigationController(self.slam)
        self.object_detector = object_detector
        self.fire_segmentation = FireSegmentation()
        self.fire_suppression = FireSuppression()
        self.current_fire_severity = None
        self.fire_location = None
        self.auto_patrol_enabled = False
        self.patrol_waypoints = patrol_waypoints if patrol_waypoints is not None else []
        self.current_waypoint_index = 0

    def set_navigation_goal(self, x, y):
        # Ensure the goal is within the map boundaries
        map_size = self.slam.map_size * self.slam.resolution
        x = np.clip(x, 0, map_size - 1)
        y = np.clip(y, 0, map_size - 1)
        
        self.navigation.set_goal(x, y)
        self.fire_location = (x, y)
        logging.info(f"Navigation goal set to fire location: ({x:.2f}, {y:.2f})")

    def update_vision_data(self, camera_frame):
        """
        Process a camera frame to detect fire and people, then take action.
        """
        detected_objects = self.object_detector.detect_objects(camera_frame)
        fire_detections = [obj for obj in detected_objects if obj['class_name'] == 'fire']
        person_detections = [obj for obj in detected_objects if obj['class_name'] == 'person']

        if person_detections:
            self.handle_person_detection(person_detections[0])
        elif fire_detections:
            self.handle_fire_detection(fire_detections[0], camera_frame)
        
        if self.auto_patrol_enabled:
            self.auto_patrol()

    def handle_fire_detection(self, fire_detection, camera_frame):
        """
        Handles the logic for responding to a fire detection.
        """
        bbox = fire_detection['bounding_box']
        
        # Estimate fire location
        fire_center_x = (bbox[0] + bbox[2]) / 2
        fire_world_x = self.slam.get_pose()[0] + 5 * (fire_center_x / 640 - 0.5)
        fire_world_y = self.slam.get_pose()[1] + 5
        self.fire_location = (fire_world_x, fire_world_y)
        
        # Estimate fire severity using thermal simulation
        estimated_temp = estimate_temperature_from_frame(camera_frame, bbox)
        self.current_fire_severity = self._estimate_fire_severity(fire_detection, estimated_temp, camera_frame)
        
        logging.info(f"Fire detected with severity: {self.current_fire_severity} at {estimated_temp:.2f}°C")
        self.set_navigation_goal(self.fire_location[0], self.fire_location[1])
        
        # Activate fire suppression system
        self.fire_suppression.suppress_fire(self.current_fire_severity)

    def handle_person_detection(self, person_detection):
        """
        Handles the logic for responding to a person detection.
        """
        logging.warning("Person detected! Stopping navigation for safety.")
        self.navigation.goal_position = None # Clear the goal to stop navigation

    def _estimate_fire_severity(self, fire_detection, temperature: float, camera_frame: np.ndarray):
        """
        Estimates fire severity based on confidence, size, and simulated temperature.
        """
        confidence = fire_detection['confidence']
        bbox = fire_detection['bounding_box']
        area = self.fire_segmentation.get_fire_area(camera_frame, bbox)

        # Define severity thresholds
        # Adjusted thresholds for the enhanced temperature model
        if temperature > 700 and confidence > 0.85 and area > 15000:
            return 'critical'
        elif temperature > 500 and confidence > 0.75 and area > 10000:
            return 'high'
        elif temperature > 350 and confidence > 0.65 and area > 7500:
            return 'medium'
        else:
            return 'low'

    def auto_patrol(self):
        """
        Auto-Patrol mode: the robot cycles through a predefined list of waypoints.
        """
        if not self.patrol_waypoints:
            logging.warning("No patrol waypoints defined.")
            return

        if self.navigation.is_goal_reached():
            # Move to the next waypoint
            self.current_waypoint_index = (self.current_waypoint_index + 1) % len(self.patrol_waypoints)
            next_waypoint = self.patrol_waypoints[self.current_waypoint_index]
            self.set_navigation_goal(next_waypoint[0], next_waypoint[1])
            logging.info(f"Patrolling to next waypoint: {next_waypoint}")
            self.navigation.navigate()


