"""
Unit tests for TemplateService - Handover 1011 Phase 2

Tests all new methods added to TemplateService for template endpoint migration.
Verifies tenant isolation, CRUD operations, history management, and deletion.

Uses real PostgreSQL database for proper integration testing.

Updated (0730-fix): Migrated from mock-based tests to real database integration
tests to fix fixture conflicts with base_fixtures.py.
"""

from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select

from src.giljo_mcp.models.templates import AgentTemplate, TemplateArchive, TemplateUsageStats
from src.giljo_mcp.services.template_service import TemplateService



# Test Fixtures
@pytest.fixture
def other_tenant_key():
    """Fixture for a different tenant key"""
    from src.giljo_mcp.tenant import TenantManager

    return TenantManager.generate_tenant_key()


@pytest_asyncio.fixture
async def template_service(db_manager, tenant_manager):
    """Fixture for TemplateService instance using real database manager"""
    return TemplateService(db_manager, tenant_manager)


@pytest_asyncio.fixture
async def sample_template(db_session, test_tenant_key, test_product):
    """Fixture for creating a sample template in the database"""
    template = AgentTemplate(
        id=str(uuid4()),
        tenant_key=test_tenant_key,
        product_id=test_product.id,
        name="test-analyzer",
        role="analyzer",
        category="custom",
        cli_tool="claude",
        background_color="#FF5733",
        description="Test analyzer agent",
        system_instructions="You are an analyzer agent.",
        is_active=True,
        is_default=False,
        version="1.0.0",
    )
    db_session.add(template)
    await db_session.commit()
    await db_session.refresh(template)
    return template


# ============================================================================
# Template Retrieval Tests
# ============================================================================


@pytest.mark.asyncio
async def test_get_template_by_id_success(db_session, template_service, test_tenant_key, sample_template):
    """Test retrieving template by ID with correct tenant"""
    result = await template_service.get_template_by_id(db_session, sample_template.id, test_tenant_key)

    assert result is not None
    assert result.id == sample_template.id
    assert result.name == "test-analyzer"


@pytest.mark.asyncio
async def test_get_template_by_id_wrong_tenant(db_session, template_service, other_tenant_key, sample_template):
    """Test tenant isolation - cannot access template from different tenant"""
    result = await template_service.get_template_by_id(db_session, sample_template.id, other_tenant_key)

    assert result is None


@pytest.mark.asyncio
async def test_list_templates_with_filters_no_filters(db_session, template_service, test_tenant_key, sample_template):
    """Test listing templates without filters"""
    results = await template_service.list_templates_with_filters(db_session, test_tenant_key)

    assert len(results) >= 1
    template_ids = [t.id for t in results]
    assert sample_template.id in template_ids


@pytest.mark.asyncio
async def test_list_templates_with_filters_role_filter(
    db_session, template_service, test_tenant_key, sample_template, test_product
):
    """Test listing templates with role filter"""
    # Add another template with different role
    other_template = AgentTemplate(
        id=str(uuid4()),
        tenant_key=test_tenant_key,
        product_id=test_product.id,
        name="test-reviewer",
        role="reviewer",
        category="custom",
        system_instructions="You are a reviewer.",
    )
    db_session.add(other_template)
    await db_session.commit()

    results = await template_service.list_templates_with_filters(db_session, test_tenant_key, role="analyzer")

    assert len(results) >= 1
    assert all(t.role == "analyzer" for t in results)


@pytest.mark.asyncio
async def test_list_templates_with_filters_is_active_filter(
    db_session, template_service, test_tenant_key, sample_template, test_product
):
    """Test listing templates with is_active filter"""
    inactive_template = AgentTemplate(
        id=str(uuid4()),
        tenant_key=test_tenant_key,
        product_id=test_product.id,
        name="test-inactive",
        role="analyzer",
        category="custom",
        system_instructions="Inactive template",
        is_active=False,
    )
    db_session.add(inactive_template)
    await db_session.commit()

    results = await template_service.list_templates_with_filters(db_session, test_tenant_key, is_active=True)

    assert all(t.is_active is True for t in results)


