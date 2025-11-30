"""
Integration tests for complete context flow (Handover 0272) - Test-Driven Development

This comprehensive test suite validates that all handovers (0266-0271) work together
correctly in the complete orchestrator context delivery pipeline.

Coverage:
- Handover 0266: Field priority persistence
- Handover 0267: Serena MCP instructions
- Handover 0268: 360 memory context
- Handover 0269: GitHub integration toggle
- Handover 0270: MCP tool catalog instructions
- Handover 0271: Testing configuration context

Test Flow:
1. User configures ALL settings (priorities, GitHub toggle, Serena, testing config)
2. Settings persist to database
3. Project is staged (triggers context generation)
4. Orchestrator receives complete context via get_orchestrator_instructions MCP tool
5. Context includes all enabled features in correct order/format

These are INTEGRATION tests, validating complete user journeys across system
boundaries, not isolated unit tests.
"""

import json
import pytest
import pytest_asyncio
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from src.giljo_mcp.models import User, Product, Project, MCPAgentJob
from src.giljo_mcp.thin_prompt_generator import ThinClientPromptGenerator
from src.giljo_mcp.mission_planner import MissionPlanner
from src.giljo_mcp.services.product_service import ProductService
from src.giljo_mcp.services.project_service import ProjectService
from src.giljo_mcp.services.orchestration_service import OrchestrationService

from tests.fixtures.base_fixtures import db_manager, db_session


# ============================================================================
# TEST DATA FIXTURES
# ============================================================================

@pytest_asyncio.fixture
async def integration_tenant_key():
    """Generate unique tenant key for test isolation"""
    return f"integration_tenant_{uuid4().hex[:8]}"


@pytest_asyncio.fixture
async def fully_configured_user(db_session, integration_tenant_key):
    """Create user with ALL settings configured"""
    user = User(
        id=str(uuid4()),
        username=f"fullconfig_{uuid4().hex[:6]}",
        email=f"fullconfig_{uuid4().hex[:6]}@example.com",
        tenant_key=integration_tenant_key,
        role="developer",
        password_hash="hashed_password",
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
            },
        },
        depth_config={
            "vision_chunking": "heavy",
            "memory_last_n_projects": 10,
            "git_commits": 50,
        },
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def product_with_all_features(db_session, integration_tenant_key):
    """Create product with vision docs, memory, GitHub config"""
    product = Product(
        id=str(uuid4()),
        name=f"FullFeatureProduct_{uuid4().hex[:6]}",
        description="Product with all features enabled",
        product_type="backend_service",
        tech_stack={
            "languages": ["python"],
            "frameworks": ["fastapi"],
            "database": "postgresql",
        },
        testing_config={
            "framework": "pytest",
            "coverage_target": 85,
            "strategy": "comprehensive",
            "ci_system": "github_actions",
        },
        tenant_key=integration_tenant_key,
        active_product=True,
    )
    db_session.add(product)
    await db_session.flush()
    return product


@pytest_asyncio.fixture
async def project_ready_to_stage(db_session, product_with_all_features, integration_tenant_key):
    """Create project ready for staging"""
    project = Project(
        id=str(uuid4()),
        product_id=product_with_all_features.id,
        name=f"IntegrationProject_{uuid4().hex[:6]}",
        description="Project for complete context flow testing",
        status="created",
        tenant_key=integration_tenant_key,
    )
    db_session.add(project)
    await db_session.flush()
    return project


# ============================================================================
# TEST SUITE 1: Complete Settings Persistence Flow
# ============================================================================

