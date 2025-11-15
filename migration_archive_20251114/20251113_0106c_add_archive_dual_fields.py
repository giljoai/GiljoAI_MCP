"""Add system_instructions and user_instructions to template_archives (Handover 0106c)

Revision ID: 20251113_0106c
Revises: 8cd632d27c5e
Create Date: 2025-11-13

CRITICAL SCHEMA ALIGNMENT FIX: Aligns template_archives with agent_templates dual-field structure.

Context:
- Handover 0106 added system_instructions/user_instructions to agent_templates
- template_archives table was created WITHOUT these columns (add_template_mgmt migration)
- ORM model (TemplateArchive) includes these fields (lines 142-143 of models/templates.py)
- Fresh installs using create_all() get columns, but migration-based installs don't
- Tests expect both fields to exist (test_templates_api_0106.py)

This migration:
1. Adds system_instructions column (Text, nullable)
2. Adds user_instructions column (Text, nullable)
3. Backfills existing archives (splits template_content if present)
4. Creates index for archive searches
5. Marks template_content as deprecated (consistent with agent_templates)

Migration Strategy:
- Nullable columns (archives may have old data format)
- Backfill from template_content where available
- Non-destructive (template_content preserved for rollback)
- Idempotent (safe to run multiple times)

Schema Changes:
- Add system_instructions column (Text, nullable)
- Add user_instructions column (Text, nullable)

Data Migration:
- Split existing template_content at MCP marker (if present)
- Content before marker → user_instructions
- Content after marker → system_instructions
- If no marker: template_content → user_instructions, system_instructions NULL

Rollback Strategy:
- Merge system_instructions + user_instructions back to template_content
- Drop new columns
- Remove deprecation comment
"""
from typing import Union, Sequence
import re
import logging

import sqlalchemy as sa
from sqlalchemy import text
from alembic import op

# Configure logging
logger = logging.getLogger(__name__)

# Revision identifiers, used by Alembic.
revision: str = "20251113_0106c"
down_revision: Union[str, Sequence[str], None] = "8cd632d27c5e"  # After merge of 0106 + 0106b
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _split_template_content_archive(content: str) -> tuple[str, str]:
    """Split archive template content into user and system instructions.

    For archives, we handle two cases:
    1. Content has MCP marker → split at marker
    2. Content has no marker → treat entire content as user_instructions

    Unlike agent_templates (0106), we don't apply default system instructions
    to archives because they represent historical snapshots.

    Args:
        content: Original template_content from archive

    Returns:
        tuple[str, str]: (user_instructions, system_instructions or None)
    """
    if not content or len(content.strip()) == 0:
        return ("", None)

    # Regex pattern for MCP marker (case-insensitive, optional spacing)
    mcp_pattern = r"##\s*MCP\s+COMMUNICATION\s+PROTOCOL"

    match = re.search(mcp_pattern, content, re.IGNORECASE)

    if match:
        # Split at the marker
        split_index = match.start()
        user_instructions = content[:split_index].strip()
        system_instructions = content[split_index:].strip()

        logger.info(f"Split archive: user={len(user_instructions)} chars, system={len(system_instructions)} chars")
        return (user_instructions, system_instructions)
    else:
        # No marker found - treat entire content as user_instructions
        # system_instructions remains NULL for historical archives
        logger.debug("No MCP marker in archive - storing as user_instructions only")
        return (content.strip(), None)


