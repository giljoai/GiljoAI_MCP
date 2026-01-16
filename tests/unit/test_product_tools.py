"""
Unit tests for product configuration management tools

Tests get_product_config(), update_product_config(), and get_product_settings()
"""

import pytest

from src.giljo_mcp.models import Product, Project
from src.giljo_mcp.tools.product import (
    get_product_config,
    get_product_settings,
    update_product_config,
)


@pytest.fixture
async def product_with_config(db_session):
    """Create a product with full config_data for testing"""
    product = Product(
        tenant_key="test-tenant",
        name="Test Product",
        description="Product for testing",
        config_data={
            "architecture": "Microservices with REST API",
            "serena_mcp_enabled": True,
            "tech_stack": ["Python 3.13", "FastAPI", "PostgreSQL 18", "Vue 3"],
            "backend_framework": "FastAPI",
            "frontend_framework": "Vue 3 + Vuetify",
            "database_type": "PostgreSQL 18",
            "deployment_modes": ["localhost", "server"],
            "codebase_structure": {
                "src": "Main source code",
                "tests": "Test suites",
                "docs": "Documentation",
            },
            "critical_features": [
                "Multi-agent orchestration",
                "Database management",
                "API endpoints",
            ],
            "test_commands": ["pytest tests/", "pytest --cov=giljo_mcp"],
            "test_config": {
                "coverage": 80,
                "unit_tests": "tests/unit",
                "integration_tests": "tests/integration",
            },
            "known_issues": ["Context window management", "Error handling edge cases"],
            "api_docs": "docs/api/",
            "documentation_style": "Google style docstrings",
        },
    )
    db_session.add(product)
    await db_session.commit()
    return product


@pytest.fixture
async def project_with_product(db_session, product_with_config):
    """Create a project linked to a product"""
    project = Project(
        tenant_key=product_with_config.tenant_key,
        product_id=product_with_config.id,
        name="Test Project",
        description="Test project description",  # Added for NOT NULL constraint
        mission="Test project mission",
        status="active",
    )
    db_session.add(project)
    await db_session.commit()
    return project


# Agent fixtures removed - tests use agent_name/agent_role strings directly
# product.py tools don't query Agent model, they just use name/role for filtering


class TestGetProductConfigFiltered:
    """Test get_product_config() with filtered=True (role-based filtering)"""

    async def test_implementer_gets_filtered_config(self, db_session, project_with_product):
        """Test that implementer gets only relevant fields"""
        result = await get_product_config(
            project_id=str(project_with_product.id),
            filtered=True,
            agent_name="implementer-1",
            agent_role="implementer",
            session=db_session,
        )

        assert result["success"] is True
        config = result["config"]

        # Should have implementer-relevant fields
        assert "architecture" in config
        assert "tech_stack" in config
        assert "codebase_structure" in config
        assert "critical_features" in config
        assert "database_type" in config
        assert "backend_framework" in config
        assert "frontend_framework" in config
        assert "deployment_modes" in config
        assert "serena_mcp_enabled" in config  # Always included

        # Should NOT have fields outside implementer scope
        assert "test_commands" not in config
        assert "test_config" not in config
        assert "known_issues" not in config
        assert "api_docs" not in config
        assert "documentation_style" not in config

    async def test_tester_gets_filtered_config(self, db_session, project_with_product):
        """Test that tester gets only testing-relevant fields"""
        result = await get_product_config(
            project_id=str(project_with_product.id),
            filtered=True,
            agent_name="tester-qa",
            agent_role="tester",
            session=db_session,
        )

        assert result["success"] is True
        config = result["config"]

        # Should have tester-relevant fields
        assert "test_commands" in config
        assert "test_config" in config
        assert "critical_features" in config
        assert "known_issues" in config
        assert "tech_stack" in config
        assert "serena_mcp_enabled" in config  # Always included

        # Should NOT have implementation details
        assert "codebase_structure" not in config
        assert "deployment_modes" not in config
        assert "api_docs" not in config

    async def test_role_detection_from_agent_name(self, db_session, project_with_product):
        """Test that role is detected from agent name when not provided"""
        result = await get_product_config(
            project_id=str(project_with_product.id),
            filtered=True,
            agent_name="implementer-1",  # Role detected from name
            session=db_session,
        )

        assert result["success"] is True
        config = result["config"]

        # Should still get filtered config based on name
        assert "architecture" in config
        assert "tech_stack" in config
        assert "test_commands" not in config  # Not in implementer scope

    async def test_unknown_role_uses_default_filtering(self, db_session, project_with_product):
        """Test that unknown roles get analyzer-level filtering (default)"""
        # No need to create agent - product.py only uses agent_name/role strings
        result = await get_product_config(
            project_id=str(project_with_product.id),
            filtered=True,
            agent_name="custom-agent",
            agent_role="custom",
            session=db_session,
        )

        assert result["success"] is True
        config = result["config"]

        # Should get analyzer-level fields (default fallback)
        assert "architecture" in config
        assert "tech_stack" in config
        assert "codebase_structure" in config
        assert "critical_features" in config
        assert "known_issues" in config


