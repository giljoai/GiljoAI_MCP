#!/usr/bin/env python
"""
MCP Stdio Adapter for GiljoAI
Bridges stdio-based MCP protocol to HTTP-based API server

This adapter:
1. Receives MCP commands via stdio from Claude
2. Translates them to HTTP REST calls
3. Forwards to the main server on localhost:8000
4. Returns responses back via stdio

This allows Claude to use stdio while the server remains HTTP-based for multi-user support.
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urljoin

import httpx

# Add src to path
src_dir = Path(__file__).parent.parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from giljo_mcp.config_manager import get_config

# Configure logging to file only (not stderr which would interfere with stdio)
log_dir = Path.home() / ".giljo_mcp" / "logs"
log_dir.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_dir / "mcp_adapter.log"),
    ]
)
logger = logging.getLogger(__name__)


class MCPAdapter:
    """Stdio to HTTP adapter for MCP protocol"""

    def __init__(self, server_url: str = None, api_key: Optional[str] = None):
        """
        Initialize the MCP adapter

        Args:
            server_url: Base URL of the GiljoAI API server (default: http://localhost:7272)
            api_key: Optional API key for authentication
        """
        # Try to get port from environment or config
        default_port = os.getenv("GILJO_PORT", "7272")
        default_url = f"http://localhost:{default_port}"
        self.server_url = server_url or os.getenv("GILJO_API_URL", default_url)
        self.api_key = api_key or os.getenv("GILJO_API_KEY")
        self.client = httpx.AsyncClient(timeout=30.0)
        self.tenant_key: Optional[str] = None
        self.project_id: Optional[str] = None

        logger.info(f"MCP Adapter initialized with server: {self.server_url}")

    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()

    async def call_api(self, endpoint: str, method: str = "POST", **kwargs) -> Dict[str, Any]:
        """
        Make an HTTP call to the API server

        Args:
            endpoint: API endpoint path
            method: HTTP method (GET, POST, etc.)
            **kwargs: Additional arguments for the request

        Returns:
            API response as dictionary
        """
        url = urljoin(self.server_url, endpoint)

        # Add authentication header if API key is available
        headers = kwargs.pop("headers", {})
        if self.api_key:
            headers["X-API-Key"] = self.api_key

        try:
            response = await self.client.request(
                method=method,
                url=url,
                headers=headers,
                **kwargs
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"HTTP error calling {url}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error calling API {url}: {e}")
            raise

    async def handle_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle a tool call from MCP protocol

        Args:
            tool_name: Name of the tool to execute
            arguments: Tool arguments

        Returns:
            Tool execution result
        """
        logger.debug(f"Handling tool call: {tool_name} with args: {arguments}")

        # Special handling for certain tools
        if tool_name == "create_project":
            # After creating a project, store the tenant key
            result = await self.call_api(
                "/mcp/tools/execute",
                json={
                    "tool": tool_name,
                    "arguments": arguments,
                    "tenant_key": self.tenant_key,
                    "project_id": self.project_id
                }
            )
            if result.get("success") and result.get("result"):
                self.tenant_key = result["result"].get("tenant_key")
                self.project_id = result["result"].get("project_id")
                logger.info(f"Set tenant context: {self.tenant_key}, project: {self.project_id}")
            return result

        elif tool_name == "switch_project":
            # Update project context
            result = await self.call_api(
                "/mcp/tools/execute",
                json={
                    "tool": tool_name,
                    "arguments": arguments,
                    "tenant_key": self.tenant_key
                }
            )
            if result.get("success") and result.get("result"):
                self.project_id = result["result"].get("project_id")
                self.tenant_key = result["result"].get("tenant_key")
                logger.info(f"Switched to project: {self.project_id}")
            return result

        else:
            # Standard tool execution
            return await self.call_api(
                "/mcp/tools/execute",
                json={
                    "tool": tool_name,
                    "arguments": arguments,
                    "tenant_key": self.tenant_key,
                    "project_id": self.project_id
                }
            )

    async def handle_list_tools(self) -> Dict[str, Any]:
        """Get list of available tools from the server"""
        return await self.call_api("/mcp/tools/list", method="GET")

    async def handle_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle an incoming MCP message

        Args:
            message: MCP protocol message

        Returns:
            Response message
        """
        msg_type = message.get("type")
        msg_id = message.get("id")

        logger.debug(f"Handling message type: {msg_type}, id: {msg_id}")

        try:
            if msg_type == "initialize":
                # Initialize connection
                return {
                    "type": "initialize_response",
                    "id": msg_id,
                    "result": {
                        "protocol_version": "1.0",
                        "server_info": {
                            "name": "GiljoAI MCP Adapter",
                            "version": "2.0.0",
                            "backend": self.server_url
                        },
                        "capabilities": {
                            "tools": True,
                            "resources": False,
                            "prompts": False
                        }
                    }
                }

            elif msg_type == "tools/list":
                # List available tools
                tools_data = await self.handle_list_tools()
                tools_list = []

                # Flatten the categorized tools into MCP format
                for category, tools in tools_data.get("tools", {}).items():
                    for tool in tools:
                        tools_list.append({
                            "name": tool["name"],
                            "description": tool["description"],
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    name: {"type": "string", "description": desc}
                                    for name, desc in tool.get("arguments", {}).items()
                                },
                                "required": list(tool.get("arguments", {}).keys())
                            }
                        })

                return {
                    "type": "tools/list_response",
                    "id": msg_id,
                    "result": {
                        "tools": tools_list
                    }
                }

            elif msg_type == "tools/call":
                # Execute a tool
                tool_name = message.get("params", {}).get("name")
                arguments = message.get("params", {}).get("arguments", {})

                result = await self.handle_tool_call(tool_name, arguments)

                if result.get("success"):
                    return {
                        "type": "tools/call_response",
                        "id": msg_id,
                        "result": result.get("result", {})
                    }
                else:
                    return {
                        "type": "error",
                        "id": msg_id,
                        "error": {
                            "code": -32603,
                            "message": result.get("error", "Tool execution failed")
                        }
                    }

            elif msg_type == "close":
                # Close connection
                logger.info("Received close message")
                return {
                    "type": "close_response",
                    "id": msg_id
                }

            else:
                # Unknown message type
                logger.warning(f"Unknown message type: {msg_type}")
                return {
                    "type": "error",
                    "id": msg_id,
                    "error": {
                        "code": -32601,
                        "message": f"Unknown message type: {msg_type}"
                    }
                }

        except Exception as e:
            logger.exception(f"Error handling message: {e}")
            return {
                "type": "error",
                "id": msg_id,
                "error": {
                    "code": -32603,
                    "message": str(e)
                }
            }

    async def run_stdio(self):
        """
        Run the stdio communication loop
        Reads from stdin, processes messages, writes to stdout
        """
        logger.info("Starting stdio communication loop")

        try:
            # Check if server is available
            health_check = await self.call_api("/mcp/tools/health", method="GET")
            logger.info(f"Server health: {health_check}")
        except Exception as e:
            logger.error(f"Failed to connect to server: {e}")
            error_msg = {
                "type": "error",
                "error": {
                    "code": -32603,
                    "message": f"Cannot connect to GiljoAI server at {self.server_url}. Is it running?"
                }
            }
            print(json.dumps(error_msg), flush=True)
            return

        # Main communication loop
        try:
            while True:
                # Read from stdin
                line = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
                if not line:
                    logger.info("Stdin closed, exiting")
                    break

                line = line.strip()
                if not line:
                    continue

                try:
                    # Parse JSON message
                    message = json.loads(line)
                    logger.debug(f"Received: {message}")

                    # Handle the message
                    response = await self.handle_message(message)

                    # Send response
                    response_json = json.dumps(response)
                    print(response_json, flush=True)
                    logger.debug(f"Sent: {response}")

                    # Check if we should exit
                    if message.get("type") == "close":
                        logger.info("Closing adapter")
                        break

                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON received: {e}")
                    error_response = {
                        "type": "error",
                        "error": {
                            "code": -32700,
                            "message": "Invalid JSON"
                        }
                    }
                    print(json.dumps(error_response), flush=True)

        except KeyboardInterrupt:
            logger.info("Interrupted, exiting")
        except Exception as e:
            logger.exception(f"Unexpected error in stdio loop: {e}")
        finally:
            await self.close()


async def main():
    """Main entry point for the MCP adapter"""
    logger.info("=" * 60)
    logger.info("GiljoAI MCP Stdio Adapter Starting")
    logger.info("=" * 60)

    # Load configuration
    config = get_config()

    # Determine server URL
    server_url = os.getenv("GILJO_API_URL")
    if not server_url:
        # Use configured API port or environment variable
        api_port = os.getenv("GILJO_PORT")
        if not api_port:
            api_port = getattr(config.server, "port", None) or getattr(config.server, "api_port", 7272)
        server_url = f"http://localhost:{api_port}"

    # Get API key if needed
    api_key = None
    if config.server.mode.value != "LOCAL":
        api_key = os.getenv("GILJO_API_KEY") or os.getenv("API_KEY")
        if not api_key:
            logger.warning("No API key provided for non-LOCAL mode")

    # Create and run adapter
    adapter = MCPAdapter(server_url=server_url, api_key=api_key)

    logger.info(f"Connecting to server at: {server_url}")
    logger.info(f"Authentication: {'API Key' if api_key else 'None (LOCAL mode)'}")

    await adapter.run_stdio()

    logger.info("MCP Adapter shutdown complete")


if __name__ == "__main__":
    # Run the adapter
    asyncio.run(main())
