"""
Re-chunk existing vision documents that exceed 20K tokens.

Handover 0347: Restore chunking removed in 0246b (Claude Code 25K limit)

Usage:
    python scripts/rechunk_vision_document.py [--document-id UUID]

If no document-id provided, re-chunks ALL documents >20K tokens without chunks.
"""

import asyncio
import argparse
import sys
from pathlib import Path

import yaml

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import select
from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.models import VisionDocument
from src.giljo_mcp.context_management.chunker import VisionDocumentChunker


def load_config():
    """Load config.yaml from project root."""
    config_path = project_root / "config.yaml"
    if not config_path.exists():
        raise FileNotFoundError(f"config.yaml not found at {config_path}")
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


async def rechunk_document(db_manager: DatabaseManager, document_id: str = None):
    """Re-chunk vision documents exceeding 20K tokens."""

    async with db_manager.get_session_async() as session:
        # Build query
        stmt = select(VisionDocument).where(
            VisionDocument.is_active == True
        )

        if document_id:
            stmt = stmt.where(VisionDocument.id == document_id)
        else:
            # Find documents >20K tokens without chunks
            stmt = stmt.where(
                VisionDocument.original_token_count > 20000,
                (VisionDocument.chunk_count == 0) | (VisionDocument.chunk_count == None)
            )

        result = await session.execute(stmt)
        documents = result.scalars().all()

        if not documents:
            print("No documents found matching criteria.")
            return

        print(f"Found {len(documents)} document(s) to re-chunk:")
        for doc in documents:
            print(f"  - {doc.id}: {doc.document_name or 'Unnamed'} ({doc.original_token_count or 0:,} tokens)")

        chunker = VisionDocumentChunker(target_chunk_size=20000)

        for doc in documents:
            print(f"\nProcessing: {doc.id}")
            try:
                chunk_result = await chunker.chunk_vision_document(
                    session=session,
                    tenant_key=doc.tenant_key,
                    vision_document_id=str(doc.id)
                )

                if chunk_result.get("success"):
                    print(f"  SUCCESS: Created {chunk_result.get('chunks_created', 0)} chunks")
                else:
                    print(f"  FAILED: {chunk_result.get('error', 'Unknown error')}")

            except Exception as e:
                print(f"  ERROR: {e}")

        # Commit all changes
        await session.commit()
        print("\nAll changes committed.")


async def main():
    parser = argparse.ArgumentParser(description="Re-chunk vision documents")
    parser.add_argument(
        "--document-id",
        help="Specific document UUID to re-chunk (optional)"
    )
    args = parser.parse_args()

    # Load .env file
    from dotenv import load_dotenv
    import os
    load_dotenv(project_root / ".env")

    # Get DATABASE_URL from environment
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("ERROR: DATABASE_URL not found in .env")
        sys.exit(1)

    # Convert to async URL if needed
    if "postgresql://" in db_url and "asyncpg" not in db_url:
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://")

    print(f"Connecting to database...")

    db_manager = DatabaseManager(database_url=db_url, is_async=True)

    try:
        await rechunk_document(db_manager, args.document_id)
    finally:
        await db_manager.close_async()


if __name__ == "__main__":
    asyncio.run(main())
