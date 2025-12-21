"""
TDD Tests for MCPAgentJob Removal from API Endpoints (Handover 0367b).

RED PHASE - These tests define the BEHAVIOR we want after removing
all MCPAgentJob references from the API endpoint layer.

Design Philosophy:
- API endpoints must ONLY query AgentJob + AgentExecution
- Zero MCPAgentJob imports in api/endpoints/ production code
- Zero fallback/bridge code to MCPAgentJob
- Response DTOs use agent_id (UUID str), not job_id (int)

Test Categories:
1. Static Import Tests: Verify no MCPAgentJob imports in endpoint files
2. Behavior Tests: Verify endpoints work with AgentJob + AgentExecution

Files Covered:
- api/endpoints/prompts.py (28 refs)
- api/endpoints/statistics.py (21 refs)
- api/endpoints/agent_jobs/filters.py (13 refs)
- api/endpoints/agent_jobs/table_view.py (12 refs)
- api/endpoints/agent_jobs/succession.py (11 refs)
- api/endpoints/agent_jobs/operations.py (10 refs)
- api/endpoints/projects/status.py (8 refs)
"""

import ast
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy import func, select

from src.giljo_mcp.models.agent_identity import AgentExecution, AgentJob
from src.giljo_mcp.models.projects import Project


# ============================================================================
# Test Fixtures (0367b-specific)
# ============================================================================


@pytest_asyncio.fixture
async def test_tenant_0367b() -> str:
    """Generate unique tenant key for test isolation."""
    return f"tk_0367b_{uuid.uuid4().hex[:12]}"


@pytest_asyncio.fixture
async def test_project_0367b(db_session, test_tenant_0367b) -> Project:
    """Create test project for 0367b tests."""
    project = Project(
        id=str(uuid.uuid4()),
        name="0367b API Endpoint Migration Test",
        description="Test project for API endpoint MCPAgentJob removal",
        mission="Test API endpoints use AgentJob + AgentExecution",
        status="active",
        tenant_key=test_tenant_0367b,
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    return project


@pytest_asyncio.fixture
async def test_agent_job_0367b(db_session, test_project_0367b, test_tenant_0367b) -> AgentJob:
    """Create test AgentJob (work order)."""
    job = AgentJob(
        job_id=str(uuid.uuid4()),
        tenant_key=test_tenant_0367b,
        project_id=test_project_0367b.id,
        mission="Test mission for 0367b API endpoints",
        job_type="orchestrator",
        status="active",
    )
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)
    return job


