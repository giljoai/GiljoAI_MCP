# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Tests for 0907: MCP Bootstrap Setup Tool (giljo_setup).

Tests the combined ZIP staging that bundles slash commands + agent templates
into a single download for first-time setup.
"""

import zipfile
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.giljo_mcp.file_staging import FileStaging


def _make_template(name: str, role: str, description: str = "") -> MagicMock:
    """Create a mock AgentTemplate with required fields."""
    from datetime import datetime, timezone

    t = MagicMock()
    t.name = name
    t.role = role
    t.description = description or f"Agent for {role}"
    t.system_instructions = f"You are the {role} agent."
    t.user_instructions = f"Handle {role} tasks."
    t.behavioral_rules = "Follow project conventions."
    t.success_criteria = "Deliver quality work."
    t.model = "sonnet"
    t.background_color = None
    t.is_active = True
    t.is_default = False
    t.tenant_key = "test-tenant"
    t.cli_tool = None
    t.tools = None
    t.updated_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    t.last_exported_at = None
    return t


@pytest.fixture
def staging_dir(tmp_path):
    """Pre-created staging directory."""
    d = tmp_path / "staging"
    d.mkdir()
    return d


@pytest.fixture
def templates():
    """Two mock agent templates."""
    return [
        _make_template("Orchestrator", "orchestrator"),
        _make_template("Analyzer", "analyzer"),
    ]


@pytest.fixture
def mock_session(templates):
    """Mock async DB session that returns templates."""
    session = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = templates
    session.execute = AsyncMock(return_value=result)
    session.commit = AsyncMock()
    return session


class TestStageCombinedSetup:
    """Test FileStaging.stage_combined_setup() for all 3 platforms."""

    @pytest.mark.asyncio
    async def test_claude_code_zip_structure(self, staging_dir, mock_session):
        """Claude Code ZIP contains commands/*.md and agents/*.md."""
        staging = FileStaging(db_session=mock_session)

        zip_path, msg = await staging.stage_combined_setup(
            staging_dir, "test-tenant", platform="claude_code",
        )

        assert zip_path is not None
        assert zip_path.exists()
        assert "Successfully staged" in msg

        with zipfile.ZipFile(zip_path) as zf:
            names = zf.namelist()
            # Slash commands in commands/ directory
            assert "commands/gil_get_agents.md" in names
            assert "commands/gil_add.md" in names
            # Agent templates in agents/ directory
            agent_files = [n for n in names if n.startswith("agents/")]
            assert len(agent_files) == 2
            for af in agent_files:
                assert af.endswith(".md")

    @pytest.mark.asyncio
    async def test_gemini_cli_zip_structure(self, staging_dir, mock_session):
        """Gemini CLI ZIP contains commands/*.toml and agents/*.md."""
        staging = FileStaging(db_session=mock_session)

        zip_path, _ = await staging.stage_combined_setup(
            staging_dir, "test-tenant", platform="gemini_cli",
        )

        assert zip_path is not None

        with zipfile.ZipFile(zip_path) as zf:
            names = zf.namelist()
            # Slash commands as TOML
            assert "commands/gil_get_agents.toml" in names
            assert "commands/gil_add.toml" in names
            # Agent templates as MD
            agent_files = [n for n in names if n.startswith("agents/")]
            assert len(agent_files) == 2
            for af in agent_files:
                assert af.endswith(".md")

    @pytest.mark.asyncio
    async def test_codex_cli_zip_structure(self, staging_dir, mock_session):
        """Codex CLI ZIP contains skills/*/SKILL.md and agents/gil-*.toml."""
        staging = FileStaging(db_session=mock_session)

        zip_path, _ = await staging.stage_combined_setup(
            staging_dir, "test-tenant", platform="codex_cli",
        )

        assert zip_path is not None

        with zipfile.ZipFile(zip_path) as zf:
            names = zf.namelist()
            # Skills (Codex's slash command format)
            assert "skills/gil-get-agents/SKILL.md" in names
            assert "skills/gil-add/SKILL.md" in names
            # Agent templates as TOML
            agent_files = [n for n in names if n.startswith("agents/")]
            assert len(agent_files) == 2
            for af in agent_files:
                assert af.endswith(".toml")

    @pytest.mark.asyncio
    async def test_codex_agent_toml_content(self, staging_dir, mock_session):
        """Codex agent TOML files contain required fields."""
        staging = FileStaging(db_session=mock_session)

        zip_path, _ = await staging.stage_combined_setup(
            staging_dir, "test-tenant", platform="codex_cli",
        )

        with zipfile.ZipFile(zip_path) as zf:
            agent_files = [n for n in zf.namelist() if n.startswith("agents/")]
            for af in agent_files:
                content = zf.read(af).decode("utf-8")
                # Must have TOML-style key-value pairs
                assert "name =" in content
                assert "description =" in content
                assert "developer_instructions" in content

    @pytest.mark.asyncio
    async def test_zip_filename(self, staging_dir, mock_session):
        """Combined ZIP uses giljo_setup.zip filename."""
        staging = FileStaging(db_session=mock_session)

        zip_path, _ = await staging.stage_combined_setup(
            staging_dir, "test-tenant", platform="claude_code",
        )

        assert zip_path.name == "giljo_setup.zip"

    @pytest.mark.asyncio
    async def test_no_templates_still_includes_slash_commands(self, staging_dir):
        """If no agent templates exist, ZIP still contains slash commands."""
        session = AsyncMock()
        result = MagicMock()
        result.scalars.return_value.all.return_value = []
        session.execute = AsyncMock(return_value=result)

        staging = FileStaging(db_session=session)

        zip_path, _ = await staging.stage_combined_setup(
            staging_dir, "test-tenant", platform="claude_code",
        )

        assert zip_path is not None
        with zipfile.ZipFile(zip_path) as zf:
            names = zf.namelist()
            # Slash commands present
            assert "commands/gil_get_agents.md" in names
            # No agent templates
            agent_files = [n for n in names if n.startswith("agents/")]
            assert len(agent_files) == 0

    @pytest.mark.asyncio
    async def test_invalid_platform_raises(self, staging_dir, mock_session):
        """Invalid platform raises ValueError."""
        staging = FileStaging(db_session=mock_session)

        with pytest.raises(ValueError, match="Unknown platform"):
            await staging.stage_combined_setup(
                staging_dir, "test-tenant", platform="invalid",
            )

    @pytest.mark.asyncio
    async def test_generic_zip_structure(self, staging_dir, mock_session):
        """Generic ZIP contains commands/*.md and agents/*.md without platform frontmatter."""
        staging = FileStaging(db_session=mock_session)

        zip_path, _ = await staging.stage_combined_setup(
            staging_dir, "test-tenant", platform="generic",
        )

        assert zip_path is not None

        with zipfile.ZipFile(zip_path) as zf:
            names = zf.namelist()
            # Slash commands as plain MD reference
            cmd_files = [n for n in names if n.startswith("commands/")]
            assert len(cmd_files) >= 2
            # Agent templates as plain MD
            agent_files = [n for n in names if n.startswith("agents/")]
            assert len(agent_files) == 2
            for af in agent_files:
                assert af.endswith(".md")
                content = zf.read(af).decode("utf-8")
                # Generic templates must NOT have YAML frontmatter
                assert not content.startswith("---")

    @pytest.mark.asyncio
    async def test_updates_last_exported_at(self, staging_dir, mock_session, templates):
        """Agent templates get last_exported_at updated after staging."""
        staging = FileStaging(db_session=mock_session)

        await staging.stage_combined_setup(
            staging_dir, "test-tenant", platform="claude_code",
        )

        # Verify commit was called (timestamp update persisted)
        mock_session.commit.assert_awaited_once()
        # Verify templates got timestamps set
        for t in templates:
            assert t.last_exported_at is not None
