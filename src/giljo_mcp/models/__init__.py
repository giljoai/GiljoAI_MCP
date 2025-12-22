"""
Database models package for GiljoAI MCP.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️  IMPORT GUIDANCE FOR NEW CODE (Post-Handover 0128a)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ PREFERRED (New Code):
Use specific module imports for clarity and maintainability:

    from src.giljo_mcp.models.auth import User, APIKey, MCPSession
    from src.giljo_mcp.models.projects import Project, Session
    from src.giljo_mcp.models.agents import AgentInteraction, Job
    from src.giljo_mcp.models.agent_identity import AgentJob, AgentExecution
    from src.giljo_mcp.models.products import Product, VisionDocument
    from src.giljo_mcp.models.tasks import Task, Message
    from src.giljo_mcp.models.templates import AgentTemplate
    from src.giljo_mcp.models.context import ContextIndex, MCPContextIndex
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
├── projects.py        → Project, Session
├── agents.py          → AgentInteraction, Job
├── agent_identity.py  → AgentJob, AgentExecution (Handover 0366a)
├── templates.py       → AgentTemplate, TemplateArchive, TemplateAugmentation, TemplateUsageStats
├── tasks.py           → Task, Message
├── context.py         → ContextIndex, LargeDocumentIndex, MCPContextIndex, MCPContextSummary
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
from .base import (
    Base,
    generate_uuid,
    generate_project_alias,
)

# Auth models
from .auth import (
    User,
    APIKey,
    MCPSession,
)

# Product models
from .products import (
    Product,
    VisionDocument,
    Vision,
)

# Project models
from .projects import (
    Project,
    Session,
)

# Agent models
from .agents import (
    AgentInteraction,
    Job,
)

# Agent Identity models (Handover 0366a)
from .agent_identity import (
    AgentJob,
    AgentExecution,
)

# Template models
from .templates import (
    AgentTemplate,
    TemplateArchive,
    TemplateAugmentation,
    TemplateUsageStats,
)

# Task and message models
from .tasks import (
    Task,
    Message,
)

# Context models
from .context import (
    ContextIndex,
    LargeDocumentIndex,
    MCPContextIndex,
    MCPContextSummary,
)

# Configuration models
from .config import (
    Configuration,
    DiscoveryConfig,
    GitConfig,
    GitCommit,
    SetupState,
    OptimizationRule,
    OptimizationMetric,
    DownloadToken,
    ApiMetrics,
)

# Settings models
from .settings import Settings

# Export all for backward compatibility
__all__ = [
    # Base
    "Base",
    "generate_uuid",
    "generate_project_alias",
    # Auth
    "User",
    "APIKey",
    "MCPSession",
    # Products
    "Product",
    "VisionDocument",
    "Vision",
    # Projects
    "Project",
    "Session",
    # Agents
    "AgentInteraction",
    "Job",
    # Agent Identity (Handover 0366a)
    "AgentJob",
    "AgentExecution",
    # Templates
    "AgentTemplate",
    "TemplateArchive",
    "TemplateAugmentation",
    "TemplateUsageStats",
    # Tasks
    "Task",
    "Message",
    # Context
    "ContextIndex",
    "LargeDocumentIndex",
    "MCPContextIndex",
    "MCPContextSummary",
    # Config
    "Configuration",
    "DiscoveryConfig",
    "GitConfig",
    "GitCommit",
    "SetupState",
    "OptimizationRule",
    "OptimizationMetric",
    "DownloadToken",
    "ApiMetrics",
    # Settings
    "Settings",
]
