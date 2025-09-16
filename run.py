#!/usr/bin/env python3
"""
GenBI Application Launcher
Provides easy startup with environment validation
"""

import os
import sys
import subprocess
import logging
from pathlib import Path

def check_requirements():
    """Check if all required packages are installed"""
    try:
        import streamlit
        import langchain
        import langgraph
        import langchain_groq
        import plotly
        import chromadb
        import sqlalchemy
        import pandas
        print("✅ All required packages are installed")
        return True
    except ImportError as e:
        print(f"❌ Missing package: {e}")
        print("Please run: pip install -r requirements.txt")
        return False

def check_environment():
    """Check environment configuration"""
    env_file = Path(".env")
    if not env_file.exists():
        print("⚠️  .env file not found. Please copy .env.example to .env and configure it.")
        return False
    
    # Check for Groq API key
    from dotenv import load_dotenv
    load_dotenv()
    
    if not os.getenv("GROQ_API_KEY"):
        print("⚠️  GROQ_API_KEY not found in .env file")
        print("Please add your Groq API key to the .env file")
        return False
    
    print("✅ Environment configuration looks good")
    return True

def create_directories():
    """Create necessary directories"""
    directories = [
        "chroma_db",
        "logs"
    ]
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
    
    print("✅ Directories created")

def setup_logging():
    """Setup logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/genbi.log'),
            logging.StreamHandler()
        ]
    )

def main():
    """Main launcher function"""
    print("🚀 Starting GenBI Application...")
    print("=" * 50)
    
    # Check requirements
    if not check_requirements():
        sys.exit(1)
    
    # Check environment
    if not check_environment():
        sys.exit(1)
    
    # Create directories
    create_directories()
    
    # Setup logging
    setup_logging()
    
    print("✅ All checks passed!")
    print("🌐 Starting Streamlit application...")
    print("=" * 50)
    
    # Launch Streamlit
    try:
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", "app_new.py",
            "--server.port", "8501",
            "--server.address", "0.0.0.0",
            "--theme.base", "light"
        ])
    except KeyboardInterrupt:
        print("\n👋 GenBI Application stopped")
    except Exception as e:
        print(f"❌ Error starting application: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
