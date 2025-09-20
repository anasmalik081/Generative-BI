from typing import Dict, List, Any, Optional, Tuple
import re
import logging
from auth.jwt_manager import jwt_manager

logger = logging.getLogger(__name__)

class AuthorizationManager:
    def __init__(self):
        pass
    
    def check_database_access(self, database_name: str, user_permissions: Dict[str, List[str]]) -> bool:
        """Check if user has access to database"""
        allowed_databases = user_permissions.get("databases", [])
        return "*" in allowed_databases or database_name in allowed_databases
    
    def check_table_access(self, table_name: str, user_permissions: Dict[str, List[str]]) -> bool:
        """Check if user has access to table"""
        allowed_tables = user_permissions.get("tables", [])
        return "*" in allowed_tables or table_name in allowed_tables
    
    def check_column_access(self, table_name: str, column_name: str, 
                          user_permissions: Dict[str, List[str]]) -> bool:
        """Check if user has access to specific column"""
        allowed_columns = user_permissions.get("columns", [])
        
        # Check for wildcard access
        if "*" in allowed_columns:
            return True
        
        # Check for table.column format
        full_column = f"{table_name}.{column_name}"
        if full_column in allowed_columns:
            return True
        
        # Check for column name only
        return column_name in allowed_columns
    
    def extract_sql_objects(self, sql_query: str) -> Dict[str, List[str]]:
        """Extract tables and columns from SQL query"""
        sql_lower = sql_query.lower()
        
        # Extract tables from FROM and JOIN clauses
        tables = []
        from_pattern = r'\bfrom\s+([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)?)'
        join_pattern = r'\bjoin\s+([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)?)'
        
        tables.extend(re.findall(from_pattern, sql_lower))
        tables.extend(re.findall(join_pattern, sql_lower))
        
        # Extract columns from SELECT clause
        columns = []
        select_pattern = r'\bselect\s+(.*?)\s+from'
        select_match = re.search(select_pattern, sql_lower, re.DOTALL)
        
        if select_match:
            select_clause = select_match.group(1)
            # Simple column extraction (can be enhanced)
            column_pattern = r'([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)?)'
            columns.extend(re.findall(column_pattern, select_clause))
        
        return {
            "tables": list(set(tables)),
            "columns": list(set(columns))
        }
    
    def authorize_sql_query(self, sql_query: str, user_permissions: Dict[str, List[str]]) -> Tuple[bool, str]:
        """Authorize SQL query against user permissions"""
        try:
            sql_objects = self.extract_sql_objects(sql_query)
            
            # Check table access
            for table in sql_objects["tables"]:
                if not self.check_table_access(table, user_permissions):
                    return False, f"Access denied to table: {table}"
            
            # Check column access
            for column in sql_objects["columns"]:
                # Extract table name if column is in table.column format
                if "." in column:
                    table_name, col_name = column.split(".", 1)
                    if not self.check_column_access(table_name, col_name, user_permissions):
                        return False, f"Access denied to column: {column}"
                else:
                    # For columns without table prefix, check against all accessed tables
                    has_access = False
                    for table in sql_objects["tables"]:
                        if self.check_column_access(table, column, user_permissions):
                            has_access = True
                            break
                    
                    if not has_access:
                        return False, f"Access denied to column: {column}"
            
            return True, "Query authorized"
            
        except Exception as e:
            logger.error(f"Error authorizing query: {e}")
            return False, "Authorization check failed"
    
    def filter_schema_metadata(self, schema_info: Dict[str, Any], 
                             user_permissions: Dict[str, List[str]]) -> Dict[str, Any]:
        """Filter schema metadata based on user permissions (for display only)"""
        filtered_schema = {}
        
        for table_name, table_info in schema_info.items():
            if self.check_table_access(table_name, user_permissions):
                filtered_columns = {}
                
                for column_name, column_info in table_info.get("columns", {}).items():
                    if self.check_column_access(table_name, column_name, user_permissions):
                        filtered_columns[column_name] = column_info
                
                if filtered_columns:  # Only include table if user has access to at least one column
                    filtered_schema[table_name] = {
                        **table_info,
                        "columns": filtered_columns
                    }
        
        return filtered_schema
    
    def get_current_user_permissions(self) -> Optional[Dict[str, List[str]]]:
        """Get current user's permissions"""
        current_user = jwt_manager.get_current_user()
        return current_user.get("permissions") if current_user else None
    
    def is_admin_user(self) -> bool:
        """Check if current user is admin"""
        current_user = jwt_manager.get_current_user()
        if current_user:
            return "admin" in current_user.get("roles", [])
        return False

authorization_manager = AuthorizationManager()
