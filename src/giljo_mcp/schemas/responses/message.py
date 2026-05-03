# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""Message service response models."""

from pydantic import BaseModel, ConfigDict, Field


class StagingDirective(BaseModel):
    """Staging session completion directive for orchestrator stop signal.

    Defense-in-depth Layer 5.5: Reinforced advisory STOP signal for staging
    completion (Handover 0709b).
    """

    status: str
    action: str
    message: str
    implementation_gate: str
    next_step: str

    model_config = ConfigDict(from_attributes=True)


class SendMessageResult(BaseModel):
    """Message send result.

    Returned by send_message() and broadcast().
    message_id is Optional because broadcasting to an empty project yields None.
    staging_directive is present only when a staging-phase orchestrator broadcasts.
    """

    message_id: str | None = None
    to_agents: list[str] = Field(default_factory=list)
    excluded_agents: list[str] = Field(
        default_factory=list,
        description="Agents excluded from delivery (completed/decommissioned)",
    )
    warnings: list[str] = Field(default_factory=list)
    message_type: str = "direct"
    staging_directive: StagingDirective | None = None

    model_config = ConfigDict(from_attributes=True)


class BroadcastResult(BaseModel):
    """Broadcast-to-project result.

    Extends SendMessageResult semantics with a recipient count.
    Returned by broadcast_to_project().
    """

    message_id: str | None = None
    to_agents: list[str] = Field(default_factory=list)
    excluded_agents: list[str] = Field(
        default_factory=list,
        description="Agents excluded from delivery (completed/decommissioned)",
    )
    message_type: str = "broadcast"
    recipients_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class MessageListResult(BaseModel):
    """Message list result.

    Returned by get_messages(), receive_messages(), and inspect_messages().
    The optional agent field is populated by get_messages() only.
    """

    messages: list[dict] = Field(default_factory=list)
    count: int = 0
    agent: str | None = None

    model_config = ConfigDict(from_attributes=True)


class CompleteMessageResult(BaseModel):
    """Message completion result."""

    message_id: str
    completed_by: str

    model_config = ConfigDict(from_attributes=True)


class AcknowledgeMessageResult(BaseModel):
    """Message acknowledgment result."""

    acknowledged: bool = True
    message_id: str

    model_config = ConfigDict(from_attributes=True)


class MessageStatusResult(BaseModel):
    """Message delivery/read status result."""

    message_id: str
    status: str
    acknowledged_by: list[str] = []
    completed_by: list[str] = []
    recipients_count: int = 0

    model_config = ConfigDict(from_attributes=True)
