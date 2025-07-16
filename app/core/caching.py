"""
Redis caching system for performance optimization
"""
import redis
import json
import pickle
from typing import Any, Optional, Dict, List, Union
from datetime import timedelta
import asyncio
from functools import wraps
import hashlib
import time

from app.core.error_handling import logger
from app.core.config_manager import config

class CacheManager:
    """Advanced Redis-based caching system"""
    
    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url or config.api.cors_origins[0] if hasattr(config, 'api') else "redis://localhost:6379/0"
        self.redis_client = None
        self.is_connected = False
        self.fallback_cache = {}  # In-memory fallback
        
    def connect(self):
        """Connect to Redis server"""
        try:
            self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
            # Test connection
            self.redis_client.ping()
            self.is_connected = True
            logger.info("Connected to Redis cache")
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}. Using in-memory fallback cache.")
            self.is_connected = False
    
    def _get_key(self, key: str, namespace: str = "firebot") -> str:
        """Get formatted cache key"""
        return f"{namespace}:{key}"
    
    def set(self, key: str, value: Any, ttl: int = 3600, namespace: str = "firebot") -> bool:
        """Set cache value with TTL"""
        formatted_key = self._get_key(key, namespace)
        
        try:
            if self.is_connected and self.redis_client:
                # Serialize complex objects
                if isinstance(value, (dict, list, tuple)):
                    serialized_value = json.dumps(value)
                else:
                    serialized_value = str(value)
                
                self.redis_client.setex(formatted_key, ttl, serialized_value)
                return True
            else:
                # Fallback to in-memory cache
                expiry_time = time.time() + ttl
                self.fallback_cache[formatted_key] = {
                    'value': value,
                    'expiry': expiry_time
                }
                return True
                
        except Exception as e:
            logger.error(f"Failed to set cache key {formatted_key}: {e}")
            return False
    
    def get(self, key: str, namespace: str = "firebot") -> Optional[Any]:
        """Get cache value"""
        formatted_key = self._get_key(key, namespace)
        
        try:
            if self.is_connected and self.redis_client:
                value = self.redis_client.get(formatted_key)
                if value is not None:
                    # Try to deserialize JSON
                    try:
                        return json.loads(value)
                    except json.JSONDecodeError:
                        return value
                return None
            else:
                # Fallback to in-memory cache
                cached_item = self.fallback_cache.get(formatted_key)
                if cached_item and cached_item['expiry'] > time.time():
                    return cached_item['value']
                elif cached_item:
                    # Remove expired item
                    del self.fallback_cache[formatted_key]
                return None
                
        except Exception as e:
            logger.error(f"Failed to get cache key {formatted_key}: {e}")
            return None
    
    def delete(self, key: str, namespace: str = "firebot") -> bool:
        """Delete cache value"""
        formatted_key = self._get_key(key, namespace)
        
        try:
            if self.is_connected and self.redis_client:
                return bool(self.redis_client.delete(formatted_key))
            else:
                if formatted_key in self.fallback_cache:
                    del self.fallback_cache[formatted_key]
                    return True
                return False
                
        except Exception as e:
            logger.error(f"Failed to delete cache key {formatted_key}: {e}")
            return False
    
    def exists(self, key: str, namespace: str = "firebot") -> bool:
        """Check if cache key exists"""
        formatted_key = self._get_key(key, namespace)
        
        try:
            if self.is_connected and self.redis_client:
                return bool(self.redis_client.exists(formatted_key))
            else:
                cached_item = self.fallback_cache.get(formatted_key)
                return cached_item is not None and cached_item['expiry'] > time.time()
                
        except Exception as e:
            logger.error(f"Failed to check cache key existence {formatted_key}: {e}")
            return False
    
    def increment(self, key: str, amount: int = 1, namespace: str = "firebot") -> Optional[int]:
        """Increment a numeric cache value"""
        formatted_key = self._get_key(key, namespace)
        
        try:
            if self.is_connected and self.redis_client:
                return self.redis_client.incr(formatted_key, amount)
            else:
                # Fallback implementation
                current = self.get(key, namespace) or 0
                new_value = int(current) + amount
                self.set(key, new_value, namespace=namespace)
                return new_value
                
        except Exception as e:
            logger.error(f"Failed to increment cache key {formatted_key}: {e}")
            return None
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        try:
            if self.is_connected and self.redis_client:
                info = self.redis_client.info('memory')
                return {
                    'connected': True,
                    'used_memory': info.get('used_memory', 0),
                    'used_memory_human': info.get('used_memory_human', '0B'),
                    'connected_clients': self.redis_client.info('clients').get('connected_clients', 0),
                    'total_commands_processed': self.redis_client.info('stats').get('total_commands_processed', 0)
                }
            else:
                return {
                    'connected': False,
                    'fallback_cache_size': len(self.fallback_cache),
                    'fallback_active_items': sum(
                        1 for item in self.fallback_cache.values() 
                        if item['expiry'] > time.time()
                    )
                }
                
        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {'connected': False, 'error': str(e)}
    
    def clear(self, pattern: str = None, namespace: str = "firebot") -> int:
        """Clear cache keys matching pattern"""
        try:
            if self.is_connected and self.redis_client:
                if pattern:
                    search_pattern = self._get_key(pattern, namespace)
                    keys = self.redis_client.keys(search_pattern)
                    if keys:
                        return self.redis_client.delete(*keys)
                    return 0
                else:
                    # Clear all keys in namespace
                    search_pattern = self._get_key("*", namespace)
                    keys = self.redis_client.keys(search_pattern)
                    if keys:
                        return self.redis_client.delete(*keys)
                    return 0
            else:
                # Clear fallback cache
                namespace_prefix = self._get_key("", namespace)
                keys_to_delete = [
                    key for key in self.fallback_cache.keys()
                    if key.startswith(namespace_prefix)
                ]
                for key in keys_to_delete:
                    del self.fallback_cache[key]
                return len(keys_to_delete)
                
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
            return 0

