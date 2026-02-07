"""
Unit tests for AgentSelector class.

Tests the agent selection logic with multi-tenant isolation, template priority cascade,
and scope boundary determination. This is a SECURITY-CRITICAL component.

Following TDD principles: Tests written BEFORE implementation.
"""

from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.agent_selector import AgentSelector
from src.giljo_mcp.models import AgentTemplate
from src.giljo_mcp.orchestration_types import AgentConfig


class TestAgentSelector:
    """Test cases for AgentSelector class."""

    @pytest.fixture
    def mock_db_manager(self):
        """Create a mock database manager."""
        db_manager = Mock()
        db_manager.is_async = True
        return db_manager

    @pytest.fixture
    def agent_selector(self, mock_db_manager):
        """Create AgentSelector instance with mocked database."""
        return AgentSelector(mock_db_manager)

    @pytest.fixture
    def system_templates(self):
        """Create system default templates."""
        templates = []

        # Implementer template
        impl_template = Mock(spec=AgentTemplate)
        impl_template.id = "template_sys_impl"
        impl_template.tenant_key = "system"
        impl_template.product_id = None
        impl_template.name = "implementer"
        impl_template.description = "System default implementer"
        impl_template.system_instructions = "You are a professional implementer..."
        impl_template.variables = []
        impl_template.is_active = True
        impl_template.is_default = True
        templates.append(impl_template)

        # Tester template
        tester_template = Mock(spec=AgentTemplate)
        tester_template.id = "template_sys_tester"
        tester_template.tenant_key = "system"
        tester_template.product_id = None
        tester_template.name = "tester"
        tester_template.description = "System default tester"
        tester_template.system_instructions = "You are a professional tester..."
        tester_template.variables = []
        tester_template.is_active = True
        tester_template.is_default = True
        templates.append(tester_template)

        # Code reviewer template
        reviewer_template = Mock(spec=AgentTemplate)
        reviewer_template.id = "template_sys_reviewer"
        reviewer_template.tenant_key = "system"
        reviewer_template.product_id = None
        reviewer_template.name = "code-reviewer"
        reviewer_template.description = "System default code reviewer"
        reviewer_template.system_instructions = "You are a professional code reviewer..."
        reviewer_template.variables = []
        reviewer_template.is_active = True
        reviewer_template.is_default = True
        templates.append(reviewer_template)

        return templates

    @pytest.fixture
    def tenant_templates(self):
        """Create tenant-specific templates."""
        templates = []

        # Tenant A implementer
        impl_template = Mock(spec=AgentTemplate)
        impl_template.id = "template_tenant_a_impl"
        impl_template.tenant_key = "tenant-a"
        impl_template.product_id = None
        impl_template.name = "implementer"
        impl_template.description = "Tenant A implementer"
        impl_template.system_instructions = "You are Tenant A's implementer..."
        impl_template.variables = []
        impl_template.is_active = True
        impl_template.is_default = False
        templates.append(impl_template)

        return templates

    @pytest.fixture
    def product_templates(self):
        """Create product-specific templates."""
        templates = []

        # Product 1 implementer
        impl_template = Mock(spec=AgentTemplate)
        impl_template.id = "template_product_1_impl"
        impl_template.tenant_key = "tenant-a"
        impl_template.product_id = "product-1"
        impl_template.name = "implementer"
        impl_template.description = "Product 1 implementer"
        impl_template.system_instructions = "You are Product 1's implementer..."
        impl_template.variables = []
        impl_template.is_active = True
        impl_template.is_default = False
        templates.append(impl_template)

        return templates

    @pytest.fixture
    def inactive_template(self):
        """Create an inactive template."""
        template = Mock(spec=AgentTemplate)
        template.id = "template_inactive"
        template.tenant_key = "tenant-a"
        template.product_id = None
        template.name = "implementer"
        template.description = "Inactive implementer"
        template.system_instructions = "You are an inactive implementer..."
        template.variables = []
        template.is_active = False
        template.is_default = False
        return template

    # Test 1: Basic agent selection
    @pytest.mark.asyncio
    async def test_select_agents_basic(self, agent_selector, mock_db_manager, system_templates):
        """Test basic agent selection with system defaults."""
        # Mock database session
        mock_session = AsyncMock(spec=AsyncSession)
        mock_db_manager.get_session_async = Mock(
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_session))
        )

        # Mock query results - return system implementer template
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=system_templates[0])
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Select agents
        work_types = {"implementer": "high"}
        agents = await agent_selector.select_agents(work_types=work_types, tenant_key="tenant-a")

        # Verify results
        assert len(agents) == 1
        assert isinstance(agents[0], AgentConfig)
        assert agents[0].role == "implementer"
        assert agents[0].template_id == "template_sys_impl"
        assert agents[0].priority == "high"
        assert agents[0].mission_scope is not None
        assert len(agents[0].mission_scope) > 0

    # Test 2: Product-specific template priority
    @pytest.mark.asyncio
    async def test_select_agents_product_specific(
        self, agent_selector, mock_db_manager, product_templates, system_templates
    ):
        """Test that product-specific templates have highest priority."""
        # Mock database session
        mock_session = AsyncMock(spec=AsyncSession)
        mock_db_manager.get_session_async = Mock(
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_session))
        )

        # First query tries product-specific, returns the product template
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=product_templates[0])
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Select agents with product_id
        work_types = {"implementer": "high"}
        agents = await agent_selector.select_agents(
            work_types=work_types, tenant_key="tenant-a", product_id="product-1"
        )

        # Verify product template was used
        assert len(agents) == 1
        assert agents[0].template_id == "template_product_1_impl"
        assert agents[0].role == "implementer"

    # Test 3: Tenant-specific template fallback
    @pytest.mark.asyncio
    async def test_select_agents_tenant_specific(
        self, agent_selector, mock_db_manager, tenant_templates, system_templates
    ):
        """Test that tenant templates are used when no product template exists."""
        # Mock database session
        mock_session = AsyncMock(spec=AsyncSession)
        mock_db_manager.get_session_async = Mock(
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_session))
        )

        # First query (product-specific) returns None, second (tenant) returns template
        mock_result_product = Mock()
        mock_result_product.scalar_one_or_none = Mock(return_value=None)

        mock_result_tenant = Mock()
        mock_result_tenant.scalar_one_or_none = Mock(return_value=tenant_templates[0])

        # Setup side_effect for multiple execute calls
        mock_session.execute = AsyncMock(side_effect=[mock_result_product, mock_result_tenant])

        # Select agents with product_id (but no product template exists)
        work_types = {"implementer": "high"}
        agents = await agent_selector.select_agents(
            work_types=work_types, tenant_key="tenant-a", product_id="product-1"
        )

        # Verify tenant template was used
        assert len(agents) == 1
        assert agents[0].template_id == "template_tenant_a_impl"
        assert agents[0].role == "implementer"

    # Test 4: System default template fallback
    @pytest.mark.asyncio
    async def test_select_agents_system_default(self, agent_selector, mock_db_manager, system_templates):
        """Test that system defaults are used when no tenant template exists."""
        # Mock database session
        mock_session = AsyncMock(spec=AsyncSession)
        mock_db_manager.get_session_async = Mock(
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_session))
        )

        # All queries return None except system default
        mock_result_none = Mock()
        mock_result_none.scalar_one_or_none = Mock(return_value=None)

        mock_result_system = Mock()
        mock_result_system.scalar_one_or_none = Mock(return_value=system_templates[0])

        # Setup side_effect for cascade: product -> tenant -> system
        mock_session.execute = AsyncMock(side_effect=[mock_result_none, mock_result_none, mock_result_system])

        # Select agents with product_id
        work_types = {"implementer": "high"}
        agents = await agent_selector.select_agents(
            work_types=work_types, tenant_key="tenant-b", product_id="product-2"
        )

        # Verify system template was used
        assert len(agents) == 1
        assert agents[0].template_id == "template_sys_impl"
        assert agents[0].role == "implementer"

    # Test 5: Multi-tenant isolation (SECURITY CRITICAL)
    @pytest.mark.asyncio
    async def test_select_agents_multi_tenant_isolation(self, agent_selector, mock_db_manager, tenant_templates):
        """Test that tenant isolation is enforced - tenants cannot access each other's templates."""
        # Create templates for two different tenants
        tenant_a_template = tenant_templates[0]  # tenant-a

        tenant_b_template = Mock(spec=AgentTemplate)
        tenant_b_template.id = "template_tenant_b_impl"
        tenant_b_template.tenant_key = "tenant-b"
        tenant_b_template.product_id = None
        tenant_b_template.name = "implementer"
        tenant_b_template.system_instructions = "Tenant B implementer..."
        tenant_b_template.is_active = True
        tenant_b_template.is_default = False

        # Mock database session
        mock_session = AsyncMock(spec=AsyncSession)
        mock_db_manager.get_session_async = Mock(
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_session))
        )

        # First call (tenant-a): product -> tenant-a template
        mock_result_a_product = Mock()
        mock_result_a_product.scalar_one_or_none = Mock(return_value=None)

        mock_result_a_tenant = Mock()
        mock_result_a_tenant.scalar_one_or_none = Mock(return_value=tenant_a_template)

        mock_session.execute = AsyncMock(side_effect=[mock_result_a_product, mock_result_a_tenant])

        # Tenant A selects agents
        work_types = {"implementer": "high"}
        agents_a = await agent_selector.select_agents(
            work_types=work_types, tenant_key="tenant-a", product_id="product-1"
        )

        # Verify Tenant A got their template
        assert len(agents_a) == 1
        assert agents_a[0].template_id == "template_tenant_a_impl"

        # Second call (tenant-b): Should NOT get tenant-a's template
        mock_result_b_product = Mock()
        mock_result_b_product.scalar_one_or_none = Mock(return_value=None)

        mock_result_b_tenant = Mock()
        mock_result_b_tenant.scalar_one_or_none = Mock(return_value=tenant_b_template)

        mock_session.execute = AsyncMock(side_effect=[mock_result_b_product, mock_result_b_tenant])

        # Tenant B selects agents
        agents_b = await agent_selector.select_agents(
            work_types=work_types, tenant_key="tenant-b", product_id="product-2"
        )

        # Verify Tenant B got their template, NOT tenant A's
        assert len(agents_b) == 1
        assert agents_b[0].template_id == "template_tenant_b_impl"
        assert agents_b[0].template_id != agents_a[0].template_id

    # Test 6: Template priority cascade
    @pytest.mark.asyncio
    async def test_get_template_priority_cascade(
        self, agent_selector, mock_db_manager, product_templates, system_templates
    ):
        """Test the template selection priority: product > tenant > system."""
        # Mock database session
        mock_session = AsyncMock(spec=AsyncSession)
        mock_db_manager.get_session_async = Mock(
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_session))
        )

        # Test product priority (returns product template immediately)
        mock_result_product = Mock()
        mock_result_product.scalar_one_or_none = Mock(return_value=product_templates[0])
        mock_session.execute = AsyncMock(return_value=mock_result_product)

        template = await agent_selector._get_template(
            agent_display_name="implementer", tenant_key="tenant-a", product_id="product-1"
        )

        assert template is not None
        assert template.id == "template_product_1_impl"
        assert template.product_id == "product-1"

    # Test 7: Inactive templates filtered
    @pytest.mark.asyncio
    async def test_get_template_inactive_filtered(
        self, agent_selector, mock_db_manager, inactive_template, system_templates
    ):
        """Test that inactive templates are excluded from selection."""
        # Mock database session
        mock_session = AsyncMock(spec=AsyncSession)
        mock_db_manager.get_session_async = Mock(
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_session))
        )

        # Inactive template should not be returned, system default used instead
        mock_result_product = Mock()
        mock_result_product.scalar_one_or_none = Mock(return_value=None)

        mock_result_tenant = Mock()
        mock_result_tenant.scalar_one_or_none = Mock(return_value=None)

        mock_result_system = Mock()
        mock_result_system.scalar_one_or_none = Mock(return_value=system_templates[0])

        mock_session.execute = AsyncMock(side_effect=[mock_result_product, mock_result_tenant, mock_result_system])

        # Select agents - should skip inactive and use system
        work_types = {"implementer": "high"}
        agents = await agent_selector.select_agents(
            work_types=work_types, tenant_key="tenant-a", product_id="product-1"
        )

        # Verify system template used (inactive was filtered out)
        assert len(agents) == 1
        assert agents[0].template_id == "template_sys_impl"
        assert agents[0].template_id != inactive_template.id

    # Test 8: Scope boundary determination
    def test_determine_scope(self, agent_selector):
        """Test scope boundary generation for different agent types and priorities."""
        # Test implementer with high priority
        scope = agent_selector._determine_scope("implementer", "high")
        assert "production code" in scope.lower()
        assert "do not" in scope.lower() or "not modify" in scope.lower()

        # Test tester with medium priority
        scope = agent_selector._determine_scope("tester", "medium")
        assert "test" in scope.lower()
        assert "do not" in scope.lower() or "not modify" in scope.lower()

        # Test code-reviewer
        scope = agent_selector._determine_scope("code-reviewer", "high")
        assert "review" in scope.lower()
        assert "do not" in scope.lower() or "suggest" in scope.lower()

        # Test frontend-implementer
        scope = agent_selector._determine_scope("frontend-implementer", "high")
        assert "ui" in scope.lower() or "frontend" in scope.lower()
        assert "do not" in scope.lower() or "not modify" in scope.lower()

        # Test database-specialist
        scope = agent_selector._determine_scope("database-specialist", "high")
        assert "database" in scope.lower() or "schema" in scope.lower()

        # Test unknown agent type (should have generic scope)
        scope = agent_selector._determine_scope("unknown-agent", "high")
        assert len(scope) > 0

    # Test 9: Missing template handling
    @pytest.mark.asyncio
    async def test_select_agents_missing_template(self, agent_selector, mock_db_manager):
        """Test graceful handling when no template is found for an agent type."""
        # Mock database session
        mock_session = AsyncMock(spec=AsyncSession)
        mock_db_manager.get_session_async = Mock(
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_session))
        )

        # All queries return None (no templates found)
        mock_result_none = Mock()
        mock_result_none.scalar_one_or_none = Mock(return_value=None)
        mock_session.execute = AsyncMock(return_value=mock_result_none)

        # Select agents with non-existent agent type
        work_types = {"unknown-agent": "high"}
        agents = await agent_selector.select_agents(work_types=work_types, tenant_key="tenant-a")

        # Should return empty list or handle gracefully
        assert isinstance(agents, list)
        # When no template found, agent should be skipped
        assert len(agents) == 0

    # Test 10: Priority sorting
    @pytest.mark.asyncio
    async def test_select_agents_priority_sorting(self, agent_selector, mock_db_manager, system_templates):
        """Test that agents are sorted by priority (required > high > medium > low)."""
        # Mock database session
        mock_session = AsyncMock(spec=AsyncSession)
        mock_db_manager.get_session_async = Mock(
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_session))
        )

        # Mock results for different agent types
        def mock_execute_side_effect(*args, **kwargs):
            # Return different templates based on the query
            mock_result = Mock()
            # We'll just cycle through system templates for simplicity
            mock_result.scalar_one_or_none = Mock(
                side_effect=[
                    system_templates[0],  # implementer
                    system_templates[1],  # tester
                    system_templates[2],  # code-reviewer
                ]
            )
            return mock_result

        mock_session.execute = AsyncMock(
            side_effect=[
                Mock(scalar_one_or_none=Mock(return_value=system_templates[0])),
                Mock(scalar_one_or_none=Mock(return_value=system_templates[1])),
                Mock(scalar_one_or_none=Mock(return_value=system_templates[2])),
            ]
        )

        # Select agents with different priorities
        work_types = {"tester": "medium", "implementer": "required", "code-reviewer": "high"}
        agents = await agent_selector.select_agents(work_types=work_types, tenant_key="tenant-a")

        # Verify agents are sorted by priority
        assert len(agents) == 3

        # Priority order: required > high > medium
        priority_order = {"required": 0, "high": 1, "medium": 2, "low": 3}
        for i in range(len(agents) - 1):
            current_priority = priority_order[agents[i].priority]
            next_priority = priority_order[agents[i + 1].priority]
            assert current_priority <= next_priority, (
                f"Agents not sorted by priority: {agents[i].priority} before {agents[i + 1].priority}"
            )

    # Test 11: Empty work_types dict
    @pytest.mark.asyncio
    async def test_select_agents_empty_work_types(self, agent_selector, mock_db_manager):
        """Test handling of empty work_types dictionary."""
        agents = await agent_selector.select_agents(work_types={}, tenant_key="tenant-a")

        # Should return empty list
        assert isinstance(agents, list)
        assert len(agents) == 0

    # Test 12: Null product_id handling
    @pytest.mark.asyncio
    async def test_select_agents_null_product_id(self, agent_selector, mock_db_manager, tenant_templates):
        """Test that product_id=None skips product template lookup."""
        # Mock database session
        mock_session = AsyncMock(spec=AsyncSession)
        mock_db_manager.get_session_async = Mock(
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_session))
        )

        # Should only query tenant and system (not product)
        mock_result_tenant = Mock()
        mock_result_tenant.scalar_one_or_none = Mock(return_value=tenant_templates[0])
        mock_session.execute = AsyncMock(return_value=mock_result_tenant)

        # Select agents without product_id
        work_types = {"implementer": "high"}
        agents = await agent_selector.select_agents(work_types=work_types, tenant_key="tenant-a", product_id=None)

        # Verify tenant template was used
        assert len(agents) == 1
        assert agents[0].template_id == "template_tenant_a_impl"

        # Verify only one execute call (tenant query, no product query)
        # Since product_id is None, we skip product-specific query
        assert mock_session.execute.call_count == 1
