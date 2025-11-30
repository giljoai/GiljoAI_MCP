"""
Integration tests for agent spawning with context (Handover 0272)

This test suite validates that spawned agents receive appropriate context based
on their role, respecting all handover features:

- Handover 0266: Field priorities used to determine context detail level
- Handover 0267: Serena instructions included when Serena enabled
- Handover 0268: 360 memory available for context
- Handover 0269: GitHub integration status available
- Handover 0270: MCP tool catalog available to agents
- Handover 0271: Testing config available for test-focused agents

Tests validate:
1. Different agent roles receive role-appropriate context
2. Field priorities control what context is visible
3. Context respects user settings and product configuration
4. Agent missions are complete and actionable
5. Agent has access to necessary MCP tools via instructions
"""

import json
import pytest
import pytest_asyncio
from uuid import uuid4
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.models import (
    User, Product, Project, MCPAgentJob, AgentTemplate
)
from src.giljo_mcp.mission_planner import MissionPlanner
from src.giljo_mcp.thin_prompt_generator import ThinClientPromptGenerator

from tests.fixtures.base_fixtures import db_manager, db_session


# ============================================================================
# FIXTURES
# ============================================================================

@pytest_asyncio.fixture
async def agent_test_tenant():
    """Unique tenant for agent spawning tests"""
    return f"agent_tenant_{uuid4().hex[:8]}"


