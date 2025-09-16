from langchain_groq import ChatGroq
from langchain.prompts import ChatPromptTemplate
from typing import Dict, List, Any, Optional
import json
import logging
from config.settings import settings
from semantic_layer.enhanced_semantic_layer import enhanced_semantic_layer
from database.connection_manager import db_manager

logger = logging.getLogger(__name__)

class QueryIntent:
    """Represents the understood intent of a natural language query"""
    def __init__(self):
        self.query_type = ""  # SELECT, AGGREGATE, JOIN, FILTER, etc.
        self.entities = []    # Tables/entities involved
        self.attributes = []  # Columns needed
        self.conditions = []  # WHERE conditions
        self.aggregations = [] # GROUP BY, aggregation functions
        self.sorting = []     # ORDER BY
        self.limits = []      # LIMIT, TOP N
        self.time_filters = [] # Date/time conditions
        self.relationships = [] # JOIN conditions

class AdvancedQueryPlanner:
    def __init__(self):
        self.llm = ChatGroq(
            groq_api_key=settings.groq_api_key,
            model_name=settings.chat_model,
            temperature=0.0  # More deterministic
        )
        self.schema_graph = {}
        self.query_patterns = self._load_query_patterns()
    
    def _load_query_patterns(self) -> Dict[str, Dict]:
        """Load common query patterns for few-shot learning"""
        return {
            "top_n": {
                "pattern": "top N {entity} by {metric}",
                "template": "SELECT {columns} FROM {table} ORDER BY {metric} DESC LIMIT {n}",
                "examples": [
                    {
                        "nl": "top 10 customers by revenue",
                        "sql": "SELECT customer_name, SUM(order_total) as revenue FROM customers c JOIN orders o ON c.customer_id = o.customer_id GROUP BY c.customer_id, customer_name ORDER BY revenue DESC LIMIT 10"
                    }
                ]
            },
            "aggregation": {
                "pattern": "total/sum/count of {metric} by {dimension}",
                "template": "SELECT {dimension}, {aggregation}({metric}) FROM {table} GROUP BY {dimension}",
                "examples": [
                    {
                        "nl": "total sales by month",
                        "sql": "SELECT DATE_TRUNC('month', order_date) as month, SUM(total_amount) as total_sales FROM orders GROUP BY DATE_TRUNC('month', order_date) ORDER BY month"
                    }
                ]
            },
            "filter": {
                "pattern": "{entity} where {condition}",
                "template": "SELECT {columns} FROM {table} WHERE {condition}",
                "examples": [
                    {
                        "nl": "customers from New York",
                        "sql": "SELECT * FROM customers WHERE city = 'New York'"
                    }
                ]
            },
            "comparison": {
                "pattern": "compare {metric} across {dimensions}",
                "template": "SELECT {dimensions}, {metric} FROM {table} GROUP BY {dimensions}",
                "examples": [
                    {
                        "nl": "compare sales across regions",
                        "sql": "SELECT region, SUM(total_amount) as total_sales FROM orders GROUP BY region ORDER BY total_sales DESC"
                    }
                ]
            },
            "trend": {
                "pattern": "{metric} trend over time",
                "template": "SELECT {time_dimension}, {metric} FROM {table} GROUP BY {time_dimension} ORDER BY {time_dimension}",
                "examples": [
                    {
                        "nl": "revenue trend over last 12 months",
                        "sql": "SELECT DATE_TRUNC('month', order_date) as month, SUM(total_amount) as revenue FROM orders WHERE order_date >= CURRENT_DATE - INTERVAL '12 months' GROUP BY DATE_TRUNC('month', order_date) ORDER BY month"
                    }
                ]
            }
        }
    
    def understand_query_intent(self, user_query: str, schema_context: Dict) -> QueryIntent:
        """Understand the intent behind the natural language query"""
        try:
            # Create a comprehensive prompt for intent understanding
            intent_prompt = ChatPromptTemplate.from_template("""
            You are an expert data analyst. Analyze this natural language query and extract the intent.
            
            Query: "{user_query}"
            
            Available Schema:
            {schema_context}
            
            Analyze the query and identify:
            1. Query Type (SELECT, AGGREGATE, JOIN, FILTER, TREND, COMPARISON, TOP_N)
            2. Main Entities (tables involved)
            3. Attributes (columns needed)
            4. Conditions (WHERE clauses)
            5. Aggregations (SUM, COUNT, AVG, etc.)
            6. Sorting requirements (ORDER BY)
            7. Limits (TOP N, LIMIT)
            8. Time filters (date ranges, periods)
            9. Relationships (JOINs needed)
            
            Respond in JSON format:
            {{
                "query_type": "type of query",
                "entities": ["table1", "table2"],
                "attributes": ["column1", "column2"],
                "conditions": ["condition1", "condition2"],
                "aggregations": ["SUM(column)", "COUNT(*)"],
                "sorting": ["column DESC", "column ASC"],
                "limits": ["LIMIT 10"],
                "time_filters": ["date_column >= '2024-01-01'"],
                "relationships": ["table1.id = table2.foreign_id"],
                "confidence": 0.9
            }}
            """)
            
            response = self.llm.invoke(intent_prompt.format_messages(
                user_query=user_query,
                schema_context=self._format_schema_for_intent(schema_context)
            ))
            
            # Parse the intent
            intent_data = json.loads(response.content)
            
            intent = QueryIntent()
            intent.query_type = intent_data.get("query_type", "SELECT")
            intent.entities = intent_data.get("entities", [])
            intent.attributes = intent_data.get("attributes", [])
            intent.conditions = intent_data.get("conditions", [])
            intent.aggregations = intent_data.get("aggregations", [])
            intent.sorting = intent_data.get("sorting", [])
            intent.limits = intent_data.get("limits", [])
            intent.time_filters = intent_data.get("time_filters", [])
            intent.relationships = intent_data.get("relationships", [])
            
            logger.info(f"Query intent understood: {intent.query_type} involving {intent.entities}")
            return intent
            
        except Exception as e:
            logger.error(f"Intent understanding failed: {str(e)}")
            # Return basic intent
            intent = QueryIntent()
            intent.query_type = "SELECT"
            return intent
    
    def generate_sql_from_intent(self, intent: QueryIntent, user_query: str, schema_context: Dict) -> str:
        """Generate SQL based on understood intent with few-shot examples"""
        try:
            # Find matching pattern
            matching_pattern = self._find_matching_pattern(intent, user_query)
            
            # Get relevant examples
            examples = self._get_relevant_examples(intent, matching_pattern)
            
            # Create advanced SQL generation prompt
            sql_prompt = ChatPromptTemplate.from_template("""
            You are a PostgreSQL expert specializing in complex business queries. Generate accurate SQL based on the query intent and examples.
            
            Original Query: "{user_query}"
            
            Query Intent Analysis:
            - Type: {query_type}
            - Tables: {entities}
            - Columns: {attributes}
            - Conditions: {conditions}
            - Aggregations: {aggregations}
            - Sorting: {sorting}
            - Limits: {limits}
            - Time Filters: {time_filters}
            - Relationships: {relationships}
            
            Available Schema:
            {schema_context}
            
            Similar Query Examples:
            {examples}
            
            SQL Generation Rules:
            1. Use ONLY tables and columns from the provided schema
            2. Follow PostgreSQL syntax exactly
            3. Use proper JOINs based on foreign key relationships
            4. Apply appropriate WHERE conditions
            5. Use correct aggregation functions and GROUP BY
            6. Add proper ORDER BY for meaningful results
            7. Include LIMIT for large result sets
            8. Handle NULL values appropriately
            9. Use table aliases for readability
            10. Optimize for performance
            
            Generate the complete, executable PostgreSQL SQL query:
            """)
            
            response = self.llm.invoke(sql_prompt.format_messages(
                user_query=user_query,
                query_type=intent.query_type,
                entities=", ".join(intent.entities),
                attributes=", ".join(intent.attributes),
                conditions=", ".join(intent.conditions),
                aggregations=", ".join(intent.aggregations),
                sorting=", ".join(intent.sorting),
                limits=", ".join(intent.limits),
                time_filters=", ".join(intent.time_filters),
                relationships=", ".join(intent.relationships),
                schema_context=self._format_detailed_schema(schema_context),
                examples=self._format_examples(examples)
            ))
            
            # Extract and clean SQL
            sql = self._extract_sql(response.content)
            logger.info(f"Generated SQL from intent: {sql}")
            return sql
            
        except Exception as e:
            logger.error(f"SQL generation from intent failed: {str(e)}")
            return ""
    
    def _find_matching_pattern(self, intent: QueryIntent, user_query: str) -> Optional[str]:
        """Find the best matching query pattern"""
        query_lower = user_query.lower()
        
        # Check for specific patterns
        if any(word in query_lower for word in ["top", "best", "highest", "lowest"]):
            return "top_n"
        elif any(word in query_lower for word in ["total", "sum", "count", "average", "by"]):
            return "aggregation"
        elif any(word in query_lower for word in ["compare", "comparison", "across", "between"]):
            return "comparison"
        elif any(word in query_lower for word in ["trend", "over time", "monthly", "yearly"]):
            return "trend"
        elif any(word in query_lower for word in ["where", "from", "in", "with"]):
            return "filter"
        else:
            return "aggregation"  # Default to aggregation as it's most common
    
    def _get_relevant_examples(self, intent: QueryIntent, pattern: Optional[str]) -> List[Dict]:
        """Get relevant examples based on intent and pattern"""
        examples = []
        
        if pattern and pattern in self.query_patterns:
            examples.extend(self.query_patterns[pattern]["examples"])
        
        # Add more examples based on entities
        for entity in intent.entities:
            if "customer" in entity.lower():
                examples.append({
                    "nl": "show all customers with their total orders",
                    "sql": "SELECT c.customer_name, COUNT(o.order_id) as total_orders FROM customers c LEFT JOIN orders o ON c.customer_id = o.customer_id GROUP BY c.customer_id, c.customer_name"
                })
            elif "order" in entity.lower():
                examples.append({
                    "nl": "show recent orders with customer details",
                    "sql": "SELECT o.order_id, o.order_date, c.customer_name, o.total_amount FROM orders o JOIN customers c ON o.customer_id = c.customer_id ORDER BY o.order_date DESC LIMIT 20"
                })
        
        return examples[:3]  # Limit to 3 most relevant examples
    
    def _format_schema_for_intent(self, schema_context: Dict) -> str:
        """Format schema for intent understanding"""
        formatted = ""
        for table_name, table_info in schema_context.items():
            formatted += f"\nTable: {table_name}\n"
            columns = table_info.get('columns', [])
            for col in columns[:10]:  # First 10 columns
                col_name = col.get('name', 'unknown')
                col_type = col.get('type', 'unknown')
                formatted += f"  - {col_name} ({col_type})\n"
        return formatted
    
    def _format_detailed_schema(self, schema_context: Dict) -> str:
        """Format detailed schema with relationships"""
        formatted = ""
        for table_name, table_info in schema_context.items():
            formatted += f"\n=== Table: {table_name} ===\n"
            
            # Columns
            columns = table_info.get('columns', [])
            formatted += "Columns:\n"
            for col in columns:
                col_name = col.get('name', 'unknown')
                col_type = col.get('type', 'unknown')
                nullable = "NULL" if col.get('nullable', True) else "NOT NULL"
                pk = " (PRIMARY KEY)" if col.get('primary_key', False) else ""
                formatted += f"  - {col_name}: {col_type} {nullable}{pk}\n"
            
            # Foreign keys
            fks = table_info.get('foreign_keys', [])
            if fks:
                formatted += "Foreign Keys:\n"
                for fk in fks:
                    source_col = fk.get('constrained_columns', [''])[0]
                    target_table = fk.get('referred_table', '')
                    target_col = fk.get('referred_columns', [''])[0]
                    formatted += f"  - {source_col} → {target_table}.{target_col}\n"
        
        return formatted
    
    def _format_examples(self, examples: List[Dict]) -> str:
        """Format examples for the prompt"""
        formatted = ""
        for i, example in enumerate(examples, 1):
            formatted += f"\nExample {i}:\n"
            formatted += f"Question: {example['nl']}\n"
            formatted += f"SQL: {example['sql']}\n"
        return formatted
    
    def _extract_sql(self, response: str) -> str:
        """Extract SQL from LLM response"""
        import re
        
        # Try to find SQL in code blocks
        sql_pattern = r'```(?:sql)?\s*(.*?)\s*```'
        match = re.search(sql_pattern, response, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
        
        # Try to find SELECT statement
        select_pattern = r'(SELECT\s+.*?)(?:\n\n|\Z)'
        match = re.search(select_pattern, response, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
        
        # If response starts with SELECT, use it directly
        if response.strip().upper().startswith('SELECT'):
            return response.strip()
        
        return ""
    
    def validate_and_optimize_sql(self, sql: str, intent: QueryIntent) -> tuple[str, float]:
        """Validate and optimize the generated SQL"""
        try:
            if not sql or not sql.strip():
                return "", 0.0
            
            # Basic validation
            sql_upper = sql.upper()
            confidence = 0.5
            
            # Check for required elements based on intent
            if intent.query_type == "AGGREGATE" and "GROUP BY" in sql_upper:
                confidence += 0.2
            if intent.query_type == "TOP_N" and ("LIMIT" in sql_upper or "TOP" in sql_upper):
                confidence += 0.2
            if intent.entities and any(entity.lower() in sql.lower() for entity in intent.entities):
                confidence += 0.2
            if intent.attributes and any(attr.lower() in sql.lower() for attr in intent.attributes):
                confidence += 0.1
            
            # Try to execute with LIMIT 1 for validation
            try:
                validation_sql = sql
                if "LIMIT" not in sql_upper:
                    validation_sql += " LIMIT 1"
                
                db_manager.execute_query(validation_sql)
                confidence = min(confidence + 0.3, 1.0)
                
            except Exception as e:
                logger.warning(f"SQL validation failed: {str(e)}")
                confidence = max(confidence - 0.3, 0.1)
            
            return sql, confidence
            
        except Exception as e:
            logger.error(f"SQL validation failed: {str(e)}")
            return sql, 0.1

# Global instance
advanced_query_planner = AdvancedQueryPlanner()
