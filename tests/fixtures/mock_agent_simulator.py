"""
Mock Agent Simulator for E2E Testing.

Simulates real agent behavior with fast-completing execution (5-10 seconds)
for E2E testing. Makes real MCP HTTP calls to backend at http://localhost:7272/mcp.

Supports both execution modes:
- Claude Code subagent mode (simulated Task calls)
- Multi-terminal mode (direct MCP HTTP requests)

Example usage:
    >>> simulator = MockAgentSimulator(
    ...     job_id="job-123",
    ...     tenant_key="tenant-abc",
    ...     api_key="test-api-key",
    ...     api_url="http://localhost:7272/mcp",
    ...     agent_display_name="implementer"
    ... )
    >>> await simulator.run()  # Complete execution in 5-10 seconds
"""

import asyncio
import json
import logging
import random
from typing import Any, Optional

from aiohttp import ClientError, ClientSession, ClientTimeout


logger = logging.getLogger(__name__)


class MockAgentSimulator:
    """
    Mock agent simulator for E2E testing.

    Simulates agent execution in 5-10 seconds (not hours) while making
    real MCP HTTP calls to the backend server.

    Attributes:
        job_id: Agent job UUID
        tenant_key: Tenant isolation key
        api_key: MCP API key for authentication
        api_url: MCP HTTP endpoint URL
        agent_display_name: Type of agent (implementer, tester, reviewer, documenter)
    """

    def __init__(
        self,
        job_id: str,
        tenant_key: str,
        api_key: str,
        api_url: str = "http://localhost:7272/mcp",
        agent_display_name: str = "implementer",
    ):
        """
        Initialize mock agent simulator.

        Args:
            job_id: Agent job UUID
            tenant_key: Tenant isolation key
            api_key: MCP API key for authentication
            api_url: MCP HTTP endpoint URL (default: http://localhost:7272/mcp)
            agent_display_name: Type of agent (default: implementer)
        """
        self.job_id = job_id
        self.tenant_key = tenant_key
        self.api_key = api_key
        self.api_url = api_url
        self.agent_display_name = agent_display_name

        self._session: Optional[ClientSession] = None
        self._request_id: int = 0
        self._logger = logging.getLogger(f"{__name__}.{agent_display_name}")

    async def _get_session(self) -> ClientSession:
        """
        Get or create aiohttp ClientSession.

        Returns:
            Active ClientSession instance
        """
        if self._session is None or self._session.closed:
            timeout = ClientTimeout(total=30, connect=10)
            self._session = ClientSession(timeout=timeout)
        return self._session

    async def _make_mcp_request(self, method: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """
        Make MCP HTTP request to backend server.

        Args:
            method: MCP tool method name (e.g., "mcp__giljo-mcp__get_agent_mission")
            arguments: Tool arguments

        Returns:
            MCP response dictionary

        Raises:
            ClientError: On network/connection errors
        """
        self._request_id += 1

        # JSON-RPC 2.0 format
        payload = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": method, "arguments": arguments},
            "id": self._request_id,
        }

        headers = {"X-API-Key": self.api_key, "Content-Type": "application/json"}

        session = await self._get_session()

        try:
            async with session.post(self.api_url, json=payload, headers=headers) as response:
                response.raise_for_status()
                return await response.json()
        except ClientError as e:
            self._logger.error(f"MCP request failed: {e}", exc_info=True)
            raise

    async def fetch_mission(self, job_id: str, tenant_key: str) -> dict[str, Any]:
        """
        Fetch agent mission from backend via get_agent_mission MCP tool.

        Args:
            job_id: Agent job UUID
            tenant_key: Tenant isolation key

        Returns:
            Mission dictionary with agent details and mission text
        """
        try:
            self._logger.info(f"Fetching mission for job {job_id}")

            response = await self._make_mcp_request(
                method="mcp__giljo-mcp__get_agent_mission",
                arguments={"job_id": job_id, "tenant_key": tenant_key},
            )

            # Parse MCP response
            if "result" in response and "content" in response["result"]:
                content = response["result"]["content"]
                if content and len(content) > 0:
                    text = content[0].get("text", "{}")
                    result = json.loads(text)
                    self._logger.info(f"Mission fetched successfully: {result.get('agent_display_name', 'unknown')}")
                    return result

            self._logger.warning(f"Invalid mission response format: {response}")
            return {"error": "INVALID_RESPONSE", "message": "Missing content in response"}

        except ClientError as e:
            self._logger.error(f"Network error fetching mission: {e}")
            return {"error": "NETWORK_ERROR", "message": f"Connection failed: {e!s}"}
        except json.JSONDecodeError as e:
            self._logger.error(f"JSON decode error: {e}")
            return {"error": "PARSE_ERROR", "message": f"Invalid JSON response: {e!s}"}
        except Exception as e:
            self._logger.error(f"Unexpected error fetching mission: {e}", exc_info=True)
            return {"error": "UNKNOWN_ERROR", "message": f"Unexpected error: {e!s}"}

    async def execute_work(self, mission: dict[str, Any]) -> None:
        """
        Simulate agent work execution.

        Logs actions and sleeps to simulate work phases (5-10 seconds total).
        Does not actually perform real work - just simulation for testing.

        Args:
            mission: Mission dictionary with mission text and metadata
        """
        mission_text = mission.get("mission", "No mission provided")
        self._logger.info(f"Starting work execution: {mission_text[:100]}")

        # Simulate different work phases with random timing (5-10 seconds total)
        phases = [
            ("Analyzing requirements", 1, 2),
            ("Planning implementation", 1, 2),
            ("Executing work", 2, 4),
            ("Validating results", 1, 2),
        ]

        for phase_name, min_duration, max_duration in phases:
            duration = random.uniform(min_duration, max_duration)
            self._logger.info(f"Work phase: {phase_name} (duration: {duration:.2f}s)")
            await asyncio.sleep(duration)

        self._logger.info("Work execution completed")

    async def send_message_to_agent(self, to_agent_id: str, message: str) -> dict[str, Any]:
        """
        Send message to another agent via send_message MCP tool.

        Args:
            to_agent_id: Target agent job ID
            message: Message content

        Returns:
            Result dictionary with message_id if successful
        """
        try:
            self._logger.info(f"Sending message to {to_agent_id}")

            response = await self._make_mcp_request(
                method="mcp__giljo-mcp__send_message",
                arguments={"to_agent": to_agent_id, "message": message, "priority": "medium"},
            )

            # Parse MCP response
            if "result" in response and "content" in response["result"]:
                content = response["result"]["content"]
                if content and len(content) > 0:
                    text = content[0].get("text", "{}")
                    result = json.loads(text)
                    self._logger.info(f"Message sent successfully: {result.get('message_id', 'unknown')}")
                    return result

            return {"error": "INVALID_RESPONSE", "message": "Missing content in response"}

        except Exception as e:
            self._logger.error(f"Error sending message: {e}", exc_info=True)
            return {"error": "MESSAGE_ERROR", "message": f"Failed to send message: {e!s}"}

    async def check_messages(self) -> dict[str, Any]:
        """
        Check for incoming messages via receive_messages MCP tool.

        Returns:
            Dictionary with messages list
        """
        try:
            self._logger.debug("Checking for messages")

            response = await self._make_mcp_request(
                method="mcp__giljo-mcp__receive_messages", arguments={"agent_id": self.job_id}
            )

            # Parse MCP response
            if "result" in response and "content" in response["result"]:
                content = response["result"]["content"]
                if content and len(content) > 0:
                    text = content[0].get("text", "{}")
                    result = json.loads(text)
                    message_count = len(result.get("messages", []))
                    self._logger.debug(f"Received {message_count} messages")
                    return result

            return {"success": True, "messages": []}

        except Exception as e:
            self._logger.error(f"Error checking messages: {e}", exc_info=True)
            return {"error": "MESSAGE_CHECK_ERROR", "message": f"Failed to check messages: {e!s}"}

    async def report_progress(self, progress: dict[str, Any]) -> dict[str, Any]:
        """
        Report progress to backend via report_progress MCP tool.

        Args:
            progress: Progress dictionary (phase, completion percentage, details)

        Returns:
            Result dictionary
        """
        try:
            self._logger.info(
                f"Reporting progress: {progress.get('phase', 'unknown')} - {progress.get('completion', 0)}%"
            )

            response = await self._make_mcp_request(
                method="mcp__giljo-mcp__report_progress",
                arguments={"job_id": self.job_id, "progress": progress},
            )

            # Parse MCP response
            if "result" in response and "content" in response["result"]:
                content = response["result"]["content"]
                if content and len(content) > 0:
                    text = content[0].get("text", "{}")
                    result = json.loads(text)
                    return result

            return {"success": True}

        except Exception as e:
            self._logger.error(f"Error reporting progress: {e}", exc_info=True)
            return {"error": "PROGRESS_ERROR", "message": f"Failed to report progress: {e!s}"}

    async def complete_job(self, result: dict[str, Any]) -> dict[str, Any]:
        """
        Complete job via complete_job MCP tool.

        Args:
            result: Completion result dictionary (status, summary, files_changed, etc.)

        Returns:
            Result dictionary
        """
        try:
            self._logger.info(f"Completing job: {result.get('status', 'unknown')}")

            response = await self._make_mcp_request(
                method="mcp__giljo-mcp__complete_job", arguments={"job_id": self.job_id, "result": result}
            )

            # Parse MCP response
            if "result" in response and "content" in response["result"]:
                content = response["result"]["content"]
                if content and len(content) > 0:
                    text = content[0].get("text", "{}")
                    result_data = json.loads(text)
                    self._logger.info("Job completed successfully")
                    return result_data

            return {"success": True}

        except Exception as e:
            self._logger.error(f"Error completing job: {e}", exc_info=True)
            return {"error": "COMPLETION_ERROR", "message": f"Failed to complete job: {e!s}"}

    async def run(self) -> None:
        """
        Main execution loop for mock agent.

        Workflow:
        1. Fetch mission from backend
        2. Execute simulated work (5-10 seconds)
        3. Check for messages (optional)
        4. Report progress (optional)
        5. Complete job

        Completes in <15 seconds for E2E testing.
        """
        try:
            self._logger.info(f"Starting mock agent execution: {self.agent_display_name} (job: {self.job_id})")

            # Phase 1: Fetch mission
            mission = await self.fetch_mission(self.job_id, self.tenant_key)

            if "error" in mission:
                self._logger.error(f"Failed to fetch mission: {mission.get('message', 'Unknown error')}")
                return

            # Phase 2: Execute work (5-10 seconds)
            await self.execute_work(mission)

            # Phase 3: Check for messages (optional, non-blocking)
            messages = await self.check_messages()
            if messages.get("messages"):
                self._logger.info(f"Received {len(messages['messages'])} messages during execution")

            # Phase 4: Report progress (optional)
            await self.report_progress(
                {
                    "phase": "completion",
                    "completion": 100,
                    "details": f"Mock {self.agent_display_name} work completed successfully",
                }
            )

            # Phase 5: Complete job
            completion_result = {
                "status": "success",
                "summary": f"Mock {self.agent_display_name} completed simulation",
                "agent_display_name": self.agent_display_name,
                "duration_seconds": "5-10",
            }

            await self.complete_job(completion_result)

            self._logger.info(f"Mock agent execution completed: {self.agent_display_name}")

        except Exception as e:
            self._logger.error(f"Error during agent execution: {e}", exc_info=True)
        finally:
            # Cleanup session
            if self._session and not self._session.closed:
                await self._session.close()


# Standalone execution helper for testing
async def run_mock_agent(
    job_id: str,
    tenant_key: str,
    api_key: str,
    agent_display_name: str = "implementer",
    api_url: str = "http://localhost:7272/mcp",
) -> None:
    """
    Standalone function to run a mock agent.

    Args:
        job_id: Agent job UUID
        tenant_key: Tenant isolation key
        api_key: MCP API key
        agent_display_name: Agent display name (default: implementer)
        api_url: MCP endpoint URL (default: http://localhost:7272/mcp)

    Example:
        >>> await run_mock_agent(
        ...     job_id="job-123",
        ...     tenant_key="tenant-abc",
        ...     api_key="test-key",
        ...     agent_display_name="implementer"
        ... )
    """
    simulator = MockAgentSimulator(
        job_id=job_id, tenant_key=tenant_key, api_key=api_key, api_url=api_url, agent_display_name=agent_display_name
    )

    await simulator.run()
