#!/usr/bin/env python3
"""
Install Structr dependencies

Install all required dependencies for Structr core and dashboard.
"""

import subprocess
import sys


def install_dependencies():
    """Install all required dependencies"""
    
    print("📦 Installing Structr Dependencies")
    print("=" * 40)
    
    dependencies = [
        # Core dependencies
        "requests>=2.31.0",
        "beautifulsoup4>=4.12.0", 
        "click>=8.1.0",
        "pydantic>=2.5.0",
        "jinja2>=3.1.0",
        
        # Dashboard dependencies
        "streamlit>=1.46.0",
        "plotly>=6.0.0",
        "pandas>=2.0.0",
        
        # Testing
        "pytest>=7.4.0"
    ]
    
    print("Installing core dependencies...")
    
    for dep in dependencies:
        print(f"  Installing {dep}...")
        try:
            subprocess.run([
                sys.executable, "-m", "pip", "install", dep
            ], check=True, capture_output=True)
            print(f"  ✅ {dep}")
        except subprocess.CalledProcessError:
            print(f"  ❌ Failed to install {dep}")
    
    print("\n✅ Installation complete!")
    print("\n🚀 Next steps:")
    print("1. python demo_dashboard.py    # Generate sample data")
    print("2. python start_dashboard.py  # Launch dashboard")


if __name__ == "__main__":
    install_dependencies()