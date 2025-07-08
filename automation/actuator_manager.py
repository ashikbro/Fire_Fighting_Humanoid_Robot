from hardware_integration import actuator_interface

class ActuatorManager:
    def __init__(self):
        pass

    def move_forward(self, distance):
        actuator_interface.move_forward(distance)

    def turn(self, angle):
        actuator_interface.turn(angle)

    def activate_water_pump(self, duration):
        actuator_interface.activate_water_pump(duration)

    def stop_all(self):
        actuator_interface.stop_all_motors()

if __name__ == "__main__":
    am = ActuatorManager()
    am.move_forward(10)
    am.turn(90)
    am.activate_water_pump(5)
    am.stop_all()
