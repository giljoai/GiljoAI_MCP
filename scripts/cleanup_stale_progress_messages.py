#!/usr/bin/env python3
"""
Cleanup Script for Stale Progress Messages (Handover 0289)

This script migrates progress messages from the messages table to the
agent_executions.progress field where they belong.

Progress updates should NOT create message records. They should update:
- agent_executions.progress (integer 0-100)
- agent_executions.current_task (string)

Usage:
    python scripts/cleanup_stale_progress_messages.py [--dry-run]

Options:
    --dry-run    Preview changes without modifying the database
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.giljo_mcp.models import Message
from src.giljo_mcp.models.agent_identity import AgentJob, AgentExecution
from src.giljo_mcp.config_manager import ConfigManager


async def get_async_session() -> AsyncSession:
    """Create async database session"""
    config = ConfigManager()
    db_url = config.get_database_url()

    # Convert to async URL if needed
    if "asyncpg" not in db_url:
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://")

    engine = create_async_engine(db_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return async_session()


def extract_progress_from_content(content: str) -> tuple[int, str]:
    """
    Extract progress percentage and current_task from message content.

    Progress messages are typically JSON like:
    {"percentage": 25, "current_task": "Creating backend folder structure", "message": "..."}

    Returns:
        (progress_percentage, current_task)
    """
    try:
        data = json.loads(content)
        percentage = data.get("percentage", 0)
        current_task = data.get("current_task", data.get("message", ""))
        return (int(percentage), str(current_task))
    except (json.JSONDecodeError, TypeError, ValueError):
        # Not JSON, try to extract from plain text
        return (0, str(content)[:255] if content else "")


async def find_agent_job_for_message(
    session: AsyncSession,
    message: Message
) -> AgentExecution | None:
    """
    Find the agent execution that should receive this progress update.

    Uses message metadata or searches by tenant/project.
    Returns the AgentExecution instance (not AgentJob).
    """
    # Check if job_id is in metadata
    job_id = message.meta_data.get("job_id") if message.meta_data else None

    if job_id:
        result = await session.execute(
            select(AgentExecution).where(
                AgentExecution.job_id == job_id,
                AgentExecution.tenant_key == message.tenant_key
            )
        )
        return result.scalar_one_or_none()

    # Try to find by from_agent in metadata
    from_agent = message.meta_data.get("_from_agent") if message.meta_data else None

    if from_agent and message.project_id:
        result = await session.execute(
            select(AgentExecution).join(
                AgentJob, AgentExecution.job_id == AgentJob.job_id
            ).where(
                AgentExecution.agent_display_name == from_agent,
                AgentJob.project_id == message.project_id,
                AgentExecution.tenant_key == message.tenant_key
            ).order_by(AgentExecution.started_at.desc()).limit(1)
        )
        return result.scalar_one_or_none()

    return None


async def cleanup_progress_messages(dry_run: bool = False) -> dict:
    """
    Main cleanup function.

    1. Find all progress messages in messages table
    2. Extract progress data
    3. Update corresponding agent executions
    4. Delete progress messages

    Returns:
        Statistics about the cleanup
    """
    stats = {
        "found": 0,
        "migrated": 0,
        "deleted": 0,
        "orphaned": 0,  # Progress messages without matching agent execution
        "errors": []
    }

    async with await get_async_session() as session:
        # Find all progress messages
        result = await session.execute(
            select(Message).where(Message.message_type == "progress")
        )
        progress_messages = result.scalars().all()
        stats["found"] = len(progress_messages)

        print(f"\nFound {stats['found']} progress messages to process")

        for message in progress_messages:
            try:
                print(f"\nProcessing message {message.id}:")
                print(f"  Tenant: {message.tenant_key}")
                print(f"  Project: {message.project_id}")
                print(f"  Content: {message.content[:100]}...")

                # Extract progress data
                percentage, current_task = extract_progress_from_content(message.content)
                print(f"  Extracted: {percentage}% - {current_task[:50]}...")

                # Find corresponding agent execution
                agent_execution = await find_agent_job_for_message(session, message)

                if agent_execution:
                    print(f"  Found agent execution: {agent_execution.job_id} ({agent_execution.agent_display_name})")

                    if not dry_run:
                        # Update agent execution with progress
                        agent_execution.progress = percentage
                        agent_execution.current_task = current_task[:255]

                        # Delete the progress message
                        await session.delete(message)
                        await session.commit()

                    stats["migrated"] += 1
                    stats["deleted"] += 1
                    print(f"  {'Would migrate' if dry_run else 'Migrated'} to agent execution")
                else:
                    print(f"  WARNING: No matching agent execution found (orphaned)")
                    stats["orphaned"] += 1

                    if not dry_run:
                        # Delete orphaned progress message
                        await session.delete(message)
                        await session.commit()
                        stats["deleted"] += 1
                        print(f"  Deleted orphaned message")
                    else:
                        print(f"  Would delete orphaned message")

            except Exception as e:
                error_msg = f"Error processing message {message.id}: {str(e)}"
                print(f"  ERROR: {error_msg}")
                stats["errors"].append(error_msg)

        print(f"\n{'DRY RUN - ' if dry_run else ''}Cleanup Summary:")
        print(f"  Found: {stats['found']} progress messages")
        print(f"  Migrated: {stats['migrated']}")
        print(f"  Deleted: {stats['deleted']}")
        print(f"  Orphaned: {stats['orphaned']}")
        if stats["errors"]:
            print(f"  Errors: {len(stats['errors'])}")
            for error in stats["errors"]:
                print(f"    - {error}")

    return stats


def main():
    parser = argparse.ArgumentParser(
        description="Cleanup stale progress messages from messages table"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without modifying database"
    )
    args = parser.parse_args()

    print("=" * 60)
    print("Progress Message Cleanup Script (Handover 0289)")
    print("=" * 60)

    if args.dry_run:
        print("\n*** DRY RUN MODE - No changes will be made ***\n")
    else:
        print("\n*** LIVE MODE - Database will be modified ***")
        response = input("Continue? [y/N]: ")
        if response.lower() != 'y':
            print("Aborted.")
            sys.exit(0)

    stats = asyncio.run(cleanup_progress_messages(dry_run=args.dry_run))

    print("\n" + "=" * 60)
    if args.dry_run:
        print("DRY RUN complete. Run without --dry-run to apply changes.")
    else:
        print("Cleanup complete.")
    print("=" * 60)

    # Exit with error if there were issues
    if stats["errors"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
