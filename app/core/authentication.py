"""
JWT-based authentication system
"""
import jwt
import bcrypt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import sqlite3
import os
from app.core.error_handling import logger
from app.core.config_manager import config

security = HTTPBearer()

class AuthManager:
    """JWT Authentication Manager"""
    
    def __init__(self):
        self.secret_key = config.security.jwt_secret
        self.algorithm = "HS256"
        self.token_expiry = config.security.token_expiry
        self.db_path = os.path.join(os.path.dirname(__file__), "..", "firebot.db")
        
    def hash_password(self, password: str) -> str:
        """Hash a password using bcrypt"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify a password against its hash"""
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    
    def create_user(self, username: str, password: str, role: str = "operator") -> bool:
        """Create a new user"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if user already exists
            cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
            if cursor.fetchone():
                return False
            
            # Hash password and create user
            password_hash = self.hash_password(password)
            cursor.execute("""
                INSERT INTO users (username, password_hash, role, is_active)
                VALUES (?, ?, ?, 1)
            """, (username, password_hash, role))
            
            conn.commit()
            logger.info(f"Created user: {username} with role: {role}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create user {username}: {e}")
            return False
        finally:
            conn.close()
    
    def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate a user and return user data"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, username, password_hash, role, is_active 
                FROM users WHERE username = ? AND is_active = 1
            """, (username,))
            
            user = cursor.fetchone()
            if not user:
                return None
            
            if self.verify_password(password, user['password_hash']):
                # Update last login
                cursor.execute("""
                    UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?
                """, (user['id'],))
                conn.commit()
                
                return {
                    'id': user['id'],
                    'username': user['username'],
                    'role': user['role']
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Authentication failed for {username}: {e}")
            return None
        finally:
            conn.close()
    
    def create_access_token(self, user_data: Dict[str, Any]) -> str:
        """Create a JWT access token"""
        payload = {
            'user_id': user_data['id'],
            'username': user_data['username'],
            'role': user_data['role'],
            'exp': datetime.utcnow() + timedelta(seconds=self.token_expiry),
            'iat': datetime.utcnow()
        }
        
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode a JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("Token has expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return None
    
    def get_current_user(self, credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
        """Get current user from JWT token"""
        token = credentials.credentials
        payload = self.verify_token(token)
        
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return payload
    
    def require_role(self, required_role: str):
        """Decorator to require specific role"""
        def role_checker(current_user: Dict = Depends(self.get_current_user)):
            user_role = current_user.get('role')
            if user_role != required_role and user_role != 'admin':
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Access denied. Required role: {required_role}"
                )
            return current_user
        return role_checker
    
    def require_admin(self, current_user: Dict = Depends(get_current_user)):
        """Require admin role"""
        if current_user.get('role') != 'admin':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )
        return current_user

# Global auth manager instance
auth_manager = AuthManager()

# Convenience functions
def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    return auth_manager.get_current_user(credentials)

def require_admin(current_user: Dict = Depends(get_current_user)):
    return auth_manager.require_admin(current_user)

def require_operator():
    return auth_manager.require_role("operator")

# Export commonly used items
__all__ = [
    'AuthManager', 'auth_manager', 'get_current_user', 
    'require_admin', 'require_operator'
]
