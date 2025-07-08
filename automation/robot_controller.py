from automation.navigation import NavigationController
from automation.actuator_control import ActuatorController
import logging
from vision_fire_detection.fire_detection import FireDetection

class RobotController:
    """
    High-level controller integrating navigation, obstacle avoidance, actuator control,
    fire detection, and object detection for the firefighting humanoid robot.
    """

    def __init__(self):
        self.navigation = NavigationController()
        self.actuators = ActuatorController()
        self.current_fire_severity = None
        self.fire_location = None  # (x, y) coordinates of detected fire
        self.fire_detector = FireDetection(method='cnn', enable_object_detection=True)
        self.auto_patrol_enabled = False  # New attribute for Auto-Patrol mode

    def set_navigation_goal(self, x, y):
        self.navigation.set_goal(x, y)
        self.fire_location = (x, y)
        logging.info(f"Navigation goal set to fire location: {self.fire_location}")

    def update_sensor_data(self, lidar_data=None, ultrasonic_data=None, camera_data=None):
        self.navigation.update_sensors(lidar_data, ultrasonic_data, camera_data)
        if camera_data is not None:
            fire_detected = self.fire_detector.detect_fire(camera_data)
            if fire_detected:
                logging.info("Fire detected from camera data.")
                # For simplicity, assume fire location is current robot position
                current_pos = self.navigation.get_current_position()
                self.fire_location = current_pos
                # Example sensor data for severity prediction (replace with real sensor input)
                example_sensor_data = {
                    'Temperature': 35.0,
                    'SmokeDensity': 200.0,
                    'GasLevel': 50.0,
                    'Humidity': 40.0
                }
                severity = self.fire_detector.predict_fire_severity(example_sensor_data)
                if severity:
                    self.current_fire_severity = severity
                    self.set_navigation_goal(*self.fire_location)
                    self.perform_navigation()
                    self.activate_fire_suppression()

            detections = self.fire_detector.detect_objects(camera_data)
            if detections:
                logging.info(f"Objects detected: {[det['class_name'] for det in detections]}")

        # If Auto-Patrol mode is enabled, perform patrol behavior
        if self.auto_patrol_enabled:
            self.auto_patrol()

    def perform_navigation(self):
        try:
            if self.navigation.detect_obstacles():
                logging.warning("Obstacle detected! Stopping and activating avoidance maneuvers.")
                self.actuators.stop()
                # Simple avoidance maneuver: turn right and move forward a bit
                self.actuators.turn_right(angle=45)
                self.actuators.move_forward(speed=0.5)
                # After avoidance, replan path
                path = self.navigation.plan_path()
                if not path:
                    logging.warning("No path to goal after avoidance.")
                    self.actuators.stop()
                    return
            else:
                path = self.navigation.plan_path()
                if not path:
                    logging.warning("No path to goal.")
                    self.actuators.stop()
                    return

            for waypoint in path:
                # Calculate direction to waypoint and turn accordingly
                current_pos = self.navigation.get_current_position()
                direction = self.navigation.calculate_direction(current_pos, waypoint)
                if direction == "left":
                    self.actuators.turn_left(angle=15)
                elif direction == "right":
                    self.actuators.turn_right(angle=15)
                logging.info(f"Moving to waypoint: {waypoint}")
                self.actuators.move_forward(speed=1.0)
                # Add delay or sensor feedback here if needed
            self.actuators.stop()
        except Exception as e:
            logging.error(f"Error during navigation: {e}")
            self.actuators.stop()

    def auto_patrol(self):
        """
        Auto-Patrol mode: robot moves forward continuously and stops if obstacle detected.
        """
        if self.navigation.detect_obstacles():
            logging.info("Auto-Patrol: Obstacle detected, stopping.")
            self.actuators.stop()
        else:
            logging.info("Auto-Patrol: Path clear, moving forward.")
            self.actuators.move_forward(speed=1.0)

    def activate_fire_suppression(self):
        logging.info("Activating fire suppression system.")
        self.actuators.activate_water_pump()
        if self.current_fire_severity in ['high', 'critical']:
            self.actuators.activate_extinguisher()
            logging.info("Extinguisher activated due to high fire severity.")
        else:
            self.actuators.deactivate_extinguisher()
            logging.info("Extinguisher deactivated due to low fire severity.")

    def deactivate_fire_suppression(self):
        logging.info("Deactivating fire suppression system.")
        self.actuators.deactivate_water_pump()
        self.actuators.deactivate_extinguisher()

    def handle_fire_prediction(self, severity, fire_coords):
        """
        Handle fire severity prediction and trigger robot actions.
        :param severity: Predicted fire severity (e.g., 'low', 'medium', 'high', 'critical')
        :param fire_coords: Tuple (x, y) coordinates of fire location
        """
        logging.info(f"Received fire severity prediction: {severity} at location {fire_coords}")
        self.current_fire_severity = severity
        self.set_navigation_goal(*fire_coords)
        self.perform_navigation()
        self.activate_fire_suppression()
