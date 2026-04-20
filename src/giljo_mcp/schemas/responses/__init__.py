# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Service-layer Pydantic response models for GiljoAI MCP.

Re-exports all domain-specific response models so that existing imports
(``from giljo_mcp.schemas.service_responses import X``) continue to work
unchanged. New code may import directly from domain sub-modules.

Split from monolithic service_responses.py in Sprint 002e.
"""

from giljo_mcp.schemas.responses.auth import (
    ApiKeyCreateResult,
    ApiKeyInfo,
    AuthResult,
    SetupState,
    SetupStateInfo,
    UserInfo,
)
from giljo_mcp.schemas.responses.consolidation import (
    ConsolidationResult,
    MultiLevelSummaryLevel,
    SummarizeMultiLevelResult,
    SummarizeSingleResult,
    SummaryLevel,
)
from giljo_mcp.schemas.responses.message import (
    AcknowledgeMessageResult,
    BroadcastResult,
    CompleteMessageResult,
    MessageListResult,
    MessageStatusResult,
    SendMessageResult,
    StagingDirective,
)
from giljo_mcp.schemas.responses.orchestration import (
    AgentTodoCounts,
    AgentWorkflowDetail,
    CompleteJobResult,
    DismissResult,
    ErrorReportResult,
    InstructionsResponse,
    JobListResult,
    MissionResponse,
    MissionUpdateResult,
    PendingJobsResult,
    ProgressResult,
    ReactivationResult,
    SpawnResult,
    SuccessionContextResult,
    SuccessionResult,
    SuccessionStatus,
    WorkflowStatus,
)
from giljo_mcp.schemas.responses.product import (
    CascadeImpact,
    GitIntegrationSettings,
    PathValidationResult,
    ProductStatistics,
    PurgeResult,
    VisionUploadResult,
)
from giljo_mcp.schemas.responses.project import (
    ActiveProjectDetail,
    CanCloseResult,
    CloseoutData,
    CloseoutPromptResult,
    NuclearDeleteResult,
    ProjectCloseOutResult,
    ProjectCompleteResult,
    ProjectData,
    ProjectDetail,
    ProjectLaunchResult,
    ProjectListItem,
    ProjectMissionUpdateResult,
    ProjectPurgeResult,
    ProjectResumeResult,
    ProjectSummaryResult,
    ProjectSwitchResult,
    ProjectTypeInfo,
    SoftDeleteResult,
)
from giljo_mcp.schemas.responses.shared import (
    DeleteResult,
    OperationResult,
    PaginatedResult,
)
from giljo_mcp.schemas.responses.task import (
    ConversionResult,
    TaskListResponse,
    TaskSummary,
    TaskUpdateResult,
)
from giljo_mcp.schemas.responses.template import (
    TemplateCreateResult,
    TemplateDetail,
    TemplateGetResult,
    TemplateListResult,
    TemplateUpdateResult,
)


__all__ = [
    "AcknowledgeMessageResult",
    "ActiveProjectDetail",
    # Orchestration
    "AgentTodoCounts",
    "AgentWorkflowDetail",
    "ApiKeyCreateResult",
    "ApiKeyInfo",
    # Auth
    "AuthResult",
    "BroadcastResult",
    "CanCloseResult",
    "CascadeImpact",
    "CloseoutData",
    "CloseoutPromptResult",
    "CompleteJobResult",
    "CompleteMessageResult",
    "ConsolidationResult",
    "ConversionResult",
    # Shared
    "DeleteResult",
    "DismissResult",
    "ErrorReportResult",
    "GitIntegrationSettings",
    "InstructionsResponse",
    "JobListResult",
    "MessageListResult",
    "MessageStatusResult",
    "MissionResponse",
    "MissionUpdateResult",
    "MultiLevelSummaryLevel",
    "NuclearDeleteResult",
    "OperationResult",
    "PaginatedResult",
    "PathValidationResult",
    "PendingJobsResult",
    # Product
    "ProductStatistics",
    "ProgressResult",
    "ProjectCloseOutResult",
    "ProjectCompleteResult",
    "ProjectData",
    "ProjectDetail",
    "ProjectLaunchResult",
    "ProjectListItem",
    "ProjectMissionUpdateResult",
    "ProjectPurgeResult",
    "ProjectResumeResult",
    "ProjectSummaryResult",
    "ProjectSwitchResult",
    # Project
    "ProjectTypeInfo",
    "PurgeResult",
    "ReactivationResult",
    "SendMessageResult",
    "SetupState",
    "SetupStateInfo",
    "SoftDeleteResult",
    "SpawnResult",
    # Message
    "StagingDirective",
    "SuccessionContextResult",
    "SuccessionResult",
    "SuccessionStatus",
    "SummarizeMultiLevelResult",
    "SummarizeSingleResult",
    # Consolidation
    "SummaryLevel",
    # Task
    "TaskListResponse",
    "TaskSummary",
    "TaskUpdateResult",
    "TemplateCreateResult",
    "TemplateDetail",
    "TemplateGetResult",
    # Template
    "TemplateListResult",
    "TemplateUpdateResult",
    "UserInfo",
    "VisionUploadResult",
    "WorkflowStatus",
]
