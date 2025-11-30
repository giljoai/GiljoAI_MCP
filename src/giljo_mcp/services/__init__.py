"""
Services module for GiljoAI MCP.

This module contains service classes for managing integrations and external tools.

Handover 0121 (Phase 1): ProjectService extracted from ToolAccessor
Handover 0123 (Phase 2): TemplateService, TaskService, MessageService, ContextService, OrchestrationService extracted
Handover 0127b: ProductService extracted from direct database access
Handover 0322 (Phase 1/2): AuthService, UserService added
"""

from .auth_service import AuthService
from .claude_config_manager import ClaudeConfigManager
from .config_service import ConfigService
from .context_service import ContextService
from .git_service import GitService
from .message_service import MessageService
from .orchestration_service import OrchestrationService
from .product_service import ProductService
from .project_service import ProjectService
from .serena_detector import SerenaDetector
from .task_service import TaskService
from .template_service import TemplateService
from .user_service import UserService


__all__ = [
    "AuthService",
    "ClaudeConfigManager",
    "ConfigService",
    "ContextService",
    "GitService",
    "MessageService",
    "OrchestrationService",
    "ProductService",
    "ProjectService",
    "SerenaDetector",
    "TaskService",
    "TemplateService",
    "UserService",
]
