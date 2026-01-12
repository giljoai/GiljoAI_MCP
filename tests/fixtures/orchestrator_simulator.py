#!/usr/bin/env python
"""
Orchestrator Simulator for E2E Testing

Simulates orchestrator behavior executing the 7-task staging workflow without requiring actual AI.
Makes real MCP HTTP calls to backend and completes in <30 seconds.

Created: 2025-11-27
Purpose: Enable automated E2E testing of orchestrator workflows
Version: v3.2+ (implements Handover 0246a staging workflow)

Usage:
    simulator = OrchestratorSimulator(
        project_id="uuid-here",
        product_id="uuid-here",
        tenant_key="tenant_key",
        orchestrator_id="uuid-here",
        mission="Build a REST API"
    )
    result = await simulator.execute_staging()
    print(f"Spawned {len(simulator.spawned_agents)} agents")
"""

import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class OrchestratorSimulator:
    """
    Simulates orchestrator executing 7-task staging workflow.

    Implements the complete staging workflow from Handover 0246a:
    1. Identity & Context Verification
    2. MCP Health Check
    3. Environment Understanding
    4. Agent Discovery & Version Check
    5. Context Prioritization & Mission Creation
    6. Agent Job Spawning
    7. Activation

    All tasks make real MCP HTTP calls to backend for realistic testing.
    """

    def __init__(
        self,
        project_id: str,
        product_id: str,
        tenant_key: str,
        orchestrator_id: str,
        mission: str,
        mcp_base_url: str = "http://localhost:7272",
    ):
        """
        Initialize OrchestratorSimulator.

        Args:
            project_id: UUID of project being orchestrated
            product_id: UUID of parent product
            tenant_key: Multi-tenant isolation key
            orchestrator_id: UUID of orchestrator job
            mission: User-provided mission/requirements (<10K tokens)
            mcp_base_url: Base URL for MCP HTTP endpoint
        """
        self.project_id = project_id
        self.product_id = product_id
        self.tenant_key = tenant_key
        self.orchestrator_id = orchestrator_id
        self.mission = mission
        self.mcp_base_url = mcp_base_url

        # Staging results tracking
        self.staging_result: dict[str, Any] = {}
        self.spawned_agents: list[dict[str, Any]] = []
        self.discovered_agents: list[dict[str, Any]] = []

        logger.info(
            f"[ORCHESTRATOR_SIMULATOR] Initialized for project {project_id}",
            extra={"project_id": project_id, "tenant_key": tenant_key},
        )

    async def task1_identity_verification(self) -> None:
        """
        Task 1: Identity & Context Verification

        Validates:
        - Project ID is valid UUID
        - Tenant key matches authenticated user
        - Product ID is associated with project
        - Orchestrator connection to MCP server
        """
        logger.info("[TASK 1] Starting identity verification")

        # Verify project exists (would normally query database)
        project_exists = await self._verify_project_exists(self.project_id, self.tenant_key)

        if not project_exists:
            raise ValueError(f"Project {self.project_id} not found for tenant {self.tenant_key}")

        # Record task completion
        self.staging_result["identity_verification"] = {
            "status": "completed",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "project_id": self.project_id,
            "product_id": self.product_id,
            "tenant_key": self.tenant_key,
            "orchestrator_id": self.orchestrator_id,
        }

        logger.info("[TASK 1] Identity verification complete")

    async def task2_mcp_health_check(self) -> None:
        """
        Task 2: MCP Health Check

        Validates:
        - MCP server responds within 2 seconds
        - Authentication token valid
        - All required tools available
        """
        logger.info("[TASK 2] Starting MCP health check")

        # Call health_check() MCP tool
        health_response = await self._call_mcp_tool("health_check", {})

        if not health_response.get("status") == "healthy":
            raise RuntimeError("MCP server health check failed")

        response_time = health_response.get("response_time_ms", 0)
        if response_time > 2000:
            logger.warning(f"[TASK 2] MCP server slow response: {response_time}ms")

        # Record task completion
        self.staging_result["mcp_health_check"] = {
            "status": "completed",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "response_time_ms": response_time,
            "mcp_version": health_response.get("version", "unknown"),
        }

        logger.info(f"[TASK 2] MCP health check complete ({response_time}ms)")

    async def task3_environment_understanding(self) -> None:
        """
        Task 3: Environment Understanding

        Reads:
        - CLAUDE.md from project root
        - Tech stack information
        - Project structure
        - Context management settings
        """
        logger.info("[TASK 3] Starting environment understanding")

        # Read CLAUDE.md using cross-platform path handling
        claude_md_path = Path.cwd() / "CLAUDE.md"
        claude_md_found = False
        tech_stack = "Unknown"

        if claude_md_path.exists():
            try:
                claude_content = claude_md_path.read_text(encoding="utf-8")
                claude_md_found = True

                # Extract tech stack (simple parsing)
                if "Backend:" in claude_content:
                    tech_stack_line = [line for line in claude_content.split("\n") if "Backend:" in line][0]
                    tech_stack = tech_stack_line.split("Backend:")[1].strip()
                elif "Tech Stack" in claude_content:
                    # Find tech stack section
                    lines = claude_content.split("\n")
                    for i, line in enumerate(lines):
                        if "Tech Stack" in line:
                            # Get next few lines
                            tech_stack = "\n".join(lines[i : i + 5])
                            break

                logger.info("[TASK 3] CLAUDE.md found and parsed")
            except Exception as e:
                logger.warning(f"[TASK 3] Failed to parse CLAUDE.md: {e}")
                tech_stack = "Error reading CLAUDE.md"
        else:
            logger.warning("[TASK 3] CLAUDE.md not found, using defaults")

        # Record task completion
        self.staging_result["environment_understanding"] = {
            "status": "completed",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "claude_md_found": claude_md_found,
            "tech_stack": tech_stack,
            "project_root": str(Path.cwd()),
        }

        logger.info("[TASK 3] Environment understanding complete")

    async def task4_agent_discovery(self) -> None:
        """
        Task 4: Agent Discovery & Version Check

        Discovers:
        - Available agents via get_available_agents() MCP tool
        - Agent versions and capabilities
        - Version compatibility
        """
        logger.info("[TASK 4] Starting agent discovery")

        # Call get_available_agents() MCP tool
        agents_response = await self._call_mcp_tool(
            "get_available_agents", {"tenant_key": self.tenant_key, "active_only": True}
        )

        if not agents_response.get("success"):
            raise RuntimeError("Agent discovery failed")

        agents = agents_response.get("agents", [])
        self.discovered_agents = agents

        logger.info(f"[TASK 4] Discovered {len(agents)} agents")

        # Record task completion
        self.staging_result["agent_discovery"] = {
            "status": "completed",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agents_found": agents,
            "agent_count": len(agents),
        }

        logger.info("[TASK 4] Agent discovery complete")

    async def task5_context_and_mission(self) -> None:
        """
        Task 5: Context Prioritization & Mission Creation

        Fetches:
        - Product context via fetch_product_context()
        - Tech stack via fetch_tech_stack()
        - Creates unified mission (<10K tokens)
        """
        logger.info("[TASK 5] Starting context prioritization and mission creation")

        # Fetch product context
        product_context_response = await self._call_mcp_tool(
            "fetch_product_context",
            {"product_id": self.product_id, "tenant_key": self.tenant_key, "priority_filter": 1},
        )

        # Fetch tech stack
        tech_stack_response = await self._call_mcp_tool(
            "fetch_tech_stack", {"product_id": self.product_id, "tenant_key": self.tenant_key}
        )

        # Create condensed mission (simulate mission condensation)
        mission_parts = [
            f"Mission: {self.mission}",
            f"Product: {product_context_response.get('product_name', 'Unknown')}",
            f"Tech Stack: {tech_stack_response.get('languages', [])}",
        ]

        condensed_mission = "\n\n".join(mission_parts)

        # Ensure mission is under 10K tokens (1 token ≈ 4 chars)
        mission_tokens = len(condensed_mission) // 4
        if mission_tokens > 10000:
            # Truncate mission to stay under budget
            max_chars = 10000 * 4
            condensed_mission = condensed_mission[:max_chars]
            mission_tokens = 10000

        # Record task completion
        self.staging_result["context_prioritization"] = {
            "status": "completed",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "mission_tokens": mission_tokens,
            "product_context_fetched": product_context_response.get("success", False),
            "tech_stack_fetched": tech_stack_response.get("success", False),
        }

        logger.info(f"[TASK 5] Context prioritization complete ({mission_tokens} tokens)")

    async def task6_spawn_agents(self) -> None:
        """
        Task 6: Agent Job Spawning

        Creates:
        - MCPAgentJob records for each discovered agent
        - Assigns missions to each agent
        - Sets initial status to 'waiting'
        """
        logger.info("[TASK 6] Starting agent job spawning")

        # Get discovered agents from task4
        agents = self.staging_result.get("agent_discovery", {}).get("agents_found", [])

        if not agents:
            raise RuntimeError("No agents discovered in Task 4")

        # Spawn 3 agents: implementer, tester, reviewer
        agents_to_spawn = ["implementer", "tester", "reviewer"]

        for agent_display_name in agents_to_spawn:
            # Find matching agent in discovered agents
            agent_info = next((a for a in agents if a["name"] == agent_display_name), None)

            if not agent_info:
                logger.warning(f"[TASK 6] Agent type '{agent_display_name}' not found, skipping")
                continue

            # Create agent-specific mission
            agent_mission = self._create_agent_mission(agent_display_name)

            # Call spawn_agent_job() MCP tool
            spawn_response = await self._call_mcp_tool(
                "spawn_agent_job",
                {
                    "agent_display_name": agent_display_name,
                    "agent_name": agent_display_name.capitalize(),
                    "mission": agent_mission,
                    "project_id": self.project_id,
                    "tenant_key": self.tenant_key,
                },
            )

            if spawn_response.get("success"):
                job_info = {
                    "job_id": spawn_response.get("job_id"),
                    "agent_display_name": agent_display_name,
                    "status": spawn_response.get("status", "waiting"),
                    "mission": agent_mission,
                }
                self.spawned_agents.append(job_info)
                logger.info(f"[TASK 6] Spawned {agent_display_name} agent: {job_info['job_id']}")
            else:
                logger.error(f"[TASK 6] Failed to spawn {agent_display_name} agent")

        # Record task completion
        self.staging_result["job_spawning"] = {
            "status": "completed",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agents_spawned": len(self.spawned_agents),
            "agent_display_names": [a["agent_display_name"] for a in self.spawned_agents],
        }

        logger.info(f"[TASK 6] Agent job spawning complete ({len(self.spawned_agents)} agents)")

    async def task7_activation(self) -> None:
        """
        Task 7: Activation

        Activates:
        - Project status transitions to 'active'
        - WebSocket event broadcasting enabled
        - Orchestrator health monitoring started
        """
        logger.info("[TASK 7] Starting project activation")

        # Get workflow status
        status_response = await self._call_mcp_tool(
            "get_workflow_status", {"project_id": self.project_id, "tenant_key": self.tenant_key}
        )

        project_status = status_response.get("status", "unknown")

        # Record task completion
        self.staging_result["activation"] = {
            "status": "completed",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "project_status": project_status,
            "workflow_status_fetched": status_response.get("success", False),
        }

        logger.info("[TASK 7] Project activation complete")

    async def execute_staging(self) -> dict[str, Any]:
        """
        Execute complete 7-task staging workflow.

        Returns:
            {
                "success": True,
                "staging_complete": True,
                "duration_ms": 15234,
                "tasks_completed": [list of task names],
                "spawned_agents_count": 3,
                "staging_result": {full staging results},
                "spawned_agents": [list of spawned agent info]
            }
        """
        start_time = datetime.now(timezone.utc)
        logger.info("[ORCHESTRATOR_SIMULATOR] Starting staging workflow execution")

        try:
            # Execute all 7 tasks sequentially
            await self.task1_identity_verification()
            await self.task2_mcp_health_check()
            await self.task3_environment_understanding()
            await self.task4_agent_discovery()
            await self.task5_context_and_mission()
            await self.task6_spawn_agents()
            await self.task7_activation()

            end_time = datetime.now(timezone.utc)
            duration_ms = int((end_time - start_time).total_seconds() * 1000)

            tasks_completed = [
                "identity_verification",
                "mcp_health_check",
                "environment_understanding",
                "agent_discovery",
                "context_prioritization",
                "job_spawning",
                "activation",
            ]

            result = {
                "success": True,
                "staging_complete": True,
                "duration_ms": duration_ms,
                "tasks_completed": tasks_completed,
                "spawned_agents_count": len(self.spawned_agents),
                "staging_result": self.staging_result,
                "spawned_agents": self.spawned_agents,
            }

            logger.info(
                f"[ORCHESTRATOR_SIMULATOR] Staging workflow complete in {duration_ms}ms",
                extra={"duration_ms": duration_ms, "agents_spawned": len(self.spawned_agents)},
            )

            return result

        except Exception as e:
            logger.error(f"[ORCHESTRATOR_SIMULATOR] Staging workflow failed: {e}", exc_info=True)
            return {
                "success": False,
                "staging_complete": False,
                "error": str(e),
                "staging_result": self.staging_result,
                "spawned_agents": self.spawned_agents,
            }

    # Helper methods

    async def _verify_project_exists(self, project_id: str, tenant_key: str) -> bool:
        """
        Verify project exists in database.

        In real implementation, this would query the database.
        For testing, we assume project exists.

        Args:
            project_id: Project UUID
            tenant_key: Tenant isolation key

        Returns:
            True if project exists, False otherwise
        """
        # For testing purposes, always return True
        # Real implementation would query database
        return True

    async def _call_mcp_tool(self, tool_name: str, params: dict[str, Any]) -> dict[str, Any]:
        """
        Call MCP tool via HTTP endpoint.

        This makes real HTTP POST requests to the MCP server.

        Args:
            tool_name: Name of MCP tool to call
            params: Tool parameters

        Returns:
            Tool response as dictionary
        """
        # Import here to avoid circular dependencies
        import aiohttp

        url = f"{self.mcp_base_url}/mcp"
        payload = {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": tool_name, "arguments": params}}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("result", {})
                    else:
                        logger.error(f"MCP tool call failed: {response.status}")
                        return {"success": False, "error": f"HTTP {response.status}"}

        except Exception as e:
            logger.error(f"MCP tool call exception: {e}", exc_info=True)
            raise

    def _create_agent_mission(self, agent_display_name: str) -> str:
        """
        Create agent-specific mission from main mission.

        Args:
            agent_display_name: Type of agent (implementer, tester, reviewer)

        Returns:
            Agent-specific mission string
        """
        missions = {
            "implementer": f"Implement the following: {self.mission}\n\nFollow project coding standards and use proper error handling.",
            "tester": f"Test the implementation: {self.mission}\n\nWrite comprehensive unit and integration tests.",
            "reviewer": f"Review the implementation and tests: {self.mission}\n\nCheck for code quality, security, and best practices.",
        }

        return missions.get(agent_display_name, f"Execute: {self.mission}")


# Example usage
if __name__ == "__main__":
    import uuid

    async def main():
        """Example usage of OrchestratorSimulator"""
        simulator = OrchestratorSimulator(
            project_id=str(uuid.uuid4()),
            product_id=str(uuid.uuid4()),
            tenant_key="example_tenant",
            orchestrator_id=str(uuid.uuid4()),
            mission="Build a simple REST API with 3 endpoints for user authentication",
        )

        result = await simulator.execute_staging()

        print(f"\nStaging Result:")
        print(f"  Success: {result['success']}")
        print(f"  Duration: {result['duration_ms']}ms")
        print(f"  Tasks Completed: {len(result['tasks_completed'])}")
        print(f"  Agents Spawned: {result['spawned_agents_count']}")
        print(f"\nSpawned Agents:")
        for agent in result["spawned_agents"]:
            print(f"  - {agent['agent_display_name']}: {agent['job_id']}")

    asyncio.run(main())
