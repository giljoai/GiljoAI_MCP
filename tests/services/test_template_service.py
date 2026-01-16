"""
Unit tests for TemplateService - Handover 1011 Phase 2

Tests all new methods added to TemplateService for template endpoint migration.
Verifies tenant isolation, CRUD operations, history management, and deletion.

Uses mocked database for isolation from PostgreSQL dependency.
"""

import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

from src.giljo_mcp.models.agent_identity import AgentJob
from src.giljo_mcp.models.templates import AgentTemplate, TemplateArchive, TemplateAugmentation, TemplateUsageStats
from src.giljo_mcp.services.template_service import TemplateService
from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.tenant import TenantManager


# Test Fixtures
@pytest.fixture
def tenant_key():
    """Fixture for test tenant key"""
    return "test-tenant-001"


@pytest.fixture
def other_tenant_key():
    """Fixture for a different tenant key"""
    return "test-tenant-002"


@pytest.fixture
def product_id():
    """Fixture for test product ID"""
    return str(uuid4())


@pytest.fixture
def mock_session():
    """Mock database session"""
    session = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()
    session.delete = AsyncMock()
    return session


@pytest.fixture
def db_manager(mock_session):
    """Fixture for database manager with mocked session"""
    db_manager = MagicMock()
    db_manager.get_session_async = MagicMock(return_value=mock_session)
    return db_manager


@pytest.fixture
def tenant_manager(tenant_key):
    """Fixture for tenant manager with mocked current tenant"""
    manager = MagicMock()
    manager.get_current_tenant = MagicMock(return_value=tenant_key)
    return manager


@pytest.fixture
def template_service(db_manager, tenant_manager):
    """Fixture for TemplateService instance"""
    return TemplateService(db_manager, tenant_manager)


@pytest.fixture
async def sample_template(tenant_key, product_id):
    """Fixture for creating a sample template"""
    return AgentTemplate(
        id=str(uuid4()),
        tenant_key=tenant_key,
        product_id=product_id,
        name="test-analyzer",
        role="analyzer",
        category="custom",
        cli_tool="claude",
        background_color="#FF5733",
        description="Test analyzer agent",
        template_content="You are an analyzer agent.",
        system_instructions="You are an analyzer agent.",
        is_active=True,
        is_default=False,
        version="1.0.0",
    )


# ============================================================================
# Template Retrieval Tests
# ============================================================================


@pytest.mark.asyncio
async def test_get_template_by_id_success(template_service, tenant_key, sample_template):
    """Test retrieving template by ID with correct tenant"""
    async with template_service.db_manager.get_session_async() as session:
        session.add(sample_template)
        await session.commit()

        result = await template_service.get_template_by_id(
            session, sample_template.id, tenant_key
        )

        assert result is not None
        assert result.id == sample_template.id
        assert result.name == "test-analyzer"


@pytest.mark.asyncio
async def test_get_template_by_id_wrong_tenant(template_service, tenant_key, other_tenant_key, sample_template):
    """Test tenant isolation - cannot access template from different tenant"""
    async with template_service.db_manager.get_session_async() as session:
        session.add(sample_template)
        await session.commit()

        result = await template_service.get_template_by_id(
            session, sample_template.id, other_tenant_key
        )

        assert result is None


@pytest.mark.asyncio
async def test_list_templates_with_filters_no_filters(template_service, tenant_key, sample_template):
    """Test listing templates without filters"""
    async with template_service.db_manager.get_session_async() as session:
        session.add(sample_template)
        await session.commit()

        results = await template_service.list_templates_with_filters(
            session, tenant_key
        )

        assert len(results) == 1
        assert results[0].id == sample_template.id


@pytest.mark.asyncio
async def test_list_templates_with_filters_role_filter(template_service, tenant_key, sample_template):
    """Test listing templates with role filter"""
    async with template_service.db_manager.get_session_async() as session:
        session.add(sample_template)

        # Add another template with different role
        other_template = AgentTemplate(
            id=str(uuid4()),
            tenant_key=tenant_key,
            product_id=sample_template.product_id,
            name="test-reviewer",
            role="reviewer",
            category="custom",
            template_content="You are a reviewer.",
        )
        session.add(other_template)
        await session.commit()

        results = await template_service.list_templates_with_filters(
            session, tenant_key, role="analyzer"
        )

        assert len(results) == 1
        assert results[0].role == "analyzer"


