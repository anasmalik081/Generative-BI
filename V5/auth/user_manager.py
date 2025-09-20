import json
import hashlib
from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class UserManager:
    def __init__(self):
        self.users_file = Path("auth/users.json")
        self.users_file.parent.mkdir(exist_ok=True)
        self._initialize_users()
    
    def _initialize_users(self):
        """Initialize users file with default admin user"""
        if not self.users_file.exists():
            default_users = {
                "admin": {
                    "user_id": "admin",
                    "username": "admin",
                    "password_hash": self._hash_password("admin123"),
                    "roles": ["admin"],
                    "permissions": {
                        "databases": ["*"],
                        "tables": ["*"],
                        "columns": ["*"]
                    },
                    "created_at": "2024-01-01T00:00:00Z"
                }
            }
            self._save_users(default_users)
    
    def _hash_password(self, password: str) -> str:
        """Hash password using SHA256"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def _load_users(self) -> Dict[str, Any]:
        """Load users from file"""
        try:
            with open(self.users_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading users: {e}")
            return {}
    
    def _save_users(self, users: Dict[str, Any]):
        """Save users to file"""
        try:
            with open(self.users_file, 'w') as f:
                json.dump(users, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving users: {e}")
    
    def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate user credentials"""
        users = self._load_users()
        user = users.get(username)
        
        if user and user["password_hash"] == self._hash_password(password):
            return {
                "user_id": user["user_id"],
                "username": user["username"],
                "roles": user["roles"],
                "permissions": user["permissions"]
            }
        return None
    
    def create_user(self, username: str, password: str, roles: List[str], 
                   permissions: Dict[str, List[str]]) -> bool:
        """Create new user"""
        users = self._load_users()
        
        if username in users:
            return False
        
        users[username] = {
            "user_id": username,
            "username": username,
            "password_hash": self._hash_password(password),
            "roles": roles,
            "permissions": permissions,
            "created_at": datetime.utcnow().isoformat() + "Z"
        }
        
        self._save_users(users)
        return True
    
    def get_user_permissions(self, username: str) -> Optional[Dict[str, List[str]]]:
        """Get user permissions"""
        users = self._load_users()
        user = users.get(username)
        return user["permissions"] if user else None
    
    def update_user_permissions(self, username: str, permissions: Dict[str, List[str]]) -> bool:
        """Update user permissions"""
        users = self._load_users()
        
        if username not in users:
            return False
        
        users[username]["permissions"] = permissions
        self._save_users(users)
        return True

user_manager = UserManager()