# Global cache manager instance
cache_manager = CacheManager()

def cached(ttl: int = 3600, namespace: str = "firebot", key_prefix: str = None):
    """Decorator for caching function results"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            key_parts = [key_prefix or func.__name__]
            
            # Add args to key
            for arg in args:
                if isinstance(arg, (str, int, float, bool)):
                    key_parts.append(str(arg))
                else:
                    # Hash complex objects
                    key_parts.append(hashlib.md5(str(arg).encode()).hexdigest()[:8])
            
            # Add kwargs to key
            for k, v in sorted(kwargs.items()):
                if isinstance(v, (str, int, float, bool)):
                    key_parts.append(f"{k}:{v}")
                else:
                    key_parts.append(f"{k}:{hashlib.md5(str(v).encode()).hexdigest()[:8]}")
            
            cache_key = ":".join(key_parts)
            
            # Try to get from cache
            cached_result = cache_manager.get(cache_key, namespace)
            if cached_result is not None:
                logger.debug(f"Cache hit for {cache_key}")
                return cached_result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache_manager.set(cache_key, result, ttl, namespace)
            logger.debug(f"Cache miss for {cache_key}, result cached")
            
            return result
        
        return wrapper
    return decorator

class SensorDataCache:
    """Specialized cache for sensor data"""
    
    def __init__(self, cache_manager: CacheManager):
        self.cache = cache_manager
        self.namespace = "sensors"
    
    def store_reading(self, sensor_id: str, data: Dict[str, Any], ttl: int = 300):
        """Store sensor reading"""
        key = f"reading:{sensor_id}:{int(time.time())}"
        return self.cache.set(key, data, ttl, self.namespace)
    
    def get_latest_reading(self, sensor_id: str) -> Optional[Dict[str, Any]]:
        """Get latest sensor reading"""
        pattern = f"reading:{sensor_id}:*"
        # This is a simplified implementation
        # In a real scenario, you'd need a more sophisticated approach
        return self.cache.get(f"latest:{sensor_id}", self.namespace)
    
    def store_prediction(self, prediction_data: Dict[str, Any], ttl: int = 600):
        """Store fire prediction result"""
        key = f"prediction:{int(time.time())}"
        return self.cache.set(key, prediction_data, ttl, self.namespace)

class RobotStatusCache:
    """Specialized cache for robot status"""
    
    def __init__(self, cache_manager: CacheManager):
        self.cache = cache_manager
        self.namespace = "robot"
    
    def update_status(self, status_data: Dict[str, Any], ttl: int = 60):
        """Update robot status"""
        return self.cache.set("current_status", status_data, ttl, self.namespace)
    
    def get_status(self) -> Optional[Dict[str, Any]]:
        """Get current robot status"""
        return self.cache.get("current_status", self.namespace)
    
    def store_command_result(self, command_id: str, result: Dict[str, Any], ttl: int = 300):
        """Store command execution result"""
        key = f"command_result:{command_id}"
        return self.cache.set(key, result, ttl, self.namespace)

# Initialize cache manager
cache_manager.connect()

# Specialized cache instances
sensor_cache = SensorDataCache(cache_manager)
robot_cache = RobotStatusCache(cache_manager)

# Export commonly used items
__all__ = [
    'CacheManager', 'cache_manager', 'cached', 
    'SensorDataCache', 'RobotStatusCache',
    'sensor_cache', 'robot_cache'
]