@pytest.mark.asyncio
async def test_list_templates_with_filters_is_active_filter(template_service, tenant_key, sample_template):
    """Test listing templates with is_active filter"""
    async with template_service.db_manager.get_session_async() as session:
        sample_template.is_active = True
        session.add(sample_template)

        inactive_template = AgentTemplate(
            id=str(uuid4()),
            tenant_key=tenant_key,
            product_id=sample_template.product_id,
            name="test-inactive",
            role="analyzer",
            category="custom",
            template_content="Inactive template",
            is_active=False,
        )
        session.add(inactive_template)
        await session.commit()

        results = await template_service.list_templates_with_filters(
            session, tenant_key, is_active=True
        )

        assert len(results) == 1
        assert results[0].is_active is True


@pytest.mark.asyncio
async def test_check_template_name_exists_true(template_service, tenant_key, sample_template):
    """Test checking if template name exists (returns True)"""
    async with template_service.db_manager.get_session_async() as session:
        session.add(sample_template)
        await session.commit()

        exists = await template_service.check_template_name_exists(
            session, tenant_key, "test-analyzer"
        )

        assert exists is True


@pytest.mark.asyncio
async def test_check_template_name_exists_false(template_service, tenant_key):
    """Test checking if template name exists (returns False)"""
    async with template_service.db_manager.get_session_async() as session:
        exists = await template_service.check_template_name_exists(
            session, tenant_key, "nonexistent-template"
        )

        assert exists is False


@pytest.mark.asyncio
async def test_get_default_templates_by_role(template_service, tenant_key, product_id):
    """Test retrieving default templates by role"""
    async with template_service.db_manager.get_session_async() as session:
        default_template = AgentTemplate(
            id=str(uuid4()),
            tenant_key=tenant_key,
            product_id=product_id,
            name="default-orchestrator",
            role="orchestrator",
            category="system",
            template_content="Default orchestrator",
            is_default=True,
        )
        session.add(default_template)
        await session.commit()

        results = await template_service.get_default_templates_by_role(
            session, tenant_key, "orchestrator", product_id
        )

        assert len(results) == 1
        assert results[0].is_default is True
        assert results[0].role == "orchestrator"


@pytest.mark.asyncio
async def test_get_active_user_managed_count(template_service, tenant_key, sample_template):
    """Test counting active user-managed templates"""
    async with template_service.db_manager.get_session_async() as session:
        sample_template.is_active = True
        session.add(sample_template)
        await session.commit()

        count = await template_service.get_active_user_managed_count(
            session, tenant_key
        )

        assert count == 1


@pytest.mark.asyncio
async def test_get_active_user_managed_count_excludes_system_roles(template_service, tenant_key, product_id):
    """Test that system-managed roles are excluded from count"""
    async with template_service.db_manager.get_session_async() as session:
        orchestrator_template = AgentTemplate(
            id=str(uuid4()),
            tenant_key=tenant_key,
            product_id=product_id,
            name="orchestrator",
            role="orchestrator",  # System-managed role
            category="system",
            template_content="Orchestrator",
            is_active=True,
        )
        session.add(orchestrator_template)
        await session.commit()

        count = await template_service.get_active_user_managed_count(
            session, tenant_key
        )

        assert count == 0  # System role not counted


# ============================================================================
# Template Deletion Tests
# ============================================================================


@pytest.mark.asyncio
async def test_hard_delete_template_success(template_service, tenant_key, sample_template):
    """Test hard deleting a template"""
    async with template_service.db_manager.get_session_async() as session:
        session.add(sample_template)
        await session.commit()

        deleted = await template_service.hard_delete_template(
            session, sample_template.id, tenant_key
        )

        assert deleted is True

        # Verify template is deleted
        result = await session.execute(
            select(AgentTemplate).where(AgentTemplate.id == sample_template.id)
        )
        assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_hard_delete_template_cascades(template_service, tenant_key, sample_template):
    """Test that hard delete cascades to related records"""
    async with template_service.db_manager.get_session_async() as session:
        session.add(sample_template)

        # Add related records
        augmentation = TemplateAugmentation(
            tenant_key=tenant_key,
            template_id=sample_template.id,
            name="Test Augmentation",
            augmentation_type="prepend",
            content="Additional instructions",
        )
        session.add(augmentation)

        usage_stat = TemplateUsageStats(
            tenant_key=tenant_key,
            template_id=sample_template.id,
            project_id=str(uuid4()),
            generation_ms=150,
        )
        session.add(usage_stat)

        archive = TemplateArchive(
            tenant_key=tenant_key,
            template_id=sample_template.id,
            product_id=sample_template.product_id,
            name=sample_template.name,
            category=sample_template.category,
            role=sample_template.role,
            template_content=sample_template.template_content,
            version="1.0.0",
            archive_reason="Test",
            archive_type="manual",
            archived_by="test-user",
        )
        session.add(archive)

        await session.commit()

        # Delete template
        deleted = await template_service.hard_delete_template(
            session, sample_template.id, tenant_key
        )

        assert deleted is True

        # Verify all related records are deleted
        aug_result = await session.execute(
            select(TemplateAugmentation).where(TemplateAugmentation.template_id == sample_template.id)
        )
        assert aug_result.scalar_one_or_none() is None

        stat_result = await session.execute(
            select(TemplateUsageStats).where(TemplateUsageStats.template_id == sample_template.id)
        )
        assert stat_result.scalar_one_or_none() is None

        archive_result = await session.execute(
            select(TemplateArchive).where(TemplateArchive.template_id == sample_template.id)
        )
        assert archive_result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_hard_delete_template_wrong_tenant(template_service, tenant_key, other_tenant_key, sample_template):
    """Test that hard delete fails for wrong tenant"""
    async with template_service.db_manager.get_session_async() as session:
        session.add(sample_template)
        await session.commit()

        deleted = await template_service.hard_delete_template(
            session, sample_template.id, other_tenant_key
        )

        assert deleted is False

        # Verify template still exists
        result = await session.execute(
            select(AgentTemplate).where(AgentTemplate.id == sample_template.id)
        )
        assert result.scalar_one_or_none() is not None


