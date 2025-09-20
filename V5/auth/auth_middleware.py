import streamlit as st
from typing import Dict, Any, Optional, Callable
import logging
from auth.jwt_manager import jwt_manager
from auth.user_manager import user_manager
from auth.authorization_manager import authorization_manager

logger = logging.getLogger(__name__)

class AuthMiddleware:
    def __init__(self):
        pass
    
    def require_auth(self, func: Callable) -> Callable:
        """Decorator to require authentication"""
        def wrapper(*args, **kwargs):
            if not jwt_manager.is_authenticated():
                self.show_login_form()
                return None
            return func(*args, **kwargs)
        return wrapper
    
    def show_login_form(self):
        """Display login form"""
        st.markdown("### 🔐 Authentication Required")
        
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login")
            
            if submit:
                user_data = user_manager.authenticate_user(username, password)
                if user_data:
                    token = jwt_manager.create_token(
                        user_data["user_id"],
                        user_data["username"],
                        user_data["roles"],
                        user_data["permissions"]
                    )
                    st.session_state.auth_token = token
                    st.session_state.current_user = user_data
                    st.success("Login successful!")
                    st.rerun()
                else:
                    st.error("Invalid credentials")
    
    def show_user_info(self):
        """Display current user info in sidebar"""
        current_user = jwt_manager.get_current_user()
        if current_user:
            with st.sidebar:
                st.markdown("---")
                st.markdown("### 👤 User Info")
                st.write(f"**User:** {current_user['username']}")
                st.write(f"**Roles:** {', '.join(current_user['roles'])}")
                
                if st.button("🚪 Logout"):
                    jwt_manager.logout()
                    st.rerun()
    
    def check_query_authorization(self, sql_query: str) -> tuple[bool, str]:
        """Check if current user is authorized to execute query"""
        current_user = jwt_manager.get_current_user()
        if not current_user:
            return False, "User not authenticated"
        
        user_permissions = current_user.get("permissions", {})
        return authorization_manager.authorize_sql_query(sql_query, user_permissions)
    
    def get_filtered_schema(self, schema_info: Dict[str, Any]) -> Dict[str, Any]:
        """Get schema filtered by user permissions (for display only)"""
        current_user = jwt_manager.get_current_user()
        if not current_user:
            return {}
        
        user_permissions = current_user.get("permissions", {})
        return authorization_manager.filter_schema_metadata(schema_info, user_permissions)

auth_middleware = AuthMiddleware()
