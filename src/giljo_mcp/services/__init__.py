"""
Services module for GiljoAI MCP.

This module contains service classes for managing integrations and external tools.

Handover 0121 (Phase 1): ProjectService extracted from ToolAccessor
Handover 0123 (Phase 2): TemplateService, TaskService, MessageService, ContextService extracted
"""

from .claude_config_manager import ClaudeConfigManager
from .config_service import ConfigService
from .context_service import ContextService
from .message_service import MessageService
from .project_service import ProjectService
from .serena_detector import SerenaDetector
from .task_service import TaskService
from .template_service import TemplateService


__all__ = [
    "ClaudeConfigManager",
    "ConfigService",
    "ContextService",
    "MessageService",
    "ProjectService",
    "SerenaDetector",
    "TaskService",
    "TemplateService",
]
