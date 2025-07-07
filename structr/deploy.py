#!/usr/bin/env python3
"""
Structr Dashboard Deployment Script

Automated deployment to various hosting platforms.
"""

import subprocess
import sys
import os
import json
from pathlib import Path
import argparse

def run_command(cmd, description="Running command"):
    """Run a shell command with proper error handling"""
    print(f"🔧 {description}...")
    print(f"$ {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error: {e}")
        if e.stderr:
            print(f"Error output: {e.stderr}")
        return False

def deploy_railway():
    """Deploy to Railway"""
    print("🚂 Deploying to Railway...")
    
    # Check if Railway CLI is installed
    if not run_command(["railway", "--version"], "Checking Railway CLI"):
        print("❌ Railway CLI not found. Install with: npm install -g @railway/cli")
        return False
    
    # Check if logged in
    if not run_command(["railway", "whoami"], "Checking Railway authentication"):
        print("❌ Please log in to Railway first: railway login")
        return False
    
    # Initialize project if needed
    if not Path("railway.toml").exists():
        if not run_command(["railway", "init"], "Initializing Railway project"):
            return False
    
    # Set environment variables
    env_vars = {
        "PYTHONPATH": "/app",
        "STREAMLIT_SERVER_PORT": "8501",
        "STREAMLIT_SERVER_ADDRESS": "0.0.0.0",
        "STREAMLIT_SERVER_HEADLESS": "true",
        "STREAMLIT_BROWSER_GATHER_USAGE_STATS": "false",
        "STRUCTR_ENV": "production",
        "STRUCTR_OUTPUT_DIR": "/app/output",
        "STRUCTR_INPUT_DIR": "/app/input",
        "STRUCTR_LLM_MODEL": "mistral"
    }
    
    print("⚙️ Setting environment variables...")
    for key, value in env_vars.items():
        if not run_command(["railway", "variables", "set", f"{key}={value}"], f"Setting {key}"):
            return False
    
    # Deploy
    if not run_command(["railway", "up"], "Deploying to Railway"):
        return False
    
    print("✅ Railway deployment complete!")
    print("🔍 Check status: railway status")
    print("📋 View logs: railway logs")
    return True

def deploy_render():
    """Deploy to Render (requires GitHub integration)"""
    print("🎨 Deploying to Render...")
    
    # Check if render.yaml exists
    if not Path("render.yaml").exists():
        print("❌ render.yaml not found. Please set up Render via GitHub integration.")
        print("1. Push your code to GitHub")
        print("2. Connect your repository to Render")
        print("3. The render.yaml file will be used automatically")
        return False
    
    print("✅ render.yaml found. Deploy via Render dashboard or GitHub integration.")
    return True

def deploy_streamlit_cloud():
    """Deploy to Streamlit Cloud"""
    print("☁️ Deploying to Streamlit Cloud...")
    
    # Check if .streamlit/config.toml exists
    if not Path(".streamlit/config.toml").exists():
        print("❌ .streamlit/config.toml not found. Please set up Streamlit Cloud configuration.")
        return False
    
    print("✅ Streamlit Cloud configuration found.")
    print("📝 To deploy:")
    print("1. Push your code to GitHub")
    print("2. Visit https://share.streamlit.io")
    print("3. Connect your repository")
    print("4. Set up secrets in .streamlit/secrets.toml")
    return True

def deploy_digitalocean():
    """Deploy to DigitalOcean App Platform"""
    print("🌊 Deploying to DigitalOcean...")
    
    # Check if doctl is installed
    if not run_command(["doctl", "version"], "Checking DigitalOcean CLI"):
        print("❌ doctl CLI not found. Install from: https://github.com/digitalocean/doctl")
        return False
    
    # Check if app.yaml exists
    if not Path(".do/app.yaml").exists():
        print("❌ .do/app.yaml not found.")
        return False
    
    # Check authentication
    if not run_command(["doctl", "auth", "list"], "Checking DigitalOcean authentication"):
        print("❌ Please authenticate with DigitalOcean: doctl auth init")
        return False
    
    # Create app
    if not run_command(["doctl", "apps", "create", "--spec", ".do/app.yaml"], "Creating DigitalOcean app"):
        return False
    
    print("✅ DigitalOcean deployment initiated!")
    print("🔍 Check status: doctl apps list")
    return True

def deploy_docker():
    """Build and test Docker image locally"""
    print("🐳 Building Docker image...")
    
    # Build image
    if not run_command(["docker", "build", "-t", "structr-dashboard", "."], "Building Docker image"):
        return False
    
    # Test run
    print("🧪 Testing Docker image...")
    print("Run locally with: docker run -p 8501:8501 structr-dashboard")
    return True

def check_prerequisites():
    """Check if all required files exist"""
    required_files = [
        "requirements.txt",
        "dashboard_app.py",
        "start_dashboard.py",
        "config.py",
        "Dockerfile"
    ]
    
    missing_files = []
    for file in required_files:
        if not Path(file).exists():
            missing_files.append(file)
    
    if missing_files:
        print(f"❌ Missing required files: {', '.join(missing_files)}")
        return False
    
    print("✅ All required files found")
    return True

def main():
    """Main deployment function"""
    parser = argparse.ArgumentParser(description="Deploy Structr Dashboard to various platforms")
    parser.add_argument("platform", nargs="?", choices=["railway", "render", "streamlit", "digitalocean", "docker"], 
                       help="Deployment platform")
    parser.add_argument("--check", action="store_true", help="Check prerequisites only")
    
    args = parser.parse_args()
    
    print("🚀 Structr Dashboard Deployment Tool")
    print("=" * 50)
    
    # Check prerequisites
    if not check_prerequisites():
        sys.exit(1)
    
    if args.check:
        print("✅ Prerequisites check passed")
        sys.exit(0)
    
    # Check if platform is provided
    if not args.platform:
        print("❌ Error: Platform is required when not using --check")
        print("Available platforms: railway, render, streamlit, digitalocean, docker")
        sys.exit(1)
    
    # Deploy to selected platform
    success = False
    
    if args.platform == "railway":
        success = deploy_railway()
    elif args.platform == "render":
        success = deploy_render()
    elif args.platform == "streamlit":
        success = deploy_streamlit_cloud()
    elif args.platform == "digitalocean":
        success = deploy_digitalocean()
    elif args.platform == "docker":
        success = deploy_docker()
    
    if success:
        print("\n🎉 Deployment completed successfully!")
    else:
        print("\n❌ Deployment failed. Check the errors above.")
        sys.exit(1)

if __name__ == "__main__":
    main()