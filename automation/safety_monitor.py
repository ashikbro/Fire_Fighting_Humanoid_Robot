import threading
import time
import logging

class SafetyMonitor:
    def __init__(self, battery_threshold=20, watchdog_timeout=10):
        self.battery_threshold = battery_threshold
        self.watchdog_timeout = watchdog_timeout
        self.last_heartbeat = time.time()
        self.watchdog_thread = threading.Thread(target=self._watchdog_loop)
        self.running = False
        self.battery_level = 100  # Placeholder for actual battery level reading

    def start(self):
        self.running = True
        self.watchdog_thread.start()
        logging.info("Safety monitor started.")

    def stop(self):
        self.running = False
        self.watchdog_thread.join()
        logging.info("Safety monitor stopped.")

    def heartbeat(self):
        self.last_heartbeat = time.time()
        logging.debug("Heartbeat received.")

    def _watchdog_loop(self):
        while self.running:
            time_since_heartbeat = time.time() - self.last_heartbeat
            if time_since_heartbeat > self.watchdog_timeout:
                logging.error("Watchdog timeout exceeded. System reset triggered.")
                self.reset_system()
            self.check_battery()
            time.sleep(1)

    def check_battery(self):
        # Placeholder for actual battery level check
        if self.battery_level < self.battery_threshold:
            logging.warning(f"Battery level low: {self.battery_level}%. Initiating auto-shutdown.")
            self.auto_shutdown()

    def reset_system(self):
        logging.info("Performing system reset...")
        # Placeholder for actual reset logic

    def auto_shutdown(self):
        logging.info("Performing auto-shutdown due to low battery...")
        # Placeholder for actual shutdown logic

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    monitor = SafetyMonitor()
    monitor.start()
    try:
        while True:
            monitor.heartbeat()
            time.sleep(5)
    except KeyboardInterrupt:
        monitor.stop()
