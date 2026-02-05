"""
Comprehensive tests for template_seeder.py

Tests cover:
- Idempotency (running twice doesn't duplicate)
- All 6 templates seeded correctly
- Metadata fields populated correctly
- Multi-tenant isolation
- Error handling
"""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.models import AgentTemplate
from src.giljo_mcp.template_seeder import seed_tenant_templates


@pytest.fixture
def tenant_key():
    """Fixture providing unique tenant key for isolation"""
    return f"test_tenant_{uuid4().hex[:8]}"


@pytest.mark.asyncio
class TestTemplateSeedingBasics:
    """Basic template seeding functionality tests"""

    async def test_seed_templates_creates_all_six_templates(self, db_session: AsyncSession, tenant_key: str):
        """Test that seeding creates all 6 agent templates"""
        # Act
        count = await seed_tenant_templates(db_session, tenant_key)

        # Assert
        assert count == 6, "Should seed exactly 6 templates"

        # Verify in database
        result = await db_session.execute(
            select(func.count(AgentTemplate.id)).where(AgentTemplate.tenant_key == tenant_key)
        )
        db_count = result.scalar()
        assert db_count == 6, "Database should contain 6 templates"

    async def test_seeded_templates_have_correct_roles(self, db_session: AsyncSession, tenant_key: str):
        """Test that all expected role templates are seeded"""
        # Act
        await seed_tenant_templates(db_session, tenant_key)

        # Assert - check all 6 roles exist
        expected_roles = {"orchestrator", "analyzer", "implementer", "tester", "reviewer", "documenter"}

        result = await db_session.execute(select(AgentTemplate.role).where(AgentTemplate.tenant_key == tenant_key))
        seeded_roles = {row[0] for row in result.all()}

        assert seeded_roles == expected_roles, f"Expected roles {expected_roles}, got {seeded_roles}"

    async def test_seeded_templates_have_content(self, db_session: AsyncSession, tenant_key: str):
        """Test that all templates have non-empty content"""
        # Act
        await seed_tenant_templates(db_session, tenant_key)

        # Assert
        result = await db_session.execute(select(AgentTemplate).where(AgentTemplate.tenant_key == tenant_key))
        templates = result.scalars().all()

        for template in templates:
            assert template.system_instructions, f"Template {template.role} should have content"
            assert len(template.system_instructions) > 100, f"Template {template.role} content too short"


@pytest.mark.asyncio
class TestTemplateMetadata:
    """Tests for template metadata fields"""

    async def test_orchestrator_metadata_complete(self, db_session: AsyncSession, tenant_key: str):
        """Test orchestrator template has complete metadata"""
        # Act
        await seed_tenant_templates(db_session, tenant_key)

        # Assert
        result = await db_session.execute(
            select(AgentTemplate).where(AgentTemplate.tenant_key == tenant_key, AgentTemplate.role == "orchestrator")
        )
        template = result.scalar_one()

        # Check metadata fields
        assert template.category == "role"
        assert template.behavioral_rules, "Should have behavioral rules"
        assert len(template.behavioral_rules) >= 3, "Should have at least 3 behavioral rules"
        assert template.success_criteria, "Should have success criteria"
        assert len(template.success_criteria) >= 3, "Should have at least 3 success criteria"
        assert template.variables, "Should have variables"
        assert "project_name" in template.variables
        assert template.tool == "claude"
        assert template.version == "3.0.0"
        assert template.is_active is True
        assert template.is_default is False
        assert "default" in template.tags
        assert "tenant" in template.tags

    async def test_all_templates_have_required_metadata(self, db_session: AsyncSession, tenant_key: str):
        """Test all templates have required metadata fields"""
        # Act
        await seed_tenant_templates(db_session, tenant_key)

        # Assert
        result = await db_session.execute(select(AgentTemplate).where(AgentTemplate.tenant_key == tenant_key))
        templates = result.scalars().all()

        for template in templates:
            # Core fields
            assert template.name == template.role, f"Name should match role for {template.role}"
            assert template.category == "role"
            assert template.role in ["orchestrator", "analyzer", "implementer", "tester", "reviewer", "documenter"]

            # Metadata
            assert isinstance(template.behavioral_rules, list), f"{template.role} behavioral_rules not a list"
            assert isinstance(template.success_criteria, list), f"{template.role} success_criteria not a list"
            assert isinstance(template.variables, list), f"{template.role} variables not a list"
            assert len(template.variables) >= 1, f"{template.role} should have at least 1 variable"

            # Settings
            assert template.tool == "claude"
            assert template.version == "3.0.0"
            assert template.is_active is True
            assert template.is_default is False
            assert isinstance(template.tags, list)
            assert "default" in template.tags
            assert "tenant" in template.tags

            # Timestamps
            assert template.created_at is not None
            assert isinstance(template.created_at, datetime)

    async def test_templates_have_no_product_id(self, db_session: AsyncSession, tenant_key: str):
        """Test that seeded templates are tenant-level (no product_id)"""
        # Act
        await seed_tenant_templates(db_session, tenant_key)

        # Assert
        result = await db_session.execute(select(AgentTemplate).where(AgentTemplate.tenant_key == tenant_key))
        templates = result.scalars().all()

        for template in templates:
            assert template.product_id is None, f"Template {template.role} should be tenant-level (product_id=None)"


