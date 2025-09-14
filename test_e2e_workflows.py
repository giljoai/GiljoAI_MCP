#!/usr/bin/env python
"""
End-to-End Workflow Test Suite for GiljoAI MCP
Tests complete project lifecycle and multi-agent coordination
"""

import sys
import asyncio
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
import uuid

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from giljo_mcp.database import DatabaseManager
from giljo_mcp.tools.project import create_project, list_projects, project_status, close_project
from giljo_mcp.tools.agent import ensure_agent, assign_job, handoff, agent_health, decommission_agent
from giljo_mcp.tools.message import send_message, get_messages, acknowledge_message, complete_message, broadcast
from giljo_mcp.tools.context import get_context_index, get_vision