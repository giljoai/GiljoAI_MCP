#!/usr/bin/env python3
"""
DEPRECATED (Handover 0387h): This script is no longer needed.
The JSONB messages array has been replaced with counter columns.
Scheduled for removal in next major release.

Original Purpose: JSONB Message Repair Script

Background:
-----------
A bug in the broadcast message handling stored incorrect message_ids in the
AgentExecution.messages JSONB array. When broadcasting to multiple agents,
all recipients received the same message_id instead of their unique message_id.

This caused message counter mismatches and acknowledgment failures because:
1. Frontend displays messages from JSONB (agent_executions.messages)
2. Acknowledgment updates the Message table by message_id
3. Wrong message_id = acknowledgment updates the wrong row

This script repairs existing data by:
1. Clearing all existing JSONB message arrays
2. Rebuilding them from the Message table (source of truth)
3. Preserving correct message_id to agent relationships
4. Updating status based on Message.status (pending vs acknowledged)

Usage:
------
    python scripts/repair_jsonb_messages.py [--dry-run] [--tenant-key TENANT_KEY]

Options:
    --dry-run           Preview changes without modifying the database
    --tenant-key        Repair only specific tenant (default: all tenants)
    --verbose           Show detailed progress information

Safety:
-------
- Runs in a transaction (atomic - all or nothing)
- Dry-run mode available for preview
- Preserves Message table data (read-only source)
- Can be run multiple times safely (idempotent)

Author: Claude Code (Implementation Specialist)
Date: 2026-01-05
"""

import argparse
import asyncio
import sys
from pathlib import Path
from datetime import datetime, timezone

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.attributes import flag_modified

from src.giljo_mcp.models.tasks import Message
from src.giljo_mcp.models.agent_identity import AgentJob, AgentExecution
from src.giljo_mcp.config_manager import ConfigManager


class MessageRepairStats:
    """Track repair statistics"""

    def __init__(self):
        self.agents_processed = 0
        self.agents_cleared = 0
        self.messages_rebuilt = 0
        self.errors = 0
        self.start_time = datetime.now()

    def report(self):
        """Print final statistics"""
        duration = (datetime.now() - self.start_time).total_seconds()
        print("\n" + "=" * 60)
        print("REPAIR SUMMARY")
        print("=" * 60)
        print(f"Agents Processed:      {self.agents_processed}")
        print(f"Agents Cleared:        {self.agents_cleared}")
        print(f"Messages Rebuilt:      {self.messages_rebuilt}")
        print(f"Errors:                {self.errors}")
        print(f"Duration:              {duration:.2f}s")
        print("=" * 60)


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


async def clear_all_jsonb_messages(
    session: AsyncSession,
    tenant_key: str = None,
    verbose: bool = False
) -> int:
    """
    Clear all JSONB message arrays in agent_executions table.

    Args:
        session: Active database session
        tenant_key: Optional tenant filter (None = all tenants)
        verbose: Show detailed progress

    Returns:
        Number of agents cleared
    """
    # Build query with optional tenant filter
    query = select(AgentExecution)
    if tenant_key:
        query = query.where(AgentExecution.tenant_key == tenant_key)

    result = await session.execute(query)
    agents = result.scalars().all()

    cleared_count = 0
    for agent in agents:
        if agent.messages:  # Only clear if not empty
            agent.messages = []
            flag_modified(agent, "messages")
            cleared_count += 1

            if verbose:
                print(f"  Cleared {agent.agent_type} ({agent.agent_id})")

    return cleared_count


