"""
Comprehensive audit logging system for security and compliance
"""
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from enum import Enum
from dataclasses import dataclass, asdict
from pathlib import Path
import hashlib
import uuid

from app.core.error_handling import logger

class AuditEventType(Enum):
    """Types of audit events"""
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    USER_LOGIN_FAILED = "user_login_failed"
    USER_CREATED = "user_created"
    USER_DELETED = "user_deleted"
    USER_MODIFIED = "user_modified"
    
    ROBOT_COMMAND = "robot_command"
    ROBOT_STATUS_CHANGE = "robot_status_change"
    EMERGENCY_STOP = "emergency_stop"
    FIRE_DETECTION = "fire_detection"
    SUPPRESSION_ACTIVATED = "suppression_activated"
    
    API_ACCESS = "api_access"
    API_ERROR = "api_error"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    SECURITY_VIOLATION = "security_violation"
    
    DATA_ACCESS = "data_access"
    DATA_MODIFICATION = "data_modification"
    DATA_DELETION = "data_deletion"
    
    CONFIG_CHANGE = "config_change"
    SYSTEM_STARTUP = "system_startup"
    SYSTEM_SHUTDOWN = "system_shutdown"
    
    FILE_UPLOAD = "file_upload"
    FILE_DOWNLOAD = "file_download"
    FILE_DELETION = "file_deletion"

@dataclass
class AuditEvent:
    """Audit event data structure"""
    event_id: str
    event_type: str
    timestamp: datetime
    user_id: Optional[str]
    username: Optional[str]
    source_ip: Optional[str]
    user_agent: Optional[str]
    resource: Optional[str]
    action: str
    result: str  # success, failure, error
    details: Dict[str, Any]
    risk_level: str  # low, medium, high, critical
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['details'] = json.dumps(self.details)
        return data

