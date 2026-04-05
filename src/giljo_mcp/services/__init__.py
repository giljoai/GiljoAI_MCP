"""
Services module for GiljoAI MCP.

This module contains service classes for managing integrations and external tools.

Handover 0121 (Phase 1): ProjectService extracted from ToolAccessor
Handover 0123 (Phase 2): TemplateService, TaskService, MessageService, OrchestrationService extracted
Handover 0127b: ProductService extracted from direct database access
Handover 0322 (Phase 1/2): AuthService, UserService added
Handover 0424b: OrgService added for organization management
"""

from .auth_service import AuthService
from .config_service import ConfigService
from .message_routing_service import MessageRoutingService
from .message_service import MessageService
from .orchestration_service import OrchestrationService
from .org_service import OrgService
from .product_service import ProductService
from .project_service import ProjectService
from .task_service import TaskService
from .template_service import TemplateService
from .user_service import UserService


__all__ = [
    "AuthService",
    "ConfigService",
    "MessageRoutingService",
    "MessageService",
    "OrchestrationService",
    "OrgService",
    "ProductService",
    "ProjectService",
    "TaskService",
    "TemplateService",
    "UserService",
]
