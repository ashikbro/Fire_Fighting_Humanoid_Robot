import hardware_integration.sensor_interface as sensor_interface
from automation.sensor_fusion import SensorFusion
from src.anomaly_detection import AnomalyDetector
import numpy as np

class SensorFusionIntegration:
    def __init__(self):
        self.sensor_fusion = SensorFusion()
        self.anomaly_detector = AnomalyDetector()

    def update_and_fuse(self):
        # Read sensor data
        sensor_data = sensor_interface.get_all_sensor_data()

        # Update fusion module
        self.sensor_fusion.update_smoke(sensor_data.get("smoke_density"))
        self.sensor_fusion.update_gas(sensor_data.get("gas_level"))
        # For visual and thermal data, placeholders or integration with vision modules needed
        self.sensor_fusion.update_visual(None)  # To be updated with actual visual features
        self.sensor_fusion.update_thermal(None)  # To be updated with actual thermal data

        # Fuse data
        fused_data = self.sensor_fusion.fuse()

        # Detect anomalies
        if fused_data.size > 0:
            fused_data_reshaped = np.array(fused_data).reshape(1, -1)
            anomalies = self.anomaly_detector.predict(fused_data_reshaped)
            is_anomaly = anomalies[0]
        else:
            is_anomaly = False

        return fused_data, is_anomaly

if __name__ == "__main__":
    fusion_integration = SensorFusionIntegration()
    fused, anomaly = fusion_integration.update_and_fuse()
    print("Fused sensor data:", fused)
    print("Anomaly detected:", anomaly)
