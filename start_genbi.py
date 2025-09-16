#!/usr/bin/env python3
"""
Simple GenBI launcher
"""

import subprocess
import sys

def main():
    """Launch GenBI with the new interface"""
    print("🚀 Starting GenBI - Natural Language Business Intelligence")
    print("=" * 60)
    
    try:
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", "app_new.py",
            "--server.port", "8501",
            "--server.address", "localhost",
            "--theme.base", "light",
            "--browser.gatherUsageStats", "false"
        ])
    except KeyboardInterrupt:
        print("\n👋 GenBI stopped")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
