"""Unit tests for database-dependent template validation functions (Handover 0103 Phase 8).

Tests validation functions that require database access:
- validate_agent_name()
- can_activate_role()

Split from test_template_validation_0103.py for maintainability.
Fixtures sync_db_manager, sync_db_session, and create_test_template are in conftest.py.
"""

import uuid

import pytest
from sqlalchemy.orm import Session

from src.giljo_mcp.template_validation import (
    can_activate_role,
    validate_agent_name,
)
from tests.unit.conftest import create_test_template


class TestValidateAgentName:
    """Test validate_agent_name function."""

    def test_valid_name(self, sync_db_session: Session):
        """Test valid agent name passes validation."""
        tenant_key = str(uuid.uuid4())
        is_valid, msg = validate_agent_name("orchestrator", tenant_key, sync_db_session)
        assert is_valid is True
        assert msg == ""

    def test_valid_with_hyphens(self, sync_db_session: Session):
        """Test valid name with hyphens passes validation."""
        tenant_key = str(uuid.uuid4())
        is_valid, msg = validate_agent_name("orchestrator-v2", tenant_key, sync_db_session)
        assert is_valid is True
        assert msg == ""

    def test_valid_with_numbers(self, sync_db_session: Session):
        """Test valid name with numbers passes validation."""
        tenant_key = str(uuid.uuid4())
        is_valid, msg = validate_agent_name("tester-123", tenant_key, sync_db_session)
        assert is_valid is True
        assert msg == ""

    def test_invalid_uppercase(self, sync_db_session: Session):
        """Test uppercase letters rejected."""
        tenant_key = str(uuid.uuid4())
        is_valid, msg = validate_agent_name("Orchestrator", tenant_key, sync_db_session)
        assert is_valid is False
        assert "lowercase" in msg

    def test_invalid_spaces(self, sync_db_session: Session):
        """Test spaces rejected."""
        tenant_key = str(uuid.uuid4())
        is_valid, msg = validate_agent_name("my agent", tenant_key, sync_db_session)
        assert is_valid is False
        assert "lowercase" in msg

    def test_invalid_underscores(self, sync_db_session: Session):
        """Test underscores rejected."""
        tenant_key = str(uuid.uuid4())
        is_valid, msg = validate_agent_name("my_agent", tenant_key, sync_db_session)
        assert is_valid is False
        assert "lowercase" in msg

    def test_invalid_special_chars(self, sync_db_session: Session):
        """Test special characters rejected."""
        tenant_key = str(uuid.uuid4())
        is_valid, msg = validate_agent_name("agent@test", tenant_key, sync_db_session)
        assert is_valid is False
        assert "lowercase" in msg

    def test_too_long(self, sync_db_session: Session):
        """Test name over 100 characters rejected."""
        tenant_key = str(uuid.uuid4())
        long_name = "a" * 101
        is_valid, msg = validate_agent_name(long_name, tenant_key, sync_db_session)
        assert is_valid is False
        assert "100 characters" in msg

    def test_exactly_100_chars(self, sync_db_session: Session):
        """Test name exactly 100 characters accepted."""
        tenant_key = str(uuid.uuid4())
        exact_name = "a" * 100
        is_valid, msg = validate_agent_name(exact_name, tenant_key, sync_db_session)
        assert is_valid is True
        assert msg == ""

    def test_duplicate_name_same_tenant(self, sync_db_session: Session):
        """Test duplicate name in same tenant rejected."""
        tenant_key = str(uuid.uuid4())

        # Create existing template
        create_test_template(sync_db_session, tenant_key, name="existing-agent")

        # Try to validate same name
        is_valid, msg = validate_agent_name("existing-agent", tenant_key, sync_db_session)
        assert is_valid is False
        assert "already exists" in msg

    def test_duplicate_name_different_tenant(self, sync_db_session: Session):
        """Test duplicate name in different tenant allowed (tenant isolation)."""
        tenant_key_1 = str(uuid.uuid4())
        tenant_key_2 = str(uuid.uuid4())

        # Create template in tenant 1
        create_test_template(sync_db_session, tenant_key_1, name="shared-name")

        # Same name should be valid in tenant 2
        is_valid, msg = validate_agent_name("shared-name", tenant_key_2, sync_db_session)
        assert is_valid is True
        assert msg == ""

    def test_exclude_id_allows_same_name(self, sync_db_session: Session):
        """Test excluding ID allows updating template with same name."""
        tenant_key = str(uuid.uuid4())

        # Create existing template
        template = create_test_template(sync_db_session, tenant_key, name="update-me")

        # Should be valid when excluding the template's own ID
        is_valid, msg = validate_agent_name("update-me", tenant_key, sync_db_session, exclude_id=template.id)
        assert is_valid is True
        assert msg == ""

    def test_exclude_id_still_catches_other_duplicates(self, sync_db_session: Session):
        """Test excluding ID still catches duplicates from other templates."""
        tenant_key = str(uuid.uuid4())

        # Create two templates
        template_1 = create_test_template(sync_db_session, tenant_key, name="agent-1")
        create_test_template(sync_db_session, tenant_key, name="agent-2")

        # Try to rename template-1 to agent-2 (should fail)
        is_valid, msg = validate_agent_name("agent-2", tenant_key, sync_db_session, exclude_id=template_1.id)
        assert is_valid is False
        assert "already exists" in msg

    def test_empty_name(self, sync_db_session: Session):
        """Test empty name rejected."""
        tenant_key = str(uuid.uuid4())
        is_valid, msg = validate_agent_name("", tenant_key, sync_db_session)
        assert is_valid is False
        assert "lowercase" in msg