def upgrade() -> None:
    """Upgrade schema - add system_instructions and user_instructions to template_archives.

    Migration Steps:
    1. Analyze current state (log archive counts)
    2. Add new columns (nullable for backwards compatibility)
    3. Migrate data (split template_content for existing archives)
    4. Add comment to template_content (mark as deprecated)
    5. Verification (log completion stats)
    """
    logger.info("=" * 80)
    logger.info("Starting migration 0106c: Add Dual Fields to Template Archives")
    logger.info("=" * 80)

    # Get database connection
    connection = op.get_bind()

    # ========================================================================
    # STEP 1: Analyze Current State
    # ========================================================================
    logger.info("STEP 1: Analyzing current state...")

    result = connection.execute(text("SELECT COUNT(*) FROM template_archives"))
    total_archives = result.scalar()
    logger.info(f"Found {total_archives} archives to migrate")

    # ========================================================================
    # STEP 2: Add New Columns (nullable for historical archives)
    # ========================================================================
    logger.info("STEP 2: Adding new columns (idempotent - checks for existence)...")

    # Check if system_instructions column exists
    system_col_check = connection.execute(
        text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'template_archives'
            AND column_name = 'system_instructions'
        """)
    )
    system_col_exists = system_col_check.fetchone() is not None

    # Check if user_instructions column exists
    user_col_check = connection.execute(
        text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'template_archives'
            AND column_name = 'user_instructions'
        """)
    )
    user_col_exists = user_col_check.fetchone() is not None

    if system_col_exists and user_col_exists:
        logger.info("Columns already exist (skipping creation)")
        logger.info("Migration may have been applied manually or by previous process")
        # Skip to verification step - columns exist, just verify data
    else:
        if not system_col_exists:
            op.add_column(
                "template_archives",
                sa.Column(
                    "system_instructions",
                    sa.Text(),
                    nullable=True,  # Nullable - historical archives may not have system instructions
                    comment="Protected MCP coordination rules archived with template (nullable for historical data)",
                ),
            )
            logger.info("Added system_instructions column")
        else:
            logger.info("system_instructions column already exists")

        if not user_col_exists:
            op.add_column(
                "template_archives",
                sa.Column(
                    "user_instructions",
                    sa.Text(),
                    nullable=True,
                    comment="User-customizable guidance archived with template (nullable for historical data)",
                ),
            )
            logger.info("Added user_instructions column")
        else:
            logger.info("user_instructions column already exists")

        logger.info("Column addition complete")

    # ========================================================================
    # STEP 3: Migrate Data (split template_content for existing archives)
    # ========================================================================
    logger.info("STEP 3: Migrating data - splitting template_content...")

    # Fetch all archives with content
    archives_result = connection.execute(
        text("SELECT id, template_content FROM template_archives WHERE template_content IS NOT NULL ORDER BY id")
    )
    archives = archives_result.fetchall()

    migrated_count = 0
    with_marker_count = 0
    without_marker_count = 0

    for archive_id, template_content in archives:
        # Split content
        user_instructions, system_instructions = _split_template_content_archive(template_content or "")

        # Track marker detection
        if system_instructions is not None:
            with_marker_count += 1
        else:
            without_marker_count += 1

        # Update archive with split content
        connection.execute(
            text("""
                UPDATE template_archives
                SET system_instructions = :sys_inst,
                    user_instructions = :user_inst
                WHERE id = :archive_id
            """),
            {
                "sys_inst": system_instructions,  # May be NULL for historical archives
                "user_inst": user_instructions if len(user_instructions) > 0 else None,
                "archive_id": archive_id,
            },
        )

        migrated_count += 1

        if migrated_count % 100 == 0:
            logger.info(f"Migrated {migrated_count}/{len(archives)} archives...")

    logger.info(f"Data migration complete:")
    logger.info(f"  - Total migrated: {migrated_count}")
    logger.info(f"  - With MCP marker (split): {with_marker_count}")
    logger.info(f"  - Without marker (user_instructions only): {without_marker_count}")

    # ========================================================================
    # STEP 4: Mark template_content as Deprecated
    # ========================================================================
    logger.info("STEP 4: Marking template_content as deprecated...")

    # Update column comment to indicate deprecation
    op.alter_column(
        "template_archives",
        "template_content",
        existing_type=sa.Text(),
        comment="DEPRECATED (v3.1): Use system_instructions + user_instructions instead. Preserved for rollback compatibility.",
    )

    logger.info("template_content marked as deprecated")

    # ========================================================================
    # STEP 5: Verification
    # ========================================================================
    logger.info("STEP 5: Verifying migration...")

    # Verify column addition
    verification_result = connection.execute(
        text("""
            SELECT
                COUNT(*) as total,
                COUNT(system_instructions) as with_system,
                COUNT(user_instructions) as with_user,
                AVG(LENGTH(system_instructions)) as avg_system_len,
                AVG(LENGTH(user_instructions)) as avg_user_len
            FROM template_archives
        """)
    )
    stats = verification_result.fetchone()

    logger.info(f"Verification results:")
    logger.info(f"  - Total archives: {stats[0]}")
    logger.info(f"  - With system_instructions: {stats[1]}")
    logger.info(f"  - With user_instructions: {stats[2]}")
    logger.info(f"  - Avg system_instructions length: {stats[3]:.0f} chars" if stats[3] else "  - Avg system_instructions length: N/A")
    logger.info(f"  - Avg user_instructions length: {stats[4]:.0f} chars" if stats[4] else "  - Avg user_instructions length: N/A")

    logger.info("=" * 80)
    logger.info("Migration 0106c completed successfully!")
    logger.info("template_archives now aligned with agent_templates dual-field structure")
    logger.info("=" * 80)


