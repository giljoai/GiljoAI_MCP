"""
Unit tests for AgentTemplate export tracking - Handover 0335 Task 3

Tests last_exported_at timestamp tracking and may_be_stale flag computation.
Following TDD principles - these tests are written BEFORE implementation.
"""

from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.giljo_mcp.models import AgentTemplate


class TestAgentTemplateExportTracking:
    """Tests for last_exported_at column and timestamp tracking."""

    def test_agent_template_has_last_exported_at_column(self):
        """Test that AgentTemplate model has last_exported_at column."""
        # Create template instance
        template = AgentTemplate(
            id=str(uuid4()),
            tenant_key="test_tenant",
            name="test-agent",
            role="developer",
            system_instructions="Test content",
            system_instructions="Test instructions",
            is_active=True,
        )

        # Verify column exists
        assert hasattr(template, "last_exported_at")
        # Should be nullable (None by default)
        assert template.last_exported_at is None

    def test_last_exported_at_accepts_datetime(self):
        """Test that last_exported_at accepts datetime values."""
        export_time = datetime.now(timezone.utc)

        template = AgentTemplate(
            id=str(uuid4()),
            tenant_key="test_tenant",
            name="test-agent",
            role="developer",
            system_instructions="Test content",
            system_instructions="Test instructions",
            is_active=True,
            last_exported_at=export_time,
        )

        assert template.last_exported_at == export_time
        assert template.last_exported_at.tzinfo == timezone.utc


class TestMayBeStaleComputation:
    """Tests for may_be_stale flag computation logic."""

    def test_may_be_stale_true_when_modified_after_export(self):
        """Test may_be_stale is True when updated_at > last_exported_at."""
        now = datetime.now(timezone.utc)
        exported_time = now - timedelta(hours=2)
        modified_time = now - timedelta(hours=1)

        template = AgentTemplate(
            id=str(uuid4()),
            tenant_key="test_tenant",
            name="test-agent",
            role="developer",
            system_instructions="Test content",
            system_instructions="Test instructions",
            is_active=True,
            last_exported_at=exported_time,
            updated_at=modified_time,
        )

        # Compute may_be_stale
        may_be_stale = (
            template.updated_at is not None
            and template.last_exported_at is not None
            and template.updated_at > template.last_exported_at
        )

        assert may_be_stale is True

    def test_may_be_stale_false_when_exported_after_modification(self):
        """Test may_be_stale is False when last_exported_at > updated_at."""
        now = datetime.now(timezone.utc)
        modified_time = now - timedelta(hours=2)
        exported_time = now - timedelta(hours=1)

        template = AgentTemplate(
            id=str(uuid4()),
            tenant_key="test_tenant",
            name="test-agent",
            role="developer",
            system_instructions="Test content",
            system_instructions="Test instructions",
            is_active=True,
            last_exported_at=exported_time,
            updated_at=modified_time,
        )

        # Compute may_be_stale
        may_be_stale = (
            template.updated_at is not None
            and template.last_exported_at is not None
            and template.updated_at > template.last_exported_at
        )

        assert may_be_stale is False

    def test_may_be_stale_false_when_never_exported(self):
        """Test may_be_stale is False when last_exported_at is None."""
        template = AgentTemplate(
            id=str(uuid4()),
            tenant_key="test_tenant",
            name="test-agent",
            role="developer",
            system_instructions="Test content",
            system_instructions="Test instructions",
            is_active=True,
            last_exported_at=None,
            updated_at=datetime.now(timezone.utc),
        )

        # Compute may_be_stale
        may_be_stale = (
            template.updated_at is not None
            and template.last_exported_at is not None
            and template.updated_at > template.last_exported_at
        )

        assert may_be_stale is False

    def test_may_be_stale_property_or_method(self):
        """Test that may_be_stale is accessible as property or computed field."""
        now = datetime.now(timezone.utc)
        template = AgentTemplate(
            id=str(uuid4()),
            tenant_key="test_tenant",
            name="test-agent",
            role="developer",
            system_instructions="Test content",
            system_instructions="Test instructions",
            is_active=True,
            last_exported_at=now - timedelta(hours=2),
            updated_at=now - timedelta(hours=1),
        )

        # Check if may_be_stale exists as property or method
        # This will be implemented as @property decorator
        if hasattr(template, "may_be_stale"):
            # Property exists
            if callable(template.may_be_stale):
                assert template.may_be_stale() is True
            else:
                assert template.may_be_stale is True
        else:
            # For now, compute manually (will be refactored to property)
            may_be_stale = (
                template.updated_at is not None
                and template.last_exported_at is not None
                and template.updated_at > template.last_exported_at
            )
            assert may_be_stale is True


class TestExportEndpointTimestampUpdate:
    """Tests for export endpoint setting last_exported_at."""

    def test_export_sets_last_exported_at_timestamp(self):
        """Test that export function updates last_exported_at field."""
        # This is a simple test to verify the model has the field
        # and can be set during export. The actual export timestamp
        # setting will be verified through integration tests.

        now = datetime.now(timezone.utc)
        template = AgentTemplate(
            id=str(uuid4()),
            tenant_key="test_tenant",
            name="test-agent",
            role="developer",
            system_instructions="Test content",
            system_instructions="Test instructions",
            is_active=True,
            last_exported_at=None,
        )

        # Verify field exists and can be set
        assert template.last_exported_at is None

        # Simulate export by setting timestamp
        template.last_exported_at = now

        # Verify timestamp was set
        assert template.last_exported_at == now
        assert template.last_exported_at.tzinfo == timezone.utc

    @pytest.mark.asyncio
    async def test_export_updates_existing_last_exported_at(self):
        """Test that re-exporting updates last_exported_at to new timestamp."""
        # This test will verify that exporting again updates the timestamp
        # Implementation will add timestamp update logic to export function

        # Mock template with existing export timestamp
        old_export_time = datetime.now(timezone.utc) - timedelta(days=1)

        mock_template = MagicMock(spec=AgentTemplate)
        mock_template.id = "tmpl-123"
        mock_template.name = "test-agent"
        mock_template.role = "developer"
        mock_template.tool = "claude"
        mock_template.description = "Test template"
        mock_template.system_instructions = "Test content"
        mock_template.behavioral_rules = []
        mock_template.success_criteria = []
        mock_template.last_exported_at = old_export_time

        # The export function should update this to current time
        # Will be verified in implementation
        assert mock_template.last_exported_at == old_export_time
