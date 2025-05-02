class FireSuppressionController:
    def __init__(self, actuator_manager, navigation_controller, alert_manager):
        self.actuator_manager = actuator_manager
        self.navigation_controller = navigation_controller
        self.alert_manager = alert_manager
        self.suppression_active = False

    def evaluate_fire_severity(self, fire_severity):
        # Simple logic: activate suppression if severity is high
        if fire_severity == "High" and not self.suppression_active:
            self.activate_suppression()
        elif fire_severity != "High" and self.suppression_active:
            self.deactivate_suppression()

    def activate_suppression(self):
        print("Activating fire suppression system.")
        self.actuator_manager.activate_water_pump(10)  # activate water pump for 10 seconds
        self.suppression_active = True
        self.alert_manager.send_alert("Fire suppression activated due to high fire severity.")

    def deactivate_suppression(self):
        print("Deactivating fire suppression system.")
        self.actuator_manager.stop_all()
        self.suppression_active = False
        self.alert_manager.send_alert("Fire suppression deactivated.")

    def suppression_task(self):
        # This method can be called periodically or triggered by events
        # For demo, placeholder to show usage
        pass

if __name__ == "__main__":
    from automation.actuator_manager import ActuatorManager
    from automation.navigation import NavigationController
    from alerts.alert_manager import AlertManager

    actuator_manager = ActuatorManager()
    navigation_controller = NavigationController()
    alert_manager = AlertManager("sender@example.com", "password", "receiver@example.com")

    fsc = FireSuppressionController(actuator_manager, navigation_controller, alert_manager)
    # Example usage
    fsc.evaluate_fire_severity("High")
