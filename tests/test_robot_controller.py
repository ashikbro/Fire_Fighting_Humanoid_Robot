import unittest
from unittest.mock import MagicMock, patch
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from automation.robot_controller import RobotController

class TestRobotController(unittest.TestCase):
    def setUp(self):
        self.robot_controller = RobotController()
        # Mock navigation and actuators to avoid hardware dependencies
        self.robot_controller.navigation = MagicMock()
        self.robot_controller.actuators = MagicMock()
        self.robot_controller.fire_detector = MagicMock()

    def test_fire_detection_and_navigation(self):
        # Mock fire detection to return True
        self.robot_controller.fire_detector.detect_fire.return_value = True
        # Mock fire severity prediction
        self.robot_controller.fire_detector.predict_fire_severity.return_value = 'high'
        # Mock current position
        self.robot_controller.navigation.get_current_position.return_value = (10, 20)
        # Mock navigation plan_path to return a path
        self.robot_controller.navigation.plan_path.return_value = [(11, 21), (12, 22)]
        # Mock detect_obstacles to return False
        self.robot_controller.navigation.detect_obstacles.return_value = False

        # Call update_sensor_data with dummy camera data
        self.robot_controller.update_sensor_data(camera_data='dummy_frame')

        # Check if fire detection was called
        self.robot_controller.fire_detector.detect_fire.assert_called_once_with('dummy_frame')
        # Check if fire severity prediction was called
        self.robot_controller.fire_detector.predict_fire_severity.assert_called_once()
        # Check if navigation goal was set
        self.assertEqual(self.robot_controller.fire_location, (10, 20))
        # Check if perform_navigation was called by checking if actuators.move_forward was called
        self.assertTrue(self.robot_controller.actuators.move_forward.called)
        # Check if fire suppression was activated
        self.robot_controller.actuators.activate_water_pump.assert_called_once()
        self.robot_controller.actuators.activate_extinguisher.assert_called_once()

    def test_object_detection_logging(self):
        # Mock object detection to return some detections
        self.robot_controller.fire_detector.detect_fire.return_value = False
        self.robot_controller.fire_detector.detect_objects.return_value = [
            {'class_name': 'person', 'confidence': 0.9, 'box': [0, 0, 10, 10]}
        ]

        with patch('logging.info') as mock_log_info:
            self.robot_controller.update_sensor_data(camera_data='dummy_frame')
            mock_log_info.assert_any_call("Objects detected: ['person']")

if __name__ == '__main__':
    unittest.main()

vision_fire_detection/dataset_fire_images/
    train/
        fire/
        non_fire/
    val/
        fire/
        non_fire/
