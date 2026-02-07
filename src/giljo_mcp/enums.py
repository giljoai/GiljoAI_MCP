"""
Consolidated enums for GiljoAI MCP
Single source of truth for all enumeration types
"""

from enum import Enum


class AgentRole(Enum):
    """Standard agent roles with predefined capabilities."""

    ORCHESTRATOR = "orchestrator"
    ANALYZER = "analyzer"
    IMPLEMENTER = "implementer"
    TESTER = "tester"
    REVIEWER = "reviewer"
    DOCUMENTER = "documenter"


class ProjectType(Enum):
    """Project types for template customization."""

    FOUNDATION = "foundation"
    MCP_INTEGRATION = "mcp_integration"
    ORCHESTRATION = "orchestration"
    USER_INTERFACE = "user_interface"
    DEPLOYMENT = "deployment"
    GENERAL = "general"


class AgentStatus(Enum):
    """Agent lifecycle status."""

    PENDING = "pending"
    ACTIVE = "active"
    IDLE = "idle"
    WORKING = "working"
    DECOMMISSIONED = "decommissioned"
    ERROR = "error"


class ProjectStatus(Enum):
    """Project lifecycle status (Handover 0071)."""

    ACTIVE = "active"
    INACTIVE = "inactive"  # Deactivated projects (can be reactivated)
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    DELETED = "deleted"  # Soft-deleted projects (Handover 0070)


class MessageType(Enum):
    """Message types for inter-agent communication."""

    DIRECT = "direct"
    BROADCAST = "broadcast"
    HANDOFF = "handoff"
    STATUS = "status"
    ERROR = "error"


class MessagePriority(Enum):
    """Message priority levels."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"
    CRITICAL = "critical"


class MessageStatus(Enum):
    """Message processing status."""

    PENDING = "pending"
    ACKNOWLEDGED = "acknowledged"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


class TemplateCategory(Enum):
    """Template categories."""

    ROLE = "role"
    PROJECT_TYPE = "project_type"
    CUSTOM = "custom"
    SPECIALIZED = "specialized"
    CORE = "core"


class JobStatus(Enum):
    """Job execution status."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ContextStatus(Enum):
    """Context usage status for visual indicators."""

    GREEN = "green"  # < 50%
    YELLOW = "yellow"  # 50-80%
    RED = "red"  # > 80%
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    EXCEEDED = "exceeded"
