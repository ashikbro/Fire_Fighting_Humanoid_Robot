class FireSuppression:
    def __init__(self):
        from automation.actuator_manager import ActuatorManager
        from alerts.alert_manager import AlertManager

        self.actuator_manager = ActuatorManager()
        self.alert_manager = AlertManager()
        self.suppression_active = False

    def suppress_fire(self, fire_severity):
        # Simple logic: activate suppression if severity is high or critical
        if fire_severity in ["high", "critical"] and not self.suppression_active:
            self.activate_suppression()
        elif fire_severity not in ["high", "critical"] and self.suppression_active:
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
    from alerts.alert_manager import AlertManager

    actuator_manager = ActuatorManager()
    alert_manager = AlertManager("sender@example.com", "password", "receiver@example.com")

    fsc = FireSuppression()
    # Example usage
    fsc.suppress_fire("high")
