import logging
import numpy as np
from automation.navigation import NavigationController
from automation.slam_module import SLAMModule
from vision.object_detector import ObjectDetector
from vision.thermal_simulation import estimate_temperature_from_frame
from vision.fire_segmentation import FireSegmentation

class RobotController:
    """
    Advanced controller for the firefighting robot, integrating SLAM-based navigation
    and object detection.
    """

    def __init__(self, object_detector, patrol_waypoints=None, simulation_mode=True):
        # Initialize missing components that were referenced but not imported
        from automation.actuator_manager import ActuatorManager
        self.actuator_manager = ActuatorManager()
        
        # Initialize SLAM module properly
        self.slam = SLAMModule(map_size=50, resolution=0.5)
        
        # Enhanced navigation with DWA
        self.navigation = NavigationController(self.slam)
        
        self.object_detector = object_detector
        self.fire_segmentation = FireSegmentation()
        
        # Initialize time series analysis for fire detection
        from automation.time_series_analysis import TimeSeriesFlameDetector
        self.flame_detector = TimeSeriesFlameDetector(window_size=5, threshold=0.6)
        
        from automation.fire_suppression import FireSuppression
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
        """Enhanced vision processing with time series analysis"""
        detected_objects = self.object_detector.detect_objects(camera_frame)
        fire_detections = [obj for obj in detected_objects if obj['class_name'] == 'fire']
        person_detections = [obj for obj in detected_objects if obj['class_name'] == 'person']
        
        # Use time series analysis for fire confirmation
        fire_detected = len(fire_detections) > 0
        self.flame_detector.add_detection(fire_detected)
        confirmed_fire = self.flame_detector.is_fire_confirmed()
        
        if person_detections:
            self.handle_person_detection(person_detections[0])
        elif confirmed_fire and fire_detections:
            self.handle_fire_detection(fire_detections[0], camera_frame)
        
        if self.auto_patrol_enabled:
            self.auto_patrol()

    def handle_fire_detection(self, fire_detection, camera_frame):
        """Enhanced fire detection with better location estimation"""
        bbox = fire_detection['bounding_box']
        
        # Advanced fire analysis with semantic segmentation
        fire_mask = self.fire_segmentation.get_fire_mask(camera_frame, bbox)
        fire_area = self.fire_segmentation.get_fire_area(fire_mask)
        
        # Estimate fire location using camera geometry
        fire_center_x = (bbox[0] + bbox[2]) / 2
        fire_center_y = (bbox[1] + bbox[3]) / 2
        
        # Simple depth estimation based on bounding box size
        bbox_area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
        estimated_depth = max(2.0, min(10.0, 50000 / bbox_area))  # Inverse relationship
        
        try:
            pose_x, pose_y, pose_theta = self.slam.get_pose()
            
            # Convert screen coordinates to world coordinates
            camera_angle = (fire_center_x / camera_frame.shape[1] - 0.5) * np.pi/3  # Assume 60° FOV
            world_angle = pose_theta + camera_angle
            
            fire_world_x = pose_x + estimated_depth * np.cos(world_angle)
            fire_world_y = pose_y + estimated_depth * np.sin(world_angle)
            self.fire_location = (fire_world_x, fire_world_y)
            
            logging.info(f"Fire located at world coordinates: ({fire_world_x:.2f}, {fire_world_y:.2f})")
            
        except Exception as e:
            logging.error(f"Error estimating fire location: {e}")
            self.fire_location = None
        
        # Estimate fire severity using thermal simulation and precise area
        try:
            estimated_temp = estimate_temperature_from_frame(camera_frame, bbox)
            self.current_fire_severity = self._estimate_fire_severity(fire_detection, estimated_temp, fire_area)
        except Exception as e:
            logging.error(f"Error estimating fire severity: {e}")
            self.current_fire_severity = 'low'
        
        logging.info(f"Fire detected with severity: {self.current_fire_severity} at {estimated_temp:.2f}°C")
        if self.fire_location:
            self.set_navigation_goal(self.fire_location[0], self.fire_location[1])
        
        # Activate fire suppression system
        self.fire_suppression.suppress_fire(self.current_fire_severity)

    def handle_person_detection(self, person_detection):
        """
        Handles the logic for responding to a person detection.
        """
        logging.warning("Person detected! Stopping navigation for safety.")
        self.navigation.goal_position = None # Clear the goal to stop navigation

    def _estimate_fire_severity(self, fire_detection, temperature: float, fire_area: int):
        """
        Estimates fire severity based on confidence, precise area from segmentation, and simulated temperature.
        """
        confidence = fire_detection['confidence']

        # Define severity thresholds using the more accurate fire area
        if temperature > 700 and confidence > 0.85 and fire_area > 12000:
            return 'critical'
        elif temperature > 500 and confidence > 0.75 and fire_area > 8000:
            return 'high'
        elif temperature > 350 and confidence > 0.65 and fire_area > 5000:
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


