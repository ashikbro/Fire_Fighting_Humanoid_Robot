"""
Rate limiting and security middleware
"""
import time
import hashlib
from typing import Dict, Optional
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from collections import defaultdict, deque
from datetime import datetime, timedelta
import asyncio
from app.core.error_handling import logger

class RateLimiter:
    """Advanced rate limiter with multiple strategies"""
    
    def __init__(self):
        # Store for different rate limiting buckets
        self.buckets: Dict[str, Dict[str, deque]] = defaultdict(lambda: defaultdict(deque))
        self.blocked_ips: Dict[str, datetime] = {}
        self.suspicious_ips: Dict[str, int] = defaultdict(int)
        
        # Rate limiting rules
        self.rules = {
            'global': {'requests': 1000, 'window': 3600},  # 1000 req/hour global
            'per_ip': {'requests': 100, 'window': 3600},    # 100 req/hour per IP
            'auth': {'requests': 5, 'window': 300},         # 5 auth attempts per 5 min
            'api_calls': {'requests': 50, 'window': 60},    # 50 API calls per minute
            'upload': {'requests': 10, 'window': 60},       # 10 uploads per minute
        }
        
        # Cleanup task
        self._cleanup_task = None
        
    async def start_cleanup_task(self):
        """Start the cleanup task"""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            
    async def _cleanup_loop(self):
        """Cleanup old entries periodically"""
        while True:
            try:
                await asyncio.sleep(300)  # Clean every 5 minutes
                await self._cleanup_old_entries()
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
                
    async def _cleanup_old_entries(self):
        """Remove old entries from buckets"""
        current_time = time.time()
        
        for bucket_type, bucket_data in self.buckets.items():
            for key, requests in bucket_data.items():
                # Remove requests older than the window
                rule = self.rules.get(bucket_type, self.rules['global'])
                cutoff_time = current_time - rule['window']
                
                while requests and requests[0] < cutoff_time:
                    requests.popleft()
                    
        # Clean blocked IPs
        current_dt = datetime.now()
        expired_blocks = [
            ip for ip, block_time in self.blocked_ips.items()
            if current_dt - block_time > timedelta(hours=1)
        ]
        for ip in expired_blocks:
            del self.blocked_ips[ip]
            
    def get_client_identifier(self, request: Request) -> str:
        """Get unique client identifier"""
        # Try to get real IP from headers (for reverse proxy setups)
        real_ip = request.headers.get('X-Real-IP')
        forwarded_for = request.headers.get('X-Forwarded-For')
        
        if real_ip:
            client_ip = real_ip
        elif forwarded_for:
            client_ip = forwarded_for.split(',')[0].strip()
        else:
            client_ip = request.client.host if request.client else 'unknown'
            
        return client_ip
        
    def is_rate_limited(self, request: Request, rule_type: str = 'per_ip') -> tuple[bool, Optional[dict]]:
        """Check if request should be rate limited"""
        current_time = time.time()
        client_id = self.get_client_identifier(request)
        
        # Check if IP is blocked
        if client_id in self.blocked_ips:
            block_time = self.blocked_ips[client_id]
            if datetime.now() - block_time < timedelta(hours=1):
                return True, {
                    'error': 'IP temporarily blocked',
                    'retry_after': 3600,
                    'blocked_until': (block_time + timedelta(hours=1)).isoformat()
                }
            else:
                del self.blocked_ips[client_id]
                
        # Get rate limiting rule
        rule = self.rules.get(rule_type, self.rules['per_ip'])
        max_requests = rule['requests']
        window_size = rule['window']
        
        # Get request history for this client and rule type
        requests = self.buckets[rule_type][client_id]
        
        # Remove old requests outside the window
        cutoff_time = current_time - window_size
        while requests and requests[0] < cutoff_time:
            requests.popleft()
            
        # Check if limit exceeded
        if len(requests) >= max_requests:
            # Increase suspicion level
            self.suspicious_ips[client_id] += 1
            
            # Block IP if too many violations
            if self.suspicious_ips[client_id] >= 5:
                self.blocked_ips[client_id] = datetime.now()
                logger.warning(f"Blocked IP {client_id} due to repeated rate limit violations")
                
            return True, {
                'error': 'Rate limit exceeded',
                'limit': max_requests,
                'window': window_size,
                'retry_after': int(window_size - (current_time - requests[0])) if requests else window_size,
                'violations': self.suspicious_ips[client_id]
            }
            
        # Add current request to history
        requests.append(current_time)
        return False, None
        
    def get_rate_limit_headers(self, request: Request, rule_type: str = 'per_ip') -> dict:
        """Get rate limit headers for response"""
        client_id = self.get_client_identifier(request)
        rule = self.rules.get(rule_type, self.rules['per_ip'])
        requests = self.buckets[rule_type][client_id]
        
        current_time = time.time()
        cutoff_time = current_time - rule['window']
        
        # Count current requests in window
        current_requests = sum(1 for req_time in requests if req_time > cutoff_time)
        
        return {
            'X-RateLimit-Limit': str(rule['requests']),
            'X-RateLimit-Remaining': str(max(0, rule['requests'] - current_requests)),
            'X-RateLimit-Reset': str(int(current_time + rule['window'])),
            'X-RateLimit-Window': str(rule['window'])
        }

