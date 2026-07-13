# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Dedicated chain-conductor staging-response builder (BE-6186).

The dedicated chain conductor is a PROJECT-LESS orchestrator (BE-6184): it owns no
project row, so the project-bound staging assembler in
``MissionOrchestrationService`` cannot build its staging response. This module owns
the small pure builder for it: given a resolved conductor ``ChainContext`` and the
conductor's own ``job_id``, it returns the staging response carrying CH_CAPABILITY +
CH_CHAIN_STAGING as ``orchestrator_protocol`` (the same shape a project-bound staging
response uses), so the conductor receives its authoritative staging script rather than
the STOP placeholder BE-6184 returned.

Factored out of ``mission_orchestration_service.py`` to keep that module under the
800-line guardrail (BE-6186). Pure: no DB, no session; the caller resolves the
``ChainContext`` and threads it in. Edition Scope: CE.
"""

from __future__ import annotations

from typing import Any

from giljo_mcp.platform_registry import Platform, get_platform
from giljo_mcp.services.protocol_sections.chapters_chain import (
    _build_ch_capability,
    _build_ch_chain_staging,
)
from giljo_mcp.services.sequence_chain_context import ChainContext


def build_conductor_staging_response(
    *,
    chain_ctx: ChainContext,
    job_id: str,
    agent_id: str,
    tenant_key: str,
    product_id: str | None = None,
    preset: Platform | None = None,
) -> dict[str, Any]:
    """Return the staging response for a dedicated, project-less chain conductor.

    ``chain_ctx`` is a resolved conductor ChainContext (role == "conductor"). The
    conductor's own ``job_id`` is threaded into CH_CHAIN_STAGING (its write channel
    for the chain mission via update_job_mission). CH_CAPABILITY + CH_CHAIN_STAGING
    are returned under ``orchestrator_protocol`` exactly the way the project-bound
    staging assembler carries the protocol, so the conductor consumes it the same way.

    BE-6177 (UNIT 1): the conductor now READS DEEP before planning and writes ONLY the
    chain mission (with structured per-project contracts), no longer each project's
    mission. ``product_id`` is the conductor's deep-read handle: it is surfaced in the
    identity block so the conductor can call get_context(product_id=...) for the
    product's conventions and each project's description before authoring contracts. It
    is the head project's product_id, resolved by the caller; None when the head
    project is gone (the conductor degrades gracefully to list_projects).
    """
    chain_mode = chain_ctx.execution_mode
    platform = get_platform(chain_mode)
    can_spawn = platform.can_spawn_terminals if platform is not None else True

    # BE-8003f (D2 activation): a resolved harness ``preset`` (shell-less) renders the
    # inline-conducting CH_CAPABILITY ladder; preset=None keeps today's bytes (D1).
    orchestrator_protocol = {
        "ch_capability": _build_ch_capability(
            execution_mode=chain_mode,
            can_spawn_terminals=can_spawn,
            preset=preset,
        ),
        "ch_chain_staging": _build_ch_chain_staging(
            run_id=chain_ctx.run_id,
            resolved_order=chain_ctx.resolved_order,
            execution_mode=chain_mode,
            job_id=job_id,
            product_id=product_id,
        ),
        "navigation_hint": (
            "You are the dedicated chain conductor. CH_CHAIN_STAGING is your "
            "authoritative staging script; CH_CAPABILITY states how each project is spawned."
        ),
    }

    identity: dict[str, Any] = {
        "job_id": job_id,
        "agent_id": agent_id,
        "project_id": None,
        "product_id": product_id,
        "run_id": chain_ctx.run_id,
        "tenant_key": tenant_key,
        "id_glossary": {
            "job_id": "Your OWN conductor job: update_job_mission (chain mission), complete_job (staging-end)",
            "agent_id": "Use for: post_to_thread(from_agent), get_thread_history(as_participant) on the Hub thread you create",
            "product_id": (
                "The chain's product: read context BEFORE planning via "
                "get_context(product_id=...) (product conventions + each project's "
                "description); the deep read that lets you write concrete contracts"
            ),
        },
    }

    # BE-6187: the conductor STANDS UP the Hub thread itself as Step 0 of
    # CH_CHAIN_STAGING (create_thread), then joins it (join_thread). The server does
    # NOT create the thread; it only exposes the tools the conductor needs to do so.
    # Sub-orchestrators later discover the thread via search_threads(run_id).
    #
    # BE-6177 (UNIT 1): get_context + list_projects are the conductor's deep-read
    # affordance (read the product conventions + every project description before
    # planning). update_project_mission is GONE: the conductor writes ONLY the chain
    # mission (update_job_mission); each sub-orchestrator authors its OWN project
    # mission at its turn, so the conductor never has a reason to write one.
    mcp_tools_available = [
        "create_thread",
        "join_thread",
        "get_context",
        "list_projects",
        "update_job_mission",
        "stage_project",
        "get_workflow_status",
        "complete_job",
        "post_to_thread",
        "get_thread_history",
    ]

    return {
        "status": "CHAIN_CONDUCTOR_STAGING",
        "identity": identity,
        "orchestrator_protocol": orchestrator_protocol,
        "mcp_tools_available": mcp_tools_available,
        "thin_client": True,
    }
