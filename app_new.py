import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from typing import Dict, Any, List
import logging
import time
from datetime import datetime

# Import our modules
from config.settings import settings
from ui_components.setup_wizard import setup_wizard
from ui_components.query_interface import query_interface

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="GenBI - Natural Language Business Intelligence",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"  # Hide sidebar for cleaner look
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        margin-bottom: 2rem;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    .step-header {
        font-size: 2rem;
        font-weight: bold;
        color: #2E86AB;
        margin-bottom: 1rem;
    }
    
    .metric-card {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #667eea;
        margin: 0.5rem 0;
    }
    
    .success-card {
        background-color: #d4edda;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #28a745;
        margin: 1rem 0;
    }
    
    .info-card {
        background-color: #e8f4fd;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #2196f3;
        margin: 1rem 0;
    }
    
    .warning-card {
        background-color: #fff3cd;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #ffc107;
        margin: 1rem 0;
    }
    
    .sql-container {
        background-color: #1e1e1e;
        color: #ffffff;
        padding: 1rem;
        border-radius: 0.5rem;
        font-family: 'Courier New', monospace;
    }
    
    /* Hide Streamlit default elements for cleaner look */
    .stDeployButton {display:none;}
    footer {visibility: hidden;}
    .stApp > header {visibility: hidden;}
    
    /* Custom button styling */
    .stButton > button {
        width: 100%;
        border-radius: 0.5rem;
        border: none;
        padding: 0.75rem 1rem;
        font-weight: 600;
        transition: all 0.3s;
        font-size: 1rem;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }
    
    /* Make primary buttons more prominent */
    .stButton > button[kind="primary"] {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        font-size: 1.1rem;
        padding: 1rem 1.5rem;
    }
</style>
""", unsafe_allow_html=True)

def initialize_session_state():
    """Initialize session state variables"""
    # Core application state
    if 'app_initialized' not in st.session_state:
        st.session_state.app_initialized = True
        st.session_state.connected = False
        st.session_state.schema_loaded = False
        st.session_state.semantic_layer_built = False
        st.session_state.query_history = []
        st.session_state.current_result = None
        
        # Wizard state
        st.session_state.wizard_step = 0
        st.session_state.wizard_completed = False
        st.session_state.show_query_interface = False
        
        # Connection state
        st.session_state.connection_details = {}
        st.session_state.schema_info = {}
        st.session_state.semantic_method = None
        
        # UI state
        st.session_state.selected_db_type = "PostgreSQL"
        st.session_state.sample_queries = []

def main():
    """Main application entry point"""
    initialize_session_state()
    
    # App header
    st.markdown('<h1 class="main-header">GenBI - Natural Language Business Intelligence</h1>', 
                unsafe_allow_html=True)
    
    # Determine which interface to show
    if st.session_state.wizard_completed and st.session_state.show_query_interface:
        # Show main query interface
        query_interface.render_query_interface()
    else:
        # Show setup wizard
        setup_wizard.render_wizard()
    
    # Footer
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown(
            "<div style='text-align: center; color: #666; font-size: 0.9rem;'>"
            "🚀 <strong>GenBI</strong> - Powered by LangChain, LangGraph, Groq & Streamlit<br>"
            "Making data accessible through natural language"
            "</div>", 
            unsafe_allow_html=True
        )

if __name__ == "__main__":
    main()
