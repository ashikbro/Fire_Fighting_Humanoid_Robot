import unittest
import numpy as np
from automation.navigation import NavigationController
from automation.slam_module import SLAMModule

class TestNavigationWithDWA(unittest.TestCase):

    def setUp(self):
        """Set up a test environment with a simple map."""
        self.slam = SLAMModule()
        # Create a map with an obstacle
        self.slam.get_map()[5, 5] = 1
        self.navigation = NavigationController(self.slam)
        self.navigation.path_history = []

    def test_dwa_navigation(self):
        """
        Test that the DWA navigation can guide the robot to a goal while avoiding obstacles.
        """
        # Set a goal on the other side of the obstacle
        self.navigation.set_goal(8, 8)
        
        # Set the robot's initial pose
        self.slam.ekf.x = np.array([1, 1, 0])
        
        # Run the navigation
        self.navigation.navigate()
        
        # Check if the robot reached the goal
        self.assertTrue(self.navigation.is_goal_reached(), "Robot did not reach the goal.")
        
        # Check that the robot did not pass through the obstacle
        path_x = [p[0] for p in self.navigation.path_history]
        path_y = [p[1] for p in self.navigation.path_history]
        
        obstacle_passed = False
        for x, y in zip(path_x, path_y):
            if int(x) == 5 and int(y) == 5:
                obstacle_passed = True
                break
        
        self.assertFalse(obstacle_passed, "Robot passed through an obstacle.")

if __name__ == '__main__':
    unittest.main()