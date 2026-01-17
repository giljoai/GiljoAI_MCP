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

    # Stage slash commands
    zip_path, msg = await staging.stage_slash_commands(staging_path)

    # Stage agent templates
    zip_path, msg = await staging.stage_agent_templates(staging_path, tenant_key, db_session)

    # Cleanup
    await staging.cleanup(tenant_key, token)
"""

import json
import logging
import re
import shutil
import zipfile
from pathlib import Path
from typing import Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import AgentTemplate
from .tools.slash_command_templates import get_all_templates


logger = logging.getLogger(__name__)


class FileStaging:
    """
    Manages temporary file staging for download tokens.

    Creates staging directories, generates ZIP files, and handles cleanup
    with multi-tenant isolation and directory traversal protection.
    """

    def __init__(self, base_path: Optional[Path] = None, db_session: Optional[AsyncSession] = None):
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
    ) -> Tuple[Optional[Path], str]:
        """
        Stage slash commands as a ZIP file.

        Creates a ZIP file containing GiljoAI slash command files (.md) for CLI tools.
        Includes core commands: gil_get_claude_agents (unified agent installer),
        gil_activate, gil_launch, gil_handover

        Args:
            staging_path: Pre-created staging directory (temp/{tenant_key}/{token}/)

        Returns:
            Tuple (zip_path|None, message)

        Raises:
            None - returns (None, message) on error
        """
        try:
            staging_path.mkdir(parents=True, exist_ok=True)
            zip_path = staging_path / "slash_commands.zip"

            # Get all templates
            all_templates = get_all_templates()
            # Select a stable subset - core commands for CLI users
            # Note: Legacy template installers removed (redundant with gil_get_claude_agents)
            wanted = [
                "gil_get_claude_agents.md",  # Unified agent installer (interactive)
                "gil_activate.md",
                "gil_launch.md",
                "gil_handover.md",
            ]
            missing = [w for w in wanted if w not in all_templates]
            if missing:
                msg = f"Missing slash command templates: {', '.join(missing)}"
                logger.error(msg)
                return (None, msg)
            templates = {name: all_templates[name] for name in wanted}

            # Create ZIP file with single command
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for filename, content in templates.items():
                    zf.writestr(filename, content)

            logger.info(f"Staged slash commands ZIP: {zip_path} ({len(templates)} files)")
            return (zip_path, f"Successfully staged {len(templates)} slash commands")
        except OSError as e:
            msg = f"Disk error creating slash commands ZIP: {e}"
            logger.error(msg)
            return (None, msg)
        except Exception as e:
            msg = f"Unexpected error creating slash commands ZIP: {e}"
            logger.error(msg)
            return (None, msg)

    async def stage_agent_templates(
        self,
        staging_path: Path,
        tenant_key: str,
        db_session: Optional[AsyncSession] = None,
    ) -> Tuple[Optional[Path], str]:
        """
        Stage agent templates as a ZIP file.

        Queries the database for active agent templates belonging to the
        tenant and creates a ZIP file with .md files.

        **Handover 0421**: Updates last_exported_at timestamp for all exported templates
        to enable staleness detection in get_available_agents().

        Args:
            staging_path: Pre-created staging directory (temp/{tenant_key}/{token}/)
            tenant_key: Tenant identifier
            db_session: Optional DB session override

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
            stmt = (
                select(AgentTemplate)
                .where(AgentTemplate.tenant_key == tenant_key, AgentTemplate.is_active == True)
            )

            result = await session.execute(stmt)
            all_active = result.scalars().all()

            if not all_active:
                msg = f"No active templates found for tenant: {tenant_key}"
                logger.warning(msg)
                return (None, msg)

            # Apply packaging selection (cap to 8 templates)
            from .template_renderer import _slugify_filename, render_claude_agent, select_templates_for_packaging

            selected = select_templates_for_packaging(all_active, max_count=8)

            # Create ZIP file with Claude-compatible YAML/Markdown
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for template in selected:
                    filename = f"{_slugify_filename(template.name)}.md"
                    content = render_claude_agent(template)
                    zf.writestr(filename, content)

            # ═══════════════════════════════════════════════════════════════════════
            # Handover 0421: Update export timestamp for staleness detection
            # ═══════════════════════════════════════════════════════════════════════
            export_timestamp = datetime.now(timezone.utc)

            for template in selected:
                template.last_exported_at = export_timestamp

            await session.commit()

            logger.info(
                f"Updated last_exported_at for {len(selected)} templates at {export_timestamp.isoformat()}"
            )
            # ═══════════════════════════════════════════════════════════════════════

            logger.info(
                f"Staged agent templates ZIP: {zip_path} ({len(selected)} files from {len(all_active)} active templates)"
            )
            return (zip_path, f"Successfully staged {len(selected)} agent templates")
        except OSError as e:
            msg = f"Disk error staging agent templates: {e}"
            logger.error(msg)
            return (None, msg)
        except Exception as e:
            msg = f"Unexpected error staging agent templates: {e}"
            logger.error(msg)
            # Rollback on error
            if session:
                await session.rollback()
            return (None, msg)

    async def save_metadata(self, staging_dir: Path, metadata: dict) -> Path:
        """
        Save metadata JSON file to staging directory.

        Args:
            staging_dir: Staging directory path
            metadata: Metadata dictionary to save

        Returns:
            Path: Path to metadata.json file

        Raises:
            HTTPException: If file write fails
        """
        try:
            metadata_path = staging_dir / "metadata.json"
            metadata_path.write_text(json.dumps(metadata, indent=2))

            logger.debug(f"Saved metadata to: {metadata_path}")
            return metadata_path

        except Exception as e:
            logger.error(f"Error saving metadata: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to save metadata")

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

        except Exception as e:
            # Best-effort cleanup - log but don't raise
            logger.warning(f"Error cleaning up staging directory: {e}")
            return False

    async def get_staging_path(self, tenant_key: str, token: str) -> Path:
        """
        Get staging directory path for a token.

        Args:
            tenant_key: Tenant identifier
            token: UUID token string

        Returns:
            Path: Staging directory path (may not exist)
        """
        return self.base_path / tenant_key / token

    @staticmethod
    def validate_filename(filename: str) -> bool:
        """Validate filename to prevent directory traversal and invalid characters."""
        if ".." in filename or "/" in filename or "\\" in filename:
            return False
        return re.match(r"^[a-zA-Z0-9._-]+$", filename) is not None
