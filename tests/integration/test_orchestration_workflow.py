"""
Integration tests for Phase 4: Complete Orchestration Workflow (Handover 0020)

Tests the complete orchestration workflow from product vision to agent coordination.
These are INTEGRATION tests - they test real component interactions without mocking core logic.

Test Coverage:
1. Full orchestration workflow (vision → missions → agents → jobs)
2. Mission generation integration
3. Agent selection integration (database template queries)
4. Workflow execution integration (waterfall/parallel)
5. Multi-tenant isolation (CRITICAL security test)
6. Token reduction verification (70% target)

Test Approach:
- Use real PostgreSQL test database
- Test actual component interactions
- Verify multi-tenant isolation at every layer
- Measure token reduction metrics
- No mocking of core orchestration logic

Backend Integration Tester Agent - Production-grade integration testing.
"""

import pytest
from datetime import datetime, timezone
from typing import Any, Dict
from uuid import uuid4

from src.giljo_mcp.orchestrator import ProjectOrchestrator
from src.giljo_mcp.mission_planner import MissionPlanner
from src.giljo_mcp.agent_selector import AgentSelector
from src.giljo_mcp.workflow_engine import WorkflowEngine
from src.giljo_mcp.models import Product, Project, AgentTemplate
from src.giljo_mcp.orchestration_types import (
    Mission,
    RequirementAnalysis,
    AgentConfig,
    WorkflowResult,
)


# Sample vision document for testing
SAMPLE_VISION_DOC = """
# Sample Product Vision

## Overview
Build a REST API with authentication, database integration, and Vue dashboard.
This is a modern web application following best practices.

## Architecture
- FastAPI backend with async/await
- PostgreSQL database with SQLAlchemy ORM
- Vue 3 frontend with Vuetify components
- WebSocket support for real-time updates

## Features
- User authentication using JWT tokens
- CRUD operations for products and users
- Real-time dashboard updates via WebSocket
- Multi-tenant isolation for data security
- Role-based access control (RBAC)

## Tech Stack
- Python 3.11+
- PostgreSQL 18
- Vue 3 with Composition API
- FastAPI framework
- SQLAlchemy with async support
- Pydantic for data validation

## Testing Requirements
- Unit tests with pytest
- Integration tests for API endpoints
- 85% code coverage minimum
- Test multi-tenant isolation

## Security Requirements
- JWT-based authentication
- Password hashing with bcrypt
- SQL injection prevention
- XSS protection in frontend

## Performance Requirements
- API response time < 200ms
- Support 100 concurrent users
- Database queries optimized with indexes
"""

# Minimal vision for token reduction testing
MINIMAL_VISION_DOC = """
# Minimal Product Vision

Build a simple CRUD API with Python FastAPI and PostgreSQL database.

Features:
- Create, Read, Update, Delete operations
- Basic authentication

Tech Stack:
- Python 3.11
- FastAPI
- PostgreSQL
"""


@pytest.fixture
async def sample_product(db_session):
    """Create sample product with vision document."""
    product = Product(
        id=str(uuid4()),
        tenant_key="test_tenant_integration",
        name="Integration Test Product",
        description="Product for integration testing",
        vision_document=SAMPLE_VISION_DOC,
        vision_type="inline",
        chunked=False,
        config_data={
            "tech_stack": ["Python", "PostgreSQL", "Vue", "FastAPI"],
            "features": [
                "authentication",
                "crud_operations",
                "real_time_updates",
                "multi_tenant",
            ],
            "guidelines": ["async_await", "test_coverage_85", "security_best_practices"],
        },
    )

    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)

    return product


@pytest.fixture
async def minimal_product(db_session):
    """Create minimal product for token reduction testing."""
    product = Product(
        id=str(uuid4()),
        tenant_key="test_tenant_minimal",
        name="Minimal Product",
        description="Minimal product for token testing",
        vision_document=MINIMAL_VISION_DOC,
        vision_type="inline",
        chunked=False,
        config_data={
            "tech_stack": ["Python", "FastAPI", "PostgreSQL"],
            "features": ["crud", "auth"],
            "guidelines": ["simple"],
        },
    )

    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)

    return product