# ============================================================================
# Template History Tests
# ============================================================================


@pytest.mark.asyncio
async def test_get_template_history(template_service, tenant_key, sample_template):
    """Test retrieving template history"""
    async with template_service.db_manager.get_session_async() as session:
        session.add(sample_template)

        archive1 = TemplateArchive(
            tenant_key=tenant_key,
            template_id=sample_template.id,
            product_id=sample_template.product_id,
            name=sample_template.name,
            category=sample_template.category,
            role=sample_template.role,
            template_content="Version 1",
            version="1.0.0",
            archive_reason="Initial version",
            archive_type="auto",
            archived_by="system",
        )
        session.add(archive1)

        archive2 = TemplateArchive(
            tenant_key=tenant_key,
            template_id=sample_template.id,
            product_id=sample_template.product_id,
            name=sample_template.name,
            category=sample_template.category,
            role=sample_template.role,
            template_content="Version 2",
            version="2.0.0",
            archive_reason="Update",
            archive_type="auto",
            archived_by="user",
        )
        session.add(archive2)

        await session.commit()

        history = await template_service.get_template_history(
            session, sample_template.id, tenant_key
        )

        assert len(history) == 2
        # Should be ordered by archived_at desc (most recent first)
        assert history[0].version == "2.0.0"
        assert history[1].version == "1.0.0"


@pytest.mark.asyncio
async def test_get_archive_by_id_success(template_service, tenant_key, sample_template):
    """Test retrieving specific archive entry"""
    async with template_service.db_manager.get_session_async() as session:
        session.add(sample_template)

        archive = TemplateArchive(
            tenant_key=tenant_key,
            template_id=sample_template.id,
            product_id=sample_template.product_id,
            name=sample_template.name,
            category=sample_template.category,
            role=sample_template.role,
            template_content="Archived content",
            version="1.0.0",
            archive_reason="Test",
            archive_type="manual",
            archived_by="test-user",
        )
        session.add(archive)
        await session.commit()

        result = await template_service.get_archive_by_id(
            session, archive.id, sample_template.id, tenant_key
        )

        assert result is not None
        assert result.id == archive.id
        assert result.template_content == "Archived content"


@pytest.mark.asyncio
async def test_create_template_archive(template_service, sample_template):
    """Test creating an archive from a template"""
    async with template_service.db_manager.get_session_async() as session:
        session.add(sample_template)
        await session.commit()

        archive = await template_service.create_template_archive(
            session,
            sample_template,
            archive_reason="Test archive",
            archive_type="manual",
            archived_by="test-user"
        )

        assert archive.template_id == sample_template.id
        assert archive.tenant_key == sample_template.tenant_key
        assert archive.archive_reason == "Test archive"
        assert archive.archived_by == "test-user"


@pytest.mark.asyncio
async def test_restore_template_from_archive(template_service, sample_template):
    """Test restoring template content from archive"""
    async with template_service.db_manager.get_session_async() as session:
        session.add(sample_template)

        archive = TemplateArchive(
            tenant_key=sample_template.tenant_key,
            template_id=sample_template.id,
            product_id=sample_template.product_id,
            name=sample_template.name,
            category=sample_template.category,
            role=sample_template.role,
            template_content="Archived content",
            variables=["var1", "var2"],
            behavioral_rules=["rule1"],
            success_criteria=["criteria1"],
            version="2.0.0",
            archive_reason="Test",
            archive_type="manual",
            archived_by="test-user",
        )
        session.add(archive)
        await session.commit()

        await template_service.restore_template_from_archive(
            session, sample_template, archive
        )

        assert sample_template.template_content == "Archived content"
        assert sample_template.variables == ["var1", "var2"]
        assert sample_template.behavioral_rules == ["rule1"]
        assert sample_template.success_criteria == ["criteria1"]
        assert sample_template.version == "2.0.0"


