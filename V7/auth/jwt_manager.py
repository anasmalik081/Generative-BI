import jwt
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import streamlit as st
from config.settings import settings
import logging

logger = logging.getLogger(__name__)

class JWTManager:
    def __init__(self):
        self.secret_key = self._get_secret_key()
        self.algorithm = "HS256"
        self.token_expiry_hours = 24
    
    def _get_secret_key(self) -> str:
        """Generate or retrieve secret key"""
        # Use a combination of settings for secret key generation
        base_string = f"{settings.groq_api_key or settings.openai_api_key}genbi_secret"
        return hashlib.sha256(base_string.encode()).hexdigest()
    
    def create_token(self, user_id: str, username: str, roles: list, permissions: dict = None) -> str:
        """Create JWT token for user"""
        payload = {
            "user_id": user_id,
            "username": username,
            "roles": roles,
            "permissions": permissions or {"databases": ["*"], "tables": ["*"], "columns": ["*"]},
            "exp": datetime.utcnow() + timedelta(hours=self.token_expiry_hours),
            "iat": datetime.utcnow()
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("Token has expired")
            return None
        except jwt.InvalidTokenError:
            logger.warning("Invalid token")
            return None
    
    def get_current_user(self) -> Optional[Dict[str, Any]]:
        """Get current user from session state"""
        if 'auth_token' in st.session_state:
            return self.verify_token(st.session_state.auth_token)
        return None
    
    def is_authenticated(self) -> bool:
        """Check if user is authenticated"""
        return self.get_current_user() is not None
    
    def logout(self):
        """Clear authentication from session"""
        if 'auth_token' in st.session_state:
            del st.session_state.auth_token
        if 'current_user' in st.session_state:
            del st.session_state.current_user

jwt_manager = JWTManager()
