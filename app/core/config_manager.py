"""
Enhanced configuration management system
"""
import os
import json
import yaml
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass, asdict
from pathlib import Path
from app.core.error_handling import logger

@dataclass
class APIConfig:
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    workers: int = 1
    reload: bool = False
    api_key: str = "your_secret_api_key"
    cors_origins: list = None
    
    def __post_init__(self):
        if self.cors_origins is None:
            self.cors_origins = ["http://localhost:3000", "http://localhost:8000"]

@dataclass
class DatabaseConfig:
    url: str = "sqlite:///./firebot.db"
    echo: bool = False
    pool_size: int = 5
    max_overflow: int = 10
    backup_interval: int = 3600  # seconds

@dataclass
class RobotConfig:
    simulation_mode: bool = True
    camera_index: int = 0
    max_speed: float = 1.0
    battery_threshold: int = 20
    patrol_waypoints: list = None
    
    def __post_init__(self):
        if self.patrol_waypoints is None:
            self.patrol_waypoints = [[10, 10], [10, 40], [40, 40], [40, 10]]

@dataclass
class VisionConfig:
    model_path: str = "runs/detect/train/weights/best.pt"
    confidence_threshold: float = 0.5
    iou_threshold: float = 0.45
    max_detections: int = 100
    image_size: int = 640

@dataclass
class NavigationConfig:
    map_size: int = 100
    resolution: float = 1.0
    goal_tolerance: float = 0.5
    max_planning_time: float = 5.0
    path_smoothing: bool = True

@dataclass
class LoggingConfig:
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_rotation: bool = True
    max_file_size: int = 10  # MB
    backup_count: int = 5

@dataclass
class SecurityConfig:
    jwt_secret: str = "your_jwt_secret_key"
    token_expiry: int = 3600  # seconds
    password_min_length: int = 8
    max_login_attempts: int = 5
    session_timeout: int = 1800  # seconds

@dataclass
class MQTTConfig:
    broker: str = "localhost"
    port: int = 1883
    username: str = ""
    password: str = ""
    keepalive: int = 60
    qos: int = 1

