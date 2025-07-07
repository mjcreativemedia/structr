"""
API Authentication

Simple API key authentication for Structr API.
"""

from fastapi import HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List, Optional
import hashlib
import secrets
import time


class APIKeyAuth:
    """
    Simple API key authentication.
    
    Supports:
    - Bearer token authentication
    - API key validation
    - Rate limiting per key
    """
    
    def __init__(self, api_keys: List[str]):
        self.api_keys = set(api_keys)
        self.bearer = HTTPBearer(auto_error=False)
        
        # Rate limiting tracking
        self._rate_limits: dict = {}  # key -> {count, window_start}
        self._rate_limit_window = 60  # 1 minute
        self._rate_limit_max = 100    # requests per minute
    
    def add_api_key(self, api_key: str) -> None:
        """Add new API key"""
        self.api_keys.add(api_key)
    
    def remove_api_key(self, api_key: str) -> None:
        """Remove API key"""
        self.api_keys.discard(api_key)
    
    def generate_api_key(self, prefix: str = "sk") -> str:
        """Generate new API key"""
        random_part = secrets.token_urlsafe(32)
        return f"{prefix}-{random_part}"
    
    def validate_api_key(self, api_key: str) -> bool:
        """Validate API key"""
        return api_key in self.api_keys
    
    def check_rate_limit(self, api_key: str) -> bool:
        """Check if API key is within rate limits"""
        current_time = time.time()
        
        if api_key not in self._rate_limits:
            self._rate_limits[api_key] = {
                'count': 1,
                'window_start': current_time
            }
            return True
        
        rate_data = self._rate_limits[api_key]
        
        # Reset window if expired
        if current_time - rate_data['window_start'] > self._rate_limit_window:
            rate_data['count'] = 1
            rate_data['window_start'] = current_time
            return True
        
        # Check if over limit
        if rate_data['count'] >= self._rate_limit_max:
            return False
        
        # Increment counter
        rate_data['count'] += 1
        return True
    
    async def get_current_user(
        self, 
        request: Request,
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(None)
    ) -> Optional[str]:
        """
        Get current user/API key from request.
        Returns None if no authentication required.
        """
        # Check if auth is required
        app_config = getattr(request.app.state, 'config', {})
        if not app_config.get('require_auth', False):
            return "anonymous"
        
        # Get credentials
        if not credentials:
            credentials = await self.bearer(request)
        
        if not credentials:
            raise HTTPException(
                status_code=401,
                detail="Missing authentication credentials"
            )
        
        api_key = credentials.credentials
        
        # Validate API key
        if not self.validate_api_key(api_key):
            raise HTTPException(
                status_code=401,
                detail="Invalid API key"
            )
        
        # Check rate limits
        if not self.check_rate_limit(api_key):
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded"
            )
        
        return api_key
    
    def get_rate_limit_info(self, api_key: str) -> dict:
        """Get rate limit information for API key"""
        if api_key not in self._rate_limits:
            return {
                'requests_used': 0,
                'requests_remaining': self._rate_limit_max,
                'reset_time': time.time() + self._rate_limit_window
            }
        
        rate_data = self._rate_limits[api_key]
        current_time = time.time()
        
        # Check if window expired
        if current_time - rate_data['window_start'] > self._rate_limit_window:
            return {
                'requests_used': 0,
                'requests_remaining': self._rate_limit_max,
                'reset_time': current_time + self._rate_limit_window
            }
        
        return {
            'requests_used': rate_data['count'],
            'requests_remaining': max(0, self._rate_limit_max - rate_data['count']),
            'reset_time': rate_data['window_start'] + self._rate_limit_window
        }


# Optional user management for more advanced auth
class UserManager:
    """
    Simple user management for API access.
    Can be extended for database-backed user management.
    """
    
    def __init__(self):
        self.users: dict = {}  # user_id -> user_data
    
    def create_user(self, 
                   user_id: str,
                   name: str,
                   email: str,
                   permissions: List[str] = None) -> dict:
        """Create new user"""
        api_key = APIKeyAuth([]).generate_api_key("user")
        
        user_data = {
            'user_id': user_id,
            'name': name,
            'email': email,
            'api_key': api_key,
            'permissions': permissions or ['read'],
            'created_at': time.time(),
            'last_access': None,
            'active': True
        }
        
        self.users[user_id] = user_data
        return user_data
    
    def get_user(self, user_id: str) -> Optional[dict]:
        """Get user by ID"""
        return self.users.get(user_id)
    
    def get_user_by_api_key(self, api_key: str) -> Optional[dict]:
        """Get user by API key"""
        for user in self.users.values():
            if user.get('api_key') == api_key:
                return user
        return None
    
    def update_last_access(self, user_id: str) -> None:
        """Update user's last access time"""
        if user_id in self.users:
            self.users[user_id]['last_access'] = time.time()
    
    def has_permission(self, user_id: str, permission: str) -> bool:
        """Check if user has specific permission"""
        user = self.get_user(user_id)
        if not user or not user.get('active'):
            return False
        
        permissions = user.get('permissions', [])
        return 'admin' in permissions or permission in permissions
    
    def list_users(self) -> List[dict]:
        """List all users"""
        return list(self.users.values())


# Default permissions
PERMISSIONS = {
    'read': 'Read access to data and status',
    'write': 'Create and modify resources',
    'batch': 'Submit batch processing jobs',
    'admin': 'Full administrative access'
}