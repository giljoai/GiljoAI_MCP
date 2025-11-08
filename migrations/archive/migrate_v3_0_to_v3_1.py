#!/usr/bin/env python3
"""
Database Migration Script: v3.0 → v3.1
Handover 0045 - Multi-Tool Agent Orchestration System

This script migrates existing GiljoAI MCP v3.0 installations to v3.1 by:
1. Adding Agent.job_id column (String(36), nullable, indexed)
2. Adding Agent.mode column (String(20), default='claude')
3. Updating agent templates with MCP coordination instructions
4. Verifying migration success

IMPORTANT: This script is IDEMPOTENT - safe to run multiple times.

Usage:
    python migrate_v3_0_to_v3_1.py                    # Interactive mode
    python migrate_v3_0_to_v3_1.py --auto-confirm     # Skip confirmation prompt
    python migrate_v3_0_to_v3_1.py --dry-run          # Show changes without applying

Prerequisites:
    - PostgreSQL 14+ running
    - .env file with DATABASE_URL configured
    - Database backup created (HIGHLY RECOMMENDED)
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Any, Dict


# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Configure UTF-8 encoding for Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# Load environment variables
from dotenv import load_dotenv


load_dotenv()

from colorama import Fore, Style, init


init(autoreset=True)


class MigrationV3_0_to_V3_1:
    """
    Database migration handler for v3.0 → v3.1 upgrade.

    Adds multi-tool orchestration support:
    - Agent.job_id field for MCP job tracking
    - Agent.mode field for tool selection (claude/codex/gemini)
    - Enhanced agent templates with MCP coordination protocol
    """

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.results: Dict[str, Any] = {}
        self.db_url = None
        self.db_manager = None

    def print_header(self, text: str):
        """Print styled header."""
        separator = "=" * 70
        print(f"\n{Fore.CYAN}{Style.BRIGHT}{separator}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{Style.BRIGHT}  {text}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{Style.BRIGHT}{separator}{Style.RESET_ALL}\n")

    def print_success(self, text: str):
        """Print success message."""
        print(f"{Fore.GREEN}✅ {text}{Style.RESET_ALL}")

    def print_error(self, text: str):
        """Print error message."""
        print(f"{Fore.RED}❌ {text}{Style.RESET_ALL}")

    def print_warning(self, text: str):
        """Print warning message."""
        print(f"{Fore.YELLOW}⚠️  {text}{Style.RESET_ALL}")

    def print_info(self, text: str):
        """Print info message."""
        print(f"{Fore.BLUE}ℹ️  {text}{Style.RESET_ALL}")

    async def verify_prerequisites(self) -> bool:
        """
        Verify migration prerequisites.

        Returns:
            True if all prerequisites met, False otherwise
        """
        self.print_header("Verifying Prerequisites")

        # Check DATABASE_URL
        self.db_url = os.getenv("DATABASE_URL")
        if not self.db_url:
            self.print_error("DATABASE_URL not found in environment")
            self.print_info("Create .env file with DATABASE_URL=postgresql://...")
            return False

        self.print_success(f"Database URL configured: {self.db_url.split('@')[0]}@...")

        # Test database connection
        try:
            from giljo_mcp.database import DatabaseManager

            self.db_manager = DatabaseManager(database_url=self.db_url, is_async=True)

            # Test connection
            async with self.db_manager.get_session_async() as session:
                from sqlalchemy import text

                await session.execute(text("SELECT 1"))

            self.print_success("Database connection successful")

        except Exception as e:
            self.print_error(f"Database connection failed: {e}")
            self.print_info("Verify PostgreSQL is running and credentials are correct")
            return False

        # Recommend backup
        self.print_warning("IMPORTANT: Database backup recommended before migration")
        self.print_info("Backup command: pg_dump -U postgres giljo_mcp > backup_v3_0.sql")

        return True

    async def check_migration_needed(self) -> bool:
        """
        Check if migration is needed (columns don't exist).

        Returns:
            True if migration needed, False if already migrated
        """
        self.print_header("Checking Migration Status")

        try:
            from sqlalchemy import text

            async with self.db_manager.async_engine.connect() as conn:
                # Check if columns exist
                result = await conn.execute(
                    text("""
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = 'agents'
                    AND column_name IN ('job_id', 'mode')
                """)
                )

                existing_columns = [row[0] for row in result.fetchall()]

            if "job_id" in existing_columns and "mode" in existing_columns:
                self.print_success("Migration already applied (columns exist)")
                self.print_info("Database is already at v3.1 schema")
                return False

            if "job_id" in existing_columns:
                self.print_warning("Partial migration detected: job_id exists, mode missing")
                return True

            if "mode" in existing_columns:
                self.print_warning("Partial migration detected: mode exists, job_id missing")
                return True

            self.print_info("Migration needed: Adding job_id and mode columns")
            return True

        except Exception as e:
            self.print_error(f"Failed to check migration status: {e}")
            return False

    async def add_agent_columns(self) -> bool:
        """
        Add job_id and mode columns to agents table.

        Returns:
            True if successful, False otherwise
        """
        self.print_header("Adding Agent Table Columns")

        if self.dry_run:
            self.print_warning("DRY RUN: Would execute the following SQL:")
            print("""
            ALTER TABLE agents ADD COLUMN IF NOT EXISTS job_id VARCHAR(36);
            ALTER TABLE agents ADD COLUMN IF NOT EXISTS mode VARCHAR(20) DEFAULT 'claude';
            CREATE INDEX IF NOT EXISTS idx_agent_job_id ON agents(job_id);
            """)
            return True

        try:
            from sqlalchemy import text

            async with self.db_manager.async_engine.begin() as conn:
                # Add job_id column
                await conn.execute(
                    text("""
                    ALTER TABLE agents
                    ADD COLUMN IF NOT EXISTS job_id VARCHAR(36)
                """)
                )
                self.print_success("Added job_id column")

                # Add mode column with default
                await conn.execute(
                    text("""
                    ALTER TABLE agents
                    ADD COLUMN IF NOT EXISTS mode VARCHAR(20) DEFAULT 'claude'
                """)
                )
                self.print_success("Added mode column")

                # Create index on job_id
                await conn.execute(
                    text("""
                    CREATE INDEX IF NOT EXISTS idx_agent_job_id
                    ON agents(job_id)
                """)
                )
                self.print_success("Created index on job_id")

            self.results["columns_added"] = True
            return True

        except Exception as e:
            self.print_error(f"Failed to add columns: {e}")
            self.results["columns_added"] = False
            return False

    async def update_agent_templates(self) -> bool:
        """
        Update existing agent templates with MCP coordination instructions.

        Returns:
            True if successful, False otherwise
        """
        self.print_header("Updating Agent Templates")

        if self.dry_run:
            self.print_warning("DRY RUN: Would append MCP coordination section to all templates")
            return True

        try:
            from sqlalchemy import select

            from giljo_mcp.models import AgentTemplate
            from giljo_mcp.template_seeder import _get_mcp_coordination_section

            mcp_section = _get_mcp_coordination_section()

            async with self.db_manager.get_session_async() as session:
                # Get all templates
                result = await session.execute(select(AgentTemplate))
                templates = result.scalars().all()

                updated_count = 0
                for template in templates:
                    # Check if MCP section already present (idempotency)
                    if "MCP COMMUNICATION PROTOCOL" not in template.template_content:
                        # Append MCP section
                        template.template_content += "\n\n" + mcp_section
                        updated_count += 1

                await session.commit()

            if updated_count > 0:
                self.print_success(f"Updated {updated_count} templates with MCP coordination")
            else:
                self.print_info("All templates already have MCP coordination section")

            self.results["templates_updated"] = updated_count
            return True

        except Exception as e:
            self.print_error(f"Failed to update templates: {e}")
            self.results["templates_updated"] = 0
            return False

    async def verify_migration(self) -> bool:
        """
        Verify migration was successful.

        Returns:
            True if verification passed, False otherwise
        """
        self.print_header("Verifying Migration")

        if self.dry_run:
            self.print_warning("DRY RUN: Skipping verification")
            return True

        try:
            from giljo_mcp.models import Agent

            # Verify columns exist
            columns = {col.name: col for col in Agent.__table__.columns}

            if "job_id" not in columns:
                self.print_error("Verification failed: job_id column missing")
                return False

            if "mode" not in columns:
                self.print_error("Verification failed: mode column missing")
                return False

            # Verify index exists
            has_job_id_index = any("job_id" in [col.name for col in idx.columns] for idx in Agent.__table__.indexes)

            if not has_job_id_index:
                self.print_error("Verification failed: index on job_id missing")
                return False

            self.print_success("Schema verification passed")

            # Test creating an agent with project
            from uuid import uuid4

            from giljo_mcp.models import Project

            test_tenant_key = f"test_{uuid4().hex[:8]}"
            test_project_id = str(uuid4())
            test_agent_id = str(uuid4())

            async with self.db_manager.get_session_async() as session:
                # Create test project (required for foreign key)
                test_project = Project(
                    id=test_project_id,
                    tenant_key=test_tenant_key,
                    name="Migration Test Project",
                    mission="Temporary project for migration verification",
                )
                session.add(test_project)
                await session.flush()

                # Create test agent
                test_agent = Agent(
                    id=test_agent_id,
                    tenant_key=test_tenant_key,
                    project_id=test_project_id,
                    name="Migration Test Agent",
                    role="tester",
                    status="active",
                    mission="Verify migration",
                )
                session.add(test_agent)
                await session.commit()

            # Retrieve to verify defaults (separate session to test database-level defaults)
            async with self.db_manager.get_session_async() as session:
                from sqlalchemy import delete, select

                result = await session.execute(select(Agent).where(Agent.id == test_agent_id))
                retrieved = result.scalar_one_or_none()

                if not retrieved:
                    self.print_error("Verification failed: Could not retrieve test agent")
                    return False

                if retrieved.mode != "claude":
                    self.print_error(f"Verification failed: mode = {retrieved.mode} (expected 'claude')")
                    return False

                # Clean up
                await session.execute(delete(Agent).where(Agent.id == test_agent_id))
                await session.execute(delete(Project).where(Project.id == test_project_id))
                await session.commit()

            self.print_success("Agent creation test passed")
            return True

        except Exception as e:
            self.print_error(f"Verification failed: {e}")
            return False

    async def run_migration(self, auto_confirm: bool = False) -> bool:
        """
        Execute complete migration workflow.

        Args:
            auto_confirm: Skip confirmation prompt if True

        Returns:
            True if migration successful, False otherwise
        """
        self.print_header("GiljoAI MCP Migration: v3.0 → v3.1")

        if self.dry_run:
            self.print_warning("DRY RUN MODE - No changes will be applied")

        # Step 1: Verify prerequisites
        if not await self.verify_prerequisites():
            return False

        # Step 2: Check if migration needed
        if not await self.check_migration_needed():
            self.print_success("Database already at v3.1 - no migration needed")
            await self.db_manager.close_async()
            return True

        # Step 3: Confirmation prompt
        if not auto_confirm and not self.dry_run:
            self.print_header("Migration Confirmation")
            self.print_warning("This will modify the database schema")
            print(f"\n{Fore.YELLOW}Changes to be applied:{Style.RESET_ALL}")
            print("  1. Add 'job_id' column to agents table")
            print("  2. Add 'mode' column to agents table (default: 'claude')")
            print("  3. Create index on job_id")
            print("  4. Update agent templates with MCP coordination")

            response = input(f"\n{Fore.CYAN}Proceed with migration? (yes/no): {Style.RESET_ALL}").strip().lower()

            if response not in ["yes", "y"]:
                self.print_warning("Migration cancelled by user")
                await self.db_manager.close_async()
                return False

        # Step 4: Add columns
        if not await self.add_agent_columns():
            await self.db_manager.close_async()
            return False

        # Step 5: Update templates
        if not await self.update_agent_templates():
            await self.db_manager.close_async()
            return False

        # Step 6: Verify migration
        if not await self.verify_migration():
            await self.db_manager.close_async()
            return False

        # Success
        self.print_header("Migration Complete")

        if not self.dry_run:
            self.print_success("Database successfully migrated to v3.1")
            self.print_info("New features available:")
            print("  • Multi-tool agent support (Claude Code, Codex, Gemini CLI)")
            print("  • MCP job coordination via Agent.job_id")
            print("  • Agent mode selection via Agent.mode")
            print("  • Enhanced templates with MCP communication protocol")

        await self.db_manager.close_async()
        return True


async def main():
    """Main migration execution."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Migrate GiljoAI MCP from v3.0 to v3.1", formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--auto-confirm", action="store_true", help="Skip confirmation prompt")
    parser.add_argument("--dry-run", action="store_true", help="Show changes without applying them")

    args = parser.parse_args()

    try:
        migration = MigrationV3_0_to_V3_1(dry_run=args.dry_run)
        success = await migration.run_migration(auto_confirm=args.auto_confirm)

        sys.exit(0 if success else 1)

    except KeyboardInterrupt:
        print(f"\n\n{Fore.YELLOW}Migration interrupted by user{Style.RESET_ALL}")
        sys.exit(130)

    except Exception as e:
        print(f"\n\n{Fore.RED}❌ FATAL ERROR: {e}{Style.RESET_ALL}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
