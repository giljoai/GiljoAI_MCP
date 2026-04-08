# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
File Staging for one-time download token system.

Handover 0100: Temporary file staging for secure downloads.

Features:
- Staging directory creation (temp/{tenant_key}/{token}/)
- ZIP file generation for slash commands and agent templates
- Metadata JSON persistence
- Cleanup after download
- Directory traversal protection

Usage:
    staging = FileStaging(base_path=Path("temp"), db_session=db_session)

    # Create staging path
    staging_path = await staging.create_staging_directory(tenant_key, token)

    # Stage slash commands (platform: claude_code, gemini_cli, codex_cli)
    zip_path, msg = await staging.stage_slash_commands(staging_path, platform="claude_code")

    # Stage agent templates (platform: claude_code, gemini_cli, codex_cli)
    zip_path, msg = await staging.stage_agent_templates(staging_path, tenant_key, db_session, platform="claude_code")

    # Cleanup
    await staging.cleanup(tenant_key, token)
"""

import logging
import re
import shutil
import zipfile
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import AgentTemplate
from .tools.slash_command_templates import get_all_templates


logger = logging.getLogger(__name__)


def _codex_agents_to_toml(agents: list[dict]) -> list[tuple[str, str]]:
    """Convert Codex agent dicts to (zip_path, toml_content) pairs.

    Renders each agent as a standalone TOML file that Codex CLI reads
    when referenced from config.toml. Uses the gil- prefix to avoid
    shadowing Codex built-in roles.
    """
    entries = []
    for agent in agents:
        name = agent["agent_name"]
        slug = name.lower().replace(" ", "-").replace("_", "-")
        if not slug.startswith("gil-"):
            slug = f"gil-{slug}"

        # Escape triple-quoted strings for TOML multiline
        instructions = agent.get("developer_instructions", "")
        # Replace any literal triple-quotes in instructions to avoid TOML parse errors
        instructions = instructions.replace('"""', '\\"\\"\\"')

        toml_content = (
            f'name = "{slug}"\n'
            f'description = "{agent.get("description", "")}"\n'
            f'nickname_candidates = ["{slug}"]\n'
            f'model = "{agent.get("suggested_model", "gpt-5.2-codex")}"\n'
            f'model_reasoning_effort = "{agent.get("suggested_reasoning_effort", "medium")}"\n'
            f'developer_instructions = """\n{instructions}\n"""\n'
        )
        entries.append((f"agents/{slug}.toml", toml_content))
    return entries