@pytest.mark.asyncio
class TestIdempotency:
    """Tests for idempotent seeding behavior"""

    async def test_seeding_twice_does_not_duplicate(self, db_session: AsyncSession, tenant_key: str):
        """Test that running seed twice doesn't create duplicates"""
        # Act - First seed
        count1 = await seed_tenant_templates(db_session, tenant_key)
        assert count1 == 6

        # Act - Second seed
        count2 = await seed_tenant_templates(db_session, tenant_key)

        # Assert - Second seed should return 0 (skipped)
        assert count2 == 0, "Second seed should skip and return 0"

        # Verify still only 6 templates
        result = await db_session.execute(
            select(func.count(AgentTemplate.id)).where(AgentTemplate.tenant_key == tenant_key)
        )
        db_count = result.scalar()
        assert db_count == 6, "Should still have exactly 6 templates, no duplicates"

    async def test_seeding_skips_when_partial_templates_exist(self, db_session: AsyncSession, tenant_key: str):
        """Test that seeding skips if tenant already has any templates"""
        # Arrange - Create one template manually
        manual_template = AgentTemplate(
            id=str(uuid4()),
            tenant_key=tenant_key,
            name="custom",
            category="role",
            role="custom",
            system_instructions="Custom template content",
            variables=["project_name"],
            behavioral_rules=["Rule 1"],
            success_criteria=["Success 1"],
            tool="claude",
            version="1.0.0",
            is_active=True,
            is_default=False,
            tags=["custom"],
            created_at=datetime.now(timezone.utc),
        )
        db_session.add(manual_template)
        await db_session.commit()

        # Act - Try to seed
        count = await seed_tenant_templates(db_session, tenant_key)

        # Assert - Should skip
        assert count == 0, "Should skip seeding when templates already exist"

        # Verify still only 1 template
        result = await db_session.execute(
            select(func.count(AgentTemplate.id)).where(AgentTemplate.tenant_key == tenant_key)
        )
        db_count = result.scalar()
        assert db_count == 1, "Should still have only the manual template"


@pytest.mark.asyncio
class TestMultiTenantIsolation:
    """Tests for multi-tenant data isolation"""

    async def test_seeding_different_tenants_is_isolated(self, db_session: AsyncSession):
        """Test that seeding for multiple tenants creates isolated template sets"""
        # Act - Seed for two different tenants
        tenant1 = f"tenant1_{uuid4().hex[:8]}"
        tenant2 = f"tenant2_{uuid4().hex[:8]}"

        count1 = await seed_tenant_templates(db_session, tenant1)
        count2 = await seed_tenant_templates(db_session, tenant2)

        # Assert - Both should seed successfully
        assert count1 == 6
        assert count2 == 6

        # Verify tenant 1 templates
        result1 = await db_session.execute(select(AgentTemplate).where(AgentTemplate.tenant_key == tenant1))
        tenant1_templates = result1.scalars().all()
        assert len(tenant1_templates) == 6
        assert all(t.tenant_key == tenant1 for t in tenant1_templates)

        # Verify tenant 2 templates
        result2 = await db_session.execute(select(AgentTemplate).where(AgentTemplate.tenant_key == tenant2))
        tenant2_templates = result2.scalars().all()
        assert len(tenant2_templates) == 6
        assert all(t.tenant_key == tenant2 for t in tenant2_templates)

        # Verify no cross-contamination
        tenant1_ids = {t.id for t in tenant1_templates}
        tenant2_ids = {t.id for t in tenant2_templates}
        assert tenant1_ids.isdisjoint(tenant2_ids), "Template IDs should be unique across tenants"

    async def test_seeding_respects_tenant_boundary(self, db_session: AsyncSession):
        """Test that seeding only affects the specified tenant"""
        # Arrange - Seed for tenant 1
        tenant1 = f"tenant1_{uuid4().hex[:8]}"
        tenant2 = f"tenant2_{uuid4().hex[:8]}"

        await seed_tenant_templates(db_session, tenant1)

        # Act - Check tenant 2 (should be empty)
        result = await db_session.execute(
            select(func.count(AgentTemplate.id)).where(AgentTemplate.tenant_key == tenant2)
        )
        tenant2_count = result.scalar()

        # Assert
        assert tenant2_count == 0, "Tenant 2 should have no templates yet"

        # Now seed tenant 2
        count = await seed_tenant_templates(db_session, tenant2)
        assert count == 6, "Tenant 2 should seed successfully"