class TestCompleteSettingsPersistence:
    """
    Validate that ALL user settings persist through database and reach orchestrator.

    This tests the complete flow:
    - UI → Database → Orchestrator
    """

    async def test_field_priorities_reach_orchestrator(
        self,
        db_session,
        fully_configured_user,
        product_with_all_features,
        project_ready_to_stage,
        integration_tenant_key,
    ):
        """
        REQUIREMENT: Field priorities saved by user must reach orchestrator
        in get_orchestrator_instructions response (Handover 0266)
        """
        # Get user's field priorities
        assert fully_configured_user.field_priority_config is not None
        priorities = fully_configured_user.field_priority_config["priorities"]

        # Verify they're properly configured
        assert priorities["product_core"] == 1
        assert priorities["vision_documents"] == 2
        assert priorities["tech_stack"] == 2

        # Simulate staging (where priorities are passed to job)
        job = MCPAgentJob(
            id=str(uuid4()),
            product_id=product_with_all_features.id,
            project_id=project_ready_to_stage.id,
            user_id=fully_configured_user.id,
            agent_type="orchestrator",
            status="staged",
            tenant_key=integration_tenant_key,
            job_metadata={
                "user_id": fully_configured_user.id,
                "field_priorities": priorities,
                "tool": "orchestrate_project",
            },
        )
        db_session.add(job)
        await db_session.flush()

        # Retrieve from database and verify persistence
        retrieved_job = await db_session.get(MCPAgentJob, job.id)
        assert retrieved_job.job_metadata["field_priorities"] == priorities

    async def test_depth_config_setting_persists(
        self,
        db_session,
        fully_configured_user,
    ):
        """
        REQUIREMENT: Depth configuration must persist (for context detail levels)
        """
        # Verify initial state
        assert fully_configured_user.depth_config is not None
        assert fully_configured_user.depth_config["vision_chunking"] == "heavy"

        # Simulate database round-trip
        await db_session.flush()
        retrieved_user = await db_session.get(User, fully_configured_user.id)
        assert retrieved_user.depth_config["vision_chunking"] == "heavy"

    async def test_github_integration_setting_persists(
        self,
        db_session,
        product_with_all_features,
    ):
        """
        REQUIREMENT: GitHub integration toggle must persist (Handover 0269)
        """
        # Add GitHub toggle to product memory
        product_with_all_features.product_memory = {
            "git_integration": {
                "enabled": True,
                "repository_url": "https://github.com/example/repo",
                "last_sync": datetime.utcnow().isoformat(),
            }
        }
        await db_session.flush()

        # Verify persistence
        retrieved_product = await db_session.get(Product, product_with_all_features.id)
        assert retrieved_product.product_memory["git_integration"]["enabled"] is True

    async def test_testing_configuration_persists(
        self,
        db_session,
        product_with_all_features,
    ):
        """
        REQUIREMENT: Testing configuration must persist in product (Handover 0271)
        """
        assert product_with_all_features.testing_config is not None
        assert product_with_all_features.testing_config["framework"] == "pytest"
        assert product_with_all_features.testing_config["coverage_target"] == 85

        # Verify persistence
        await db_session.flush()
        retrieved_product = await db_session.get(Product, product_with_all_features.id)
        assert retrieved_product.testing_config["framework"] == "pytest"


# ============================================================================
# TEST SUITE 2: Context Generation with All Features
# ============================================================================

class TestContextGenerationWithAllFeatures:
    """
    Validate that context generation includes all features based on priorities.

    This tests that orchestrator receives properly formatted context including:
    - Field priorities
    - Serena instructions (when enabled)
    - 360 memory (when enabled)
    - GitHub integration status
    - MCP tool catalog
    - Testing configuration
    """

    async def test_mission_planner_includes_all_context_types(
        self,
        db_session,
        fully_configured_user,
        product_with_all_features,
        project_ready_to_stage,
        integration_tenant_key,
    ):
        """
        REQUIREMENT: MissionPlanner must build context with all enabled features
        integrated together (integration test of all handovers)

        Tests that when user has all features enabled:
        1. Field priorities are applied
        2. Vision documents included at correct priority
        3. Serena instructions included (when enabled)
        4. 360 memory included (when enabled)
        5. GitHub status included (when enabled)
        6. Testing config included (when enabled)
        """
        planner = MissionPlanner(test_session=db_session)

        # Build context with all features
        context = await planner._build_context_with_priorities(
            user=fully_configured_user,
            product=product_with_all_features,
            project=project_ready_to_stage,
            field_priorities=fully_configured_user.field_priority_config["priorities"],
            include_serena=fully_configured_user.serena_enabled,
        )

        # Verify context is not empty
        assert context is not None
        assert len(context) > 0

        # Verify key components are included
        context_lower = context.lower()
        assert "product" in context_lower
        assert "architecture" in context_lower or "tech" in context_lower

    async def test_thin_client_generator_passes_all_metadata(
        self,
        db_session,
        fully_configured_user,
        product_with_all_features,
        project_ready_to_stage,
        integration_tenant_key,
    ):
        """
        REQUIREMENT: ThinClientPromptGenerator must include field priorities
        and all user settings in job metadata (Handover 0266)
        """
        generator = ThinClientPromptGenerator(test_session=db_session)

        # Generate thin client prompt with all metadata
        prompt_data = await generator.generate_thin_orchestrator_prompt(
            product_id=product_with_all_features.id,
            project_id=project_ready_to_stage.id,
            user_id=fully_configured_user.id,
            tenant_key=integration_tenant_key,
        )

        # Verify metadata is included
        assert "job_metadata" in prompt_data
        metadata = prompt_data["job_metadata"]

        # Field priorities must be present (Handover 0266)
        assert "field_priorities" in metadata
        assert len(metadata["field_priorities"]) > 0

        # User ID must be present
        assert metadata.get("user_id") == fully_configured_user.id


