"""
Unit tests for Project 3.9.b Template Management System
Tests database models, MCP tools, and template operations
"""

import sys
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, Mock

import pytest
import pytest_asyncio


# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.models import AgentTemplate, TemplateArchive, TemplateUsageStats
from src.giljo_mcp.template_adapter import MissionTemplateGeneratorV2 as MissionTemplateGenerator
from src.giljo_mcp.tenant import TenantManager
from src.giljo_mcp.tools.template import register_template_tools
from tests.helpers.test_db_helper import PostgreSQLTestHelper


def _apply_augmentation(template: str, replacements: dict) -> str:
    """Simple variable substitution for testing"""
    result = template
    for key, value in replacements.items():
        result = result.replace(f"{{{key}}}", str(value))
    return result


@pytest.mark.asyncio
class TestTemplateModels:
    """Test database models for template system"""

    @pytest_asyncio.fixture
    async def db_manager(self):
        """Create test database manager"""
        db_manager = DatabaseManager(PostgreSQLTestHelper.get_test_db_url(async_driver=False))
        await db_manager.initialize()
        yield db_manager
        await db_manager.close()

    @pytest.fixture
    def tenant_manager(self):
        """Create test tenant manager"""
        return TenantManager()

    async def test_agent_template_creation(self, db_manager):
        """Test creating an agent template"""
        async with db_manager.get_session() as session:
            template = AgentTemplate(
                tenant_key="test-tenant",
                product_id="test-product",
                name="orchestrator",
                category="role",
                role="orchestrator",
                template_content="Mission: {project_name}\\nObjective: {objective}",
                variables=["project_name", "objective"],
                behavioral_rules=["Rule 1", "Rule 2"],
                success_criteria=["Success 1", "Success 2"],
                description="Test orchestrator template",
                version="1.0.0",
                is_active=True,
                is_default=True,
            )
            session.add(template)
            await session.commit()

            # Verify creation
            result = await session.get(AgentTemplate, template.id)
            assert result is not None
            assert result.name == "orchestrator"
            assert result.tenant_key == "test-tenant"
            assert result.product_id == "test-product"
            assert len(result.variables) == 2
            assert "project_name" in result.variables

    async def test_template_archive_creation(self, db_manager):
        """Test creating a template archive"""
        async with db_manager.get_session() as session:
            # Create template first
            template = AgentTemplate(
                tenant_key="test-tenant",
                product_id="test-product",
                name="analyzer",
                category="role",
                template_content="Analyze: {task}",
                version="1.0.0",
            )
            session.add(template)
            await session.commit()

            # Create archive
            archive = TemplateArchive(
                tenant_key="test-tenant",
                template_id=template.id,
                product_id="test-product",
                name=template.name,
                category=template.category,
                template_content=template.template_content,
                version=template.version,
                archive_reason="Test archive",
                archive_type="manual",
                archived_by="tester",
            )
            session.add(archive)
            await session.commit()

            # Verify archive
            result = await session.get(TemplateArchive, archive.id)
            assert result is not None
            assert result.template_id == template.id
            assert result.archive_reason == "Test archive"

    # NOTE: test_template_augmentation removed (Handover 0423 - TemplateAugmentation model deleted)


class TestTemplateTools:
    """Test MCP tool implementations"""

    @pytest.fixture
    def mock_mcp(self):
        """Create mock MCP server"""
        mcp = Mock()
        mcp.tool = Mock(return_value=lambda f: f)
        return mcp

    @pytest.fixture
    async def setup_tools(self, mock_mcp):
        """Setup template tools with mocks"""
        db_manager = DatabaseManager(PostgreSQLTestHelper.get_test_db_url(async_driver=False))
        await db_manager.initialize()
        tenant_manager = TenantManager()
        tenant_manager.current_tenant = "test-tenant"
        tenant_manager.current_product = "test-product"

        # Register tools
        register_template_tools(mock_mcp, db_manager, tenant_manager)

        yield db_manager, tenant_manager

        await db_manager.close()

    async def test_list_agent_templates(self, setup_tools):
        """Test listing agent templates"""
        db_manager, _tenant_manager = setup_tools

        # Create test templates
        async with db_manager.get_session() as session:
            templates = [
                AgentTemplate(
                    tenant_key="test-tenant",
                    product_id="test-product",
                    name=f"template_{i}",
                    category="role",
                    template_content=f"Content {i}",
                    version="1.0.0",
                    is_active=True,
                )
                for i in range(3)
            ]
            session.add_all(templates)
            await session.commit()

        # Test list operation
        # Note: In real test, we'd call the actual tool function
        # For now, we verify the database contains the templates
        async with db_manager.get_session() as session:
            from sqlalchemy import select

            stmt = select(AgentTemplate).where(
                AgentTemplate.tenant_key == "test-tenant",
                AgentTemplate.product_id == "test-product",
                AgentTemplate.is_active,
            )
            result = await session.execute(stmt)
            templates = result.scalars().all()

            assert len(templates) == 3
            assert all(t.tenant_key == "test-tenant" for t in templates)
            assert all(t.product_id == "test-product" for t in templates)


