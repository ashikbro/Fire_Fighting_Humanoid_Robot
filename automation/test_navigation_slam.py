import unittest
import numpy as np
from automation.slam_module import SLAMModule
from automation.navigation_enhanced import EnhancedNavigationController

class TestNavigationSLAMIntegration(unittest.TestCase):
    def setUp(self):
        self.slam = SLAMModule(map_size=(50, 50), resolution=1.0)
        self.navigation = EnhancedNavigationController()
        self.navigation.slam = self.slam

    def test_slam_update_and_position(self):
        # Simulate sensor data with some distances
        sensor_data = np.array([1.0, 0.8, 0.6, 0.4, 0.5])
        self.slam.update(sensor_data)
        position, orientation = self.slam.get_position()
        self.assertIsInstance(position, np.ndarray)
        self.assertEqual(position.shape, (2,))
        self.assertIsInstance(orientation, float)

    def test_navigation_plan_path_updates_slam(self):
        self.navigation.set_goal(10, 10)
        # Provide some dummy sensor data
        lidar_data = [1.0, 0.9, 0.8]
        ultrasonic_data = [1.0, 0.9]
        camera_data = [0.5, 0.3]
        self.navigation.update_sensors(lidar_data, ultrasonic_data, camera_data)
        path = self.navigation.plan_path()
        self.assertTrue(len(path) >= 2)
        self.assertTrue(np.allclose(path[-1], np.array([10, 10])))

if __name__ == "__main__":
    unittest.main()
