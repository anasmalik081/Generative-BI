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
        """Create new user in both app and database"""
        users = self._load_users()
        
        if username in users:
            return False
        
        # Create database user with same credentials
        if not self._create_database_user(username, password, permissions):
            logger.error(f"Failed to create database user for {username}")
            return False
        
        users[username] = {
            "user_id": username,
            "username": username,
            "password_hash": self._hash_password(password),
            "db_password": password,  # Store plain password for DB connections
            "roles": roles,
            "permissions": permissions,
            "created_at": datetime.utcnow().isoformat() + "Z"
        }
        
        self._save_users(users)
        return True
    
    def _create_database_user(self, username: str, password: str, permissions: Dict[str, List[str]]) -> bool:
        """Create PostgreSQL user with permissions"""
        try:
            from database.connection_manager import db_manager
            from sqlalchemy import text
            
            # Get admin connection
            admin_conn = db_manager.get_connection()
            
            # Use the actual database name from the established connection
            actual_db_name = db_manager.current_db
            logger.info(f"Using database name: {actual_db_name}")
            
            # Create user (handle if user already exists)
            try:
                admin_conn.execute(text(f"CREATE USER {username} WITH PASSWORD '{password}'"))
                logger.info(f"Created PostgreSQL user: {username}")
            except Exception as e:
                if "already exists" in str(e).lower():
                    logger.info(f"Database user {username} already exists, updating permissions...")
                else:
                    raise e
            
            # Grant database permissions with proper quoting
            databases = permissions.get("databases", [])
            if "*" in databases:
                # Use double quotes to preserve case
                admin_conn.execute(text(f'GRANT ALL PRIVILEGES ON DATABASE "{actual_db_name}" TO {username}'))
            else:
                admin_conn.execute(text(f'GRANT CONNECT ON DATABASE "{actual_db_name}" TO {username}'))
            
            # Grant table permissions
            tables = permissions.get("tables", [])
            if "*" in tables:
                admin_conn.execute(text(f"GRANT SELECT ON ALL TABLES IN SCHEMA public TO {username}"))
            else:
                for table in tables:
                    try:
                        admin_conn.execute(text(f"GRANT SELECT ON {table} TO {username}"))
                    except Exception as e:
                        logger.warning(f"Could not grant access to table {table}: {e}")
            
            # Commit the transaction
            admin_conn.commit()
            admin_conn.close()
            
            logger.info(f"Database user {username} created successfully with permissions")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create database user {username}: {e}")
            return False
    
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
