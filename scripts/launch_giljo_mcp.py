#!/usr/bin/env python
"""
GiljoAI MCP Standalone Launcher
Launches GiljoAI MCP server independently
"""

import sys
import os
import subprocess
import argparse
from pathlib import Path

def setup_environment():
    """Setup environment for GiljoAI MCP"""
    # Add project root to Python path
    project_root = Path(__file__).parent.parent.absolute()
    sys.path.insert(0, str(project_root))
    
    # Load .env file if it exists
    env_file = project_root / ".env"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key.strip()] = value.strip()
    
    return project_root

def check_dependencies():
    """Check if required dependencies are installed"""
    try:
        import fastmcp
        import fastapi
        import sqlalchemy
        return True
    except ImportError as e:
        print(f"Missing dependency: {e}")
        print("Please run: pip install -r requirements.txt")
        return False

def launch_mcp_server(project_root, mode="local", port=6001):
    """Launch the MCP server"""
    print(f"Starting GiljoAI MCP Server in {mode.upper()} mode on port {port}...")
    
    # Set environment variables
    os.environ["GILJO_MCP_MODE"] = mode.upper()
    os.environ["GILJO_MCP_SERVER_PORT"] = str(port)
    
    # Launch the server
    cmd = [sys.executable, "-m", "giljo_mcp.server"]
    
    try:
        subprocess.run(cmd, cwd=project_root, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error starting server: {e}")
        return False
    except KeyboardInterrupt:
        print("\nServer stopped by user")
        return True
    
    return True

def launch_dashboard(project_root, port=6000):
    """Launch the Vue dashboard"""
    print(f"Starting GiljoAI Dashboard on port {port}...")
    
    frontend_dir = project_root / "frontend"
    if not frontend_dir.exists():
        print("Frontend directory not found. Dashboard unavailable.")
        return False
    
    # Check if npm is available
    try:
        subprocess.run(["npm", "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("npm not found. Please install Node.js to use the dashboard.")
        return False
    
    # Install dependencies if needed
    if not (frontend_dir / "node_modules").exists():
        print("Installing frontend dependencies...")
        subprocess.run(["npm", "install"], cwd=frontend_dir, check=True)
    
    # Start the dev server
    cmd = ["npm", "run", "dev", "--", "--port", str(port)]
    
    try:
        subprocess.run(cmd, cwd=frontend_dir, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error starting dashboard: {e}")
        return False
    except KeyboardInterrupt:
        print("\nDashboard stopped by user")
        return True
    
    return True

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="GiljoAI MCP Standalone Launcher")
    parser.add_argument("--mode", choices=["local", "lan", "wan"], default="local",
                       help="Deployment mode (default: local)")
    parser.add_argument("--mcp-port", type=int, default=6001,
                       help="MCP server port (default: 6001)")
    parser.add_argument("--dashboard-port", type=int, default=6000,
                       help="Dashboard port (default: 6000)")
    parser.add_argument("--no-dashboard", action="store_true",
                       help="Don't launch the dashboard")
    parser.add_argument("--dashboard-only", action="store_true",
                       help="Only launch the dashboard")
    
    args = parser.parse_args()
    
    # Setup environment
    project_root = setup_environment()
    
    print("=" * 60)
    print("GiljoAI MCP Coding Orchestrator - Standalone Mode")
    print("=" * 60)
    
    # Check dependencies
    if not args.dashboard_only and not check_dependencies():
        print("\nPlease install dependencies first:")
        print("  pip install -r requirements.txt")
        return 1
    
    # Launch components
    if args.dashboard_only:
        # Dashboard only
        if not launch_dashboard(project_root, args.dashboard_port):
            return 1
    elif args.no_dashboard:
        # MCP server only
        if not launch_mcp_server(project_root, args.mode, args.mcp_port):
            return 1
    else:
        # Both server and dashboard
        import threading
        import time
        
        # Start MCP server in a thread
        server_thread = threading.Thread(
            target=launch_mcp_server,
            args=(project_root, args.mode, args.mcp_port)
        )
        server_thread.daemon = True
        server_thread.start()
        
        # Give server time to start
        time.sleep(2)
        
        # Launch dashboard in main thread
        if not launch_dashboard(project_root, args.dashboard_port):
            return 1
    
    print("\nGiljoAI MCP shutdown complete")
    return 0

if __name__ == "__main__":
    sys.exit(main())