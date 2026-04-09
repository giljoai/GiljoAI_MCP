# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
TDD Tests for Handover 0411a: Phase Labels on AgentJob - Orchestrator Instructions.

Change D: phase_assignment_instructions in orchestrator protocol
(multi-terminal only, not CLI mode).

Split from test_orchestration_service_phase_labels.py during test reorganization.
"""

import pytest

# ============================================================================
# Change D: Phase assignment instructions in orchestrator protocol
# ============================================================================


@pytest.mark.asyncio
class TestOrchestratorPhaseInstructions:
    """Tests that get_orchestrator_instructions includes phase assignment instructions
    ONLY in multi-terminal mode (not CLI mode)."""

    async def test_phase_instructions_present_in_multi_terminal_mode(
        self, db_session, db_manager, test_project_multi_terminal, test_tenant_key
    ):
        """Verify phase_assignment_instructions present when execution_mode is multi_terminal."""
        from src.giljo_mcp.services.orchestration_service import OrchestrationService
        from src.giljo_mcp.tenant import TenantManager

        tenant_manager = TenantManager()
        service = OrchestrationService(
            db_manager=db_manager, tenant_manager=tenant_manager, test_session=db_session
        )

        # Spawn an orchestrator for the multi-terminal project
        spawn_result = await service.spawn_agent_job(
            agent_display_name="orchestrator",
            agent_name="orchestrator",
            mission="Orchestrate multi-terminal project",
            project_id=test_project_multi_terminal.id,
            tenant_key=test_tenant_key,
        )

        # Get orchestrator instructions
        instructions = await service.get_orchestrator_instructions(
            job_id=spawn_result.job_id,
            tenant_key=test_tenant_key,
        )

        assert "phase_assignment_instructions" in instructions
        phase_text = instructions["phase_assignment_instructions"]
        assert "Phase 1" in phase_text
        assert "Phase 2" in phase_text
        assert "parallel" in phase_text.lower()

    async def test_phase_instructions_absent_in_cli_mode(
        self, db_session, db_manager, test_project_cli_mode, test_tenant_key
    ):
        """Verify phase_assignment_instructions NOT present when execution_mode is claude_code_cli."""
        from src.giljo_mcp.services.orchestration_service import OrchestrationService
        from src.giljo_mcp.tenant import TenantManager

        tenant_manager = TenantManager()
        service = OrchestrationService(
            db_manager=db_manager, tenant_manager=tenant_manager, test_session=db_session
        )

        # Spawn an orchestrator for the CLI project
        spawn_result = await service.spawn_agent_job(
            agent_display_name="orchestrator",
            agent_name="orchestrator",
            mission="Orchestrate CLI project",
            project_id=test_project_cli_mode.id,
            tenant_key=test_tenant_key,
        )

        # Get orchestrator instructions
        instructions = await service.get_orchestrator_instructions(
            job_id=spawn_result.job_id,
            tenant_key=test_tenant_key,
        )

        assert "phase_assignment_instructions" not in instructions

    async def test_phase_instructions_contain_expected_content(
        self, db_session, db_manager, test_project_multi_terminal, test_tenant_key
    ):
        """Verify phase_assignment_instructions content includes all expected guidance."""
        from src.giljo_mcp.services.orchestration_service import OrchestrationService
        from src.giljo_mcp.tenant import TenantManager

        tenant_manager = TenantManager()
        service = OrchestrationService(
            db_manager=db_manager, tenant_manager=tenant_manager, test_session=db_session
        )

        spawn_result = await service.spawn_agent_job(
            agent_display_name="orchestrator",
            agent_name="orchestrator",
            mission="Orchestrate multi-terminal project",
            project_id=test_project_multi_terminal.id,
            tenant_key=test_tenant_key,
        )

        instructions = await service.get_orchestrator_instructions(
            job_id=spawn_result.job_id,
            tenant_key=test_tenant_key,
        )

        phase_text = instructions["phase_assignment_instructions"]
        # Check key content elements
        assert "Execution Phase Assignment" in phase_text
        assert "Multi-Terminal Mode" in phase_text
        assert "spawn_agent_job" in phase_text
        assert "Phase 1" in phase_text
        assert "Phase 2" in phase_text
        assert "Phase 3" in phase_text
        assert "Phase 4" in phase_text

    async def test_phase_instructions_present_for_default_mode(
        self, db_session, db_manager, test_project, test_tenant_key
    ):
        """Verify phase_assignment_instructions present when execution_mode is default (None/multi_terminal)."""
        from src.giljo_mcp.services.orchestration_service import OrchestrationService
        from src.giljo_mcp.tenant import TenantManager

        tenant_manager = TenantManager()
        service = OrchestrationService(
            db_manager=db_manager, tenant_manager=tenant_manager, test_session=db_session
        )

        # Default project (no explicit execution_mode = defaults to multi_terminal)
        spawn_result = await service.spawn_agent_job(
            agent_display_name="orchestrator",
            agent_name="orchestrator",
            mission="Orchestrate default project",
            project_id=test_project.id,
            tenant_key=test_tenant_key,
        )

        instructions = await service.get_orchestrator_instructions(
            job_id=spawn_result.job_id,
            tenant_key=test_tenant_key,
        )

        # Default mode should include phase instructions (not CLI mode)
        assert "phase_assignment_instructions" in instructions
