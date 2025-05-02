from automation.navigation import NavigationController
from automation.actuator_control import ActuatorController

class RobotController:
    """
    High-level controller integrating navigation, obstacle avoidance, and actuator control
    for the firefighting humanoid robot.
    """

    def __init__(self):
        self.navigation = NavigationController()
        self.actuators = ActuatorController()

    def set_navigation_goal(self, x, y):
        self.navigation.set_goal(x, y)

    def update_sensor_data(self, lidar_data=None, ultrasonic_data=None, camera_data=None):
        self.navigation.update_sensors(lidar_data, ultrasonic_data, camera_data)

    def perform_navigation(self):
        if self.navigation.detect_obstacles():
            print("Obstacle detected! Stopping and activating avoidance maneuvers.")
            self.actuators.stop()
            # TODO: Implement avoidance maneuvers or path replanning
        else:
            path = self.navigation.plan_path()
            if not path:
                print("No path to goal.")
                self.actuators.stop()
                return
            for waypoint in path:
                # Move towards waypoint
                print(f"Moving to waypoint: {waypoint}")
                self.actuators.move_forward()
                # TODO: Add logic to turn and adjust position based on waypoint
            self.actuators.stop()

    def activate_fire_suppression(self):
        print("Activating fire suppression system.")
        self.actuators.activate_water_pump()
        # TODO: Add logic to control extinguisher if needed

    def deactivate_fire_suppression(self):
        print("Deactivating fire suppression system.")
        self.actuators.deactivate_water_pump()
        self.actuators.deactivate_extinguisher()
