#!/usr/bin/env python3
"""
Simple test for Groq API connectivity
"""

import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq

load_dotenv()

def test_groq_api():
    """Test basic Groq API functionality"""
    api_key = os.getenv("GROQ_API_KEY")
    
    if not api_key:
        print("❌ GROQ_API_KEY not found in environment")
        return False
    
    print(f"✅ API Key found: {api_key[:10]}...")
    
    try:
        # Initialize the model
        llm = ChatGroq(
            groq_api_key=api_key,
            model_name="openai/gpt-oss-20b",
            temperature=0.1
        )
        
        # Test a simple query
        response = llm.invoke("Write a simple SQL query to select all records from a table called 'users'. Return only the SQL query.")
        
        print(f"✅ Groq API working! Response: {response.content}")
        return True
        
    except Exception as e:
        print(f"❌ Groq API error: {e}")
        return False

if __name__ == "__main__":
    test_groq_api()
