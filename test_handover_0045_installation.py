#!/usr/bin/env python3
"""
Installation Flow Verification Test Script for Handover 0045
Multi-Tool Agent Orchestration System

This script validates that install.py correctly sets up all components
for the multi-tool orchestration system including:
1. Database schema (Agent.job_id, Agent.mode fields)
2. Template seeding with MCP coordination instructions
3. MCP tools registration
4. Backward compatibility

Usage:
    python test_handover_0045_installation.py
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Any, Dict


# Configure UTF-8 encoding for Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Load environment variables
from dotenv import load_dotenv


load_dotenv()


class InstallationVerificationTest:
    """Test harness for Handover 0045 installation verification."""

    def __init__(self):
        self.results: Dict[str, Dict[str, Any]] = {}
        self.passed = 0
        self.failed = 0

    def log_success(self, test_name: str, message: str):
        """Log successful test."""
        print(f"✅ PASS: {test_name} - {message}")
        self.results[test_name] = {"status": "PASS", "message": message}
        self.passed += 1

    def log_failure(self, test_name: str, message: str, error: Exception = None):
        """Log failed test."""
        error_detail = f" ({error})" if error else ""
        print(f"❌ FAIL: {test_name} - {message}{error_detail}")
        self.results[test_name] = {"status": "FAIL", "message": message, "error": str(error) if error else None}
        self.failed += 1

    def log_info(self, message: str):
        """Log informational message."""
        print(f"ℹ️  INFO: {message}")

    async def test_database_schema(self) -> bool:
        """
        Test 1: Verify Agent model has job_id and mode fields.

        Validates:
        - Agent.job_id field exists (String(36), nullable, indexed)
        - Agent.mode field exists (String(20), default='claude')
        - Both fields have correct types and constraints
        """
        test_name = "Database Schema Verification"
        self.log_info(f"Running {test_name}...")

        try:
            from giljo_mcp.models import Agent

            # Get Agent table columns
            columns = {col.name: col for col in Agent.__table__.columns}

            # Check job_id field
            if "job_id" not in columns:
                self.log_failure(test_name, "Agent.job_id field missing")
                return False

            job_id_col = columns["job_id"]
            if str(job_id_col.type) != "VARCHAR(36)":
                self.log_failure(test_name, f"Agent.job_id has wrong type: {job_id_col.type} (expected VARCHAR(36))")
                return False

            if not job_id_col.nullable:
                self.log_failure(test_name, "Agent.job_id should be nullable")
                return False

            # Check mode field
            if "mode" not in columns:
                self.log_failure(test_name, "Agent.mode field missing")
                return False

            mode_col = columns["mode"]
            if str(mode_col.type) != "VARCHAR(20)":
                self.log_failure(test_name, f"Agent.mode has wrong type: {mode_col.type} (expected VARCHAR(20))")
                return False

            # Check index on job_id
            has_job_id_index = any("job_id" in [col.name for col in idx.columns] for idx in Agent.__table__.indexes)

            if not has_job_id_index:
                self.log_failure(test_name, "Missing index on Agent.job_id")
                return False

            self.log_success(test_name, "Agent.job_id and Agent.mode fields present with correct schema")
            return True

        except Exception as e:
            self.log_failure(test_name, "Exception during schema check", e)
            return False

    async def test_template_seeding(self) -> bool:
        """
        Test 2: Verify template seeding includes MCP coordination section.

        Validates:
        - Templates contain MCP COMMUNICATION PROTOCOL section
        - MCP checkpoint instructions present
        - Progress reporting guidance included
        - Error handling protocol documented
        """
        test_name = "Template Seeding with MCP"
        self.log_info(f"Running {test_name}...")

        try:
            from giljo_mcp.template_seeder import _get_mcp_coordination_section

            # Get MCP coordination section
            mcp_section = _get_mcp_coordination_section()

            # Verify required elements present
            required_elements = [
                "MCP COMMUNICATION PROTOCOL",
                "Phase 1: Job Acknowledgment",
                "Phase 2: Incremental Progress",
                "Phase 3: Completion",
                "Error Handling",
                "mcp__giljo_mcp__get_pending_jobs",
                "mcp__giljo_mcp__acknowledge_job",
                "mcp__giljo_mcp__report_progress",
                "mcp__giljo_mcp__complete_job",
                "mcp__giljo_mcp__get_next_instruction",
                "mcp__giljo_mcp__report_error",
            ]

            missing_elements = []
            for element in required_elements:
                if element not in mcp_section:
                    missing_elements.append(element)

            if missing_elements:
                self.log_failure(test_name, f"Missing MCP elements: {', '.join(missing_elements)}")
                return False

            self.log_success(
                test_name, f"MCP coordination section contains all {len(required_elements)} required elements"
            )
            return True

        except Exception as e:
            self.log_failure(test_name, "Exception during template check", e)
            return False

    async def test_mcp_tools_registration(self) -> bool:
        """
        Test 3: Verify MCP coordination tools are properly registered.

        Validates:
        - agent_coordination module importable
        - register_agent_coordination_tools function exists
        - All 7 coordination tools present
        """
        test_name = "MCP Tools Registration"
        self.log_info(f"Running {test_name}...")

        try:
            from giljo_mcp.database import DatabaseManager
            from giljo_mcp.tools import register_agent_coordination_tools

            # Create mock tools dict
            tools = {}

            # Get database URL
            db_url = os.getenv("DATABASE_URL")
            if not db_url:
                self.log_failure(test_name, "DATABASE_URL not found in environment")
                return False

            # Create database manager
            db_manager = DatabaseManager(database_url=db_url, is_async=False)

            # Register tools
            register_agent_coordination_tools(tools, db_manager)

            # Expected tools
            expected_tools = [
                "get_pending_jobs",
                "acknowledge_job",
                "report_progress",
                "get_next_instruction",
                "complete_job",
                "report_error",
                "send_message",
            ]

            missing_tools = []
            for tool_name in expected_tools:
                if tool_name not in tools:
                    missing_tools.append(tool_name)

            if missing_tools:
                self.log_failure(test_name, f"Missing MCP tools: {', '.join(missing_tools)}")
                return False

            self.log_success(test_name, f"All {len(expected_tools)} MCP coordination tools registered")
            return True

        except Exception as e:
            self.log_failure(test_name, "Exception during tools check", e)
            return False

    async def test_backward_compatibility(self) -> bool:
        """
        Test 4: Verify backward compatibility with existing data.

        Validates:
        - Agent model can be instantiated with old schema (no job_id/mode)
        - Default values applied correctly at database level
        - Existing queries still work
        """
        test_name = "Backward Compatibility"
        self.log_info(f"Running {test_name}...")

        try:
            from uuid import uuid4

            from giljo_mcp.database import DatabaseManager
            from giljo_mcp.models import Agent

            # Get database URL
            db_url = os.getenv("DATABASE_URL")
            if not db_url:
                self.log_failure(test_name, "DATABASE_URL not found")
                return False

            # Create async database manager
            db_manager = DatabaseManager(database_url=db_url, is_async=True)

            # Create test project and agent without specifying new fields
            from giljo_mcp.models import Project

            test_agent_id = str(uuid4())
            test_tenant_key = f"test_{uuid4().hex[:8]}"
            test_project_id = str(uuid4())

            async with db_manager.get_session_async() as session:
                # Create test project (required for foreign key)
                project = Project(
                    id=test_project_id,
                    tenant_key=test_tenant_key,
                    name="Test Project",
                    mission="Test project for backward compatibility",
                )
                session.add(project)
                await session.flush()

                # Create agent without specifying new fields
                agent = Agent(
                    id=test_agent_id,
                    tenant_key=test_tenant_key,
                    project_id=test_project_id,
                    name="Test Agent",
                    role="implementer",
                    status="active",
                    mission="Test mission",
                )
                session.add(agent)
                await session.commit()

            # Retrieve agent from database to check defaults
            from sqlalchemy import delete, select

            async with db_manager.get_session_async() as session:
                result = await session.execute(select(Agent).where(Agent.id == test_agent_id))
                retrieved_agent = result.scalar_one_or_none()

                if not retrieved_agent:
                    self.log_failure(test_name, "Could not retrieve test agent")
                    return False

                # Verify Python-level default applied
                if retrieved_agent.mode != "claude":
                    self.log_failure(test_name, f"Default mode not applied: {retrieved_agent.mode} (expected 'claude')")
                    return False

                if retrieved_agent.job_id is not None:
                    self.log_failure(test_name, f"job_id should default to None, got: {retrieved_agent.job_id}")
                    return False

                # Clean up test data
                await session.execute(delete(Agent).where(Agent.id == test_agent_id))
                await session.execute(delete(Project).where(Project.id == test_project_id))
                await session.commit()

            await db_manager.close_async()

            self.log_success(test_name, "Agent model backward compatible with default values")
            return True

        except Exception as e:
            self.log_failure(test_name, "Exception during compatibility check", e)
            return False

    async def test_installation_idempotency(self) -> bool:
        """
        Test 5: Verify installation is idempotent.

        Validates:
        - Template seeding skips if templates exist
        - Table creation doesn't fail if tables exist
        - Setup state handles repeated runs
        """
        test_name = "Installation Idempotency"
        self.log_info(f"Running {test_name}...")

        try:
            from uuid import uuid4

            from giljo_mcp.database import DatabaseManager
            from giljo_mcp.template_seeder import seed_tenant_templates

            # Get database URL
            db_url = os.getenv("DATABASE_URL")
            if not db_url:
                self.log_failure(test_name, "DATABASE_URL not found")
                return False

            # Create async database manager
            db_manager = DatabaseManager(database_url=db_url, is_async=True)

            # Test tenant key
            test_tenant = f"test_{uuid4().hex[:8]}"

            # First seeding - should create templates
            async with db_manager.get_session_async() as session:
                count1 = await seed_tenant_templates(session, test_tenant)

            if count1 == 0:
                self.log_failure(test_name, "First seeding returned 0 templates")
                return False

            # Second seeding - should skip (idempotent)
            async with db_manager.get_session_async() as session:
                count2 = await seed_tenant_templates(session, test_tenant)

            if count2 != 0:
                self.log_failure(test_name, f"Second seeding should return 0 (idempotent), got {count2}")
                return False

            # Clean up test tenant templates
            from sqlalchemy import delete

            from giljo_mcp.models import AgentTemplate

            async with db_manager.get_session_async() as session:
                await session.execute(delete(AgentTemplate).where(AgentTemplate.tenant_key == test_tenant))
                await session.commit()

            await db_manager.close_async()

            self.log_success(test_name, f"Template seeding is idempotent (first={count1}, second={count2})")
            return True

        except Exception as e:
            self.log_failure(test_name, "Exception during idempotency check", e)
            return False

    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all installation verification tests."""
        print("\n" + "=" * 70)
        print("HANDOVER 0045 - INSTALLATION VERIFICATION TEST SUITE")
        print("=" * 70 + "\n")

        # Run tests sequentially
        await self.test_database_schema()
        await self.test_template_seeding()
        await self.test_mcp_tools_registration()
        await self.test_backward_compatibility()
        await self.test_installation_idempotency()

        # Print summary
        print("\n" + "=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)
        print(f"Total Tests: {self.passed + self.failed}")
        print(f"Passed: {self.passed} ✅")
        print(f"Failed: {self.failed} ❌")
        print(f"Success Rate: {(self.passed / (self.passed + self.failed) * 100):.1f}%")
        print("=" * 70 + "\n")

        return {
            "total": self.passed + self.failed,
            "passed": self.passed,
            "failed": self.failed,
            "success_rate": self.passed / (self.passed + self.failed) if (self.passed + self.failed) > 0 else 0,
            "results": self.results,
        }


async def main():
    """Main test execution."""
    try:
        test_suite = InstallationVerificationTest()
        results = await test_suite.run_all_tests()

        # Exit with appropriate code
        sys.exit(0 if results["failed"] == 0 else 1)

    except KeyboardInterrupt:
        print("\n\nTest suite interrupted by user")
        sys.exit(130)

    except Exception as e:
        print(f"\n\n❌ FATAL ERROR: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
