"""
Integration tests for spawn_agent_job validation (Handover 0260 Phase 5b).

End-to-end tests validating agent type validation when spawning agents through
the full orchestration workflow. Tests real database interactions, MCP tool
invocation, and error handling.

Test Coverage:
1. Valid agent spawning through orchestrator workflow
2. Invalid agent type rejection with database verification
3. Multi-tenant isolation in validation
4. get_available_agents integration with spawn_agent_job
5. Orchestrator receives correct constraint in CLI mode
6. Error messages guide orchestrator to fix invalid spawns
"""

import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.models import AgentTemplate, Product, Project, User
from src.giljo_mcp.models.agent_identity import AgentJob, AgentExecution
from src.giljo_mcp.tools.orchestration import (
    get_orchestrator_instructions,
    spawn_agent_job,
)
from src.giljo_mcp.tools.agent_discovery import get_available_agents
from tests.fixtures.base_fixtures import db_manager, db_session


# ============================================================================
# FIXTURES
# ============================================================================


@pytest_asyncio.fixture
async def validation_tenant():
    """Unique tenant for validation tests"""
    return f"val_tenant_{uuid.uuid4().hex[:8]}"


@pytest_asyncio.fixture
async def validation_user(db_session, validation_tenant):
    """User who will orchestrate agents"""
    user = User(
        id=str(uuid.uuid4()),
        username=f"valuser_{uuid.uuid4().hex[:6]}",
        email=f"valuser_{uuid.uuid4().hex[:6]}@test.com",
        tenant_key=validation_tenant,
        role="developer",
        password_hash="hash",
        field_priority_config={
            "version": "2.0",
            "priorities": {
                "product_core": 1,
                "agent_templates": 2,
            },
        },
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def validation_product(db_session, validation_tenant):
    """Product with agent templates for validation"""
    product = Product(
        id=str(uuid.uuid4()),
        name=f"ValidationProd_{uuid.uuid4().hex[:6]}",
        description="Product for validation testing",
        product_type="backend_service",
        tenant_key=validation_tenant,
    )
    db_session.add(product)
    await db_session.flush()
    return product


@pytest_asyncio.fixture
async def validation_project(db_session, validation_product, validation_tenant):
    """Project for validation testing"""
    project = Project(
        id=str(uuid.uuid4()),
        product_id=validation_product.id,
        name=f"ValidationProject_{uuid.uuid4().hex[:6]}",
        description="Test project for agent validation",
        status="created",
        tenant_key=validation_tenant,
    )
    db_session.add(project)
    await db_session.flush()
    return project


@pytest_asyncio.fixture
async def validation_templates(db_session, validation_product, validation_tenant):
    """Active agent templates for validation testing"""
    templates = [
        AgentTemplate(
            id=str(uuid.uuid4()),
            name="implementer",
            role="Code Implementation Specialist",
            description="Implements features",
            tenant_key=validation_tenant,
            product_id=validation_product.id,
            is_active=True,
            version="1.0.0",
            template_content="# Implementer\n\nImplements code.",
        ),
        AgentTemplate(
            id=str(uuid.uuid4()),
            name="tester",
            role="Testing Specialist",
            description="Writes tests",
            tenant_key=validation_tenant,
            product_id=validation_product.id,
            is_active=True,
            version="1.0.0",
            template_content="# Tester\n\nWrites tests.",
        ),
        AgentTemplate(
            id=str(uuid.uuid4()),
            name="reviewer",
            role="Code Review Specialist",
            description="Reviews code",
            tenant_key=validation_tenant,
            product_id=validation_product.id,
            is_active=True,
            version="1.0.0",
            template_content="# Reviewer\n\nReviews code.",
        ),
    ]
    for template in templates:
        db_session.add(template)
    await db_session.flush()
    return templates


@pytest_asyncio.fixture
async def cli_orchestrator(db_session, validation_project, validation_tenant, validation_user):
    """Orchestrator in CLI mode for testing constraints"""
    orchestrator = AgentExecution(
        job_id=str(uuid.uuid4()),
        project_id=validation_project.id,
        tenant_key=validation_tenant,
        agent_type="orchestrator",
        agent_name="CLI Orchestrator",
        status="waiting",
        mission="Test orchestration with validation",
        tool_type="claude-code",
        job_metadata={
            "field_priorities": validation_user.field_priority_config["priorities"],
            "execution_mode": "claude_code_cli",  # CLI mode
            "user_id": validation_user.id,
        },
    )
    db_session.add(orchestrator)
    await db_session.flush()
    return orchestrator


# ============================================================================
# TEST SUITE 1: Valid Agent Spawning
# ============================================================================


class TestValidAgentSpawning:
    """Test successful agent spawning with valid agent types"""

    @pytest.mark.asyncio
    async def test_spawn_implementer_agent_succeeds(
        self, db_session, validation_project, validation_tenant, validation_templates
    ):
        """
        INTEGRATION: Spawn implementer agent with valid agent_type through full workflow
        """
        # Spawn implementer (valid type)
        result = await spawn_agent_job(
            agent_type="implementer",
            agent_name="Backend Implementer",
            mission="Implement user authentication",
            project_id=str(validation_project.id),
            tenant_key=validation_tenant,
            session=db_session,
        )

        # ASSERTION: Spawn succeeds
        assert result["success"] is True
        assert "job_id" in result

        # ASSERTION: Agent job exists in database
        job_id = result["job_id"]
        stmt = select(AgentExecution).where(AgentExecution.job_id == job_id)
        db_result = await db_session.execute(stmt)
        agent_job = db_result.scalar_one_or_none()

        assert agent_job is not None, "Agent job should exist in database"
        assert agent_job.agent_type == "implementer"
        assert agent_job.tenant_key == validation_tenant
        assert agent_job.status == "waiting"

    @pytest.mark.asyncio
    async def test_spawn_all_valid_agent_types(
        self, db_session, validation_project, validation_tenant, validation_templates
    ):
        """
        INTEGRATION: All valid agent types from templates can be spawned
        """
        # Spawn each valid type
        for agent_type in ["implementer", "tester", "reviewer"]:
            result = await spawn_agent_job(
                agent_type=agent_type,
                agent_name=f"Test {agent_type.title()}",
                mission=f"Test mission for {agent_type}",
                project_id=str(validation_project.id),
                tenant_key=validation_tenant,
                session=db_session,
            )

            # ASSERTION: Each spawn succeeds
            assert result["success"] is True, (
                f"Failed to spawn valid agent_type '{agent_type}': {result.get('error')}"
            )

            # ASSERTION: Agent exists in database
            job_id = result["job_id"]
            stmt = select(AgentExecution).where(AgentExecution.job_id == job_id)
            db_result = await db_session.execute(stmt)
            agent_job = db_result.scalar_one()

            assert agent_job.agent_type == agent_type


# ============================================================================
# TEST SUITE 2: Invalid Agent Type Rejection
# ============================================================================


class TestInvalidAgentTypeRejection:
    """Test rejection of invalid agent types with helpful errors"""

    @pytest.mark.asyncio
    async def test_spawn_invented_agent_type_rejected(
        self, db_session, validation_project, validation_tenant, validation_templates
    ):
        """
        INTEGRATION: Invented agent types are rejected with helpful error
        """
        # Attempt to spawn invented agent type
        result = await spawn_agent_job(
            agent_type="backend-api-specialist",  # INVALID (invented)
            agent_name="API Developer",
            mission="Develop APIs",
            project_id=str(validation_project.id),
            tenant_key=validation_tenant,
            session=db_session,
        )

        # ASSERTION 1: Spawn fails
        assert result["success"] is False

        # ASSERTION 2: Error message present
        assert "error" in result
        error_msg = result["error"]

        # ASSERTION 3: Error mentions invalid type
        assert "Invalid agent_type" in error_msg
        assert "backend-api-specialist" in error_msg

        # ASSERTION 4: Error lists valid types
        assert "implementer" in error_msg
        assert "tester" in error_msg
        assert "reviewer" in error_msg

        # ASSERTION 5: Hint present
        assert "hint" in result
        assert "agent_name" in result["hint"]

        # ASSERTION 6: No agent job created in database
        stmt = select(AgentExecution).where(
            AgentExecution.project_id == validation_project.id,
            AgentExecution.agent_type == "backend-api-specialist",
        )
        db_result = await db_session.execute(stmt)
        agent_job = db_result.scalar_one_or_none()

        assert agent_job is None, (
            "Invalid agent type should NOT create database entry"
        )

    @pytest.mark.asyncio
    async def test_spawn_descriptive_name_as_type_rejected(
        self, db_session, validation_project, validation_tenant, validation_templates
    ):
        """
        INTEGRATION: Descriptive names used as agent_type are rejected
        """
        # Attempt to use descriptive name as agent_type (common mistake)
        result = await spawn_agent_job(
            agent_type="Backend Testing Specialist Agent",  # WRONG
            agent_name="Tester",
            mission="Test backend",
            project_id=str(validation_project.id),
            tenant_key=validation_tenant,
            session=db_session,
        )

        # ASSERTION: Rejected
        assert result["success"] is False
        assert "error" in result

        # ASSERTION: Hint explains agent_name vs agent_type
        assert "hint" in result
        hint_lower = result["hint"].lower()
        assert "agent_name" in hint_lower
        assert "agent_type" in hint_lower

    @pytest.mark.asyncio
    async def test_spawn_wrong_case_agent_type_rejected(
        self, db_session, validation_project, validation_tenant, validation_templates
    ):
        """
        INTEGRATION: Agent type matching is case-sensitive
        """
        # Attempt to spawn with wrong case
        result = await spawn_agent_job(
            agent_type="Implementer",  # WRONG CASE (should be lowercase)
            agent_name="Backend Developer",
            mission="Develop backend",
            project_id=str(validation_project.id),
            tenant_key=validation_tenant,
            session=db_session,
        )

        # ASSERTION: Rejected
        assert result["success"] is False
        assert "error" in result

        # ASSERTION: Error shows correct case
        error_msg = result["error"]
        assert "implementer" in error_msg, (
            "Error should show correct lowercase version"
        )


# ============================================================================
# TEST SUITE 3: Multi-Tenant Isolation
# ============================================================================


class TestMultiTenantValidation:
    """Test validation respects multi-tenant boundaries"""

    @pytest.mark.asyncio
    async def test_spawn_validates_against_tenant_templates_only(
        self, db_session, validation_project, validation_tenant, validation_templates
    ):
        """
        INTEGRATION: Agent type validation only considers templates for current tenant
        """
        # Create template for DIFFERENT tenant
        other_tenant = f"other_{uuid.uuid4().hex[:8]}"
        other_product = Product(
            id=str(uuid.uuid4()),
            name="Other Product",
            tenant_key=other_tenant,
        )
        db_session.add(other_product)
        await db_session.flush()

        other_template = AgentTemplate(
            id=str(uuid.uuid4()),
            name="other_agent",  # Only exists in other tenant
            role="Other Agent",
            tenant_key=other_tenant,
            product_id=other_product.id,
            is_active=True,
            template_content="# Other Agent\n\nFor other tenant.",
        )
        db_session.add(other_template)
        await db_session.flush()

        # Attempt to spawn agent from OTHER tenant's templates
        result = await spawn_agent_job(
            agent_type="other_agent",  # Exists in other tenant, not current
            agent_name="Test Agent",
            mission="Test mission",
            project_id=str(validation_project.id),
            tenant_key=validation_tenant,  # Current tenant
            session=db_session,
        )

        # ASSERTION: Rejected (not in current tenant's templates)
        assert result["success"] is False

        # ASSERTION: Error lists only current tenant's templates
        error_msg = result["error"]
        assert "implementer" in error_msg  # Current tenant's template
        assert "other_agent" not in error_msg  # Other tenant's template


# ============================================================================
# TEST SUITE 4: Orchestrator Constraint Integration
# ============================================================================


class TestOrchestratorConstraintIntegration:
    """Test orchestrator receives correct constraints in CLI mode"""

    @pytest.mark.asyncio
    async def test_orchestrator_receives_constraint_in_cli_mode(
        self, db_session, cli_orchestrator, validation_tenant, validation_templates, db_manager
    ):
        """
        INTEGRATION: CLI orchestrator receives agent_spawning_constraint with
        accurate list of allowed agent types from database
        """
        # Get orchestrator instructions
        result = await get_orchestrator_instructions(
            orchestrator_id=cli_orchestrator.job_id,
            tenant_key=validation_tenant,
            db_manager=db_manager,
        )

        # ASSERTION 1: Constraint present
        assert "agent_spawning_constraint" in result

        constraint = result["agent_spawning_constraint"]

        # ASSERTION 2: Constraint structure correct
        assert constraint["mode"] == "strict_task_tool"
        assert "allowed_agent_types" in constraint
        assert "instruction" in constraint

        # ASSERTION 3: allowed_agent_types matches database templates
        allowed_types = set(constraint["allowed_agent_types"])
        expected_types = {"implementer", "tester", "reviewer"}

        assert allowed_types == expected_types, (
            f"Constraint should match active templates. "
            f"Expected: {expected_types}, Got: {allowed_types}"
        )

    @pytest.mark.asyncio
    async def test_constraint_matches_get_available_agents(
        self, db_session, cli_orchestrator, validation_tenant, validation_templates, db_manager
    ):
        """
        INTEGRATION: agent_spawning_constraint matches get_available_agents() output
        """
        # Get orchestrator constraint
        orch_result = await get_orchestrator_instructions(
            orchestrator_id=cli_orchestrator.job_id,
            tenant_key=validation_tenant,
            db_manager=db_manager,
        )

        constraint_types = set(orch_result["agent_spawning_constraint"]["allowed_agent_types"])

        # Get available agents directly
        agents_result = await get_available_agents(
            db_session, validation_tenant, depth="type_only"
        )

        available_types = {agent["name"] for agent in agents_result["data"]["agents"]}

        # ASSERTION: Both sources match
        assert constraint_types == available_types, (
            f"Constraint and get_available_agents() must match. "
            f"Constraint: {constraint_types}, Available: {available_types}"
        )


# ============================================================================
# TEST SUITE 5: Error Message Quality
# ============================================================================


class TestErrorMessageQuality:
    """Test error messages provide actionable guidance"""

    @pytest.mark.asyncio
    async def test_error_message_lists_all_valid_types(
        self, db_session, validation_project, validation_tenant, validation_templates
    ):
        """
        INTEGRATION: Error message lists ALL valid agent types for orchestrator
        """
        result = await spawn_agent_job(
            agent_type="invalid",
            agent_name="Test Agent",
            mission="Test mission",
            project_id=str(validation_project.id),
            tenant_key=validation_tenant,
            session=db_session,
        )

        error_msg = result["error"]

        # ASSERTION: All valid types mentioned
        for template in validation_templates:
            assert template.name in error_msg, (
                f"Error should list all valid types. Missing: {template.name}"
            )

    @pytest.mark.asyncio
    async def test_hint_guides_orchestrator_to_fix(
        self, db_session, validation_project, validation_tenant, validation_templates
    ):
        """
        INTEGRATION: Hint field provides actionable guidance to fix error
        """
        result = await spawn_agent_job(
            agent_type="custom-agent-type",
            agent_name="Custom Agent",
            mission="Test mission",
            project_id=str(validation_project.id),
            tenant_key=validation_tenant,
            session=db_session,
        )

        # ASSERTION: Hint present
        assert "hint" in result

        hint = result["hint"]

        # ASSERTION: Hint explains agent_name for descriptive text
        assert "agent_name" in hint

        # ASSERTION: Hint explains agent_type for exact match
        assert "agent_type" in hint

        # ASSERTION: Hint mentions template requirement
        hint_lower = hint.lower()
        assert any(word in hint_lower for word in ["exact", "match", "template"])


# ============================================================================
# TEST SUITE 6: Inactive Template Handling
# ============================================================================


class TestInactiveTemplateHandling:
    """Test inactive templates are excluded from validation"""

    @pytest.mark.asyncio
    async def test_inactive_template_not_spawnable(
        self, db_session, validation_project, validation_tenant, validation_product
    ):
        """
        INTEGRATION: Inactive templates cannot be spawned even if they exist
        """
        # Create inactive template
        inactive_template = AgentTemplate(
            id=str(uuid.uuid4()),
            name="deprecated",
            role="Deprecated Agent",
            tenant_key=validation_tenant,
            product_id=validation_product.id,
            is_active=False,  # INACTIVE
            template_content="# Deprecated\n\nOld agent.",
        )
        db_session.add(inactive_template)
        await db_session.flush()

        # Attempt to spawn inactive agent
        result = await spawn_agent_job(
            agent_type="deprecated",
            agent_name="Deprecated Agent",
            mission="Test mission",
            project_id=str(validation_project.id),
            tenant_key=validation_tenant,
            session=db_session,
        )

        # ASSERTION: Rejected
        assert result["success"] is False
        assert "error" in result

        # ASSERTION: Error does NOT list inactive template
        error_msg = result["error"]
        assert "deprecated" not in error_msg, (
            "Error should NOT list inactive templates as valid options"
        )

    @pytest.mark.asyncio
    async def test_orchestrator_constraint_excludes_inactive_templates(
        self, db_session, cli_orchestrator, validation_tenant, validation_product, db_manager
    ):
        """
        INTEGRATION: Orchestrator constraint excludes inactive templates
        """
        # Add inactive template
        inactive_template = AgentTemplate(
            id=str(uuid.uuid4()),
            name="old_agent",
            role="Old Agent",
            tenant_key=validation_tenant,
            product_id=validation_product.id,
            is_active=False,
            template_content="# Old Agent\n\nInactive agent.",
        )
        db_session.add(inactive_template)
        await db_session.flush()

        # Get orchestrator instructions
        result = await get_orchestrator_instructions(
            orchestrator_id=cli_orchestrator.job_id,
            tenant_key=validation_tenant,
            db_manager=db_manager,
        )

        constraint = result["agent_spawning_constraint"]
        allowed_types = constraint["allowed_agent_types"]

        # ASSERTION: Inactive template NOT in allowed types
        assert "old_agent" not in allowed_types, (
            "Inactive templates must NOT be in allowed_agent_types"
        )