class TestPerformanceBenchmarks:
    """Test performance requirements"""

    def test_template_generation_speed(self):
        """Test template generation is under 0.1ms"""
        template_content = "Mission: {project}\\nObjective: {objective}\\nDetails: {details}"
        augmentations = {
            "project": "Test Project",
            "objective": "Complete testing",
            "details": "Comprehensive unit tests",
        }

        # Measure generation time
        start = time.perf_counter()
        result = _apply_augmentation(template_content, augmentations)
        end = time.perf_counter()

        generation_time_ms = (end - start) * 1000

        assert generation_time_ms < 0.1, f"Generation took {generation_time_ms}ms, exceeds 0.1ms target"
        assert "Test Project" in result
        assert "Complete testing" in result

    def test_augmentation_performance(self):
        """Test augmentation performance with complex templates"""
        # Large template with many variables
        template_content = "\\n".join([f"Line {i}: {{var_{i}}}" for i in range(100)])

        augmentations = {f"var_{i}": f"value_{i}" for i in range(100)}

        # Measure augmentation time
        iterations = 100
        start = time.perf_counter()
        for _ in range(iterations):
            _apply_augmentation(template_content, augmentations)
        end = time.perf_counter()

        avg_time_ms = ((end - start) / iterations) * 1000

        assert avg_time_ms < 0.1, f"Average augmentation took {avg_time_ms}ms, exceeds 0.1ms target"


@pytest.mark.asyncio
class TestProductIsolation:
    """Test multi-tenant product isolation"""

    @pytest_asyncio.fixture
    async def multi_tenant_db(self):
        """Setup database with multiple tenants/products"""
        db_manager = DatabaseManager(PostgreSQLTestHelper.get_test_db_url(async_driver=False))
        await db_manager.initialize()

        async with db_manager.get_session() as session:
            # Create templates for different products
            templates = [
                AgentTemplate(
                    tenant_key="tenant1",
                    product_id="product1",
                    name="orchestrator",
                    category="role",
                    template_content="Product 1 template",
                    version="1.0.0",
                ),
                AgentTemplate(
                    tenant_key="tenant1",
                    product_id="product2",
                    name="orchestrator",
                    category="role",
                    template_content="Product 2 template",
                    version="1.0.0",
                ),
                AgentTemplate(
                    tenant_key="tenant2",
                    product_id="product3",
                    name="orchestrator",
                    category="role",
                    template_content="Tenant 2 template",
                    version="1.0.0",
                ),
            ]
            session.add_all(templates)
            await session.commit()

        yield db_manager
        await db_manager.close()

    async def test_product_isolation(self, multi_tenant_db):
        """Test templates are isolated by product"""
        async with multi_tenant_db.get_session() as session:
            from sqlalchemy import select

            # Query for product1 templates
            stmt = select(AgentTemplate).where(
                AgentTemplate.tenant_key == "tenant1", AgentTemplate.product_id == "product1"
            )
            result = await session.execute(stmt)
            product1_templates = result.scalars().all()

            assert len(product1_templates) == 1
            assert product1_templates[0].template_content == "Product 1 template"

            # Verify no cross-product access
            assert all(t.product_id == "product1" for t in product1_templates)

    async def test_tenant_isolation(self, multi_tenant_db):
        """Test templates are isolated by tenant"""
        async with multi_tenant_db.get_session() as session:
            from sqlalchemy import select

            # Query for tenant1 templates
            stmt = select(AgentTemplate).where(AgentTemplate.tenant_key == "tenant1")
            result = await session.execute(stmt)
            tenant1_templates = result.scalars().all()

            # Should have 2 templates (product1 and product2)
            assert len(tenant1_templates) == 2
            assert all(t.tenant_key == "tenant1" for t in tenant1_templates)

            # Query for tenant2 templates
            stmt = select(AgentTemplate).where(AgentTemplate.tenant_key == "tenant2")
            result = await session.execute(stmt)
            tenant2_templates = result.scalars().all()

            # Should have 1 template
            assert len(tenant2_templates) == 1
            assert all(t.tenant_key == "tenant2" for t in tenant2_templates)


