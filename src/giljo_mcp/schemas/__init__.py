"""
Service-layer Pydantic response models.

These models provide typed return values for service methods,
replacing dict[str, Any] returns with validated, documented models.

Created: Handover 0731
"""

from src.giljo_mcp.schemas.service_responses import (
    AuthResult,
    BroadcastResult,
    CascadeImpact,
    ConsolidationResult,
    ConversionResult,
    DeleteResult,
    GitIntegrationSettings,
    InstructionsResponse,
    MessageListResult,
    MissionResponse,
    MissionUpdateResult,
    OperationResult,
    PaginatedResult,
    PathValidationResult,
    ProductStatistics,
    PurgeResult,
    SendMessageResult,
    SetupState,
    SpawnResult,
    SuccessionResult,
    SuccessionStatus,
    TaskListResponse,
    TaskSummary,
    TaskUpdateResult,
    TemplateListResult,
    TransferResult,
    VisionUploadResult,
)


__all__ = [
    "AuthResult",
    "BroadcastResult",
    "CascadeImpact",
    "ConsolidationResult",
    "ConversionResult",
    "DeleteResult",
    "GitIntegrationSettings",
    "InstructionsResponse",
    "MessageListResult",
    "MissionResponse",
    "MissionUpdateResult",
    "OperationResult",
    "PaginatedResult",
    "PathValidationResult",
    "ProductStatistics",
    "PurgeResult",
    "SendMessageResult",
    "SetupState",
    "SpawnResult",
    "SuccessionResult",
    "SuccessionStatus",
    "TaskListResponse",
    "TaskSummary",
    "TaskUpdateResult",
    "TemplateListResult",
    "TransferResult",
    "VisionUploadResult",
]
