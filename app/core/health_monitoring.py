"""
Health check and monitoring system for the Fire Fighting Robot
"""
import psutil
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass
from app.core.error_handling import logger

@dataclass
class HealthMetric:
    name: str
    value: float
    unit: str
    status: str  # 'ok', 'warning', 'critical'
    timestamp: datetime
    threshold_warning: float = None
    threshold_critical: float = None

class SystemMonitor:
    """Monitor system health and performance metrics"""
    
    def __init__(self):
        self.start_time = datetime.now()
        self.metrics_history: Dict[str, List[HealthMetric]] = {}
        self.monitoring = False
        self.monitor_thread = None
        
    def start_monitoring(self, interval: int = 30):
        """Start continuous monitoring"""
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, args=(interval,))
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        logger.info("System monitoring started")
        
    def stop_monitoring(self):
        """Stop monitoring"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("System monitoring stopped")
        
    def _monitor_loop(self, interval: int):
        """Main monitoring loop"""
        while self.monitoring:
            try:
                self._collect_metrics()
                time.sleep(interval)
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(interval)
                
    def _collect_metrics(self):
        """Collect system metrics"""
        timestamp = datetime.now()
        
        # CPU Usage
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_metric = HealthMetric(
            name="cpu_usage",
            value=cpu_percent,
            unit="%",
            status=self._get_status(cpu_percent, 70, 90),
            timestamp=timestamp,
            threshold_warning=70.0,
            threshold_critical=90.0
        )
        self._add_metric(cpu_metric)
        
        # Memory Usage
        memory = psutil.virtual_memory()
        memory_metric = HealthMetric(
            name="memory_usage",
            value=memory.percent,
            unit="%",
            status=self._get_status(memory.percent, 80, 95),
            timestamp=timestamp,
            threshold_warning=80.0,
            threshold_critical=95.0
        )
        self._add_metric(memory_metric)
        
        # Disk Usage
        disk = psutil.disk_usage('/')
        disk_percent = (disk.used / disk.total) * 100
        disk_metric = HealthMetric(
            name="disk_usage",
            value=disk_percent,
            unit="%",
            status=self._get_status(disk_percent, 85, 95),
            timestamp=timestamp,
            threshold_warning=85.0,
            threshold_critical=95.0
        )
        self._add_metric(disk_metric)
        
        # Network connections
        connections = len(psutil.net_connections())
        network_metric = HealthMetric(
            name="network_connections",
            value=connections,
            unit="count",
            status=self._get_status(connections, 100, 200),
            timestamp=timestamp,
            threshold_warning=100.0,
            threshold_critical=200.0
        )
        self._add_metric(network_metric)
        
        # System uptime
        uptime_seconds = (timestamp - self.start_time).total_seconds()
        uptime_metric = HealthMetric(
            name="uptime",
            value=uptime_seconds,
            unit="seconds",
            status="ok",
            timestamp=timestamp
        )
        self._add_metric(uptime_metric)
        
    def _get_status(self, value: float, warning_threshold: float, critical_threshold: float) -> str:
        """Determine status based on thresholds"""
        if value >= critical_threshold:
            return "critical"
        elif value >= warning_threshold:
            return "warning"
        else:
            return "ok"
            
    def _add_metric(self, metric: HealthMetric):
        """Add metric to history"""
        if metric.name not in self.metrics_history:
            self.metrics_history[metric.name] = []
            
        self.metrics_history[metric.name].append(metric)
        
        # Keep only last 100 readings
        if len(self.metrics_history[metric.name]) > 100:
            self.metrics_history[metric.name] = self.metrics_history[metric.name][-100:]
            
        # Log critical metrics
        if metric.status == "critical":
            logger.error(f"CRITICAL: {metric.name} = {metric.value}{metric.unit}")
        elif metric.status == "warning":
            logger.warning(f"WARNING: {metric.name} = {metric.value}{metric.unit}")
            
    def get_current_health(self) -> Dict[str, HealthMetric]:
        """Get current health status"""
        current_health = {}
        for metric_name, metrics in self.metrics_history.items():
            if metrics:
                current_health[metric_name] = metrics[-1]
        return current_health
        
    def get_health_summary(self) -> Dict:
        """Get health summary"""
        current = self.get_current_health()
        
        summary = {
            "overall_status": "ok",
            "timestamp": datetime.now().isoformat(),
            "uptime_seconds": (datetime.now() - self.start_time).total_seconds(),
            "metrics": {}
        }
        
        critical_count = 0
        warning_count = 0
        
        for name, metric in current.items():
            summary["metrics"][name] = {
                "value": metric.value,
                "unit": metric.unit,
                "status": metric.status,
                "timestamp": metric.timestamp.isoformat()
            }
            
            if metric.status == "critical":
                critical_count += 1
            elif metric.status == "warning":
                warning_count += 1
                
        # Determine overall status
        if critical_count > 0:
            summary["overall_status"] = "critical"
        elif warning_count > 0:
            summary["overall_status"] = "warning"
            
        summary["critical_count"] = critical_count
        summary["warning_count"] = warning_count
        
        return summary

class RobotHealthChecker:
    """Health checker specifically for robot components"""
    
    def __init__(self, robot_controller=None):
        self.robot_controller = robot_controller
        self.last_check = None
        
    def check_vision_system(self) -> HealthMetric:
        """Check vision system health"""
        try:
            # Test vision system
            if hasattr(self.robot_controller, 'object_detector'):
                # Simple test - try to initialize detector
                detector = self.robot_controller.object_detector
                status = "ok" if detector else "critical"
            else:
                status = "warning"
                
            return HealthMetric(
                name="vision_system",
                value=1.0 if status == "ok" else 0.0,
                unit="status",
                status=status,
                timestamp=datetime.now()
            )
        except Exception as e:
            logger.error(f"Vision system check failed: {e}")
            return HealthMetric(
                name="vision_system",
                value=0.0,
                unit="status",
                status="critical",
                timestamp=datetime.now()
            )
            
    def check_navigation_system(self) -> HealthMetric:
        """Check navigation system health"""
        try:
            if hasattr(self.robot_controller, 'navigation'):
                nav = self.robot_controller.navigation
                status = "ok" if nav else "critical"
            else:
                status = "warning"
                
            return HealthMetric(
                name="navigation_system",
                value=1.0 if status == "ok" else 0.0,
                unit="status",
                status=status,
                timestamp=datetime.now()
            )
        except Exception as e:
            logger.error(f"Navigation system check failed: {e}")
            return HealthMetric(
                name="navigation_system",
                value=0.0,
                unit="status",
                status="critical",
                timestamp=datetime.now()
            )
            
    def check_communication(self) -> HealthMetric:
        """Check communication systems"""
        try:
            # Simple network connectivity check
            import socket
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            status = "ok"
            value = 1.0
        except Exception:
            status = "warning"
            value = 0.0
            
        return HealthMetric(
            name="communication",
            value=value,
            unit="status",
            status=status,
            timestamp=datetime.now()
        )
        
    def comprehensive_health_check(self) -> Dict[str, HealthMetric]:
        """Perform comprehensive health check"""
        self.last_check = datetime.now()
        
        health_checks = {
            "vision": self.check_vision_system(),
            "navigation": self.check_navigation_system(),
            "communication": self.check_communication()
        }
        
        return health_checks

# Global instances
system_monitor = SystemMonitor()
robot_health_checker = RobotHealthChecker()

# Export commonly used items
__all__ = [
    'HealthMetric', 'SystemMonitor', 'RobotHealthChecker',
    'system_monitor', 'robot_health_checker'
]
