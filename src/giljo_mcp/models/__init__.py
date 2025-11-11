"""
Database models package for GiljoAI MCP.

This package contains all SQLAlchemy models organized by domain:
- base: Base class and utility functions
- auth: User authentication and API key management
- products: Product and vision document management
- projects: Project and development session tracking
- agents: Agent job orchestration and interactions
- templates: Reusable agent mission templates
- tasks: Task and message management
- context: Context indexing and summarization
- config: System configuration and setup

All models are re-exported here for backward compatibility.
Existing code can continue to import from src.giljo_mcp.models:
    from src.giljo_mcp.models import User, Project, MCPAgentJob
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
    MCPAgentJob,
    AgentInteraction,
    Job,
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
    "MCPAgentJob",
    "AgentInteraction",
    "Job",
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
]