@pytest.mark.asyncio
async def test_reset_template_to_defaults(template_service, sample_template):
    """Test resetting template to default values"""
    async with template_service.db_manager.get_session_async() as session:
        sample_template.user_instructions = "Custom instructions"
        sample_template.behavioral_rules = ["rule1", "rule2"]
        sample_template.success_criteria = ["criteria1"]
        sample_template.tags = ["tag1", "tag2"]

        session.add(sample_template)
        await session.commit()

        await template_service.reset_template_to_defaults(session, sample_template)

        assert sample_template.user_instructions is None
        assert sample_template.behavioral_rules == []
        assert sample_template.success_criteria == []
        assert sample_template.tags == []


@pytest.mark.asyncio
async def test_reset_system_instructions(template_service, sample_template):
    """Test resetting system instructions to canonical default"""
    async with template_service.db_manager.get_session_async() as session:
        sample_template.system_instructions = "Custom system instructions"
        session.add(sample_template)
        await session.commit()

        await template_service.reset_system_instructions(session, sample_template)

        assert "acknowledge_job()" in sample_template.system_instructions
        assert "report_progress()" in sample_template.system_instructions
        assert "complete_job()" in sample_template.system_instructions
        assert "get_next_instruction()" in sample_template.system_instructions


# ============================================================================
# Template Preview/Diff Tests
# ============================================================================


@pytest.mark.asyncio
async def test_check_cross_tenant_template_exists_true(template_service, tenant_key, sample_template):
    """Test checking if template exists across tenants (returns True)"""
    async with template_service.db_manager.get_session_async() as session:
        session.add(sample_template)
        await session.commit()

        exists = await template_service.check_cross_tenant_template_exists(
            session, sample_template.id
        )

        assert exists is True


@pytest.mark.asyncio
async def test_check_cross_tenant_template_exists_false(template_service):
    """Test checking if template exists across tenants (returns False)"""
    async with template_service.db_manager.get_session_async() as session:
        exists = await template_service.check_cross_tenant_template_exists(
            session, str(uuid4())
        )

        assert exists is False


# ============================================================================
# Tenant Isolation Tests
# ============================================================================


@pytest.mark.asyncio
async def test_tenant_isolation_list_templates(template_service, tenant_key, other_tenant_key, sample_template):
    """Test that list_templates_with_filters respects tenant isolation"""
    async with template_service.db_manager.get_session_async() as session:
        session.add(sample_template)

        other_template = AgentTemplate(
            id=str(uuid4()),
            tenant_key=other_tenant_key,
            product_id=sample_template.product_id,
            name="other-template",
            role="analyzer",
            category="custom",
            template_content="Other tenant template",
        )
        session.add(other_template)
        await session.commit()

        # List templates for tenant_key
        results = await template_service.list_templates_with_filters(
            session, tenant_key
        )

        assert len(results) == 1
        assert results[0].tenant_key == tenant_key


@pytest.mark.asyncio
async def test_tenant_isolation_get_template_history(template_service, tenant_key, other_tenant_key, sample_template):
    """Test that get_template_history respects tenant isolation"""
    async with template_service.db_manager.get_session_async() as session:
        session.add(sample_template)

        # Create archive for correct tenant
        archive1 = TemplateArchive(
            tenant_key=tenant_key,
            template_id=sample_template.id,
            product_id=sample_template.product_id,
            name=sample_template.name,
            category=sample_template.category,
            role=sample_template.role,
            template_content="Version 1",
            version="1.0.0",
            archive_reason="Test",
            archive_type="auto",
            archived_by="system",
        )
        session.add(archive1)

        # Create archive for different tenant (should not be returned)
        archive2 = TemplateArchive(
            tenant_key=other_tenant_key,
            template_id=sample_template.id,
            product_id=sample_template.product_id,
            name=sample_template.name,
            category=sample_template.category,
            role=sample_template.role,
            template_content="Version 2",
            version="2.0.0",
            archive_reason="Test",
            archive_type="auto",
            archived_by="system",
        )
        session.add(archive2)

        await session.commit()

        history = await template_service.get_template_history(
            session, sample_template.id, tenant_key
        )

        assert len(history) == 1
        assert history[0].tenant_key == tenant_key
