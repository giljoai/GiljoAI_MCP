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

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from sqlalchemy import select

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
async def test_agent_execution_0367a(
    db_session, test_agent_job_0367a, test_tenant_0367a
) -> AgentExecution:
    """Create test AgentExecution (executor)."""
    execution = AgentExecution(
        agent_id=str(uuid.uuid4()),
        job_id=test_agent_job_0367a.job_id,
        tenant_key=test_tenant_0367a,
        agent_display_name="orchestrator",
        agent_name="Orchestrator #1",
        instance_number=1,
        status="working",
        progress=50,
        messages=[],
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

    async def test_complete_job_returns_error_when_execution_not_found(
        self, db_session, db_manager, test_tenant_0367a
    ):
        """
        complete_job() should return error when AgentExecution not found.

        It should NOT fallback to MCPAgentJob table.
        """
        from src.giljo_mcp.services.orchestration_service import OrchestrationService
        from src.giljo_mcp.tenant import TenantManager

        tenant_manager = TenantManager()
        service = OrchestrationService(
            db_manager=db_manager,
            tenant_manager=tenant_manager,
            test_session=db_session
        )

        # Try to complete a non-existent job
        fake_job_id = str(uuid.uuid4())
        result = await service.complete_job(
            job_id=fake_job_id,
            result={"output": "test"},  # Required parameter
            tenant_key=test_tenant_0367a,
        )

        # Should return error, NOT fallback to MCPAgentJob
        assert result["status"] == "error"
        assert "not found" in result["error"].lower() or "no active execution" in result["error"].lower()

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
        service = OrchestrationService(
            db_manager=db_manager,
            tenant_manager=tenant_manager,
            test_session=db_session
        )

        # Complete the job
        result = await service.complete_job(
            job_id=test_agent_job_0367a.job_id,
            result={"output": "test"},  # Required parameter
            tenant_key=test_tenant_0367a,
        )

        # Verify success
        assert result["status"] == "success" or result.get("success") is True

        # Verify AgentExecution was updated
        await db_session.refresh(test_agent_execution_0367a)
        assert test_agent_execution_0367a.status in ["complete", "decommissioned"]
        assert test_agent_execution_0367a.progress == 100

    async def test_trigger_succession_returns_error_when_execution_not_found(
        self, db_session, db_manager, test_tenant_0367a
    ):
        """
        trigger_succession() should return error when AgentExecution not found.

        It should NOT fallback to MCPAgentJob table and create legacy successor.
        """
        from src.giljo_mcp.services.orchestration_service import OrchestrationService
        from src.giljo_mcp.tenant import TenantManager

        tenant_manager = TenantManager()
        service = OrchestrationService(
            db_manager=db_manager,
            tenant_manager=tenant_manager,
            test_session=db_session
        )

        # Try to trigger succession on non-existent agent
        fake_agent_id = str(uuid.uuid4())

        # Should raise ValueError or return error, NOT create MCPAgentJob
        with pytest.raises(ValueError) as exc_info:
            await service.trigger_succession(
                job_id=fake_agent_id,  # job_id is the first param (treated as agent_id if agent_id not provided)
                reason="context_limit",
                tenant_key=test_tenant_0367a,
            )

        assert "not found" in str(exc_info.value).lower()

    async def test_trigger_succession_creates_agent_execution_not_mcp_agent_job(
        self, db_session, db_manager, test_agent_execution_0367a, test_agent_job_0367a, test_tenant_0367a
    ):
        """
        trigger_succession() should create new AgentExecution, not MCPAgentJob.

        Expected:
        - Creates new AgentExecution with same job_id
        - Increments instance_number
        - Links via spawned_by (predecessor's agent_id)
        - Does NOT create MCPAgentJob record
        """
        from src.giljo_mcp.services.orchestration_service import OrchestrationService
        from src.giljo_mcp.tenant import TenantManager

        tenant_manager = TenantManager()
        service = OrchestrationService(
            db_manager=db_manager,
            tenant_manager=tenant_manager,
            test_session=db_session
        )

        # Trigger succession
        result = await service.trigger_succession(
            job_id=test_agent_execution_0367a.agent_id,  # job_id used as agent_id for backwards compat
            reason="context_limit",
            tenant_key=test_tenant_0367a,
        )

        # Verify success
        assert result["success"] is True
        assert "successor_agent_id" in result

        # Verify successor is an AgentExecution (same job_id, different agent_id)
        successor_stmt = select(AgentExecution).where(
            AgentExecution.agent_id == result["successor_agent_id"]
        )
        successor_result = await db_session.execute(successor_stmt)
        successor = successor_result.scalar_one_or_none()

        assert successor is not None
        assert successor.job_id == test_agent_job_0367a.job_id  # Same job
        assert successor.agent_id != test_agent_execution_0367a.agent_id  # Different executor
        assert successor.instance_number == 2  # Incremented
        assert successor.spawned_by == test_agent_execution_0367a.agent_id  # Linked to predecessor


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
        import importlib.util
        import ast
        from pathlib import Path

        file_path = Path("src/giljo_mcp/services/orchestration_service.py")

        if not file_path.exists():
            pytest.skip("File not found - likely in different working directory")

        with open(file_path, "r", encoding="utf-8") as f:
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

    def test_agent_job_manager_no_mcpagentjob_import(self):
        """
        AgentJobManager should not import MCPAgentJob.
        """
        import importlib.util
        import ast
        from pathlib import Path

        file_path = Path("src/giljo_mcp/agent_job_manager.py")

        if not file_path.exists():
            pytest.skip("File not found - likely in different working directory")

        with open(file_path, "r", encoding="utf-8") as f:
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
        assert len(mcp_agent_job_imports) == 0, (
            f"AgentJobManager still imports MCPAgentJob: {mcp_agent_job_imports}"
        )

    def test_project_service_no_mcpagentjob_import(self):
        """
        ProjectService should not import MCPAgentJob.
        """
        import ast
        from pathlib import Path

        file_path = Path("src/giljo_mcp/services/project_service.py")

        if not file_path.exists():
            pytest.skip("File not found - likely in different working directory")

        with open(file_path, "r", encoding="utf-8") as f:
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
        assert len(mcp_agent_job_imports) == 0, (
            f"ProjectService still imports MCPAgentJob: {mcp_agent_job_imports}"
        )

    def test_message_service_no_mcpagentjob_import(self):
        """
        MessageService should not import MCPAgentJob.
        """
        import ast
        from pathlib import Path

        file_path = Path("src/giljo_mcp/services/message_service.py")

        if not file_path.exists():
            pytest.skip("File not found - likely in different working directory")

        with open(file_path, "r", encoding="utf-8") as f:
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
        assert len(mcp_agent_job_imports) == 0, (
            f"MessageService still imports MCPAgentJob: {mcp_agent_job_imports}"
        )

    def test_agent_message_queue_no_mcpagentjob_import(self):
        """
        AgentMessageQueue should not import MCPAgentJob.
        """
        import ast
        from pathlib import Path

        file_path = Path("src/giljo_mcp/agent_message_queue.py")

        if not file_path.exists():
            pytest.skip("File not found - likely in different working directory")

        with open(file_path, "r", encoding="utf-8") as f:
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
        assert len(mcp_agent_job_imports) == 0, (
            f"AgentMessageQueue still imports MCPAgentJob: {mcp_agent_job_imports}"
        )

    def test_job_monitoring_no_mcpagentjob_import(self):
        """
        JobMonitoring should not import MCPAgentJob.
        """
        import ast
        from pathlib import Path

        file_path = Path("src/giljo_mcp/job_monitoring.py")

        if not file_path.exists():
            pytest.skip("File not found - likely in different working directory")

        with open(file_path, "r", encoding="utf-8") as f:
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
        assert len(mcp_agent_job_imports) == 0, (
            f"JobMonitoring still imports MCPAgentJob: {mcp_agent_job_imports}"
        )