class ConfigManager:
    """Centralized configuration management"""
    
    def __init__(self, config_dir: str = None):
        self.config_dir = Path(config_dir or os.path.join(os.path.dirname(__file__), "..", "..", "config"))
        self.config_dir.mkdir(exist_ok=True)
        
        # Initialize configurations
        self.api = APIConfig()
        self.database = DatabaseConfig()
        self.robot = RobotConfig()
        self.vision = VisionConfig()
        self.navigation = NavigationConfig()
        self.logging = LoggingConfig()
        self.security = SecurityConfig()
        self.mqtt = MQTTConfig()
        
        # Load configurations
        self.load_all_configs()
        
    def load_all_configs(self):
        """Load all configuration files"""
        try:
            # Load from environment variables first
            self._load_from_env()
            
            # Load from config files
            config_files = {
                'api': 'api.yaml',
                'database': 'database.yaml',
                'robot': 'robot.yaml',
                'vision': 'vision.yaml',
                'navigation': 'navigation.yaml',
                'logging': 'logging.yaml',
                'security': 'security.yaml',
                'mqtt': 'mqtt.yaml'
            }
            
            for config_name, filename in config_files.items():
                self._load_config_file(config_name, filename)
                
        except Exception as e:
            logger.error(f"Error loading configurations: {e}")
            
    def _load_from_env(self):
        """Load configuration from environment variables"""
        # API Configuration
        self.api.host = os.getenv("API_HOST", self.api.host)
        self.api.port = int(os.getenv("API_PORT", self.api.port))
        self.api.debug = os.getenv("DEBUG", str(self.api.debug)).lower() in ("true", "1", "t")
        self.api.api_key = os.getenv("API_KEY", self.api.api_key)
        
        # Database Configuration
        self.database.url = os.getenv("DATABASE_URL", self.database.url)
        
        # Robot Configuration
        self.robot.simulation_mode = os.getenv("SIMULATION_MODE", str(self.robot.simulation_mode)).lower() in ("true", "1", "t")
        self.robot.camera_index = int(os.getenv("CAMERA_INDEX", self.robot.camera_index))
        
        # Vision Configuration
        self.vision.model_path = os.getenv("YOLO_MODEL_PATH", self.vision.model_path)
        
        # Logging Configuration
        self.logging.level = os.getenv("LOG_LEVEL", self.logging.level)
        
        # Security Configuration
        self.security.jwt_secret = os.getenv("SECRET_KEY", self.security.jwt_secret)
        
        # MQTT Configuration
        self.mqtt.broker = os.getenv("MQTT_BROKER", self.mqtt.broker)
        self.mqtt.port = int(os.getenv("MQTT_PORT", self.mqtt.port))
        self.mqtt.username = os.getenv("MQTT_USERNAME", self.mqtt.username)
        self.mqtt.password = os.getenv("MQTT_PASSWORD", self.mqtt.password)
        
    def _load_config_file(self, config_name: str, filename: str):
        """Load configuration from YAML file"""
        config_path = self.config_dir / filename
        
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    data = yaml.safe_load(f) or {}
                    
                config_obj = getattr(self, config_name)
                for key, value in data.items():
                    if hasattr(config_obj, key):
                        setattr(config_obj, key, value)
                        
                logger.info(f"Loaded configuration from {filename}")
                
            except Exception as e:
                logger.warning(f"Error loading {filename}: {e}")
        else:
            # Create default config file
            self._save_config_file(config_name, filename)
            
    def _save_config_file(self, config_name: str, filename: str):
        """Save configuration to YAML file"""
        config_path = self.config_dir / filename
        
        try:
            config_obj = getattr(self, config_name)
            data = asdict(config_obj)
            
            with open(config_path, 'w') as f:
                yaml.dump(data, f, default_flow_style=False, indent=2)
                
            logger.info(f"Saved default configuration to {filename}")
            
        except Exception as e:
            logger.error(f"Error saving {filename}: {e}")
            
    def save_all_configs(self):
        """Save all configurations to files"""
        config_files = {
            'api': 'api.yaml',
            'database': 'database.yaml',
            'robot': 'robot.yaml',
            'vision': 'vision.yaml',
            'navigation': 'navigation.yaml',
            'logging': 'logging.yaml',
            'security': 'security.yaml',
            'mqtt': 'mqtt.yaml'
        }
        
        for config_name, filename in config_files.items():
            self._save_config_file(config_name, filename)
            
    def get_config_dict(self) -> Dict[str, Any]:
        """Get all configurations as dictionary"""
        return {
            'api': asdict(self.api),
            'database': asdict(self.database),
            'robot': asdict(self.robot),
            'vision': asdict(self.vision),
            'navigation': asdict(self.navigation),
            'logging': asdict(self.logging),
            'security': asdict(self.security),
            'mqtt': asdict(self.mqtt)
        }
        
    def update_config(self, section: str, key: str, value: Any):
        """Update a specific configuration value"""
        if hasattr(self, section):
            config_obj = getattr(self, section)
            if hasattr(config_obj, key):
                setattr(config_obj, key, value)
                logger.info(f"Updated {section}.{key} = {value}")
                return True
        return False
        
    def reload_configs(self):
        """Reload all configurations"""
        logger.info("Reloading configurations...")
        self.load_all_configs()
        
    def validate_configs(self) -> Dict[str, list]:
        """Validate all configurations"""
        issues = {
            'errors': [],
            'warnings': []
        }
        
        # API validation
        if not 1 <= self.api.port <= 65535:
            issues['errors'].append("API port must be between 1 and 65535")
            
        if self.api.api_key == "your_secret_api_key":
            issues['warnings'].append("API key is using default value")
            
        # Security validation
        if self.security.jwt_secret == "your_jwt_secret_key":
            issues['warnings'].append("JWT secret is using default value")
            
        if self.security.password_min_length < 8:
            issues['warnings'].append("Password minimum length should be at least 8")
            
        # Vision validation
        if not os.path.exists(self.vision.model_path):
            issues['warnings'].append(f"Vision model path does not exist: {self.vision.model_path}")
            
        # Robot validation
        if not self.robot.patrol_waypoints:
            issues['warnings'].append("No patrol waypoints configured")
            
        return issues

# Global configuration instance
config = ConfigManager()

# Export commonly used items
__all__ = [
    'APIConfig', 'DatabaseConfig', 'RobotConfig', 'VisionConfig', 
    'NavigationConfig', 'LoggingConfig', 'SecurityConfig', 'MQTTConfig',
    'ConfigManager', 'config'
]
