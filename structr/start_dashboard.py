#!/usr/bin/env python3
"""
Structr Dashboard Launcher

Start the Streamlit dashboard for visual PDP management.
Production-ready with environment detection and proper configuration.
"""

import subprocess
import sys
import os
from pathlib import Path
import webbrowser
import time

# Import centralized configuration
from config import StructrConfig as CONFIG


def setup_environment():
    """Set up environment and create necessary directories"""
    project_root = Path(__file__).parent
    
    # Create required directories
    dirs_to_create = [
        CONFIG.OUTPUT_DIR / 'bundles',
        CONFIG.OUTPUT_DIR / 'exports',
        CONFIG.OUTPUT_DIR / 'jobs',
        CONFIG.OUTPUT_DIR / 'monitoring',
        CONFIG.INPUT_DIR,
        CONFIG.UPLOADS_DIR,
        Path('cache')
    ]
    
    for dir_path in dirs_to_create:
        if not dir_path.is_absolute():
            dir_path = project_root / dir_path
        dir_path.mkdir(parents=True, exist_ok=True)
    
    # Set environment variables for production
    env = os.getenv('STRUCTR_ENV', 'development')
    if env == 'production':
        os.environ['STREAMLIT_SERVER_HEADLESS'] = 'true'
        os.environ['STREAMLIT_BROWSER_GATHER_USAGE_STATS'] = 'false'
        os.environ['STREAMLIT_SERVER_ENABLE_CORS'] = 'false'
        os.environ['STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION'] = 'true'
    
    return env, project_root

def get_streamlit_args(env, project_root):
    """Build Streamlit command arguments based on environment"""
    dashboard_file = project_root / "dashboard_app.py"
    
    # Base arguments
    args = [
        sys.executable, "-m", "streamlit", "run", 
        str(dashboard_file),
        "--server.port", str(CONFIG.get_dashboard_port()),
        "--server.address", CONFIG.SERVER_ADDRESS,
        "--server.headless", str(CONFIG.DASHBOARD_HEADLESS).lower(),
        "--browser.gatherUsageStats", "false"
    ]
    
    # Production-specific arguments
    if env == 'production':
        # Use PORT environment variable if available (for hosting platforms)
        port = os.getenv('PORT', str(CONFIG.get_dashboard_port()))
        args[args.index(str(CONFIG.get_dashboard_port()))] = port
        
        args.extend([
            "--server.enableCORS", "false",
            "--server.enableXsrfProtection", "true",
            "--server.maxUploadSize", "200"
        ])
    
    return args

def main():
    """Launch the Structr dashboard"""
    
    # Setup environment
    env, project_root = setup_environment()
    
    print(f"🧱 Starting Structr Dashboard ({env} mode)...")
    print("=" * 50)
    
    # Check if streamlit is installed
    try:
        import streamlit
        print("✅ Streamlit found")
    except ImportError:
        if env != 'production':  # Don't auto-install in production
            print("❌ Streamlit not found. Installing...")
            subprocess.run([sys.executable, "-m", "pip", "install", "streamlit", "plotly", "pandas"])
            print("✅ Dependencies installed")
        else:
            print("❌ Streamlit not found in production environment!")
            sys.exit(1)
    
    # Check if bundles exist
    bundles_dir = CONFIG.get_bundles_dir()
    if bundles_dir.exists() and any(bundles_dir.iterdir()):
        bundle_count = len([d for d in bundles_dir.iterdir() if d.is_dir()])
        print(f"✅ Found {bundle_count} existing bundles")
    else:
        print("⚠️  No bundles found - generate some PDPs first for full functionality")
    
    # Get Streamlit arguments
    args = get_streamlit_args(env, project_root)
    
    # Show startup info
    dashboard_file = project_root / "dashboard_app.py"
    port = os.getenv('PORT', str(CONFIG.get_dashboard_port()))
    
    print(f"🚀 Launching dashboard: {dashboard_file}")
    if env == 'development':
        print(f"📊 Dashboard will open at: http://{CONFIG.SERVER_ADDRESS}:{port}")
    else:
        print(f"📊 Dashboard running on port: {port}")
    print("🔄 Use Ctrl+C to stop the dashboard")
    print("=" * 50)
    
    if env == 'development':
        print(f"Command: {' '.join(args)}")
        print("=" * 50)
    
    try:
        # Start streamlit
        subprocess.run(args, cwd=project_root, check=True)
        
    except KeyboardInterrupt:
        print("\n👋 Dashboard stopped")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error starting dashboard: {e}")
        if env == 'development':
            print("\nTry running manually:")
            print(f"cd {project_root}")
            print("streamlit run dashboard_app.py")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()