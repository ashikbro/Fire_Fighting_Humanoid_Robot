import threading
import time
from automation.sensor_manager import SensorManager
from automation.navigation import NavigationController
from alerts.alert_manager import AlertManager

class TaskScheduler:
    def __init__(self):
        self.sensor_manager = SensorManager()
        self.navigation_controller = NavigationController()
        self.alert_manager = AlertManager("sender@example.com", "password", "receiver@example.com")
        self.running = False

    def sensor_task(self):
        while self.running:
            data = self.sensor_manager.poll_sensors()
            print(f"[Sensor Task] Scheduled Sensor Data: {data}")
            time.sleep(10)  # sensor polling interval

    def navigation_task(self):
        while self.running:
            print("[Navigation Task] Executing navigation step...")
            self.navigation_controller.navigate()
            print("[Navigation Task] Navigation step completed.")
            time.sleep(5)  # navigation decision interval

    def alert_task(self):
        while self.running:
            print("[Alert Task] Checking for alerts...")
            self.alert_manager.check_and_send_alert()
            print("[Alert Task] Alert check completed.")
            time.sleep(300)  # alert check interval

    def anomaly_detection_task(self):
        import src.anomaly_detection as anomaly_detection
        while self.running:
            print("[Anomaly Detection Task] Running anomaly detection on sensor data...")
            # Assuming sensor data is logged in alerts/prediction_logs.csv or similar
            data_path = "data/fire_data_bangladesh.csv"
            anomaly_detection.detect_anomalies(data_path)
            print("[Anomaly Detection Task] Anomaly detection completed.")
            time.sleep(600)  # run every 10 minutes

    def voice_command_task(self):
        from alerts.voice_command import VoiceCommandInterface
        nav_controller = self.navigation_controller
        vci = VoiceCommandInterface(nav_controller)
        vci.start()
        try:
            while self.running:
                time.sleep(0.1)
        except KeyboardInterrupt:
            vci.stop()

    def predictive_maintenance_task(self):
        from src.predictive_maintenance import PredictiveMaintenance
        pm = PredictiveMaintenance()
        pm.train_model()
        while self.running:
            sensor_data = self.sensor_manager.poll_sensors()
            time_to_failure = pm.predict_maintenance(sensor_data)
            print(f"[Predictive Maintenance Task] Predicted time to failure: {time_to_failure:.2f} units")
            if time_to_failure < 10:  # threshold for alert
                print("[Predictive Maintenance Task] Maintenance needed soon!")
            time.sleep(600)  # run every 10 minutes

    def fire_suppression_task(self):
        from automation.fire_suppression import FireSuppressionController
        fsc = FireSuppressionController(self.alert_manager.actuator_manager, self.navigation_controller, self.alert_manager)
        while self.running:
            # For demo, get fire severity from some source, here we simulate
            fire_severity = "High"  # This should be replaced with actual prediction input
            fsc.evaluate_fire_severity(fire_severity)
            time.sleep(60)  # check every minute

    def start(self):
        self.running = True
        self.sensor_thread = threading.Thread(target=self.sensor_task)
        self.navigation_thread = threading.Thread(target=self.navigation_task)
        self.alert_thread = threading.Thread(target=self.alert_task)
        self.anomaly_thread = threading.Thread(target=self.anomaly_detection_task)
        self.voice_command_thread = threading.Thread(target=self.voice_command_task)
        self.predictive_maintenance_thread = threading.Thread(target=self.predictive_maintenance_task)
        self.fire_suppression_thread = threading.Thread(target=self.fire_suppression_task)
        self.sensor_thread.start()
        self.navigation_thread.start()
        self.alert_thread.start()
        self.anomaly_thread.start()
        self.voice_command_thread.start()
        self.predictive_maintenance_thread.start()
        self.fire_suppression_thread.start()

    def stop(self):
        self.running = False
        self.sensor_thread.join()
        self.navigation_thread.join()
        self.alert_thread.join()
        self.anomaly_thread.join()
        self.voice_command_thread.join()
        self.predictive_maintenance_thread.join()
        self.fire_suppression_thread.join()

if __name__ == "__main__":
    scheduler = TaskScheduler()
    try:
        scheduler.start()
    except KeyboardInterrupt:
        scheduler.stop()
        print("Task Scheduler stopped.")