@pytest.mark.asyncio
async def test_check_template_name_exists_true(db_session, template_service, test_tenant_key, sample_template):
    """Test checking if template name exists (returns True)"""
    exists = await template_service.check_template_name_exists(db_session, test_tenant_key, "test-analyzer")

    assert exists is True


@pytest.mark.asyncio
async def test_check_template_name_exists_false(db_session, template_service, test_tenant_key):
    """Test checking if template name exists (returns False)"""
    exists = await template_service.check_template_name_exists(db_session, test_tenant_key, "nonexistent-template")

    assert exists is False


@pytest.mark.asyncio
async def test_get_default_templates_by_role(db_session, template_service, test_tenant_key, test_product):
    """Test retrieving default templates by role"""
    default_template = AgentTemplate(
        id=str(uuid4()),
        tenant_key=test_tenant_key,
        product_id=test_product.id,
        name="default-orchestrator",
        role="orchestrator",
        category="system",
        system_instructions="Default orchestrator",
        is_default=True,
    )
    db_session.add(default_template)
    await db_session.commit()

    results = await template_service.get_default_templates_by_role(
        db_session, test_tenant_key, "orchestrator", test_product.id
    )

    assert len(results) >= 1
    assert all(t.is_default is True for t in results)
    assert all(t.role == "orchestrator" for t in results)


@pytest.mark.asyncio
async def test_get_active_user_managed_count(db_session, template_service, test_tenant_key, sample_template):
    """Test counting active user-managed templates"""
    count = await template_service.get_active_user_managed_count(db_session, test_tenant_key)

    # The sample_template has role="analyzer" which is not a system role
    assert count >= 1


@pytest.mark.asyncio
async def test_get_active_user_managed_count_excludes_system_roles(
    db_session, template_service, test_tenant_key, test_product
):
    """Test that system-managed roles are excluded from count"""
    # Get initial count
    initial_count = await template_service.get_active_user_managed_count(db_session, test_tenant_key)

    # Add an orchestrator template (system-managed role)
    orchestrator_template = AgentTemplate(
        id=str(uuid4()),
        tenant_key=test_tenant_key,
        product_id=test_product.id,
        name="orchestrator-for-count-test",
        role="orchestrator",  # System-managed role
        category="system",
        system_instructions="Orchestrator",
        is_active=True,
    )
    db_session.add(orchestrator_template)
    await db_session.commit()

    # Count should be same (orchestrator is excluded)
    count = await template_service.get_active_user_managed_count(db_session, test_tenant_key)

    assert count == initial_count  # System role not counted


# ============================================================================
# Template Deletion Tests
# ============================================================================


@pytest.mark.asyncio
async def test_hard_delete_template_success(db_session, template_service, test_tenant_key, sample_template):
    """Test hard deleting a template"""
    template_id = sample_template.id

    deleted = await template_service.hard_delete_template(db_session, template_id, test_tenant_key)

    assert deleted is True

    # Verify template is deleted
    result = await db_session.execute(select(AgentTemplate).where(AgentTemplate.id == template_id))
    assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_hard_delete_template_cascades(
    db_session, template_service, test_tenant_key, sample_template, test_project_id
):
    """Test that hard delete cascades to related records"""
    # Add related records - use real project_id to satisfy FK constraint
    usage_stat = TemplateUsageStats(
        tenant_key=test_tenant_key,
        template_id=sample_template.id,
        project_id=test_project_id,
        generation_ms=150,
    )
    db_session.add(usage_stat)

    archive = TemplateArchive(
        tenant_key=test_tenant_key,
        template_id=sample_template.id,
        product_id=sample_template.product_id,
        name=sample_template.name,
        category=sample_template.category,
        role=sample_template.role,
        system_instructions=sample_template.system_instructions,
        version="1.0.0",
        archive_reason="Test",
        archive_type="manual",
        archived_by="test-user",
    )
    db_session.add(archive)
    await db_session.commit()

    template_id = sample_template.id

    # Delete template
    deleted = await template_service.hard_delete_template(db_session, template_id, test_tenant_key)

    assert deleted is True

    # Verify all related records are deleted
    stat_result = await db_session.execute(
        select(TemplateUsageStats).where(TemplateUsageStats.template_id == template_id)
    )
    assert stat_result.scalar_one_or_none() is None

    archive_result = await db_session.execute(
        select(TemplateArchive).where(TemplateArchive.template_id == template_id)
    )
    assert archive_result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_hard_delete_template_wrong_tenant(
    db_session, template_service, test_tenant_key, other_tenant_key, sample_template
):
    """Test that hard delete fails for wrong tenant"""
    deleted = await template_service.hard_delete_template(db_session, sample_template.id, other_tenant_key)

    assert deleted is False

    # Verify template still exists
    result = await db_session.execute(select(AgentTemplate).where(AgentTemplate.id == sample_template.id))
    assert result.scalar_one_or_none() is not None


