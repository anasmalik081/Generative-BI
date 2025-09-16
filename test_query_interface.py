#!/usr/bin/env python3
"""
Simple test for query interface functionality
"""

import streamlit as st
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_query_interface():
    """Test the query interface components"""
    st.title("🧪 Query Interface Test")
    
    # Test basic button functionality
    st.header("Button Test")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("Test Button 1", type="primary", use_container_width=True):
            st.success("Button 1 clicked!")
    
    with col2:
        if st.button("Test Button 2", use_container_width=True):
            st.success("Button 2 clicked!")
    
    with col3:
        if st.button("Test Button 3", type="secondary", use_container_width=True):
            st.success("Button 3 clicked!")
    
    # Test text area
    st.header("Text Input Test")
    user_input = st.text_area(
        "Enter your test query:",
        placeholder="e.g., Show me all customers",
        height=100
    )
    
    if user_input:
        st.info(f"You entered: {user_input}")
    
    # Test expandable sections
    st.header("Expandable Section Test")
    with st.expander("Test Options"):
        option1 = st.checkbox("Option 1", value=True)
        option2 = st.slider("Option 2", 1, 100, 50)
        option3 = st.selectbox("Option 3", ["A", "B", "C"])
        
        st.write(f"Selected: {option1}, {option2}, {option3}")

if __name__ == "__main__":
    test_query_interface()
