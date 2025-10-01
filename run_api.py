#!/usr/bin/env python3
"""
Direct API server runner for GiljoAI MCP
"""
import sys
import os
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Add src directory to Python path
script_dir = Path(__file__).parent
src_dir = script_dir / "src"
sys.path.insert(0, str(src_dir))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Import and run the server
if __name__ == "__main__":
    import uvicorn
    from api.app import app

    # Get port from environment or use default
    port = int(os.environ.get("GILJO_SERVER_PORT", 7272))

    print(f"Starting GiljoAI MCP Server on port {port}...")
    print(f"API docs will be available at: http://localhost:{port}/docs")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="debug",
        reload=False
    )