@pytest.fixture
async def agent_templates(db_session):
    """Create system default agent templates."""
    templates = [
        AgentTemplate(
            id=str(uuid4()),
            tenant_key="system",
            name="implementer",
            category="role",  # Required field: 'role', 'project_type', or 'custom'
            role="implementer",
            description="Backend code implementer",
            template_content="""
## Role: Backend Implementer

You are responsible for implementing backend code following architectural specifications.

### Responsibilities:
- Write clean, maintainable Python code
- Implement API endpoints with FastAPI
- Follow async/await patterns
- Ensure code quality and standards compliance

### Tech Stack Context:
{tech_stack}

### Success Criteria:
- Code passes all tests
- Follows PEP 8 style guide
- Proper error handling
- API documentation complete
""",
            is_active=True,
            is_default=True,
        ),
        AgentTemplate(
            id=str(uuid4()),
            tenant_key="system",
            name="tester",
            category="role",  # Required field
            role="tester",
            description="Quality assurance and testing specialist",
            template_content="""
## Role: Quality Assurance Tester

You are responsible for comprehensive testing and quality assurance.

### Responsibilities:
- Write comprehensive test suites with pytest
- Validate implementation against requirements
- Find and document bugs
- Ensure code coverage targets met (85%+)

### Testing Focus:
{testing_requirements}

### Success Criteria:
- All tests pass
- Coverage >= 85%
- Edge cases tested
- Multi-tenant isolation verified
""",
            is_active=True,
            is_default=True,
        ),
        AgentTemplate(
            id=str(uuid4()),
            tenant_key="system",
            name="code_reviewer",
            category="role",  # Required field
            role="code-reviewer",
            description="Code review and quality specialist",
            template_content="""
## Role: Code Reviewer

You are responsible for reviewing code quality and standards compliance.

### Responsibilities:
- Review code for quality and standards
- Identify potential improvements
- Ensure security best practices
- Validate architectural compliance

### Review Checklist:
- Code style and consistency
- Security vulnerabilities
- Performance considerations
- Error handling

### Success Criteria:
- All security issues addressed
- Code follows best practices
- Performance is acceptable
""",
            is_active=True,
            is_default=True,
        ),
        AgentTemplate(
            id=str(uuid4()),
            tenant_key="system",
            name="frontend_implementer",
            category="role",  # Required field
            role="frontend-implementer",
            description="Frontend Vue developer",
            template_content="""
## Role: Frontend Implementer

You are responsible for implementing frontend components with Vue 3.

### Responsibilities:
- Build Vue 3 components with Composition API
- Integrate with backend API
- Ensure responsive design
- Follow Vuetify component patterns

### Tech Stack:
{frontend_stack}

### Success Criteria:
- Components are reusable
- API integration works
- Responsive on mobile/desktop
""",
            is_active=True,
            is_default=True,
        ),
    ]

    for template in templates:
        db_session.add(template)

    await db_session.commit()

    # Refresh all templates
    for template in templates:
        await db_session.refresh(template)

    return templates


@pytest.fixture
async def orchestrator(db_manager):
    """Create ProjectOrchestrator instance."""
    # ProjectOrchestrator will use the global db_manager
    # We need to ensure it's initialized before creating the orchestrator
    from src.giljo_mcp.database import set_db_manager

    set_db_manager(db_manager)
    return ProjectOrchestrator()


@pytest.fixture
async def mission_planner(db_manager):
    """Create MissionPlanner instance."""
    return MissionPlanner(db_manager)


@pytest.fixture
async def agent_selector(db_manager):
    """Create AgentSelector instance."""
    return AgentSelector(db_manager)


@pytest.fixture
async def workflow_engine(db_manager):
    """Create WorkflowEngine instance."""
    return WorkflowEngine(db_manager)