class TestGetProductConfigUnfiltered:
    """Test get_product_config() with filtered=False (full config)"""

    async def test_orchestrator_gets_full_config(self, db_session, project_with_product):
        """Test that orchestrator with filtered=False gets ALL fields"""
        result = await get_product_config(
            project_id=str(project_with_product.id),
            filtered=False,
            session=db_session,
        )

        assert result["success"] is True
        config = result["config"]

        # Should have ALL fields from config_data
        assert "architecture" in config
        assert "tech_stack" in config
        assert "codebase_structure" in config
        assert "critical_features" in config
        assert "test_commands" in config
        assert "test_config" in config
        assert "known_issues" in config
        assert "api_docs" in config
        assert "documentation_style" in config
        assert "database_type" in config
        assert "backend_framework" in config
        assert "frontend_framework" in config
        assert "deployment_modes" in config
        assert "serena_mcp_enabled" in config

    async def test_worker_can_request_full_config(self, db_session, project_with_product):
        """Test that worker agents can request full config with filtered=False"""
        result = await get_product_config(
            project_id=str(project_with_product.id),
            filtered=False,
            session=db_session,
        )

        assert result["success"] is True
        config = result["config"]

        # Should get full config even as worker
        assert len(config) == 14  # All fields present
        assert "test_commands" in config  # Outside normal implementer scope


class TestGetProductConfigErrors:
    """Test error cases for get_product_config()"""

    async def test_missing_project_id(self, db_session):
        """Test error when project_id doesn't exist"""
        result = await get_product_config(
            project_id="non-existent-id",
            filtered=True,
            agent_name="implementer-1",
            session=db_session,
        )

        assert result["success"] is False
        assert "not found" in result["error"].lower()

    async def test_missing_product(self, db_session):
        """Test error when project has no product"""
        project_no_product = Project(
            tenant_key="test-tenant",
            product_id=None,  # No product
            name="Orphan Project",
            description="Test project without product",
            mission="Test",
            status="active",
        )
        db_session.add(project_no_product)
        await db_session.commit()

        result = await get_product_config(
            project_id=str(project_no_product.id),
            filtered=True,
            agent_name="implementer-1",
            session=db_session,
        )

        assert result["success"] is False
        assert "no product" in result["error"].lower()

    async def test_filtered_requires_agent_name(self, db_session, project_with_product):
        """Test that filtered=True requires agent_name parameter"""
        result = await get_product_config(
            project_id=str(project_with_product.id),
            filtered=True,
            # Missing agent_name
            session=db_session,
        )

        assert result["success"] is False
        assert "agent_name required" in result["error"].lower()

    async def test_empty_config_data(self, db_session):
        """Test handling when config_data is empty"""
        product_empty = Product(
            tenant_key="test-tenant",
            name="Empty Product",
            description="No config",
            config_data={},  # Empty config
        )
        db_session.add(product_empty)
        await db_session.commit()  # Commit product first to get its ID
        await db_session.refresh(product_empty)  # Refresh to get the ID

        project_empty = Project(
            tenant_key=product_empty.tenant_key,
            product_id=product_empty.id,  # Now product_empty.id is available
            name="Test Project",
            description="Test project with empty config",
            mission="Test",
            status="active",
        )
        db_session.add(project_empty)
        await db_session.commit()

        result = await get_product_config(
            project_id=str(project_empty.id),
            filtered=False,
            session=db_session,
        )

        assert result["success"] is True
        assert result["config"] == {}