@pytest_asyncio.fixture
async def test_agent_execution_0367b(
    db_session, test_agent_job_0367b, test_tenant_0367b
) -> AgentExecution:
    """Create test AgentExecution (executor)."""
    execution = AgentExecution(
        agent_id=str(uuid.uuid4()),
        job_id=test_agent_job_0367b.job_id,
        tenant_key=test_tenant_0367b,
        agent_type="orchestrator",
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
# Static Import Tests: Verify No MCPAgentJob Imports
# ============================================================================


class TestNoMCPAgentJobImportInAPIEndpoints:
    """
    Verify that MCPAgentJob is NOT imported in API endpoint files.

    This is a static code analysis test - checking imports.
    After 0367b migration, these tests should all PASS.
    """

    def _check_file_for_mcpagentjob_imports(self, file_path: Path) -> list[str]:
        """
        Parse a Python file and return list of MCPAgentJob imports found.

        Returns empty list if no MCPAgentJob imports found (PASS condition).
        """
        if not file_path.exists():
            pytest.skip(f"File not found: {file_path}")

        with open(file_path, "r", encoding="utf-8") as f:
            source = f.read()

        tree = ast.parse(source)
        mcp_agent_job_imports = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.names:
                    for alias in node.names:
                        if alias.name == "MCPAgentJob":
                            mcp_agent_job_imports.append(
                                f"from {node.module} import MCPAgentJob (line {node.lineno})"
                            )
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if "MCPAgentJob" in alias.name:
                        mcp_agent_job_imports.append(
                            f"import {alias.name} (line {node.lineno})"
                        )

        return mcp_agent_job_imports

    def test_prompts_py_no_mcpagentjob_import(self):
        """
        api/endpoints/prompts.py should not import MCPAgentJob.

        This file has 28 MCPAgentJob references that must be migrated.
        """
        file_path = Path("api/endpoints/prompts.py")
        imports = self._check_file_for_mcpagentjob_imports(file_path)

        assert len(imports) == 0, (
            f"prompts.py still imports MCPAgentJob:\n" + "\n".join(imports)
        )

    def test_statistics_py_no_mcpagentjob_import(self):
        """
        api/endpoints/statistics.py should not import MCPAgentJob.

        This file has 21 MCPAgentJob references that must be migrated.
        """
        file_path = Path("api/endpoints/statistics.py")
        imports = self._check_file_for_mcpagentjob_imports(file_path)

        assert len(imports) == 0, (
            f"statistics.py still imports MCPAgentJob:\n" + "\n".join(imports)
        )

    def test_filters_py_no_mcpagentjob_import(self):
        """
        api/endpoints/agent_jobs/filters.py should not import MCPAgentJob.

        This file has 13 MCPAgentJob references that must be migrated.
        """
        file_path = Path("api/endpoints/agent_jobs/filters.py")
        imports = self._check_file_for_mcpagentjob_imports(file_path)

        assert len(imports) == 0, (
            f"filters.py still imports MCPAgentJob:\n" + "\n".join(imports)
        )

    def test_table_view_py_no_mcpagentjob_import(self):
        """
        api/endpoints/agent_jobs/table_view.py should not import MCPAgentJob.

        This file has 12 MCPAgentJob references that must be migrated.
        """
        file_path = Path("api/endpoints/agent_jobs/table_view.py")
        imports = self._check_file_for_mcpagentjob_imports(file_path)

        assert len(imports) == 0, (
            f"table_view.py still imports MCPAgentJob:\n" + "\n".join(imports)
        )

    def test_succession_py_no_mcpagentjob_import(self):
        """
        api/endpoints/agent_jobs/succession.py should not import MCPAgentJob.

        This file has 11 MCPAgentJob references that must be migrated.
        """
        file_path = Path("api/endpoints/agent_jobs/succession.py")
        imports = self._check_file_for_mcpagentjob_imports(file_path)

        assert len(imports) == 0, (
            f"succession.py still imports MCPAgentJob:\n" + "\n".join(imports)
        )

    def test_operations_py_no_mcpagentjob_import(self):
        """
        api/endpoints/agent_jobs/operations.py should not import MCPAgentJob.

        This file has 10 MCPAgentJob references that must be migrated.
        """
        file_path = Path("api/endpoints/agent_jobs/operations.py")
        imports = self._check_file_for_mcpagentjob_imports(file_path)

        assert len(imports) == 0, (
            f"operations.py still imports MCPAgentJob:\n" + "\n".join(imports)
        )

    def test_projects_status_py_no_mcpagentjob_import(self):
        """
        api/endpoints/projects/status.py should not import MCPAgentJob.

        This file has 8 MCPAgentJob references that must be migrated.
        """
        file_path = Path("api/endpoints/projects/status.py")
        imports = self._check_file_for_mcpagentjob_imports(file_path)

        assert len(imports) == 0, (
            f"projects/status.py still imports MCPAgentJob:\n" + "\n".join(imports)
        )


# ============================================================================
# Static Reference Tests: Verify No MCPAgentJob Usage in Query Logic
# ============================================================================


class TestNoMCPAgentJobUsageInAPIEndpoints:
    """
    Verify that MCPAgentJob is not used in query logic (select, where clauses).

    This catches cases where MCPAgentJob is used without import (e.g., via alias).
    """

    def _check_file_for_mcpagentjob_usage(self, file_path: Path) -> list[str]:
        """
        Check source code for MCPAgentJob usage patterns.

        Returns list of lines containing MCPAgentJob usage.
        """
        if not file_path.exists():
            pytest.skip(f"File not found: {file_path}")

        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        usages = []
        for i, line in enumerate(lines, 1):
            # Check for various MCPAgentJob usage patterns
            if "MCPAgentJob" in line:
                # Skip import statements (covered by import tests)
                if "import" in line.lower():
                    continue
                # Skip comments
                if line.strip().startswith("#"):
                    continue
                usages.append(f"Line {i}: {line.strip()}")

        return usages

    def test_prompts_py_no_mcpagentjob_usage(self):
        """prompts.py should not use MCPAgentJob in queries."""
        file_path = Path("api/endpoints/prompts.py")
        usages = self._check_file_for_mcpagentjob_usage(file_path)

        assert len(usages) == 0, (
            f"prompts.py still uses MCPAgentJob:\n" + "\n".join(usages)
        )

    def test_statistics_py_no_mcpagentjob_usage(self):
        """statistics.py should not use MCPAgentJob in queries."""
        file_path = Path("api/endpoints/statistics.py")
        usages = self._check_file_for_mcpagentjob_usage(file_path)

        assert len(usages) == 0, (
            f"statistics.py still uses MCPAgentJob:\n" + "\n".join(usages)
        )

    def test_filters_py_no_mcpagentjob_usage(self):
        """filters.py should not use MCPAgentJob in queries."""
        file_path = Path("api/endpoints/agent_jobs/filters.py")
        usages = self._check_file_for_mcpagentjob_usage(file_path)

        assert len(usages) == 0, (
            f"filters.py still uses MCPAgentJob:\n" + "\n".join(usages)
        )

    def test_table_view_py_no_mcpagentjob_usage(self):
        """table_view.py should not use MCPAgentJob in queries."""
        file_path = Path("api/endpoints/agent_jobs/table_view.py")
        usages = self._check_file_for_mcpagentjob_usage(file_path)

        assert len(usages) == 0, (
            f"table_view.py still uses MCPAgentJob:\n" + "\n".join(usages)
        )

    def test_succession_py_no_mcpagentjob_usage(self):
        """succession.py should not use MCPAgentJob in queries."""
        file_path = Path("api/endpoints/agent_jobs/succession.py")
        usages = self._check_file_for_mcpagentjob_usage(file_path)

        assert len(usages) == 0, (
            f"succession.py still uses MCPAgentJob:\n" + "\n".join(usages)
        )

    def test_operations_py_no_mcpagentjob_usage(self):
        """operations.py should not use MCPAgentJob in queries."""
        file_path = Path("api/endpoints/agent_jobs/operations.py")
        usages = self._check_file_for_mcpagentjob_usage(file_path)

        assert len(usages) == 0, (
            f"operations.py still uses MCPAgentJob:\n" + "\n".join(usages)
        )

    def test_projects_status_py_no_mcpagentjob_usage(self):
        """projects/status.py should not use MCPAgentJob in queries."""
        file_path = Path("api/endpoints/projects/status.py")
        usages = self._check_file_for_mcpagentjob_usage(file_path)

        assert len(usages) == 0, (
            f"projects/status.py still uses MCPAgentJob:\n" + "\n".join(usages)
        )


# ============================================================================
# Behavioral Tests: Statistics Endpoint Migration
# ============================================================================


class TestStatisticsEndpointBehavior:
    """
    Verify statistics.py endpoints work correctly with AgentExecution.

    Key Changes:
    - Count agents by querying AgentExecution (not MCPAgentJob)
    - Status mapping: "complete" (not "completed"), "working" (not "running")
    - Use agent_id field (not job_id) for agent counts
    - Filter by tenant_key on AgentExecution table
    """

    @pytest.mark.asyncio
    async def test_system_stats_counts_agent_executions(
        self, db_session, test_project_0367b, test_agent_execution_0367b, test_tenant_0367b
    ):
        """
        System stats endpoint should count AgentExecution records.

        Verifies:
        - total_agents counts AgentExecution.agent_id
        - active_agents counts status in ['waiting', 'working']
        - total_agents_spawned counts all AgentExecution records
        - total_jobs_completed counts status='complete'
        """
        # Create additional test data
        execution2 = AgentExecution(
            agent_id=str(uuid.uuid4()),
            job_id=test_agent_execution_0367b.job_id,
            tenant_key=test_tenant_0367b,
            agent_type="implementor",
            agent_name="Implementor #1",
            instance_number=1,
            status="complete",
            progress=100,
            messages=[],
        )
        db_session.add(execution2)

        execution3 = AgentExecution(
            agent_id=str(uuid.uuid4()),
            job_id=test_agent_execution_0367b.job_id,
            tenant_key=test_tenant_0367b,
            agent_type="tester",
            agent_name="Tester #1",
            instance_number=1,
            status="waiting",
            progress=0,
            messages=[],
        )
        db_session.add(execution3)
        await db_session.commit()

        # Verify counts via direct query (simulating endpoint logic)
        total_agents = await db_session.scalar(
            select(func.count(AgentExecution.agent_id)).where(
                AgentExecution.tenant_key == test_tenant_0367b
            )
        )

        active_agents = await db_session.scalar(
            select(func.count(AgentExecution.agent_id)).where(
                AgentExecution.tenant_key == test_tenant_0367b,
                AgentExecution.status.in_(["waiting", "working"])
            )
        )

        completed_agents = await db_session.scalar(
            select(func.count(AgentExecution.agent_id)).where(
                AgentExecution.tenant_key == test_tenant_0367b,
                AgentExecution.status == "complete"
            )
        )

        assert total_agents == 3, "Should count all 3 agent executions"
        assert active_agents == 2, "Should count 2 active agents (waiting + working)"
        assert completed_agents == 1, "Should count 1 completed agent"

    @pytest.mark.asyncio
    async def test_project_stats_counts_agent_executions_per_project(
        self, db_session, test_project_0367b, test_agent_job_0367b, test_tenant_0367b
    ):
        """
        Project stats endpoint should count AgentExecution per project.

        Verifies:
        - Agent count filters by AgentJob.project_id via join
        - Multi-tenant isolation (filters by tenant_key)
        - Correct agent_count per project
        """
        # Create executions for the test project
        execution1 = AgentExecution(
            agent_id=str(uuid.uuid4()),
            job_id=test_agent_job_0367b.job_id,
            tenant_key=test_tenant_0367b,
            agent_type="orchestrator",
            agent_name="Orchestrator #1",
            instance_number=1,
            status="working",
            progress=50,
            messages=[],
        )
        db_session.add(execution1)

        execution2 = AgentExecution(
            agent_id=str(uuid.uuid4()),
            job_id=test_agent_job_0367b.job_id,
            tenant_key=test_tenant_0367b,
            agent_type="architect",
            agent_name="Architect #1",
            instance_number=1,
            status="complete",
            progress=100,
            messages=[],
        )
        db_session.add(execution2)
        await db_session.commit()

        # Simulate project stats query logic
        # Must join AgentExecution -> AgentJob to filter by project_id
        agent_count = await db_session.scalar(
            select(func.count(AgentExecution.agent_id))
            .join(AgentJob, AgentExecution.job_id == AgentJob.job_id)
            .where(
                AgentJob.project_id == test_project_0367b.id,
                AgentJob.tenant_key == test_tenant_0367b,
                AgentExecution.tenant_key == test_tenant_0367b
            )
        )

        assert agent_count == 2, "Should count 2 agent executions for this project"

    @pytest.mark.asyncio
    async def test_agent_stats_queries_agent_execution_not_mcpagentjob(
        self, db_session, test_agent_job_0367b, test_tenant_0367b
    ):
        """
        Agent stats endpoint should query AgentExecution table.

        Verifies:
        - Queries AgentExecution (not MCPAgentJob)
        - Returns agent_id as primary identifier
        - Maps agent_type and agent_name from AgentExecution
        - Status filtering works with AgentExecution statuses
        """
        # Create test executions
        execution1 = AgentExecution(
            agent_id=str(uuid.uuid4()),
            job_id=test_agent_job_0367b.job_id,
            tenant_key=test_tenant_0367b,
            agent_type="orchestrator",
            agent_name="Orchestrator #1",
            instance_number=1,
            status="working",
            progress=50,
            messages=[],
        )
        db_session.add(execution1)

        execution2 = AgentExecution(
            agent_id=str(uuid.uuid4()),
            job_id=test_agent_job_0367b.job_id,
            tenant_key=test_tenant_0367b,
            agent_type="implementor",
            agent_name="Implementor #1",
            instance_number=1,
            status="waiting",
            progress=0,
            messages=[],
        )
        db_session.add(execution2)
        await db_session.commit()

        # Simulate agent stats query (filter by status)
        working_agents = await db_session.execute(
            select(AgentExecution).where(
                AgentExecution.tenant_key == test_tenant_0367b,
                AgentExecution.status == "working"
            )
        )
        working_list = working_agents.scalars().all()

        waiting_agents = await db_session.execute(
            select(AgentExecution).where(
                AgentExecution.tenant_key == test_tenant_0367b,
                AgentExecution.status == "waiting"
            )
        )
        waiting_list = waiting_agents.scalars().all()

        assert len(working_list) == 1, "Should find 1 working agent"
        assert len(waiting_list) == 1, "Should find 1 waiting agent"
        assert working_list[0].agent_type == "orchestrator"
        assert waiting_list[0].agent_type == "implementor"

    @pytest.mark.asyncio
    async def test_agent_stats_status_filter_mapping(
        self, db_session, test_agent_job_0367b, test_tenant_0367b
    ):
        """
        Agent stats status filter should map to AgentExecution statuses.

        Status Mapping:
        - "active" -> status in ['waiting', 'working']
        - "idle" -> status == 'waiting'
        - "working" -> status == 'working'
        - "decommissioned" -> status == 'decommissioned'

        Verifies endpoint handles legacy status names correctly.
        """
        # Create test executions with various statuses
        statuses = ["waiting", "working", "complete", "decommissioned"]
        for status in statuses:
            execution = AgentExecution(
                agent_id=str(uuid.uuid4()),
                job_id=test_agent_job_0367b.job_id,
                tenant_key=test_tenant_0367b,
                agent_type="test-agent",
                agent_name=f"Agent {status}",
                instance_number=1,
                status=status,
                progress=0,
                messages=[],
            )
            db_session.add(execution)
        await db_session.commit()

        # Test "active" filter (waiting + working)
        active_count = await db_session.scalar(
            select(func.count(AgentExecution.agent_id)).where(
                AgentExecution.tenant_key == test_tenant_0367b,
                AgentExecution.status.in_(["waiting", "working"])
            )
        )
        assert active_count == 2, "Active should count waiting + working"

        # Test "idle" filter (waiting only)
        idle_count = await db_session.scalar(
            select(func.count(AgentExecution.agent_id)).where(
                AgentExecution.tenant_key == test_tenant_0367b,
                AgentExecution.status == "waiting"
            )
        )
        assert idle_count == 1, "Idle should count waiting only"

        # Test "working" filter
        working_count = await db_session.scalar(
            select(func.count(AgentExecution.agent_id)).where(
                AgentExecution.tenant_key == test_tenant_0367b,
                AgentExecution.status == "working"
            )
        )
        assert working_count == 1, "Working should count working only"

        # Test "decommissioned" filter
        decom_count = await db_session.scalar(
            select(func.count(AgentExecution.agent_id)).where(
                AgentExecution.tenant_key == test_tenant_0367b,
                AgentExecution.status == "decommissioned"
            )
        )
        assert decom_count == 1, "Should count decommissioned agents"
