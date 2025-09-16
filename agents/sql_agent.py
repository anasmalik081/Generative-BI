from langchain_groq import ChatGroq
from langchain.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain.schema import BaseOutputParser
from langgraph.graph import StateGraph, END
from typing import Dict, List, Any, TypedDict
import json
import re
from config.settings import settings
from semantic_layer.vector_store import semantic_layer
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

class SQLOutputParser(BaseOutputParser):
    def parse(self, text: str) -> str:
        # Clean the input text
        text = text.strip()
        
        # Extract SQL from markdown code blocks first
        sql_pattern = r'```(?:sql)?\s*(.*?)\s*```'
        match = re.search(sql_pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            sql_content = match.group(1).strip()
            if sql_content and sql_content.upper().startswith('SELECT'):
                return sql_content
        
        # Try to find SQL without markdown - more comprehensive pattern
        sql_pattern = r'(SELECT\s+.*?)(?:\n\n|$)'
        match = re.search(sql_pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            sql_content = match.group(1).strip()
            # Remove trailing semicolon if present
            if sql_content.endswith(';'):
                sql_content = sql_content[:-1]
            return sql_content
        
        # If the entire text looks like SQL, return it
        if text.upper().startswith('SELECT'):
            # Remove trailing semicolon if present
            if text.endswith(';'):
                text = text[:-1]
            return text
        
        # Last resort - return the text as is but log a warning
        logger.warning(f"Could not parse SQL from: {text[:100]}...")
        return text

class SQLAgent:
    def __init__(self):
        self.llm = ChatGroq(
            groq_api_key=settings.groq_api_key,
            model_name=settings.chat_model,
            temperature=0.1
        )
        self.sql_parser = SQLOutputParser()
        self.graph = self._create_workflow()
    
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
        
        return workflow.compile()
    
    def _analyze_query(self, state: SQLGenerationState) -> SQLGenerationState:
        """Analyze user query and find relevant schema elements"""
        try:
            user_query = state["user_query"]
            
            # Search for relevant schema elements
            relevant_schema = semantic_layer.search_relevant_schema(
                user_query, 
                connection_name="default", 
                top_k=15
            )
            
            state["relevant_schema"] = relevant_schema
            logger.info(f"Found {len(relevant_schema)} relevant schema elements")
            
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
            logger.info(f"CONTEXT SCHEMA: {schema_context}")
            
            system_prompt = """You are an expert SQL query generator. Your task is to convert natural language queries into accurate, optimized SQL queries.

Guidelines:
1. Generate syntactically correct SQL queries
2. Use appropriate JOINs when multiple tables are involved
3. Apply proper WHERE clauses for filtering
4. Use aggregate functions (COUNT, SUM, AVG, etc.) when needed
5. Include ORDER BY and LIMIT clauses when appropriate
6. Optimize for performance on large datasets
7. Use table aliases for readability
8. Handle date/time queries properly
9. Consider NULL values in conditions

Schema Information:
{schema_context}

Important Notes:
- Only use tables and columns that exist in the schema
- Be careful with data types and formatting
- Use proper SQL syntax for the database type
- If the query is ambiguous, make reasonable assumptions
- Return only the SQL query without explanations"""

            human_prompt = """Convert this natural language query to SQL:
{user_query}

Return only the SQL query."""

            prompt = ChatPromptTemplate.from_messages([
                SystemMessagePromptTemplate.from_template(system_prompt),
                HumanMessagePromptTemplate.from_template(human_prompt)
            ])
            
            chain = prompt | self.llm | self.sql_parser
            
            generated_sql = chain.invoke({
                "schema_context": schema_context,
                "user_query": user_query
            })
            logger.info(f"GENERATED SQL: {generated_sql}")
            
            state["generated_sql"] = generated_sql
            logger.info("SQL query generated successfully")
            
        except Exception as e:
            logger.error(f"SQL generation failed: {str(e)}")
            state["error_message"] = f"SQL generation failed: {str(e)}"
        
        return state
    
    def _validate_sql(self, state: SQLGenerationState) -> SQLGenerationState:
        """Validate the generated SQL query"""
        try:
            generated_sql = state["generated_sql"]
            
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
                
                # Test query execution
                db_manager.execute_query(validation_sql)
                state["validated_sql"] = generated_sql
                state["confidence_score"] = 0.9
                
            except Exception as db_error:
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
            user_query = state["user_query"]
            generated_sql = state["generated_sql"]
            error_message = state["error_message"]
            relevant_schema = state["relevant_schema"]
            
            schema_context = self._format_schema_context(relevant_schema)
            
            refine_prompt = """The previous SQL query had an error. Please fix it.

Original Query Request: {user_query}
Previous SQL: {generated_sql}
Error: {error_message}

Schema Information:
{schema_context}

Please generate a corrected SQL query that addresses the error while fulfilling the original request.
Return only the corrected SQL query."""

            prompt = ChatPromptTemplate.from_template(refine_prompt)
            chain = prompt | self.llm | self.sql_parser
            
            refined_sql = chain.invoke({
                "user_query": user_query,
                "generated_sql": generated_sql,
                "error_message": error_message,
                "schema_context": schema_context
            })
            
            state["generated_sql"] = refined_sql
            state["error_message"] = ""  # Clear previous error
            logger.info("SQL query refined")
            
        except Exception as e:
            logger.error(f"SQL refinement failed: {str(e)}")
            state["error_message"] = f"SQL refinement failed: {str(e)}"
        
        return state
    
    def _should_execute_or_refine(self, state: SQLGenerationState) -> str:
        """Decide whether to execute, refine, or end based on validation results"""
        if state.get("error_message"):
            # If there's an error and we haven't tried refining yet, try to refine
            if state.get("confidence_score", 0) < 0.5:
                return "refine"
            else:
                return "end"  # Give up after refinement attempt
        elif state.get("validated_sql"):
            return "execute"
        else:
            return "end"
    
    def _format_schema_context(self, relevant_schema: List[Dict]) -> str:
        """Format schema information for the prompt"""
        context = ""
        tables_seen = set()
        
        for item in relevant_schema:
            metadata = item["metadata"]
            if metadata["type"] == "table" and metadata["table"] not in tables_seen:
                context += f"\nTable: {metadata['table']}\n"
                tables_seen.add(metadata["table"])
            elif metadata["type"] == "column":
                context += f"  - {metadata['column']} ({metadata['data_type']})\n"
        
        return context
    
    def process_query(self, user_query: str) -> Dict[str, Any]:
        """Process natural language query and return results"""
        try:
            initial_state = SQLGenerationState(
                user_query=user_query,
                relevant_schema=[],
                generated_sql="",
                validated_sql="",
                execution_result=None,
                error_message="",
                confidence_score=0.0
            )
            
            final_state = self.graph.invoke(initial_state)
            
            return {
                "user_query": final_state["user_query"],
                "generated_sql": final_state.get("validated_sql") or final_state.get("generated_sql"),
                "execution_result": final_state.get("execution_result"),
                "error_message": final_state.get("error_message"),
                "confidence_score": final_state.get("confidence_score", 0.0),
                "relevant_schema": final_state.get("relevant_schema", [])
            }
            
        except Exception as e:
            logger.error(f"Query processing failed: {str(e)}")
            return {
                "user_query": user_query,
                "generated_sql": "",
                "execution_result": None,
                "error_message": f"Query processing failed: {str(e)}",
                "confidence_score": 0.0,
                "relevant_schema": []
            }

# Global instance
sql_agent = SQLAgent()
