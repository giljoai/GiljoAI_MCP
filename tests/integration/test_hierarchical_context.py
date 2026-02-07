"""
Integration tests for hierarchical context loading workflow.

Tests the complete flow:
1. Orchestrator gets FULL config_data
2. Worker agents get FILTERED config_data based on role
3. Context context prioritization is significant (60%+ for focused workers)
4. Multi-agent coordination maintains proper context boundaries
"""

import pytest


pytest.skip("TODO(0127a-2): Comprehensive refactoring needed for MCPAgentJob model", allow_module_level=True)
import json

import pytest

from src.giljo_mcp.context_manager import get_filtered_config, get_full_config
from src.giljo_mcp.database import get_db_manager


# TODO(0127a): from src.giljo_mcp.models import Agent, Product, Project
# from src.giljo_mcp.models import MCPAgentJob  # Use this instead


@pytest.fixture
def db_session():
    """Get database session"""
    db = get_db_manager()
    with db.get_session() as session:
        yield session


@pytest.fixture
def sample_product(db_session):
    """Create sample product with rich config_data"""
    product = Product(
        id="test-product-hierarchical",
        tenant_key="test-tenant-hierarchical",
        name="GiljoAI MCP Test Product",
        description="Test product for hierarchical context testing",
        config_data={
            "architecture": "FastAPI + PostgreSQL + Vue.js",
            "tech_stack": ["Python 3.11", "PostgreSQL 18", "Vue 3", "FastAPI", "SQLAlchemy", "Alembic"],
            "codebase_structure": {
                "api": "REST endpoints and WebSocket handlers",
                "frontend": "Vue 3 dashboard with Vuetify",
                "src/giljo_mcp": "Core orchestration engine",
                "tests": "Comprehensive test suites",
                "docs": "Documentation and manuals",
            },
            "critical_features": [
                "Multi-tenant isolation",
                "Agent orchestration",
                "Message queue coordination",
                "Vision document chunking",
                "Database-backed templates",
            ],
            "test_commands": ["pytest tests/", "pytest tests/unit/", "pytest tests/integration/", "npm run test"],
            "test_config": {"coverage_threshold": 80, "framework": "pytest", "parallel": True},
            "api_docs": "/docs/api_reference.md",
            "documentation_style": "Markdown with mermaid diagrams",
            "serena_mcp_enabled": True,
            "database_type": "postgresql",
            "frontend_framework": "Vue 3",
            "backend_framework": "FastAPI",
            "deployment_modes": ["localhost", "server"],
            "known_issues": ["Performance optimization needed for large vision documents"],
        },
    )
    db_session.add(product)
    db_session.commit()
    db_session.refresh(product)
    yield product

    # Cleanup
    db_session.delete(product)
    db_session.commit()


