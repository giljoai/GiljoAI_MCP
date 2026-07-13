# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""BE-6054c: compose the thread loop/sleep directive into an agent mission.

Extracted into a sibling module so mission_service.py stays under the 800-line
guardrail (split, not grow). ``compose_loop_directive`` is the single entry the
mission composer calls: it reads whether the agent has a live loop directive (a
``loop_directive`` message on a non-terminal thread) and appends the directive
prose when so. Never raises — a read failure must not block a mission.

Edition Scope: CE.
"""

from __future__ import annotations

import logging
from typing import Any

from giljo_mcp.repositories.comm_thread_repository import CommThreadRepository
from giljo_mcp.services.protocol_sections.chapters_coordination import _build_thread_loop_directive


def append_loop_directive(full_protocol: str, active: bool) -> str:
    """Append the thread loop/sleep directive to a protocol when active (pure)."""
    if not active:
        return full_protocol
    return full_protocol + "\n" + _build_thread_loop_directive()


async def compose_loop_directive(
    full_protocol: str,
    open_session: Any,
    tenant_key: str,
    agent_id: str,
    logger: logging.Logger | None = None,
) -> str:
    """Append the loop/sleep directive to ``full_protocol`` iff ``agent_id`` has a
    live loop directive. ``open_session`` is a callable returning an
    async-context-manager session (e.g. ``MissionService._get_session``).
    """
    try:
        async with open_session(tenant_key) as session:
            active = await CommThreadRepository().has_active_loop_directive(session, tenant_key, agent_id)
    except Exception:  # noqa: BLE001 - resilience: never block a mission on this read
        if logger is not None:
            logger.warning("[LOOP-DIRECTIVE] Failed to read loop-directive state")
        active = False
    return append_loop_directive(full_protocol, active)
