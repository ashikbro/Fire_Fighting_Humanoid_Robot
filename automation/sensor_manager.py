import time
from hardware_integration import sensor_interface

class SensorManager:
    def __init__(self, poll_interval=1.0):
        self.poll_interval = poll_interval  # seconds
        self.latest_data = None

    def poll_sensors(self):
        self.latest_data = sensor_interface.get_all_sensor_data()
        return self.latest_data

    def start_polling(self):
        while True:
            data = self.poll_sensors()
            print(f"Sensor Data: {data}")
            time.sleep(self.poll_interval)

if __name__ == "__main__":
    sm = SensorManager()
    sm.start_polling()
