import streamlit as st
from typing import Dict, List, Any
from auth.user_manager import user_manager
from auth.jwt_manager import jwt_manager
from auth.authorization_manager import authorization_manager
import logging

logger = logging.getLogger(__name__)

class AdminInterface:
    def __init__(self):
        pass
    
    def show_admin_panel(self):
        """Show admin panel if user is admin"""
        if not authorization_manager.is_admin_user():
            return
        
        with st.sidebar:
            st.markdown("---")
            st.markdown("### 👑 Admin Panel")
            
            if st.button("👥 Manage Users"):
                st.session_state.show_admin_panel = True
        
        # Show admin panel in main area if requested
        if st.session_state.get('show_admin_panel', False):
            self._render_user_management()
    
    def _render_user_management(self):
        """Render user management interface"""
        st.markdown("## 👥 User Management")
        
        tab1, tab2 = st.tabs(["Create User", "Manage Permissions"])
        
        with tab1:
            self._render_create_user()
        
        with tab2:
            self._render_manage_permissions()
        
        if st.button("🔙 Back to Main"):
            st.session_state.show_admin_panel = False
            st.rerun()
    
    def _render_create_user(self):
        """Render create user form"""
        st.markdown("### ➕ Create New User")
        
        with st.form("create_user_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            
            st.markdown("**Roles:**")
            is_admin = st.checkbox("Admin")
            is_analyst = st.checkbox("Analyst", value=True)
            
            st.markdown("**Database Permissions:**")
            databases = st.text_area("Databases (comma-separated, * for all)", value="*")
            
            st.markdown("**Table Permissions:**")
            tables = st.text_area("Tables (comma-separated, * for all)", value="*")
            
            st.markdown("**Column Permissions:**")
            columns = st.text_area("Columns (comma-separated, * for all)", value="*")
            
            submit = st.form_submit_button("Create User")
            
            if submit:
                if username and password:
                    roles = []
                    if is_admin:
                        roles.append("admin")
                    if is_analyst:
                        roles.append("analyst")
                    
                    permissions = {
                        "databases": [db.strip() for db in databases.split(",") if db.strip()],
                        "tables": [table.strip() for table in tables.split(",") if table.strip()],
                        "columns": [col.strip() for col in columns.split(",") if col.strip()]
                    }
                    
                    if user_manager.create_user(username, password, roles, permissions):
                        st.success(f"User '{username}' created successfully!")
                    else:
                        st.error("Failed to create user. Username might already exist.")
                else:
                    st.error("Please provide username and password")
    
    def _render_manage_permissions(self):
        """Render permission management interface"""
        st.markdown("### 🔐 Manage User Permissions")
        
        # This is a simplified version - in production, you'd load actual users
        st.info("Permission management interface - extend based on your needs")
        
        sample_permissions = {
            "databases": ["sales_db", "analytics_db"],
            "tables": ["customers", "orders", "products"],
            "columns": ["customer_name", "order_date", "total_amount"]
        }
        
        st.json(sample_permissions)

admin_interface = AdminInterface()
