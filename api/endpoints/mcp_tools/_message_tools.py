# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""
Message Communication Tools -- @mcp.tool wrappers (BE-6042d split of mcp_sdk_server.py).

Mechanically extracted verbatim from the pre-split ``mcp_sdk_server.py``. Each
wrapper registers against the shared ``mcp`` instance from ``_base`` as a decorator
side effect at import time. Behavior, signatures, names, and descriptions unchanged.

BE-9012d (bus retirement, phase d): send_message / receive_messages / get_messages
(and their ``_drain_agent_threads`` shim support) were HARD-REMOVED — the Agent
Message Hub (create_thread / post_to_thread / get_thread_history / ...) is the sole
inter-agent messaging surface now. ``request_approval`` was never part of the bus
and is unaffected.
"""

from typing import Annotated, Any

from mcp.server.fastmcp import Context
from pydantic import Field

from api.endpoints.mcp_tools._base import (
    MCP_SHORT_TEXT_MAX,
    _call_tool,
    mcp,
)
from api.endpoints.mcp_tools._inline_approval import maybe_elicit_approval_inline


@mcp.tool(
    description=(
        "Request a user approval before continuing (HITL gate: closeout with deferred findings, "
        "an ambiguous decision). ORCHESTRATOR JOBS ONLY — the dashboard approval card binds to "
        "the orchestrator's job; a worker call returns a structured rejection "
        "(ORCHESTRATOR_ONLY_APPROVAL) and should escalate via post_to_thread instead. Creates a "
        "user_approvals row and flips the calling agent to status='awaiting_user'. options: list "
        "of {id, label} dicts. Returns {approval_id, status}. Tenant-scoped. See get_giljo_guide "
        "for how the dashboard surfaces and clears this gate."
    ),
)
async def request_approval(
    job_id: Annotated[str, Field(description="Calling agent's job_id (UUID).")],
    project_id: Annotated[str, Field(description="Project UUID the approval belongs to.")],
    reason: Annotated[
        str,
        Field(
            max_length=MCP_SHORT_TEXT_MAX, description="Plain-English explanation shown to the user (<= 2000 chars)."
        ),
    ],
    options: Annotated[
        list[dict],
        Field(description="List of {id, label} option dicts (1-10 items, unique ids)."),
    ],
    context: Annotated[
        dict | None,
        Field(description="Optional structured payload (deferred findings, etc). <= 16 KB serialized."),
    ] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "job_id": job_id,
        "project_id": project_id,
        "reason": reason,
        "options": options,
        "context": context,
    }
    result = await _call_tool(ctx, "request_approval", kwargs)
    # BE-6038 (NO-SHIP-UNTIL-GA): opt-in inline approval-card overlay. Dormant unless
    # GILJO_INLINE_APPROVAL_ELICIT is set AND the client supports elicitation; otherwise
    # returns ``result`` unchanged (today's async awaiting_user behavior). Never raises.
    return await maybe_elicit_approval_inline(ctx, result, reason=reason, options=options)