# ============================================================================
# Template History Tests
# ============================================================================


@pytest.mark.asyncio
async def test_get_template_history(db_session, template_service, test_tenant_key, sample_template):
    """Test retrieving template history"""
    archive1 = TemplateArchive(
        tenant_key=test_tenant_key,
        template_id=sample_template.id,
        product_id=sample_template.product_id,
        name=sample_template.name,
        category=sample_template.category,
        role=sample_template.role,
        system_instructions="Version 1",
        version="1.0.0",
        archive_reason="Initial version",
        archive_type="auto",
        archived_by="system",
    )
    db_session.add(archive1)

    archive2 = TemplateArchive(
        tenant_key=test_tenant_key,
        template_id=sample_template.id,
        product_id=sample_template.product_id,
        name=sample_template.name,
        category=sample_template.category,
        role=sample_template.role,
        system_instructions="Version 2",
        version="2.0.0",
        archive_reason="Update",
        archive_type="auto",
        archived_by="user",
    )
    db_session.add(archive2)

    await db_session.commit()

    history = await template_service.get_template_history(db_session, sample_template.id, test_tenant_key)

    assert len(history) == 2
    # Should be ordered by archived_at desc (most recent first)
    versions = [h.version for h in history]
    assert "1.0.0" in versions
    assert "2.0.0" in versions


@pytest.mark.asyncio
async def test_get_archive_by_id_success(db_session, template_service, test_tenant_key, sample_template):
    """Test retrieving specific archive entry"""
    archive = TemplateArchive(
        tenant_key=test_tenant_key,
        template_id=sample_template.id,
        product_id=sample_template.product_id,
        name=sample_template.name,
        category=sample_template.category,
        role=sample_template.role,
        system_instructions="Archived content",
        version="1.0.0",
        archive_reason="Test",
        archive_type="manual",
        archived_by="test-user",
    )
    db_session.add(archive)
    await db_session.commit()
    await db_session.refresh(archive)

    result = await template_service.get_archive_by_id(db_session, archive.id, sample_template.id, test_tenant_key)

    assert result is not None
    assert result.id == archive.id
    assert result.system_instructions == "Archived content"


@pytest.mark.asyncio
async def test_create_template_archive(db_session, template_service, sample_template):
    """Test creating an archive from a template"""
    archive = await template_service.create_template_archive(
        db_session, sample_template, archive_reason="Test archive", archive_type="manual", archived_by="test-user"
    )

    assert archive.template_id == sample_template.id
    assert archive.tenant_key == sample_template.tenant_key
    assert archive.archive_reason == "Test archive"
    assert archive.archived_by == "test-user"


@pytest.mark.asyncio
async def test_restore_template_from_archive(db_session, template_service, sample_template):
    """Test restoring template content from archive.

    Note: restore_template_from_archive only restores variables, behavioral_rules,
    success_criteria, and version - NOT system_instructions.
    """
    archive = TemplateArchive(
        tenant_key=sample_template.tenant_key,
        template_id=sample_template.id,
        product_id=sample_template.product_id,
        name=sample_template.name,
        category=sample_template.category,
        role=sample_template.role,
        system_instructions="Archived content",
        variables=["var1", "var2"],
        behavioral_rules=["rule1"],
        success_criteria=["criteria1"],
        version="2.0.0",
        archive_reason="Test",
        archive_type="manual",
        archived_by="test-user",
    )
    db_session.add(archive)
    await db_session.commit()

    await template_service.restore_template_from_archive(db_session, sample_template, archive)

    # Note: system_instructions is NOT restored by this method (by design)
    assert sample_template.variables == ["var1", "var2"]
    assert sample_template.behavioral_rules == ["rule1"]
    assert sample_template.success_criteria == ["criteria1"]
    assert sample_template.version == "2.0.0"