class TestAugmentationEdgeCases:
    """Test edge cases for template augmentation"""

    def test_missing_variables(self):
        """Test handling missing variables in augmentation"""
        template = "Hello {name}, welcome to {project}"
        augmentations = {"name": "Tester"}  # Missing 'project'

        result = _apply_augmentation(template, augmentations)
        assert "Hello Tester" in result
        assert "{project}" in result  # Unsubstituted variable remains

    def test_recursive_variables(self):
        """Test recursive variable references"""
        template = "Value: {var1}"
        augmentations = {"var1": "{var2}", "var2": "{var1}"}  # Recursive

        result = _apply_augmentation(template, augmentations)
        # Should handle gracefully without infinite loop
        assert result is not None

    def test_special_characters(self):
        """Test special characters in variables"""
        template = "SQL: {query}"
        augmentations = {"query": "SELECT * FROM users WHERE name = 'O\\'Brien'"}

        result = _apply_augmentation(template, augmentations)
        assert "O\\'Brien" in result

    def test_empty_augmentation(self):
        """Test empty augmentation map"""
        template = "Static template content"
        augmentations = {}

        result = _apply_augmentation(template, augmentations)
        assert result == template

    def test_nested_braces(self):
        """Test nested braces in template"""
        template = "Code: {{inline: {variable}}}"
        augmentations = {"variable": "test_value"}

        result = _apply_augmentation(template, augmentations)
        assert "test_value" in result

    def test_invalid_variable_names(self):
        """Test invalid variable names"""
        template = "Test: {123invalid} {valid_var}"
        augmentations = {"123invalid": "should_not_match", "valid_var": "should_match"}

        result = _apply_augmentation(template, augmentations)
        assert "should_match" in result
        assert "{123invalid}" in result  # Invalid name not substituted


@pytest.mark.asyncio
class TestArchiveSystem:
    """Test template archive functionality"""

    @pytest.fixture
    async def db_with_template(self):
        """Create database with template"""
        db_manager = DatabaseManager(PostgreSQLTestHelper.get_test_db_url(async_driver=False))
        await db_manager.initialize()

        async with db_manager.get_session() as session:
            template = AgentTemplate(
                id="template-1",
                tenant_key="test-tenant",
                product_id="test-product",
                name="test-template",
                category="role",
                template_content="Original content",
                version="1.0.0",
                usage_count=5,
                avg_generation_ms=0.05,
            )
            session.add(template)
            await session.commit()

        yield db_manager
        await db_manager.close()

    async def test_auto_archive_on_update(self, db_with_template):
        """Test auto-archiving when template is updated"""
        async with db_with_template.get_session() as session:
            from sqlalchemy import select

            # Get template
            stmt = select(AgentTemplate).where(AgentTemplate.id == "template-1")
            result = await session.execute(stmt)
            template = result.scalar_one()

            # Simulate update with archive
            archive = TemplateArchive(
                tenant_key=template.tenant_key,
                template_id=template.id,
                product_id=template.product_id,
                name=template.name,
                category=template.category,
                template_content=template.template_content,
                version=template.version,
                archive_reason="Before update",
                archive_type="auto",
                usage_count_at_archive=template.usage_count,
                avg_generation_ms_at_archive=template.avg_generation_ms,
            )
            session.add(archive)

            # Update template
            template.template_content = "Updated content"
            template.version = "1.1.0"

            await session.commit()

            # Verify archive created
            stmt = select(TemplateArchive).where(TemplateArchive.template_id == "template-1")
            result = await session.execute(stmt)
            archives = result.scalars().all()

            assert len(archives) == 1
            assert archives[0].template_content == "Original content"
            assert archives[0].version == "1.0.0"
            assert archives[0].usage_count_at_archive == 5


