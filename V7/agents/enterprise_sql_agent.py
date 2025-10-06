from langchain.prompts import ChatPromptTemplate
from typing import Dict, List, Any
import logging
import pandas as pd
import re
from config.settings import settings
from config.llm_factory import llm_factory
from semantic_layer.enhanced_semantic_layer import enhanced_semantic_layer
from database.connection_manager import db_manager
from agents.advanced_query_planner import advanced_query_planner, QueryIntent
from auth.auth_middleware import auth_middleware

logger = logging.getLogger(__name__)

class EnterpriseSQLAgent:
    def __init__(self):
        self.llm = llm_factory.get_chat_model()
        self.query_planner = advanced_query_planner
        self.schema_cache = {}
        self.few_shot_examples = self._load_few_shot_examples()
    
    def _load_few_shot_examples(self) -> Dict[str, List[Dict]]:
        """Load few-shot examples for better SQL generation"""
        return {
            "aggregation": [
                {
                    "query": "Show me total sales by month",
                    "sql": "SELECT DATE_TRUNC('month', order_date) as month, SUM(total_amount) as total_sales FROM orders GROUP BY DATE_TRUNC('month', order_date) ORDER BY month"
                },
                {
                    "query": "What's the average order value by customer",
                    "sql": "SELECT c.customer_name, AVG(o.total_amount) as avg_order_value FROM customers c JOIN orders o ON c.customer_id = o.customer_id GROUP BY c.customer_id, c.customer_name ORDER BY avg_order_value DESC"
                }
            ],
            "filtering": [
                {
                    "query": "Find customers who haven't ordered in 6 months",
                    "sql": "SELECT c.* FROM customers c LEFT JOIN orders o ON c.customer_id = o.customer_id AND o.order_date >= CURRENT_DATE - INTERVAL '6 months' WHERE o.customer_id IS NULL"
                }
            ],
            "ranking": [
                {
                    "query": "Top 10 customers by revenue",
                    "sql": "SELECT c.customer_name, SUM(o.total_amount) as total_revenue FROM customers c JOIN orders o ON c.customer_id = o.customer_id GROUP BY c.customer_id, c.customer_name ORDER BY total_revenue DESC LIMIT 10"
                }
            ]
        }
    
    def _classify_query_type(self, user_query: str) -> str:
        """Classify query type for better example selection"""
        query_lower = user_query.lower()
        
        if any(word in query_lower for word in ['top', 'best', 'highest', 'lowest', 'rank']):
            return "ranking"
        elif any(word in query_lower for word in ['total', 'sum', 'average', 'count', 'group']):
            return "aggregation"
        elif any(word in query_lower for word in ['find', 'where', 'filter', 'haven\'t', 'without']):
            return "filtering"
        else:
            return "general"
    
    def _get_relevant_examples(self, query_type: str) -> List[Dict]:
        """Get relevant few-shot examples"""
        examples = self.few_shot_examples.get(query_type, [])
        if not examples and query_type != "general":
            examples = self.few_shot_examples.get("aggregation", [])
        return examples[:2]
    
    def _enhanced_sql_generation(self, user_query: str, relevant_schema: Dict) -> str:
        """Enhanced SQL generation with few-shot examples"""
        try:
            # Classify query type
            query_type = self._classify_query_type(user_query)
            
            # Get relevant examples
            examples = self._get_relevant_examples(query_type)
            
            # Build examples text
            examples_text = ""
            if examples:
                examples_text = "\nEXAMPLES:\n"
                for i, example in enumerate(examples, 1):
                    examples_text += f"{i}. Question: {example['query']}\n"
                    examples_text += f"   SQL: {example['sql']}\n\n"
            
            # Build enhanced schema context
            schema_context = self._build_enhanced_schema_context(relevant_schema)
            
            # Create enhanced prompt
            system_message = f"""You are an expert PostgreSQL query generator. Generate accurate SQL queries based on the schema and examples provided.

{schema_context}
{examples_text}

RULES:
1. Use ONLY tables and columns from the schema above
2. Follow PostgreSQL syntax exactly
3. Use proper JOINs when accessing multiple tables
4. Include appropriate WHERE, GROUP BY, ORDER BY clauses
5. Use aggregate functions (SUM, COUNT, AVG) when needed
6. Handle date/time queries with proper functions (DATE_TRUNC, INTERVAL)
7. Return ONLY the SQL query, no explanations
8. Do not use markdown formatting

QUERY ANALYSIS:
- Identify key entities (tables, columns, conditions)
- Determine if aggregation is needed
- Check if filtering or sorting is required
- Consider table relationships for JOINs"""

            human_message = f"Generate PostgreSQL SQL for: {user_query}"
            
            prompt = ChatPromptTemplate.from_messages([
                ("system", system_message),
                ("human", human_message)
            ])
            
            response = self.llm.invoke(prompt.format_messages())
            generated_sql = self._clean_sql(response.content)
            
            logger.info(f"Enhanced SQL generated: {generated_sql}")
            return generated_sql
            
        except Exception as e:
            logger.error(f"Enhanced SQL generation failed: {e}")
            return ""
    
    def _build_enhanced_schema_context(self, relevant_schema: Dict) -> str:
        """Build enhanced schema context with relationships"""
        context = "DATABASE SCHEMA:\n"
        relationships = []
        
        for table_name, table_info in relevant_schema.items():
            context += f"\nTable: {table_name}\n"
            context += "Columns:\n"
            
            for col in table_info.get('columns', [])[:8]:
                col_info = f"  - {col['name']} ({col['type']}"
                if col.get('primary_key'):
                    col_info += ", PRIMARY KEY"
                if col.get('foreign_key'):
                    col_info += f", FOREIGN KEY -> {col['foreign_key']}"
                    relationships.append(f"{table_name}.{col['name']} -> {col['foreign_key']}")
                col_info += ")"
                context += col_info + "\n"
        
        if relationships:
            context += "\nTABLE RELATIONSHIPS:\n"
            for rel in relationships[:5]:
                context += f"  - {rel}\n"
        
        return context
    
    def _clean_sql(self, sql: str) -> str:
        """Clean and validate SQL"""
        if not sql:
            return ""
        
        # Remove markdown formatting
        sql = re.sub(r'```sql\s*', '', sql)
        sql = re.sub(r'```\s*', '', sql)
        
        # Clean whitespace
        sql = ' '.join(sql.split())
        
        # Remove trailing semicolon
        sql = sql.rstrip(';')
        
        # Ensure it starts with SELECT
        if not sql.upper().startswith('SELECT'):
            return ""
        
        return sql
    
    def _validate_sql_enhanced(self, sql: str) -> Dict[str, Any]:
        """Enhanced SQL validation"""
        try:
            if not sql:
                return {"valid": False, "error": "Empty SQL query", "confidence": 0.0}
            
            # Basic syntax checks
            sql_upper = sql.upper()
            
            # Check for required SELECT
            if not sql_upper.startswith('SELECT'):
                return {"valid": False, "error": "Query must start with SELECT", "confidence": 0.0}
            
            # Check for balanced parentheses
            if sql.count('(') != sql.count(')'):
                return {"valid": False, "error": "Unbalanced parentheses", "confidence": 0.0}
            
            # Check for dangerous operations
            dangerous_patterns = ['DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER', 'CREATE']
            for pattern in dangerous_patterns:
                if pattern in sql_upper:
                    return {"valid": False, "error": f"Dangerous operation: {pattern}", "confidence": 0.0}
            
            # Test with database
            sql_clean = sql.rstrip(';')
            sql_upper = sql_clean.upper()
            
            # Only add LIMIT if not already present
            if 'LIMIT' not in sql_upper and 'TOP' not in sql_upper:
                test_sql = sql_clean + " LIMIT 1"
            else:
                test_sql = sql_clean
            try:
                db_manager.execute_query(test_sql)
                return {"valid": True, "error": None, "confidence": 0.9}
            except Exception as db_error:
                return {"valid": False, "error": f"Database error: {str(db_error)}", "confidence": 0.2}
                
        except Exception as e:
            return {"valid": False, "error": f"Validation error: {str(e)}", "confidence": 0.0}
    
    def process_query(self, user_query: str) -> Dict[str, Any]:
        """Process natural language query with enhanced approach"""
        try:
            logger.info(f"🚀 Processing enhanced enterprise query: {user_query}")
            
            # Store current query for authorization checks
            self.current_query = user_query
            
            # Step 1: Get enhanced schema context
            relevant_schema = self._get_comprehensive_schema_context(user_query)
            
            # Step 1.5: Layer 1 - Pre-generation Authorization
            logger.info("🔐 Layer 1: Pre-generation authorization check...")
            pre_auth_result = self._check_pre_generation_authorization(relevant_schema)
            if not pre_auth_result["authorized"]:
                logger.warning(f"❌ Layer 1 blocked: {pre_auth_result['message']}")
                return self._create_error_result(user_query, f"Access denied: {pre_auth_result['message']}")
            logger.info("✅ Layer 1 passed: User authorized for all relevant schema objects")
            
            # Step 2: Generate SQL with enhanced method
            logger.info("⚡ Generating enhanced SQL...")
            generated_sql = self._enhanced_sql_generation(user_query, relevant_schema)
            
            if not generated_sql:
                # Fallback to original method
                logger.info("🔄 Falling back to original generation...")
                intent = self.query_planner.understand_query_intent(user_query, relevant_schema)
                generated_sql = self.query_planner.generate_sql_from_intent(
                    intent, user_query, relevant_schema
                )
            
            if not generated_sql:
                return self._create_error_result(user_query, "Failed to generate SQL query")
            
            # Step 2.5: Authorization check
            logger.info("🔐 Checking authorization...")
            is_authorized, auth_message = auth_middleware.check_query_authorization(generated_sql)
            if not is_authorized:
                logger.warning(f"❌ Query not authorized: {auth_message}")
                return self._create_error_result(user_query, f"Access denied: {auth_message}")
            
            # Step 3: Enhanced validation
            logger.info("✅ Enhanced validation...")
            validation_result = self._validate_sql_enhanced(generated_sql)
            
            if not validation_result["valid"]:
                # Try to refine the SQL
                logger.info("🔧 Attempting SQL refinement...")
                refined_sql = self._refine_sql(user_query, generated_sql, validation_result["error"])
                if refined_sql:
                    # Re-check authorization for refined SQL
                    is_authorized, auth_message = auth_middleware.check_query_authorization(refined_sql)
                    if not is_authorized:
                        logger.warning(f"❌ Refined query not authorized: {auth_message}")
                        return self._create_error_result(user_query, f"Access denied: {auth_message}")
                    
                    generated_sql = refined_sql
                    validation_result = self._validate_sql_enhanced(generated_sql)
            
            # Step 4: Execute query
            logger.info("🔄 Executing SQL query...")
            execution_result = self._execute_sql_safely(generated_sql)
            
            # Step 5: Return comprehensive result
            result = {
                "user_query": user_query,
                "generated_sql": generated_sql,
                "execution_result": execution_result["data"],
                "error_message": execution_result["error"],
                "confidence_score": validation_result.get("confidence", 0.5),
                "validation_result": validation_result,
                "relevant_schema": self._format_schema_summary(relevant_schema),
                "execution_stats": {
                    "rows_returned": len(execution_result["data"]) if execution_result["data"] is not None else 0,
                    "execution_time": execution_result.get("execution_time", 0)
                }
            }
            
            logger.info(f"✅ Query processed successfully. Confidence: {validation_result.get('confidence', 0.5):.2f}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Enhanced query processing failed: {str(e)}")
            return self._create_error_result(user_query, f"Processing failed: {str(e)}")
    
    def _refine_sql(self, user_query: str, sql: str, error: str) -> str:
        """Refine SQL based on validation error"""
        try:
            refinement_prompt = f"""The following SQL query has an error:
SQL: {sql}
Error: {error}

Original question: {user_query}

Please fix the SQL query to resolve the error. Return only the corrected SQL query without any explanations or formatting."""
            
            response = self.llm.invoke(refinement_prompt)
            refined_sql = self._clean_sql(response.content)
            
            logger.info(f"SQL refined: {refined_sql}")
            return refined_sql
            
        except Exception as e:
            logger.error(f"SQL refinement failed: {e}")
            return ""
    
    def _check_pre_generation_authorization(self, relevant_schema: Dict[str, Any]) -> Dict[str, Any]:
        """Layer 1: Check if user is authorized for tables required by the specific query"""
        try:
            from auth.jwt_manager import jwt_manager
            from auth.authorization_manager import authorization_manager
            
            current_user = jwt_manager.get_current_user()
            if not current_user:
                return {"authorized": False, "message": "User not authenticated"}
            
            user_permissions = current_user.get("permissions", {})
            
            # Determine which tables are actually required for this query
            required_tables = self._predict_required_tables(self.current_query, relevant_schema)
            
            if not required_tables:
                return {"authorized": False, "message": "No tables identified for this query"}
            
            # Check authorization only for required tables
            unauthorized_objects = []
            for table_name in required_tables:
                if not authorization_manager.check_table_access(table_name, user_permissions):
                    unauthorized_objects.append(f"table '{table_name}'")
                    continue
                
                # Check key columns for this table
                table_info = relevant_schema.get(table_name, {})
                columns = table_info.get('columns', [])
                for column in columns[:5]:  # Check first 5 columns (most likely to be used)
                    column_name = column.get('name') if isinstance(column, dict) else str(column)
                    if not authorization_manager.check_column_access(table_name, column_name, user_permissions):
                        unauthorized_objects.append(f"column '{table_name}.{column_name}'")
            
            if unauthorized_objects:
                missing_perms = ", ".join(unauthorized_objects[:3])
                return {
                    "authorized": False, 
                    "message": f"Missing permissions for: {missing_perms}"
                }
            
            logger.info(f"Layer 1: User authorized for required tables: {required_tables}")
            return {"authorized": True, "message": f"Access granted to required tables: {required_tables}"}
            
        except Exception as e:
            logger.error(f"Pre-generation authorization check failed: {e}")
            return {"authorized": False, "message": "Authorization check failed"}
    
    def _predict_required_tables(self, user_query: str, relevant_schema: Dict[str, Any]) -> List[str]:
        """Predict which tables are actually required for the user query"""
        try:
            schema_summary = "\n".join([f"- {table}: {', '.join([col.get('name', str(col)) for col in info.get('columns', [])[:3]])}" 
                                      for table, info in relevant_schema.items()])
            
            prompt = f"""Given this user query and available tables, identify ONLY the tables that are absolutely required to answer the query.

USER QUERY: {user_query}

AVAILABLE TABLES:
{schema_summary}

Return only the table names that are required, separated by commas. Be minimal - only include tables that are essential for this specific query.

REQUIRED TABLES:"""
            
            response = self.llm.invoke(prompt)
            required_tables_str = response.content.strip()
            
            # Parse table names
            required_tables = [table.strip() for table in required_tables_str.split(',') if table.strip()]
            
            # Validate that predicted tables exist in relevant schema
            valid_tables = [table for table in required_tables if table in relevant_schema]
            
            logger.info(f"Predicted required tables for '{user_query}': {valid_tables}")
            return valid_tables
            
        except Exception as e:
            logger.error(f"Failed to predict required tables: {e}")
            # Fallback: return all relevant tables
            return list(relevant_schema.keys())

    def _get_comprehensive_schema_context(self, user_query: str) -> Dict[str, Any]:
        """Get comprehensive schema context with relationships"""
        try:
            # Get enhanced semantic search results
            semantic_results = enhanced_semantic_layer.search_enhanced_schema(
                user_query, connection_name="default", top_k=20
            )
            
            # Extract relevant tables
            relevant_tables = set()
            for item in semantic_results:
                metadata = item.get('metadata', {})
                table_name = metadata.get('table')
                if table_name:
                    relevant_tables.add(table_name)
            
            # Get full schema for relevant tables
            if not hasattr(self, '_full_schema') or not self._full_schema:
                self._full_schema = db_manager.get_table_schema()
            
            comprehensive_schema = {}
            
            # Add primary tables
            for table_name in relevant_tables:
                if table_name in self._full_schema:
                    comprehensive_schema[table_name] = self._full_schema[table_name]
            
            # Add related tables through foreign keys
            for table_name in list(relevant_tables):
                if table_name in self._full_schema:
                    table_info = self._full_schema[table_name]
                    
                    # Add tables referenced by foreign keys
                    for fk in table_info.get('foreign_keys', []):
                        ref_table = fk.get('referred_table')
                        if ref_table and ref_table in self._full_schema:
                            comprehensive_schema[ref_table] = self._full_schema[ref_table]
                    
                    # Add tables that reference this table
                    for other_table, other_info in self._full_schema.items():
                        for fk in other_info.get('foreign_keys', []):
                            if fk.get('referred_table') == table_name:
                                comprehensive_schema[other_table] = self._full_schema[other_table]
            
            logger.info(f"📊 Comprehensive schema context: {len(comprehensive_schema)} tables")
            return comprehensive_schema
            
        except Exception as e:
            logger.error(f"Failed to get comprehensive schema: {str(e)}")
            return {}
    
    def _execute_sql_safely(self, sql: str) -> Dict[str, Any]:
        """Execute SQL with safety measures and Layer 3 authorization"""
        try:
            import time
            start_time = time.time()
            
            # Add safety limit if not present
            sql_upper = sql.upper()
            sql = sql.rstrip(';')  # Remove trailing semicolon
            if "LIMIT" not in sql_upper and "TOP" not in sql_upper:
                sql += f" LIMIT {min(settings.max_query_results, 5000)}"
            
            # Layer 3: Execute with user-specific database connection
            logger.info("🔐 Layer 3: Database-level authorization...")
            result_df = self._execute_with_user_connection(sql)
            execution_time = time.time() - start_time
            
            logger.info(f"✅ Layer 3 passed: SQL executed successfully: {len(result_df)} rows in {execution_time:.2f}s")
            
            return {
                "data": result_df,
                "error": "",
                "execution_time": execution_time
            }
            
        except Exception as e:
            logger.error(f"❌ Layer 3 blocked: {str(e)}")
            return {
                "data": None,
                "error": f"Database access denied: {str(e)}",
                "execution_time": 0
            }
    
    def _execute_with_user_connection(self, sql: str) -> pd.DataFrame:
        """Execute SQL using user-specific database connection"""
        try:
            from auth.jwt_manager import jwt_manager
            from auth.user_manager import user_manager
            
            # Get current user
            current_user = jwt_manager.get_current_user()
            if not current_user:
                raise Exception("User not authenticated")
            
            username = current_user.get("username")
            
            # Get user's actual password from users.json (for DB connection)
            users_data = user_manager._load_users()
            if username not in users_data:
                raise Exception(f"User {username} not found")
            
            # Get stored plain password for DB connection
            db_password = users_data[username].get("db_password")
            if not db_password:
                # Fallback to admin connection if no DB password stored
                logger.warning(f"No DB password for user {username}, using admin connection")
                return db_manager.execute_query(sql)
            
            # Execute with user-specific connection
            logger.info(f"Executing query with user credentials: {username}")
            
            try:
                # Get user connection from connection manager
                user_conn = db_manager.get_user_connection(username, db_password)
                
                # Execute query with user connection
                import pandas as pd
                result_df = pd.read_sql(sql, user_conn)
                user_conn.close()
                
                return result_df
                
            except Exception as db_error:
                # This is the actual Layer 3 block - database denied access
                raise Exception(f"Database access denied for user '{username}': {str(db_error)}")
            
        except Exception as e:
            logger.error(f"User connection execution failed: {e}")
            raise Exception(f"Layer 3 authorization failed: {str(e)}")
    
    def _format_schema_summary(self, schema_context: Dict[str, Any]) -> List[Dict]:
        """Format schema summary for result"""
        summary = []
        for table_name, table_info in schema_context.items():
            columns = table_info.get('columns', [])
            summary.append({
                'table': table_name,
                'columns': len(columns),
                'key_columns': [col['name'] for col in columns[:5]]
            })
        return summary
    
    def _create_error_result(self, user_query: str, error_message: str) -> Dict[str, Any]:
        """Create standardized error result"""
        return {
            "user_query": user_query,
            "query_intent": {"type": "UNKNOWN", "entities": [], "attributes": [], "conditions": []},
            "generated_sql": "",
            "execution_result": None,
            "error_message": error_message,
            "confidence_score": 0.0,
            "relevant_schema": [],
            "execution_stats": {"rows_returned": 0, "execution_time": 0}
        }
    
    def get_query_suggestions(self, schema_context: Dict[str, Any]) -> List[str]:
        """Generate intelligent query suggestions based on schema"""
        suggestions = []
        
        # Analyze schema to generate suggestions
        for table_name, table_info in list(schema_context.items())[:5]:
            columns = table_info.get('columns', [])
            
            # Look for common patterns
            has_date = any('date' in col['name'].lower() or 'time' in col['name'].lower() for col in columns)
            has_amount = any('amount' in col['name'].lower() or 'price' in col['name'].lower() or 'revenue' in col['name'].lower() for col in columns)
            has_name = any('name' in col['name'].lower() for col in columns)
            
            if has_date and has_amount:
                suggestions.append(f"Show {table_name} trends over time")
                suggestions.append(f"What's the total amount in {table_name} by month?")
            
            if has_name and has_amount:
                suggestions.append(f"Top 10 {table_name} by amount")
                suggestions.append(f"Show all {table_name} with their totals")
            
            if has_name:
                suggestions.append(f"List all {table_name}")
                suggestions.append(f"Count of {table_name} by category")
        
        return suggestions[:8]  # Return top 8 suggestions

# Global instance
enterprise_sql_agent = EnterpriseSQLAgent()