# Global rate limiter instance
rate_limiter = RateLimiter()

async def rate_limit_middleware(request: Request, call_next):
    """Rate limiting middleware for FastAPI"""
    
    # Start cleanup task if not started
    await rate_limiter.start_cleanup_task()
    
    # Determine rule type based on path
    path = request.url.path
    rule_type = 'per_ip'  # Default
    
    if '/auth/' in path:
        rule_type = 'auth'
    elif '/upload' in path:
        rule_type = 'upload'
    elif '/api/' in path:
        rule_type = 'api_calls'
        
    # Check rate limit
    is_limited, limit_info = rate_limiter.is_rate_limited(request, rule_type)
    
    if is_limited:
        logger.warning(f"Rate limit exceeded for {rate_limiter.get_client_identifier(request)}: {limit_info}")
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                'success': False,
                'message': 'Rate limit exceeded',
                'details': limit_info
            },
            headers={'Retry-After': str(limit_info.get('retry_after', 60))}
        )
    
    # Process request
    response = await call_next(request)
    
    # Add rate limit headers
    headers = rate_limiter.get_rate_limit_headers(request, rule_type)
    for key, value in headers.items():
        response.headers[key] = value
        
    return response

class SecurityMiddleware:
    """Security middleware for additional protections"""
    
    def __init__(self):
        self.suspicious_patterns = [
            # SQL injection patterns
            r'union\s+select', r'drop\s+table', r'insert\s+into',
            # XSS patterns  
            r'<script', r'javascript:', r'onerror=',
            # Path traversal
            r'\.\./', r'\.\.\\', 
            # Command injection
            r';\s*rm\s+', r';\s*cat\s+', r'&&', r'\|\|'
        ]
        
    async def __call__(self, request: Request, call_next):
        """Security middleware handler"""
        
        # Check for suspicious patterns in URL and query params
        full_url = str(request.url)
        if self._contains_suspicious_pattern(full_url):
            logger.warning(f"Suspicious request detected from {request.client.host}: {full_url}")
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={'success': False, 'message': 'Request blocked by security filter'}
            )
        
        # Add security headers to response
        response = await call_next(request)
        
        # Security headers
        security_headers = {
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block',
            'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
            'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'",
            'Referrer-Policy': 'strict-origin-when-cross-origin'
        }
        
        for key, value in security_headers.items():
            response.headers[key] = value
            
        return response
        
    def _contains_suspicious_pattern(self, text: str) -> bool:
        """Check if text contains suspicious patterns"""
        import re
        text_lower = text.lower()
        
        for pattern in self.suspicious_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return True
                
        return False

# Export middleware instances
security_middleware = SecurityMiddleware()

__all__ = ['rate_limiter', 'rate_limit_middleware', 'security_middleware', 'RateLimiter', 'SecurityMiddleware']