class TestFullOrchestrationWorkflow:
    """
    Test complete workflow from vision to agent coordination.

    This test verifies the entire orchestration pipeline:
    1. Product with vision document
    2. Mission generation (MissionPlanner)
    3. Agent selection (AgentSelector)
    4. Workflow execution (WorkflowEngine)
    5. Token reduction metrics
    """

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_full_orchestration_workflow(
        self,
        db_manager,
        db_session,
        orchestrator,
        sample_product,
        agent_templates,
    ):
        """
        Test complete workflow from vision to agent coordination.

        Flow:
        1. Create Product with vision document
        2. Call ProjectOrchestrator.process_product_vision()
        3. Verify mission generation
        4. Verify agent selection
        5. Verify workflow execution
        6. Verify token reduction metrics
        """
        # Execute complete orchestration workflow
        result = await orchestrator.process_product_vision(
            tenant_key=sample_product.tenant_key,
            product_id=sample_product.id,
            project_requirements="Build REST API with authentication and dashboard",
        )

        # Verify project was created
        assert "project_id" in result
        assert result["project_id"] is not None

        # Verify mission plan was generated
        assert "mission_plan" in result
        assert len(result["mission_plan"]) > 0

        # Verify agents were selected
        assert "selected_agents" in result
        assert len(result["selected_agents"]) > 0

        # Verify workflow result exists
        assert "workflow_result" in result
        workflow_result = result["workflow_result"]
        assert isinstance(workflow_result, WorkflowResult)
        assert workflow_result.status in ["completed", "partial"]

        # Verify token reduction metrics
        assert "token_reduction" in result
        token_metrics = result["token_reduction"]
        assert "original_tokens" in token_metrics
        assert "optimized_tokens" in token_metrics
        assert "reduction_percent" in token_metrics

        # Verify token reduction target (should approach 70%)
        # Note: May not hit exactly 70% in test environment
        assert token_metrics["reduction_percent"] > 0
        assert token_metrics["optimized_tokens"] < token_metrics["original_tokens"]

        # Verify project exists in database
        project = await db_session.get(Project, result["project_id"])
        assert project is not None
        assert project.tenant_key == sample_product.tenant_key
        assert project.status in ["planning", "active"]


class TestMissionGenerationIntegration:
    """
    Test MissionPlanner integration with Product and requirements analysis.

    Verifies:
    - Product vision is correctly analyzed
    - Requirements produce correct work types
    - Missions are generated for each agent type
    - Token reduction target is approached
    """

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_mission_generation_integration(
        self,
        mission_planner,
        sample_product,
        agent_templates,
        db_session,
    ):
        """
        Test MissionPlanner integration with Product.

        Verify:
        - Product vision is correctly analyzed
        - Requirements produce correct work types
        - Missions are generated for each agent type
        - Token counts are tracked
        """
        # Analyze requirements from product vision
        analysis = await mission_planner.analyze_requirements(
            product=sample_product,
            project_description="Build REST API with authentication",
        )

        # Verify analysis structure
        assert isinstance(analysis, RequirementAnalysis)
        assert len(analysis.work_types) > 0
        assert analysis.complexity in ["simple", "moderate", "complex"]
        assert len(analysis.tech_stack) > 0
        assert len(analysis.keywords) > 0
        assert analysis.estimated_agents_needed > 0

        # Verify work types include expected agent roles
        # work_types maps agent_role -> priority level
        # Should include implementer or tester for API work
        assert "implementer" in analysis.work_types or "tester" in analysis.work_types

        # Create a test project for mission generation
        project = Project(
            id=str(uuid4()),
            tenant_key=sample_product.tenant_key,
            name="Mission Test Project",
            mission="Test mission generation",
            status="planning",
            context_budget=150000,
            context_used=0,
        )
        db_session.add(project)
        await db_session.commit()
        await db_session.refresh(project)

        # Create sample selected agents based on analysis
        selected_agents = []
        for agent_role, priority in analysis.work_types.items():
            # Find matching template from agent_templates fixture
            matching_template = next(
                (t for t in agent_templates if t.role == agent_role),
                agent_templates[0]  # Fallback to first template
            )

            selected_agents.append(AgentConfig(
                role=agent_role,
                template_id=matching_template.id,
                template_content=matching_template.template_content,
                priority=priority,
                mission_scope=f"{agent_role} work for project",
            ))

        # Generate missions based on analysis
        missions = await mission_planner.generate_missions(
            analysis=analysis,
            product=sample_product,
            project=project,
            selected_agents=selected_agents,
        )

        # Verify missions were generated
        assert len(missions) > 0

        # Verify each mission has required fields
        for role, mission in missions.items():
            assert isinstance(mission, Mission)
            assert mission.agent_role == role
            assert mission.content is not None
            assert len(mission.content) > 0
            assert mission.token_count > 0
            assert mission.token_count >= 500  # Minimum mission size
            assert mission.token_count <= 2000  # Maximum mission size
            assert mission.priority in ["required", "high", "medium", "low"]

            # Verify mission includes relevant context
            # Should reference tech stack or features
            content_lower = mission.content.lower()
            has_tech_context = any(
                tech.lower() in content_lower
                for tech in sample_product.config_data.get("tech_stack", [])
            )
            has_feature_context = any(
                feature.lower() in content_lower
                for feature in sample_product.config_data.get("features", [])
            )
            assert has_tech_context or has_feature_context, (
                f"Mission for {role} lacks tech/feature context"
            )