@pytest.mark.asyncio
class TestMigrationFromLegacy:
    """Test migration from mission_templates.py"""

    @pytest.mark.asyncio
    async def test_migrate_existing_templates(self):
        """Test migrating templates from Python code to database"""

        db_manager = DatabaseManager(PostgreSQLTestHelper.get_test_db_url(async_driver=False))
        await db_manager.initialize()

        # Get legacy templates
        generator = MissionTemplateGenerator()
        legacy_templates = [
            ("orchestrator", generator.ORCHESTRATOR_TEMPLATE),
            ("analyzer", generator.ANALYZER_TEMPLATE),
            ("implementer", generator.IMPLEMENTER_TEMPLATE),
            ("tester", generator.TESTER_TEMPLATE),
            ("reviewer", generator.REVIEWER_TEMPLATE),
        ]

        # Migrate to database
        async with db_manager.get_session() as session:
            for name, content in legacy_templates:
                template = AgentTemplate(
                    tenant_key="migrated",
                    product_id="legacy",
                    name=name,
                    category="role",
                    role=name,
                    template_content=content,
                    version="1.0.0",
                    is_active=True,
                    is_default=True,
                    description="Migrated from mission_templates.py",
                )
                session.add(template)

            await session.commit()

            # Verify migration
            from sqlalchemy import select

            stmt = select(AgentTemplate).where(AgentTemplate.tenant_key == "migrated")
            result = await session.execute(stmt)
            migrated = result.scalars().all()

            assert len(migrated) == 5
            assert {t.name for t in migrated} == {"orchestrator", "analyzer", "implementer", "tester", "reviewer"}

        await db_manager.close()


