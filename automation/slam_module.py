import numpy as np

class SLAMModule:
    """
    Basic SLAM (Simultaneous Localization and Mapping) module implementation using a grid map and
    simple position update based on sensor data.
    """

    def __init__(self, map_size=(100, 100), resolution=1.0):
        self.map_size = map_size
        self.resolution = resolution
        self.map = np.zeros(map_size)  # 2D occupancy grid map
        self.position = np.array([map_size[0] // 2, map_size[1] // 2], dtype=float)  # Start at center
        self.orientation = 0.0  # Robot's orientation in radians

    def update(self, sensor_data):
        """
        Update the map and robot position based on sensor data.
        :param sensor_data: fused sensor data from sensor fusion module
        """
        # Improved SLAM update using a simple occupancy grid and probabilistic update

        # Parameters for occupancy update
        prob_hit = 0.7
        prob_miss = 0.4
        log_odds_hit = np.log(prob_hit / (1 - prob_hit))
        log_odds_miss = np.log(prob_miss / (1 - prob_miss))

        # Initialize log-odds map if not present
        if not hasattr(self, 'log_odds_map'):
            self.log_odds_map = np.zeros(self.map_size)

        # Update log-odds based on sensor data
        for i, distance in enumerate(sensor_data):
            angle = self.orientation + (i - len(sensor_data) / 2) * (np.pi / len(sensor_data))
            x = int(self.position[0] + distance * np.cos(angle) / self.resolution)
            y = int(self.position[1] + distance * np.sin(angle) / self.resolution)
            if 0 <= x < self.map_size[0] and 0 <= y < self.map_size[1]:
                self.log_odds_map[x, y] += log_odds_hit
                # Update neighboring cells as free space
                for dx in range(-1, 2):
                    for dy in range(-1, 2):
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < self.map_size[0] and 0 <= ny < self.map_size[1]:
                            self.log_odds_map[nx, ny] += log_odds_miss

        # Convert log-odds to probability map
        self.map = 1 - 1 / (1 + np.exp(self.log_odds_map))

        # Update position estimate (placeholder with noise)
        noise = np.random.normal(0, 0.01, 2)
        self.position += np.array([0.1 * np.cos(self.orientation), 0.1 * np.sin(self.orientation)]) + noise

    def get_map(self):
        """
        Return the current map.
        """
        return self.map

    def visualize_map(self):
        """
        Visualize the occupancy grid map using matplotlib.
        """
        import matplotlib.pyplot as plt

        plt.imshow(self.map, cmap='gray', origin='lower')
        plt.title('SLAM Occupancy Grid Map')
        plt.colorbar(label='Occupancy Probability')
        plt.xlabel('X')
        plt.ylabel('Y')
        plt.show()

    def get_position(self):
        """
        Return the current estimated position and orientation.
        """
        return self.position, self.orientation