def downgrade() -> None:
    """Downgrade schema - merge system + user back to template_content.

    Rollback Steps:
    1. Merge system_instructions + user_instructions → template_content
    2. Drop new columns
    3. Remove deprecation comment from template_content
    4. Verification
    """
    logger.info("=" * 80)
    logger.info("Rolling back migration 0106c: Add Archive Dual Fields")
    logger.info("=" * 80)

    connection = op.get_bind()

    # ========================================================================
    # STEP 1: Merge Content Back to template_content
    # ========================================================================
    logger.info("STEP 1: Merging system_instructions + user_instructions → template_content...")

    # Merge with proper spacing (handle NULL system_instructions for historical archives)
    connection.execute(
        text("""
            UPDATE template_archives
            SET template_content = CASE
                WHEN system_instructions IS NOT NULL AND user_instructions IS NOT NULL
                    AND LENGTH(TRIM(user_instructions)) > 0 AND LENGTH(TRIM(system_instructions)) > 0
                THEN user_instructions || E'\\n\\n' || system_instructions
                WHEN system_instructions IS NOT NULL AND LENGTH(TRIM(system_instructions)) > 0
                THEN system_instructions
                WHEN user_instructions IS NOT NULL AND LENGTH(TRIM(user_instructions)) > 0
                THEN user_instructions
                ELSE template_content  -- Preserve original if both are NULL
            END
        """)
    )

    logger.info("Content merged back to template_content")

    # ========================================================================
    # STEP 2: Drop New Columns
    # ========================================================================
    logger.info("STEP 2: Dropping new columns...")

    op.drop_column("template_archives", "user_instructions")
    op.drop_column("template_archives", "system_instructions")

    logger.info("Columns dropped")

    # ========================================================================
    # STEP 3: Remove Deprecation Comment
    # ========================================================================
    logger.info("STEP 3: Removing deprecation comment from template_content...")

    op.alter_column(
        "template_archives",
        "template_content",
        existing_type=sa.Text(),
        comment=None,
    )

    logger.info("Deprecation comment removed")

    # ========================================================================
    # STEP 4: Verification
    # ========================================================================
    logger.info("STEP 4: Verifying rollback...")

    result = connection.execute(
        text("""
            SELECT
                COUNT(*) as total,
                AVG(LENGTH(template_content)) as avg_len
            FROM template_archives
        """)
    )
    stats = result.fetchone()

    logger.info(f"Rollback verification:")
    logger.info(f"  - Total archives: {stats[0]}")
    logger.info(f"  - Avg template_content length: {stats[1]:.0f} chars" if stats[1] else "  - Avg template_content length: N/A")

    logger.info("=" * 80)
    logger.info("Rollback completed successfully!")
    logger.info("=" * 80)
