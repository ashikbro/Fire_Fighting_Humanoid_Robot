import csv
import os
from datetime import datetime

LOG_FILE = "alerts/prediction_logs.csv"

def log_prediction(severity, sensor_data):
    file_exists = os.path.isfile(LOG_FILE)
    with open(LOG_FILE, mode='a', newline='') as file:
        writer = csv.writer(file)
        if not file_exists:
            writer.writerow(["Timestamp", "FireSeverity", "Temperature", "SmokeDensity", "GasLevel", "Humidity"])
        writer.writerow([
            datetime.now().isoformat(),
            severity,
            sensor_data.get("temperature", ""),
            sensor_data.get("smoke_density", ""),
            sensor_data.get("gas_level", ""),
            sensor_data.get("humidity", "")
        ])

if __name__ == "__main__":
    # Example usage
    sample_severity = "High"
    sample_sensor_data = {"temperature": 80, "smoke_density": 900, "gas_level": 300, "humidity": 20}
    log_prediction(sample_severity, sample_sensor_data)
