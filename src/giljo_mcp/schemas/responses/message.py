# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Message service response models."""

from pydantic import BaseModel, ConfigDict, Field


class StagingDirective(BaseModel):
    """Staging session completion directive — success or diagnostic.

    `status` distinguishes the success path from diagnostic non-success paths:
      - "STAGING_SESSION_COMPLETE": staging flag was flipped this call. action="STOP".
      - "ALREADY_COMPLETE": project was already staged; this call did not change state.
      - "NOT_BROADCAST": staging-phase orchestrator sent a single-recipient direct
        message; STAGING_COMPLETE requires to_agents=['all'] + message_type='broadcast'.
      - "NOT_ORCHESTRATOR": broadcast sender is not the orchestrator; only the
        orchestrator can complete staging.
      - "SENDER_NOT_FOUND": from_agent did not resolve to an active execution.

    Only the success path populates `action`, `implementation_gate`, and `next_step`.
    Diagnostic statuses populate `status` + `message` only.
    """

    status: str
    message: str
    action: str | None = None
    implementation_gate: str | None = None
    next_step: str | None = None

    model_config = ConfigDict(from_attributes=True)


class SendMessageResult(BaseModel):
    """Message send result.

    Returned by send_message() and broadcast().
    message_id is Optional because broadcasting to an empty project yields None.
    staging_directive is populated on broadcast attempts during staging (success
    flips the staging flag; diagnostic statuses explain why a broadcast did NOT
    flip the flag). It remains None for ordinary direct messages outside staging.
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