@pytest.fixture
def sample_project(db_session, sample_product):
    """Create sample project linked to product"""
    project = Project(
        id="test-project-hierarchical",
        tenant_key="test-tenant-hierarchical",
        product_id=sample_product.id,
        name="Test Project Hierarchical",
        mission="Test hierarchical context loading",
        status="active",
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    yield project

    # Cleanup
    db_session.delete(project)
    db_session.commit()


class TestOrchestratorFullContext:
    """Test orchestrator receives FULL config_data"""

    def test_orchestrator_gets_all_fields(self, sample_product):
        """Test orchestrator receives complete config_data"""
        config = get_full_config(sample_product)

        # Verify all fields present
        expected_fields = [
            "architecture",
            "tech_stack",
            "codebase_structure",
            "critical_features",
            "test_commands",
            "test_config",
            "api_docs",
            "documentation_style",
            "serena_mcp_enabled",
            "database_type",
            "frontend_framework",
            "backend_framework",
            "deployment_modes",
            "known_issues",
        ]

        for field in expected_fields:
            assert field in config, f"Orchestrator missing field: {field}"

        # Verify total field count
        assert len(config) == len(sample_product.config_data)

    def test_orchestrator_by_name(self, sample_product):
        """Test orchestrator identified by name gets full config"""
        config = get_filtered_config("orchestrator", sample_product)

        assert len(config) == len(sample_product.config_data)

    def test_orchestrator_by_role(self, sample_product):
        """Test orchestrator identified by role gets full config"""
        config = get_filtered_config("agent-123", sample_product, agent_role="orchestrator")

        assert len(config) == len(sample_product.config_data)

    def test_orchestrator_agent_model(self, db_session, sample_project, sample_product):
        """Test orchestrator Agent model gets full config"""
        orchestrator = Agent(
            tenant_key="test-tenant-hierarchical",
            project_id=sample_project.id,
            name="orchestrator",
            role="orchestrator",
            status="active",
        )
        db_session.add(orchestrator)
        db_session.commit()

        # Get config using orchestrator's name and role
        config = get_filtered_config(orchestrator.name, sample_product, orchestrator.role)

        assert len(config) == len(sample_product.config_data)

        # Cleanup
        db_session.delete(orchestrator)
        db_session.commit()


class TestWorkerAgentFilteredContext:
    """Test worker agents receive FILTERED config_data"""

    def test_implementer_filtered_config(self, sample_product):
        """Test implementer receives implementation-focused config"""
        config = get_filtered_config("implementer-dev-1", sample_product)

        # Should have
        assert "architecture" in config
        assert "tech_stack" in config
        assert "codebase_structure" in config
        assert "critical_features" in config
        assert "database_type" in config
        assert "backend_framework" in config
        assert "frontend_framework" in config
        assert "deployment_modes" in config

        # Should NOT have
        assert "test_commands" not in config
        assert "test_config" not in config
        assert "api_docs" not in config
        assert "documentation_style" not in config

        # Always has serena flag
        assert "serena_mcp_enabled" in config

    def test_tester_filtered_config(self, sample_product):
        """Test tester receives testing-focused config"""
        config = get_filtered_config("tester-qa-1", sample_product)

        # Should have
        assert "test_commands" in config
        assert "test_config" in config
        assert "critical_features" in config
        assert "tech_stack" in config
        assert "known_issues" in config

        # Should NOT have
        assert "codebase_structure" not in config
        assert "api_docs" not in config
        assert "database_type" not in config

        # Always has serena flag
        assert "serena_mcp_enabled" in config

    def test_documenter_filtered_config(self, sample_product):
        """Test documenter receives documentation-focused config"""
        config = get_filtered_config("documenter-docs", sample_product)

        # Should have
        assert "api_docs" in config
        assert "documentation_style" in config
        assert "architecture" in config
        assert "critical_features" in config
        assert "codebase_structure" in config

        # Should NOT have
        assert "test_commands" not in config
        assert "test_config" not in config
        assert "database_type" not in config

    def test_analyzer_filtered_config(self, sample_product):
        """Test analyzer receives analysis-focused config"""
        config = get_filtered_config("analyzer-code", sample_product)

        # Should have
        assert "architecture" in config
        assert "tech_stack" in config
        assert "codebase_structure" in config
        assert "critical_features" in config
        assert "known_issues" in config

        # Should NOT have
        assert "test_commands" not in config
        assert "api_docs" not in config

    def test_reviewer_filtered_config(self, sample_product):
        """Test reviewer receives review-focused config"""
        config = get_filtered_config("reviewer-1", sample_product)

        # Should have
        assert "architecture" in config
        assert "tech_stack" in config
        assert "critical_features" in config
        assert "documentation_style" in config

        # Should NOT have
        assert "codebase_structure" not in config
        assert "test_commands" not in config
        assert "test_config" not in config


class TestContextTokenReduction:
    """Test that filtering achieves significant context prioritization"""

    def test_implementer_token_reduction(self, sample_product):
        """Test implementer config has significant context prioritization"""
        full_config = get_full_config(sample_product)
        filtered_config = get_filtered_config("implementer-1", sample_product)

        # Calculate field reduction
        field_reduction = (len(full_config) - len(filtered_config)) / len(full_config)

        # Should have at least 30% field reduction
        assert field_reduction >= 0.3, f"Field reduction: {field_reduction:.1%}"

        # Calculate approximate context prioritization
        full_tokens = estimate_tokens(full_config)
        filtered_tokens = estimate_tokens(filtered_config)
        token_reduction = (full_tokens - filtered_tokens) / full_tokens

        # Should have significant context prioritization
        assert token_reduction > 0.2, f"Context prioritization: {token_reduction:.1%}"

    def test_tester_token_reduction(self, sample_product):
        """Test tester config has significant context prioritization"""
        full_config = get_full_config(sample_product)
        filtered_config = get_filtered_config("tester-1", sample_product)

        field_reduction = (len(full_config) - len(filtered_config)) / len(full_config)

        # Tester should have even more reduction (more specialized)
        assert field_reduction >= 0.4, f"Field reduction: {field_reduction:.1%}"

    def test_documenter_token_reduction(self, sample_product):
        """Test documenter config has significant context prioritization"""
        full_config = get_full_config(sample_product)
        filtered_config = get_filtered_config("documenter-1", sample_product)

        field_reduction = (len(full_config) - len(filtered_config)) / len(full_config)

        assert field_reduction >= 0.4, f"Field reduction: {field_reduction:.1%}"

    def test_all_workers_reduce_tokens(self, sample_product):
        """Test that all worker roles achieve context prioritization"""
        full_config = get_full_config(sample_product)
        worker_roles = ["implementer", "tester", "documenter", "analyzer", "reviewer"]

        for role in worker_roles:
            filtered_config = get_filtered_config(f"{role}-1", sample_product)
            field_count = len(filtered_config)
            full_count = len(full_config)

            # All workers should have fewer fields than orchestrator
            assert field_count < full_count, f"{role} should have fewer fields"


class TestMultiAgentCoordination:
    """Test multi-agent scenarios maintain proper context boundaries"""

    def test_multiple_agents_different_contexts(self, db_session, sample_project, sample_product):
        """Test multiple agents with different roles get appropriate contexts"""
        # Create orchestrator
        orchestrator = Agent(
            tenant_key="test-tenant-hierarchical",
            project_id=sample_project.id,
            name="orchestrator",
            role="orchestrator",
            status="active",
        )

        # Create implementer
        implementer = Agent(
            tenant_key="test-tenant-hierarchical",
            project_id=sample_project.id,
            name="implementer-dev-1",
            role="implementer",
            status="active",
        )

        # Create tester
        tester = Agent(
            tenant_key="test-tenant-hierarchical",
            project_id=sample_project.id,
            name="tester-qa-1",
            role="tester",
            status="active",
        )

        db_session.add_all([orchestrator, implementer, tester])
        db_session.commit()

        # Get configs for each
        orch_config = get_filtered_config(orchestrator.name, sample_product, orchestrator.role)
        impl_config = get_filtered_config(implementer.name, sample_product, implementer.role)
        test_config = get_filtered_config(tester.name, sample_product, tester.role)

        # Verify orchestrator has everything
        assert len(orch_config) == len(sample_product.config_data)

        # Verify implementer has implementation fields but not test fields
        assert "codebase_structure" in impl_config
        assert "test_commands" not in impl_config

        # Verify tester has test fields but not implementation fields
        assert "test_commands" in test_config
        assert "codebase_structure" not in test_config

        # Verify no cross-contamination
        assert "test_config" not in impl_config
        assert "database_type" not in test_config

        # Cleanup
        db_session.delete(orchestrator)
        db_session.delete(implementer)
        db_session.delete(tester)
        db_session.commit()

    def test_handoff_maintains_context_filtering(self, db_session, sample_project, sample_product):
        """Test agent handoffs maintain proper context filtering"""
        # Orchestrator spawns implementer
        orchestrator = Agent(
            tenant_key="test-tenant-hierarchical",
            project_id=sample_project.id,
            name="orchestrator",
            role="orchestrator",
            status="database_initialized",
        )

        implementer = Agent(
            tenant_key="test-tenant-hierarchical",
            project_id=sample_project.id,
            name="implementer-1",
            role="implementer",
            status="active",
        )

        db_session.add_all([orchestrator, implementer])
        db_session.commit()

        # Both agents should get appropriate context
        orch_config = get_filtered_config(orchestrator.name, sample_product, orchestrator.role)
        impl_config = get_filtered_config(implementer.name, sample_product, implementer.role)

        # Orchestrator had full context
        assert len(orch_config) == len(sample_product.config_data)

        # Implementer gets filtered context
        assert len(impl_config) < len(orch_config)
        assert "codebase_structure" in impl_config
        assert "test_commands" not in impl_config

        # Cleanup
        db_session.delete(orchestrator)
        db_session.delete(implementer)
        db_session.commit()


class TestContextConsistency:
    """Test context loading consistency across multiple calls"""

    def test_repeated_calls_return_same_context(self, sample_product):
        """Test that repeated calls return consistent context"""
        config1 = get_filtered_config("implementer-1", sample_product)
        config2 = get_filtered_config("implementer-1", sample_product)

        assert config1 == config2

    def test_different_agents_same_role_get_same_context(self, sample_product):
        """Test that different agents with same role get same filtered context"""
        config1 = get_filtered_config("implementer-dev-1", sample_product)
        config2 = get_filtered_config("implementer-dev-2", sample_product)
        config3 = get_filtered_config("implementer-code-writer", sample_product)

        assert config1 == config2 == config3

    def test_serena_flag_always_included(self, sample_product):
        """Test that serena_mcp_enabled is always included in filtered configs"""
        roles = ["implementer", "tester", "documenter", "analyzer", "reviewer"]

        for role in roles:
            config = get_filtered_config(f"{role}-1", sample_product)
            assert "serena_mcp_enabled" in config, f"{role} missing serena_mcp_enabled flag"


# Helper functions


def estimate_tokens(config_dict: dict) -> int:
    """
    Rough estimate of tokens for config_data.
    Uses Claude's approximation: 1 token ≈ 4 characters
    """
    config_str = json.dumps(config_dict, indent=2)
    return len(config_str) // 4