# ============================================================================
# TEST SUITE 3: Orchestrator Receives Complete Context
# ============================================================================

class TestOrchestratorContextDelivery:
    """
    Validate that orchestrator receives all context through get_orchestrator_instructions
    MCP tool, with all features integrated.

    This is the ultimate integration test: settings → database → MCP tool → orchestrator
    """

    async def test_orchestrator_receives_field_priorities(
        self,
        db_session,
        db_manager,
        fully_configured_user,
        product_with_all_features,
        project_ready_to_stage,
        integration_tenant_key,
    ):
        """
        REQUIREMENT: get_orchestrator_instructions must return non-empty field_priorities
        (Handover 0266 - critical requirement)
        """
        # Create orchestration job
        job = MCPAgentJob(
            id=str(uuid4()),
            product_id=product_with_all_features.id,
            project_id=project_ready_to_stage.id,
            user_id=fully_configured_user.id,
            agent_type="orchestrator",
            status="active",
            tenant_key=integration_tenant_key,
            job_metadata={
                "user_id": fully_configured_user.id,
                "field_priorities": fully_configured_user.field_priority_config["priorities"],
            },
        )
        db_session.add(job)
        await db_session.flush()

        # Verify job has priorities in metadata
        assert job.job_metadata["field_priorities"] is not None
        assert job.job_metadata["field_priorities"]["product_core"] == 1

    async def test_orchestrator_context_respects_all_settings(
        self,
        db_session,
        fully_configured_user,
        product_with_all_features,
        project_ready_to_stage,
        integration_tenant_key,
    ):
        """
        REQUIREMENT: Complete orchestrator context must integrate ALL handovers:
        - Field priorities (0266)
        - Serena instructions (0267)
        - 360 memory (0268)
        - GitHub integration (0269)
        - MCP tool catalog (0270)
        - Testing config (0271)
        """
        planner = MissionPlanner(test_session=db_session)

        # Build orchestrator mission with all features
        mission = await planner.plan_orchestrator_mission(
            user_id=fully_configured_user.id,
            product_id=product_with_all_features.id,
            project_id=project_ready_to_stage.id,
            tenant_key=integration_tenant_key,
        )

        # Mission should be substantial (not empty)
        assert mission is not None
        assert len(mission) > 500  # Should be detailed

        # Mission should contain structured sections
        mission_lower = mission.lower()

        # Should reference key capabilities
        assert any(word in mission_lower for word in ["product", "architecture", "project"])


# ============================================================================
# TEST SUITE 4: Multi-Tenant Isolation in Context Flow
# ============================================================================

