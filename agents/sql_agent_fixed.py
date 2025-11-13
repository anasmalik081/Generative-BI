from langchain_groq import ChatGroq
from langchain.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain.schema import BaseOutputParser
from langgraph.graph import StateGraph, END
from typing import Dict, List, Any, TypedDict
import json
import re
from config.settings import settings
from semantic_layer.enhanced_semantic_layer import enhanced_semantic_layer
from database.connection_manager import db_manager
import logging

logger = logging.getLogger(__name__)

class SQLGenerationState(TypedDict):
    user_query: str
    relevant_schema: List[Dict]
    generated_sql: str
    validated_sql: str
    execution_result: Any
    error_message: str
    confidence_score: float
    refinement_attempts: int  # Track refinement attempts

class ImprovedSQLOutputParser(BaseOutputParser):
    def parse(self, text: str) -> str:
        """Parse SQL from LLM response with better error handling"""
        logger.info(f"Parsing LLM response: {text[:200]}...")
        
        # Clean the input text
        text = text.strip()
        
        # Method 1: Extract from code blocks
        patterns = [
            r'```sql\s*(.*?)\s*```',
            r'```\s*(SELECT.*?)\s*```',
            r'```(.*?)```'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            if match:
                sql_content = match.group(1).strip()
                if sql_content and 'SELECT' in sql_content.upper():
                    logger.info(f"Extracted SQL from code block: {sql_content}")
                    return self._clean_sql(sql_content)
        
        # Method 2: Look for SELECT statements
        select_patterns = [
            r'(SELECT\s+.*?)(?:\n\n|\Z)',
            r'(SELECT\s+.*?)(?:;|\Z)',
            r'(SELECT.*?)(?:\n\n|\Z)'
        ]
        
        for pattern in select_patterns:
            match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            if match:
                sql_content = match.group(1).strip()
                logger.info(f"Extracted SQL with pattern: {sql_content}")
                return self._clean_sql(sql_content)
        
        # Method 3: If text starts with SELECT, use it directly
        if text.upper().startswith('SELECT'):
            logger.info(f"Using direct SQL: {text}")
            return self._clean_sql(text)
        
        # Method 4: Look for any SQL-like content
        if any(keyword in text.upper() for keyword in ['SELECT', 'FROM', 'WHERE']):
            # Try to extract the SQL part
            lines = text.split('\n')
            sql_lines = []
            in_sql = False
            
            for line in lines:
                line = line.strip()
                if line.upper().startswith('SELECT'):
                    in_sql = True
                    sql_lines.append(line)
                elif in_sql and line:
                    if any(keyword in line.upper() for keyword in ['FROM', 'WHERE', 'GROUP', 'ORDER', 'HAVING', 'LIMIT']):
                        sql_lines.append(line)
                    elif line.endswith(';'):
                        sql_lines.append(line)
                        break
                    elif not line.replace(',', '').replace('(', '').replace(')', '').strip():
                        continue
                    else:
                        sql_lines.append(line)
            
            if sql_lines:
                sql_content = ' '.join(sql_lines)
                logger.info(f"Reconstructed SQL: {sql_content}")
                return self._clean_sql(sql_content)
        
        # If all else fails, log and return empty
        logger.error(f"Could not parse SQL from response: {text}")
        return ""
    
    def _clean_sql(self, sql: str) -> str:
        """Clean and format SQL query"""
        # Remove extra whitespace
        sql = ' '.join(sql.split())
        
        # Remove trailing semicolon if present
        if sql.endswith(';'):
            sql = sql[:-1]
        
        # Ensure it starts with SELECT
        if not sql.upper().startswith('SELECT'):
            return ""
        
        return sql

class ImprovedSQLAgent:
    def __init__(self):
        self.llm = ChatGroq(
            groq_api_key=settings.groq_api_key,
            model_name=settings.chat_model,
            temperature=0.1,
            max_tokens=1000
        )
        self.sql_parser = ImprovedSQLOutputParser()
        self.graph = self._create_workflow()
        self.max_refinement_attempts = 2  # Limit refinement attempts
    
    def _create_workflow(self) -> StateGraph:
        """Create LangGraph workflow for SQL generation"""
        workflow = StateGraph(SQLGenerationState)
        
        # Add nodes
        workflow.add_node("analyze_query", self._analyze_query)
        workflow.add_node("generate_sql", self._generate_sql)
        workflow.add_node("validate_sql", self._validate_sql)
        workflow.add_node("execute_sql", self._execute_sql)
        workflow.add_node("refine_sql", self._refine_sql)
        
        # Add edges
        workflow.set_entry_point("analyze_query")
        workflow.add_edge("analyze_query", "generate_sql")
        workflow.add_edge("generate_sql", "validate_sql")
        
        # Conditional edge based on validation
        workflow.add_conditional_edges(
            "validate_sql",
            self._should_execute_or_refine,
            {
                "execute": "execute_sql",
                "refine": "refine_sql",
                "end": END
            }
        )
        
        workflow.add_edge("execute_sql", END)
        workflow.add_edge("refine_sql", "validate_sql")
        
        # Compile with recursion limit
        return workflow.compile(
            checkpointer=None,
            debug=False
        )
    
    def _analyze_query(self, state: SQLGenerationState) -> SQLGenerationState:
        """Analyze user query and find relevant schema elements"""
        try:
            user_query = state["user_query"]
            logger.info(f"Analyzing query: {user_query}")
            
            # Search for relevant schema elements
            relevant_schema = enhanced_semantic_layer.search_enhanced_schema(
                user_query, 
                connection_name="default", 
                top_k=15
            )
            
            state["relevant_schema"] = relevant_schema
            logger.info(f"Found {len(relevant_schema)} relevant schema elements")
            
            # Log the relevant schema for debugging
            for item in relevant_schema[:5]:
                logger.info(f"Relevant: {item.get('metadata', {})}")
            
        except Exception as e:
            logger.error(f"Query analysis failed: {str(e)}")
            state["error_message"] = f"Query analysis failed: {str(e)}"
        
        return state
    
    def _generate_sql(self, state: SQLGenerationState) -> SQLGenerationState:
        """Generate SQL query based on natural language input"""
        try:
            user_query = state["user_query"]
            relevant_schema = state["relevant_schema"]
            
            # Create schema context
            schema_context = self._format_schema_context(relevant_schema)
            logger.info(f"Schema context: {schema_context}")
            
            # If no relevant schema found, try to get basic table info
            if not schema_context.strip():
                logger.warning("No relevant schema found, trying to get basic table info")
                try:
                    all_schema = db_manager.get_table_schema()
                    if all_schema:
                        # Use first few tables as fallback
                        fallback_context = ""
                        for table_name, table_info in list(all_schema.items())[:3]:
                            fallback_context += f"\nTable: {table_name}\n"
                            for col in table_info['columns'][:10]:  # First 10 columns
                                fallback_context += f"  - {col['name']} ({col['type']})\n"
                        schema_context = fallback_context
                        logger.info(f"Using fallback schema: {schema_context}")
                except Exception as e:
                    logger.error(f"Failed to get fallback schema: {e}")
            
            # Create a more explicit prompt
            system_message = f"""You are a PostgreSQL expert. Convert the user's natural language question into a complete, valid PostgreSQL SQL query.

AVAILABLE TABLES AND COLUMNS:
{schema_context}

RULES:
1. Write a complete SQL query starting with SELECT
2. Only use tables and columns from the schema above
3. Use proper PostgreSQL syntax
4. Include appropriate WHERE, GROUP BY, ORDER BY clauses as needed
5. Return ONLY the SQL query, no explanations
6. Do not use markdown formatting or code blocks
7. Make reasonable assumptions if the query is ambiguous

EXAMPLE FORMAT:
SELECT column1, column2 FROM table1 WHERE condition ORDER BY column1 LIMIT 100"""

            human_message = f"""Question: {user_query}

Write the complete PostgreSQL SQL query:"""

            # Use a simpler approach without the parser in the chain
            prompt = ChatPromptTemplate.from_messages([
                ("system", system_message),
                ("human", human_message)
            ])
            
            # Get response from LLM
            response = self.llm.invoke(prompt.format_messages(user_query=user_query))
            logger.info(f"LLM Response: {response.content}")
            
            # Parse the SQL
            generated_sql = self.sql_parser.parse(response.content)
            logger.info(f"Parsed SQL: {generated_sql}")
            
            if not generated_sql:
                # Try a direct approach
                generated_sql = self._generate_simple_fallback_query(user_query, schema_context)
                logger.info(f"Using fallback SQL: {generated_sql}")
            
            state["generated_sql"] = generated_sql
            
        except Exception as e:
            logger.error(f"SQL generation failed: {str(e)}")
            state["error_message"] = f"SQL generation failed: {str(e)}"
            # Try a simple fallback
            try:
                fallback_sql = self._generate_simple_fallback_query(state["user_query"], "")
                state["generated_sql"] = fallback_sql
                logger.info(f"Using emergency fallback: {fallback_sql}")
            except:
                pass
        
        return state
    
    def _generate_simple_fallback_query(self, user_query: str, schema_context: str) -> str:
        """Generate a simple fallback query when main generation fails"""
        try:
            # Get available tables
            all_schema = db_manager.get_table_schema()
            if not all_schema:
                return "SELECT 1 as test_query"
            
            # Use the first table as fallback
            first_table = list(all_schema.keys())[0]
            first_table_info = all_schema[first_table]
            
            # Get first few columns
            columns = [col['name'] for col in first_table_info['columns'][:5]]
            
            # Create a simple SELECT query
            fallback_sql = f"SELECT {', '.join(columns)} FROM {first_table} LIMIT 10"
            logger.info(f"Generated fallback query: {fallback_sql}")
            return fallback_sql
            
        except Exception as e:
            logger.error(f"Fallback generation failed: {e}")
            return "SELECT 1 as test_query"
    
    def _validate_sql(self, state: SQLGenerationState) -> SQLGenerationState:
        """Validate the generated SQL query"""
        try:
            generated_sql = state["generated_sql"]
            logger.info(f"Validating SQL: {generated_sql}")
            
            if not generated_sql:
                state["error_message"] = "No SQL query generated"
                return state
            
            # Basic SQL syntax validation
            sql_lower = generated_sql.lower().strip()
            
            # Check for basic SQL structure
            if not sql_lower.startswith('select'):
                state["error_message"] = "Query must start with SELECT"
                return state
            
            # Check for potential SQL injection patterns
            dangerous_patterns = ['drop', 'delete', 'truncate', 'alter', 'create', 'insert', 'update']
            for pattern in dangerous_patterns:
                if pattern in sql_lower:
                    state["error_message"] = f"Potentially dangerous SQL operation detected: {pattern}"
                    return state
            
            # Try to validate with database (dry run)
            try:
                # Add LIMIT to prevent large result sets during validation
                validation_sql = generated_sql
                if 'limit' not in sql_lower and 'top' not in sql_lower:
                    validation_sql += " LIMIT 1"
                
                logger.info(f"Testing query: {validation_sql}")
                # Test query execution
                test_result = db_manager.execute_query(validation_sql)
                logger.info(f"Validation successful, got {len(test_result)} rows")
                
                state["validated_sql"] = generated_sql
                state["confidence_score"] = 0.9
                
            except Exception as db_error:
                logger.error(f"SQL validation failed: {str(db_error)}")
                state["error_message"] = f"SQL validation failed: {str(db_error)}"
                state["confidence_score"] = 0.3
            
        except Exception as e:
            logger.error(f"SQL validation failed: {str(e)}")
            state["error_message"] = f"SQL validation failed: {str(e)}"
        
        return state
    
    def _execute_sql(self, state: SQLGenerationState) -> SQLGenerationState:
        """Execute the validated SQL query"""
        try:
            validated_sql = state["validated_sql"]
            logger.info(f"Executing SQL: {validated_sql}")
            
            # Add safety limit if not present
            sql_lower = validated_sql.lower()
            if 'limit' not in sql_lower and 'top' not in sql_lower:
                validated_sql += f" LIMIT {settings.max_query_results}"
            
            result = db_manager.execute_query(validated_sql)
            state["execution_result"] = result
            logger.info(f"SQL executed successfully, returned {len(result)} rows")
            
        except Exception as e:
            logger.error(f"SQL execution failed: {str(e)}")
            state["error_message"] = f"SQL execution failed: {str(e)}"
        
        return state
    
    def _refine_sql(self, state: SQLGenerationState) -> SQLGenerationState:
        """Refine SQL query based on validation errors"""
        try:
            # Increment refinement attempts
            current_attempts = state.get("refinement_attempts", 0)
            state["refinement_attempts"] = current_attempts + 1
            
            logger.info(f"Refining SQL query (attempt {state['refinement_attempts']})")
            
            user_query = state["user_query"]
            generated_sql = state["generated_sql"]
            error_message = state["error_message"]
            relevant_schema = state["relevant_schema"]
            
            schema_context = self._format_schema_context(relevant_schema)
            
            refine_prompt = f"""The previous SQL query had an error. Please fix it.

Original Query Request: {user_query}
Previous SQL: {generated_sql}
Error: {error_message}

Schema Information:
{schema_context}

Please generate a corrected PostgreSQL SQL query that addresses the error while fulfilling the original request.
Return only the corrected SQL query without any formatting or explanations."""

            response = self.llm.invoke([("human", refine_prompt)])
            refined_sql = self.sql_parser.parse(response.content)
            
            if refined_sql and refined_sql != generated_sql:
                state["generated_sql"] = refined_sql
                state["error_message"] = ""  # Clear previous error
                logger.info(f"SQL query refined: {refined_sql}")
            else:
                logger.error("Failed to refine SQL query or got same result")
                state["error_message"] = "Unable to refine query further"
            
        except Exception as e:
            logger.error(f"SQL refinement failed: {str(e)}")
            state["error_message"] = f"SQL refinement failed: {str(e)}"
        
        return state
    
    def _should_execute_or_refine(self, state: SQLGenerationState) -> str:
        """Decide whether to execute, refine, or end based on validation results"""
        refinement_attempts = state.get("refinement_attempts", 0)
        
        # If we've reached max refinement attempts, stop trying
        if refinement_attempts >= self.max_refinement_attempts:
            logger.warning(f"Max refinement attempts ({self.max_refinement_attempts}) reached, ending workflow")
            return "end"
        
        if state.get("error_message"):
            # If there's an error and we haven't exceeded attempts, try to refine
            if state.get("confidence_score", 0) < 0.5:
                logger.info(f"Attempting refinement (attempt {refinement_attempts + 1}/{self.max_refinement_attempts})")
                return "refine"
            else:
                return "end"
        elif state.get("validated_sql"):
            return "execute"
        else:
            return "end"
    
    def _format_schema_context(self, relevant_schema: List[Dict]) -> str:
        """Format schema information for the prompt"""
        if not relevant_schema:
            return ""
        
        context = ""
        tables_seen = set()
        
        # Group by table
        table_info = {}
        for item in relevant_schema:
            metadata = item.get("metadata", {})
            if metadata.get("type") == "table":
                table_name = metadata.get("table")
                if table_name and table_name not in tables_seen:
                    table_info[table_name] = []
                    tables_seen.add(table_name)
            elif metadata.get("type") == "column":
                table_name = metadata.get("table")
                column_name = metadata.get("column")
                data_type = metadata.get("data_type", "")
                if table_name and column_name:
                    if table_name not in table_info:
                        table_info[table_name] = []
                    table_info[table_name].append(f"{column_name} ({data_type})")
        
        # Format the context
        for table_name, columns in table_info.items():
            context += f"\nTable: {table_name}\n"
            for column in columns[:10]:  # Limit columns to prevent prompt overflow
                context += f"  - {column}\n"
        
        return context
    
    def process_query(self, user_query: str) -> Dict[str, Any]:
        """Process natural language query and return results"""
        try:
            logger.info(f"Processing query: {user_query}")
            
            initial_state = SQLGenerationState(
                user_query=user_query,
                relevant_schema=[],
                generated_sql="",
                validated_sql="",
                execution_result=None,
                error_message="",
                confidence_score=0.0,
                refinement_attempts=0  # Initialize refinement attempts
            )
            
            # Configure recursion limit for the graph execution
            config = {
                "recursion_limit": 10,  # Set a reasonable limit
                "max_execution_time": 60  # 60 seconds timeout
            }
            
            try:
                final_state = self.graph.invoke(initial_state, config=config)
            except Exception as graph_error:
                if "recursion limit" in str(graph_error).lower():
                    logger.error("Recursion limit reached, falling back to simple SQL generation")
                    # Fallback: try simple SQL generation without refinement
                    return self._fallback_simple_generation(user_query)
                else:
                    raise graph_error
            
            result = {
                "user_query": final_state["user_query"],
                "generated_sql": final_state.get("validated_sql") or final_state.get("generated_sql"),
                "execution_result": final_state.get("execution_result"),
                "error_message": final_state.get("error_message"),
                "confidence_score": final_state.get("confidence_score", 0.0),
                "relevant_schema": final_state.get("relevant_schema", []),
                "refinement_attempts": final_state.get("refinement_attempts", 0)
            }
            
            logger.info(f"Query processing completed. SQL: {result['generated_sql']}")
            return result
            
        except Exception as e:
            logger.error(f"Query processing failed: {str(e)}")
            return {
                "user_query": user_query,
                "generated_sql": "",
                "execution_result": None,
                "error_message": f"Query processing failed: {str(e)}",
                "confidence_score": 0.0,
                "relevant_schema": [],
                "refinement_attempts": 0
            }
    
    def _fallback_simple_generation(self, user_query: str) -> Dict[str, Any]:
        """Fallback method for simple SQL generation without workflow"""
        try:
            logger.info("Using fallback simple SQL generation")
            
            # Get relevant schema
            relevant_schema = enhanced_semantic_layer.search_enhanced_schema(
                user_query, connection_name="default", top_k=10
            )
            
            # Generate SQL directly
            schema_context = self._format_schema_context(relevant_schema)
            
            system_message = f"""You are a PostgreSQL expert. Convert the user's natural language question into a complete, valid PostgreSQL SQL query.

AVAILABLE TABLES AND COLUMNS:
{schema_context}

RULES:
1. Write a complete SQL query starting with SELECT
2. Only use tables and columns from the schema above
3. Use proper PostgreSQL syntax
4. Return ONLY the SQL query, no explanations
5. Do not use markdown formatting"""

            response = self.llm.invoke([
                ("system", system_message),
                ("human", f"Question: {user_query}\n\nWrite the complete PostgreSQL SQL query:")
            ])
            
            generated_sql = self.sql_parser.parse(response.content)
            
            if generated_sql:
                # Try to execute it
                try:
                    result_df = db_manager.execute_query(generated_sql + " LIMIT 1000")
                    return {
                        "user_query": user_query,
                        "generated_sql": generated_sql,
                        "execution_result": result_df,
                        "error_message": "",
                        "confidence_score": 0.7,
                        "relevant_schema": relevant_schema,
                        "refinement_attempts": 0
                    }
                except Exception as exec_error:
                    return {
                        "user_query": user_query,
                        "generated_sql": generated_sql,
                        "execution_result": None,
                        "error_message": f"SQL execution failed: {str(exec_error)}",
                        "confidence_score": 0.3,
                        "relevant_schema": relevant_schema,
                        "refinement_attempts": 0
                    }
            else:
                return {
                    "user_query": user_query,
                    "generated_sql": "",
                    "execution_result": None,
                    "error_message": "Failed to generate SQL query",
                    "confidence_score": 0.0,
                    "relevant_schema": relevant_schema,
                    "refinement_attempts": 0
                }
                
        except Exception as e:
            logger.error(f"Fallback generation failed: {str(e)}")
            return {
                "user_query": user_query,
                "generated_sql": "",
                "execution_result": None,
                "error_message": f"Fallback generation failed: {str(e)}",
                "confidence_score": 0.0,
                "relevant_schema": [],
                "refinement_attempts": 0
            }

# Global instance
improved_sql_agent = ImprovedSQLAgent()
