import numpy as np

class LidarSimulator:
    """
    A class to simulate Lidar data based on a 2D map.
    """
    def __init__(self, map_data: np.ndarray, resolution: float, num_beams: int = 180, max_range: float = 10.0):
        """
        Initializes the LidarSimulator.
        
        Args:
            map_data: The 2D map of the environment.
            resolution: The resolution of the map (meters per pixel).
            num_beams: The number of Lidar beams to simulate.
            max_range: The maximum range of the Lidar sensor (in meters).
        """
        self.map_data = map_data
        self.resolution = resolution
        self.num_beams = num_beams
        self.max_range_pixels = max_range / resolution
        self.angles = np.linspace(-np.pi / 2, np.pi / 2, num_beams)

    def get_scan(self, robot_pose: tuple) -> np.ndarray:
        """
        Generates a simulated Lidar scan from the robot's current pose.
        
        Args:
            robot_pose: The robot's current pose (x, y, theta) in world coordinates.
            
        Returns:
            An array of Lidar ranges in meters.
        """
        robot_x, robot_y, robot_theta = robot_pose
        ranges = np.full(self.num_beams, self.max_range_pixels * self.resolution)
        
        for i, angle in enumerate(self.angles):
            scan_angle = robot_theta + angle
            
            for r in range(1, int(self.max_range_pixels)):
                x = robot_x + r * np.cos(scan_angle)
                y = robot_y + r * np.sin(scan_angle)
                
                map_x = int(x / self.resolution)
                map_y = int(y / self.resolution)
                
                if not (0 <= map_x < self.map_data.shape[1] and 0 <= map_y < self.map_data.shape[0]):
                    break
                
                if self.map_data[map_y, map_x] == 1: # Obstacle
                    ranges[i] = r * self.resolution
                    break
                    
        return ranges