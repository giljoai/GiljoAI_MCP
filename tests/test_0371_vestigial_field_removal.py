"""
Tests for Handover 0371 Phase 4.6: Vestigial template field removal.

Verifies that `project_type` and `preferred_tool` have been removed from
all Pydantic schemas and the CRUD response builder, and that `cli_tool`
(the real field) remains intact.
"""

from api.endpoints.templates.models import (
    TemplateCreate,
    TemplateResponse,
    TemplateUpdate,
)


class TestProjectTypeFieldRemoval:
    """Verify project_type is fully removed from Pydantic schemas."""

    def test_template_response_has_no_project_type_field(self):
        """TemplateResponse schema must not contain a project_type field."""
        field_names = set(TemplateResponse.model_fields.keys())
        assert "project_type" not in field_names, (
            "project_type should be removed from TemplateResponse"
        )

    def test_template_create_has_no_project_type_field(self):
        """TemplateCreate schema must not accept project_type."""
        field_names = set(TemplateCreate.model_fields.keys())
        assert "project_type" not in field_names, (
            "project_type should be removed from TemplateCreate"
        )

    def test_template_create_rejects_project_type_in_payload(self):
        """Sending project_type in a create payload must not populate the field."""
        data = {
            "role": "analyzer",
            "system_instructions": "Test instructions",
            "project_type": "web_app",
        }
        instance = TemplateCreate(**data)
        # After removal, the field should not be present on the instance
        assert not hasattr(instance, "project_type") or "project_type" not in instance.model_fields_set


class TestPreferredToolFieldRemoval:
    """Verify preferred_tool is fully removed from Pydantic schemas."""

    def test_template_response_has_no_preferred_tool_field(self):
        """TemplateResponse schema must not contain a preferred_tool field."""
        field_names = set(TemplateResponse.model_fields.keys())
        assert "preferred_tool" not in field_names, (
            "preferred_tool should be removed from TemplateResponse"
        )

    def test_template_create_has_no_preferred_tool_field(self):
        """TemplateCreate schema must not accept preferred_tool."""
        field_names = set(TemplateCreate.model_fields.keys())
        assert "preferred_tool" not in field_names, (
            "preferred_tool should be removed from TemplateCreate"
        )

    def test_template_update_has_no_preferred_tool_field(self):
        """TemplateUpdate schema must not accept preferred_tool."""
        field_names = set(TemplateUpdate.model_fields.keys())
        assert "preferred_tool" not in field_names, (
            "preferred_tool should be removed from TemplateUpdate"
        )

    def test_template_create_rejects_preferred_tool_in_payload(self):
        """Sending preferred_tool in a create payload must not populate the field."""
        data = {
            "role": "analyzer",
            "system_instructions": "Test instructions",
            "preferred_tool": "codex",
        }
        instance = TemplateCreate(**data)
        assert not hasattr(instance, "preferred_tool") or "preferred_tool" not in instance.model_fields_set


class TestCliToolFieldRetained:
    """Verify cli_tool (the real field) remains in all schemas."""

    def test_template_response_has_cli_tool(self):
        """TemplateResponse must still include cli_tool."""
        field_names = set(TemplateResponse.model_fields.keys())
        assert "cli_tool" in field_names, (
            "cli_tool must remain in TemplateResponse"
        )

    def test_template_create_has_cli_tool(self):
        """TemplateCreate must still include cli_tool."""
        field_names = set(TemplateCreate.model_fields.keys())
        assert "cli_tool" in field_names, (
            "cli_tool must remain in TemplateCreate"
        )

    def test_template_update_has_cli_tool(self):
        """TemplateUpdate must still include cli_tool."""
        field_names = set(TemplateUpdate.model_fields.keys())
        assert "cli_tool" in field_names, (
            "cli_tool must remain in TemplateUpdate"
        )

    def test_template_create_default_cli_tool_is_claude(self):
        """TemplateCreate cli_tool defaults to 'claude'."""
        instance = TemplateCreate(
            role="analyzer",
            system_instructions="Test instructions",
        )
        assert instance.cli_tool == "claude"


class TestCategoryFieldRetained:
    """Verify category field is NOT removed (it is still used)."""

    def test_template_response_has_category(self):
        """TemplateResponse must still include category."""
        field_names = set(TemplateResponse.model_fields.keys())
        assert "category" in field_names, (
            "category must remain in TemplateResponse"
        )

    def test_template_create_has_category(self):
        """TemplateCreate must still include category."""
        field_names = set(TemplateCreate.model_fields.keys())
        assert "category" in field_names, (
            "category must remain in TemplateCreate"
        )


class TestOrmModelProjectTypeRemoval:
    """Verify project_type is removed from the SQLAlchemy model."""

    def test_agent_template_has_no_project_type_column(self):
        """AgentTemplate ORM model must not have project_type column."""
        from src.giljo_mcp.models.templates import AgentTemplate

        column_names = {c.name for c in AgentTemplate.__table__.columns}
        assert "project_type" not in column_names, (
            "project_type column should be removed from AgentTemplate model"
        )


class TestTemplateManagerGetTemplateSignature:
    """Verify get_template no longer accepts project_type parameter."""

    def test_get_template_has_no_project_type_param(self):
        """UnifiedTemplateManager.get_template must not accept project_type."""
        import inspect

        from src.giljo_mcp.template_manager import UnifiedTemplateManager

        sig = inspect.signature(UnifiedTemplateManager.get_template)
        param_names = set(sig.parameters.keys())
        assert "project_type" not in param_names, (
            "project_type parameter should be removed from get_template"
        )
