import logging

class ActuatorController:
    """
    Control module for robot actuators such as motors, water pumps, and extinguishers.
    """

    def __init__(self):
        # Initialize actuator states
        self.motors_state = "stopped"
        self.water_pump_state = "off"
        self.extinguisher_state = "off"

    def move_forward(self, speed=1.0):
        """
        Move the robot forward at the specified speed.
        """
        try:
            self.motors_state = f"moving forward at speed {speed}"
            logging.info(self.motors_state)
            # Simulated hardware control code
            print(f"[Simulated] Motors moving forward at speed {speed}")
        except Exception as e:
            logging.error(f"Error moving forward: {e}")

    def move_backward(self, speed=1.0):
        """
        Move the robot backward at the specified speed.
        """
        try:
            self.motors_state = f"moving backward at speed {speed}"
            logging.info(self.motors_state)
            # Simulated hardware control code
            print(f"[Simulated] Motors moving backward at speed {speed}")
        except Exception as e:
            logging.error(f"Error moving backward: {e}")

    def turn_left(self, angle=90):
        """
        Turn the robot left by the specified angle.
        """
        try:
            self.motors_state = f"turning left by {angle} degrees"
            logging.info(self.motors_state)
            # Simulated hardware control code
            print(f"[Simulated] Motors turning left by {angle} degrees")
        except Exception as e:
            logging.error(f"Error turning left: {e}")

    def turn_right(self, angle=90):
        """
        Turn the robot right by the specified angle.
        """
        try:
            self.motors_state = f"turning right by {angle} degrees"
            logging.info(self.motors_state)
            # Simulated hardware control code
            print(f"[Simulated] Motors turning right by {angle} degrees")
        except Exception as e:
            logging.error(f"Error turning right: {e}")

    def stop(self):
        """
        Stop all robot movement.
        """
        try:
            self.motors_state = "stopped"
            logging.info(self.motors_state)
            # Simulated hardware control code
            print("[Simulated] Motors stopped")
        except Exception as e:
            logging.error(f"Error stopping motors: {e}")

    def activate_water_pump(self):
        """
        Activate the water pump for fire suppression.
        """
        try:
            self.water_pump_state = "on"
            logging.info("Water pump activated")
            # Simulated hardware control code
            print("[Simulated] Water pump activated")
        except Exception as e:
            logging.error(f"Error activating water pump: {e}")

    def deactivate_water_pump(self):
        """
        Deactivate the water pump.
        """
        try:
            self.water_pump_state = "off"
            logging.info("Water pump deactivated")
            # Simulated hardware control code
            print("[Simulated] Water pump deactivated")
        except Exception as e:
            logging.error(f"Error deactivating water pump: {e}")

    def activate_extinguisher(self):
        """
        Activate the fire extinguisher.
        """
        try:
            self.extinguisher_state = "on"
            logging.info("Extinguisher activated")
            # Simulated hardware control code
            print("[Simulated] Extinguisher activated")
        except Exception as e:
            logging.error(f"Error activating extinguisher: {e}")

    def deactivate_extinguisher(self):
        """
        Deactivate the fire extinguisher.
        """
        try:
            self.extinguisher_state = "off"
            logging.info("Extinguisher deactivated")
            # Simulated hardware control code
            print("[Simulated] Extinguisher deactivated")
        except Exception as e:
            logging.error(f"Error deactivating extinguisher: {e}")