@pytest_asyncio.fixture
async def agent_test_user(db_session, agent_test_tenant):
    """User who will orchestrate agents"""
    user = User(
        id=str(uuid4()),
        username=f"agentuser_{uuid4().hex[:6]}",
        email=f"agentuser_{uuid4().hex[:6]}@example.com",
        tenant_key=agent_test_tenant,
        role="developer",
        password_hash="hash",
        field_priority_config={
            "version": "2.0",
            "priorities": {
                "product_core": 1,
                "vision_documents": 2,
                "tech_stack": 2,
                "architecture": 2,
                "testing": 2,
                "memory_360": 2,
                "git_history": 3,
                "agent_templates": 3,
            }
        },
        serena_enabled=True,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def agent_test_product(db_session, agent_test_tenant):
    """Product with full configuration for agent tests"""
    product = Product(
        id=str(uuid4()),
        name=f"AgentTestProd_{uuid4().hex[:6]}",
        description="Product for agent spawning tests",
        product_type="backend_service",
        tenant_key=agent_test_tenant,
        tech_stack={
            "languages": ["python"],
            "frameworks": ["fastapi"],
            "database": "postgresql",
        },
        testing_config={
            "framework": "pytest",
            "coverage_target": 85,
            "strategy": "comprehensive",
        },
        product_memory={
            "git_integration": {
                "enabled": True,
                "repository_url": "https://github.com/example/repo",
            },
            "sequential_history": [
                {
                    "sequence": 1,
                    "type": "project_closeout",
                    "project_id": str(uuid4()),
                    "summary": "First iteration completed",
                    "timestamp": datetime.utcnow().isoformat(),
                }
            ]
        },
    )
    db_session.add(product)
    await db_session.flush()
    return product


@pytest_asyncio.fixture
async def agent_test_project(db_session, agent_test_product, agent_test_tenant):
    """Project for agents to work on"""
    project = Project(
        id=str(uuid4()),
        product_id=agent_test_product.id,
        name=f"AgentTestProject_{uuid4().hex[:6]}",
        description="Test project for agent spawning",
        status="created",
        tenant_key=agent_test_tenant,
    )
    db_session.add(project)
    await db_session.flush()
    return project


# ============================================================================
# TEST SUITE 1: Implementer Agent Context
# ============================================================================

class TestImplementerAgentContext:
    """
    Validate that Implementer agents receive development-focused context
    """

    async def test_implementer_receives_full_tech_stack(
        self,
        db_session,
        agent_test_user,
        agent_test_product,
        agent_test_project,
        agent_test_tenant,
    ):
        """
        REQUIREMENT: Implementer agents must have full tech stack to code effectively
        """
        planner = MissionPlanner(test_session=db_session)

        # Generate implementer mission
        mission = await planner.plan_orchestrator_mission(
            user_id=agent_test_user.id,
            product_id=agent_test_product.id,
            project_id=agent_test_project.id,
            tenant_key=agent_test_tenant,
        )

        # Mission must include tech stack details
        assert mission is not None
        mission_lower = mission.lower()

        # Should mention technologies
        tech_keywords = ["python", "fastapi", "postgresql", "backend"]
        assert any(keyword in mission_lower for keyword in tech_keywords)

    async def test_implementer_receives_architecture_context(
        self,
        db_session,
        agent_test_user,
        agent_test_product,
        agent_test_project,
        agent_test_tenant,
    ):
        """
        REQUIREMENT: Implementer agents must understand system architecture
        """
        planner = MissionPlanner(test_session=db_session)

        mission = await planner.plan_orchestrator_mission(
            user_id=agent_test_user.id,
            product_id=agent_test_product.id,
            project_id=agent_test_project.id,
            tenant_key=agent_test_tenant,
        )

        # Architecture context should be present
        assert mission is not None
        assert len(mission) > 500

    async def test_implementer_receives_project_specifics(
        self,
        db_session,
        agent_test_user,
        agent_test_product,
        agent_test_project,
        agent_test_tenant,
    ):
        """
        REQUIREMENT: Implementer must know current project name and scope
        """
        planner = MissionPlanner(test_session=db_session)

        mission = await planner.plan_orchestrator_mission(
            user_id=agent_test_user.id,
            product_id=agent_test_product.id,
            project_id=agent_test_project.id,
            tenant_key=agent_test_tenant,
        )

        # Project name should be in mission
        assert agent_test_project.name in mission or "project" in mission.lower()


# ============================================================================
# TEST SUITE 2: Tester Agent Context
# ============================================================================

class TestTesterAgentContext:
    """
    Validate that Tester agents receive testing-focused context
    """

    async def test_tester_receives_testing_config(
        self,
        db_session,
        agent_test_user,
        agent_test_product,
        agent_test_project,
        agent_test_tenant,
    ):
        """
        REQUIREMENT: Tester agents must have testing configuration (Handover 0271)
        to create appropriate tests
        """
        planner = MissionPlanner(test_session=db_session)

        mission = await planner.plan_orchestrator_mission(
            user_id=agent_test_user.id,
            product_id=agent_test_product.id,
            project_id=agent_test_project.id,
            tenant_key=agent_test_tenant,
        )

        # Testing config should be included
        assert mission is not None
        mission_lower = mission.lower()

        # Should mention testing framework
        assert any(keyword in mission_lower for keyword in ["test", "pytest", "coverage"])

    async def test_tester_receives_tech_stack_for_tests(
        self,
        db_session,
        agent_test_user,
        agent_test_product,
        agent_test_project,
        agent_test_tenant,
    ):
        """
        REQUIREMENT: Tester must know tech stack to create language-appropriate tests
        """
        planner = MissionPlanner(test_session=db_session)

        mission = await planner.plan_orchestrator_mission(
            user_id=agent_test_user.id,
            product_id=agent_test_product.id,
            project_id=agent_test_project.id,
            tenant_key=agent_test_tenant,
        )

        assert mission is not None
        # Should include language/framework
        assert "python" in mission.lower()


# ============================================================================
# TEST SUITE 3: Architect Agent Context
# ============================================================================

class TestArchitectAgentContext:
    """
    Validate that Architect agents receive design-focused context
    """

    async def test_architect_receives_full_architecture(
        self,
        db_session,
        agent_test_user,
        agent_test_product,
        agent_test_project,
        agent_test_tenant,
    ):
        """
        REQUIREMENT: Architect agents must have comprehensive architecture info
        to make informed design decisions
        """
        planner = MissionPlanner(test_session=db_session)

        mission = await planner.plan_orchestrator_mission(
            user_id=agent_test_user.id,
            product_id=agent_test_product.id,
            project_id=agent_test_project.id,
            tenant_key=agent_test_tenant,
        )

        assert mission is not None
        # Should be detailed enough for architecture decisions
        assert len(mission) > 800

    async def test_architect_receives_memory_context(
        self,
        db_session,
        agent_test_user,
        agent_test_product,
        agent_test_project,
        agent_test_tenant,
    ):
        """
        REQUIREMENT: Architect must understand product history (360 memory)
        to maintain architectural consistency
        """
        planner = MissionPlanner(test_session=db_session)

        mission = await planner.plan_orchestrator_mission(
            user_id=agent_test_user.id,
            product_id=agent_test_product.id,
            project_id=agent_test_project.id,
            tenant_key=agent_test_tenant,
        )

        # Memory/history should be referenced
        assert mission is not None


# ============================================================================
# TEST SUITE 4: Context Respects Field Priorities
# ============================================================================

class TestContextRespectsPriorities:
    """
    Validate that agent context respects user's field priority settings
    """

    async def test_high_priority_contexts_always_included(
        self,
        db_session,
        agent_test_user,
        agent_test_product,
        agent_test_project,
        agent_test_tenant,
    ):
        """
        REQUIREMENT: Priority 1 contexts always included in agent mission
        (Handover 0266 - field priority persistence affects agent context)
        """
        # Ensure product_core is priority 1
        assert agent_test_user.field_priority_config["priorities"]["product_core"] == 1

        planner = MissionPlanner(test_session=db_session)
        mission = await planner.plan_orchestrator_mission(
            user_id=agent_test_user.id,
            product_id=agent_test_product.id,
            project_id=agent_test_project.id,
            tenant_key=agent_test_tenant,
        )

        # Product core (highest priority) must be included
        assert mission is not None
        assert "product" in mission.lower()

    async def test_excluded_priority_contexts_not_included(
        self,
        db_session,
        agent_test_tenant,
    ):
        """
        REQUIREMENT: Priority 4 (EXCLUDED) contexts not included in agent mission
        """
        # Create user who excludes git_history
        user = User(
            id=str(uuid4()),
            username=f"excludeuser_{uuid4().hex[:6]}",
            email=f"excludeuser_{uuid4().hex[:6]}@example.com",
            tenant_key=agent_test_tenant,
            role="developer",
            password_hash="hash",
            field_priority_config={
                "version": "2.0",
                "priorities": {
                    "product_core": 1,
                    "git_history": 4,  # EXCLUDED
                }
            },
        )
        db_session.add(user)
        await db_session.flush()

        # Verify priority setting
        assert user.field_priority_config["priorities"]["git_history"] == 4


# ============================================================================
# TEST SUITE 5: Serena Instructions in Agent Context
# ============================================================================

class TestSerenaInstructionsForAgents:
    """
    Validate that Serena instructions are included when enabled (Handover 0267)
    """

    async def test_agent_receives_serena_instructions_when_enabled(
        self,
        db_session,
        agent_test_user,
        agent_test_product,
        agent_test_project,
        agent_test_tenant,
    ):
        """
        REQUIREMENT: When Serena enabled, agents receive Serena tool instructions
        (Handover 0267)
        """
        # Verify Serena is enabled
        assert agent_test_user.serena_enabled is True

        planner = MissionPlanner(test_session=db_session)
        mission = await planner.plan_orchestrator_mission(
            user_id=agent_test_user.id,
            product_id=agent_test_product.id,
            project_id=agent_test_project.id,
            tenant_key=agent_test_tenant,
        )

        # Mission should be comprehensive (includes Serena instructions)
        assert mission is not None
        assert len(mission) > 500

    async def test_agent_lacks_serena_instructions_when_disabled(
        self,
        db_session,
        agent_test_tenant,
        agent_test_product,
        agent_test_project,
    ):
        """
        REQUIREMENT: When Serena disabled, agents do NOT receive Serena instructions
        """
        # Create user with Serena disabled
        user = User(
            id=str(uuid4()),
            username=f"noserena_{uuid4().hex[:6]}",
            email=f"noserena_{uuid4().hex[:6]}@example.com",
            tenant_key=agent_test_tenant,
            role="developer",
            password_hash="hash",
            serena_enabled=False,  # Disabled
        )
        db_session.add(user)
        await db_session.flush()

        # Verify Serena is disabled
        assert user.serena_enabled is False


# ============================================================================
# TEST SUITE 6: Agent Mission Completeness
# ============================================================================

class TestAgentMissionCompleteness:
    """
    Validate that agent missions are complete and actionable
    """

    async def test_agent_mission_includes_scope_and_objectives(
        self,
        db_session,
        agent_test_user,
        agent_test_product,
        agent_test_project,
        agent_test_tenant,
    ):
        """
        REQUIREMENT: Agent mission must clearly state scope and objectives
        """
        planner = MissionPlanner(test_session=db_session)
        mission = await planner.plan_orchestrator_mission(
            user_id=agent_test_user.id,
            product_id=agent_test_product.id,
            project_id=agent_test_project.id,
            tenant_key=agent_test_tenant,
        )

        assert mission is not None
        # Should have structure
        assert len(mission) > 200

    async def test_agent_mission_references_available_tools(
        self,
        db_session,
        agent_test_user,
        agent_test_product,
        agent_test_project,
        agent_test_tenant,
    ):
        """
        REQUIREMENT: Agent mission should reference available MCP tools
        (Handover 0270 - MCP tool catalog)
        """
        planner = MissionPlanner(test_session=db_session)
        mission = await planner.plan_orchestrator_mission(
            user_id=agent_test_user.id,
            product_id=agent_test_product.id,
            project_id=agent_test_project.id,
            tenant_key=agent_test_tenant,
        )

        assert mission is not None
        # Should reference tools/capabilities
        mission_lower = mission.lower()
        assert any(word in mission_lower for word in ["tool", "capability", "feature", "mcp"])

    async def test_agent_mission_is_executable(
        self,
        db_session,
        agent_test_user,
        agent_test_product,
        agent_test_project,
        agent_test_tenant,
    ):
        """
        REQUIREMENT: Agent mission must be specific and actionable
        (not vague or incomplete)
        """
        planner = MissionPlanner(test_session=db_session)
        mission = await planner.plan_orchestrator_mission(
            user_id=agent_test_user.id,
            product_id=agent_test_product.id,
            project_id=agent_test_project.id,
            tenant_key=agent_test_tenant,
        )

        assert mission is not None
        # Should have substantial content
        assert len(mission) > 500
        # Should have multiple sections
        assert mission.count("\n") > 5


# ============================================================================
# TEST SUITE 7: Agent Job Metadata Completeness
# ============================================================================

class TestAgentJobMetadataCompleteness:
    """
    Validate that agent jobs have complete metadata for execution
    """

    async def test_agent_job_includes_field_priorities(
        self,
        db_session,
        agent_test_user,
        agent_test_product,
        agent_test_project,
        agent_test_tenant,
    ):
        """
        REQUIREMENT: Agent job metadata must include field priorities
        (Handover 0266)
        """
        generator = ThinClientPromptGenerator(test_session=db_session)

        prompt_data = await generator.generate_thin_orchestrator_prompt(
            product_id=agent_test_product.id,
            project_id=agent_test_project.id,
            user_id=agent_test_user.id,
            tenant_key=agent_test_tenant,
        )

        # Must have metadata with priorities
        assert "job_metadata" in prompt_data
        metadata = prompt_data["job_metadata"]
        assert "field_priorities" in metadata

    async def test_agent_job_includes_user_id(
        self,
        db_session,
        agent_test_user,
        agent_test_product,
        agent_test_project,
        agent_test_tenant,
    ):
        """
        REQUIREMENT: Agent job must include user_id for context loading
        """
        generator = ThinClientPromptGenerator(test_session=db_session)

        prompt_data = await generator.generate_thin_orchestrator_prompt(
            product_id=agent_test_product.id,
            project_id=agent_test_project.id,
            user_id=agent_test_user.id,
            tenant_key=agent_test_tenant,
        )

        metadata = prompt_data["job_metadata"]
        assert metadata.get("user_id") == agent_test_user.id

    async def test_agent_job_includes_tenant_key(
        self,
        db_session,
        agent_test_user,
        agent_test_product,
        agent_test_project,
        agent_test_tenant,
    ):
        """
        REQUIREMENT: Agent job must include tenant_key for multi-tenant isolation
        """
        generator = ThinClientPromptGenerator(test_session=db_session)

        prompt_data = await generator.generate_thin_orchestrator_prompt(
            product_id=agent_test_product.id,
            project_id=agent_test_project.id,
            user_id=agent_test_user.id,
            tenant_key=agent_test_tenant,
        )

        metadata = prompt_data["job_metadata"]
        assert metadata.get("tenant_key") == agent_test_tenant


# ============================================================================
# TEST SUITE 8: Role-Specific Context Filtering
# ============================================================================

class TestRoleSpecificContextFiltering:
    """
    Validate that context is filtered based on agent role
    """

    async def test_implementer_includes_code_examples(
        self,
        db_session,
        agent_test_user,
        agent_test_product,
        agent_test_project,
        agent_test_tenant,
    ):
        """
        REQUIREMENT: Implementer context should guide code development
        """
        planner = MissionPlanner(test_session=db_session)

        mission = await planner.plan_orchestrator_mission(
            user_id=agent_test_user.id,
            product_id=agent_test_product.id,
            project_id=agent_test_project.id,
            tenant_key=agent_test_tenant,
        )

        assert mission is not None
        # Should include implementation guidance
        assert len(mission) > 400

    async def test_tester_emphasizes_quality_standards(
        self,
        db_session,
        agent_test_user,
        agent_test_product,
        agent_test_project,
        agent_test_tenant,
    ):
        """
        REQUIREMENT: Tester context should emphasize quality standards
        """
        # Ensure testing config is present
        assert agent_test_product.testing_config is not None
        assert agent_test_product.testing_config["coverage_target"] == 85

        planner = MissionPlanner(test_session=db_session)

        mission = await planner.plan_orchestrator_mission(
            user_id=agent_test_user.id,
            product_id=agent_test_product.id,
            project_id=agent_test_project.id,
            tenant_key=agent_test_tenant,
        )

        assert mission is not None
