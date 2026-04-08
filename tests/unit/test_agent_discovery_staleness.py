# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Tests for agent staleness detection in get_available_agents() (Handover 0421).

Split from test_agent_discovery.py.

Test Coverage:
- _format_agent_info() includes staleness fields
- Staleness fields with type_only depth
- get_available_agents() staleness warning when stale agents detected
- No staleness warning when all agents are fresh
- Actionable guidance in staleness warning
- Null timestamp handling for staleness detection
"""

from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio

from src.giljo_mcp.models import AgentTemplate


class TestAgentStalenessDetection:
    """Test suite for agent staleness detection (Handover 0421)."""

    @pytest_asyncio.fixture(autouse=True)
    async def setup_method(self, db_session):
        """Setup for each test method"""
        from src.giljo_mcp.tenant import TenantManager

        self.db_session = db_session
        self.tenant_key = TenantManager.generate_tenant_key()

    @pytest.mark.asyncio
    async def test_format_agent_info_includes_staleness_fields(self, db_session):
        """Test that _format_agent_info() includes staleness detection fields."""
        from src.giljo_mcp.tools.agent_discovery import _format_agent_info

        # Create template with staleness
        now = datetime.now(timezone.utc)
        template = AgentTemplate(
            id="test-template-1",
            tenant_key=self.tenant_key,
            name="test-agent",
            role="Tester",
            version="1.0.0",
            system_instructions="Test template",
            is_active=True,
            updated_at=now,
            last_exported_at=now - timedelta(days=1),  # Exported 1 day ago
        )

        # Format with full depth
        result = _format_agent_info(template, depth="full")

        # Verify staleness fields present
        assert "may_be_stale" in result
        assert result["may_be_stale"] is True  # updated_at > last_exported_at
        assert "last_exported_at" in result
        assert "updated_at" in result
        assert result["last_exported_at"] == (now - timedelta(days=1)).isoformat()
        assert result["updated_at"] == now.isoformat()

    @pytest.mark.asyncio
    async def test_format_agent_info_staleness_fields_with_type_only_depth(self, db_session):
        """Test that staleness fields are included even with type_only depth."""
        from src.giljo_mcp.tools.agent_discovery import _format_agent_info

        now = datetime.now(timezone.utc)
        template = AgentTemplate(
            id="test-template-2",
            tenant_key=self.tenant_key,
            name="test-agent",
            role="Tester",
            version="1.0.0",
            system_instructions="Test template",
            is_active=True,
            updated_at=now,
            last_exported_at=now - timedelta(days=1),
        )

        # Format with type_only depth
        result = _format_agent_info(template, depth="type_only")

        # Staleness fields should still be present (always included)
        assert "may_be_stale" in result
        assert "last_exported_at" in result
        assert "updated_at" in result

    @pytest.mark.asyncio
    async def test_get_available_agents_includes_staleness_warning(self, db_session):
        """Test that get_available_agents() includes staleness warning when stale agents detected."""
        from src.giljo_mcp.tools.agent_discovery import get_available_agents

        # Create stale template
        now = datetime.now(timezone.utc)
        stale_template = AgentTemplate(
            id="stale-template",
            tenant_key=self.tenant_key,
            name="stale-agent",
            role="Stale Role",
            version="1.0.0",
            system_instructions="Stale template",
            is_active=True,
            updated_at=now,
            last_exported_at=now - timedelta(days=1),
        )

        # Create fresh template
        fresh_template = AgentTemplate(
            id="fresh-template",
            tenant_key=self.tenant_key,
            name="fresh-agent",
            role="Fresh Role",
            version="1.0.0",
            system_instructions="Fresh template",
            is_active=True,
            updated_at=now - timedelta(days=2),
            last_exported_at=now,
        )

        db_session.add_all([stale_template, fresh_template])
        await db_session.commit()

        # Call get_available_agents
        result = await get_available_agents(db_session, self.tenant_key, depth="full")

        # Verify response structure
        assert result["success"] is True
        assert "data" in result
        assert "agents" in result["data"]
        assert "staleness_warning" in result["data"]

        # Verify staleness warning
        warning = result["data"]["staleness_warning"]
        assert warning["has_stale_agents"] is True
        assert warning["stale_count"] == 1
        assert "stale-agent" in warning["stale_agents"]
        assert "fresh-agent" not in warning["stale_agents"]
        assert "action_required" in warning
        assert "options" in warning
        assert len(warning["options"]) == 3

    @pytest.mark.asyncio
    async def test_get_available_agents_no_staleness_warning_when_all_fresh(self, db_session):
        """Test that staleness_warning is omitted when all agents are fresh."""
        from src.giljo_mcp.tools.agent_discovery import get_available_agents

        # Create fresh template
        now = datetime.now(timezone.utc)
        fresh_template = AgentTemplate(
            id="fresh-template",
            tenant_key=self.tenant_key,
            name="fresh-agent",
            role="Fresh Role",
            version="1.0.0",
            system_instructions="Fresh template",
            is_active=True,
            updated_at=now - timedelta(days=1),
            last_exported_at=now,
        )

        db_session.add(fresh_template)
        await db_session.commit()

        # Call get_available_agents
        result = await get_available_agents(db_session, self.tenant_key, depth="full")

        # Verify staleness_warning is NOT present
        assert result["success"] is True
        assert "staleness_warning" not in result["data"]

    @pytest.mark.asyncio
    async def test_staleness_warning_includes_actionable_guidance(self, db_session):
        """Test that staleness warning provides actionable guidance."""
        from src.giljo_mcp.tools.agent_discovery import get_available_agents

        now = datetime.now(timezone.utc)
        stale_template = AgentTemplate(
            id="stale-template",
            tenant_key=self.tenant_key,
            name="stale-agent",
            role="Stale Role",
            version="1.0.0",
            system_instructions="Stale template",
            is_active=True,
            updated_at=now,
            last_exported_at=now - timedelta(days=1),
        )

        db_session.add(stale_template)
        await db_session.commit()

        result = await get_available_agents(db_session, self.tenant_key, depth="full")

        warning = result["data"]["staleness_warning"]

        # Verify action_required mentions key concepts
        assert "gil_get_agents" in warning["action_required"]
        assert "sync" in warning["action_required"].lower() or "export" in warning["action_required"].lower()

        # Verify options provide clear choices
        assert any("gil_get_agents" in option for option in warning["options"])
        assert any("continue" in option.lower() for option in warning["options"])
        assert any("abort" in option.lower() for option in warning["options"])

    @pytest.mark.asyncio
    async def test_staleness_detection_handles_null_timestamps(self, db_session):
        """Test staleness detection handles null last_exported_at gracefully."""
        from src.giljo_mcp.tools.agent_discovery import get_available_agents

        # Create template that was never exported
        template = AgentTemplate(
            id="never-exported",
            tenant_key=self.tenant_key,
            name="new-agent",
            role="New Role",
            version="1.0.0",
            system_instructions="New template",
            is_active=True,
            updated_at=datetime.now(timezone.utc),
            last_exported_at=None,  # Never exported
        )

        db_session.add(template)
        await db_session.commit()

        result = await get_available_agents(db_session, self.tenant_key, depth="full")

        # Should not crash, template should NOT be marked as stale
        assert result["success"] is True
        agents = result["data"]["agents"]
        assert len(agents) == 1
        assert agents[0]["may_be_stale"] is False  # Not stale if never exported
        assert agents[0]["last_exported_at"] is None
