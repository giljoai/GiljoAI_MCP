# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""
Unit tests for AgentTemplate export tracking - Handover 0335 Task 3.

Tests the last_exported_at column and the real AgentTemplate.may_be_stale
property. Previously these tests re-implemented a simplified 3-term staleness
formula inline, which silently diverged from production: the real property has
four branches (is_active, user_managed_export, never-exported, created_at
fallback) and the inline copy ignored three of them — notably it asserted that
a never-exported template was NOT stale, the opposite of production. These now
drive the actual property so a regression in any branch fails the suite.
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from giljo_mcp.models import AgentTemplate


class TestAgentTemplateExportTracking:
    """Tests for last_exported_at column and timestamp tracking."""

    def test_agent_template_has_last_exported_at_column(self):
        """Test that AgentTemplate model has last_exported_at column."""
        template = AgentTemplate(
            id=str(uuid4()),
            tenant_key="test_tenant",
            name="test-agent",
            role="developer",
            system_instructions="Test instructions",
            is_active=True,
        )

        assert hasattr(template, "last_exported_at")
        # Should be nullable (None by default)
        assert template.last_exported_at is None

    def test_last_exported_at_accepts_datetime(self):
        """Test that last_exported_at accepts datetime values."""
        export_time = datetime.now(UTC)

        template = AgentTemplate(
            id=str(uuid4()),
            tenant_key="test_tenant",
            name="test-agent",
            role="developer",
            system_instructions="Test instructions",
            is_active=True,
            last_exported_at=export_time,
        )

        assert template.last_exported_at == export_time
        assert template.last_exported_at.tzinfo == UTC


class TestMayBeStaleComputation:
    """Tests for the real AgentTemplate.may_be_stale property (all four branches)."""

    def _template(self, **overrides):
        base = {
            "id": str(uuid4()),
            "tenant_key": "test_tenant",
            "name": "test-agent",
            "role": "developer",
            "system_instructions": "Test instructions",
            "is_active": True,
        }
        base.update(overrides)
        return AgentTemplate(**base)

    def test_stale_when_modified_after_export(self):
        """Active template changed after its last export is flagged stale."""
        now = datetime.now(UTC)
        template = self._template(
            last_exported_at=now - timedelta(hours=2),
            updated_at=now - timedelta(hours=1),
        )

        assert template.may_be_stale is True

    def test_not_stale_when_exported_after_modification(self):
        """Active template exported after its last change is up to date."""
        now = datetime.now(UTC)
        template = self._template(
            last_exported_at=now - timedelta(hours=1),
            updated_at=now - timedelta(hours=2),
        )

        assert template.may_be_stale is False

    def test_stale_when_never_exported(self):
        """A never-exported active template IS stale (last_exported_at is None).

        Regression guard: the prior inline test asserted False here, contradicting
        the production property which returns True. Driving the real property
        locks in the correct behavior.
        """
        template = self._template(last_exported_at=None, updated_at=datetime.now(UTC))

        assert template.may_be_stale is True

    def test_not_stale_when_inactive(self):
        """Disabled templates are never flagged stale, even if modified after export."""
        now = datetime.now(UTC)
        template = self._template(
            is_active=False,
            last_exported_at=now - timedelta(hours=2),
            updated_at=now - timedelta(hours=1),
        )

        assert template.may_be_stale is False

    def test_not_stale_when_user_managed_export(self):
        """user_managed_export dismisses staleness regardless of timestamps."""
        now = datetime.now(UTC)
        template = self._template(
            user_managed_export=True,
            last_exported_at=now - timedelta(hours=2),
            updated_at=now - timedelta(hours=1),
        )

        assert template.may_be_stale is False

    def test_stale_uses_created_at_when_updated_at_missing(self):
        """When updated_at is NULL (freshly seeded), created_at is the modified-at fallback."""
        now = datetime.now(UTC)
        template = self._template(
            last_exported_at=now - timedelta(hours=2),
            updated_at=None,
            created_at=now - timedelta(hours=1),
        )

        assert template.may_be_stale is True


class TestExportTimestampFlipsStaleness:
    """Setting last_exported_at flips may_be_stale — the actual effect of an export."""

    def test_export_timestamp_flips_may_be_stale_to_false(self):
        """A never-exported template is stale; recording an export clears it."""
        now = datetime.now(UTC)
        template = AgentTemplate(
            id=str(uuid4()),
            tenant_key="test_tenant",
            name="test-agent",
            role="developer",
            system_instructions="Test instructions",
            is_active=True,
            updated_at=now - timedelta(hours=1),
            last_exported_at=None,
        )

        assert template.may_be_stale is True  # never exported

        # Simulate an export completing after the last modification.
        template.last_exported_at = now

        assert template.may_be_stale is False
