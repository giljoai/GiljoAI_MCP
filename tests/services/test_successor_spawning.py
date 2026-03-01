"""
Successor Spawning Tests - Handover 0497e

Validates:
1. spawn_agent_job with predecessor_job_id injects predecessor context into mission
2. Predecessor context includes completion summary and commits (with truncation)
3. predecessor_job_id validated: must exist, same project, same tenant
4. Invalid predecessor_job_id raises appropriate errors
5. get_agent_result MCP tool returns stored result with tenant isolation
6. Spawn without predecessor_job_id preserves existing behavior (regression)
"""

import random
import uuid

import pytest
import pytest_asyncio
from sqlalchemy import select

from src.giljo_mcp.models import AgentExecution, AgentJob, AgentTemplate, Project
from src.giljo_mcp.services.orchestration_service import OrchestrationService
from src.giljo_mcp.tenant import TenantManager


# ============================================================================
# Fixtures
# ============================================================================


@pytest_asyncio.fixture
async def tenant_key() -> str:
    """Generate a valid tenant key for test isolation."""
    return TenantManager.generate_tenant_key()


@pytest_asyncio.fixture
async def other_tenant_key() -> str:
    """Generate a second tenant key for cross-tenant tests."""
    return TenantManager.generate_tenant_key()


@pytest_asyncio.fixture
async def agent_templates(db_session, tenant_key):
    """Create agent templates needed by spawn_agent_job validation."""
    for name in ["specialist-1", "tdd-implementor", "orchestrator"]:
        template = AgentTemplate(
            tenant_key=tenant_key,
            name=name,
            role=name,
            description=f"Test template for {name}",
            system_instructions=f"# {name}\nTest agent.",
            is_active=True,
        )
        db_session.add(template)
    await db_session.commit()


@pytest_asyncio.fixture
async def other_tenant_templates(db_session, other_tenant_key):
    """Create templates for the other tenant."""
    for name in ["specialist-1"]:
        template = AgentTemplate(
            tenant_key=other_tenant_key,
            name=name,
            role=name,
            description=f"Other tenant template for {name}",
            system_instructions=f"# {name}\nOther tenant agent.",
            is_active=True,
        )
        db_session.add(template)
    await db_session.commit()


@pytest_asyncio.fixture
async def project(db_session, tenant_key, agent_templates) -> Project:
    """Create a test project."""
    from datetime import datetime, timezone

    proj = Project(
        id=str(uuid.uuid4()),
        name="Successor Test Project",
        description="Test project for 0497e successor spawning",
        mission="Test recovery flow",
        status="active",
        tenant_key=tenant_key,
        implementation_launched_at=datetime.now(timezone.utc),
        series_number=random.randint(1, 999999),
    )
    db_session.add(proj)
    await db_session.commit()
    await db_session.refresh(proj)
    return proj


@pytest_asyncio.fixture
async def other_project(db_session, other_tenant_key, other_tenant_templates) -> Project:
    """Create a project in a different tenant."""
    from datetime import datetime, timezone

    proj = Project(
        id=str(uuid.uuid4()),
        name="Other Tenant Project",
        description="Project in a different tenant",
        mission="Other tenant work",
        status="active",
        tenant_key=other_tenant_key,
        implementation_launched_at=datetime.now(timezone.utc),
        series_number=random.randint(1, 999999),
    )
    db_session.add(proj)
    await db_session.commit()
    await db_session.refresh(proj)
    return proj


@pytest_asyncio.fixture
async def service(db_session, db_manager) -> OrchestrationService:
    """Create OrchestrationService with shared test session."""
    tm = TenantManager()
    return OrchestrationService(
        db_manager=db_manager,
        tenant_manager=tm,
        test_session=db_session,
    )


async def _spawn_and_complete(service, project_id, tenant_key, result_payload, agent_name="specialist-1"):
    """Helper: spawn an agent, complete it with a result, return spawn result."""
    spawn = await service.spawn_agent_job(
        agent_display_name="predecessor",
        agent_name=agent_name,
        mission="Do predecessor work",
        project_id=project_id,
        tenant_key=tenant_key,
    )
    await service.complete_job(
        job_id=spawn.job_id,
        result=result_payload,
        tenant_key=tenant_key,
    )
    return spawn


