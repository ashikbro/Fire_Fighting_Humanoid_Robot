"""
Database initialization and management module
"""
import sqlite3
import os
import logging
from datetime import datetime
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

DATABASE_PATH = os.path.join(os.path.dirname(__file__), "..", "firebot.db")

def init_db():
    """Initialize the database with required tables"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Create incidents table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS incidents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                event_type TEXT NOT NULL,
                severity TEXT,
                location TEXT,
                sensor_data TEXT,
                confidence REAL,
                response_time REAL,
                status TEXT DEFAULT 'active'
            )
        ''')
        
        # Create robot_status table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS robot_status (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                battery_level INTEGER,
                position_x REAL,
                position_y REAL,
                orientation REAL,
                temperature REAL,
                system_status TEXT,
                active_mission TEXT
            )
        ''')
        
        # Create sensor_readings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sensor_readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                temperature REAL,
                smoke_density REAL,
                gas_level REAL,
                humidity REAL,
                flame_detected BOOLEAN,
                prediction TEXT,
                confidence REAL
            )
        ''')
        
        # Create users table for authentication
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT DEFAULT 'operator',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_login DATETIME,
                is_active BOOLEAN DEFAULT 1
            )
        ''')
        
        conn.commit()
        logger.info("Database initialized successfully")
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise
    finally:
        conn.close()

def log_incident(event_type: str, severity: str = None, location: str = None, 
                sensor_data: str = None, confidence: float = None, 
                response_time: float = None) -> int:
    """Log an incident to the database"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO incidents (event_type, severity, location, sensor_data, confidence, response_time)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (event_type, severity, location, sensor_data, confidence, response_time))
        
        incident_id = cursor.lastrowid
        conn.commit()
        logger.info(f"Incident logged with ID: {incident_id}")
        return incident_id
        
    except Exception as e:
        logger.error(f"Failed to log incident: {e}")
        raise
    finally:
        conn.close()

def get_incident_history(limit: int = 100) -> List[Dict]:
    """Get incident history from database"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM incidents 
            ORDER BY timestamp DESC 
            LIMIT ?
        ''', (limit,))
        
        incidents = [dict(row) for row in cursor.fetchall()]
        return incidents
        
    except Exception as e:
        logger.error(f"Failed to get incident history: {e}")
        return []
    finally:
        conn.close()

def log_sensor_reading(temperature: float, smoke_density: float, gas_level: float, 
                      humidity: float, flame_detected: bool = False, 
                      prediction: str = None, confidence: float = None) -> int:
    """Log sensor reading to database"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO sensor_readings (temperature, smoke_density, gas_level, humidity, 
                                       flame_detected, prediction, confidence)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (temperature, smoke_density, gas_level, humidity, flame_detected, prediction, confidence))
        
        reading_id = cursor.lastrowid
        conn.commit()
        return reading_id
        
    except Exception as e:
        logger.error(f"Failed to log sensor reading: {e}")
        raise
    finally:
        conn.close()

def update_robot_status(battery_level: int = None, position_x: float = None, 
                       position_y: float = None, orientation: float = None,
                       temperature: float = None, system_status: str = None,
                       active_mission: str = None) -> int:
    """Update robot status in database"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO robot_status (battery_level, position_x, position_y, orientation, 
                                    temperature, system_status, active_mission)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (battery_level, position_x, position_y, orientation, temperature, system_status, active_mission))
        
        status_id = cursor.lastrowid
        conn.commit()
        return status_id
        
    except Exception as e:
        logger.error(f"Failed to update robot status: {e}")
        raise
    finally:
        conn.close()

# Initialize database on import
if __name__ == "__main__":
    init_db()
