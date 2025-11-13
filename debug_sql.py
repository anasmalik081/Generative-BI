#!/usr/bin/env python3
"""
Debug script for SQL generation issues
Run this to test the SQL agent independently
"""

import os
import sys
import logging
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment
load_dotenv()

# Import modules
from config.settings import settings
from database.connection_manager import db_manager
from semantic_layer.vector_store import semantic_layer
from agents.sql_agent_fixed import improved_sql_agent

def test_database_connection():
    """Test database connection"""
    print("🔗 Testing database connection...")
    try:
        success = db_manager.connect("postgresql")
        if success:
            print("✅ Database connection successful")
            
            # Test a simple query
            result = db_manager.execute_query("SELECT 1 as test")
            print(f"✅ Test query successful: {result}")
            return True
        else:
            print("❌ Database connection failed")
            return False
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        return False

def test_schema_loading():
    """Test schema loading"""
    print("\n📊 Testing schema loading...")
    try:
        schema_info = db_manager.get_table_schema()
        print(f"✅ Found {len(schema_info)} tables")
        
        # Print first few tables
        for i, (table_name, table_info) in enumerate(list(schema_info.items())[:3]):
            print(f"  Table {i+1}: {table_name} ({len(table_info['columns'])} columns)")
            for j, col in enumerate(table_info['columns'][:3]):
                print(f"    - {col['name']} ({col['type']})")
        
        # Load into semantic layer
        semantic_layer.create_schema_embeddings(schema_info)
        print("✅ Schema loaded into semantic layer")
        return True
        
    except Exception as e:
        print(f"❌ Schema loading error: {e}")
        return False

def test_sql_generation(query: str):
    """Test SQL generation for a specific query"""
    print(f"\n🤖 Testing SQL generation for: '{query}'")
    try:
        # Test semantic search first
        relevant_schema = semantic_layer.search_relevant_schema(query, top_k=10)
        print(f"✅ Found {len(relevant_schema)} relevant schema items")
        
        for item in relevant_schema[:3]:
            metadata = item.get('metadata', {})
            print(f"  - {metadata.get('type', 'unknown')}: {metadata.get('table', '')}.{metadata.get('column', '')}")
        
        # Test SQL generation
        result = improved_sql_agent.process_query(query)
        
        print(f"\n📝 Generated SQL: {result.get('generated_sql', 'None')}")
        print(f"🎯 Confidence: {result.get('confidence_score', 0):.2f}")
        
        if result.get('error_message'):
            print(f"❌ Error: {result['error_message']}")
        
        if result.get('execution_result') is not None:
            df = result['execution_result']
            print(f"✅ Query executed successfully! Got {len(df)} rows")
            if not df.empty:
                print("📊 Sample data:")
                print(df.head())
        
        return result
        
    except Exception as e:
        print(f"❌ SQL generation error: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    """Main debug function"""
    print("🚀 GenBI SQL Debug Tool")
    print("=" * 50)
    
    # Check environment
    if not settings.groq_api_key:
        print("❌ GROQ_API_KEY not found in environment")
        return
    
    print(f"✅ Groq API key found: {settings.groq_api_key[:10]}...")
    
    # Test database connection
    if not test_database_connection():
        return
    
    # Test schema loading
    if not test_schema_loading():
        return
    
    # Test queries
    test_queries = [
        "SELECT * FROM customers LIMIT 5",  # Direct SQL test
        "Show me all customers",  # Simple natural language
        "What are the top 5 customers by total orders?",  # More complex
        "List all products with their prices"  # Another simple one
    ]
    
    for query in test_queries:
        result = test_sql_generation(query)
        print("\n" + "="*50)
    
    print("\n🏁 Debug complete!")

if __name__ == "__main__":
    main()
