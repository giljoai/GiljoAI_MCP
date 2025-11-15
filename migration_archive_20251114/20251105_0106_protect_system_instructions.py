"""Protect system instructions in agent templates (Handover 0106)

Revision ID: 20251105_0106
Revises: ad108814e707
Create Date: 2025-11-05

CRITICAL SECURITY FIX: Separate system MCP coordination instructions from
user-editable content to prevent users from accidentally disabling agent
coordination.

This migration:
1. Adds system_instructions (non-editable MCP coordination rules)
2. Adds user_instructions (editable role-specific guidance)
3. Splits existing template_content into system + user sections
4. Marks template_content as deprecated (will be removed in v4.0)
5. Adds GIN trigram index for full-text search on system_instructions

Schema Changes:
- Add system_instructions column (Text, NOT NULL)
- Add user_instructions column (Text, nullable)
- Add GIN index on system_instructions for search optimization

Data Migration:
- Split template_content at "## MCP COMMUNICATION PROTOCOL" marker
- Content before marker → user_instructions
- Content after marker → system_instructions
- If no marker found → use default system instructions template

Rollback Strategy:
- Merge system_instructions + user_instructions back to template_content
- Drop new columns
- Restore original schema
"""
from collections.abc import Sequence
from typing import Union
import re
import logging

import sqlalchemy as sa
from sqlalchemy import text
from alembic import op

# Configure logging
logger = logging.getLogger(__name__)


# Revision identifiers, used by Alembic.
revision: str = "20251105_0106"
down_revision: Union[str, Sequence[str], None] = "ad108814e707"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Default system instructions template (used when no MCP marker found)
DEFAULT_SYSTEM_INSTRUCTIONS = """# GiljoAI MCP Coordination Protocol (NON-EDITABLE)

**CRITICAL**: You MUST use these MCP tools for all agent coordination.

## Job Lifecycle Management

### 1. acknowledge_job()
**Call FIRST when starting work**
```
acknowledge_job(
    job_id="{job_id}",
    agent_id="{agent_id}",
    tenant_key="{tenant_key}"
)
```
Transitions your job from `waiting` → `active`. Required to claim the job.

### 2. report_progress()
**Call every 2 minutes with status updates**
```
report_progress(
    job_id="{job_id}",
    progress={{
        "task": "Current task description",
        "percent": 50,
        "context_tokens_used": 5000
    }},
    tenant_key="{tenant_key}"
)
```
Updates job status and enables orchestrator succession at 90% context capacity.

### 3. complete_job()
**Call when work is finished**
```
complete_job(
    job_id="{job_id}",
    result={{
        "summary": "Work completed successfully",
        "artifacts": ["file1.py", "file2.py"]
    }},
    tenant_key="{tenant_key}"
)
```
Marks job as complete and notifies orchestrator.

## Agent-to-Agent Communication

### 4. send_message()
**Send messages to other agents**
```
send_message(
    to_agent="{target_agent_id}",
    message="Message content",
    priority="medium",
    tenant_key="{tenant_key}"
)
```
Coordinate with orchestrator or peer agents.

### 5. receive_messages()
**Check for incoming messages**
```
receive_messages(
    agent_id="{agent_id}",
    limit=10,
    tenant_key="{tenant_key}"
)
```
Check every 5 minutes for coordination messages.

## Error Handling

### 6. report_error()
**Report errors or blockers immediately**
```
report_error(
    job_id="{job_id}",
    error="Error description",
    tenant_key="{tenant_key}"
)
```
Set job status to "blocked" and wait for orchestrator guidance.

## Progress Reporting Rules

**MANDATORY REQUIREMENTS**:
- Report progress every 2 minutes
- Include context token estimate
- Include percentage complete (0-100)
- Describe current task in detail

**Context tracking enables**:
- Orchestrator succession at 90% capacity
- Seamless handover between instances
- 70% token reduction optimization

## Role Adherence

**Your assigned role**: `{agent_type}`

**Critical rules**:
- Stay within your role boundaries
- Do NOT perform tasks outside your role
- Coordinate via send_message() for cross-role tasks
- Always defer to orchestrator for mission coordination

## Your Runtime Identity
These values are injected at job spawn time:
- Agent ID: `{agent_id}`
- Tenant Key: `{tenant_key}`
- Job ID: `{job_id}`
- Agent Type: `{agent_type}`

**NEVER hardcode these values** - they are provided dynamically.

---

**End of System Instructions** (Non-Editable)
"""


