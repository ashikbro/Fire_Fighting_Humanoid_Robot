"""Safe simulated actuator interface."""

def move_forward(speed: float = 1.0) -> None:
    """Simulate forward movement."""

def turn(angle: float = 90.0) -> None:
    """Simulate a turn."""

def activate_water_pump(duration: float = 0.0) -> None:
    """Simulate water-pump activation."""

def stop_all_motors() -> None:
    """Simulate an emergency motor stop."""