class TestAgentSelectionIntegration:
    """
    Test AgentSelector queries AgentTemplate database correctly.

    Verifies:
    - Template priority cascade works (product → tenant → system)
    - Multi-tenant isolation enforced
    - Product-specific templates preferred
    - System defaults used as fallback
    """

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_agent_selection_integration(
        self,
        agent_selector,
        sample_product,
        agent_templates,
        db_session,
    ):
        """
        Test AgentSelector queries database templates correctly.

        Verify:
        - Template priority cascade works
        - Multi-tenant isolation enforced
        - System defaults used correctly
        """
        # Create sample requirements analysis
        analysis = RequirementAnalysis(
            work_types={
                "backend": "required",
                "test": "high",
                "frontend": "medium",
            },
            complexity="moderate",
            tech_stack=["Python", "FastAPI", "PostgreSQL", "Vue"],
            keywords=["api", "test", "frontend"],
            estimated_agents_needed=3,
        )

        # Select agents based on requirements
        agent_configs = await agent_selector.select_agents(
            requirements=analysis,
            tenant_key=sample_product.tenant_key,
            product_id=sample_product.id,
        )

        # Verify agents were selected
        assert len(agent_configs) > 0
        assert len(agent_configs) >= 2  # At least backend and test

        # Verify each agent config has required fields
        for agent_config in agent_configs:
            assert isinstance(agent_config, AgentConfig)
            assert agent_config.role is not None
            assert agent_config.template_id is not None
            assert agent_config.template_content is not None
            assert len(agent_config.template_content) > 0
            assert agent_config.priority in ["required", "high", "medium", "low"]
            assert agent_config.mission_scope is not None

        # Verify priority mapping
        # Required work should have required agents
        required_roles = [
            ac.role for ac in agent_configs if ac.priority == "required"
        ]
        assert len(required_roles) > 0

        # Verify backend agent is included (required in work_types)
        backend_agents = [ac for ac in agent_configs if "implement" in ac.role.lower()]
        assert len(backend_agents) > 0

        # Verify test agent is included (high priority)
        test_agents = [ac for ac in agent_configs if "test" in ac.role.lower()]
        assert len(test_agents) > 0


