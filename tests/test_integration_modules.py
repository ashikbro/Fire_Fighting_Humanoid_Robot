import os
import sys
import types
from unittest.mock import MagicMock

import numpy as np
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from automation.safety_monitor_integration import SafetyMonitorIntegration


@pytest.fixture
def fusion_integration_module(monkeypatch):
    """Import automation.sensor_fusion_integration with its absent/heavy deps stubbed."""
    sensor_interface = types.ModuleType("hardware_integration.sensor_interface")
    sensor_interface.get_all_sensor_data = MagicMock()
    hardware_integration = types.ModuleType("hardware_integration")
    hardware_integration.sensor_interface = sensor_interface
    anomaly_detection = types.ModuleType("src.anomaly_detection")
    anomaly_detection.AnomalyDetector = MagicMock()

    monkeypatch.setitem(sys.modules, "hardware_integration", hardware_integration)
    monkeypatch.setitem(sys.modules, "hardware_integration.sensor_interface", sensor_interface)
    monkeypatch.setitem(sys.modules, "src.anomaly_detection", anomaly_detection)
    monkeypatch.delitem(sys.modules, "automation.sensor_fusion_integration", raising=False)

    import automation.sensor_fusion_integration as module
    yield module
    sys.modules.pop("automation.sensor_fusion_integration", None)


def test_sensor_fusion_integration_uses_enhanced_fusion(fusion_integration_module):
    from automation.sensor_fusion_enhanced import SensorFusion

    integration = fusion_integration_module.SensorFusionIntegration()
    assert isinstance(integration.sensor_fusion, SensorFusion)


def test_sensor_fusion_integration_skips_missing_readings(fusion_integration_module):
    sensor_interface = fusion_integration_module.sensor_interface
    sensor_interface.get_all_sensor_data.return_value = {"smoke_density": 0.7, "gas_level": None}

    integration = fusion_integration_module.SensorFusionIntegration()
    integration.anomaly_detector.predict.return_value = np.array([1])

    fused, is_anomaly = integration.update_and_fuse()

    assert integration.sensor_fusion.smoke_data is not None
    assert integration.sensor_fusion.gas_data is None
    assert integration.sensor_fusion.visual_data is None
    assert integration.sensor_fusion.thermal_data is None
    assert fused.shape == (1,)
    assert is_anomaly == 1


def test_sensor_fusion_integration_with_no_readings(fusion_integration_module):
    fusion_integration_module.sensor_interface.get_all_sensor_data.return_value = {}

    integration = fusion_integration_module.SensorFusionIntegration()
    fused, is_anomaly = integration.update_and_fuse()

    assert fused.size == 0
    assert is_anomaly is False
    integration.anomaly_detector.predict.assert_not_called()


def test_safety_monitor_integration_construction():
    integration = SafetyMonitorIntegration(battery_threshold=30, check_interval=2, watchdog_timeout=7)
    assert integration.check_interval == 2
    assert integration.safety_monitor.battery_threshold == 30
    assert integration.safety_monitor.watchdog_timeout == 7


def test_safety_monitor_integration_check_once_feeds_watchdog_and_battery(monkeypatch):
    integration = SafetyMonitorIntegration(battery_threshold=20)
    monitor = integration.safety_monitor
    monitor.last_heartbeat = 0
    shutdown = MagicMock()
    monkeypatch.setattr(monitor, "auto_shutdown", shutdown)

    monkeypatch.setattr(integration, "get_battery_level", lambda: 50)
    integration.check_once()
    assert monitor.battery_level == 50
    assert monitor.last_heartbeat > 0
    shutdown.assert_not_called()

    monkeypatch.setattr(integration, "get_battery_level", lambda: 10)
    integration.check_once()
    assert monitor.battery_level == 10
    shutdown.assert_called_once()


def test_safety_monitor_integration_start_stop():
    integration = SafetyMonitorIntegration(check_interval=0.01)
    integration.start()
    integration.stop()
    assert not integration.monitor_thread.is_alive()
    assert not integration.safety_monitor.watchdog_thread.is_alive()
