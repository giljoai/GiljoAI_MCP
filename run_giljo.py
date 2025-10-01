#!/usr/bin/env python3
"""
Direct runner for GiljoAI MCP server without pip install
"""
import sys
import os
from pathlib import Path

# Add src directory to Python path
script_dir = Path(__file__).parent
src_dir = script_dir / "src"
sys.path.insert(0, str(src_dir))

# Now import and run the main function
if __name__ == "__main__":
    from giljo_mcp.__main__ import main
    main()
