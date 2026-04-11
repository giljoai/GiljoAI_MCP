# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
TDD Tests for Handover 0411a: Phase Labels on AgentJob - Template ID and List Jobs.

Change B: template_id populated on AgentJob when template found.
Change C: list_jobs includes `phase` in the response dict.

Split from test_orchestration_service_phase_labels.py during test reorganization.
"""

import pytest
from sqlalchemy import select

from src.giljo_mcp.models import AgentJob, AgentTemplate


# ============================================================================
# Change B: template_id populated on AgentJob when template found
# ============================================================================


@pytest.mark.asyncio
class TestSpawnPopulatesTemplateId:
    """Tests that spawn_agent_job populates template_id on AgentJob when template is found."""

    async def test_template_id_set_in_multi_terminal_mode(
        self, db_session, db_manager, test_project_multi_terminal, test_tenant_key
    ):
        """Verify template_id is set on AgentJob when template found in multi-terminal mode."""
        from src.giljo_mcp.services.orchestration_service import OrchestrationService
        from src.giljo_mcp.tenant import TenantManager

        tenant_manager = TenantManager()
        service = OrchestrationService(db_manager=db_manager, tenant_manager=tenant_manager, test_session=db_session)

        result = await service.spawn_agent_job(
            agent_display_name="analyzer",
            agent_name="analyzer-1",
            mission="Analyze the codebase",
            project_id=test_project_multi_terminal.id,
            tenant_key=test_tenant_key,
            phase=1,
        )

        # Verify template_id is set on AgentJob
        job_stmt = select(AgentJob).where(AgentJob.job_id == result.job_id)
        job_result = await db_session.execute(job_stmt)
        job = job_result.scalar_one()
        assert job.template_id is not None

        # Verify it matches the actual template
        template_stmt = select(AgentTemplate).where(
            AgentTemplate.name == "analyzer-1",
            AgentTemplate.tenant_key == test_tenant_key,
        )
        template_result = await db_session.execute(template_stmt)
        template = template_result.scalar_one()
        assert job.template_id == template.id

    async def test_template_id_none_when_no_template_found(self, db_session, db_manager, test_project, test_tenant_key):
        """Verify template_id remains None for orchestrator (no template lookup)."""
        from src.giljo_mcp.services.orchestration_service import OrchestrationService
        from src.giljo_mcp.tenant import TenantManager

        tenant_manager = TenantManager()
        service = OrchestrationService(db_manager=db_manager, tenant_manager=tenant_manager, test_session=db_session)

        result = await service.spawn_agent_job(
            agent_display_name="orchestrator",
            agent_name="orchestrator",
            mission="Orchestrate project",
            project_id=test_project.id,
            tenant_key=test_tenant_key,
        )

        job_stmt = select(AgentJob).where(AgentJob.job_id == result.job_id)
        job_result = await db_session.execute(job_stmt)
        job = job_result.scalar_one()
        # Orchestrator skips agent_name validation and template lookup
        assert job.template_id is None


# ============================================================================
# Change C: list_jobs includes phase in response
# ============================================================================


@pytest.mark.asyncio
class TestListJobsIncludesPhase:
    """Tests that list_jobs includes `phase` in each job dict."""

    async def test_list_jobs_returns_phase_value(self, db_session, db_manager, test_project, test_tenant_key):
        """Verify list_jobs response includes phase for jobs with phase set."""
        from src.giljo_mcp.services.orchestration_service import OrchestrationService
        from src.giljo_mcp.tenant import TenantManager

        tenant_manager = TenantManager()
        service = OrchestrationService(db_manager=db_manager, tenant_manager=tenant_manager, test_session=db_session)

        # Create a job with phase
        await service.spawn_agent_job(
            agent_display_name="analyzer",
            agent_name="analyzer-1",
            mission="Analyze the codebase",
            project_id=test_project.id,
            tenant_key=test_tenant_key,
            phase=1,
        )

        # List jobs
        result = await service.list_jobs(
            tenant_key=test_tenant_key,
            project_id=test_project.id,
        )

        assert len(result.jobs) >= 1
        job_dict = result.jobs[0]
        assert "phase" in job_dict
        assert job_dict["phase"] == 1

    async def test_list_jobs_returns_none_phase_when_not_set(
        self, db_session, db_manager, test_project, test_tenant_key
    ):
        """Verify list_jobs response includes phase=None for jobs without phase."""
        from src.giljo_mcp.services.orchestration_service import OrchestrationService
        from src.giljo_mcp.tenant import TenantManager

        tenant_manager = TenantManager()
        service = OrchestrationService(db_manager=db_manager, tenant_manager=tenant_manager, test_session=db_session)

        # Create a job without phase
        await service.spawn_agent_job(
            agent_display_name="impl",
            agent_name="impl-1",
            mission="Implement feature",
            project_id=test_project.id,
            tenant_key=test_tenant_key,
        )

        result = await service.list_jobs(
            tenant_key=test_tenant_key,
            project_id=test_project.id,
        )

        assert len(result.jobs) >= 1
        # Find the job we just created (may not be first due to ordering)
        impl_jobs = [j for j in result.jobs if j["agent_display_name"] == "impl"]
        assert len(impl_jobs) >= 1
        assert "phase" in impl_jobs[0]
        assert impl_jobs[0]["phase"] is None

    async def test_list_jobs_returns_multiple_phases(self, db_session, db_manager, test_project, test_tenant_key):
        """Verify list_jobs correctly returns different phases for different jobs."""
        from src.giljo_mcp.services.orchestration_service import OrchestrationService
        from src.giljo_mcp.tenant import TenantManager

        tenant_manager = TenantManager()
        service = OrchestrationService(db_manager=db_manager, tenant_manager=tenant_manager, test_session=db_session)

        # Create jobs with different phases
        await service.spawn_agent_job(
            agent_display_name="analyzer",
            agent_name="analyzer-1",
            mission="Analyze first",
            project_id=test_project.id,
            tenant_key=test_tenant_key,
            phase=1,
        )
        await service.spawn_agent_job(
            agent_display_name="implementer",
            agent_name="impl-1",
            mission="Implement second",
            project_id=test_project.id,
            tenant_key=test_tenant_key,
            phase=2,
        )
        await service.spawn_agent_job(
            agent_display_name="tester",
            agent_name="tester-1",
            mission="Test third",
            project_id=test_project.id,
            tenant_key=test_tenant_key,
            phase=3,
        )

        result = await service.list_jobs(
            tenant_key=test_tenant_key,
            project_id=test_project.id,
        )

        assert len(result.jobs) >= 3
        phases = {j["agent_display_name"]: j["phase"] for j in result.jobs}
        assert phases.get("analyzer") == 1
        assert phases.get("implementer") == 2
        assert phases.get("tester") == 3