class TestUpdateProductConfig:
    """Test update_product_config() function"""

    async def test_merge_mode_updates_existing_fields(self, db_session, project_with_product, product_with_config):
        """Test that merge=True updates existing fields without removing others"""
        updates = {
            "architecture": "Updated Microservices Architecture",
            "database_type": "PostgreSQL 19",
        }

        result = await update_product_config(
            project_id=str(project_with_product.id),
            config_updates=updates,
            merge=True,
            session=db_session,
        )

        assert result["success"] is True
        assert result["updated_fields"] == ["architecture", "database_type"]

        # Verify in database
        await db_session.refresh(product_with_config)
        assert product_with_config.config_data["architecture"] == updates["architecture"]
        assert product_with_config.config_data["database_type"] == updates["database_type"]

        # Other fields should remain unchanged
        assert "tech_stack" in product_with_config.config_data
        assert "critical_features" in product_with_config.config_data

    async def test_merge_mode_adds_new_fields(self, db_session, project_with_product, product_with_config):
        """Test that merge=True adds new fields to config"""
        updates = {
            "new_field": "New Value",
            "monitoring": {"enabled": True, "tool": "Prometheus"},
        }

        result = await update_product_config(
            project_id=str(project_with_product.id),
            config_updates=updates,
            merge=True,
            session=db_session,
        )

        assert result["success"] is True
        assert "new_field" in result["updated_fields"]
        assert "monitoring" in result["updated_fields"]

        # Verify in database
        await db_session.refresh(product_with_config)
        assert product_with_config.config_data["new_field"] == "New Value"
        assert product_with_config.config_data["monitoring"]["enabled"] is True

    async def test_replace_mode_overwrites_config(self, db_session, project_with_product, product_with_config):
        """Test that merge=False replaces entire config"""
        new_config = {
            "architecture": "New Architecture",
            "serena_mcp_enabled": True,
            "tech_stack": ["Python", "React"],
        }

        result = await update_product_config(
            project_id=str(project_with_product.id),
            config_updates=new_config,
            merge=False,
            session=db_session,
        )

        assert result["success"] is True

        # Verify in database - should only have new fields
        await db_session.refresh(product_with_config)
        assert product_with_config.config_data == new_config

        # Old fields should be gone
        assert "critical_features" not in product_with_config.config_data
        assert "test_commands" not in product_with_config.config_data

    async def test_deep_merge_nested_objects(self, db_session, project_with_product, product_with_config):
        """Test that nested objects are deep merged"""
        updates = {
            "codebase_structure": {
                "api": "API layer",  # New field in nested object
                # Should keep existing: src, tests, docs
            },
        }

        result = await update_product_config(
            project_id=str(project_with_product.id),
            config_updates=updates,
            merge=True,
            session=db_session,
        )

        assert result["success"] is True

        # Verify deep merge
        await db_session.refresh(product_with_config)
        structure = product_with_config.config_data["codebase_structure"]
        assert structure["api"] == "API layer"  # New field added
        assert structure["src"] == "Main source code"  # Existing preserved
        assert structure["tests"] == "Test suites"  # Existing preserved


