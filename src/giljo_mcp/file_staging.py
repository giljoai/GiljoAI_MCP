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

    # Stage slash commands
    zip_path = await staging.stage_slash_commands(tenant_key, token)

    # Stage agent templates
    zip_path = await staging.stage_agent_templates(tenant_key, token)

    # Cleanup
    await staging.cleanup(tenant_key, token)
"""

import json
import logging
import shutil
import zipfile
from pathlib import Path
from typing import Optional

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

    def __init__(
        self,
        base_path: Optional[Path] = None,
        db_session: Optional[AsyncSession] = None
    ):
        """
        Initialize FileStaging.

        Args:
            base_path: Base directory for staging (defaults to ./temp)
            db_session: Optional AsyncSession for agent template queries
        """
        self.base_path = base_path or Path.cwd() / "temp"
        self.db_session = db_session

    async def create_staging_directory(
        self,
        tenant_key: str,
        token: str
    ) -> Path:
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
        tenant_key: str,
        token: str
    ) -> Path:
        """
        Stage slash commands as a ZIP file.

        Creates a ZIP file containing all three slash command templates:
        - gil_import_productagents.md
        - gil_import_personalagents.md
        - gil_handover.md

        Args:
            tenant_key: Tenant identifier
            token: UUID token string

        Returns:
            Path: Path to generated ZIP file

        Raises:
            HTTPException: If ZIP creation fails
        """
        try:
            # Create staging directory
            staging_dir = await self.create_staging_directory(tenant_key, token)
            zip_path = staging_dir / "slash_commands.zip"

            # Get slash command templates
            templates = get_all_templates()

            # Create ZIP file
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for filename, content in templates.items():
                    zf.writestr(filename, content)

            logger.info(
                f"Created slash commands ZIP: {zip_path} "
                f"({len(templates)} files)"
            )

            return zip_path

        except OSError as e:
            logger.error(f"Disk error creating slash commands ZIP: {e}")
            raise HTTPException(
                status_code=status.HTTP_507_INSUFFICIENT_STORAGE,
                detail="Failed to create download file (disk error)"
            )
        except Exception as e:
            logger.error(f"Error creating slash commands ZIP: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create download file"
            )

    async def stage_agent_templates(
        self,
        tenant_key: str,
        token: str
    ) -> Path:
        """
        Stage agent templates as a ZIP file.

        Queries the database for active agent templates belonging to the
        tenant and creates a ZIP file with .md files.

        Args:
            tenant_key: Tenant identifier
            token: UUID token string

        Returns:
            Path: Path to generated ZIP file

        Raises:
            HTTPException: If ZIP creation fails or no templates found
        """
        if not self.db_session:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database session not configured for template staging"
            )

        try:
            # Create staging directory
            staging_dir = await self.create_staging_directory(tenant_key, token)
            zip_path = staging_dir / "agent_templates.zip"

            # Query active templates for tenant
            stmt = select(AgentTemplate).where(
                AgentTemplate.tenant_key == tenant_key,
                AgentTemplate.is_active == True
            ).order_by(AgentTemplate.name)

            result = await self.db_session.execute(stmt)
            templates = result.scalars().all()

            if not templates:
                logger.warning(f"No active templates found for tenant: {tenant_key}")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No active agent templates found"
                )

            # Create ZIP file
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for template in templates:
                    # Use template name as filename (e.g., "orchestrator.md")
                    filename = f"{template.name}.md"
                    content = template.template_content or ""
                    zf.writestr(filename, content)

            logger.info(
                f"Created agent templates ZIP: {zip_path} "
                f"({len(templates)} files)"
            )

            return zip_path

        except HTTPException:
            raise
        except OSError as e:
            logger.error(f"Disk error creating agent templates ZIP: {e}")
            raise HTTPException(
                status_code=status.HTTP_507_INSUFFICIENT_STORAGE,
                detail="Failed to create download file (disk error)"
            )
        except Exception as e:
            logger.error(f"Error creating agent templates ZIP: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create download file: {str(e)}"
            )

    async def save_metadata(
        self,
        staging_dir: Path,
        metadata: dict
    ) -> Path:
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
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save metadata"
            )

    async def cleanup(
        self,
        tenant_key: str,
        token: str
    ) -> bool:
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

    async def get_staging_path(
        self,
        tenant_key: str,
        token: str
    ) -> Path:
        """
        Get staging directory path for a token.

        Args:
            tenant_key: Tenant identifier
            token: UUID token string

        Returns:
            Path: Staging directory path (may not exist)
        """
        return self.base_path / tenant_key / token
