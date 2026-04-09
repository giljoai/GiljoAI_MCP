# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
TDD Tests for MCPAgentJob Removal (Handover 0367a).

RED PHASE - These tests define the BEHAVIOR we want after removing
all MCPAgentJob references from the service layer.

Design Philosophy:
- Service layer must ONLY use AgentJob + AgentExecution
- Zero MCPAgentJob imports in production code
- Zero fallback/bridge code to MCPAgentJob
- If AgentExecution not found, return error (don't fallback to MCPAgentJob)

Test Categories:
1. OrchestrationService: No MCPAgentJob fallback
2. AgentJobManager: No Job alias (directly use AgentJob/AgentExecution)
3. ProjectService: No dual-query patterns
4. MessageService: No MCPAgentJob job lookups
"""

import random
import uuid

import pytest
import pytest_asyncio

from src.giljo_mcp.models.agent_identity import AgentExecution, AgentJob
from src.giljo_mcp.models.projects import Project

# ============================================================================
# Test Fixtures
# ============================================================================


@pytest_asyncio.fixture
async def test_tenant_0367a() -> str:
    """Generate unique tenant key for test isolation."""
    return f"tk_0367a_{uuid.uuid4().hex[:12]}"


@pytest_asyncio.fixture
async def test_project_0367a(db_session, test_tenant_0367a) -> Project:
    """Create test project for 0367a tests."""
    project = Project(
        id=str(uuid.uuid4()),
        name="0367a MCPAgentJob Removal Test",
        description="Test project for MCPAgentJob removal migration",
        mission="Test the removal of MCPAgentJob from service layer",
        status="active",
        tenant_key=test_tenant_0367a,
        series_number=random.randint(1, 999999),
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    return project


@pytest_asyncio.fixture
async def test_agent_job_0367a(db_session, test_project_0367a, test_tenant_0367a) -> AgentJob:
    """Create test AgentJob (work order)."""
    job = AgentJob(
        job_id=str(uuid.uuid4()),
        tenant_key=test_tenant_0367a,
        project_id=test_project_0367a.id,
        mission="Test mission for 0367a",
        job_type="orchestrator",
        status="active",
    )
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)
    return job


@pytest_asyncio.fixture
async def test_agent_execution_0367a(db_session, test_agent_job_0367a, test_tenant_0367a) -> AgentExecution:
    """Create test AgentExecution (executor)."""
    execution = AgentExecution(
        agent_id=str(uuid.uuid4()),
        job_id=test_agent_job_0367a.job_id,
        tenant_key=test_tenant_0367a,
        agent_display_name="orchestrator",
        agent_name="Orchestrator #1",
        status="working",
        progress=50,
        messages_sent_count=0,
        messages_waiting_count=0,
        messages_read_count=0,
    )
    db_session.add(execution)
    await db_session.commit()
    await db_session.refresh(execution)
    return execution


# ============================================================================
# Test: OrchestrationService - No MCPAgentJob Fallback in complete_job
# ============================================================================


@pytest.mark.asyncio
class TestOrchestrationServiceNoFallback:
    """
    Verify OrchestrationService does NOT fallback to MCPAgentJob.

    Expected Behavior:
    - complete_job() returns error if AgentExecution not found
    - complete_job() does NOT query MCPAgentJob table
    - trigger_succession() returns error if AgentExecution not found
    - trigger_succession() does NOT create MCPAgentJob successor
    """

    async def test_complete_job_returns_error_when_execution_not_found(self, db_session, db_manager, test_tenant_0367a):
        """
        complete_job() should raise exception when AgentExecution not found.

        It should NOT fallback to MCPAgentJob table.
        """
        from src.giljo_mcp.exceptions import ResourceNotFoundError
        from src.giljo_mcp.services.orchestration_service import OrchestrationService
        from src.giljo_mcp.tenant import TenantManager

        tenant_manager = TenantManager()
        service = OrchestrationService(db_manager=db_manager, tenant_manager=tenant_manager, test_session=db_session)

        # Try to complete a non-existent job - should raise exception
        fake_job_id = str(uuid.uuid4())
        with pytest.raises(ResourceNotFoundError) as exc_info:
            await service.complete_job(
                job_id=fake_job_id,
                result={"output": "test"},  # Required parameter
                tenant_key=test_tenant_0367a,
            )

        # Verify exception message contains expected text
        assert "not found" in str(exc_info.value).lower() or "no active execution" in str(exc_info.value).lower()

    async def test_complete_job_uses_only_agent_execution(
        self, db_session, db_manager, test_agent_execution_0367a, test_agent_job_0367a, test_tenant_0367a
    ):
        """
        complete_job() should update AgentExecution and AgentJob status.

        It should NOT touch MCPAgentJob table.
        """
        from src.giljo_mcp.services.orchestration_service import OrchestrationService
        from src.giljo_mcp.tenant import TenantManager

        tenant_manager = TenantManager()
        service = OrchestrationService(db_manager=db_manager, tenant_manager=tenant_manager, test_session=db_session)

        # Complete the job
        result = await service.complete_job(
            job_id=test_agent_job_0367a.job_id,
            result={"output": "test"},  # Required parameter
            tenant_key=test_tenant_0367a,
        )

        # Verify success - typed return (CompleteJobResult)
        assert result.status == "success"

        # Verify AgentExecution was updated
        await db_session.refresh(test_agent_execution_0367a)
        assert test_agent_execution_0367a.status in ["complete", "decommissioned"]
        assert test_agent_execution_0367a.progress == 100

    # HANDOVER 0422: Removed trigger_succession tests
    # - test_trigger_succession_returns_error_when_execution_not_found
    # - test_trigger_succession_creates_agent_execution_not_mcp_agent_job
    # trigger_succession() was removed (dead token budget cleanup)


# ============================================================================
# Test: AgentJobManager - No Job Alias
# ============================================================================


# AgentJobManager tests moved to future handover (0367a focuses on service imports first)
# The current AgentJobManager uses synchronous methods and needs a larger refactor


# ============================================================================
# Test: No MCPAgentJob Import in Service Layer
# ============================================================================


class TestNoMCPAgentJobImport:
    """
    Verify that MCPAgentJob is NOT imported in service layer files.

    This is a static code analysis test - checking imports.
    """

    def test_orchestration_service_no_mcpagentjob_import(self):
        """
        OrchestrationService should not import MCPAgentJob.
        """
        import ast
        from pathlib import Path

        repo_root = Path(__file__).resolve().parent.parent.parent
        file_path = repo_root / "src" / "giljo_mcp" / "services" / "orchestration_service.py"
        assert file_path.exists(), f"Expected source file not found: {file_path}"

        with open(file_path, encoding="utf-8") as f:
            source = f.read()

        # Parse the source code
        tree = ast.parse(source)

        # Check all imports
        mcp_agent_job_imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.names:
                    for alias in node.names:
                        if alias.name == "MCPAgentJob":
                            mcp_agent_job_imports.append(f"from {node.module} import MCPAgentJob")
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if "MCPAgentJob" in alias.name:
                        mcp_agent_job_imports.append(f"import {alias.name}")

        # Should have no MCPAgentJob imports
        assert len(mcp_agent_job_imports) == 0, (
            f"OrchestrationService still imports MCPAgentJob: {mcp_agent_job_imports}"
        )

    def test_project_service_no_mcpagentjob_import(self):
        """
        ProjectService should not import MCPAgentJob.
        """
        import ast
        from pathlib import Path

        repo_root = Path(__file__).resolve().parent.parent.parent
        file_path = repo_root / "src" / "giljo_mcp" / "services" / "project_service.py"
        assert file_path.exists(), f"Expected source file not found: {file_path}"

        with open(file_path, encoding="utf-8") as f:
            source = f.read()

        # Parse the source code
        tree = ast.parse(source)

        # Check all imports
        mcp_agent_job_imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.names:
                    for alias in node.names:
                        if alias.name == "MCPAgentJob":
                            mcp_agent_job_imports.append(f"from {node.module} import MCPAgentJob")

        # Should have no MCPAgentJob imports
        assert len(mcp_agent_job_imports) == 0, f"ProjectService still imports MCPAgentJob: {mcp_agent_job_imports}"

    def test_message_service_no_mcpagentjob_import(self):
        """
        MessageService should not import MCPAgentJob.
        """
        import ast
        from pathlib import Path

        repo_root = Path(__file__).resolve().parent.parent.parent
        file_path = repo_root / "src" / "giljo_mcp" / "services" / "message_service.py"
        assert file_path.exists(), f"Expected source file not found: {file_path}"

        with open(file_path, encoding="utf-8") as f:
            source = f.read()

        # Parse the source code
        tree = ast.parse(source)

        # Check all imports
        mcp_agent_job_imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.names:
                    for alias in node.names:
                        if alias.name == "MCPAgentJob":
                            mcp_agent_job_imports.append(f"from {node.module} import MCPAgentJob")

        # Should have no MCPAgentJob imports
        assert len(mcp_agent_job_imports) == 0, f"MessageService still imports MCPAgentJob: {mcp_agent_job_imports}"