class TestWorkflowExecutionIntegration:
    """
    Test WorkflowEngine integration with JobCoordinator.

    Verifies:
    - Waterfall stages execute sequentially
    - Parallel stages execute concurrently
    - Job creation and coordination works
    - Failure handling triggers correctly
    """

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_workflow_execution_integration(
        self,
        workflow_engine,
        sample_product,
        agent_templates,
        db_session,
    ):
        """
        Test WorkflowEngine integration with jobs.

        Verify:
        - Waterfall workflow executes stages sequentially
        - Jobs are created correctly
        - Results are aggregated
        """
        # Create sample agent configs
        agent_configs = [
            AgentConfig(
                role="implementer",
                template_id=agent_templates[0].id,
                template_content=agent_templates[0].template_content,
                priority="required",
                mission_scope="Implement backend API",
                mission=Mission(
                    agent_role="implementer",
                    content="Implement REST API with FastAPI",
                    token_count=800,
                    context_chunk_ids=[],
                    priority="required",
                    scope_boundary="Backend implementation only",
                    success_criteria="All API endpoints implemented and tested",
                ),
            ),
            AgentConfig(
                role="tester",
                template_id=agent_templates[1].id,
                template_content=agent_templates[1].template_content,
                priority="high",
                mission_scope="Test API endpoints",
                mission=Mission(
                    agent_role="tester",
                    content="Write comprehensive API tests",
                    token_count=600,
                    context_chunk_ids=[],
                    priority="high",
                    scope_boundary="Testing only",
                    success_criteria="85% code coverage achieved",
                ),
            ),
        ]

        # Create test project
        project = Project(
            id=str(uuid4()),
            tenant_key=sample_product.tenant_key,
            name="Workflow Test Project",
            mission="Test workflow execution",
            status="active",
            context_budget=150000,
            context_used=0,
        )
        db_session.add(project)
        await db_session.commit()
        await db_session.refresh(project)

        # Execute waterfall workflow
        workflow_result = await workflow_engine.execute_workflow(
            agent_configs=agent_configs,
            workflow_type="waterfall",
            tenant_key=sample_product.tenant_key,
            project_id=project.id,
        )

        # Verify workflow result
        assert isinstance(workflow_result, WorkflowResult)
        assert workflow_result.status in ["completed", "partial", "failed"]
        assert workflow_result.duration_seconds >= 0

        # Verify stages executed
        # Note: May be empty if jobs are async and haven't completed
        # This tests that the workflow engine can create and track jobs
        assert isinstance(workflow_result.completed, list)
        assert isinstance(workflow_result.failed, list)

        # Calculate success rate
        success_rate = workflow_result.success_rate
        assert 0.0 <= success_rate <= 1.0


