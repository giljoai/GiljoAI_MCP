# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""BE-6209c (Q2) — protocol_etag cache prose.

BE-6208g wired the opt-in protocol ETag mechanism end-to-end (service computes the
etag, MissionResponse carries protocol_etag/protocol_unchanged, get_job_mission passes
protocol_etag through) but NOTHING told the agent to capture the etag on call #1 and
echo it on a later call. The etag can only be carried by the AGENT across calls (the
tool layer is stateless), so the fix is PROSE: a cache note in both protocols telling
the agent to remember protocol_etag and reuse the cached protocol when
protocol_unchanged=true comes back.

Pure-string assertions (no DB, no module-level mutable state) — parallel-safe.
Edition Scope: CE.
"""

from __future__ import annotations

from giljo_mcp.services.protocol_sections.agent_lifecycle import _generate_orchestrator_protocol
from giljo_mcp.services.protocol_sections.agent_protocol import _generate_agent_protocol


def test_worker_protocol_has_etag_cache_note() -> None:
    """The worker 5-phase protocol Phase-1 tells the agent to remember + reuse protocol_etag."""
    proto = _generate_agent_protocol(
        job_id="job-6209c",
        tenant_key="tk_6209c",
        agent_name="implementer",
        agent_id="exec-6209c",
        execution_mode="claude-code",
        job_type="agent",
        tool="claude-code",
    )
    assert "PROTOCOL CACHE" in proto
    assert "protocol_etag" in proto
    assert "protocol_unchanged=true" in proto
    assert "reuse the" in proto


def test_orchestrator_protocol_has_etag_cache_note() -> None:
    """The orchestrator 3-phase protocol Phase-1 MANDATORY block carries the same cache note."""
    proto = _generate_orchestrator_protocol(
        job_id="job-6209c",
        tenant_key="tk_6209c",
        executor_id="exec-6209c",
        execution_mode="multi_terminal",
        tool="multi_terminal",
    )
    assert "PROTOCOL CACHE" in proto
    assert "protocol_etag" in proto
    assert "protocol_unchanged=true" in proto
    assert "reuse the copy you" in proto