class TestCanActivateRole:
    """Test can_activate_role function."""

    def test_first_activation(self, sync_db_session: Session):
        """Test first role activation allowed."""
        tenant_key = str(uuid.uuid4())
        can_activate, msg = can_activate_role("orchestrator", tenant_key, sync_db_session)
        assert can_activate is True
        assert msg == ""

    def test_seventh_role_activation(self, sync_db_session: Session):
        """Test 7th distinct role activation allowed."""
        tenant_key = str(uuid.uuid4())

        # Create 6 active roles
        roles = ["orchestrator", "analyzer", "implementer", "tester", "reviewer", "documenter"]
        for role in roles:
            create_test_template(sync_db_session, tenant_key, name=f"{role}-1", role=role, is_active=True)

        # 7th role should be allowed
        can_activate, msg = can_activate_role("designer", tenant_key, sync_db_session)
        assert can_activate is True
        assert msg == ""

    def test_eighth_role_activation(self, sync_db_session: Session):
        """Test 8th distinct role activation allowed."""
        tenant_key = str(uuid.uuid4())

        # Create 7 active roles
        roles = ["orchestrator", "analyzer", "implementer", "tester", "reviewer", "documenter", "designer"]
        for role in roles:
            create_test_template(sync_db_session, tenant_key, name=f"{role}-1", role=role, is_active=True)

        # 8th role should be allowed
        can_activate, msg = can_activate_role("frontend", tenant_key, sync_db_session)
        assert can_activate is True
        assert msg == ""

    def test_ninth_role_activation_blocked(self, sync_db_session: Session):
        """Test 9th distinct role activation blocked."""
        tenant_key = str(uuid.uuid4())

        # Create 8 active roles
        roles = ["orchestrator", "analyzer", "implementer", "tester", "reviewer", "documenter", "designer", "frontend"]
        for role in roles:
            create_test_template(sync_db_session, tenant_key, name=f"{role}-1", role=role, is_active=True)

        # 9th role should be blocked
        can_activate, msg = can_activate_role("backend", tenant_key, sync_db_session)
        assert can_activate is False
        assert "Maximum 8" in msg
        assert "currently 8" in msg

    def test_toggle_existing_role_allowed(self, sync_db_session: Session):
        """Test toggling existing active role allowed (no new role added)."""
        tenant_key = str(uuid.uuid4())

        # Create 8 active roles
        roles = ["orchestrator", "analyzer", "implementer", "tester", "reviewer", "documenter", "designer", "frontend"]
        for role in roles:
            create_test_template(sync_db_session, tenant_key, name=f"{role}-1", role=role, is_active=True)

        # Activating a second orchestrator should be allowed (role already active)
        can_activate, msg = can_activate_role("orchestrator", tenant_key, sync_db_session)
        assert can_activate is True
        assert msg == ""

    def test_multiple_templates_same_role(self, sync_db_session: Session):
        """Test multiple templates with same role counted as one role."""
        tenant_key = str(uuid.uuid4())

        # Create 8 roles, with orchestrator having 3 templates
        create_test_template(sync_db_session, tenant_key, name="orchestrator-1", role="orchestrator", is_active=True)
        create_test_template(sync_db_session, tenant_key, name="orchestrator-2", role="orchestrator", is_active=True)
        create_test_template(sync_db_session, tenant_key, name="orchestrator-3", role="orchestrator", is_active=True)

        roles = ["analyzer", "implementer", "tester", "reviewer", "documenter", "designer", "frontend"]
        for role in roles:
            create_test_template(sync_db_session, tenant_key, name=f"{role}-1", role=role, is_active=True)

        # Should have 8 distinct roles, activating a 4th orchestrator should be allowed
        can_activate, msg = can_activate_role("orchestrator", tenant_key, sync_db_session)
        assert can_activate is True
        assert msg == ""

    def test_exclude_id_works(self, sync_db_session: Session):
        """Test exclude_id allows updating template without counting it."""
        tenant_key = str(uuid.uuid4())

        # Create 8 active roles
        roles = ["orchestrator", "analyzer", "implementer", "tester", "reviewer", "documenter", "designer", "frontend"]
        templates = []
        for role in roles:
            template = create_test_template(sync_db_session, tenant_key, name=f"{role}-1", role=role, is_active=True)
            templates.append(template)

        # Updating orchestrator (excluding its ID) should be allowed
        can_activate, msg = can_activate_role("orchestrator", tenant_key, sync_db_session, exclude_id=templates[0].id)
        assert can_activate is True
        assert msg == ""

    def test_multi_tenant_isolation(self, sync_db_session: Session):
        """Test tenant isolation - 8 roles in tenant A doesn't block tenant B."""
        tenant_key_a = str(uuid.uuid4())
        tenant_key_b = str(uuid.uuid4())

        # Create 8 active roles in tenant A
        roles = ["orchestrator", "analyzer", "implementer", "tester", "reviewer", "documenter", "designer", "frontend"]
        for role in roles:
            create_test_template(sync_db_session, tenant_key_a, name=f"{role}-1", role=role, is_active=True)

        # Tenant B should be able to activate any role
        can_activate, msg = can_activate_role("orchestrator", tenant_key_b, sync_db_session)
        assert can_activate is True
        assert msg == ""

    def test_inactive_templates_not_counted(self, sync_db_session: Session):
        """Test inactive templates not counted toward limit."""
        tenant_key = str(uuid.uuid4())

        # Create 8 active roles
        active_roles = [
            "orchestrator",
            "analyzer",
            "implementer",
            "tester",
            "reviewer",
            "documenter",
            "designer",
            "frontend",
        ]
        for role in active_roles:
            create_test_template(sync_db_session, tenant_key, name=f"{role}-1", role=role, is_active=True)

        # Create 5 inactive templates with different roles
        inactive_roles = ["backend", "devops", "security", "qa", "architect"]
        for role in inactive_roles:
            create_test_template(sync_db_session, tenant_key, name=f"{role}-1", role=role, is_active=False)

        # Should still have only 8 active roles, so backend can't be activated
        can_activate, msg = can_activate_role("backend", tenant_key, sync_db_session)
        assert can_activate is False
        assert "Maximum 8" in msg

    def test_activating_deactivated_role_allowed(self, sync_db_session: Session):
        """Test re-activating a previously deactivated role counts as new role."""
        tenant_key = str(uuid.uuid4())

        # Create 8 active roles
        active_roles = [
            "orchestrator",
            "analyzer",
            "implementer",
            "tester",
            "reviewer",
            "documenter",
            "designer",
            "frontend",
        ]
        for role in active_roles:
            create_test_template(sync_db_session, tenant_key, name=f"{role}-1", role=role, is_active=True)

        # Create inactive backend template
        create_test_template(sync_db_session, tenant_key, name="backend-1", role="backend", is_active=False)

        # Trying to activate backend should be blocked (9th role)
        can_activate, msg = can_activate_role("backend", tenant_key, sync_db_session)
        assert can_activate is False
        assert "Maximum 8" in msg
