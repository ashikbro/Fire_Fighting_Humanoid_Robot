import threading
import time
import logging
from automation.safety_monitor import SafetyMonitor

class SafetyMonitorIntegration:
    def __init__(self, battery_threshold=20, check_interval=5):
        self.safety_monitor = SafetyMonitor(battery_threshold=battery_threshold, check_interval=check_interval)
        self.monitor_thread = None
        self.running = False

    def start(self):
        self.running = True
        self.safety_monitor.start()
        self.monitor_thread = threading.Thread(target=self._monitor_loop)
        self.monitor_thread.start()
        logging.info("Safety monitor integration started.")

    def stop(self):
        self.running = False
        self.safety_monitor.stop()
        if self.monitor_thread:
            self.monitor_thread.join()
        logging.info("Safety monitor integration stopped.")

    def _monitor_loop(self):
        while self.running:
            # Example: check battery level from sensor interface or system API
            battery_level = self.get_battery_level()
            self.safety_monitor.check_battery(battery_level)
            # Reset watchdog periodically
            self.safety_monitor.reset_watchdog()
            time.sleep(self.safety_monitor.check_interval)

    def get_battery_level(self):
        # Placeholder: replace with actual battery reading code
        return 100  # Assume full battery for now

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    safety_integration = SafetyMonitorIntegration()
    safety_integration.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        safety_integration.stop()
