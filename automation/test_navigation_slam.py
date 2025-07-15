import numpy as np
import matplotlib.pyplot as plt
import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from automation.slam_module import SLAMModule
from automation.navigation import NavigationController

def run_navigation_test():
    """
    Tests the integrated SLAM and A* navigation system in a simulated environment.
    """
    # 1. Initialize SLAM and Navigation
    slam = SLAMModule(map_size=50, resolution=0.5)
    nav = NavigationController(slam)

    # 2. Simulate a simple environment with obstacles
    # Manually add some obstacles to the SLAM map for testing
    slam.grid_map_log_odds[10:15, 20:25] = slam.log_odds_occ  # A wall
    slam.grid_map_log_odds[30:35, 10:15] = slam.log_odds_occ  # Another wall

    # 3. Set a start and goal position
    start_pose = np.array([5.0, 5.0, 0.0])
    slam.ekf.x = start_pose  # Set robot's initial pose
    nav.set_goal(20.0, 20.0) # Goal is now within the map boundaries

    # 4. Plan the path using A*
    path = nav.plan_path_astar()

    # 5. Visualize the results
    if path:
        print("Path found!")
        visualize_map_and_path(nav, slam.get_map(), start_pose, nav.goal_position, path, slam.resolution)
    else:
        print("No path found.")
        visualize_map_and_path(nav, slam.get_map(), start_pose, nav.goal_position, [], slam.resolution)

def visualize_map_and_path(nav_controller, grid_map, start_pose, goal_position, path, resolution):
    """
    Visualizes the map, obstacles, start, goal, and the planned path.
    """
    plt.figure(figsize=(10, 10))
    
    # Draw the map (obstacles are black)
    plt.imshow(grid_map.T, cmap='Greys', origin='lower')

    # Convert world coordinates to map coordinates for plotting
    start_map = nav_controller._world_to_map(start_pose[:2])
    goal_map = nav_controller._world_to_map(goal_position)

    # Draw start and goal positions
    plt.plot(start_map[0], start_map[1], 'go', markersize=10, label='Start')
    plt.plot(goal_map[0], goal_map[1], 'ro', markersize=10, label='Goal')

    # Draw the path
    if path:
        path_map = np.array([nav_controller._world_to_map(p) for p in path])
        plt.plot(path_map[:, 0], path_map[:, 1], 'b-', label='A* Path')

    plt.title('A* Navigation on SLAM Map')
    plt.xlabel('X Coordinate')
    plt.ylabel('Y Coordinate')
    plt.legend()
    plt.grid(True)
    plt.show()

if __name__ == '__main__':
    # This is a conceptual test and requires a NavigationController instance `nav`
    # to be created before calling visualize_map_and_path.
    # The following lines are corrected to run the test.
    slam = SLAMModule(map_size=50, resolution=0.5)
    nav = NavigationController(slam)
    run_navigation_test()
