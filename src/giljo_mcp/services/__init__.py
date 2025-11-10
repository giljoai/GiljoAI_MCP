"""
Services module for GiljoAI MCP.

This module contains service classes for managing integrations and external tools.
"""

from .claude_config_manager import ClaudeConfigManager
from .config_service import ConfigService
from .project_service import ProjectService
from .serena_detector import SerenaDetector


__all__ = ["ClaudeConfigManager", "ConfigService", "ProjectService", "SerenaDetector"]