def _get_default_system_instructions() -> str:
    """Get default system instructions for templates without MCP marker.

    Returns:
        str: Default system instructions template with all required MCP tools
    """
    return DEFAULT_SYSTEM_INSTRUCTIONS.strip()


def _split_template_content(content: str) -> tuple[str, str]:
    """Split template content into user instructions and system instructions.

    Splits at the first occurrence of MCP marker (case-insensitive):
    - "## MCP COMMUNICATION PROTOCOL"
    - "## MCP Communication Protocol"
    - "##MCP COMMUNICATION PROTOCOL" (no space)

    Args:
        content: Original template_content from database

    Returns:
        tuple[str, str]: (user_instructions, system_instructions)
            - user_instructions: Content before marker (role-specific guidance)
            - system_instructions: Content after marker (MCP coordination)
            - If no marker found: ("", default_system_instructions)
    """
    if not content or len(content.strip()) == 0:
        return ("", _get_default_system_instructions())

    # Regex pattern for MCP marker (case-insensitive, optional spacing)
    # Matches: "## MCP COMMUNICATION PROTOCOL", "##MCP Communication Protocol", etc.
    mcp_pattern = r"##\s*MCP\s+COMMUNICATION\s+PROTOCOL"

    match = re.search(mcp_pattern, content, re.IGNORECASE)

    if match:
        # Split at the marker
        split_index = match.start()
        user_instructions = content[:split_index].strip()
        system_instructions = content[split_index:].strip()

        logger.info(f"Split template: user={len(user_instructions)} chars, system={len(system_instructions)} chars")
        return (user_instructions, system_instructions)
    else:
        # No marker found - use entire content as user_instructions
        # and apply default system instructions
        logger.warning(f"No MCP marker found in template - using default system instructions")
        return (content.strip(), _get_default_system_instructions())