# ============================================================================
# Test 1: Spawn with predecessor injects context into mission
# ============================================================================


@pytest.mark.asyncio
class TestSpawnWithPredecessor:
    """Verify that spawning with predecessor_job_id injects predecessor context."""

    async def test_mission_contains_predecessor_context(
        self, db_session, service, project, tenant_key
    ):
        """Successor mission should contain PREDECESSOR CONTEXT section."""
        predecessor_result = {
            "summary": "Implemented auth module with JWT tokens",
            "artifacts": ["src/auth.py", "tests/test_auth.py"],
            "commits": ["abc123 feat: add auth module"],
        }
        pred_spawn = await _spawn_and_complete(
            service, project.id, tenant_key, predecessor_result
        )

        # Spawn successor with predecessor reference
        successor = await service.spawn_agent_job(
            agent_display_name="successor",
            agent_name="tdd-implementor",
            mission="Fix the JWT validation bug found by tester",
            project_id=project.id,
            tenant_key=tenant_key,
            predecessor_job_id=pred_spawn.job_id,
        )

        # Read the stored mission from DB
        stmt = select(AgentJob).where(AgentJob.job_id == successor.job_id)
        res = await db_session.execute(stmt)
        job = res.scalar_one()

        assert "## PREDECESSOR CONTEXT" in job.mission
        assert pred_spawn.job_id in job.mission
        assert "Implemented auth module with JWT tokens" in job.mission
        assert "abc123 feat: add auth module" in job.mission
        assert "Fix the JWT validation bug found by tester" in job.mission
        assert "get_agent_result" in job.mission

    async def test_predecessor_job_id_in_spawn_result(
        self, service, project, tenant_key
    ):
        """SpawnResult should include the predecessor_job_id."""
        pred_spawn = await _spawn_and_complete(
            service, project.id, tenant_key, {"summary": "Done"}
        )

        successor = await service.spawn_agent_job(
            agent_display_name="successor",
            agent_name="tdd-implementor",
            mission="Fix issues",
            project_id=project.id,
            tenant_key=tenant_key,
            predecessor_job_id=pred_spawn.job_id,
        )

        assert successor.predecessor_job_id == pred_spawn.job_id


# ============================================================================
# Test 2: Predecessor context truncation
# ============================================================================


@pytest.mark.asyncio
class TestPredecessorContextTruncation:
    """Verify summary truncation and commits capping."""

    async def test_long_summary_truncated_at_2000_chars(
        self, db_session, service, project, tenant_key
    ):
        """Summaries over 2000 chars should be truncated with [TRUNCATED] marker."""
        long_summary = "A" * 3000
        pred_spawn = await _spawn_and_complete(
            service, project.id, tenant_key, {"summary": long_summary}
        )

        successor = await service.spawn_agent_job(
            agent_display_name="successor",
            agent_name="tdd-implementor",
            mission="Fix it",
            project_id=project.id,
            tenant_key=tenant_key,
            predecessor_job_id=pred_spawn.job_id,
        )

        stmt = select(AgentJob).where(AgentJob.job_id == successor.job_id)
        res = await db_session.execute(stmt)
        job = res.scalar_one()

        assert "[TRUNCATED]" in job.mission
        # The full 3000-char summary should NOT be in the mission
        assert long_summary not in job.mission

    async def test_commits_capped_at_10(
        self, db_session, service, project, tenant_key
    ):
        """Commits list should be capped at 10 entries."""
        many_commits = [f"commit_{i}" for i in range(20)]
        pred_spawn = await _spawn_and_complete(
            service, project.id, tenant_key, {"summary": "Done", "commits": many_commits}
        )

        successor = await service.spawn_agent_job(
            agent_display_name="successor",
            agent_name="tdd-implementor",
            mission="Fix it",
            project_id=project.id,
            tenant_key=tenant_key,
            predecessor_job_id=pred_spawn.job_id,
        )

        stmt = select(AgentJob).where(AgentJob.job_id == successor.job_id)
        res = await db_session.execute(stmt)
        job = res.scalar_one()

        # commit_9 (10th entry) should be present, commit_10 should not
        assert "commit_9" in job.mission
        assert "commit_10" not in job.mission
        assert "... and 10 more" in job.mission


