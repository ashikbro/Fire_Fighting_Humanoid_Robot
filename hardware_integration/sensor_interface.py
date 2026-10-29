"""Sensor interface used by tests and the simulation runtime."""

def get_all_sensor_data() -> dict[str, float]:
    """Return a stable simulated sensor snapshot."""
    return {
        "temperature": 25.0,
        "smoke_density": 0.0,
        "gas_level": 0.0,
        "humidity": 50.0,
    }