def upgrade() -> None:
    """Upgrade schema - add system_instructions and user_instructions columns.

    Migration Steps:
    1. Analyze current state (log template counts)
    2. Add new columns (nullable initially)
    3. Migrate data (split template_content)
    4. Make system_instructions non-nullable
    5. Add GIN trigram index for full-text search
    6. Mark template_content as deprecated
    7. Verification (log completion stats)
    """
    logger.info("=" * 80)
    logger.info("Starting migration 0106: Protect System Instructions")
    logger.info("=" * 80)

    # Get database connection
    connection = op.get_bind()

    # ========================================================================
    # STEP 1: Analyze Current State
    # ========================================================================
    logger.info("STEP 1: Analyzing current state...")

    result = connection.execute(text("SELECT COUNT(*) FROM agent_templates"))
    total_templates = result.scalar()
    logger.info(f"Found {total_templates} templates to migrate")

    # ========================================================================
    # STEP 2: Add New Columns (nullable initially for data migration)
    # ========================================================================
    logger.info("STEP 2: Adding new columns...")

    op.add_column(
        "agent_templates",
        sa.Column(
            "system_instructions",
            sa.Text(),
            nullable=True,  # Nullable initially, will be made NOT NULL after migration
            comment="Protected MCP coordination rules (non-editable by users)",
        ),
    )

    op.add_column(
        "agent_templates",
        sa.Column(
            "user_instructions",
            sa.Text(),
            nullable=True,
            comment="User-customizable role-specific guidance (editable)",
        ),
    )

    logger.info("Columns added successfully")

    # ========================================================================
    # STEP 3: Migrate Data (split template_content)
    # ========================================================================
    logger.info("STEP 3: Migrating data - splitting template_content...")

    # Fetch all templates
    templates_result = connection.execute(
        text("SELECT id, template_content FROM agent_templates ORDER BY id")
    )
    templates = templates_result.fetchall()

    migrated_count = 0
    with_marker_count = 0
    without_marker_count = 0

    for template_id, template_content in templates:
        # Split content
        user_instructions, system_instructions = _split_template_content(template_content or "")

        # Track marker detection
        if "## MCP COMMUNICATION PROTOCOL" in (template_content or "").upper():
            with_marker_count += 1
        else:
            without_marker_count += 1

        # Update template with split content
        connection.execute(
            text("""
                UPDATE agent_templates
                SET system_instructions = :sys_inst,
                    user_instructions = :user_inst
                WHERE id = :template_id
            """),
            {
                "sys_inst": system_instructions,
                "user_inst": user_instructions if len(user_instructions) > 0 else None,
                "template_id": template_id,
            },
        )

        migrated_count += 1

        if migrated_count % 100 == 0:
            logger.info(f"Migrated {migrated_count}/{total_templates} templates...")

    logger.info(f"Data migration complete:")
    logger.info(f"  - Total migrated: {migrated_count}")
    logger.info(f"  - With MCP marker: {with_marker_count}")
    logger.info(f"  - Without marker (default applied): {without_marker_count}")

    # ========================================================================
    # STEP 4: Make system_instructions Non-Nullable
    # ========================================================================
    logger.info("STEP 4: Making system_instructions NOT NULL...")

    # Verify no NULL values remain
    null_check = connection.execute(
        text("SELECT COUNT(*) FROM agent_templates WHERE system_instructions IS NULL")
    )
    null_count = null_check.scalar()

    if null_count > 0:
        raise ValueError(
            f"Cannot make system_instructions NOT NULL - {null_count} templates have NULL values. "
            "Data migration may have failed."
        )

    # Make column non-nullable
    op.alter_column(
        "agent_templates",
        "system_instructions",
        existing_type=sa.Text(),
        nullable=False,
    )

    logger.info("system_instructions is now NOT NULL")

    # ========================================================================
    # STEP 5: Add GIN Trigram Index for Full-Text Search
    # ========================================================================
    logger.info("STEP 5: Adding GIN trigram index...")

    # Create pg_trgm extension if not exists (idempotent)
    connection.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))

    # Create GIN index for fast full-text search
    op.create_index(
        "idx_agent_templates_system_instructions_gin",
        "agent_templates",
        ["system_instructions"],
        unique=False,
        postgresql_using="gin",
        postgresql_ops={"system_instructions": "gin_trgm_ops"},
    )

    logger.info("GIN trigram index created")

    # ========================================================================
    # STEP 6: Mark template_content as Deprecated
    # ========================================================================
    logger.info("STEP 6: Marking template_content as deprecated...")

    # Update column comment to indicate deprecation
    op.alter_column(
        "agent_templates",
        "template_content",
        existing_type=sa.Text(),
        comment="DEPRECATED (v3.1): Use system_instructions + user_instructions instead. Will be removed in v4.0.",
    )

    logger.info("template_content marked as deprecated")

    # ========================================================================
    # STEP 7: Verification
    # ========================================================================
    logger.info("STEP 7: Verifying migration...")

    # Verify all templates have system_instructions
    verification_result = connection.execute(
        text("""
            SELECT
                COUNT(*) as total,
                COUNT(system_instructions) as with_system,
                COUNT(user_instructions) as with_user,
                AVG(LENGTH(system_instructions)) as avg_system_len,
                AVG(LENGTH(user_instructions)) as avg_user_len
            FROM agent_templates
        """)
    )
    stats = verification_result.fetchone()

    logger.info(f"Verification results:")
    logger.info(f"  - Total templates: {stats[0]}")
    logger.info(f"  - With system_instructions: {stats[1]}")
    logger.info(f"  - With user_instructions: {stats[2]}")
    logger.info(f"  - Avg system_instructions length: {stats[3]:.0f} chars")
    logger.info(f"  - Avg user_instructions length: {stats[4]:.0f} chars" if stats[4] else "  - Avg user_instructions length: N/A")

    # Verify required MCP tools present in all templates
    tool_check = connection.execute(
        text("""
            SELECT COUNT(*) FROM agent_templates
            WHERE system_instructions NOT LIKE '%acknowledge_job%'
               OR system_instructions NOT LIKE '%report_progress%'
               OR system_instructions NOT LIKE '%complete_job%'
        """)
    )
    missing_tools_count = tool_check.scalar()

    if missing_tools_count > 0:
        logger.warning(
            f"WARNING: {missing_tools_count} templates missing required MCP tools in system_instructions. "
            "This may indicate data migration issues."
        )
    else:
        logger.info(f"All templates contain required MCP tools ✓")

    logger.info("=" * 80)
    logger.info("Migration 0106 completed successfully!")
    logger.info("=" * 80)