class AuditLogger:
    """Advanced audit logging system"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or Path(__file__).parent.parent / "audit_log.db"
        self.init_database()
        
    def init_database(self):
        """Initialize audit log database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT UNIQUE NOT NULL,
                    event_type TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    user_id TEXT,
                    username TEXT,
                    source_ip TEXT,
                    user_agent TEXT,
                    resource TEXT,
                    action TEXT NOT NULL,
                    result TEXT NOT NULL,
                    details TEXT,
                    risk_level TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    checksum TEXT
                )
            ''')
            
            # Create indexes for better performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_event_type ON audit_log(event_type)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON audit_log(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_id ON audit_log(user_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_risk_level ON audit_log(risk_level)')
            
            conn.commit()
            logger.info("Audit log database initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize audit database: {e}")
            raise
        finally:
            conn.close()
    
    def _calculate_checksum(self, event: AuditEvent) -> str:
        """Calculate integrity checksum for audit event"""
        data_string = f"{event.event_id}{event.event_type}{event.timestamp.isoformat()}{event.action}{event.result}"
        return hashlib.sha256(data_string.encode()).hexdigest()
    
    def log_event(self, 
                  event_type: AuditEventType,
                  action: str,
                  result: str = "success",
                  user_id: str = None,
                  username: str = None,
                  source_ip: str = None,
                  user_agent: str = None,
                  resource: str = None,
                  details: Dict[str, Any] = None,
                  risk_level: str = "low") -> str:
        """Log an audit event"""
        
        event = AuditEvent(
            event_id=str(uuid.uuid4()),
            event_type=event_type.value,
            timestamp=datetime.utcnow(),
            user_id=user_id,
            username=username,
            source_ip=source_ip,
            user_agent=user_agent,
            resource=resource,
            action=action,
            result=result,
            details=details or {},
            risk_level=risk_level
        )
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Calculate checksum for integrity
            checksum = self._calculate_checksum(event)
            
            cursor.execute('''
                INSERT INTO audit_log (
                    event_id, event_type, timestamp, user_id, username,
                    source_ip, user_agent, resource, action, result,
                    details, risk_level, checksum
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                event.event_id, event.event_type, event.timestamp.isoformat(),
                event.user_id, event.username, event.source_ip, event.user_agent,
                event.resource, event.action, event.result,
                json.dumps(event.details), event.risk_level, checksum
            ))
            
            conn.commit()
            
            # Log high-risk events to application log as well
            if risk_level in ['high', 'critical']:
                logger.warning(f"HIGH RISK AUDIT EVENT: {event_type.value} - {action} by {username or 'unknown'}")
            
            return event.event_id
            
        except Exception as e:
            logger.error(f"Failed to log audit event: {e}")
            raise
        finally:
            conn.close()
    
    def get_events(self, 
                   event_type: Optional[str] = None,
                   user_id: Optional[str] = None,
                   risk_level: Optional[str] = None,
                   start_time: Optional[datetime] = None,
                   end_time: Optional[datetime] = None,
                   limit: int = 1000) -> List[Dict[str, Any]]:
        """Retrieve audit events with filtering"""
        
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query = "SELECT * FROM audit_log WHERE 1=1"
            params = []
            
            if event_type:
                query += " AND event_type = ?"
                params.append(event_type)
                
            if user_id:
                query += " AND user_id = ?"
                params.append(user_id)
                
            if risk_level:
                query += " AND risk_level = ?"
                params.append(risk_level)
                
            if start_time:
                query += " AND timestamp >= ?"
                params.append(start_time.isoformat())
                
            if end_time:
                query += " AND timestamp <= ?"
                params.append(end_time.isoformat())
            
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            events = cursor.fetchall()
            
            return [dict(event) for event in events]
            
        except Exception as e:
            logger.error(f"Failed to retrieve audit events: {e}")
            return []
        finally:
            conn.close()
    
    def get_security_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get security summary for the last N hours"""
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            since_time = datetime.utcnow().replace(microsecond=0) - timedelta(hours=hours)
            
            # Count events by type
            cursor.execute('''
                SELECT event_type, COUNT(*) as count
                FROM audit_log 
                WHERE timestamp >= ?
                GROUP BY event_type
            ''', (since_time.isoformat(),))
            
            event_counts = dict(cursor.fetchall())
            
            # Count by risk level
            cursor.execute('''
                SELECT risk_level, COUNT(*) as count
                FROM audit_log 
                WHERE timestamp >= ?
                GROUP BY risk_level
            ''', (since_time.isoformat(),))
            
            risk_counts = dict(cursor.fetchall())
            
            # Failed login attempts
            cursor.execute('''
                SELECT COUNT(*) as count
                FROM audit_log 
                WHERE timestamp >= ? AND event_type = ? AND result = ?
            ''', (since_time.isoformat(), AuditEventType.USER_LOGIN_FAILED.value, 'failure'))
            
            failed_logins = cursor.fetchone()[0]
            
            # Security violations
            cursor.execute('''
                SELECT COUNT(*) as count
                FROM audit_log 
                WHERE timestamp >= ? AND event_type = ?
            ''', (since_time.isoformat(), AuditEventType.SECURITY_VIOLATION.value))
            
            security_violations = cursor.fetchone()[0]
            
            return {
                'time_range_hours': hours,
                'total_events': sum(event_counts.values()),
                'event_counts': event_counts,
                'risk_counts': risk_counts,
                'failed_logins': failed_logins,
                'security_violations': security_violations,
                'alerts': self._generate_security_alerts(event_counts, risk_counts, failed_logins, security_violations)
            }
            
        except Exception as e:
            logger.error(f"Failed to generate security summary: {e}")
            return {}
        finally:
            conn.close()
    
    def _generate_security_alerts(self, event_counts, risk_counts, failed_logins, violations) -> List[str]:
        """Generate security alerts based on audit data"""
        alerts = []
        
        if failed_logins > 10:
            alerts.append(f"High number of failed login attempts: {failed_logins}")
            
        if violations > 0:
            alerts.append(f"Security violations detected: {violations}")
            
        if risk_counts.get('critical', 0) > 0:
            alerts.append(f"Critical risk events detected: {risk_counts['critical']}")
            
        if risk_counts.get('high', 0) > 5:
            alerts.append(f"High number of high-risk events: {risk_counts['high']}")
            
        return alerts
    
    def verify_integrity(self, event_id: str) -> bool:
        """Verify the integrity of an audit event"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM audit_log WHERE event_id = ?', (event_id,))
            row = cursor.fetchone()
            
            if not row:
                return False
            
            # Recreate event and calculate checksum
            event = AuditEvent(
                event_id=row['event_id'],
                event_type=row['event_type'],
                timestamp=datetime.fromisoformat(row['timestamp']),
                user_id=row['user_id'],
                username=row['username'],
                source_ip=row['source_ip'],
                user_agent=row['user_agent'],
                resource=row['resource'],
                action=row['action'],
                result=row['result'],
                details=json.loads(row['details'] or '{}'),
                risk_level=row['risk_level']
            )
            
            calculated_checksum = self._calculate_checksum(event)
            stored_checksum = row['checksum']
            
            return calculated_checksum == stored_checksum
            
        except Exception as e:
            logger.error(f"Failed to verify audit event integrity: {e}")
            return False
        finally:
            conn.close()

# Global audit logger instance
audit_logger = AuditLogger()

# Convenience functions for common audit events
def log_user_login(username: str, user_id: str, source_ip: str, success: bool = True):
    """Log user login event"""
    audit_logger.log_event(
        event_type=AuditEventType.USER_LOGIN if success else AuditEventType.USER_LOGIN_FAILED,
        action="login",
        result="success" if success else "failure",
        user_id=user_id if success else None,
        username=username,
        source_ip=source_ip,
        risk_level="low" if success else "medium"
    )

def log_robot_command(username: str, user_id: str, command: str, details: Dict[str, Any]):
    """Log robot command event"""
    audit_logger.log_event(
        event_type=AuditEventType.ROBOT_COMMAND,
        action=command,
        result="success",
        user_id=user_id,
        username=username,
        details=details,
        risk_level="medium"
    )

def log_security_violation(source_ip: str, violation_type: str, details: Dict[str, Any]):
    """Log security violation"""
    audit_logger.log_event(
        event_type=AuditEventType.SECURITY_VIOLATION,
        action=violation_type,
        result="blocked",
        source_ip=source_ip,
        details=details,
        risk_level="high"
    )

def log_fire_detection(location: str, confidence: float, details: Dict[str, Any]):
    """Log fire detection event"""
    audit_logger.log_event(
        event_type=AuditEventType.FIRE_DETECTION,
        action="fire_detected",
        result="success",
        resource=location,
        details={**details, "confidence": confidence},
        risk_level="critical"
    )

# Export commonly used items
__all__ = [
    'AuditEventType', 'AuditEvent', 'AuditLogger', 'audit_logger',
    'log_user_login', 'log_robot_command', 'log_security_violation', 'log_fire_detection'
]
