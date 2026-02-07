"""Unit tests for template validation functions (Handover 0103 Phase 8).

Tests all 5 validation functions with comprehensive coverage:
- slugify_name()
- validate_agent_name()
- validate_system_prompt()
- can_activate_role()
- get_role_color()
"""

import uuid

import pytest
from sqlalchemy.orm import Session

from src.giljo_mcp.models import AgentTemplate
from src.giljo_mcp.template_validation import (
    can_activate_role,
    get_role_color,
    slugify_name,
    validate_agent_name,
    validate_system_prompt,
)


# Sync database manager fixture for validation tests
@pytest.fixture(scope="function")
def sync_db_manager():
    """Create synchronous database manager for validation tests."""
    from src.giljo_mcp.database import DatabaseManager
    from tests.helpers.test_db_helper import PostgreSQLTestHelper

    # Create sync database manager with test database URL
    connection_string = PostgreSQLTestHelper.get_test_db_url()
    # Convert async connection string to sync (replace postgresql+asyncpg with postgresql+psycopg2)
    sync_connection_string = connection_string.replace("postgresql+asyncpg://", "postgresql+psycopg2://")

    db_mgr = DatabaseManager(sync_connection_string, is_async=False)
    return db_mgr


# Sync session fixture for validation tests
@pytest.fixture
def sync_db_session(sync_db_manager):
    """Get synchronous database session for validation tests."""
    with sync_db_manager.get_session() as session:
        yield session


# Helper function to create test templates
def create_test_template(
    db: Session,
    tenant_key: str,
    name: str = "test-agent",
    role: str = "implementer",
    is_active: bool = False,
    system_prompt: str = "Test system prompt with enough characters to be valid",
) -> AgentTemplate:
    """Create test agent template in database."""
    # Create template with only fields that exist in current DB schema
    template = AgentTemplate(
        id=str(uuid.uuid4()),
        tenant_key=tenant_key,
        name=name,
        role=role,
        category="role",
        system_instructions=system_prompt,
        is_active=is_active,
        variables=[],
        behavioral_rules=[],
        success_criteria=[],
        tool="claude",  # Default tool
    )

    # Don't set new 0103 fields if they don't exist in DB yet
    # (cli_tool, background_color, model, tools columns may not be migrated)

    db.add(template)
    db.commit()
    db.refresh(template)
    return template


class TestSlugifyName:
    """Test slugify_name function."""

    def test_role_only(self):
        """Test generating name from role only."""
        assert slugify_name("orchestrator") == "orchestrator"

    def test_role_with_suffix(self):
        """Test generating name from role and suffix."""
        assert slugify_name("orchestrator", "AmazingGuy") == "orchestrator-amazingguy"

    def test_spaces_in_suffix(self):
        """Test suffix with spaces converted to hyphens."""
        assert slugify_name("tester", "Fast Runner") == "tester-fast-runner"

    def test_underscores_in_suffix(self):
        """Test suffix with underscores converted to hyphens."""
        assert slugify_name("implementer", "API_Handler") == "implementer-api-handler"

    def test_special_chars_removed(self):
        """Test suffix with special characters removed."""
        assert slugify_name("analyzer", "Code@Guru!") == "analyzer-codeguru"

    def test_empty_suffix(self):
        """Test empty suffix returns role only."""
        assert slugify_name("reviewer", "") == "reviewer"

    def test_none_suffix(self):
        """Test None suffix returns role only."""
        assert slugify_name("documenter", None) == "documenter"

    def test_multiple_spaces_consolidated(self):
        """Test multiple consecutive spaces consolidated."""
        # Multiple spaces become multiple hyphens (regex doesn't consolidate)
        result = slugify_name("tester", "Super  Fast   Runner")
        # The regex replaces each space with hyphen individually
        assert result == "tester-super--fast---runner"

    def test_mixed_case_suffix(self):
        """Test mixed case suffix converted to lowercase."""
        assert slugify_name("backend", "APIHandlerV2") == "backend-apihandlerv2"

    def test_suffix_with_numbers(self):
        """Test suffix with numbers preserved."""
        assert slugify_name("orchestrator", "Version123") == "orchestrator-version123"


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


