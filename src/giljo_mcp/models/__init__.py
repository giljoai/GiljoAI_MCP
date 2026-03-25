"""
Database models package for GiljoAI MCP.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️  IMPORT GUIDANCE FOR NEW CODE (Post-Handover 0128a)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ PREFERRED (New Code):
Use specific module imports for clarity and maintainability:

    from src.giljo_mcp.models.auth import User, APIKey, ApiKeyIpLog, MCPSession
    from src.giljo_mcp.models.projects import Project, ProjectType
    from src.giljo_mcp.models.agent_identity import AgentJob, AgentExecution
    from src.giljo_mcp.models.products import Product, VisionDocument
    from src.giljo_mcp.models.tasks import Task, Message
    from src.giljo_mcp.models.templates import AgentTemplate
    from src.giljo_mcp.models.context import MCPContextIndex
    from src.giljo_mcp.models.config import Configuration, GitConfig

⚠️  LEGACY (Existing Code Only):
Backward compatibility maintained for 427 existing imports:

    from src.giljo_mcp.models import User, Project, AgentJob

This works but obscures which domain the model belongs to.
Use modular imports in new code to benefit from domain organization.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Package Structure (Post-Handover 0128a):
----------------------------------------
src/giljo_mcp/models/
├── base.py            → Base, generate_uuid, generate_project_alias
├── auth.py            → User, APIKey, MCPSession
├── products.py        → Product, VisionDocument, Vision
├── projects.py        → Project, ProjectType
├── agent_identity.py  → AgentJob, AgentExecution (Handover 0366a)
├── templates.py       → AgentTemplate, TemplateArchive, TemplateUsageStats
├── tasks.py           → Task, Message
├── context.py         → MCPContextIndex
└── config.py          → Configuration, DiscoveryConfig, GitConfig, GitCommit, SetupState,
                          OptimizationRule, OptimizationMetric, DownloadToken, ApiMetrics

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
    DiscoveryConfig,
    DownloadToken,
    GitCommit,
    GitConfig,
    OptimizationMetric,
    OptimizationRule,
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

# Product Memory models (Handover 0390a)
from .product_memory_entry import (
    ProductMemoryEntry,
)

# Product models
from .products import (
    Product,
    VisionDocument,
)

# Project models
from .projects import (
    Project,
    ProjectType,
)

# Settings models
from .settings import Settings

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
    TemplateUsageStats,
)


# Export all for backward compatibility
__all__ = [
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
    # Config
    "DiscoveryConfig",
    "DownloadToken",
    "GitCommit",
    "GitConfig",
    # Context
    "MCPContextIndex",
    "MCPSession",
    "Message",
    "MessageAcknowledgment",
    "MessageCompletion",
    "MessageRecipient",
    # OAuth
    "OAuthAuthorizationCode",
    "OptimizationMetric",
    "OptimizationRule",
    "OrgMembership",
    # Organizations (Handover 0424a)
    "Organization",
    # Products
    "Product",
    # Product Memory (Handover 0390a)
    "ProductMemoryEntry",
    # Projects
    "Project",
    "ProjectType",
    # Settings
    "Settings",
    "SetupState",
    # Tasks
    "Task",
    "TemplateArchive",
    "TemplateUsageStats",
    # Auth
    "User",
    "VisionDocument",
    "generate_project_alias",
    "generate_uuid",
]
