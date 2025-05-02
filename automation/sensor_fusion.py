import numpy as np

class SensorFusion:
    """
    Sensor fusion module to combine data from multiple sensors such as LIDAR, ultrasonic, and cameras
    for robust environment perception.
    """

    def __init__(self):
        # Initialize sensor data placeholders
        self.lidar_data = None
        self.ultrasonic_data = None
        self.camera_data = None

    def update_lidar(self, data):
        """
        Update LIDAR sensor data.
        :param data: numpy array or list of distance measurements
        """
        self.lidar_data = np.array(data)

    def update_ultrasonic(self, data):
        """
        Update ultrasonic sensor data.
        :param data: numpy array or list of distance measurements
        """
        self.ultrasonic_data = np.array(data)

    def update_camera(self, data):
        """
        Update camera sensor data.
        :param data: processed camera data (e.g., object detections, depth map)
        """
        self.camera_data = data

    def fuse(self):
        """
        Fuse the sensor data to create a comprehensive environmental model.
        This is a placeholder for fusion logic, which can be extended with
        Kalman filters, particle filters, or deep learning-based fusion.
        :return: fused sensor data representation
        """
        # Simple example: concatenate available sensor data
        fused_data = []

        if self.lidar_data is not None:
            fused_data.append(self.lidar_data.flatten())

        if self.ultrasonic_data is not None:
            fused_data.append(self.ultrasonic_data.flatten())

        if self.camera_data is not None:
            # Assuming camera_data is already a feature vector
            fused_data.append(np.array(self.camera_data).flatten())

        if fused_data:
            return np.concatenate(fused_data)
        else:
            return np.array([])  # No data available
