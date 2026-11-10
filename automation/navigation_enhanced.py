import numpy as np
import heapq
import logging
from automation.sensor_fusion import SensorFusion

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class NavigationEnhanced:
    """
    Enhanced navigation controller with A* path planning and obstacle avoidance.
    """

    def __init__(self, grid_size=(20, 20), resolution=1.0, max_range=10.0,
                 ultrasonic_fov=np.pi / 2):
        """
        :param grid_size: (nx, ny) occupancy grid dimensions, indexed grid[x, y].
        :param resolution: metres per grid cell; range readings are divided by
            this to convert them into cell offsets.
        :param max_range: readings at or beyond this distance (metres) are
            treated as "no return" and do not mark an obstacle.
        :param ultrasonic_fov: total angular spread (radians) of the
            ultrasonic array, centred on the robot's heading.
        """
        self.sensor_fusion = SensorFusion()
        self.grid_size = grid_size
        self.resolution = float(resolution)
        self.max_range = float(max_range)
        self.ultrasonic_fov = float(ultrasonic_fov)
        self.current_position = (0, 0)
        self.heading = 0.0  # radians, 0 = +x axis, counter-clockwise positive
        self.goal_position = None
        self.grid = np.zeros(grid_size)  # 0: free, 1: obstacle

    def set_goal(self, x, y):
        self.goal_position = (int(x), int(y))
        logging.info(f"Goal position set to: {self.goal_position}")

    def update_sensors(self, lidar_data=None, ultrasonic_data=None, camera_data=None):
        if lidar_data is not None:
            self.sensor_fusion.update_lidar(lidar_data)
        if ultrasonic_data is not None:
            self.sensor_fusion.update_ultrasonic(ultrasonic_data)
        if camera_data is not None:
            self.sensor_fusion.update_camera(camera_data)
        logging.info("Sensor data updated in sensor fusion module.")
        self.update_grid_with_obstacles()

    @staticmethod
    def lidar_angles(n, heading=0.0):
        """Bearings for an n-beam LIDAR sweep evenly covering 360 degrees,
        starting at the robot's heading."""
        return heading + 2 * np.pi * np.arange(n) / n

    @staticmethod
    def ultrasonic_angles(n, heading=0.0, fov=np.pi / 2):
        """Bearings for n ultrasonic sensors spread evenly across `fov`,
        centred on the robot's heading."""
        if n == 1:
            return np.array([heading])
        return heading + np.linspace(-fov / 2, fov / 2, n)

    def ranges_to_cells(self, ranges, angles):
        """
        Convert range readings (metres) at the given bearings into grid cells
        relative to `current_position`. Readings that are non-finite,
        non-positive, at/beyond `max_range`, outside the grid, or that land on
        the robot's own cell are dropped.
        :return: set of (x, y) integer cells
        """
        ranges = np.asarray(ranges, dtype=float).ravel()
        angles = np.asarray(angles, dtype=float).ravel()
        if ranges.shape != angles.shape:
            raise ValueError("ranges and angles must have the same length")

        valid = np.isfinite(ranges) & (ranges > 0) & (ranges < self.max_range)
        ranges, angles = ranges[valid], angles[valid]

        x0, y0 = self.current_position
        xs = np.rint(x0 + ranges * np.cos(angles) / self.resolution).astype(int)
        ys = np.rint(y0 + ranges * np.sin(angles) / self.resolution).astype(int)

        start = (int(x0), int(y0))
        cells = set()
        for x, y in zip(xs, ys):
            cell = (int(x), int(y))
            if cell == start:
                continue
            if 0 <= cell[0] < self.grid_size[0] and 0 <= cell[1] < self.grid_size[1]:
                cells.add(cell)
        return cells

    def update_grid_with_obstacles(self):
        """
        Rebuild the occupancy grid from the latest range sensor readings.

        SensorFusion.fuse() returns a flat vector of concatenated readings, which
        loses which sensor (and therefore which bearing) each value came from,
        and mixes in non-range camera features. So obstacle geometry is derived
        from the per-sensor range arrays held by the fusion module instead:
        LIDAR beams are assumed to sweep 360 degrees evenly from the heading,
        ultrasonic sensors to spread across `ultrasonic_fov` around the heading.
        Camera data is not a range measurement and is not projected.
        """
        self.grid = np.zeros(self.grid_size)
        cells = set()

        lidar = self.sensor_fusion.lidar_data
        if lidar is not None and lidar.size:
            cells |= self.ranges_to_cells(lidar, self.lidar_angles(lidar.size, self.heading))

        ultrasonic = self.sensor_fusion.ultrasonic_data
        if ultrasonic is not None and ultrasonic.size:
            cells |= self.ranges_to_cells(
                ultrasonic,
                self.ultrasonic_angles(ultrasonic.size, self.heading, self.ultrasonic_fov),
            )

        for x, y in cells:
            self.grid[x, y] = 1
        logging.info(f"Grid updated with {len(cells)} obstacle cells.")

    def heuristic(self, a, b):
        # Manhattan distance heuristic
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    def neighbors(self, node):
        dirs = [(1,0), (-1,0), (0,1), (0,-1)]
        result = []
        for d in dirs:
            neighbor = (node[0] + d[0], node[1] + d[1])
            if 0 <= neighbor[0] < self.grid_size[0] and 0 <= neighbor[1] < self.grid_size[1]:
                if self.grid[neighbor[0], neighbor[1]] == 0:
                    result.append(neighbor)
        return result

    def a_star_search(self):
        if self.goal_position is None:
            logging.warning("Goal position not set. Cannot perform path planning.")
            return []

        start = (int(self.current_position[0]), int(self.current_position[1]))
        goal = self.goal_position

        frontier = []
        heapq.heappush(frontier, (0, start))
        came_from = {}
        cost_so_far = {}
        came_from[start] = None
        cost_so_far[start] = 0

        while frontier:
            current = heapq.heappop(frontier)[1]

            if current == goal:
                break

            for next_node in self.neighbors(current):
                new_cost = cost_so_far[current] + 1
                if next_node not in cost_so_far or new_cost < cost_so_far[next_node]:
                    cost_so_far[next_node] = new_cost
                    priority = new_cost + self.heuristic(goal, next_node)
                    heapq.heappush(frontier, (priority, next_node))
                    came_from[next_node] = current

        # Reconstruct path
        path = []
        current = goal
        while current != start:
            path.append(current)
            current = came_from.get(current)
            if current is None:
                logging.warning("No path found to goal.")
                return []
        path.append(start)
        path.reverse()
        logging.info(f"Planned path: {path}")
        return path

    def move_along_path(self, path, actuator_controller):
        for waypoint in path:
            # Placeholder for movement commands to reach waypoint
            logging.info(f"Moving to waypoint: {waypoint}")
            actuator_controller.move_forward()
            # TODO: Add turning and precise movement logic
        actuator_controller.stop()

    def navigate(self, actuator_controller):
        path = self.a_star_search()
        if not path:
            logging.warning("No path to goal.")
            actuator_controller.stop()
            return
        self.move_along_path(path, actuator_controller)
