# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""BE-6038 (project BE-6255): opt-in inline approval-card overlay for ``request_approval``.

NO-SHIP-UNTIL-GA. Additive and DORMANT by default. When the
``GILJO_INLINE_APPROVAL_ELICIT`` flag is on AND the calling client declares the
elicitation capability, ``request_approval`` opportunistically surfaces the approval
card inline (via the MCP elicitation round-trip) and routes an accepted choice through
the SAME atomic ``UserApprovalService.mark_decided`` the dashboard ``/decide`` endpoint
uses -- there is NO second write path. On ANY miss -- flag off, no capability, options
empty, declined/cancelled, the transport cannot carry the round-trip, or a concurrent
dashboard decision already resolved the row -- this returns the original result unchanged
so today's exact async ``awaiting_user`` behavior holds. The overlay never raises into the
tool.

Constraint C1 (BE-6255 design, verified in the SDK): server-initiated elicitation cannot
round-trip while the MCP transport runs ``json_response=True`` (the streamable-HTTP handler
drops server-initiated requests). End-to-end inline rendering therefore lights up only once
the transport carries the elicit round-trip (INF-6038 / the GA SDK), which is why the flag
stays OFF until GA. The server-side decide-convergence logic here is reusable as-is when
that lands.

Edition Scope: Both.
"""

from __future__ import annotations

import logging
import os
from enum import Enum
from typing import Any

from mcp.server.fastmcp import Context
from pydantic import Field as PField
from pydantic import create_model


logger = logging.getLogger(__name__)

_FLAG_ENV = "GILJO_INLINE_APPROVAL_ELICIT"
_TRUTHY = {"1", "true", "yes", "on"}


def _inline_elicit_enabled() -> bool:
    """Feature flag, default OFF (NO-SHIP-UNTIL-GA)."""
    return os.getenv(_FLAG_ENV, "").strip().lower() in _TRUTHY


def _client_supports_elicitation(ctx: Context) -> bool:
    """True only if the calling client declared the elicitation capability.

    Best-effort: a probe failure (no session, older SDK) is treated as "no support"
    and must never raise into the tool.
    """
    try:
        from mcp.types import ClientCapabilities, ElicitationCapability

        session = ctx.session
        return bool(session.check_client_capability(ClientCapabilities(elicitation=ElicitationCapability())))
    except Exception:  # noqa: BLE001 - capability probe must never raise into the tool
        return False


def _normalize_options(options: list[dict] | None) -> list[dict]:
    """Keep only well-formed {id, label} option dicts with a non-empty id."""
    if not options:
        return []
    return [opt for opt in options if isinstance(opt, dict) and opt.get("id")]


def _build_choice_schema(options: list[dict]):
    """Dynamic single-field pydantic model whose ``choice`` is an enum of option ids.

    Member names are positional (``opt_<idx>``) so option ids containing hyphens/spaces
    stay valid; each enum *value* is the real option id. Labels ride ``enumNames`` (FE-1330
    elicitation enum convention) for nicer host rendering.
    """
    ids = [opt["id"] for opt in options]
    labels = [opt.get("label") or opt["id"] for opt in options]
    members = {f"opt_{idx}": opt_id for idx, opt_id in enumerate(ids)}
    choice_enum = Enum("ApprovalChoice", members)
    return create_model(
        "InlineApprovalResponse",
        choice=(
            choice_enum,
            PField(description="Selected option id", json_schema_extra={"enumNames": labels}),
        ),
    )


def _format_message(reason: str, options: list[dict]) -> str:
    lines = [reason, "", "Options:"]
    lines.extend(f"  - {opt.get('label') or opt['id']} (id: {opt['id']})" for opt in options)
    return "\n".join(lines)


def _extract_choice(data: Any) -> Any:
    """Pull the chosen option id out of the validated elicit response (enum or dict)."""
    val = getattr(data, "choice", None)
    if val is None and isinstance(data, dict):
        val = data.get("choice")
    return getattr(val, "value", val)


async def _decide_inline(ctx: Context, approval_id: str, option_id: str) -> bool:
    """Resolve the approval inline through the existing atomic write path.

    Returns True on a successful decide; None-equivalent (False) when the row was already
    resolved (concurrent dashboard decision), absent, or the write failed -- in which case
    the caller falls back to the async ``awaiting_user`` path.
    """
    from api.endpoints.mcp_tools._base import _get_tool_accessor, _resolve_tenant, _resolve_user_id
    from giljo_mcp.exceptions import ResourceNotFoundError, ValidationError

    try:
        accessor = _get_tool_accessor()
        tenant_key = _resolve_tenant(ctx)
        user_id = _resolve_user_id(ctx)
        await accessor._user_approval_service.mark_decided(
            tenant_key=tenant_key,
            approval_id=approval_id,
            option_id=option_id,
            user_id=user_id,
        )
        return True
    except (ValidationError, ResourceNotFoundError):
        # Not pending (dashboard won the race) or gone -> already resolved elsewhere.
        logger.info("[BE-6038] inline decide superseded (concurrent/absent) approval=%s", approval_id)
        return False
    except Exception:  # noqa: BLE001 - any write failure falls back to the async path
        logger.warning("[BE-6038] inline decide failed approval=%s; async fallback", approval_id, exc_info=True)
        return False


async def maybe_elicit_approval_inline(
    ctx: Context | None,
    approval_result: Any,
    *,
    reason: str,
    options: list[dict] | None,
) -> Any:
    """Overlay an inline elicitation on a freshly created pending approval.

    Returns the (possibly augmented) result. NEVER raises: every miss returns
    ``approval_result`` unchanged so the async ``awaiting_user`` fallback holds.
    """
    if ctx is None or not _inline_elicit_enabled():
        return approval_result
    if not isinstance(approval_result, dict):
        return approval_result
    approval_id = approval_result.get("approval_id")
    if not approval_id or approval_result.get("status") != "pending":
        return approval_result

    norm_options = _normalize_options(options)
    if not norm_options or not _client_supports_elicitation(ctx):
        return approval_result

    try:
        schema = _build_choice_schema(norm_options)
    except Exception:  # noqa: BLE001 - schema build is best-effort
        logger.warning("[BE-6038] inline approval schema build failed; async fallback", exc_info=True)
        return approval_result

    try:
        result = await ctx.elicit(message=_format_message(reason, norm_options), schema=schema)
    except Exception:  # noqa: BLE001 - transport may not carry the round-trip (constraint C1)
        logger.info("[BE-6038] inline elicit unavailable; async awaiting_user fallback", exc_info=True)
        return approval_result

    if getattr(result, "action", None) != "accept" or getattr(result, "data", None) is None:
        return approval_result  # declined / cancelled -> leave pending for the dashboard

    choice = _extract_choice(result.data)
    if choice not in {opt["id"] for opt in norm_options}:
        return approval_result

    if not await _decide_inline(ctx, approval_id, choice):
        return approval_result

    return {**approval_result, "status": "decided", "decided_option_id": choice, "surface": "inline"}
