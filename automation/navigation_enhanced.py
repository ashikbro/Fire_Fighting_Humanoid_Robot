import numpy as np
import heapq
import logging
from automation.sensor_fusion import SensorFusion

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class NavigationEnhanced:
    """
    Enhanced navigation controller with A* path planning and obstacle avoidance.
    """

    def __init__(self, grid_size=(20, 20)):
        self.sensor_fusion = SensorFusion()
        self.grid_size = grid_size
        self.current_position = (0, 0)
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

    def update_grid_with_obstacles(self):
        fused_data = self.sensor_fusion.fuse()
        # For simplicity, assume fused_data is a list of obstacle coordinates
        self.grid = np.zeros(self.grid_size)
        for obs in fused_data:
            x, y = int(obs[0]), int(obs[1])
            if 0 <= x < self.grid_size[0] and 0 <= y < self.grid_size[1]:
                self.grid[x, y] = 1
        logging.info("Grid updated with obstacles.")

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
