# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Tests for EventFactory.agent_status_changed() field naming fix.

The fix renamed the Pydantic field from 'new_status' to 'status' to match
all other broadcast paths. This removes the need for a frontend translator
workaround and ensures agent:status_changed events are handled uniformly.

These tests are pure unit tests with no I/O or database access.
"""

import sys
import types
import uuid

import pytest


# Stub the api package before importing its submodules so that api/__init__.py
# (which triggers create_app and requires the 'mcp' package) is never executed.
if "api" not in sys.modules:
    _api_stub = types.ModuleType("api")
    _api_stub.__path__ = ["api"]
    _api_stub.__package__ = "api"
    sys.modules["api"] = _api_stub

from api.events.schemas import EventFactory


class TestEventFactoryStatusField:
    """Verify EventFactory.agent_status_changed emits 'status', not 'new_status'."""

    def test_agent_status_changed_uses_status_field_not_new_status(self):
        """Output data contains 'status' and does not contain 'new_status'."""
        event = EventFactory.agent_status_changed(
            job_id="test-job",
            tenant_key="test-tenant",
            old_status="silent",
            new_status="working",
            agent_display_name="orchestrator",
            project_id="test-project",
        )

        assert "status" in event["data"]
        assert "new_status" not in event["data"]

    def test_agent_status_changed_status_value_matches_new_status_argument(self):
        """The 'status' field value equals what was passed as new_status."""
        event = EventFactory.agent_status_changed(
            job_id="test-job",
            tenant_key="test-tenant",
            old_status="silent",
            new_status="working",
            agent_display_name="orchestrator",
            project_id="test-project",
        )

        assert event["data"]["status"] == "working"

    def test_agent_status_changed_old_status_is_present(self):
        """The 'old_status' field is present and matches what was passed."""
        event = EventFactory.agent_status_changed(
            job_id="test-job",
            tenant_key="test-tenant",
            old_status="silent",
            new_status="working",
            agent_display_name="orchestrator",
            project_id="test-project",
        )

        assert event["data"]["old_status"] == "silent"

    def test_agent_status_changed_event_type_is_correct(self):
        """Top-level 'type' is 'agent:status_changed'."""
        event = EventFactory.agent_status_changed(
            job_id="test-job",
            tenant_key="test-tenant",
            old_status="blocked",
            new_status="working",
            agent_display_name="implementer",
            project_id="proj-123",
        )

        assert event["type"] == "agent:status_changed"

    def test_agent_status_changed_includes_project_id(self):
        """project_id is present in event data when provided."""
        project_id = str(uuid.uuid4())
        event = EventFactory.agent_status_changed(
            job_id="test-job",
            tenant_key="test-tenant",
            old_status="idle",
            new_status="working",
            agent_display_name="analyzer",
            project_id=project_id,
        )

        assert event["data"]["project_id"] == project_id

    def test_agent_status_changed_project_id_none_when_omitted(self):
        """project_id is None in event data when not provided."""
        event = EventFactory.agent_status_changed(
            job_id="test-job",
            tenant_key="test-tenant",
            old_status="sleeping",
            new_status="working",
            agent_display_name="tester",
        )

        assert event["data"]["project_id"] is None

    def test_agent_status_changed_has_schema_version(self):
        """Event includes schema_version field."""
        event = EventFactory.agent_status_changed(
            job_id="test-job",
            tenant_key="test-tenant",
            old_status="blocked",
            new_status="working",
            agent_display_name="reviewer",
        )

        assert event["schema_version"] == "1.0"

    def test_agent_status_changed_has_timestamp(self):
        """Event includes a non-empty timestamp field."""
        event = EventFactory.agent_status_changed(
            job_id="test-job",
            tenant_key="test-tenant",
            old_status="blocked",
            new_status="working",
            agent_display_name="reviewer",
        )

        assert event["timestamp"]

    def test_agent_status_changed_converts_uuid_job_id_to_string(self):
        """UUID objects passed as job_id are serialised to strings."""
        job_uuid = uuid.uuid4()
        event = EventFactory.agent_status_changed(
            job_id=job_uuid,
            tenant_key="test-tenant",
            old_status="waiting",
            new_status="working",
            agent_display_name="orchestrator",
        )

        assert event["data"]["job_id"] == str(job_uuid)

    def test_agent_status_changed_converts_uuid_project_id_to_string(self):
        """UUID objects passed as project_id are serialised to strings."""
        project_uuid = uuid.uuid4()
        event = EventFactory.agent_status_changed(
            job_id="test-job",
            tenant_key="test-tenant",
            old_status="blocked",
            new_status="working",
            agent_display_name="orchestrator",
            project_id=project_uuid,
        )

        assert event["data"]["project_id"] == str(project_uuid)

    def test_agent_status_changed_all_valid_new_statuses_accepted(self):
        """Every known valid status is accepted without raising a validation error."""
        valid_statuses = [
            "waiting", "working", "blocked", "complete",
            "silent", "decommissioned", "idle", "sleeping",
        ]
        for status in valid_statuses:
            event = EventFactory.agent_status_changed(
                job_id="test-job",
                tenant_key="test-tenant",
                old_status="working",
                new_status=status,
                agent_display_name="orchestrator",
            )
            assert event["data"]["status"] == status

    def test_agent_status_changed_duration_seconds_defaults_to_none(self):
        """duration_seconds is None when not provided."""
        event = EventFactory.agent_status_changed(
            job_id="test-job",
            tenant_key="test-tenant",
            old_status="working",
            new_status="complete",
            agent_display_name="orchestrator",
        )

        assert event["data"]["duration_seconds"] is None

    def test_agent_status_changed_duration_seconds_included_when_provided(self):
        """duration_seconds appears in event data when explicitly passed."""
        event = EventFactory.agent_status_changed(
            job_id="test-job",
            tenant_key="test-tenant",
            old_status="working",
            new_status="complete",
            agent_display_name="orchestrator",
            duration_seconds=42.5,
        )

        assert event["data"]["duration_seconds"] == 42.5
