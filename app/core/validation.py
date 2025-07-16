"""
Input validation and sanitization module
"""
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, validator
import re

class SensorDataInput(BaseModel):
    """Validated sensor data input model"""
    temperature: float = Field(..., ge=-50, le=100, description="Temperature in Celsius")
    smoke_density: float = Field(..., ge=0, le=1000, description="Smoke density level")
    gas_level: float = Field(..., ge=0, le=1000, description="Gas level")
    humidity: float = Field(..., ge=0, le=100, description="Humidity percentage")
    
    @validator('temperature')
    def validate_temperature(cls, v):
        if not -50 <= v <= 100:
            raise ValueError('Temperature must be between -50 and 100 degrees Celsius')
        return v
    
    @validator('humidity')
    def validate_humidity(cls, v):
        if not 0 <= v <= 100:
            raise ValueError('Humidity must be between 0 and 100 percent')
        return v

class RobotMovementInput(BaseModel):
    """Validated robot movement input model"""
    direction: str = Field(..., regex=r'^(forward|backward|left|right|stop)$')
    speed: float = Field(default=50.0, ge=0, le=100, description="Speed percentage")
    duration: float = Field(default=1.0, ge=0.1, le=10.0, description="Duration in seconds")

class NavigationGoalInput(BaseModel):
    """Validated navigation goal input model"""
    x: float = Field(..., ge=0, le=100, description="X coordinate")
    y: float = Field(..., ge=0, le=100, description="Y coordinate")
    tolerance: float = Field(default=0.5, ge=0.1, le=2.0, description="Goal tolerance in meters")

class UserCredentials(BaseModel):
    """Validated user credentials model"""
    username: str = Field(..., min_length=3, max_length=50, regex=r'^[a-zA-Z0-9_-]+$')
    password: str = Field(..., min_length=8, max_length=128)
    
    @validator('username')
    def validate_username(cls, v):
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('Username can only contain letters, numbers, underscores, and hyphens')
        return v
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one digit')
        return v

class APIKeyInput(BaseModel):
    """Validated API key input model"""
    api_key: str = Field(..., min_length=32, max_length=256)
    
    @validator('api_key')
    def validate_api_key(cls, v):
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('API key contains invalid characters')
        return v

class FireSuppressionInput(BaseModel):
    """Validated fire suppression input model"""
    activation_type: str = Field(..., regex=r'^(water|foam|co2|powder)$')
    duration: float = Field(default=5.0, ge=1.0, le=30.0)
    intensity: float = Field(default=100.0, ge=10.0, le=100.0)

class SystemConfigInput(BaseModel):
    """Validated system configuration input model"""
    debug_mode: bool = Field(default=False)
    simulation_mode: bool = Field(default=True)
    camera_index: int = Field(default=0, ge=0, le=10)
    log_level: str = Field(default="INFO", regex=r'^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$')

def sanitize_string(value: str, max_length: int = 255, allow_html: bool = False) -> str:
    """Sanitize string input to prevent injection attacks"""
    if not isinstance(value, str):
        return str(value)
    
    # Trim whitespace
    value = value.strip()
    
    # Limit length
    if len(value) > max_length:
        value = value[:max_length]
    
    # Remove or escape HTML if not allowed
    if not allow_html:
        value = re.sub(r'<[^>]*>', '', value)  # Remove HTML tags
        value = value.replace('&', '&amp;')
        value = value.replace('<', '&lt;')
        value = value.replace('>', '&gt;')
        value = value.replace('"', '&quot;')
        value = value.replace("'", '&#x27;')
        value = value.replace('/', '&#x2F;')
    
    # Additional security sanitization
    # Remove potential SQL injection patterns
    sql_patterns = [
        r'union\s+select', r'drop\s+table', r'insert\s+into', r'delete\s+from',
        r'update\s+.*\s+set', r'create\s+table', r'alter\s+table', r'exec\s*\(',
        r'execute\s*\(', r'sp_', r'xp_'
    ]
    
    for pattern in sql_patterns:
        value = re.sub(pattern, '', value, flags=re.IGNORECASE)
    
    # Remove potential XSS patterns
    xss_patterns = [
        r'javascript:', r'vbscript:', r'onload=', r'onerror=', r'onclick=',
        r'onmouseover=', r'onfocus=', r'onblur=', r'onchange=', r'onsubmit='
    ]
    
    for pattern in xss_patterns:
        value = re.sub(pattern, '', value, flags=re.IGNORECASE)
    
    # Remove potential command injection patterns
    cmd_patterns = [
        r';\s*rm\s+', r';\s*cat\s+', r';\s*ls\s+', r';\s*wget\s+',
        r';\s*curl\s+', r'&&', r'\|\|', r'`', r'\$\('
    ]
    
    for pattern in cmd_patterns:
        value = re.sub(pattern, '', value, flags=re.IGNORECASE)
    
    return value

def validate_file_path(file_path: str, allowed_extensions: List[str] = None) -> bool:
    """Validate file path for security"""
    # Check for path traversal attempts
    if '..' in file_path or file_path.startswith('/'):
        return False
    
    # Check file extension if specified
    if allowed_extensions:
        extension = file_path.split('.')[-1].lower()
        if extension not in [ext.lower() for ext in allowed_extensions]:
            return False
    
    return True

def validate_coordinates(x: float, y: float, max_x: float = 100.0, max_y: float = 100.0) -> bool:
    """Validate coordinate values"""
    return 0 <= x <= max_x and 0 <= y <= max_y

def validate_ip_address(ip: str) -> bool:
    """Validate IP address format"""
    pattern = r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
    return bool(re.match(pattern, ip))

def validate_port(port: Union[str, int]) -> bool:
    """Validate port number"""
    try:
        port_num = int(port)
        return 1 <= port_num <= 65535
    except (ValueError, TypeError):
        return False

# Common validation patterns
PATTERNS = {
    'email': r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
    'phone': r'^\+?1?-?\.?\s?\(?(\d{3})\)?[-.\s]?(\d{3})[-.\s]?(\d{4})$',
    'alphanumeric': r'^[a-zA-Z0-9]+$',
    'safe_string': r'^[a-zA-Z0-9\s\-_.,!?]+$'
}

def validate_pattern(value: str, pattern_name: str) -> bool:
    """Validate value against predefined patterns"""
    pattern = PATTERNS.get(pattern_name)
    if not pattern:
        raise ValueError(f"Unknown pattern: {pattern_name}")
    return bool(re.match(pattern, value))

# Export commonly used items
__all__ = [
    'SensorDataInput', 'RobotMovementInput', 'NavigationGoalInput', 
    'UserCredentials', 'APIKeyInput', 'FireSuppressionInput', 'SystemConfigInput',
    'sanitize_string', 'validate_file_path', 'validate_coordinates', 
    'validate_ip_address', 'validate_port', 'validate_pattern', 'PATTERNS'
]
