import numpy as np

class SensorFusion:
    """
    Enhanced sensor fusion module to combine data from multiple sensors such as visual, thermal, smoke, and gas
    for robust fire detection with sensor redundancy and cross-validation.
    """

    def __init__(self, weights=None):
        # Initialize sensor data placeholders
        self.visual_data = None
        self.thermal_data = None
        self.smoke_data = None
        self.gas_data = None
        # Default weights for each sensor type if not provided
        self.weights = weights if weights is not None else {
            'visual': 1.0,
            'thermal': 1.0,
            'smoke': 1.0,
            'gas': 1.0
        }
        # Sensor redundancy data storage
        self.visual_data_backup = None
        self.thermal_data_backup = None

    def update_visual(self, data):
        """
        Update visual sensor data.
        :param data: processed visual data (e.g., image features, detections)
        """
        self.visual_data_backup = self.visual_data
        self.visual_data = self._normalize(np.array(data))

    def update_thermal(self, data):
        """
        Update thermal sensor data.
        :param data: processed thermal data (e.g., temperature map)
        """
        self.thermal_data_backup = self.thermal_data
        self.thermal_data = self._normalize(np.array(data))

    def update_smoke(self, data):
        """
        Update smoke sensor data.
        :param data: numeric or processed smoke sensor reading
        """
        self.smoke_data = self._normalize(np.array([data]))

    def update_gas(self, data):
        """
        Update gas sensor data.
        :param data: numeric or processed gas sensor reading
        """
        self.gas_data = self._normalize(np.array([data]))

    def _normalize(self, data):
        """
        Normalize data to zero mean and unit variance.
        """
        if data.size == 0:
            return data
        mean = np.mean(data)
        std = np.std(data)
        if std == 0:
            return data - mean
        return (data - mean) / std

    def fuse(self):
        """
        Fuse the sensor data to create a comprehensive fire hazard representation.
        Applies weights and handles missing data.
        Implements cross-validation between primary and backup sensors for redundancy.
        :return: fused sensor data representation as numpy array
        """
        fused_data = []

        # Cross-validate visual data with backup
        if self.visual_data is not None and self.visual_data_backup is not None:
            if np.allclose(self.visual_data, self.visual_data_backup, atol=0.1):
                fused_data.append(self.weights['visual'] * self.visual_data.flatten())
            else:
                # If discrepancy, use average or flag anomaly
                avg_visual = (self.visual_data + self.visual_data_backup) / 2
                fused_data.append(self.weights['visual'] * avg_visual.flatten())
        elif self.visual_data is not None:
            fused_data.append(self.weights['visual'] * self.visual_data.flatten())

        # Cross-validate thermal data with backup
        if self.thermal_data is not None and self.thermal_data_backup is not None:
            if np.allclose(self.thermal_data, self.thermal_data_backup, atol=0.1):
                fused_data.append(self.weights['thermal'] * self.thermal_data.flatten())
            else:
                avg_thermal = (self.thermal_data + self.thermal_data_backup) / 2
                fused_data.append(self.weights['thermal'] * avg_thermal.flatten())
        elif self.thermal_data is not None:
            fused_data.append(self.weights['thermal'] * self.thermal_data.flatten())

        if self.smoke_data is not None:
            fused_data.append(self.weights['smoke'] * self.smoke_data.flatten())

        if self.gas_data is not None:
            fused_data.append(self.weights['gas'] * self.gas_data.flatten())

        if fused_data:
            return np.concatenate(fused_data)
        else:
            return np.array([])  # No data available
