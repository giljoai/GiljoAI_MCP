"""
Test script to verify orchestrator_protocol field is present in MCP response.
"""
import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from giljo_mcp.database import DatabaseManager
from giljo_mcp.tools.tool_accessor import ToolAccessor


async def test_orchestrator_protocol():
    """Test that orchestrator_protocol field is present."""

    # Initialize database
    db_manager = DatabaseManager(
        database_url="postgresql+asyncpg://postgres:***@localhost:5432/giljo_mcp",
        is_async=True
    )

    async with db_manager.get_session_async() as session:
        from sqlalchemy import and_, select
        from giljo_mcp.models.agent_identity import AgentJob

        # Find an orchestrator job with a project
        result = await session.execute(
            select(AgentJob)
            .where(and_(
                AgentJob.job_type == "orchestrator",
                AgentJob.project_id.isnot(None)
            ))
            .limit(1)
        )
        orchestrator_job = result.scalar_one_or_none()

        if not orchestrator_job:
            print("[ERROR] No orchestrator jobs found in database")
            return False

        print(f"[OK] Found orchestrator job: {orchestrator_job.job_id}")
        print(f"  Tenant: {orchestrator_job.tenant_key}")
        print(f"  Project: {orchestrator_job.project_id}")

        # Create ToolAccessor and call get_orchestrator_instructions
        from giljo_mcp.tenant import TenantManager
        tenant_manager = TenantManager()
        tool_accessor = ToolAccessor(db_manager, tenant_manager)

        response = await tool_accessor.get_orchestrator_instructions(
            job_id=orchestrator_job.job_id,
            tenant_key=orchestrator_job.tenant_key
        )

        # Check for error first
        if "error" in response:
            print(f"\n[ERROR] {response.get('error')}: {response.get('message')}")
            return False

        # Check for orchestrator_protocol field
        if "orchestrator_protocol" in response:
            print("\n[SUCCESS] orchestrator_protocol field is present!")

            protocol = response["orchestrator_protocol"]
            print(f"\n  Protocol structure:")
            for key in protocol.keys():
                print(f"    - {key}")

            # Check for expected chapters
            expected_chapters = [
                "ch1_your_mission",
                "ch2_startup_sequence",
                "ch3_agent_spawning_rules",
                "ch4_error_handling",
                "ch5_reference"
            ]

            missing = [ch for ch in expected_chapters if ch not in protocol]
            if missing:
                print(f"\n[WARNING] Missing chapters: {missing}")
            else:
                print(f"\n[SUCCESS] All expected chapters present!")

            return True
        else:
            print("\n[FAILURE] orchestrator_protocol field is MISSING!")
            print(f"\nResponse keys:")
            for key in response.keys():
                print(f"  - {key}")
            return False


if __name__ == "__main__":
    result = asyncio.run(test_orchestrator_protocol())
    sys.exit(0 if result else 1)
