import unittest
from hardware_integration import sensor_interface, actuator_interface

class TestSensorInterface(unittest.TestCase):
    def test_get_all_sensor_data(self):
        data = sensor_interface.get_all_sensor_data()
        self.assertIn("temperature", data)
        self.assertIn("smoke_density", data)
        self.assertIn("gas_level", data)
        self.assertIn("humidity", data)
        self.assertIsInstance(data["temperature"], float)
        self.assertIsInstance(data["smoke_density"], float)
        self.assertIsInstance(data["gas_level"], float)
        self.assertIsInstance(data["humidity"], float)

class TestActuatorInterface(unittest.TestCase):
    def test_actuator_functions(self):
        # Just test that functions run without error
        actuator_interface.move_forward(5)
        actuator_interface.turn(90)
        actuator_interface.activate_water_pump(3)
        actuator_interface.stop_all_motors()

if __name__ == "__main__":
    unittest.main()