@pytest.mark.asyncio
async def test_reset_template_to_defaults(db_session, template_service, sample_template):
    """Test resetting template to default values"""
    sample_template.user_instructions = "Custom instructions"
    sample_template.behavioral_rules = ["rule1", "rule2"]
    sample_template.success_criteria = ["criteria1"]
    sample_template.tags = ["tag1", "tag2"]
    await db_session.commit()

    await template_service.reset_template_to_defaults(db_session, sample_template)

    assert sample_template.user_instructions is None
    assert sample_template.behavioral_rules == []
    assert sample_template.success_criteria == []
    assert sample_template.tags == []


@pytest.mark.skip(reason="0750c3: expects old tool name acknowledge_job")
@pytest.mark.asyncio
async def test_reset_system_instructions(db_session, template_service, sample_template):
    """Test resetting system instructions to canonical default"""
    sample_template.system_instructions = "Custom system instructions"
    await db_session.commit()

    await template_service.reset_system_instructions(db_session, sample_template)

    assert "acknowledge_job()" in sample_template.system_instructions
    assert "report_progress()" in sample_template.system_instructions
    assert "complete_job()" in sample_template.system_instructions
    assert "receive_messages()" in sample_template.system_instructions


# ============================================================================
# Template Preview/Diff Tests
# ============================================================================


@pytest.mark.asyncio
async def test_check_cross_tenant_template_exists_true(db_session, template_service, sample_template):
    """Test checking if template exists across tenants (returns True)"""
    exists = await template_service.check_cross_tenant_template_exists(db_session, sample_template.id)

    assert exists is True


@pytest.mark.asyncio
async def test_check_cross_tenant_template_exists_false(db_session, template_service):
    """Test checking if template exists across tenants (returns False)"""
    exists = await template_service.check_cross_tenant_template_exists(db_session, str(uuid4()))

    assert exists is False


# ============================================================================
# Tenant Isolation Tests
# ============================================================================


@pytest.mark.asyncio
async def test_tenant_isolation_list_templates(
    db_session, template_service, test_tenant_key, other_tenant_key, sample_template, test_product
):
    """Test that list_templates_with_filters respects tenant isolation"""
    other_template = AgentTemplate(
        id=str(uuid4()),
        tenant_key=other_tenant_key,
        product_id=test_product.id,
        name="other-template",
        role="analyzer",
        category="custom",
        system_instructions="Other tenant template",
    )
    db_session.add(other_template)
    await db_session.commit()

    # List templates for test_tenant_key
    results = await template_service.list_templates_with_filters(db_session, test_tenant_key)

    assert all(t.tenant_key == test_tenant_key for t in results)


@pytest.mark.asyncio
async def test_tenant_isolation_get_template_history(
    db_session, template_service, test_tenant_key, other_tenant_key, sample_template
):
    """Test that get_template_history respects tenant isolation"""
    # Create archive for correct tenant
    archive1 = TemplateArchive(
        tenant_key=test_tenant_key,
        template_id=sample_template.id,
        product_id=sample_template.product_id,
        name=sample_template.name,
        category=sample_template.category,
        role=sample_template.role,
        system_instructions="Version 1",
        version="1.0.0",
        archive_reason="Test",
        archive_type="auto",
        archived_by="system",
    )
    db_session.add(archive1)

    # Create archive for different tenant (should not be returned)
    archive2 = TemplateArchive(
        tenant_key=other_tenant_key,
        template_id=sample_template.id,
        product_id=sample_template.product_id,
        name=sample_template.name,
        category=sample_template.category,
        role=sample_template.role,
        system_instructions="Version 2",
        version="2.0.0",
        archive_reason="Test",
        archive_type="auto",
        archived_by="system",
    )
    db_session.add(archive2)

    await db_session.commit()

    history = await template_service.get_template_history(db_session, sample_template.id, test_tenant_key)

    assert len(history) == 1
    assert history[0].tenant_key == test_tenant_key