# ============================================================================
# Test 3: Predecessor validation - existence
# ============================================================================


@pytest.mark.asyncio
class TestPredecessorValidation:
    """Verify predecessor_job_id validation."""

    async def test_nonexistent_predecessor_raises_error(
        self, service, project, tenant_key
    ):
        """Spawning with a non-existent predecessor_job_id should raise ResourceNotFoundError."""
        from src.giljo_mcp.exceptions import ResourceNotFoundError

        with pytest.raises(ResourceNotFoundError, match="Predecessor job"):
            await service.spawn_agent_job(
                agent_display_name="successor",
                agent_name="specialist-1",
                mission="Fix issues",
                project_id=project.id,
                tenant_key=tenant_key,
                predecessor_job_id=str(uuid.uuid4()),  # Non-existent
            )

    async def test_predecessor_different_project_raises_error(
        self, db_session, service, project, tenant_key
    ):
        """Predecessor from a different project should raise ValidationError."""
        from src.giljo_mcp.exceptions import ValidationError

        # Create a second project in the same tenant (unique series_number to avoid uq_project_taxonomy)
        from datetime import datetime, timezone

        proj2 = Project(
            id=str(uuid.uuid4()),
            name="Other Project",
            description="Different project",
            mission="Other work",
            status="active",
            tenant_key=tenant_key,
            series_number=random.randint(1, 999999),
            implementation_launched_at=datetime.now(timezone.utc),
        )
        db_session.add(proj2)
        await db_session.commit()

        # Spawn and complete predecessor in project2
        pred_spawn = await _spawn_and_complete(
            service, proj2.id, tenant_key, {"summary": "Done in other project"}
        )

        # Try to spawn successor in project1 referencing project2's predecessor
        with pytest.raises(ValidationError, match="different project"):
            await service.spawn_agent_job(
                agent_display_name="successor",
                agent_name="specialist-1",
                mission="Fix issues",
                project_id=project.id,
                tenant_key=tenant_key,
                predecessor_job_id=pred_spawn.job_id,
            )

    async def test_predecessor_different_tenant_raises_error(
        self, service, project, other_project, tenant_key, other_tenant_key
    ):
        """Predecessor from a different tenant should raise ResourceNotFoundError (not found in tenant scope)."""
        from src.giljo_mcp.exceptions import ResourceNotFoundError

        # Spawn and complete in OTHER tenant
        pred_spawn = await _spawn_and_complete(
            service, other_project.id, other_tenant_key, {"summary": "Other tenant work"}
        )

        # Try to spawn successor referencing other tenant's predecessor
        with pytest.raises(ResourceNotFoundError, match="Predecessor job"):
            await service.spawn_agent_job(
                agent_display_name="successor",
                agent_name="specialist-1",
                mission="Fix issues",
                project_id=project.id,
                tenant_key=tenant_key,
                predecessor_job_id=pred_spawn.job_id,
            )


# ============================================================================
# Test 4: Predecessor with no completion result
# ============================================================================


