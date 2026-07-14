# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""
Unit tests for TemplateService - Retrieval, Deletion, Cross-Tenant, and Tenant Isolation

Split from test_template_service.py. Tests template querying, filtering, deletion with
cascade behavior, cross-tenant existence checks, and tenant isolation guarantees.

Uses real PostgreSQL database for proper integration testing.
"""

from uuid import uuid4

import pytest

from giljo_mcp.models.templates import AgentTemplate, TemplateArchive


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
async def test_list_templates_with_filters_no_filters(
    db_session, template_service, test_tenant_key, test_product, sample_template
):
    """Test listing templates for a tenant without optional filters"""
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

    results = await template_service.get_default_templates_by_role(db_session, test_tenant_key, "orchestrator")

    assert len(results) >= 1
    assert all(t.is_default is True for t in results)
    assert all(t.role == "orchestrator" for t in results)


@pytest.mark.asyncio
async def test_get_active_user_managed_count(
    db_session, template_service, test_tenant_key, test_product, sample_template
):
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
#
# BE-8000j: the hard_delete_template service method was removed (never called in
# production — the live DELETE endpoint soft-deletes via delete_template, and the
# TSK-6132 reaper inlines the same cascade in purge_expired_deleted_templates,
# which is covered by tests/services/test_tsk6132_softdelete_reaper.py). Its unit
# tests were removed with it.


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