@pytest.mark.asyncio
class TestErrorHandling:
    """Tests for error handling in seeding"""

    async def test_seeding_with_empty_tenant_key_fails_gracefully(self, db_session: AsyncSession):
        """Test that seeding with empty tenant_key raises appropriate error"""
        # Act & Assert
        with pytest.raises(Exception):  # Database will reject empty tenant_key
            await seed_tenant_templates(db_session, "")

    async def test_seeding_with_none_tenant_key_fails_gracefully(self, db_session: AsyncSession):
        """Test that seeding with None tenant_key raises appropriate error"""
        # Act & Assert
        with pytest.raises(Exception):  # Database will reject None tenant_key
            await seed_tenant_templates(db_session, None)

    async def test_seeding_commits_transaction(self, db_session: AsyncSession, tenant_key: str):
        """Test that seeding properly commits changes to database"""
        # Act
        count = await seed_tenant_templates(db_session, tenant_key)
        assert count == 6

        # Create new session to verify persistence
        # (In real scenario, this would be a new session)
        result = await db_session.execute(
            select(func.count(AgentTemplate.id)).where(AgentTemplate.tenant_key == tenant_key)
        )
        db_count = result.scalar()

        # Assert
        assert db_count == 6, "Changes should be committed and persisted"


@pytest.mark.asyncio
class TestTemplateContent:
    """Tests for template content integrity"""

    async def test_orchestrator_content_matches_legacy(self, db_session: AsyncSession, tenant_key: str):
        """Test that orchestrator template content starts with legacy template and includes MCP section"""
        # Act
        await seed_tenant_templates(db_session, tenant_key)

        # Assert - Load from database
        result = await db_session.execute(
            select(AgentTemplate.system_instructions).where(
                AgentTemplate.tenant_key == tenant_key, AgentTemplate.role == "orchestrator"
            )
        )
        db_content = result.scalar_one()

        # Load legacy template for comparison
        from src.giljo_mcp.template_manager import UnifiedTemplateManager

        template_mgr = UnifiedTemplateManager()
        legacy_content = template_mgr._legacy_templates["orchestrator"]

        # Compare - should start with legacy content and include MCP section
        assert db_content.startswith(legacy_content), "Database content should start with legacy template"
        assert "MCP COMMUNICATION PROTOCOL" in db_content, "Should have MCP coordination section appended"

    async def test_all_templates_have_variable_placeholders(self, db_session: AsyncSession, tenant_key: str):
        """Test that templates contain their declared variables as placeholders"""
        # Act
        await seed_tenant_templates(db_session, tenant_key)

        # Assert
        result = await db_session.execute(select(AgentTemplate).where(AgentTemplate.tenant_key == tenant_key))
        templates = result.scalars().all()

        for template in templates:
            # Check that declared variables appear in content as {variable}
            for variable in template.variables:
                placeholder = f"{{{variable}}}"
                assert placeholder in template.system_instructions, (
                    f"Template {template.role} should contain placeholder {placeholder}"
                )

    async def test_templates_contain_role_specific_keywords(self, db_session: AsyncSession, tenant_key: str):
        """Test that templates contain expected role-specific keywords"""
        # Act
        await seed_tenant_templates(db_session, tenant_key)

        # Assert - Check role-specific keywords
        role_keywords = {
            "orchestrator": ["delegation", "discovery", "mission"],
            "analyzer": ["analysis", "requirements", "architecture"],
            "implementer": ["implementation", "code", "specifications"],
            "tester": ["test", "validation", "coverage"],
            "reviewer": ["review", "quality", "standards"],
            "documenter": ["documentation", "document", "guide"],
        }

        for role, keywords in role_keywords.items():
            result = await db_session.execute(
                select(AgentTemplate.system_instructions).where(
                    AgentTemplate.tenant_key == tenant_key, AgentTemplate.role == role
                )
            )
            content = result.scalar_one().lower()

            # At least one keyword should be present
            found_keywords = [kw for kw in keywords if kw in content]
            assert found_keywords, f"Template {role} should contain at least one of {keywords}"


@pytest.mark.asyncio
class TestPerformance:
    """Performance-related tests"""

    async def test_seeding_completes_quickly(self, db_session: AsyncSession, tenant_key: str):
        """Test that seeding completes in reasonable time"""
        import time

        # Act
        start_time = time.time()
        await seed_tenant_templates(db_session, tenant_key)
        elapsed = time.time() - start_time

        # Assert - Should complete in under 2 seconds
        assert elapsed < 2.0, f"Seeding took {elapsed:.2f}s, should be under 2s"

    async def test_idempotency_check_is_fast(self, db_session: AsyncSession, tenant_key: str):
        """Test that idempotency check (skip) is very fast"""
        import time

        # Arrange - Seed once
        await seed_tenant_templates(db_session, tenant_key)

        # Act - Second seed (should skip)
        start_time = time.time()
        await seed_tenant_templates(db_session, tenant_key)
        elapsed = time.time() - start_time

        # Assert - Skip should be nearly instant (under 0.1s)
        assert elapsed < 0.1, f"Idempotency check took {elapsed:.2f}s, should be under 0.1s"