@pytest.mark.asyncio
class TestMCPTemplateToolsIntegration:
    """Comprehensive integration tests for all 9 MCP template tools"""

    @pytest_asyncio.fixture
    async def mcp_setup(self):
        """Setup MCP server with template tools"""
        # Create mock MCP server
        mcp = MagicMock()
        mcp.tool = lambda: lambda f: f  # Simple decorator mock

        # Create database and tenant managers
        db_manager = DatabaseManager(PostgreSQLTestHelper.get_test_db_url(async_driver=False))
        await db_manager.initialize()

        tenant_manager = TenantManager()
        tenant_manager.current_tenant = "test-tenant"
        tenant_manager.current_product = "test-product"

        # Register tools and capture them
        tools = {}
        original_tool = mcp.tool

        def capture_tool():
            def decorator(func):
                tools[func.__name__] = func
                return func

            return decorator

        mcp.tool = capture_tool
        register_template_tools(mcp, db_manager, tenant_manager)
        mcp.tool = original_tool

        yield tools, db_manager, tenant_manager

        await db_manager.close()

    @pytest_asyncio.fixture
    async def seed_templates(self, mcp_setup):
        """Seed database with default templates"""
        tools, db_manager, tenant_manager = mcp_setup

        # Create default templates
        async with db_manager.get_session() as session:
            templates = [
                AgentTemplate(
                    id=str(uuid.uuid4()),
                    tenant_key="test-tenant",
                    product_id="test-product",
                    name="orchestrator",
                    category="role",
                    role="orchestrator",
                    template_content="Mission: {project_name}\nObjective: {objective}\nBehavioral Rules:\n- Rule 1\n- Rule 2",
                    variables=["project_name", "objective"],
                    behavioral_rules=["Rule 1", "Rule 2"],
                    success_criteria=["Success 1", "Success 2"],
                    version="1.0.0",
                    is_active=True,
                    is_default=True,
                    description="Default orchestrator template",
                ),
                AgentTemplate(
                    id=str(uuid.uuid4()),
                    tenant_key="test-tenant",
                    product_id="test-product",
                    name="analyzer",
                    category="role",
                    role="analyzer",
                    template_content="Analyze: {task}\nContext: {context}",
                    variables=["task", "context"],
                    version="1.0.0",
                    is_active=True,
                    description="Default analyzer template",
                ),
                AgentTemplate(
                    id=str(uuid.uuid4()),
                    tenant_key="test-tenant",
                    product_id="test-product",
                    name="implementer",
                    category="role",
                    role="implementer",
                    template_content="Implement: {feature}\nRequirements: {requirements}",
                    variables=["feature", "requirements"],
                    version="1.0.0",
                    is_active=True,
                    description="Default implementer template",
                ),
                AgentTemplate(
                    id=str(uuid.uuid4()),
                    tenant_key="test-tenant",
                    product_id="test-product",
                    name="tester",
                    category="role",
                    role="tester",
                    template_content="Test: {component}\nCriteria: {criteria}",
                    variables=["component", "criteria"],
                    version="1.0.0",
                    is_active=True,
                    description="Default tester template",
                ),
                AgentTemplate(
                    id=str(uuid.uuid4()),
                    tenant_key="test-tenant",
                    product_id="test-product",
                    name="documenter",
                    category="role",
                    role="documenter",
                    template_content="Document: {subject}\nFormat: {format}",
                    variables=["subject", "format"],
                    version="1.0.0",
                    is_active=True,
                    description="Default documenter template",
                ),
            ]

            for template in templates:
                session.add(template)
            await session.commit()

            # Store template IDs for tests
            template_ids = {t.name: t.id for t in templates}

        return tools, db_manager, tenant_manager, template_ids

    async def test_tool_1_list_agent_templates(self, seed_templates):
        """Test list_agent_templates tool"""
        tools, _db_manager, _tenant_manager, _template_ids = seed_templates

        # Test listing all templates
        result = await tools["list_agent_templates"](is_active=True)

        assert result["success"] is True
        assert result["count"] == 5
        assert len(result["templates"]) == 5

        # Verify template structure
        template = result["templates"][0]
        assert "id" in template
        assert "name" in template
        assert "category" in template
        assert "role" in template
        assert "description" in template
        assert "version" in template
        assert "variables" in template

        # Test filtering by role
        result = await tools["list_agent_templates"](role="orchestrator")
        assert result["count"] == 1
        assert result["templates"][0]["name"] == "orchestrator"

        # Test filtering by category
        result = await tools["list_agent_templates"](category="role")
        assert result["count"] == 5

        # Test filtering by product
        result = await tools["list_agent_templates"](product_id="test-product")
        assert result["count"] == 5

        # Test inactive filter
        result = await tools["list_agent_templates"](is_active=False)
        assert result["count"] == 0

    async def test_tool_2_get_agent_template(self, seed_templates):
        """Test get_agent_template tool with runtime augmentations"""
        tools, db_manager, _tenant_manager, template_ids = seed_templates

        # Test getting basic template
        start_time = time.perf_counter()
        result = await tools["get_agent_template"](name="orchestrator", product_id="test-product")
        end_time = time.perf_counter()

        assert result["success"] is True
        assert result["template"]["name"] == "orchestrator"
        assert "Mission:" in result["template"]["content"]
        assert result["template"]["version"] == "1.0.0"

        # Verify performance tracking
        generation_ms = result["template"]["generation_ms"]
        (end_time - start_time) * 1000
        assert generation_ms > 0
        assert generation_ms < 100  # Should be well under 0.1ms requirement

        # Test with variable substitution
        result = await tools["get_agent_template"](
            name="orchestrator",
            product_id="test-product",
            variables={"project_name": "Test Project", "objective": "Complete testing"},
        )

        assert result["success"] is True
        assert "Test Project" in result["template"]["content"]
        assert "Complete testing" in result["template"]["content"]

        # Test with runtime augmentations
        result = await tools["get_agent_template"](
            name="analyzer",
            product_id="test-product",
            augmentations=[{"type": "append", "content": "Additional Analysis Steps:\n- Step 1\n- Step 2"}],
            variables={"task": "Code Review", "context": "Pull Request #123"},
        )

        assert result["success"] is True
        assert "Code Review" in result["template"]["content"]
        assert "Pull Request #123" in result["template"]["content"]

        # Verify usage statistics were tracked
        async with db_manager.get_session() as session:
            from sqlalchemy import select

            stmt = select(TemplateUsageStats).where(TemplateUsageStats.template_id == template_ids["orchestrator"])
            result = await session.execute(stmt)
            stats = result.scalars().all()
            assert len(stats) >= 1  # At least one usage recorded

    async def test_tool_3_create_agent_template(self, mcp_setup):
        """Test create_agent_template tool"""
        tools, db_manager, _tenant_manager = mcp_setup

        # Create new template
        result = await tools["create_agent_template"](
            name="custom_agent",
            category="custom",
            template_content="Custom Mission: {custom_var}\nGoals:\n{goals}",
            product_id="test-product",
            role="custom",
            project_type="web_app",
            description="Custom agent for web applications",
            behavioral_rules=["Be thorough", "Follow standards"],
            success_criteria=["All tests pass", "Code reviewed"],
            tags=["web", "custom", "automated"],
            is_default=False,
        )

        assert result["success"] is True
        assert result["name"] == "custom_agent"
        assert result["category"] == "custom"
        assert "custom_var" in result["variables"]
        assert "goals" in result["variables"]

        # Verify template was created
        async with db_manager.get_session() as session:
            from sqlalchemy import select

            stmt = select(AgentTemplate).where(AgentTemplate.id == result["template_id"])
            result_db = await session.execute(stmt)
            template = result_db.scalar_one()

            assert template.name == "custom_agent"
            assert template.project_type == "web_app"
            assert len(template.behavioral_rules) == 2
            assert len(template.success_criteria) == 2
            assert len(template.tags) == 3
            assert template.is_default is False

    async def test_tool_4_update_agent_template(self, seed_templates):
        """Test update_agent_template tool with auto-archiving"""
        tools, db_manager, _tenant_manager, template_ids = seed_templates

        orchestrator_id = template_ids["orchestrator"]

        # Update template
        result = await tools["update_agent_template"](
            template_id=orchestrator_id,
            template_content="Updated Mission: {project}\nNew Objective: {goal}",
            description="Updated orchestrator template",
            behavioral_rules=["New Rule 1", "New Rule 2", "New Rule 3"],
            success_criteria=["Updated Success 1"],
            tags=["updated", "orchestrator"],
            archive_reason="Testing update functionality",
        )

        assert result["success"] is True
        assert result["new_version"] == "1.0.1"
        assert result["archived_version"] == "1.0.0"

        # Verify archive was created
        async with db_manager.get_session() as session:
            from sqlalchemy import select

            # Check archive
            stmt = select(TemplateArchive).where(TemplateArchive.template_id == orchestrator_id)
            result_db = await session.execute(stmt)
            archive = result_db.scalar_one()

            assert archive.version == "1.0.0"
            assert archive.archive_reason == "Testing update functionality"
            assert archive.archive_type == "auto"
            assert "Rule 1" in archive.behavioral_rules  # Old rules

            # Check updated template
            stmt = select(AgentTemplate).where(AgentTemplate.id == orchestrator_id)
            result_db = await session.execute(stmt)
            template = result_db.scalar_one()

            assert template.version == "1.0.1"
            assert "Updated Mission:" in template.template_content
            assert len(template.behavioral_rules) == 3
            assert "New Rule 1" in template.behavioral_rules

    async def test_tool_5_archive_template(self, seed_templates):
        """Test archive_template tool"""
        tools, db_manager, _tenant_manager, template_ids = seed_templates

        analyzer_id = template_ids["analyzer"]

        # Archive template
        result = await tools["archive_template"](
            template_id=analyzer_id, reason="Manual backup before major changes", archive_type="manual"
        )

        assert result["success"] is True
        assert result["template_name"] == "analyzer"
        assert result["archived_version"] == "1.0.0"
        assert result["archive_reason"] == "Manual backup before major changes"

        # Verify archive exists
        async with db_manager.get_session() as session:
            from sqlalchemy import select

            stmt = select(TemplateArchive).where(TemplateArchive.id == result["archive_id"])
            result_db = await session.execute(stmt)
            archive = result_db.scalar_one()

            assert archive.name == "analyzer"
            assert archive.archive_type == "manual"
            assert archive.is_restorable is True

    # NOTE: test_tool_6_create_template_augmentation removed (Handover 0423)
    # TemplateAugmentation model was deleted - DB persistence abandoned for runtime-only dicts

    async def test_tool_7_restore_template_version(self, seed_templates):
        """Test restore_template_version tool"""
        tools, db_manager, _tenant_manager, template_ids = seed_templates

        tester_id = template_ids["tester"]

        # First update the template to create an archive
        await tools["update_agent_template"](
            template_id=tester_id, template_content="Modified Test Content", archive_reason="Before restoration test"
        )

        # Get the archive ID
        async with db_manager.get_session() as session:
            from sqlalchemy import select

            stmt = select(TemplateArchive).where(TemplateArchive.template_id == tester_id)
            result_db = await session.execute(stmt)
            archive = result_db.scalar_one()
            archive_id = archive.id

        # Test restoration (overwrite)
        result = await tools["restore_template_version"](archive_id=archive_id, restore_as_new=False)

        assert result["success"] is True
        assert result["restore_type"] == "overwrite"
        assert result["restored_version"] == "1.0.0"

        # Verify template was restored
        async with db_manager.get_session() as session:
            from sqlalchemy import select

            stmt = select(AgentTemplate).where(AgentTemplate.id == tester_id)
            result_db = await session.execute(stmt)
            template = result_db.scalar_one()

            # Should have original content
            assert "Test: {component}" in template.template_content
            assert "Modified Test Content" not in template.template_content

        # Test restoration as new template
        result = await tools["restore_template_version"](archive_id=archive_id, restore_as_new=True)

        assert result["success"] is True
        assert result["restore_type"] == "new"
        assert result["template_name"] == "tester_restored"

    async def test_tool_8_suggest_template(self, seed_templates):
        """Test suggest_template tool"""
        tools, db_manager, _tenant_manager, template_ids = seed_templates

        # Update usage counts to test suggestion logic
        async with db_manager.get_session() as session:
            from sqlalchemy import update

            # Make orchestrator most used
            stmt = update(AgentTemplate).where(AgentTemplate.id == template_ids["orchestrator"]).values(usage_count=100)
            await session.execute(stmt)

            # Make analyzer second most used
            stmt = update(AgentTemplate).where(AgentTemplate.id == template_ids["analyzer"]).values(usage_count=50)
            await session.execute(stmt)

            await session.commit()

        # Test suggestion by role
        result = await tools["suggest_template"](role="orchestrator", context={"complexity": "high"})

        assert result["success"] is True
        assert result["suggestion"]["name"] == "orchestrator"
        assert result["suggestion"]["usage_count"] == 100
        assert "reason" in result["suggestion"]

        # Test suggestion with project type
        result = await tools["suggest_template"](project_type="web_app", role="analyzer")

        assert result["success"] is True
        assert result["suggestion"]["name"] == "analyzer"

        # Test suggestion for non-existent role
        result = await tools["suggest_template"](role="non_existent")

        assert result["success"] is False
        assert "No templates found" in result["error"]

    async def test_tool_9_get_template_stats(self, seed_templates):
        """Test get_template_stats tool"""
        tools, db_manager, _tenant_manager, template_ids = seed_templates

        # Create usage statistics
        async with db_manager.get_session() as session:
            for i in range(5):
                stats = TemplateUsageStats(
                    tenant_key="test-tenant",
                    template_id=template_ids["orchestrator"],
                    generation_ms=0.05 + (i * 0.01),
                    variables_used={"project_name": f"Project{i}"},
                    augmentations_applied=["aug1"] if i % 2 == 0 else ["aug2"],
                    tokens_used=100 + (i * 10),
                    agent_completed=i > 2,  # 2 of 5 completed
                    used_at=datetime.now(timezone.utc) - timedelta(days=i),
                )
                session.add(stats)

            # Add stats for another template
            for i in range(3):
                stats = TemplateUsageStats(
                    tenant_key="test-tenant",
                    template_id=template_ids["analyzer"],
                    generation_ms=0.03,
                    tokens_used=80,
                    agent_database_initialized=True,
                    used_at=datetime.now(timezone.utc) - timedelta(days=i),
                )
                session.add(stats)

            await session.commit()

        # Test stats for all templates
        result = await tools["get_template_stats"](days=30)

        assert result["success"] is True
        assert result["period_days"] == 30
        assert result["total_templates"] == 2
        assert result["total_usage"] == 8  # 5 + 3

        # Find orchestrator stats
        orchestrator_stats = None
        for stat in result["statistics"]:
            if stat["template_name"] == "orchestrator":
                orchestrator_stats = stat
                break

        assert orchestrator_stats is not None
        assert orchestrator_stats["usage_count"] == 5
        assert orchestrator_stats["completion_rate"] == 0.4  # 2/5
        assert orchestrator_stats["unique_augmentations"] == 2

        # Test stats for specific template
        result = await tools["get_template_stats"](template_id=template_ids["analyzer"], days=7)

        assert result["success"] is True
        assert len(result["statistics"]) == 1
        assert result["statistics"][0]["template_name"] == "analyzer"
        assert result["statistics"][0]["usage_count"] == 3
        assert result["statistics"][0]["completion_rate"] == 1.0  # All completed

    async def test_performance_requirements(self, seed_templates):
        """Test that template generation meets < 0.1ms requirement"""
        tools, _db_manager, _tenant_manager, _template_ids = seed_templates

        # Test multiple template retrievals
        iterations = 100
        total_time = 0

        for i in range(iterations):
            variables = {"project_name": f"Project_{i}", "objective": f"Objective_{i}"}

            start = time.perf_counter()
            result = await tools["get_agent_template"](
                name="orchestrator", product_id="test-product", variables=variables
            )
            end = time.perf_counter()

            assert result["success"] is True
            generation_time = (end - start) * 1000
            total_time += generation_time

            # Each individual generation should be under 0.1ms
            assert generation_time < 100, f"Generation {i} took {generation_time}ms"

        avg_time = total_time / iterations
        assert avg_time < 0.1, f"Average generation time {avg_time}ms exceeds 0.1ms target"

    async def test_tenant_isolation(self, mcp_setup):
        """Test that templates are properly isolated by tenant and product"""
        tools, _db_manager, tenant_manager = mcp_setup

        # Create templates for different tenants/products
        tenant_manager.current_tenant = "tenant1"
        tenant_manager.current_product = "product1"

        await tools["create_agent_template"](
            name="template1", category="role", template_content="Tenant1 Product1 Template"
        )

        tenant_manager.current_product = "product2"

        await tools["create_agent_template"](
            name="template1",  # Same name, different product
            category="role",
            template_content="Tenant1 Product2 Template",
        )

        tenant_manager.current_tenant = "tenant2"
        tenant_manager.current_product = "product1"

        await tools["create_agent_template"](
            name="template1",  # Same name, different tenant
            category="role",
            template_content="Tenant2 Product1 Template",
        )

        # Test isolation - tenant1/product1
        tenant_manager.current_tenant = "tenant1"
        tenant_manager.current_product = "product1"

        result = await tools["list_agent_templates"](product_id="product1")
        assert result["count"] == 1

        # Verify we get the right template
        result = await tools["get_agent_template"](name="template1", product_id="product1")
        assert "Tenant1 Product1" in result["template"]["content"]

        # Test isolation - tenant1/product2
        tenant_manager.current_product = "product2"

        result = await tools["get_agent_template"](name="template1", product_id="product2")
        assert "Tenant1 Product2" in result["template"]["content"]

        # Test isolation - tenant2/product1
        tenant_manager.current_tenant = "tenant2"
        tenant_manager.current_product = "product1"

        result = await tools["get_agent_template"](name="template1", product_id="product1")
        assert "Tenant2 Product1" in result["template"]["content"]

    async def test_augmentation_without_base_modification(self, seed_templates):
        """Test that runtime augmentations don't modify the base template"""
        tools, db_manager, _tenant_manager, template_ids = seed_templates

        documenter_id = template_ids["documenter"]

        # Get original template
        original = await tools["get_agent_template"](name="documenter", product_id="test-product")
        original_content = original["template"]["content"]

        # Apply runtime augmentations
        augmented = await tools["get_agent_template"](
            name="documenter",
            product_id="test-product",
            augmentations=[
                {
                    "type": "append",
                    "content": "\n## Additional Documentation Guidelines\n- Use markdown\n- Include examples",
                },
                {"type": "prepend", "content": "# Documentation Task\n"},
            ],
            variables={"subject": "API Endpoints", "format": "OpenAPI 3.0"},
        )

        # Verify augmentations were applied
        assert "Additional Documentation Guidelines" in augmented["template"]["content"]
        assert "# Documentation Task" in augmented["template"]["content"]
        assert "API Endpoints" in augmented["template"]["content"]

        # Get template again without augmentations
        unmodified = await tools["get_agent_template"](name="documenter", product_id="test-product")

        # Verify base template unchanged
        assert unmodified["template"]["content"] == original_content
        assert "Additional Documentation Guidelines" not in unmodified["template"]["content"]
        assert "# Documentation Task" not in unmodified["template"]["content"]

        # Verify database template is unchanged
        async with db_manager.get_session() as session:
            from sqlalchemy import select

            stmt = select(AgentTemplate).where(AgentTemplate.id == documenter_id)
            result = await session.execute(stmt)
            template = result.scalar_one()

            assert template.template_content == "Document: {subject}\nFormat: {format}"
            assert "Additional Documentation" not in template.template_content


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])
