# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Database models package for GiljoAI MCP.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️  IMPORT GUIDANCE FOR NEW CODE (Post-Handover 0128a)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ PREFERRED (New Code):
Use specific module imports for clarity and maintainability:

    from giljo_mcp.models.auth import User, APIKey, ApiKeyIpLog, MCPSession
    from giljo_mcp.models.projects import Project, TaxonomyType
    from giljo_mcp.models.agent_identity import AgentJob, AgentExecution
    from giljo_mcp.models.products import Product, VisionDocument
    from giljo_mcp.models.tasks import Task, Message
    from giljo_mcp.models.templates import AgentTemplate
    from giljo_mcp.models.context import MCPContextIndex
    from giljo_mcp.models.config import Configuration, SetupState

⚠️  LEGACY (Existing Code Only):
Backward compatibility maintained for 427 existing imports:

    from giljo_mcp.models import User, Project, AgentJob

This works but obscures which domain the model belongs to.
Use modular imports in new code to benefit from domain organization.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Package Structure (Post-Handover 0128a):
----------------------------------------
src/giljo_mcp/models/
├── base.py            → Base, generate_uuid, generate_project_alias
├── auth.py            → User, APIKey, MCPSession
├── products.py        → Product, VisionDocument, Vision
├── projects.py        → Project, TaxonomyType
├── agent_identity.py  → AgentJob, AgentExecution (Handover 0366a)
├── templates.py       → AgentTemplate, TemplateArchive
├── tasks.py           → Task, Message
├── context.py         → MCPContextIndex
└── config.py          → Configuration, SetupState, DownloadToken, ApiMetrics

Migration Strategy:
-------------------
- New files: Always use modular imports
- Modified files: Update imports while you're editing
- Untouched files: Leave as-is (don't create unnecessary churn)

Benefits of Modular Imports:
-----------------------------
✓ Clear domain boundaries (auth vs projects vs agents)
✓ Easier code navigation
✓ Better IDE autocompletion
✓ Self-documenting dependencies
✓ Reduced merge conflicts

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

# Base classes and utilities
# Agent Identity models (Handover 0366a, 0402)
from .agent_identity import (
    AgentExecution,
    AgentJob,
    AgentTodoItem,
)

# Auth models
from .auth import (
    APIKey,
    ApiKeyIpLog,
    MCPSession,
    User,
    UserFieldPriority,
)
from .base import (
    Base,
    generate_project_alias,
    generate_uuid,
)

# Configuration models
from .config import (
    ApiMetrics,
    Configuration,
    DownloadToken,
    SetupState,
)

# Context models
from .context import (
    MCPContextIndex,
)

# OAuth models
from .oauth import (
    OAuthAuthorizationCode,
)

# Organization models (Handover 0424a)
from .organizations import (
    Organization,
    OrgMembership,
)

# Product Agent Assignment (junction table for per-product template toggle)
from .product_agent_assignment import (
    ProductAgentAssignment,
)

# Product Memory models (Handover 0390a)
from .product_memory_entry import (
    ProductMemoryEntry,
)

# Product models
from .products import (
    Product,
    ProductArchitecture,
    ProductTechStack,
    ProductTestConfig,
    VisionDocument,
    VisionDocumentSummary,
)

# Project models
from .projects import (
    Project,
    TaxonomyType,
)

# Settings models
from .settings import Settings
from .system_setting import SystemSetting

# Task and message models
from .tasks import (
    Message,
    MessageAcknowledgment,
    MessageCompletion,
    MessageRecipient,
    Task,
)

# Template models
from .templates import (
    AgentTemplate,
    TemplateArchive,
)

# User approval primitive (BE-5029 Phase A)
from .user_approval import (
    VALID_USER_APPROVAL_STATUSES,
    UserApproval,
)


# Export all for backward compatibility
__all__ = [
    "VALID_USER_APPROVAL_STATUSES",
    # Auth
    "APIKey",
    "AgentExecution",
    "AgentJob",
    "AgentTemplate",
    "AgentTodoItem",
    "ApiKeyIpLog",
    "ApiMetrics",
    # Base
    "Base",
    # Config
    "Configuration",
    "DownloadToken",
    # Context
    "MCPContextIndex",
    "MCPSession",
    "Message",
    "MessageAcknowledgment",
    "MessageCompletion",
    "MessageRecipient",
    # OAuth
    "OAuthAuthorizationCode",
    "OrgMembership",
    # Organizations (Handover 0424a)
    "Organization",
    # Products
    "Product",
    # Product Agent Assignment
    "ProductAgentAssignment",
    "ProductArchitecture",
    # Product Memory (Handover 0390a)
    "ProductMemoryEntry",
    "ProductTechStack",
    "ProductTestConfig",
    # Projects
    "Project",
    # Settings
    "Settings",
    "SetupState",
    "SystemSetting",
    # Tasks
    "Task",
    "TaxonomyType",
    "TemplateArchive",
    "User",
    "UserApproval",
    "UserFieldPriority",
    "VisionDocument",
    "VisionDocumentSummary",
    "generate_project_alias",
    "generate_uuid",
]
