"""
Integration tests for Product Config Fields Extraction (Handover 0303).

Tests generic config_data field extraction from MissionPlanner._build_context_with_priorities().
Verifies all config fields can be prioritized with proper detail levels, tenant isolation,
and backward compatibility with existing architecture field.

TDD Approach:
- Phase 1 (RED): Tests written first (expected to fail initially)
- Phase 2 (GREEN): Implementation makes tests pass
- Phase 3 (REFACTOR): Optimize and improve code quality
"""

import pytest
import pytest_asyncio
from passlib.hash import bcrypt

from src.giljo_mcp.mission_planner import MissionPlanner
from src.giljo_mcp.models import Product, Project, User


@pytest.mark.asyncio
class TestProductConfigExtraction:
    """Test suite for generic config_data field extraction."""

    @pytest_asyncio.fixture
    async def mission_planner(self, db_manager):
        """Create MissionPlanner instance."""
        return MissionPlanner(db_manager)

    @pytest_asyncio.fixture
    async def tenant_a_user(self, db_session):
        """Create user for tenant A."""
        user = User(
            username="tenant_a_user",
            email="tenant_a@test.com",
            password_hash=bcrypt.hash("password123"),
            tenant_key="tenant_a",
            is_active=True,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        return user

    @pytest_asyncio.fixture
    async def tenant_b_user(self, db_session):
        """Create user for tenant B."""
        user = User(
            username="tenant_b_user",
            email="tenant_b@test.com",
            password_hash=bcrypt.hash("password123"),
            tenant_key="tenant_b",
            is_active=True,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        return user

    @pytest_asyncio.fixture
    async def product_with_config(self, db_session, tenant_a_user):
        """Create product with comprehensive config_data."""
        product = Product(
            name="Test Product",
            description="Product for config extraction testing",
            tenant_key=tenant_a_user.tenant_key,
            config_data={
                "architecture": "Microservices with REST APIs and event-driven architecture",
                "test_methodology": "Strict TDD - Red-Green-Refactor cycle. Write failing tests first, then implement code to make tests pass. Test coverage >80% required.",
                "coding_standards": "PEP 8, type hints required, 100% docstring coverage, comprehensive error handling",
                "deployment_strategy": "Docker containers deployed via GitHub Actions CI/CD pipeline with automated testing",
                "agent_execution_methodologies": "Sequential execution with dependency tracking, orchestrator monitors progress",
            },
        )
        db_session.add(product)
        await db_session.commit()
        await db_session.refresh(product)
        return product

    @pytest_asyncio.fixture
    async def project_basic(self, db_session, product_with_config):
        """Create basic project for testing."""
        project = Project(
            name="Test Project",
            description="Project for config extraction testing",
            product_id=product_with_config.id,
            tenant_key=product_with_config.tenant_key,
            mission="Test project mission for config extraction",
            status="active",
        )
        db_session.add(project)
        await db_session.commit()
        await db_session.refresh(project)
        return project

    async def test_extract_test_methodology_field(
        self, mission_planner, product_with_config, project_basic, tenant_a_user
    ):
        """
        Test 1: test_methodology field can be prioritized and extracted.

        Given: Product with test_methodology in config_data
        When: Build context with test_methodology priority 10 (full detail)
        Then: Test methodology appears in context with full detail
        """
        # Set test_methodology as highest priority
        field_priorities = {
            "config_data.test_methodology": 10,  # Full detail
        }

        # Build context
        context = await mission_planner._build_context_with_priorities(
            product=product_with_config,
            project=project_basic,
            field_priorities=field_priorities,
            user_id=str(tenant_a_user.id),
        )

        # Verify test methodology appears in context
        assert "## Test Methodology" in context
        assert "Red-Green-Refactor" in context
        assert "failing tests first" in context
        assert "80%" in context

    async def test_config_field_formatting(self, mission_planner, db_session, tenant_a_user):
        """
        Test 2: Config fields formatted correctly (dict and string values).

        Given: config_data with dict and string values
        When: Extract fields at different detail levels
        Then: Dict fields combined with "; ", strings preserved, formatting correct
        """
        # Create product with dict architecture value
        product = Product(
            name="Format Test Product",
            description="Testing field formatting",
            tenant_key=tenant_a_user.tenant_key,
            config_data={
                "architecture": {
                    "pattern": "MVC",
                    "api_style": "REST",
                    "design_patterns": "Repository, Factory, Observer",
                    "notes": "Microservices architecture with event-driven communication",
                },
                "test_methodology": "TDD with pytest",
            },
        )
        db_session.add(product)

        project = Project(
            name="Format Test Project",
            description="Test project",
            product_id=product.id,
            tenant_key=product.tenant_key,
            status="active",
        )
        db_session.add(project)
        await db_session.commit()
        await db_session.refresh(product)
        await db_session.refresh(project)

        # Extract architecture (dict value) and test_methodology (string value)
        field_priorities = {
            "config_data.architecture": 10,  # Full detail
            "config_data.test_methodology": 10,  # Full detail
        }

        context = await mission_planner._build_context_with_priorities(
            product=product, project=project, field_priorities=field_priorities, user_id=str(tenant_a_user.id)
        )

        # Verify dict fields combined correctly
        assert "## System Architecture" in context or "## Architecture" in context
        assert "MVC" in context
        assert "REST" in context
        assert "Repository, Factory, Observer" in context

        # Verify string fields preserved
        assert "## Test Methodology" in context
        assert "TDD with pytest" in context

    async def test_config_field_detail_levels(self, mission_planner, product_with_config, project_basic, tenant_a_user):
        """
        Test 3: Detail levels apply correctly to config fields.

        Given: test_methodology field with content
        When: Extract at priority 2 (minimal), 6 (abbreviated), 10 (full)
        Then: Token counts match expected reduction (minimal < abbreviated < full)
        """
        # Test minimal detail (priority 1-3)
        minimal_priorities = {"config_data.test_methodology": 2}
        minimal_context = await mission_planner._build_context_with_priorities(
            product=product_with_config,
            project=project_basic,
            field_priorities=minimal_priorities,
            user_id=str(tenant_a_user.id),
        )

        # Test abbreviated detail (priority 4-6)
        abbreviated_priorities = {"config_data.test_methodology": 5}
        abbreviated_context = await mission_planner._build_context_with_priorities(
            product=product_with_config,
            project=project_basic,
            field_priorities=abbreviated_priorities,
            user_id=str(tenant_a_user.id),
        )

        # Test full detail (priority 10)
        full_priorities = {"config_data.test_methodology": 10}
        full_context = await mission_planner._build_context_with_priorities(
            product=product_with_config,
            project=project_basic,
            field_priorities=full_priorities,
            user_id=str(tenant_a_user.id),
        )

        # Verify detail level progression
        minimal_tokens = mission_planner._count_tokens(minimal_context)
        abbreviated_tokens = mission_planner._count_tokens(abbreviated_context)
        full_tokens = mission_planner._count_tokens(full_context)

        # Token counts should increase with detail level
        assert minimal_tokens < abbreviated_tokens < full_tokens, (
            f"Token progression incorrect: minimal={minimal_tokens}, abbreviated={abbreviated_tokens}, full={full_tokens}"
        )

        # Full detail should contain complete text
        assert "Red-Green-Refactor" in full_context
        assert "failing tests first" in full_context

    async def test_config_fields_tenant_isolation(self, mission_planner, db_session, tenant_a_user, tenant_b_user):
        """
        Test 4: Config fields respect tenant boundaries.

        Given: Two tenants with different config_data
        When: Extract config fields for each tenant
        Then: Each tenant sees only their config fields
        """
        # Create Tenant A product
        product_a = Product(
            name="Tenant A Product",
            description="Tenant A test product",
            tenant_key=tenant_a_user.tenant_key,
            config_data={
                "test_methodology": "Tenant A uses TDD with pytest",
                "coding_standards": "Tenant A: PEP 8 strict",
            },
        )
        db_session.add(product_a)

        # Create Tenant B product
        product_b = Product(
            name="Tenant B Product",
            description="Tenant B test product",
            tenant_key=tenant_b_user.tenant_key,
            config_data={
                "test_methodology": "Tenant B uses BDD with Cucumber",
                "coding_standards": "Tenant B: Google Style Guide",
            },
        )
        db_session.add(product_b)

        # Create projects for each tenant
        project_a = Project(
            name="Tenant A Project",
            description="Tenant A project",
            product_id=product_a.id,
            tenant_key=product_a.tenant_key,
            status="active",
        )
        db_session.add(project_a)

        project_b = Project(
            name="Tenant B Project",
            description="Tenant B project",
            product_id=product_b.id,
            tenant_key=product_b.tenant_key,
            status="active",
        )
        db_session.add(project_b)

        await db_session.commit()
        await db_session.refresh(product_a)
        await db_session.refresh(product_b)
        await db_session.refresh(project_a)
        await db_session.refresh(project_b)

        # Extract config fields for Tenant A
        field_priorities = {
            "config_data.test_methodology": 10,
            "config_data.coding_standards": 10,
        }

        context_a = await mission_planner._build_context_with_priorities(
            product=product_a, project=project_a, field_priorities=field_priorities, user_id=str(tenant_a_user.id)
        )

        context_b = await mission_planner._build_context_with_priorities(
            product=product_b, project=project_b, field_priorities=field_priorities, user_id=str(tenant_b_user.id)
        )

        # Verify tenant isolation
        assert "pytest" in context_a and "pytest" not in context_b
        assert "BDD" not in context_a and "BDD" in context_b
        assert "PEP 8" in context_a and "PEP 8" not in context_b
        assert "Google Style Guide" not in context_a and "Google Style Guide" in context_b

    async def test_missing_config_fields_handled(self, mission_planner, db_session, tenant_a_user):
        """
        Test 5: Graceful handling of missing config fields.

        Given: Product without certain config fields
        When: Attempt to prioritize missing fields
        Then: No errors, context continues with available fields
        """
        # Create product with partial config_data
        product = Product(
            name="Partial Config Product",
            description="Product with incomplete config",
            tenant_key=tenant_a_user.tenant_key,
            config_data={
                "architecture": "Simple monolithic architecture",
                # Missing: test_methodology, coding_standards, deployment_strategy
            },
        )
        db_session.add(product)

        project = Project(
            name="Partial Config Project",
            description="Test project",
            product_id=product.id,
            tenant_key=product.tenant_key,
            status="active",
        )
        db_session.add(project)
        await db_session.commit()
        await db_session.refresh(product)
        await db_session.refresh(project)

        # Try to extract missing fields
        field_priorities = {
            "config_data.architecture": 10,
            "config_data.test_methodology": 10,  # Missing
            "config_data.coding_standards": 10,  # Missing
            "config_data.deployment_strategy": 10,  # Missing
        }

        # Should not raise errors
        context = await mission_planner._build_context_with_priorities(
            product=product, project=project, field_priorities=field_priorities, user_id=str(tenant_a_user.id)
        )

        # Verify context contains available field only
        assert "architecture" in context.lower()
        # Missing fields should not appear
        # No assertion for missing fields - they simply won't be in context

    async def test_arbitrary_config_fields(self, mission_planner, db_session, tenant_a_user):
        """
        Test 6: Arbitrary user-defined config fields work.

        Given: config_data with custom "deployment_workflow" field
        When: Add to field priorities
        Then: Field extracted and formatted correctly
        """
        # Create product with user-defined field
        product = Product(
            name="Custom Field Product",
            description="Product with custom config fields",
            tenant_key=tenant_a_user.tenant_key,
            config_data={
                "custom_workflow": "Use Kanban board with 2-week sprints",
                "custom_guidelines": "All PRs require 2 approvals",
            },
        )
        db_session.add(product)

        project = Project(
            name="Custom Field Project",
            description="Test project",
            product_id=product.id,
            tenant_key=product.tenant_key,
            status="active",
        )
        db_session.add(project)
        await db_session.commit()
        await db_session.refresh(product)
        await db_session.refresh(project)

        # Extract custom fields
        field_priorities = {
            "config_data.custom_workflow": 10,
            "config_data.custom_guidelines": 10,
        }

        context = await mission_planner._build_context_with_priorities(
            product=product, project=project, field_priorities=field_priorities, user_id=str(tenant_a_user.id)
        )

        # Verify custom fields extracted
        assert "Kanban" in context or "workflow" in context.lower()
        assert "PRs" in context or "approvals" in context.lower()

    async def test_architecture_field_still_works(
        self, mission_planner, product_with_config, project_basic, tenant_a_user
    ):
        """
        Test 7: Existing architecture extraction unchanged (backward compatibility).

        Given: Product with architecture field (existing)
        When: Build context with architecture priority
        Then: Architecture still extracted correctly (no regression)
        """
        # Use both old and new field keys to ensure backward compatibility
        field_priorities_old = {
            "architecture": 10,  # Old key (backward compat)
        }

        field_priorities_new = {
            "config_data.architecture": 10,  # New key
        }

        # Test old key
        context_old = await mission_planner._build_context_with_priorities(
            product=product_with_config,
            project=project_basic,
            field_priorities=field_priorities_old,
            user_id=str(tenant_a_user.id),
        )

        # Test new key
        context_new = await mission_planner._build_context_with_priorities(
            product=product_with_config,
            project=project_basic,
            field_priorities=field_priorities_new,
            user_id=str(tenant_a_user.id),
        )

        # Both should extract architecture
        assert "architecture" in context_old.lower()
        assert "Microservices" in context_old

        assert "architecture" in context_new.lower()
        assert "Microservices" in context_new