class TestUpdateProductConfigValidation:
    """Test validation errors in update_product_config()"""

    async def test_missing_required_field_architecture(self, db_session, project_with_product):
        """Test validation fails if architecture is missing in replace mode"""
        invalid_config = {
            "serena_mcp_enabled": True,
            "tech_stack": ["Python"],
            # Missing required: architecture
        }

        result = await update_product_config(
            project_id=str(project_with_product.id),
            config_updates=invalid_config,
            merge=False,  # Replace mode
            session=db_session,
        )

        assert result["success"] is False
        assert "validation" in result["error"].lower()
        assert "architecture" in result["error"].lower()

    async def test_missing_required_field_serena_mcp_enabled(self, db_session, project_with_product):
        """Test validation fails if serena_mcp_enabled is missing in replace mode"""
        invalid_config = {
            "architecture": "Test",
            "tech_stack": ["Python"],
            # Missing required: serena_mcp_enabled
        }

        result = await update_product_config(
            project_id=str(project_with_product.id),
            config_updates=invalid_config,
            merge=False,  # Replace mode
            session=db_session,
        )

        assert result["success"] is False
        assert "validation" in result["error"].lower()
        assert "serena_mcp_enabled" in result["error"].lower()

    async def test_invalid_type_tech_stack(self, db_session, project_with_product):
        """Test validation fails if tech_stack is not an array"""
        invalid_config = {
            "architecture": "Test",
            "serena_mcp_enabled": True,
            "tech_stack": "Python, FastAPI",  # Should be array, not string
        }

        result = await update_product_config(
            project_id=str(project_with_product.id),
            config_updates=invalid_config,
            merge=False,
            session=db_session,
        )

        assert result["success"] is False
        assert "validation" in result["error"].lower()
        assert "tech_stack must be an array" in result["error"]

    async def test_invalid_type_codebase_structure(self, db_session, project_with_product):
        """Test validation fails if codebase_structure is not an object"""
        invalid_config = {
            "architecture": "Test",
            "serena_mcp_enabled": True,
            "codebase_structure": "Some string",  # Should be object
        }

        result = await update_product_config(
            project_id=str(project_with_product.id),
            config_updates=invalid_config,
            merge=False,
            session=db_session,
        )

        assert result["success"] is False
        assert "validation" in result["error"].lower()
        assert "codebase_structure must be an object" in result["error"]

    async def test_invalid_type_serena_mcp_enabled(self, db_session, project_with_product):
        """Test validation fails if serena_mcp_enabled is not boolean"""
        invalid_config = {
            "architecture": "Test",
            "serena_mcp_enabled": "yes",  # Should be boolean
        }

        result = await update_product_config(
            project_id=str(project_with_product.id),
            config_updates=invalid_config,
            merge=False,
            session=db_session,
        )

        assert result["success"] is False
        assert "validation" in result["error"].lower()
        assert "serena_mcp_enabled must be a boolean" in result["error"]

    async def test_merge_mode_allows_partial_updates(self, db_session, project_with_product, product_with_config):
        """Test that merge mode doesn't require all fields (partial updates OK)"""
        partial_update = {
            "database_type": "PostgreSQL 20",  # Just one field
        }

        result = await update_product_config(
            project_id=str(project_with_product.id),
            config_updates=partial_update,
            merge=True,
            session=db_session,
        )

        # Should succeed with merge mode
        assert result["success"] is True
        await db_session.refresh(product_with_config)
        assert product_with_config.config_data["database_type"] == "PostgreSQL 20"


class TestGetProductSettings:
    """Test get_product_settings() alias function"""

    async def test_settings_alias_returns_full_config(self, db_session, project_with_product, product_with_config):
        """Test that get_product_settings() returns unfiltered config"""
        result = await get_product_settings(project_id=str(project_with_product.id), session=db_session)

        assert result["success"] is True
        config = result["config"]

        # Should have ALL fields (same as filtered=False)
        assert len(config) == 14
        assert "architecture" in config
        assert "test_commands" in config
        assert "api_docs" in config
        assert "serena_mcp_enabled" in config

    async def test_settings_alias_for_orchestrators(self, db_session, project_with_product):
        """Test that orchestrators use get_product_settings() for full access"""
        result = await get_product_settings(project_id=str(project_with_product.id), session=db_session)

        assert result["success"] is True

        # Compare with filtered version
        filtered_result = await get_product_config(
            project_id=str(project_with_product.id),
            filtered=True,
            agent_name="orchestrator",
            agent_role="orchestrator",
            session=db_session,
        )

        # Both should return full config for orchestrator
        assert result["config"] == filtered_result["config"]