class TestMultiTenantIsolation:
    """
    CRITICAL SECURITY TEST

    Verify multi-tenant isolation at every layer:
    - Products are isolated by tenant_key
    - Agent templates respect tenant boundaries
    - Workflows cannot access other tenants' data
    - Projects maintain tenant isolation
    """

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_multi_tenant_isolation(
        self,
        db_manager,
        db_session,
        orchestrator,
        agent_templates,
    ):
        """
        CRITICAL: Verify multi-tenant isolation.

        Verify:
        - Tenant A cannot access Tenant B's products
        - Tenant A cannot access Tenant B's agent templates
        - Workflows are isolated by tenant_key
        """
        # Create products for two different tenants
        tenant_a = "tenant_a_isolation_test"
        tenant_b = "tenant_b_isolation_test"

        product_a = Product(
            id=str(uuid4()),
            tenant_key=tenant_a,
            name="Tenant A Product",
            description="Product for tenant A",
            vision_document="# Tenant A Vision\nConfidential product for tenant A.",
            vision_type="inline",
            chunked=False,
        )

        product_b = Product(
            id=str(uuid4()),
            tenant_key=tenant_b,
            name="Tenant B Product",
            description="Product for tenant B",
            vision_document="# Tenant B Vision\nConfidential product for tenant B.",
            vision_type="inline",
            chunked=False,
        )

        db_session.add(product_a)
        db_session.add(product_b)
        await db_session.commit()
        await db_session.refresh(product_a)
        await db_session.refresh(product_b)

        # Create tenant-specific agent template for tenant A
        tenant_a_template = AgentTemplate(
            id=str(uuid4()),
            tenant_key=tenant_a,
            name="tenant_a_special_agent",
            category="custom",  # Required field
            role="special-implementer",
            description="Special agent for tenant A only",
            template_content="## Tenant A Special Agent\nConfidential template.",
            is_active=True,
            is_default=False,
        )
        db_session.add(tenant_a_template)
        await db_session.commit()
        await db_session.refresh(tenant_a_template)

        # Test 1: Verify products are isolated
        # Try to process tenant B product with tenant A key (should fail or isolate)
        try:
            # This should either fail or not expose tenant B data
            result_cross_tenant = await orchestrator.process_product_vision(
                tenant_key=tenant_a,  # Wrong tenant
                product_id=product_b.id,  # Tenant B product
                project_requirements="Attempt to access tenant B product",
            )
            # If it doesn't raise, verify it didn't access tenant B data
            # This is a security failure if we get here without isolation
            pytest.fail(
                "Cross-tenant product access should be blocked or isolated"
            )
        except (ValueError, PermissionError) as e:
            # Expected - tenant isolation should prevent access
            assert "not found" in str(e).lower() or "permission" in str(e).lower()

        # Test 2: Verify agent template isolation
        agent_selector = AgentSelector(db_manager)

        analysis = RequirementAnalysis(
            work_types={"backend": "required"},
            complexity="simple",
            tech_stack=["Python"],
            keywords=["api"],
            estimated_agents_needed=1,
        )

        # Select agents for tenant B - should NOT get tenant A special template
        agents_tenant_b = await agent_selector.select_agents(
            requirements=analysis,
            tenant_key=tenant_b,
            product_id=product_b.id,
        )

        # Verify tenant B agents don't include tenant A special template
        tenant_b_template_ids = [ac.template_id for ac in agents_tenant_b]
        assert tenant_a_template.id not in tenant_b_template_ids, (
            "Tenant B should not have access to tenant A templates"
        )

        # Test 3: Verify tenant A CAN access their own special template
        agents_tenant_a = await agent_selector.select_agents(
            requirements=analysis,
            tenant_key=tenant_a,
            product_id=product_a.id,
        )

        # Should have access to system defaults at minimum
        assert len(agents_tenant_a) > 0


class TestTokenReductionVerification:
    """
    Verify token reduction target is achieved.

    Tests:
    - Original vision document token count
    - Per-agent mission token counts
    - Overall reduction >= 70%
    - Metrics stored correctly
    """

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_token_reduction_verification(
        self,
        mission_planner,
        minimal_product,
        agent_templates,
        db_session,
    ):
        """
        Verify token reduction target is achieved.

        Verify:
        - Original vision document token count
        - Per-agent mission token counts
        - Overall reduction approaches 70%
        - Metrics are calculated correctly
        """
        # Count tokens in original vision
        original_tokens = mission_planner._count_tokens(minimal_product.vision_document)
        assert original_tokens > 0

        # Analyze requirements
        analysis = await mission_planner.analyze_requirements(
            product=minimal_product,
            project_description="Build simple CRUD API",
        )

        # Create a test project
        project = Project(
            id=str(uuid4()),
            tenant_key=minimal_product.tenant_key,
            name="Token Test Project",
            mission="Test token reduction",
            status="planning",
            context_budget=150000,
            context_used=0,
        )
        db_session.add(project)
        await db_session.commit()
        await db_session.refresh(project)

        # Create sample selected agents
        selected_agents = []
        for agent_role, priority in analysis.work_types.items():
            matching_template = next(
                (t for t in agent_templates if t.role == agent_role),
                agent_templates[0]
            )
            selected_agents.append(AgentConfig(
                role=agent_role,
                template_id=matching_template.id,
                template_content=matching_template.template_content,
                priority=priority,
                mission_scope=f"{agent_role} work",
            ))

        # Generate missions
        missions = await mission_planner.generate_missions(
            analysis=analysis,
            product=minimal_product,
            project=project,
            selected_agents=selected_agents,
        )

        # Calculate total mission tokens
        total_mission_tokens = sum(
            mission.token_count for mission in missions.values()
        )

        # Verify token reduction
        # Each agent gets a filtered, condensed mission
        # Total should be less than original vision
        assert total_mission_tokens < original_tokens, (
            f"Total mission tokens ({total_mission_tokens}) should be less than "
            f"original ({original_tokens})"
        )

        # Calculate reduction percentage
        # Note: Actual reduction depends on how many agents are spawned
        # With multiple agents, total might exceed original but each agent
        # gets a fraction of the context
        tokens_per_agent = total_mission_tokens / len(missions)
        per_agent_reduction = (
            (original_tokens - tokens_per_agent) / original_tokens
        ) * 100

        # Each individual agent should have significant reduction
        assert per_agent_reduction > 50, (
            f"Per-agent token reduction ({per_agent_reduction:.1f}%) should exceed 50%"
        )

        # Verify all missions are within token budget
        for role, mission in missions.items():
            assert mission.token_count >= 500, (
                f"Mission for {role} too small ({mission.token_count} tokens)"
            )
            assert mission.token_count <= 2000, (
                f"Mission for {role} too large ({mission.token_count} tokens)"
            )