def downgrade() -> None:
    """Downgrade schema - merge system + user back to template_content.

    Rollback Steps:
    1. Merge system_instructions + user_instructions → template_content
    2. Drop GIN index
    3. Drop new columns
    4. Remove deprecation comment from template_content
    5. Verification
    """
    logger.info("=" * 80)
    logger.info("Rolling back migration 0106: Protect System Instructions")
    logger.info("=" * 80)

    connection = op.get_bind()

    # ========================================================================
    # STEP 1: Merge Content Back to template_content
    # ========================================================================
    logger.info("STEP 1: Merging system_instructions + user_instructions → template_content...")

    # Merge with proper spacing
    connection.execute(
        text("""
            UPDATE agent_templates
            SET template_content = CASE
                WHEN user_instructions IS NOT NULL AND LENGTH(TRIM(user_instructions)) > 0
                THEN user_instructions || E'\\n\\n' || system_instructions
                ELSE system_instructions
            END
        """)
    )

    logger.info("Content merged back to template_content")

    # ========================================================================
    # STEP 2: Drop GIN Index
    # ========================================================================
    logger.info("STEP 2: Dropping GIN index...")

    op.drop_index("idx_agent_templates_system_instructions_gin", table_name="agent_templates")

    logger.info("GIN index dropped")

    # ========================================================================
    # STEP 3: Drop New Columns
    # ========================================================================
    logger.info("STEP 3: Dropping new columns...")

    op.drop_column("agent_templates", "user_instructions")
    op.drop_column("agent_templates", "system_instructions")

    logger.info("Columns dropped")

    # ========================================================================
    # STEP 4: Remove Deprecation Comment
    # ========================================================================
    logger.info("STEP 4: Removing deprecation comment from template_content...")

    op.alter_column(
        "agent_templates",
        "template_content",
        existing_type=sa.Text(),
        comment=None,
    )

    logger.info("Deprecation comment removed")

    # ========================================================================
    # STEP 5: Verification
    # ========================================================================
    logger.info("STEP 5: Verifying rollback...")

    result = connection.execute(
        text("""
            SELECT
                COUNT(*) as total,
                AVG(LENGTH(template_content)) as avg_len
            FROM agent_templates
        """)
    )
    stats = result.fetchone()

    logger.info(f"Rollback verification:")
    logger.info(f"  - Total templates: {stats[0]}")
    logger.info(f"  - Avg template_content length: {stats[1]:.0f} chars")

    logger.info("=" * 80)
    logger.info("Rollback completed successfully!")
    logger.info("=" * 80)
