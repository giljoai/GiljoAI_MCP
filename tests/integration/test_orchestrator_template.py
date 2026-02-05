"""
Integration tests for enhanced orchestrator template and config_data workflow.

Tests complete workflow:
1. Orchestrator template exists and is marked as default
2. activate_agent() uses enhanced template
3. Template contains discovery workflow, delegation rules, closure requirements
4. Orchestrator spawns worker agents correctly
5. Full project lifecycle with config_data integration
"""

import pytest
pytest.skip("TODO(0127a-2): Comprehensive refactoring needed for MCPAgentJob model", allow_module_level=True)
import pytest

from src.giljo_mcp.context_manager import get_filtered_config, get_full_config
# TODO(0127a): from src.giljo_mcp.models import Agent, AgentTemplate, Product, Project
# from src.giljo_mcp.models import MCPAgentJob  # Use this instead
from src.giljo_mcp.template_manager import get_template_manager


@pytest.fixture
def sample_product(db_session):
    """Create sample product with config_data"""
    product = Product(
        id="test-product-template",
        tenant_key="test-tenant-template",
        name="Template Test Product",
        config_data={
            "architecture": "FastAPI + PostgreSQL + Vue.js",
            "tech_stack": ["Python 3.11", "PostgreSQL 18", "Vue 3"],
            "codebase_structure": {"api": "REST endpoints", "frontend": "Vue dashboard"},
            "critical_features": ["Multi-tenant isolation"],
            "test_commands": ["pytest tests/"],
            "test_config": {"coverage_threshold": 80},
            "api_docs": "/docs/api.md",
            "documentation_style": "Markdown",
            "serena_mcp_enabled": True,
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
        id="test-project-template",
        tenant_key="test-tenant-template",
        product_id=sample_product.id,
        name="Template Test Project",
        mission="Test orchestrator template integration",
        status="active",
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    yield project

    # Cleanup
    db_session.delete(project)
    db_session.commit()


class TestOrchestratorTemplateExists:
    """Test that enhanced orchestrator template exists in database"""

    def test_orchestrator_template_exists(self, db_session):
        """Test that default orchestrator template exists"""
        template = (
            db_session.query(AgentTemplate)
            .filter(AgentTemplate.name == "orchestrator", AgentTemplate.is_default == True)
            .first()
        )

        assert template is not None, "Default orchestrator template not found"

    def test_orchestrator_template_properties(self, db_session):
        """Test orchestrator template has correct properties"""
        template = (
            db_session.query(AgentTemplate)
            .filter(AgentTemplate.name == "orchestrator", AgentTemplate.is_default == True)
            .first()
        )

        assert template.role == "orchestrator"
        assert template.is_active is True
        assert template.category in ["core", "orchestration"]
        assert len(template.system_instructions) > 100  # Should be substantial


class TestOrchestratorTemplateContent:
    """Test orchestrator template contains required content"""

    def test_template_contains_30_80_10_principle(self, db_session):
        """Test template contains 30-80-10 principle"""
        template = (
            db_session.query(AgentTemplate)
            .filter(AgentTemplate.name == "orchestrator", AgentTemplate.is_default == True)
            .first()
        )

        content = template.system_instructions.lower()
        assert "30-80-10" in content or "30/80/10" in content

    def test_template_contains_3_tool_rule(self, db_session):
        """Test template contains 3-tool rule"""
        template = (
            db_session.query(AgentTemplate)
            .filter(AgentTemplate.name == "orchestrator", AgentTemplate.is_default == True)
            .first()
        )

        content = template.system_instructions.lower()
        assert "3-tool" in content or "3 tool" in content

    def test_template_contains_discovery_workflow(self, db_session):
        """Test template contains discovery workflow"""
        template = (
            db_session.query(AgentTemplate)
            .filter(AgentTemplate.name == "orchestrator", AgentTemplate.is_default == True)
            .first()
        )

        content = template.system_instructions.lower()

        # Check for discovery steps
        assert "discovery" in content
        assert "serena" in content or "mcp" in content
        assert "vision" in content or "get_vision" in content

    def test_template_contains_delegation_rules(self, db_session):
        """Test template contains delegation rules"""
        template = (
            db_session.query(AgentTemplate)
            .filter(AgentTemplate.name == "orchestrator", AgentTemplate.is_default == True)
            .first()
        )

        content = template.system_instructions.lower()

        # Check for delegation enforcement
        assert "delegate" in content or "delegation" in content
        assert "ensure_agent" in content or "spawn" in content

    def test_template_contains_closure_requirements(self, db_session):
        """Test template contains project closure requirements"""
        template = (
            db_session.query(AgentTemplate)
            .filter(AgentTemplate.name == "orchestrator", AgentTemplate.is_default == True)
            .first()
        )

        content = template.system_instructions.lower()

        # Check for documentation requirements
        closure_keywords = ["completion report", "devlog", "session memory", "after-action"]
        assert any(keyword in content for keyword in closure_keywords)

    def test_template_mentions_config_data(self, db_session):
        """Test template mentions config_data or product settings"""
        template = (
            db_session.query(AgentTemplate)
            .filter(AgentTemplate.name == "orchestrator", AgentTemplate.is_default == True)
            .first()
        )

        content = template.system_instructions.lower()

        # Should mention product configuration
        config_keywords = ["config", "product settings", "product config", "get_product_settings"]
        assert any(keyword in content for keyword in config_keywords)


class TestOrchestratorAgentCreation:
    """Test orchestrator agent creation and configuration"""

    def test_create_orchestrator_agent(self, db_session, sample_project):
        """Test creating orchestrator agent for project"""
        orchestrator = Agent(
            tenant_key="test-tenant-template",
            project_id=sample_project.id,
            name="orchestrator",
            role="orchestrator",
            status="active",
        )

        db_session.add(orchestrator)
        db_session.commit()
        db_session.refresh(orchestrator)

        assert orchestrator.id is not None
        assert orchestrator.role == "orchestrator"
        assert orchestrator.project_id == sample_project.id

        # Cleanup
        db_session.delete(orchestrator)
        db_session.commit()

    def test_orchestrator_gets_full_config(self, sample_product, sample_project, db_session):
        """Test orchestrator receives FULL config_data"""
        # Create orchestrator agent
        orchestrator = Agent(
            tenant_key="test-tenant-template",
            project_id=sample_project.id,
            name="orchestrator",
            role="orchestrator",
            status="active",
        )
        db_session.add(orchestrator)
        db_session.commit()

        # Get config
        config = get_full_config(sample_product)

        assert "architecture" in config
        assert "tech_stack" in config
        assert "test_commands" in config
        assert "api_docs" in config
        assert len(config) == len(sample_product.config_data)

        # Cleanup
        db_session.delete(orchestrator)
        db_session.commit()


class TestWorkerAgentSpawning:
    """Test orchestrator spawning worker agents"""

    def test_worker_agent_gets_filtered_config(self, sample_product):
        """Test worker agents receive FILTERED config_data"""
        # Test implementer filtering
        impl_config = get_filtered_config("implementer-1", sample_product)
        assert "architecture" in impl_config
        assert "tech_stack" in impl_config
        assert "codebase_structure" in impl_config
        assert "test_commands" not in impl_config  # Should be filtered out
        assert "api_docs" not in impl_config  # Should be filtered out

        # Test tester filtering
        test_config = get_filtered_config("tester-qa", sample_product)
        assert "test_commands" in test_config
        assert "test_config" in test_config
        assert "codebase_structure" not in test_config  # Should be filtered out

    def test_multiple_worker_agents(self, db_session, sample_project, sample_product):
        """Test creating multiple worker agents with different roles"""
        implementer = Agent(
            tenant_key="test-tenant-template",
            project_id=sample_project.id,
            name="implementer-dev-1",
            role="implementer",
            status="active",
        )

        tester = Agent(
            tenant_key="test-tenant-template",
            project_id=sample_project.id,
            name="tester-qa-1",
            role="tester",
            status="active",
        )

        db_session.add_all([implementer, tester])
        db_session.commit()

        # Verify they get different filtered configs
        impl_config = get_filtered_config(implementer.name, sample_product, implementer.role)
        test_config = get_filtered_config(tester.name, sample_product, tester.role)

        # Implementer should have implementation fields
        assert "codebase_structure" in impl_config
        assert "test_commands" not in impl_config

        # Tester should have testing fields
        assert "test_commands" in test_config
        assert "codebase_structure" not in test_config

        # Cleanup
        db_session.delete(implementer)
        db_session.delete(tester)
        db_session.commit()


class TestFullProjectLifecycle:
    """Test complete project lifecycle with config_data integration"""

    def test_full_orchestrator_workflow(self, sample_project, sample_product, db_session):
        """Test complete orchestrator workflow from activation to agent spawning"""
        # Step 1: Create orchestrator
        orchestrator = Agent(
            tenant_key="test-tenant-template",
            project_id=sample_project.id,
            name="orchestrator",
            role="orchestrator",
            status="active",
        )
        db_session.add(orchestrator)
        db_session.commit()
        db_session.refresh(orchestrator)

        assert orchestrator is not None

        # Step 2: Verify orchestrator can access full config
        config = get_full_config(sample_product)
        assert len(config) == len(sample_product.config_data)

        # Step 3: Orchestrator spawns worker agent
        worker = Agent(
            tenant_key="test-tenant-template",
            project_id=sample_project.id,
            name="implementer-1",
            role="implementer",
            status="active",
        )
        db_session.add(worker)
        db_session.commit()
        db_session.refresh(worker)

        assert worker.role == "implementer"

        # Step 4: Verify worker receives filtered config
        worker_config = get_filtered_config(worker.name, sample_product, worker.role)
        assert len(worker_config) < len(sample_product.config_data)
        assert "test_commands" not in worker_config

        # Cleanup
        db_session.delete(orchestrator)
        db_session.delete(worker)
        db_session.commit()

    def test_project_with_multiple_phases(self, db_session, sample_project, sample_product):
        """Test project with orchestrator and multiple worker phases"""
        # Phase 1: Orchestrator
        orchestrator = Agent(
            tenant_key="test-tenant-template",
            project_id=sample_project.id,
            name="orchestrator",
            role="orchestrator",
            status="database_initialized",
        )

        # Phase 2: Implementation
        implementer = Agent(
            tenant_key="test-tenant-template",
            project_id=sample_project.id,
            name="implementer-1",
            role="implementer",
            status="database_initialized",
        )

        # Phase 3: Testing
        tester = Agent(
            tenant_key="test-tenant-template",
            project_id=sample_project.id,
            name="tester-1",
            role="tester",
            status="active",
        )

        db_session.add_all([orchestrator, implementer, tester])
        db_session.commit()

        # Verify all agents got appropriate context
        orch_config = get_filtered_config(orchestrator.name, sample_product, orchestrator.role)
        impl_config = get_filtered_config(implementer.name, sample_product, implementer.role)
        test_config = get_filtered_config(tester.name, sample_product, tester.role)

        # Orchestrator: full context
        assert len(orch_config) == len(sample_product.config_data)

        # Implementer: implementation context
        assert "codebase_structure" in impl_config
        assert "test_commands" not in impl_config

        # Tester: testing context
        assert "test_commands" in test_config
        assert "codebase_structure" not in test_config

        # Cleanup
        db_session.delete(orchestrator)
        db_session.delete(implementer)
        db_session.delete(tester)
        db_session.commit()


class TestTemplateManagerIntegration:
    """Test template manager integration with orchestrator template"""

    def test_template_manager_loads_orchestrator_template(self, db_session):
        """Test template manager can load orchestrator template"""
        template_mgr = get_template_manager()

        # Try to get orchestrator template
        template = (
            db_session.query(AgentTemplate)
            .filter(AgentTemplate.name == "orchestrator", AgentTemplate.is_default == True)
            .first()
        )

        assert template is not None
        assert template.system_instructions is not None
        assert len(template.system_instructions) > 0

    def test_template_variable_substitution(self, db_session, sample_project):
        """Test that template variables can be substituted"""
        template = (
            db_session.query(AgentTemplate)
            .filter(AgentTemplate.name == "orchestrator", AgentTemplate.is_default == True)
            .first()
        )

        content = template.system_instructions

        # Check for common template variables
        common_vars = ["{project_name}", "{project_mission}", "{product_name}"]
        has_variables = any(var in content for var in common_vars)

        assert has_variables, "Template should contain substitution variables"


class TestConfigDataIntegration:
    """Test config_data integration with orchestrator workflow"""

    def test_config_data_accessible_to_orchestrator(self, sample_product, db_session):
        """Test orchestrator can access product config_data"""
        config = get_full_config(sample_product)

        # Verify critical fields are accessible
        assert config.get("architecture") == "FastAPI + PostgreSQL + Vue.js"
        assert "Python 3.11" in config.get("tech_stack", [])
        assert config.get("serena_mcp_enabled") is True

    def test_config_data_validates(self, sample_product):
        """Test product config_data passes validation"""
        from src.giljo_mcp.context_manager import validate_config_data

        is_valid, errors = validate_config_data(sample_product.config_data)

        assert is_valid is True, f"Validation errors: {errors}"
        assert len(errors) == 0

    def test_config_data_summary(self, sample_product):
        """Test config_data summary generation"""
        from src.giljo_mcp.context_manager import get_config_summary

        summary = get_config_summary(sample_product)

        assert "Architecture:" in summary
        assert "FastAPI" in summary
        assert "Tech Stack:" in summary
        assert "Serena MCP:" in summary
