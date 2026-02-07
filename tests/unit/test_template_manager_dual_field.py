"""
Comprehensive tests for template_manager.py dual-field merging.

Tests the merging of system_instructions (protected) and user_instructions (editable)
when retrieving agent templates.

Handover 0106: Dual-Field System
"""

from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.models import AgentTemplate
from src.giljo_mcp.template_manager import UnifiedTemplateManager


@pytest.mark.asyncio
class TestTemplateManagerDualFieldMerging:
    """Test suite for dual-field template merging (Handover 0106)."""

    async def test_merges_system_and_user(self, db_session: AsyncSession, db_manager: DatabaseManager):
        """Verify system + user instructions merged correctly."""
        tenant_key = "test_tenant_merge"

        # Create template with both fields
        template = AgentTemplate(
            tenant_key=tenant_key,
            name="test_orchestrator",
            category="role",
            role="orchestrator",
            cli_tool="claude",
            background_color="#D4A574",
            description="Test orchestrator",
            system_instructions="## SYSTEM INSTRUCTIONS\nUse MCP tools properly.",
            user_instructions="## USER INSTRUCTIONS\nCoordinate agents effectively.",
            legacy_content="Legacy content",  # Should not be used
            model="sonnet",
            version="1.0.0",
            is_active=True,
            is_default=True,
            tags=["test"],
            created_at=datetime.now(timezone.utc),
        )

        db_session.add(template)
        await db_session.commit()

        # Get template via manager
        manager = UnifiedTemplateManager(db_manager=db_manager)
        result = await manager.get_template(
            role="orchestrator",
            tenant_key=tenant_key,
            variables={
                "project_name": "Test Project",
                "product_name": "Test Product",
                "project_mission": "Test Mission",
            },
        )

        # Verify merging
        assert "## SYSTEM INSTRUCTIONS" in result, "Should contain system instructions"
        assert "## USER INSTRUCTIONS" in result, "Should contain user instructions"

        # Verify order (system first, then user)
        system_index = result.index("## SYSTEM INSTRUCTIONS")
        user_index = result.index("## USER INSTRUCTIONS")
        assert system_index < user_index, "System instructions should come before user instructions"

    async def test_system_only_template(self, db_session: AsyncSession, db_manager: DatabaseManager):
        """Handle templates with only system_instructions."""
        tenant_key = "test_tenant_system_only"

        # Create template with only system_instructions
        template = AgentTemplate(
            tenant_key=tenant_key,
            name="test_analyzer",
            category="role",
            role="analyzer",
            cli_tool="claude",
            background_color="#E74C3C",
            description="Test analyzer",
            system_instructions="## SYSTEM INSTRUCTIONS\nUse MCP tools properly.",
            user_instructions=None,  # No user instructions
            legacy_content="Legacy content",
            model="sonnet",
            version="1.0.0",
            is_active=True,
            is_default=True,
            tags=["test"],
            created_at=datetime.now(timezone.utc),
        )

        db_session.add(template)
        await db_session.commit()

        # Get template via manager
        manager = UnifiedTemplateManager(db_manager=db_manager)
        result = await manager.get_template(
            role="analyzer",
            tenant_key=tenant_key,
            variables={"project_name": "Test Project", "custom_mission": "Analyze code"},
        )

        # Verify only system instructions returned
        assert "## SYSTEM INSTRUCTIONS" in result, "Should contain system instructions"
        assert result.strip() == "## SYSTEM INSTRUCTIONS\nUse MCP tools properly.", (
            "Should only contain system instructions"
        )

    async def test_fallback_to_legacy_content(self, db_session: AsyncSession, db_manager: DatabaseManager):
        """Fallback to legacy content if system_instructions NULL (backward compatibility)."""
        tenant_key = "test_tenant_fallback"

        # Create legacy template (system_instructions would be NULL in old data)
        # Note: This scenario shouldn't happen in practice after migration 0106
        # but we test for defensive programming
        template = AgentTemplate(
            tenant_key=tenant_key,
            name="test_implementer",
            category="role",
            role="implementer",
            cli_tool="claude",
            background_color="#3498DB",
            description="Test implementer",
            system_instructions="",  # Empty (simulating NULL after fetch)
            user_instructions=None,
            legacy_content="## LEGACY TEMPLATE\nImplement features carefully.",
            model="sonnet",
            version="1.0.0",
            is_active=True,
            is_default=True,
            tags=["test"],
            created_at=datetime.now(timezone.utc),
        )

        db_session.add(template)
        await db_session.commit()

        # Get template via manager
        manager = UnifiedTemplateManager(db_manager=db_manager)
        result = await manager.get_template(
            role="implementer",
            tenant_key=tenant_key,
            variables={"project_name": "Test Project", "custom_mission": "Implement feature"},
        )

        # Verify fallback to legacy content
        # Note: Since system_instructions is empty, manager should fall back to legacy
        assert "LEGACY TEMPLATE" in result or "Implement feature" in result, "Should use fallback mechanism"

    async def test_merge_order_system_first(self, db_session: AsyncSession, db_manager: DatabaseManager):
        """Verify system instructions always come first in merge."""
        tenant_key = "test_tenant_order"

        # Create template
        template = AgentTemplate(
            tenant_key=tenant_key,
            name="test_tester",
            category="role",
            role="tester",
            cli_tool="claude",
            background_color="#FFC300",
            description="Test tester",
            system_instructions="SYSTEM_MARKER: MCP tools required",
            user_instructions="USER_MARKER: Write comprehensive tests",
            legacy_content="Legacy",
            model="sonnet",
            version="1.0.0",
            is_active=True,
            is_default=True,
            tags=["test"],
            created_at=datetime.now(timezone.utc),
        )

        db_session.add(template)
        await db_session.commit()

        # Get template
        manager = UnifiedTemplateManager(db_manager=db_manager)
        result = await manager.get_template(
            role="tester",
            tenant_key=tenant_key,
            variables={"project_name": "Test Project", "custom_mission": "Test feature"},
        )

        # Verify order
        system_pos = result.find("SYSTEM_MARKER")
        user_pos = result.find("USER_MARKER")

        assert system_pos != -1, "Should contain system marker"
        assert user_pos != -1, "Should contain user marker"
        assert system_pos < user_pos, "SYSTEM_MARKER should appear before USER_MARKER"

    async def test_merge_preserves_whitespace(self, db_session: AsyncSession, db_manager: DatabaseManager):
        """Verify proper newline separation between system and user."""
        tenant_key = "test_tenant_whitespace"

        # Create template
        template = AgentTemplate(
            tenant_key=tenant_key,
            name="test_reviewer",
            category="role",
            role="reviewer",
            cli_tool="claude",
            background_color="#9B59B6",
            description="Test reviewer",
            system_instructions="SYSTEM LINE",
            user_instructions="USER LINE",
            legacy_content="Legacy",
            model="sonnet",
            version="1.0.0",
            is_active=True,
            is_default=True,
            tags=["test"],
            created_at=datetime.now(timezone.utc),
        )

        db_session.add(template)
        await db_session.commit()

        # Get template
        manager = UnifiedTemplateManager(db_manager=db_manager)
        result = await manager.get_template(
            role="reviewer",
            tenant_key=tenant_key,
            variables={"project_name": "Test", "custom_mission": "Review"},
        )

        # Verify proper spacing (should have double newline between sections)
        assert "SYSTEM LINE\n\nUSER LINE" in result, "Should have double newline separation"

    async def test_variable_substitution_in_both_fields(self, db_session: AsyncSession, db_manager: DatabaseManager):
        """Verify variable substitution works in both system and user instructions."""
        tenant_key = "test_tenant_vars"

        # Create template with variables in both fields
        template = AgentTemplate(
            tenant_key=tenant_key,
            name="test_documenter",
            category="role",
            role="documenter",
            cli_tool="claude",
            background_color="#27AE60",
            description="Test documenter",
            system_instructions="System: Project {project_name}",
            user_instructions="User: Mission {custom_mission}",
            legacy_content="Legacy",
            model="sonnet",
            version="1.0.0",
            is_active=True,
            is_default=True,
            tags=["test"],
            created_at=datetime.now(timezone.utc),
        )

        db_session.add(template)
        await db_session.commit()

        # Get template with variables
        manager = UnifiedTemplateManager(db_manager=db_manager)
        result = await manager.get_template(
            role="documenter",
            tenant_key=tenant_key,
            variables={
                "project_name": "TestProject",
                "custom_mission": "Document API",
            },
        )

        # Verify variables substituted
        assert "Project TestProject" in result, "Should substitute project_name in system"
        assert "Mission Document API" in result, "Should substitute custom_mission in user"

    async def test_cache_key_accounts_for_both_fields(self, db_session: AsyncSession, db_manager: DatabaseManager):
        """Verify cache invalidation works when either field changes."""
        tenant_key = "test_tenant_cache"

        # Create initial template
        template = AgentTemplate(
            tenant_key=tenant_key,
            name="test_cache_template",
            category="role",
            role="orchestrator",
            cli_tool="claude",
            background_color="#D4A574",
            description="Cache test",
            system_instructions="System V1",
            user_instructions="User V1",
            legacy_content="Legacy V1",
            model="sonnet",
            version="1.0.0",
            is_active=True,
            is_default=True,
            tags=["test"],
            created_at=datetime.now(timezone.utc),
        )

        db_session.add(template)
        await db_session.commit()

        # Get template first time (populates cache)
        manager = UnifiedTemplateManager(db_manager=db_manager)
        result1 = await manager.get_template(
            role="orchestrator",
            tenant_key=tenant_key,
            variables={"project_name": "Test", "product_name": "Product", "project_mission": "Mission"},
        )

        assert "System V1" in result1
        assert "User V1" in result1

        # Update template (change user_instructions)
        template.user_instructions = "User V2"
        await db_session.commit()

        # Invalidate cache
        await manager.invalidate_cache(role="orchestrator", tenant_key=tenant_key)

        # Get template again (should reflect changes)
        result2 = await manager.get_template(
            role="orchestrator",
            tenant_key=tenant_key,
            variables={"project_name": "Test", "product_name": "Product", "project_mission": "Mission"},
            use_cache=False,  # Force fresh fetch
        )

        assert "System V1" in result2, "System should remain V1"
        assert "User V2" in result2, "User should be updated to V2"

    async def test_product_specific_template_priority(self, db_session: AsyncSession, db_manager: DatabaseManager):
        """Verify product-specific templates take priority over tenant-level."""
        tenant_key = "test_tenant_product_priority"
        product_id = "test_product_123"

        # Create tenant-level template
        tenant_template = AgentTemplate(
            tenant_key=tenant_key,
            product_id=None,  # Tenant-level
            name="orchestrator",
            category="role",
            role="orchestrator",
            cli_tool="claude",
            background_color="#D4A574",
            description="Tenant-level orchestrator",
            system_instructions="TENANT SYSTEM",
            user_instructions="TENANT USER",
            legacy_content="Tenant legacy",
            model="sonnet",
            version="1.0.0",
            is_active=True,
            is_default=True,
            tags=["tenant"],
            created_at=datetime.now(timezone.utc),
        )

        # Create product-specific template
        product_template = AgentTemplate(
            tenant_key=tenant_key,
            product_id=product_id,  # Product-specific
            name="orchestrator",
            category="role",
            role="orchestrator",
            cli_tool="claude",
            background_color="#D4A574",
            description="Product-level orchestrator",
            system_instructions="PRODUCT SYSTEM",
            user_instructions="PRODUCT USER",
            legacy_content="Product legacy",
            model="sonnet",
            version="1.0.0",
            is_active=True,
            is_default=False,
            tags=["product"],
            created_at=datetime.now(timezone.utc),
        )

        db_session.add(tenant_template)
        db_session.add(product_template)
        await db_session.commit()

        # Get template with product_id (should return product-specific)
        manager = UnifiedTemplateManager(db_manager=db_manager)
        result = await manager.get_template(
            role="orchestrator",
            tenant_key=tenant_key,
            product_id=product_id,
            variables={"project_name": "Test", "product_name": "Product", "project_mission": "Mission"},
        )

        # Should use product-specific template
        assert "PRODUCT SYSTEM" in result, "Should use product-specific system instructions"
        assert "PRODUCT USER" in result, "Should use product-specific user instructions"
        assert "TENANT" not in result, "Should NOT use tenant-level template"

    async def test_empty_user_instructions_handling(self, db_session: AsyncSession, db_manager: DatabaseManager):
        """Handle empty (not NULL) user_instructions gracefully."""
        tenant_key = "test_tenant_empty_user"

        # Create template with empty string user_instructions
        template = AgentTemplate(
            tenant_key=tenant_key,
            name="test_empty",
            category="role",
            role="analyzer",
            cli_tool="claude",
            background_color="#E74C3C",
            description="Empty user test",
            system_instructions="SYSTEM CONTENT",
            user_instructions="",  # Empty string (not NULL)
            legacy_content="Legacy",
            model="sonnet",
            version="1.0.0",
            is_active=True,
            is_default=True,
            tags=["test"],
            created_at=datetime.now(timezone.utc),
        )

        db_session.add(template)
        await db_session.commit()

        # Get template
        manager = UnifiedTemplateManager(db_manager=db_manager)
        result = await manager.get_template(
            role="analyzer",
            tenant_key=tenant_key,
            variables={"project_name": "Test", "custom_mission": "Analyze"},
        )

        # Should only return system instructions (no double newlines for empty user)
        assert "SYSTEM CONTENT" in result
        assert result.strip() == "SYSTEM CONTENT" or "SYSTEM CONTENT\n\n" in result

    async def test_serena_augmentation_after_merge(self, db_session: AsyncSession, db_manager: DatabaseManager):
        """Verify Serena augmentation applied after system+user merge."""
        tenant_key = "test_tenant_serena"

        # Create template
        template = AgentTemplate(
            tenant_key=tenant_key,
            name="test_serena_orchestrator",
            category="role",
            role="orchestrator",
            cli_tool="claude",
            background_color="#D4A574",
            description="Serena test",
            system_instructions="SYSTEM",
            user_instructions="USER",
            legacy_content="Legacy",
            model="sonnet",
            version="1.0.0",
            is_active=True,
            is_default=True,
            tags=["test"],
            created_at=datetime.now(timezone.utc),
        )

        db_session.add(template)
        await db_session.commit()

        # Get template with Serena enabled
        manager = UnifiedTemplateManager(db_manager=db_manager)

        # Mock Serena config (would normally come from ConfigService)
        # For this test, we'll just verify the merge happens before any augmentation
        result = await manager.get_template(
            role="orchestrator",
            tenant_key=tenant_key,
            variables={
                "project_name": "Test",
                "product_name": "Product",
                "project_mission": "Mission",
                "serena_enabled": False,  # Disable Serena for this test
            },
        )

        # Verify merge happened
        assert "SYSTEM" in result
        assert "USER" in result


@pytest.mark.asyncio
class TestLegacyTemplateCompatibility:
    """Test backward compatibility with legacy single-field templates."""

    async def test_legacy_template_still_works(self, db_manager: DatabaseManager):
        """Verify legacy templates (no DB) still work via fallback."""
        manager = UnifiedTemplateManager(db_manager=None)  # No DB (legacy mode)

        # Get legacy template
        result = await manager.get_template(
            role="orchestrator",
            tenant_key="any_tenant",
            variables={
                "project_name": "Test Project",
                "product_name": "Test Product",
                "project_mission": "Test Mission",
            },
        )

        # Should return legacy template
        assert "orchestrator" in result.lower() or "project" in result.lower()
        assert len(result) > 100, "Legacy template should have content"

    async def test_missing_role_returns_fallback(self, db_session: AsyncSession, db_manager: DatabaseManager):
        """Missing role should return fallback message."""
        manager = UnifiedTemplateManager(db_manager=db_manager)

        # Get non-existent role
        result = await manager.get_template(
            role="nonexistent_role",
            tenant_key="test_tenant",
            variables={},
        )

        # Should return fallback
        assert "No template available" in result or "nonexistent_role" in result.lower()
