import numpy as np
import logging
import heapq
from automation.slam_module import SLAMModule
from hardware_integration.lidar_simulation import LidarSimulator

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class NavigationController:
    """
    Advanced navigation controller for the firefighting humanoid robot.
    Uses a SLAM-generated map, A* for global pathfinding, and DWA for local obstacle avoidance.
    """

    def __init__(self, slam_module: SLAMModule):
        self.slam = slam_module
        self.goal_position = None
        self.lidar = LidarSimulator(self.slam.get_map(), self.slam.resolution)
        self.path_history = []
        
        # Robot parameters for DWA
        self.max_speed = 1.0  # m/s
        self.min_speed = -0.5 # m/s
        self.max_yaw_rate = 40.0 * np.pi / 180.0  # rad/s
        self.max_accel = 0.2  # m/s^2
        self.max_dyaw_rate = 400.0 * np.pi / 180.0  # rad/s^2
        self.v_resolution = 0.01 # m/s
        self.yaw_rate_resolution = 0.1 * np.pi / 180.0 # rad/s
        self.dt = 0.1 # s
        self.predict_time = 3.0 # s
        self.robot_radius = 0.5 # m

    def set_goal(self, x, y):
        """
        Set the navigation goal position in world coordinates.
        """
        self.goal_position = np.array([x, y])
        logging.info(f"Goal position set to: {self.goal_position}")

    def plan_path_astar(self):
        """
        Plan a path from the robot's current position to the goal using A*.
        """
        if self.goal_position is None:
            logging.warning("Goal position not set. Cannot plan path.")
            return None

        start_map_coords = self._world_to_map(self.slam.get_pose()[:2])
        goal_map_coords = self._world_to_map(self.goal_position)
        
        if not self._is_valid(goal_map_coords):
            logging.error("Goal is outside map boundaries or in an obstacle.")
            return None

        open_set = [(0, start_map_coords)]
        came_from = {}
        g_score = {start_map_coords: 0}
        f_score = {start_map_coords: self._heuristic(start_map_coords, goal_map_coords)}

        while open_set:
            _, current = heapq.heappop(open_set)

            if current == goal_map_coords:
                return self._reconstruct_path(came_from, current)

            for neighbor in self._get_neighbors(current):
                tentative_g_score = g_score[current] + 1  # Assume cost of 1 for each step
                if tentative_g_score < g_score.get(neighbor, float('inf')):
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g_score
                    f_score[neighbor] = tentative_g_score + self._heuristic(neighbor, goal_map_coords)
                    if neighbor not in [i[1] for i in open_set]:
                        heapq.heappush(open_set, (f_score[neighbor], neighbor))
        
        logging.warning("A* pathfinding failed to find a path.")
        return None

    def _heuristic(self, a, b):
        return np.sqrt((a[0] - b[0])**2 + (a[1] - b[1])**2)

    def _get_neighbors(self, pos):
        x, y = pos
        neighbors = []
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if dx == 0 and dy == 0:
                    continue
                neighbor = (x + dx, y + dy)
                if self._is_valid(neighbor):
                    neighbors.append(neighbor)
        return neighbors

    def _is_valid(self, pos):
        x, y = pos
        if not (0 <= x < self.slam.map_size and 0 <= y < self.slam.map_size):
            return False
        # Fix indexing: numpy arrays are accessed as [row, col] = [y, x]
        if self.slam.get_map()[y, x] == 1:  # Occupied
            return False
        return True

    def _reconstruct_path(self, came_from, current):
        path = [self._map_to_world(current)]
        while current in came_from:
            current = came_from[current]
            path.append(self._map_to_world(current))
        return path[::-1]

    def _world_to_map(self, world_coords):
        return (int(world_coords[0] / self.slam.resolution), int(world_coords[1] / self.slam.resolution))

    def _map_to_world(self, map_coords):
        return (map_coords[0] * self.slam.resolution, map_coords[1] * self.slam.resolution)

    def _motion(self, pose, vel, dt):
        """
        Simulates the robot's motion.
        """
        pose[2] += vel[1] * dt
        pose[0] += vel[0] * np.cos(pose[2]) * dt
        pose[1] += vel[0] * np.sin(pose[2]) * dt
        return pose

    def _dynamic_window_approach(self, pose, current_velocity, goal, lidar_scan):
        # DWA implementation
        min_v = max(self.min_speed, current_velocity[0] - self.max_accel * self.dt)
        max_v = min(self.max_speed, current_velocity[0] + self.max_accel * self.dt)
        min_w = max(-self.max_yaw_rate, current_velocity[1] - self.max_dyaw_rate * self.dt)
        max_w = min(self.max_yaw_rate, current_velocity[1] + self.max_dyaw_rate * self.dt)

        best_cost = float('inf')
        best_vel = [0, 0]

        for v in np.arange(min_v, max_v, self.v_resolution):
            for w in np.arange(min_w, max_w, self.yaw_rate_resolution):
                trajectory = []
                temp_pose = np.copy(pose)
                for _ in np.arange(0, self.predict_time, self.dt):
                    temp_pose = self._motion(temp_pose, [v, w], self.dt)
                    trajectory.append(np.copy(temp_pose))

                # Cost calculation (simplified)
                to_goal_cost = np.linalg.norm(goal - trajectory[-1][:2])
                
                # Obstacle avoidance cost
                obs_cost = 0
                for p in trajectory:
                    for i, scan_range in enumerate(lidar_scan):
                        if scan_range < self.robot_radius:
                            obs_cost = float('inf')
                            break
                    if obs_cost == float('inf'):
                        break
                
                if obs_cost == float('inf'):
                    continue

                final_cost = to_goal_cost + obs_cost
                if final_cost < best_cost:
                    best_cost = final_cost
                    best_vel = [v, w]
        
        return best_vel

    def navigate(self):
        """
        Main navigation loop using DWA for local planning.
        """
        global_path = self.plan_path_astar()
        if not global_path:
            logging.warning("No global path to goal. Navigation halted.")
            return

        current_velocity = [0.0, 0.0]
        
        for waypoint in global_path:
            while np.linalg.norm(self.slam.get_pose()[:2] - waypoint) > self.robot_radius:
                pose = self.slam.get_pose()
                lidar_scan = self.lidar.get_scan(pose)
                
                current_velocity = self._dynamic_window_approach(pose, current_velocity, waypoint, lidar_scan)
                
                # Update robot pose
                new_pose = self._motion(pose, current_velocity, self.dt)
                self.slam.ekf.x = new_pose
                self.path_history.append(new_pose)
                
                if self.is_goal_reached():
                    logging.info("Goal reached during navigation.")
                    return
        
        logging.info("Navigation to goal completed.")

    def is_goal_reached(self, tolerance=0.5):
        """
        Check if the robot has reached its goal within a given tolerance.
        """
        if self.goal_position is None:
            return False
        
        current_position = self.slam.get_pose()[:2]
        distance_to_goal = np.linalg.norm(current_position - self.goal_position)
        
        return distance_to_goal < tolerance
