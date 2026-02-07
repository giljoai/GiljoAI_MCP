"""
External HTTP-based Agent Coordination MCP Tools (Handover 0060).

Provides HTTP API wrapper tools for agents running OUTSIDE GiljoAI server:
- Claude Code (external CLI agent)
- Codex (external agent)
- Gemini CLI (external agent)

These tools authenticate via JWT tokens and communicate with GiljoAI API endpoints.
Multi-tenant isolation is enforced server-side via JWT token validation.

Key Features:
- Async HTTP communication via aiohttp
- JWT cookie-based authentication
- Automatic re-authentication on 401 errors
- Retry logic with exponential backoff
- Comprehensive error handling
- Request timeouts (30 seconds default)
- Session management and reuse
- Input validation

Production-grade implementation following industry best practices.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import aiohttp

from ..config_manager import ConfigManager


logger = logging.getLogger(__name__)


class ExternalAgentCoordinationTools:
    """
    HTTP-based coordination tools for external agents.

    Wraps GiljoAI API endpoints to provide MCP tools for agents running outside
    the server process. Handles authentication, session management, and error handling.

    Attributes:
        session: aiohttp ClientSession for HTTP requests
        config: ConfigManager instance for configuration
        base_url: API server base URL
        authenticated: Whether session is authenticated
        max_retries: Maximum retry attempts for transient failures
        timeout: Request timeout in seconds
    """

    def __init__(
        self,
        session: Optional[aiohttp.ClientSession] = None,
        config: Optional[ConfigManager] = None,
        max_retries: int = 3,
        timeout: int = 30,
    ):
        """
        Initialize external coordination tools.

        Args:
            session: Optional aiohttp ClientSession (creates new if None)
            config: Optional ConfigManager (creates new if None)
            max_retries: Maximum retry attempts for transient failures
            timeout: Request timeout in seconds
        """
        self.session = session
        self.config = config or ConfigManager()
        self.base_url = self.config.get("api.base_url", "http://localhost:7272")
        self.authenticated = False
        self.max_retries = max_retries
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self._auth_lock = asyncio.Lock()

        logger.info(
            f"[ExternalAgentCoordinationTools] Initialized with base_url={self.base_url}, "
            f"max_retries={max_retries}, timeout={timeout}s"
        )

    async def _ensure_session(self) -> aiohttp.ClientSession:
        """
        Ensure aiohttp session exists.

        Returns:
            aiohttp ClientSession

        Note:
            Creates new session if not provided in constructor.
        """
        if self.session is None:
            self.session = aiohttp.ClientSession(timeout=self.timeout)
            logger.debug("[ExternalAgentCoordinationTools] Created new aiohttp session")
        return self.session

    async def _authenticate(self) -> bool:
        """
        Authenticate with API server and store JWT cookie.

        Returns:
            True if authentication successful, False otherwise

        Security:
            - Credentials loaded from config
            - JWT token stored in session cookie jar
            - Lock prevents concurrent authentication attempts
        """
        async with self._auth_lock:
            try:
                session = await self._ensure_session()

                username = self.config.get("auth.username")
                password = self.config.get("auth.password")

                if not username or not password:
                    logger.error("[_authenticate] Missing credentials in config")
                    return False

                auth_url = f"{self.base_url}/api/auth/login"
                payload = {"username": username, "password": password}

                logger.debug(f"[_authenticate] Authenticating as {username}")

                async with session.post(auth_url, json=payload) as resp:
                    if resp.status == 200:
                        self.authenticated = True
                        logger.info(f"[_authenticate] Authentication successful for {username}")
                        return True
                    error_text = await resp.text()
                    logger.error(f"[_authenticate] Authentication failed: status={resp.status}, error={error_text}")
                    return False

            except aiohttp.ClientConnectorError as e:
                logger.error(f"[_authenticate] Connection error: {e}")
                return False
            except asyncio.TimeoutError:
                logger.error("[_authenticate] Authentication timeout")
                return False
            except Exception as e:
                logger.error(f"[_authenticate] Unexpected error during authentication: {e}", exc_info=True)
                return False

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        json_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        retry_count: int = 0,
    ) -> Dict[str, Any]:
        """
        Make HTTP request with authentication and retry logic.

        Args:
            method: HTTP method (GET, POST, PATCH, DELETE)
            endpoint: API endpoint path (e.g., '/api/agent-jobs')
            json_data: Optional JSON request body
            params: Optional query parameters
            retry_count: Current retry attempt number

        Returns:
            dict: Response data or error dict

        Error Handling:
            - 401: Re-authenticate and retry
            - 403: Forbidden (multi-tenant violation)
            - 404: Resource not found
            - 500+: Server error
            - ConnectionError: API server unavailable
            - TimeoutError: Request timeout

        Retry Logic:
            - Transient errors (500+, connection) retry with exponential backoff
            - Max retries configurable (default 3)
            - Authentication errors trigger re-auth then retry
        """
        try:
            # Ensure authenticated
            if not self.authenticated:
                auth_success = await self._authenticate()
                if not auth_success:
                    return {"status": "error", "error": "Authentication failed - check credentials in config"}

            session = await self._ensure_session()
            url = f"{self.base_url}{endpoint}"

            logger.debug(
                f"[_make_request] {method} {url}, "
                f"json_data={'present' if json_data else 'none'}, "
                f"params={params}, retry={retry_count}"
            )

            # Make request
            async with session.request(method=method, url=url, json=json_data, params=params) as resp:
                # Handle different status codes
                if resp.status == 200 or resp.status == 201:
                    return await resp.json()

                if resp.status == 401:
                    # Re-authenticate and retry once
                    logger.warning("[_make_request] 401 Unauthorized - re-authenticating")
                    self.authenticated = False
                    auth_success = await self._authenticate()
                    if auth_success and retry_count < 1:
                        return await self._make_request(
                            method=method,
                            endpoint=endpoint,
                            json_data=json_data,
                            params=params,
                            retry_count=retry_count + 1,
                        )
                    return {"status": "error", "error": "Re-authentication failed after 401 response"}

                if resp.status == 403:
                    error_detail = await resp.text()
                    logger.warning(f"[_make_request] 403 Forbidden: {error_detail}")
                    return {"status": "error", "error": f"Unauthorized access (multi-tenant violation): {error_detail}"}

                if resp.status == 404:
                    error_detail = await resp.text()
                    logger.warning(f"[_make_request] 404 Not Found: {error_detail}")
                    return {"status": "error", "error": f"Resource not found: {error_detail}"}

                if resp.status >= 500:
                    # Server error - retry with exponential backoff
                    error_detail = await resp.text()
                    logger.error(f"[_make_request] {resp.status} Server error: {error_detail}")

                    if retry_count < self.max_retries:
                        backoff_delay = 2**retry_count  # Exponential backoff
                        logger.info(
                            f"[_make_request] Retrying in {backoff_delay}s "
                            f"(attempt {retry_count + 1}/{self.max_retries})"
                        )
                        await asyncio.sleep(backoff_delay)
                        return await self._make_request(
                            method=method,
                            endpoint=endpoint,
                            json_data=json_data,
                            params=params,
                            retry_count=retry_count + 1,
                        )
                    return {
                        "status": "error",
                        "error": f"Server error after {self.max_retries} retries: {error_detail}",
                    }

                # Other errors
                error_detail = await resp.text()
                logger.error(f"[_make_request] {resp.status} error: {error_detail}")
                return {"status": "error", "error": f"HTTP {resp.status}: {error_detail}"}

        except aiohttp.ClientConnectorError as e:
            logger.error(f"[_make_request] Connection error: {e}")

            # Retry transient connection errors
            if retry_count < self.max_retries:
                backoff_delay = 2**retry_count
                logger.info(
                    f"[_make_request] Retrying connection in {backoff_delay}s "
                    f"(attempt {retry_count + 1}/{self.max_retries})"
                )
                await asyncio.sleep(backoff_delay)
                return await self._make_request(
                    method=method, endpoint=endpoint, json_data=json_data, params=params, retry_count=retry_count + 1
                )
            return {"status": "error", "error": f"API server unavailable after {self.max_retries} retries: {e!s}"}

        except asyncio.TimeoutError:
            logger.error(f"[_make_request] Request timeout after {self.timeout.total}s")
            return {"status": "error", "error": f"Request timeout after {self.timeout.total} seconds"}

        except Exception as e:
            logger.error(f"[_make_request] Unexpected error: {e}", exc_info=True)
            return {"status": "error", "error": f"Unexpected error: {e!s}"}

    # Tool Methods - Public API

    async def create_agent_job(
        self,
        agent_display_name: str,
        mission: str,
        context_chunks: Optional[List[str]] = None,
        spawned_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a new agent job via POST /api/agent-jobs.

        Args:
            agent_display_name: Agent type (e.g., 'implementer', 'tester', 'reviewer')
            mission: Mission instructions for the agent
            context_chunks: Optional list of context chunk IDs
            spawned_by: Optional parent job_id

        Returns:
            dict: {
                'status': 'success' | 'error',
                'job_id': str (if success),
                'message': str,
                'error': str (if error)
            }

        Security:
            - Tenant isolation enforced via JWT token (server-side)
            - Only admins can create jobs (enforced server-side)

        Validation:
            - agent_display_name cannot be empty
            - mission cannot be empty
        """
        # Input validation
        if not agent_display_name or not agent_display_name.strip():
            return {"status": "error", "error": "agent_display_name cannot be empty"}

        if not mission or not mission.strip():
            return {"status": "error", "error": "mission cannot be empty"}

        payload = {
            "agent_display_name": agent_display_name.strip(),
            "mission": mission.strip(),
            "context_chunks": context_chunks or [],
            "spawned_by": spawned_by,
        }

        logger.info(
            f"[create_agent_job] Creating job for agent_display_name={agent_display_name}, mission_length={len(mission)}"
        )

        response = await self._make_request(method="POST", endpoint="/api/agent-jobs", json_data=payload)

        if "job_id" in response:
            return {
                "status": "success",
                "job_id": response["job_id"],
                "message": response.get("message", "Job created successfully"),
            }
        return response

    async def send_agent_message(
        self, job_id: str, role: str, message_type: str, content: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Send message to agent job via POST /api/agent-jobs/{job_id}/messages.

        Args:
            job_id: Job ID to send message to
            role: Message role ('system', 'agent', 'orchestrator')
            message_type: Message type ('status', 'request', 'response', 'error')
            content: Message content dictionary

        Returns:
            dict: {
                'status': 'success' | 'error',
                'message_id': str (if success),
                'timestamp': str (if success),
                'error': str (if error)
            }

        Security:
            - Tenant isolation enforced via JWT token
            - Only messages within tenant's jobs allowed
        """
        # Input validation
        if not job_id or not job_id.strip():
            return {"status": "error", "error": "job_id cannot be empty"}

        if not role or not role.strip():
            return {"status": "error", "error": "role cannot be empty"}

        if not message_type or not message_type.strip():
            return {"status": "error", "error": "message_type cannot be empty"}

        if not content or not isinstance(content, dict):
            return {"status": "error", "error": "content must be a non-empty dict"}

        payload = {"role": role.strip(), "type": message_type.strip(), "content": content}

        logger.info(f"[send_agent_message] Sending message to job {job_id}, role={role}, type={message_type}")

        response = await self._make_request(
            method="POST", endpoint=f"/api/agent-jobs/{job_id}/messages", json_data=payload
        )

        if "message_id" in response:
            return {
                "status": "success",
                "message_id": response["message_id"],
                "timestamp": response.get("timestamp", datetime.now(timezone.utc).isoformat()),
            }
        return response

    async def get_agent_job_status(self, job_id: str) -> Dict[str, Any]:
        """
        Get agent job status via GET /api/agent-jobs/{job_id}.

        Args:
            job_id: Job ID to retrieve

        Returns:
            dict: {
                'status': 'success' | 'error',
                'job': dict (if success) with keys:
                    - job_id: str
                    - agent_display_name: str
                    - mission: str
                    - status: str
                    - acknowledged: bool
                    - started_at: str (ISO datetime)
                    - completed_at: str (ISO datetime)
                    - created_at: str (ISO datetime)
                    - context_chunks: list[str]
                    - messages: list[dict]
                'error': str (if error)
            }

        Security:
            - Tenant isolation enforced via JWT token
            - Only jobs within tenant can be accessed
        """
        # Input validation
        if not job_id or not job_id.strip():
            return {"status": "error", "error": "job_id cannot be empty"}

        logger.info(f"[get_agent_job_status] Retrieving status for job {job_id}")

        response = await self._make_request(method="GET", endpoint=f"/api/agent-jobs/{job_id}")

        if "job_id" in response:
            return {"status": "success", "job": response}
        return response

    async def acknowledge_agent_job(self, job_id: str) -> Dict[str, Any]:
        """
        Acknowledge agent job via POST /api/agent-jobs/{job_id}/acknowledge.

        Transitions job from 'pending' to 'active' status.

        Args:
            job_id: Job ID to acknowledge

        Returns:
            dict: {
                'status': 'success' | 'error',
                'job': dict (if success) with keys:
                    - job_id: str
                    - status: str ('active')
                    - started_at: str (ISO datetime)
                'message': str (if success),
                'error': str (if error)
            }

        Security:
            - Tenant isolation enforced via JWT token
        """
        # Input validation
        if not job_id or not job_id.strip():
            return {"status": "error", "error": "job_id cannot be empty"}

        logger.info(f"[acknowledge_agent_job] Acknowledging job {job_id}")

        response = await self._make_request(method="POST", endpoint=f"/api/agent-jobs/{job_id}/acknowledge")

        if "job_id" in response:
            return {
                "status": "success",
                "job": {
                    "job_id": response["job_id"],
                    "status": response["status"],
                    "started_at": response["started_at"],
                },
                "message": response.get("message", "Job acknowledged successfully"),
            }
        return response

    async def complete_agent_job(self, job_id: str, result: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Complete agent job via POST /api/agent-jobs/{job_id}/complete.

        Transitions job from 'active' to 'completed' status.

        Args:
            job_id: Job ID to complete
            result: Optional result data with keys:
                - summary: str
                - files_created: list[str]
                - files_modified: list[str]
                - tests_written: list[str]
                - coverage: str
                - notes: str

        Returns:
            dict: {
                'status': 'success' | 'error',
                'job_id': str (if success),
                'message': str,
                'error': str (if error)
            }

        Security:
            - Tenant isolation enforced via JWT token
        """
        # Input validation
        if not job_id or not job_id.strip():
            return {"status": "error", "error": "job_id cannot be empty"}

        payload = {"result": result or {}}

        logger.info(f"[complete_agent_job] Completing job {job_id}")

        response = await self._make_request(
            method="POST", endpoint=f"/api/agent-jobs/{job_id}/complete", json_data=payload
        )

        if "job_id" in response:
            return {
                "status": "success",
                "job_id": response["job_id"],
                "message": response.get("message", "Job completed successfully"),
            }
        return response

    async def fail_agent_job(self, job_id: str, error: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Fail agent job via POST /api/agent-jobs/{job_id}/fail.

        Transitions job from 'active' to 'failed' status.

        Args:
            job_id: Job ID to fail
            error: Optional error data with keys:
                - type: str (error category)
                - message: str (error details)
                - context: str (what was being done)

        Returns:
            dict: {
                'status': 'success' | 'error',
                'job_id': str (if success),
                'message': str,
                'error': str (if error)
            }

        Security:
            - Tenant isolation enforced via JWT token
        """
        # Input validation
        if not job_id or not job_id.strip():
            return {"status": "error", "error": "job_id cannot be empty"}

        payload = {"error": error or {}}

        logger.info(f"[fail_agent_job] Failing job {job_id}")

        response = await self._make_request(method="POST", endpoint=f"/api/agent-jobs/{job_id}/fail", json_data=payload)

        if "job_id" in response:
            return {
                "status": "success",
                "job_id": response["job_id"],
                "message": response.get("message", "Job marked as failed"),
            }
        return response

    async def list_active_agent_jobs(
        self, status: Optional[str] = None, agent_display_name: Optional[str] = None, limit: int = 100
    ) -> Dict[str, Any]:
        """
        List active agent jobs via GET /api/agent-jobs.

        Args:
            status: Optional status filter ('pending', 'active', 'completed', 'failed')
            agent_display_name: Optional agent type filter
            limit: Maximum number of results (default 100)

        Returns:
            dict: {
                'status': 'success' | 'error',
                'jobs': list[dict] (if success),
                'total': int (if success),
                'error': str (if error)
            }

        Security:
            - Tenant isolation enforced via JWT token
            - Only jobs within tenant are returned
        """
        params = {"limit": limit, "offset": 0}

        if status:
            params["status"] = status

        if agent_display_name:
            params["agent_display_name"] = agent_display_name

        logger.info(
            f"[list_active_agent_jobs] Listing jobs with status={status}, agent_display_name={agent_display_name}, limit={limit}"
        )

        response = await self._make_request(method="GET", endpoint="/api/agent-jobs", params=params)

        if "jobs" in response:
            return {
                "status": "success",
                "jobs": response["jobs"],
                "total": response.get("total", len(response["jobs"])),
            }
        return response

    async def close(self):
        """
        Close HTTP session.

        Should be called when tools are no longer needed to release resources.
        """
        if self.session:
            await self.session.close()
            logger.info("[ExternalAgentCoordinationTools] HTTP session closed")


def register_external_agent_coordination_tools(tools: dict, config: dict) -> None:
    """
    Register HTTP-based coordination tools for external agents.

    Creates singleton instance of ExternalAgentCoordinationTools and registers
    7 tool functions for external agent coordination.

    Args:
        tools: Dictionary to register tools into
        config: Configuration dictionary or ConfigManager instance

    Registered Tools:
        - create_agent_job_external
        - send_agent_message_external
        - get_agent_job_status_external
        - acknowledge_agent_job_external
        - complete_agent_job_external
        - fail_agent_job_external
        - list_active_agent_jobs_external

    Note:
        Tools are async functions that must be awaited when called.
    """
    # Create singleton instance
    coordinator = ExternalAgentCoordinationTools(config=config)

    # Register tool functions
    tools["create_agent_job_external"] = coordinator.create_agent_job
    tools["send_agent_message_external"] = coordinator.send_agent_message
    tools["get_agent_job_status_external"] = coordinator.get_agent_job_status
    tools["acknowledge_agent_job_external"] = coordinator.acknowledge_agent_job
    tools["complete_agent_job_external"] = coordinator.complete_agent_job
    tools["fail_agent_job_external"] = coordinator.fail_agent_job
    tools["list_active_agent_jobs_external"] = coordinator.list_active_agent_jobs

    logger.info(
        "[register_external_agent_coordination_tools] Registered 7 HTTP-based coordination tools for external agents"
    )