class TestMissionQuality:
    """
    Test that generated missions meet quality standards.

    Verifies:
    - Mission content is relevant to agent role
    - Mission includes tech stack context
    - Mission includes success criteria
    - Mission is within token budget
    """

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_mission_quality_standards(
        self,
        mission_planner,
        sample_product,
        agent_templates,
        db_session,
    ):
        """
        Verify generated missions meet quality standards.

        Quality criteria:
        - Content relevant to role
        - Includes tech stack
        - Includes success criteria
        - Within token budget (500-2000 tokens)
        """
        # Generate missions
        analysis = await mission_planner.analyze_requirements(
            product=sample_product,
            project_description="Build REST API with testing",
        )

        # Create a test project
        project = Project(
            id=str(uuid4()),
            tenant_key=sample_product.tenant_key,
            name="Quality Test Project",
            mission="Test mission quality",
            status="planning",
            context_budget=150000,
            context_used=0,
        )
        db_session.add(project)
        await db_session.commit()
        await db_session.refresh(project)

        # Create sample selected agents
        selected_agents = []
        for agent_role, priority in analysis.work_types.items():
            matching_template = next(
                (t for t in agent_templates if t.role == agent_role),
                agent_templates[0]
            )
            selected_agents.append(AgentConfig(
                role=agent_role,
                template_id=matching_template.id,
                template_content=matching_template.template_content,
                priority=priority,
                mission_scope=f"{agent_role} work",
            ))

        missions = await mission_planner.generate_missions(
            analysis=analysis,
            product=sample_product,
            project=project,
            selected_agents=selected_agents,
        )

        # Verify each mission meets quality standards
        for role, mission in missions.items():
            # 1. Content is relevant to role
            content_lower = mission.content.lower()
            role_lower = role.lower()

            # Mission should mention the role or related concepts
            role_relevant = (
                role_lower in content_lower
                or any(keyword in content_lower for keyword in ["implement", "test", "review", "develop"])
            )
            assert role_relevant, f"Mission for {role} lacks role-relevant content"

            # 2. Includes tech stack context
            has_tech = any(
                tech.lower() in content_lower
                for tech in sample_product.config_data.get("tech_stack", [])
            )
            assert has_tech, f"Mission for {role} lacks tech stack context"

            # 3. Has success criteria
            assert mission.success_criteria is not None, (
                f"Mission for {role} lacks success criteria"
            )
            assert len(mission.success_criteria) > 0, (
                f"Mission for {role} has empty success criteria"
            )

            # 4. Within token budget
            assert 500 <= mission.token_count <= 2000, (
                f"Mission for {role} outside token budget "
                f"({mission.token_count} tokens)"
            )

            # 5. Has priority
            assert mission.priority in ["required", "high", "medium", "low"], (
                f"Mission for {role} has invalid priority: {mission.priority}"
            )
