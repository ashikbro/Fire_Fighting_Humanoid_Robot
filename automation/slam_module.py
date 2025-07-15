import numpy as np
from filterpy.kalman import ExtendedKalmanFilter
from filterpy.common import Q_discrete_white_noise

class SLAMModule:
    def __init__(self, map_size=100, resolution=0.1, sensor_noise=0.1):
        self.map_size = map_size
        self.resolution = resolution
        # Use log-odds for a probabilistic occupancy grid
        self.grid_map_log_odds = np.zeros((map_size, map_size), dtype=np.float32)
        self.log_odds_occ = np.log(0.85 / (1 - 0.85))  # Probability of occupancy
        self.log_odds_free = np.log(0.15 / (1 - 0.15))  # Probability of being free
        
        # Initialize EKF for sensor fusion
        self.ekf = ExtendedKalmanFilter(dim_x=3, dim_z=3)
        map_center_world_x = map_size * resolution / 2
        map_center_world_y = map_size * resolution / 2
        self.ekf.x = np.array([map_center_world_x, map_center_world_y, 0.0])  # [x, y, theta] in world coordinates
        self.ekf.F = np.eye(3)  # State transition matrix
        self.ekf.R = np.diag([sensor_noise**2, sensor_noise**2, np.deg2rad(1)**2])  # Measurement noise
        self.ekf.Q = Q_discrete_white_noise(dim=3, dt=1.0, var=0.01)  # Process noise
        self.ekf.P = np.eye(3) * 500  # Covariance matrix

    def Hx(self, x):
        """Measurement function"""
        return x

    def H_of(self, x):
        """Jacobian of measurement function"""
        return np.eye(3)

    def update(self, odometry, lidar_scan):
        """
        Update the map and robot pose using EKF for sensor fusion.
        """
        # Predict step
        self.ekf.predict()

        # Update step with odometry
        self.ekf.update(odometry, self.H_of, self.Hx)

        # Update map with lidar scan
        self._update_map_log_odds(self.ekf.x, lidar_scan)

    def _update_map_log_odds(self, pose, lidar_scan):
        """
        Update the occupancy grid map using log-odds based on the robot's pose and lidar scan.
        """
        x, y, theta = pose
        for angle, dist in lidar_scan:
            if dist == np.inf:
                continue
            
            # Calculate world coordinates of the obstacle
            world_angle = theta + np.deg2rad(angle)
            obs_x = x + dist * np.cos(world_angle)
            obs_y = y + dist * np.sin(world_angle)

            # Convert to map coordinates
            map_x = int(obs_x / self.resolution)
            map_y = int(obs_y / self.resolution)

            if 0 <= map_x < self.map_size and 0 <= map_y < self.map_size:
                # Increase the log-odds for the cell where an obstacle was detected
                self.grid_map_log_odds[map_x, map_y] += self.log_odds_occ

            # Update cells along the lidar beam as free
            # This part requires a line-drawing algorithm (e.g., Bresenham's)
            # For simplicity, we'll skip the full implementation here but acknowledge its importance.

    def get_map(self):
        # Convert log-odds to probabilities
        prob_map = 1 - 1 / (1 + np.exp(self.grid_map_log_odds))
        return (prob_map > 0.7).astype(np.int8)  # Threshold to get a binary map

    def get_pose(self):
        return self.ekf.x