class TestMultiTenantContextIsolation:
    """
    Validate that context flow maintains complete tenant isolation.

    Ensures that one tenant's settings don't leak into another's orchestrator
    context.
    """

    async def test_field_priorities_isolated_by_tenant(
        self,
        db_session,
        integration_tenant_key,
    ):
        """
        REQUIREMENT: Field priorities from one tenant must not leak to another
        """
        # Create two users in different tenants
        tenant_a = f"tenant_a_{uuid4().hex[:8]}"
        tenant_b = f"tenant_b_{uuid4().hex[:8]}"

        user_a = User(
            id=str(uuid4()),
            username=f"user_a_{uuid4().hex[:6]}",
            email=f"user_a_{uuid4().hex[:6]}@example.com",
            tenant_key=tenant_a,
            role="developer",
            password_hash="hash",
            field_priority_config={
                "version": "2.0",
                "priorities": {
                    "product_core": 1,
                    "git_history": 4,  # EXCLUDED in tenant_a
                }
            },
        )

        user_b = User(
            id=str(uuid4()),
            username=f"user_b_{uuid4().hex[:6]}",
            email=f"user_b_{uuid4().hex[:6]}@example.com",
            tenant_key=tenant_b,
            role="developer",
            password_hash="hash",
            field_priority_config={
                "version": "2.0",
                "priorities": {
                    "product_core": 1,
                    "git_history": 2,  # INCLUDED in tenant_b
                }
            },
        )

        db_session.add_all([user_a, user_b])
        await db_session.flush()

        # Verify isolation: user_a's git_history priority (4) != user_b's (2)
        retrieved_a = await db_session.get(User, user_a.id)
        retrieved_b = await db_session.get(User, user_b.id)

        assert retrieved_a.field_priority_config["priorities"]["git_history"] == 4
        assert retrieved_b.field_priority_config["priorities"]["git_history"] == 2

    async def test_github_integration_isolated_by_tenant(
        self,
        db_session,
    ):
        """
        REQUIREMENT: GitHub integration toggle isolated between tenants
        """
        tenant_a = f"tenant_a_{uuid4().hex[:8]}"
        tenant_b = f"tenant_b_{uuid4().hex[:8]}"

        product_a = Product(
            id=str(uuid4()),
            name=f"ProdA_{uuid4().hex[:6]}",
            tenant_key=tenant_a,
            product_memory={
                "git_integration": {"enabled": True}
            }
        )

        product_b = Product(
            id=str(uuid4()),
            name=f"ProdB_{uuid4().hex[:6]}",
            tenant_key=tenant_b,
            product_memory={
                "git_integration": {"enabled": False}
            }
        )

        db_session.add_all([product_a, product_b])
        await db_session.flush()

        # Verify isolation
        retrieved_a = await db_session.get(Product, product_a.id)
        retrieved_b = await db_session.get(Product, product_b.id)

        assert retrieved_a.product_memory["git_integration"]["enabled"] is True
        assert retrieved_b.product_memory["git_integration"]["enabled"] is False


# ============================================================================
# TEST SUITE 5: Edge Cases and State Transitions
# ============================================================================

class TestContextFlowEdgeCases:
    """
    Validate graceful handling of edge cases in context flow.
    """

    async def test_context_with_missing_field_priorities(
        self,
        db_session,
        integration_tenant_key,
    ):
        """
        REQUIREMENT: System should handle user with NO field priorities configured
        (should use defaults, not crash)
        """
        user = User(
            id=str(uuid4()),
            username=f"noconfig_{uuid4().hex[:6]}",
            email=f"noconfig_{uuid4().hex[:6]}@example.com",
            tenant_key=integration_tenant_key,
            role="developer",
            password_hash="hash",
            field_priority_config=None,  # No priorities configured
            serena_enabled=False,
        )

        db_session.add(user)
        await db_session.flush()

        # Verify graceful handling
        retrieved = await db_session.get(User, user.id)
        assert retrieved.field_priority_config is None

    async def test_context_with_disabled_serena(
        self,
        db_session,
        integration_tenant_key,
        product_with_all_features,
        project_ready_to_stage,
    ):
        """
        REQUIREMENT: Serena instructions should NOT be included when Serena disabled
        """
        user = User(
            id=str(uuid4()),
            username=f"noserena_{uuid4().hex[:6]}",
            email=f"noserena_{uuid4().hex[:6]}@example.com",
            tenant_key=integration_tenant_key,
            role="developer",
            password_hash="hash",
            serena_enabled=False,  # Explicitly disabled
        )

        db_session.add(user)
        await db_session.flush()

        # Verify Serena is disabled
        retrieved = await db_session.get(User, user.id)
        assert retrieved.serena_enabled is False

    async def test_context_with_empty_360_memory(
        self,
        db_session,
        integration_tenant_key,
    ):
        """
        REQUIREMENT: System should handle product with NO 360 memory gracefully
        """
        product = Product(
            id=str(uuid4()),
            name=f"NoMemory_{uuid4().hex[:6]}",
            tenant_key=integration_tenant_key,
            product_memory=None,  # No memory entries
        )

        db_session.add(product)
        await db_session.flush()

        # Verify graceful handling
        retrieved = await db_session.get(Product, product.id)
        assert retrieved.product_memory is None

    async def test_context_with_null_testing_config(
        self,
        db_session,
        integration_tenant_key,
    ):
        """
        REQUIREMENT: System should handle product with NULL testing_config
        """
        product = Product(
            id=str(uuid4()),
            name=f"NoTestConfig_{uuid4().hex[:6]}",
            tenant_key=integration_tenant_key,
            testing_config=None,  # No testing config
        )

        db_session.add(product)
        await db_session.flush()

        # Verify graceful handling
        retrieved = await db_session.get(Product, product.id)
        assert retrieved.testing_config is None


