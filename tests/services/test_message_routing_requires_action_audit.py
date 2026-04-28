# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Wave 2 Item 1, Part 1 — Audit informational message emitters.

Handover 0435d wired requires_action through the auto-block path so that
informational messages (default requires_action=False) do NOT reactivate
completed agents. This audit locks in the regression guard:

- MessageRoutingService.send_message defaults to requires_action=False
- MessageRoutingService.broadcast does NOT pass requires_action -> default False
- MessageRoutingService.broadcast_to_project -> default False
- The completion_report message_type (auto-generated agent completion notice)
  uses model defaults -> requires_action=False at the column level
- The Message model column default for requires_action is False

If a future change accidentally flips one of these defaults to True, completed
agents will be auto-reactivated by routine status messages and burn tokens in
a loop. These tests prevent that regression.
"""

from __future__ import annotations

import inspect
from unittest.mock import AsyncMock, MagicMock

import pytest


# ---------------------------------------------------------------------------
# 1. MessageRoutingService.send_message default
# ---------------------------------------------------------------------------


def test_send_message_default_requires_action_false():
    """send_message must default to requires_action=False (Handover 0435d)."""
    from giljo_mcp.services.message_routing_service import MessageRoutingService

    sig = inspect.signature(MessageRoutingService.send_message)
    assert "requires_action" in sig.parameters
    assert sig.parameters["requires_action"].default is False


# ---------------------------------------------------------------------------
# 2. MessageRoutingService.broadcast — no requires_action -> default False
# ---------------------------------------------------------------------------


def test_broadcast_signature_does_not_force_requires_action_true():
    """broadcast() must not have requires_action=True hardcoded."""
    from giljo_mcp.services.message_routing_service import MessageRoutingService

    sig = inspect.signature(MessageRoutingService.broadcast)
    # broadcast() does not expose requires_action directly; it relies on
    # send_message's default of False. If a parameter is added in future, it
    # must default to False.
    if "requires_action" in sig.parameters:
        assert sig.parameters["requires_action"].default is False


def _scan_for_requires_action_true_kwarg(src_path) -> list[str]:
    """AST-based scan: returns offending Call sites that pass requires_action=True.

    Skips docstrings and comments — only matches keyword arguments in actual
    function/method calls. ``True`` and ``Constant(value=True)`` both match.
    """
    import ast

    tree = ast.parse(src_path.read_text(encoding="utf-8"))
    offenders: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        for kw in node.keywords:
            if kw.arg != "requires_action":
                continue
            value = kw.value
            if isinstance(value, ast.Constant) and value.value is True:
                offenders.append(f"line {kw.lineno}: requires_action=True")
    return offenders


def test_broadcast_does_not_pass_requires_action_true_to_send_message():
    """AST-level guard: no informational emitter passes requires_action=True as a kwarg.

    Scans the AST for ``requires_action=True`` keyword arguments in any function
    call within ``message_routing_service.py``. If a future change adds it to
    ``broadcast``, ``broadcast_to_project``, or any helper that emits
    informational messages, this test fires.
    """
    from pathlib import Path

    src_path = Path(
        Path(__file__).parent.parent.parent / "src" / "giljo_mcp" / "services" / "message_routing_service.py"
    )
    offenders = _scan_for_requires_action_true_kwarg(src_path)
    assert not offenders, (
        "MessageRoutingService must not pass requires_action=True as a kwarg — "
        "informational emitters must default to False (Handover 0435d / Wave 2 Item 1). "
        f"Offending sites: {offenders}"
    )


# ---------------------------------------------------------------------------
# 3. broadcast_to_project — same guard
# ---------------------------------------------------------------------------


def test_broadcast_to_project_signature_does_not_force_requires_action_true():
    """broadcast_to_project() must not have requires_action=True hardcoded."""
    from giljo_mcp.services.message_routing_service import MessageRoutingService

    sig = inspect.signature(MessageRoutingService.broadcast_to_project)
    if "requires_action" in sig.parameters:
        assert sig.parameters["requires_action"].default is False


# ---------------------------------------------------------------------------
# 4. Message model column default
# ---------------------------------------------------------------------------


def test_message_model_requires_action_default_false():
    """Message.requires_action column must default to False (Handover 0435d)."""
    from giljo_mcp.models.tasks import Message

    col = Message.__table__.columns["requires_action"]
    assert col.default.arg is False
    assert col.nullable is False


# ---------------------------------------------------------------------------
# 5. completion_report message uses default (False) — repository inspection
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_completion_report_message_uses_default_requires_action():
    """
    The auto-generated completion_report message MUST not set requires_action=True.

    completion_report is the canonical "informational completion broadcast" that
    notifies upstream agents that a worker finished. If it were marked
    requires_action=True, every worker completion would auto-block its parent
    orchestrator — exactly the loop Handover 0435d closed at the messaging layer.
    """
    from pathlib import Path

    repo_src_path = Path(
        Path(__file__).parent.parent.parent / "src" / "giljo_mcp" / "repositories" / "agent_job_repository.py"
    )
    assert 'message_type="completion_report"' in repo_src_path.read_text(encoding="utf-8")

    # AST-based: ensure no Call passes requires_action=True kwarg. Defaulting
    # via the column server_default keeps the auto-completion-report at False.
    offenders = _scan_for_requires_action_true_kwarg(repo_src_path)
    assert not offenders, (
        "agent_job_repository must not pass requires_action=True on auto-generated "
        f"messages. Offending sites: {offenders}"
    )


# ---------------------------------------------------------------------------
# 6. Live: auto-block returns [] for informational messages
# ---------------------------------------------------------------------------


class TestAutoBlockBehavior:
    @pytest.fixture
    def routing_service(self):
        from giljo_mcp.services.message_routing_service import MessageRoutingService

        return MessageRoutingService(
            db_manager=MagicMock(),
            tenant_manager=MagicMock(),
        )

    @pytest.mark.asyncio
    async def test_informational_message_short_circuits_auto_block(self, routing_service):
        """requires_action=False -> auto-block returns [] without DB calls."""
        mock_session = AsyncMock()
        mock_project = MagicMock()
        mock_project.status = "active"

        result = await routing_service._auto_block_completed_recipients(
            session=mock_session,
            resolved_to_agents=["agent-123"],
            project=mock_project,
            sender_display_name="orchestrator",
            is_broadcast_fanout=False,
            requires_action=False,
        )
        assert result == []
        mock_session.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_broadcast_fanout_short_circuits_auto_block(self, routing_service):
        """Broadcasts skip auto-block regardless of requires_action."""
        mock_session = AsyncMock()
        mock_project = MagicMock()
        mock_project.status = "active"

        result = await routing_service._auto_block_completed_recipients(
            session=mock_session,
            resolved_to_agents=["agent-123"],
            project=mock_project,
            sender_display_name="orchestrator",
            is_broadcast_fanout=True,
            requires_action=True,
        )
        assert result == []
