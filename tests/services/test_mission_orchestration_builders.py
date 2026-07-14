# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""BE-9073 Split — mission_orchestration_builders extraction: free functions + shims.

Split moved ``_build_execution_mode_fields``, ``_build_category_metadata``,
``_maybe_build_ctx_self_close_directive``, ``_is_chain_member``,
``_check_staging_redirect``, and ``_attach_protocol_and_identity`` out of
mission_orchestration_service.py into a new ``mission_orchestration_builders.py`` as
free functions (each takes explicit params instead of ``self``).
``MissionOrchestrationService`` keeps thin shims of unchanged name/signature
delegating to them — existing suites (test_mission_orchestration_service,
test_be_5122_ctx_taxonomy_and_vision_hash, test_be6198_cold_start_hardening,
test_be6212_staging_dedup, test_sec0005b_verification) call those shims directly and
must keep passing unmodified.

These tests lock the new module surface + the pass-through delegation. Pure (no DB,
no module-level mutable state) — parallel-safe under xdist.
Edition Scope: CE.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch


def test_free_functions_importable_from_mission_orchestration_builders() -> None:
    """The extracted logic is importable from the new module as free functions."""
    from giljo_mcp.services.mission_orchestration_builders import (
        attach_protocol_and_identity,
        build_category_metadata,
        build_execution_mode_fields,
        check_staging_redirect,
        is_chain_member,
        maybe_build_ctx_self_close_directive,
    )

    assert callable(attach_protocol_and_identity)
    assert callable(build_category_metadata)
    assert callable(build_execution_mode_fields)
    assert callable(check_staging_redirect)
    assert callable(is_chain_member)
    assert callable(maybe_build_ctx_self_close_directive)


def test_back_compat_shims_still_present_on_mission_orchestration_service() -> None:
    """The shims other suites depend on are still attributes of MissionOrchestrationService."""
    from giljo_mcp.services.mission_orchestration_service import MissionOrchestrationService

    assert hasattr(MissionOrchestrationService, "_build_execution_mode_fields")
    assert hasattr(MissionOrchestrationService, "_build_category_metadata")
    assert hasattr(MissionOrchestrationService, "_maybe_build_ctx_self_close_directive")
    assert hasattr(MissionOrchestrationService, "_is_chain_member")
    assert hasattr(MissionOrchestrationService, "_check_staging_redirect")
    assert hasattr(MissionOrchestrationService, "_attach_protocol_and_identity")


def test_check_staging_redirect_shim_delegates_to_free_function() -> None:
    """MissionOrchestrationService._check_staging_redirect is a pure pass-through."""
    from giljo_mcp.services.mission_orchestration_builders import check_staging_redirect
    from giljo_mcp.services.mission_orchestration_service import MissionOrchestrationService

    project = SimpleNamespace(
        staging_status="staging_complete",
        implementation_launched_at=None,
        id="proj-1",
        name="Proj",
    )

    shim_result = MissionOrchestrationService._check_staging_redirect(project, "job-1", is_chain_member=False)
    direct_result = check_staging_redirect(project, "job-1", is_chain_member=False)
    assert shim_result == direct_result


def test_maybe_build_ctx_self_close_directive_shim_delegates() -> None:
    """MissionOrchestrationService._maybe_build_ctx_self_close_directive is a pure pass-through."""
    from giljo_mcp.services.mission_orchestration_builders import maybe_build_ctx_self_close_directive
    from giljo_mcp.services.mission_orchestration_service import MissionOrchestrationService

    ctx = {"project_type_abbreviation": "NOT_CTX", "product": None}

    assert MissionOrchestrationService._maybe_build_ctx_self_close_directive(
        ctx
    ) == maybe_build_ctx_self_close_directive(ctx)


def test_build_execution_mode_fields_shim_delegates() -> None:
    """MissionOrchestrationService._build_execution_mode_fields is a pure pass-through."""
    from giljo_mcp.services.mission_orchestration_builders import build_execution_mode_fields
    from giljo_mcp.services.mission_orchestration_service import MissionOrchestrationService

    service = MissionOrchestrationService.__new__(MissionOrchestrationService)
    templates = [SimpleNamespace(name="implementer")]

    shim_result = service._build_execution_mode_fields("multi_terminal", templates, "job-1")
    direct_result = build_execution_mode_fields("multi_terminal", templates, "job-1")
    assert shim_result == direct_result
    assert "phase_assignment_instructions" in shim_result


async def test_is_chain_member_shim_delegates_with_service_handles() -> None:
    """MissionOrchestrationService._is_chain_member threads db_manager/tenant_manager through."""
    from giljo_mcp.services.mission_orchestration_service import MissionOrchestrationService

    service = MissionOrchestrationService.__new__(MissionOrchestrationService)
    service.db_manager = object()
    service.tenant_manager = object()
    session = object()

    with patch(
        "giljo_mcp.services.mission_orchestration_service.is_chain_member", new=AsyncMock(return_value=True)
    ) as mocked:
        result = await service._is_chain_member(session, "proj-1", "tk")

    assert result is True
    mocked.assert_awaited_once_with(
        session, "proj-1", "tk", db_manager=service.db_manager, tenant_manager=service.tenant_manager
    )
