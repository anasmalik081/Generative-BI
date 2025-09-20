from sqlalchemy import create_engine, text, MetaData, inspect
from sqlalchemy.orm import sessionmaker
from typing import Dict, List, Any, Optional
import pandas as pd
from config.settings import settings
import logging

logger = logging.getLogger(__name__)

class DatabaseConnectionManager:
    def __init__(self):
        self.engines = {}
        self.sessions = {}
        self.metadata_cache = {}
    
    def get_connection_string(self, db_type: str, **kwargs) -> str:
        """Generate connection string based on database type"""
        if db_type.lower() == 'postgresql':
            return f"postgresql://{settings.postgres_user}:{settings.postgres_password}@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
        elif db_type.lower() == 'mysql':
            return f"mysql+pymysql://{settings.mysql_user}:{settings.mysql_password}@{settings.mysql_host}:{settings.mysql_port}/{settings.mysql_db}"
        elif db_type.lower() == 'oracle':
            return f"oracle+cx_oracle://{settings.oracle_user}:{settings.oracle_password}@{settings.oracle_host}:{settings.oracle_port}/{settings.oracle_service}"
        else:
            raise ValueError(f"Unsupported database type: {db_type}")
    
    def connect(self, db_type: str, connection_name: str = "default") -> bool:
        """Establish database connection"""
        try:
            connection_string = self.get_connection_string(db_type)
            engine = create_engine(
                connection_string,
                pool_size=10,
                max_overflow=20,
                pool_pre_ping=True,
                pool_recycle=3600
            )
            
            # Test connection
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            
            self.engines[connection_name] = engine
            Session = sessionmaker(bind=engine)
            self.sessions[connection_name] = Session()
            
            logger.info(f"Successfully connected to {db_type} database")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to {db_type}: {str(e)}")
            return False
    
    def execute_query(self, query: str, connection_name: str = "default") -> pd.DataFrame:
        """Execute SQL query and return results as DataFrame"""
        try:
            if connection_name not in self.engines:
                raise ValueError(f"No connection found for {connection_name}")
            
            with self.engines[connection_name].connect() as conn:
                result = pd.read_sql(query, conn)
                
            logger.info(f"Query executed successfully, returned {len(result)} rows")
            return result
            
        except Exception as e:
            logger.error(f"Query execution failed: {str(e)}")
            raise
    
    def get_table_schema(self, connection_name: str = "default", include_views: bool = False) -> Dict[str, List[Dict]]:
        """Get complete database schema information for actual tables only"""
        try:
            if connection_name not in self.engines:
                raise ValueError(f"No connection found for {connection_name}")
            
            if connection_name in self.metadata_cache:
                return self.metadata_cache[connection_name]
            
            inspector = inspect(self.engines[connection_name])
            schema_info = {}
            
            # Get only actual tables (not views, functions, etc.)
            all_tables = inspector.get_table_names()
            
            # Filter out PostgreSQL system tables and get only user tables
            user_tables = []
            for table_name in all_tables:
                # Skip PostgreSQL system tables, information schema, and other system objects
                if not table_name.startswith(('pg_', 'information_schema', 'sql_')):
                    # Additional check: verify it's actually a table by trying to get columns
                    try:
                        columns = inspector.get_columns(table_name)
                        if columns:  # Only include if it has columns (actual table)
                            user_tables.append(table_name)
                    except:
                        # Skip if we can't get columns (might be a function or other object)
                        continue
            
            # Optionally include views if requested
            if include_views:
                try:
                    all_views = inspector.get_view_names()
                    user_views = []
                    for view_name in all_views:
                        if not view_name.startswith(('pg_', 'information_schema', 'sql_')):
                            try:
                                columns = inspector.get_columns(view_name)
                                if columns:
                                    user_views.append(view_name)
                            except:
                                continue
                    user_tables.extend(user_views)
                except:
                    # Some databases might not support views or might error
                    pass
            
            logger.info(f"Found {len(user_tables)} user tables (filtered from {len(all_tables)} total objects)")
            
            for table_name in user_tables:
                try:
                    columns = []
                    table_columns = inspector.get_columns(table_name)
                    
                    for column in table_columns:
                        columns.append({
                            'name': column['name'],
                            'type': str(column['type']),
                            'nullable': column['nullable'],
                            'default': column.get('default'),
                            'primary_key': column.get('primary_key', False)
                        })
                    
                    # Get foreign keys
                    try:
                        foreign_keys = inspector.get_foreign_keys(table_name)
                    except:
                        foreign_keys = []
                    
                    # Get indexes
                    try:
                        indexes = inspector.get_indexes(table_name)
                    except:
                        indexes = []
                    
                    schema_info[table_name] = {
                        'columns': columns,
                        'foreign_keys': foreign_keys,
                        'indexes': indexes,
                        'table_type': 'table'  # Mark as actual table
                    }
                    
                except Exception as e:
                    logger.warning(f"Failed to get schema for table {table_name}: {str(e)}")
                    # Continue with other tables
                    continue
            
            self.metadata_cache[connection_name] = schema_info
            logger.info(f"Successfully cached schema for {len(schema_info)} actual tables")
            return schema_info
            
        except Exception as e:
            logger.error(f"Failed to get schema: {str(e)}")
            raise
    
    def get_sample_data(self, table_name: str, limit: int = 5, connection_name: str = "default") -> pd.DataFrame:
        """Get sample data from a table"""
        try:
            query = f"SELECT * FROM {table_name} LIMIT {limit}"
            return self.execute_query(query, connection_name)
        except Exception as e:
            logger.error(f"Failed to get sample data from {table_name}: {str(e)}")
            return pd.DataFrame()
    
    def close_connections(self):
        """Close all database connections"""
        for session in self.sessions.values():
            session.close()
        for engine in self.engines.values():
            engine.dispose()
        
        self.engines.clear()
        self.sessions.clear()
        logger.info("All database connections closed")

# Global instance
db_manager = DatabaseConnectionManager()