async def rebuild_agent_messages_from_table(
    session: AsyncSession,
    tenant_key: str = None,
    verbose: bool = False
) -> int:
    """
    Rebuild all JSONB message arrays from the Message table.

    This is the core repair logic that:
    1. Queries all messages from Message table
    2. Groups them by sender/recipient
    3. Rebuilds JSONB arrays with correct message_ids and status

    Args:
        session: Active database session
        tenant_key: Optional tenant filter (None = all tenants)
        verbose: Show detailed progress

    Returns:
        Number of messages rebuilt
    """
    # Query all messages with optional tenant filter
    query = select(Message).order_by(Message.created_at)
    if tenant_key:
        query = query.where(Message.tenant_key == tenant_key)

    result = await session.execute(query)
    messages = result.scalars().all()

    if verbose:
        print(f"\nProcessing {len(messages)} messages from Message table...")

    messages_rebuilt = 0

    for message in messages:
        try:
            # Get project_id and metadata
            project_id = message.project_id
            from_agent = message.meta_data.get("_from_agent", "orchestrator") if message.meta_data else "orchestrator"
            content = message.content
            priority = message.priority
            timestamp = message.created_at.isoformat() if message.created_at else datetime.now(timezone.utc).isoformat()

            # Determine message status for JSONB
            # Message.status: "pending" -> "waiting" in JSONB
            # Message.status: "acknowledged" -> "read" in JSONB
            jsonb_status = "read" if message.status == "acknowledged" else "waiting"

            # Process SENDER (outbound message)
            sender_result = await session.execute(
                select(AgentExecution).join(AgentJob).where(
                    and_(
                        AgentExecution.tenant_key == message.tenant_key,
                        AgentJob.project_id == project_id,
                        or_(
                            AgentExecution.agent_id == from_agent,
                            AgentExecution.agent_type == from_agent
                        )
                    )
                ).limit(1)
            )
            sender_agent = sender_result.scalar_one_or_none()

            if sender_agent:
                if not sender_agent.messages:
                    sender_agent.messages = []

                # Add outbound message
                sender_agent.messages.append({
                    "id": str(message.id),
                    "from": from_agent,
                    "direction": "outbound",
                    "status": "sent",
                    "text": content[:200],  # Truncate for storage
                    "priority": priority,
                    "timestamp": timestamp,
                    "to_agents": message.to_agents,
                })

                flag_modified(sender_agent, "messages")
                messages_rebuilt += 1

                if verbose:
                    print(f"  Added outbound message {message.id} to {sender_agent.agent_type}")

            # Process RECIPIENTS (inbound messages)
            # message.to_agents contains agent_ids (UUIDs)
            for recipient_agent_id in (message.to_agents or []):
                # Skip sender - don't add inbound message to sender
                if sender_agent and recipient_agent_id == sender_agent.agent_id:
                    continue

                # Look up recipient agent execution
                recipient_result = await session.execute(
                    select(AgentExecution).join(AgentJob).where(
                        and_(
                            AgentExecution.tenant_key == message.tenant_key,
                            AgentJob.project_id == project_id,
                            AgentExecution.agent_id == recipient_agent_id
                        )
                    )
                )
                recipient_agent = recipient_result.scalar_one_or_none()

                if recipient_agent:
                    if not recipient_agent.messages:
                        recipient_agent.messages = []

                    # Add inbound message with correct message_id and status
                    recipient_agent.messages.append({
                        "id": str(message.id),  # CORRECT message_id for this recipient
                        "from": from_agent,
                        "direction": "inbound",
                        "status": jsonb_status,  # "waiting" or "read"
                        "text": content[:200],  # Truncate for storage
                        "priority": priority,
                        "timestamp": timestamp,
                    })

                    flag_modified(recipient_agent, "messages")
                    messages_rebuilt += 1

                    if verbose:
                        print(f"  Added inbound message {message.id} to {recipient_agent.agent_type} (status: {jsonb_status})")

        except Exception as e:
            print(f"ERROR processing message {message.id}: {e}")
            raise  # Re-raise to trigger rollback

    return messages_rebuilt


async def repair_jsonb_messages(
    dry_run: bool = False,
    tenant_key: str = None,
    verbose: bool = False
):
    """
    Main repair function.

    Args:
        dry_run: If True, preview changes without committing
        tenant_key: Optional tenant filter (None = all tenants)
        verbose: Show detailed progress
    """
    stats = MessageRepairStats()

    print("\n" + "=" * 60)
    print("JSONB MESSAGE REPAIR SCRIPT")
    print("=" * 60)
    print(f"Mode:        {'DRY RUN (no changes)' if dry_run else 'LIVE (will modify database)'}")
    print(f"Tenant:      {tenant_key or 'ALL TENANTS'}")
    print(f"Verbose:     {verbose}")
    print("=" * 60 + "\n")

    if not dry_run:
        confirm = input("This will modify the database. Continue? [y/N]: ")
        if confirm.lower() != 'y':
            print("Aborted.")
            return

    session = await get_async_session()

    try:
        # Step 1: Count agents before clearing
        query = select(func.count(AgentExecution.agent_id))
        if tenant_key:
            query = query.where(AgentExecution.tenant_key == tenant_key)

        result = await session.execute(query)
        stats.agents_processed = result.scalar_one()

        print(f"\n[1/3] Found {stats.agents_processed} agent executions to process")

        # Step 2: Clear all JSONB message arrays
        print("\n[2/3] Clearing existing JSONB message arrays...")
        stats.agents_cleared = await clear_all_jsonb_messages(session, tenant_key, verbose)
        print(f"      Cleared {stats.agents_cleared} agents")

        # Step 3: Rebuild from Message table
        print("\n[3/3] Rebuilding JSONB arrays from Message table...")
        stats.messages_rebuilt = await rebuild_agent_messages_from_table(session, tenant_key, verbose)
        print(f"      Rebuilt {stats.messages_rebuilt} message entries")

        # Commit or rollback
        if dry_run:
            print("\n[DRY RUN] Rolling back changes (no modifications made)")
            await session.rollback()
        else:
            print("\n[LIVE] Committing changes to database...")
            await session.commit()
            print("[LIVE] Changes committed successfully!")

    except Exception as e:
        print(f"\nERROR: {e}")
        stats.errors += 1
        await session.rollback()
        raise

    finally:
        await session.close()

    # Print final statistics
    stats.report()


def main():
    """Command-line entry point"""
    parser = argparse.ArgumentParser(
        description="Repair JSONB message arrays in agent_executions table",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Preview changes without modifying database
  python scripts/repair_jsonb_messages.py --dry-run

  # Repair all tenants (live mode)
  python scripts/repair_jsonb_messages.py

  # Repair specific tenant only
  python scripts/repair_jsonb_messages.py --tenant-key tk_abc123...

  # Verbose output with dry-run
  python scripts/repair_jsonb_messages.py --dry-run --verbose
        """
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without modifying the database"
    )

    parser.add_argument(
        "--tenant-key",
        type=str,
        help="Repair only specific tenant (default: all tenants)"
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed progress information"
    )

    args = parser.parse_args()

    # Run async repair function
    asyncio.run(repair_jsonb_messages(
        dry_run=args.dry_run,
        tenant_key=args.tenant_key,
        verbose=args.verbose
    ))


if __name__ == "__main__":
    main()
