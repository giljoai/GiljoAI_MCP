"""
Services module for GiljoAI MCP.

This module contains service classes for managing integrations and external tools.
"""

from .claude_config_manager import ClaudeConfigManager
from .serena_detector import SerenaDetector

__all__ = ["SerenaDetector", "ClaudeConfigManager"]