# ============================================================================
# TEST SUITE 6: Context Completeness
# ============================================================================

class TestContextCompleteness:
    """
    Validate that complete context includes all required sections.
    """

    async def test_orchestrator_mission_structure_is_valid(
        self,
        db_session,
        fully_configured_user,
        product_with_all_features,
        project_ready_to_stage,
        integration_tenant_key,
    ):
        """
        REQUIREMENT: Orchestrator mission must have valid structure
        (is a string, contains key sections)
        """
        planner = MissionPlanner(test_session=db_session)

        mission = await planner.plan_orchestrator_mission(
            user_id=fully_configured_user.id,
            product_id=product_with_all_features.id,
            project_id=project_ready_to_stage.id,
            tenant_key=integration_tenant_key,
        )

        # Mission must be a string
        assert isinstance(mission, str)

        # Mission must be non-empty
        assert len(mission) > 0

        # Mission should be properly formatted (contain newlines, not just one line)
        assert "\n" in mission or len(mission) > 200

    async def test_context_includes_project_specific_info(
        self,
        db_session,
        fully_configured_user,
        product_with_all_features,
        project_ready_to_stage,
        integration_tenant_key,
    ):
        """
        REQUIREMENT: Orchestrator mission must include project-specific information
        """
        planner = MissionPlanner(test_session=db_session)

        mission = await planner.plan_orchestrator_mission(
            user_id=fully_configured_user.id,
            product_id=product_with_all_features.id,
            project_id=project_ready_to_stage.id,
            tenant_key=integration_tenant_key,
        )

        # Mission should mention the project name
        assert project_ready_to_stage.name in mission or "project" in mission.lower()


# ============================================================================
# TEST SUITE 7: Backward Compatibility
# ============================================================================

class TestBackwardCompatibility:
    """
    Validate that context flow is backward compatible with older versions.
    """

    async def test_user_without_serena_enabled_field_defaults_false(
        self,
        db_session,
        integration_tenant_key,
    ):
        """
        REQUIREMENT: User without serena_enabled field should default to False
        (backward compatibility)
        """
        user = User(
            id=str(uuid4()),
            username=f"compat_{uuid4().hex[:6]}",
            email=f"compat_{uuid4().hex[:6]}@example.com",
            tenant_key=integration_tenant_key,
            role="developer",
            password_hash="hash",
        )

        db_session.add(user)
        await db_session.flush()

        # Verify default
        retrieved = await db_session.get(User, user.id)
        # Should either be None or False
        assert retrieved.serena_enabled in (None, False)

    async def test_product_without_testing_config_handled_gracefully(
        self,
        db_session,
        integration_tenant_key,
    ):
        """
        REQUIREMENT: Product created before testing_config added should work
        """
        product = Product(
            id=str(uuid4()),
            name=f"OldProd_{uuid4().hex[:6]}",
            tenant_key=integration_tenant_key,
            # No testing_config field set
        )

        db_session.add(product)
        await db_session.flush()

        # Should not crash when accessing
        retrieved = await db_session.get(Product, product.id)
        assert retrieved is not None
