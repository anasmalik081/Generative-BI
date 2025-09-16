from langchain_groq import ChatGroq
from typing import Dict, List, Any
import logging
import pandas as pd
from config.settings import settings
from semantic_layer.enhanced_semantic_layer import enhanced_semantic_layer
from database.connection_manager import db_manager
from agents.advanced_query_planner import advanced_query_planner, QueryIntent

logger = logging.getLogger(__name__)

class EnterpriseSQLAgent:
    def __init__(self):
        self.llm = ChatGroq(
            groq_api_key=settings.groq_api_key,
            model_name=settings.chat_model,
            temperature=0.0
        )
        self.query_planner = advanced_query_planner
        self.schema_cache = {}
    
    def process_query(self, user_query: str) -> Dict[str, Any]:
        """Process natural language query with enterprise-grade approach"""
        try:
            logger.info(f"🚀 Processing enterprise query: {user_query}")
            
            # Step 1: Get enhanced schema context
            relevant_schema = self._get_comprehensive_schema_context(user_query)
            
            # Step 2: Understand query intent
            logger.info("🧠 Understanding query intent...")
            intent = self.query_planner.understand_query_intent(user_query, relevant_schema)
            
            # Step 3: Generate SQL based on intent
            logger.info(f"⚡ Generating SQL for {intent.query_type} query...")
            generated_sql = self.query_planner.generate_sql_from_intent(
                intent, user_query, relevant_schema
            )
            
            if not generated_sql:
                return self._create_error_result(user_query, "Failed to generate SQL query")
            
            # Step 4: Validate and optimize
            logger.info("✅ Validating and optimizing SQL...")
            validated_sql, confidence = self.query_planner.validate_and_optimize_sql(
                generated_sql, intent
            )
            
            # Step 5: Execute query
            logger.info("🔄 Executing SQL query...")
            execution_result = self._execute_sql_safely(validated_sql)
            
            # Step 6: Return comprehensive result
            result = {
                "user_query": user_query,
                "query_intent": {
                    "type": intent.query_type,
                    "entities": intent.entities,
                    "attributes": intent.attributes,
                    "conditions": intent.conditions
                },
                "generated_sql": validated_sql,
                "execution_result": execution_result["data"],
                "error_message": execution_result["error"],
                "confidence_score": confidence,
                "relevant_schema": self._format_schema_summary(relevant_schema),
                "execution_stats": {
                    "rows_returned": len(execution_result["data"]) if execution_result["data"] is not None else 0,
                    "execution_time": execution_result.get("execution_time", 0)
                }
            }
            
            logger.info(f"✅ Query processed successfully. Confidence: {confidence:.2f}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Enterprise query processing failed: {str(e)}")
            return self._create_error_result(user_query, f"Processing failed: {str(e)}")
    
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
        """Execute SQL with safety measures and performance tracking"""
        try:
            import time
            start_time = time.time()
            
            # Add safety limit if not present
            sql_upper = sql.upper()
            if "LIMIT" not in sql_upper and "TOP" not in sql_upper:
                sql += f" LIMIT {min(settings.max_query_results, 5000)}"
            
            # Execute query
            result_df = db_manager.execute_query(sql)
            execution_time = time.time() - start_time
            
            logger.info(f"✅ SQL executed successfully: {len(result_df)} rows in {execution_time:.2f}s")
            
            return {
                "data": result_df,
                "error": "",
                "execution_time": execution_time
            }
            
        except Exception as e:
            logger.error(f"❌ SQL execution failed: {str(e)}")
            return {
                "data": None,
                "error": str(e),
                "execution_time": 0
            }
    
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