class FileStaging:
    """
    Manages temporary file staging for download tokens.

    Creates staging directories, generates ZIP files, and handles cleanup
    with multi-tenant isolation and directory traversal protection.
    """

    def __init__(self, base_path: Path | None = None, db_session: AsyncSession | None = None):
        """
        Initialize FileStaging.

        Args:
            base_path: Base directory for staging (defaults to ./temp)
            db_session: Optional AsyncSession for agent template queries
        """
        self.base_path = base_path or Path.cwd() / "temp"
        self.db_session = db_session

    async def create_staging_directory(self, tenant_key: str, token: str) -> Path:
        """
        Create staging directory for a token.

        Creates directory structure: temp/{tenant_key}/{token}/
        with protection against directory traversal attacks.

        Args:
            tenant_key: Tenant identifier
            token: UUID token string

        Returns:
            Path: Staging directory path

        Raises:
            ValueError: If tenant_key or token contain path traversal attempts
        """
        # Prevent directory traversal attacks
        if ".." in tenant_key or "/" in tenant_key or "\\" in tenant_key:
            logger.error(f"Directory traversal attempt detected in tenant_key: {tenant_key}")
            raise ValueError("Invalid tenant_key: path traversal detected")

        if ".." in token or "/" in token or "\\" in token:
            logger.error(f"Directory traversal attempt detected in token: {token}")
            raise ValueError("Invalid token: path traversal detected")

        # Create staging directory
        staging_dir = self.base_path / tenant_key / token
        staging_dir.mkdir(parents=True, exist_ok=True)

        logger.debug(f"Created staging directory: {staging_dir}")
        return staging_dir

    async def stage_slash_commands(
        self,
        staging_path: Path,
        platform: str = "claude_code",
    ) -> tuple[Path | None, str]:
        """
        Stage slash commands as a ZIP file.

        Creates a ZIP file containing platform-specific slash command/skill files.

        Args:
            staging_path: Pre-created staging directory (temp/{tenant_key}/{token}/)
            platform: Target CLI platform (claude_code, gemini_cli, codex_cli)

        Returns:
            Tuple (zip_path|None, message)

        Raises:
            None - returns (None, message) on error
        """
        try:
            staging_path.mkdir(parents=True, exist_ok=True)
            zip_path = staging_path / "slash_commands.zip"

            # Get platform-specific templates (0836b)
            templates = get_all_templates(platform=platform)

            # Create ZIP file with single command
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for filename, content in templates.items():
                    zf.writestr(filename, content)

            logger.info(f"Staged slash commands ZIP: {zip_path} ({len(templates)} files)")
            return (zip_path, f"Successfully staged {len(templates)} slash commands")
        except (OSError, ValueError, RuntimeError) as e:
            if isinstance(e, OSError):
                msg = f"Disk error creating slash commands ZIP: {e}"
            else:
                msg = f"Unexpected error creating slash commands ZIP: {e}"
            logger.exception(msg)
            return (None, msg)

    async def stage_agent_templates(
        self,
        staging_path: Path,
        tenant_key: str,
        db_session: AsyncSession | None = None,
        platform: str = "claude_code",
    ) -> tuple[Path | None, str]:
        """
        Stage agent templates as a ZIP file.

        Queries the database for active agent templates belonging to the
        tenant and creates a ZIP file with platform-appropriate content.

        **Handover 0421**: Updates last_exported_at timestamp for all exported templates
        to enable staleness detection in get_available_agents().
        **Handover 0836a**: Platform-aware rendering via AgentTemplateAssembler.

        Args:
            staging_path: Pre-created staging directory (temp/{tenant_key}/{token}/)
            tenant_key: Tenant identifier
            db_session: Optional DB session override
            platform: Target platform (claude_code, codex_cli, gemini_cli)

        Returns:
            Tuple (zip_path|None, message)

        Raises:
            None - returns (None, message) on error
        """
        session = db_session or self.db_session
        if not session:
            return (None, "Database session not configured for template staging")

        try:
            from datetime import datetime, timezone

            staging_path.mkdir(parents=True, exist_ok=True)
            zip_path = staging_path / "agent_templates.zip"

            # Query active templates for tenant
            stmt = select(AgentTemplate).where(AgentTemplate.tenant_key == tenant_key, AgentTemplate.is_active)

            result = await session.execute(stmt)
            all_active = result.scalars().all()

            if not all_active:
                msg = f"No active templates found for tenant: {tenant_key}"
                logger.warning(msg)
                return (None, msg)

            # Apply packaging selection (cap to 8 templates)
            from .template_renderer import select_templates_for_packaging
            from .tools.agent_template_assembler import AgentTemplateAssembler

            selected = select_templates_for_packaging(all_active, max_count=8)

            # Assemble templates for the target platform (Handover 0836a)
            assembler = AgentTemplateAssembler()
            export_data = assembler.assemble(selected, platform)

            # Create ZIP file with platform-appropriate content
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                if platform == "codex_cli":
                    import json

                    zf.writestr("agents.json", json.dumps(export_data, indent=2))
                else:
                    for agent in export_data["agents"]:
                        zf.writestr(agent["filename"], agent["content"])

            # ═══════════════════════════════════════════════════════════════════════
            # Handover 0421: Update export timestamp for staleness detection
            # ═══════════════════════════════════════════════════════════════════════
            export_timestamp = datetime.now(timezone.utc)

            for template in selected:
                template.last_exported_at = export_timestamp

            await session.commit()

            logger.info(f"Updated last_exported_at for {len(selected)} templates at {export_timestamp.isoformat()}")
            # ═══════════════════════════════════════════════════════════════════════

            logger.info(
                f"Staged agent templates ZIP: {zip_path} ({len(selected)} files from {len(all_active)} active templates)"
            )
            return (zip_path, f"Successfully staged {len(selected)} agent templates")
        except (OSError, ValueError, RuntimeError) as e:
            if isinstance(e, OSError):
                msg = f"Disk error staging agent templates: {e}"
            else:
                msg = f"Unexpected error staging agent templates: {e}"
            logger.exception(msg)
            # Rollback on error
            if session:
                await session.rollback()
            return (None, msg)

    async def stage_combined_setup(
        self,
        staging_path: Path,
        tenant_key: str,
        db_session: AsyncSession | None = None,
        platform: str = "claude_code",
    ) -> tuple[Path | None, str]:
        """
        Stage slash commands AND agent templates in a single ZIP (Handover 0907).

        Creates a combined ZIP structured so it extracts directly into the
        platform's home directory root (~/.claude/, ~/.gemini/, ~/.codex/).
        Agent templates are binary content — no LLM processing on the client.

        Args:
            staging_path: Pre-created staging directory
            tenant_key: Tenant identifier
            db_session: Optional DB session override
            platform: Target CLI platform (claude_code, gemini_cli, codex_cli)

        Returns:
            Tuple (zip_path|None, message)
        """
        from .tools.slash_command_templates import _VALID_PLATFORMS, get_all_templates

        if platform not in _VALID_PLATFORMS:
            raise ValueError(f"Unknown platform '{platform}'. Must be one of: {', '.join(_VALID_PLATFORMS)}")

        session = db_session or self.db_session

        try:
            staging_path.mkdir(parents=True, exist_ok=True)
            zip_path = staging_path / "giljo_setup.zip"

            # --- Slash commands ---
            slash_templates = get_all_templates(platform=platform)

            # Map slash command filenames into platform directory structure
            slash_dir = "skills" if platform == "codex_cli" else "commands"

            # --- Agent templates (if DB session available) ---
            agent_entries: list[tuple[str, str]] = []
            selected_templates: list = []

            if session:
                from datetime import datetime, timezone

                from .template_renderer import select_templates_for_packaging
                from .tools.agent_template_assembler import AgentTemplateAssembler

                result = await session.execute(
                    select(AgentTemplate).where(
                        AgentTemplate.tenant_key == tenant_key,
                        AgentTemplate.is_active,
                    )
                )
                all_active = result.scalars().all()

                if all_active:
                    selected_templates = select_templates_for_packaging(all_active, max_count=8)
                    assembler = AgentTemplateAssembler()
                    export_data = assembler.assemble(selected_templates, platform)

                    if platform == "codex_cli":
                        agent_entries = _codex_agents_to_toml(export_data["agents"])
                    else:
                        for agent in export_data["agents"]:
                            agent_entries.append(
                                (
                                    f"agents/{agent['filename']}",
                                    agent["content"],
                                )
                            )

            # --- Build ZIP ---
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for filename, content in slash_templates.items():
                    zf.writestr(f"{slash_dir}/{filename}", content)
                for zip_name, content in agent_entries:
                    zf.writestr(zip_name, content)

            # Update export timestamps
            if selected_templates and session:
                export_timestamp = datetime.now(timezone.utc)
                for t in selected_templates:
                    t.last_exported_at = export_timestamp
                await session.commit()

            total = len(slash_templates) + len(agent_entries)
            logger.info(f"Staged combined setup ZIP: {zip_path} ({total} files for {platform})")
            return (
                zip_path,
                f"Successfully staged {total} files ({len(slash_templates)} commands, {len(agent_entries)} agents)",
            )

        except (OSError, ValueError, RuntimeError) as e:
            msg = f"Error staging combined setup ZIP: {e}"
            logger.exception(msg)
            if session:
                await session.rollback()
            if isinstance(e, ValueError):
                raise
            return (None, msg)

    async def cleanup(self, tenant_key: str, token: str) -> bool:
        """
        Remove staging directory and all contents.

        Performs best-effort cleanup after download completes.
        Does not raise exceptions if directory doesn't exist.

        Args:
            tenant_key: Tenant identifier
            token: UUID token string

        Returns:
            bool: True if cleanup succeeded, False otherwise
        """
        try:
            staging_dir = self.base_path / tenant_key / token

            if not staging_dir.exists():
                logger.debug(f"Staging directory already removed: {staging_dir}")
                return True

            # Remove directory and all contents
            shutil.rmtree(staging_dir)

            logger.debug(f"Cleaned up staging directory: {staging_dir}")
            return True

        except (OSError, RuntimeError) as e:
            # Best-effort cleanup - log but don't raise
            logger.warning(f"Error cleaning up staging directory: {e}")
            return False

    @staticmethod
    def validate_filename(filename: str) -> bool:
        """Validate filename to prevent directory traversal and invalid characters."""
        if ".." in filename or "/" in filename or "\\" in filename:
            return False
        return re.match(r"^[a-zA-Z0-9._-]+$", filename) is not None