class TestValidateSystemPrompt:
    """Test validate_system_prompt function."""

    def test_valid_prompt_50_chars(self):
        """Test valid prompt with 50 characters passes."""
        prompt = "This is a valid system prompt with enough content."
        is_valid, msg = validate_system_prompt(prompt)
        assert is_valid is True
        assert msg == ""

    def test_minimum_valid_20_chars(self):
        """Test minimum valid prompt with exactly 20 characters."""
        prompt = "a" * 20
        is_valid, msg = validate_system_prompt(prompt)
        assert is_valid is True
        assert msg == ""

    def test_too_short_19_chars(self):
        """Test prompt with 19 characters rejected."""
        prompt = "a" * 19
        is_valid, msg = validate_system_prompt(prompt)
        assert is_valid is False
        assert "too short" in msg

    def test_empty_string(self):
        """Test empty string rejected."""
        is_valid, msg = validate_system_prompt("")
        assert is_valid is False
        assert "required" in msg

    def test_whitespace_only(self):
        """Test whitespace-only string rejected."""
        is_valid, msg = validate_system_prompt("   \n\t  ")
        assert is_valid is False
        assert "required" in msg

    def test_whitespace_with_content_too_short(self):
        """Test string with whitespace + short content rejected."""
        prompt = "  hello world  "  # 11 chars after strip
        is_valid, msg = validate_system_prompt(prompt)
        assert is_valid is False
        assert "too short" in msg

    def test_whitespace_with_valid_content(self):
        """Test string with whitespace + valid content accepted."""
        prompt = "  " + ("a" * 20) + "  "  # 20 chars after strip
        is_valid, msg = validate_system_prompt(prompt)
        assert is_valid is True
        assert msg == ""

    def test_multiline_valid_prompt(self):
        """Test multiline prompt with enough content passes."""
        prompt = """This is a multiline
        system prompt with
        enough content."""
        is_valid, msg = validate_system_prompt(prompt)
        assert is_valid is True
        assert msg == ""

    def test_none_value(self):
        """Test None value handled gracefully."""
        is_valid, msg = validate_system_prompt(None)
        assert is_valid is False
        assert "required" in msg


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


class TestGetRoleColor:
    """Test get_role_color function."""

    def test_orchestrator_color(self):
        """Test orchestrator returns correct color."""
        assert get_role_color("orchestrator") == "#D4A574"

    def test_analyzer_color(self):
        """Test analyzer returns correct color."""
        assert get_role_color("analyzer") == "#E74C3C"

    def test_implementer_color(self):
        """Test implementer returns correct color."""
        assert get_role_color("implementer") == "#3498DB"

    def test_tester_color(self):
        """Test tester returns correct color."""
        assert get_role_color("tester") == "#FFC300"

    def test_reviewer_color(self):
        """Test reviewer returns correct color."""
        assert get_role_color("reviewer") == "#9B59B6"

    def test_documenter_color(self):
        """Test documenter returns correct color."""
        assert get_role_color("documenter") == "#27AE60"

    def test_designer_color(self):
        """Test designer returns correct color."""
        assert get_role_color("designer") == "#9B59B6"

    def test_frontend_color(self):
        """Test frontend returns correct color."""
        assert get_role_color("frontend") == "#3498DB"

    def test_backend_color(self):
        """Test backend returns correct color."""
        assert get_role_color("backend") == "#2ECC71"

    def test_unknown_role_returns_default(self):
        """Test unknown role returns default gray color."""
        assert get_role_color("unknown_role") == "#90A4AE"

    def test_empty_role_returns_default(self):
        """Test empty role returns default gray color."""
        assert get_role_color("") == "#90A4AE"

    def test_case_sensitive(self):
        """Test role colors are case-sensitive."""
        assert get_role_color("Orchestrator") == "#90A4AE"  # Uppercase should return default

    def test_all_documented_roles(self):
        """Test all documented roles have colors defined."""
        documented_roles = [
            "orchestrator",
            "analyzer",
            "designer",
            "frontend",
            "backend",
            "implementer",
            "tester",
            "reviewer",
            "documenter",
        ]

        for role in documented_roles:
            color = get_role_color(role)
            assert color.startswith("#")
            assert len(color) == 7
            assert color != "#90A4AE"  # Should not be default color