@pytest.mark.asyncio
class TestPredecessorNoResult:
    """Verify graceful handling when predecessor has no stored result."""

    async def test_predecessor_not_completed_still_injects_context(
        self, db_session, service, project, tenant_key
    ):
        """If predecessor exists but isn't complete, context still injected with defaults."""
        # Spawn predecessor but do NOT complete it
        pred_spawn = await service.spawn_agent_job(
            agent_display_name="predecessor",
            agent_name="specialist-1",
            mission="Still working",
            project_id=project.id,
            tenant_key=tenant_key,
        )

        successor = await service.spawn_agent_job(
            agent_display_name="successor",
            agent_name="tdd-implementor",
            mission="Fix the issues",
            project_id=project.id,
            tenant_key=tenant_key,
            predecessor_job_id=pred_spawn.job_id,
        )

        stmt = select(AgentJob).where(AgentJob.job_id == successor.job_id)
        res = await db_session.execute(stmt)
        job = res.scalar_one()

        assert "## PREDECESSOR CONTEXT" in job.mission
        assert "No summary available" in job.mission
        assert "Fix the issues" in job.mission


# ============================================================================
# Test 5: get_agent_result tool returns stored result
# ============================================================================


@pytest.mark.asyncio
class TestGetAgentResultTool:
    """Verify get_agent_result via tool_accessor returns stored result."""

    async def test_returns_result_for_completed_job(
        self, service, project, tenant_key
    ):
        """get_agent_result should return the result dict."""
        result_payload = {
            "summary": "Auth module complete",
            "artifacts": ["src/auth.py"],
            "commits": ["abc123"],
        }
        pred_spawn = await _spawn_and_complete(
            service, project.id, tenant_key, result_payload
        )

        stored = await service.get_agent_result(
            job_id=pred_spawn.job_id,
            tenant_key=tenant_key,
        )

        assert stored is not None
        assert stored["summary"] == "Auth module complete"
        assert "abc123" in stored["commits"]

    async def test_returns_none_for_incomplete_job(
        self, service, project, tenant_key
    ):
        """get_agent_result should return None for jobs not yet completed."""
        spawn = await service.spawn_agent_job(
            agent_display_name="specialist",
            agent_name="specialist-1",
            mission="Still working",
            project_id=project.id,
            tenant_key=tenant_key,
        )

        stored = await service.get_agent_result(
            job_id=spawn.job_id,
            tenant_key=tenant_key,
        )

        assert stored is None

    async def test_tenant_isolation(
        self, service, project, other_project, tenant_key, other_tenant_key
    ):
        """get_agent_result should NOT return results from other tenants."""
        result_payload = {"summary": "Secret work", "commits": ["secret123"]}
        pred_spawn = await _spawn_and_complete(
            service, other_project.id, other_tenant_key, result_payload
        )

        # Try to read with wrong tenant key
        stored = await service.get_agent_result(
            job_id=pred_spawn.job_id,
            tenant_key=tenant_key,  # WRONG tenant
        )

        assert stored is None


# ============================================================================
# Test 6: Regression - Spawn without predecessor unchanged
# ============================================================================


@pytest.mark.asyncio
class TestSpawnWithoutPredecessorRegression:
    """Verify existing behavior unchanged when predecessor_job_id is not provided."""

    async def test_spawn_without_predecessor_works(
        self, db_session, service, project, tenant_key
    ):
        """Normal spawn (no predecessor) should work exactly as before."""
        result = await service.spawn_agent_job(
            agent_display_name="implementer",
            agent_name="specialist-1",
            mission="Implement the feature",
            project_id=project.id,
            tenant_key=tenant_key,
        )

        assert result.job_id is not None
        assert result.agent_id is not None
        assert result.predecessor_job_id is None
        assert result.mission_stored is True

        # Verify mission does NOT contain predecessor context
        stmt = select(AgentJob).where(AgentJob.job_id == result.job_id)
        res = await db_session.execute(stmt)
        job = res.scalar_one()

        assert "PREDECESSOR CONTEXT" not in job.mission
        assert "Implement the feature" in job.mission

    async def test_spawn_with_none_predecessor_works(
        self, service, project, tenant_key
    ):
        """Explicitly passing predecessor_job_id=None should work as normal."""
        result = await service.spawn_agent_job(
            agent_display_name="implementer-2",
            agent_name="specialist-1",
            mission="Normal mission",
            project_id=project.id,
            tenant_key=tenant_key,
            predecessor_job_id=None,
        )

        assert result.job_id is not None
        assert result.predecessor_job_id is None
