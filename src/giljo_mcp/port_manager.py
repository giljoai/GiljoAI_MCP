"""
Port Manager - Centralized port configuration and management

This module provides utilities for:
- Loading ports from multiple sources (config.yaml, environment variables)
- Checking port availability
- Finding alternative ports when preferred ones are occupied
- Conflict resolution
- Configuration validation
"""

import logging
import os
import socket
from dataclasses import dataclass
from pathlib import Path

from giljo_mcp._config_io import read_config


logger = logging.getLogger(__name__)


@dataclass
class PortConfiguration:
    """Port configuration for all services"""

    # Main unified server port (v2.0 architecture)
    api_port: int = 7272  # Unified HTTP server (API + WebSocket + MCP tools)

    # Frontend development server
    frontend_port: int = 7274

    # Database
    postgres_port: int = 5432

    # Alternative ports if preferred are occupied
    api_alternatives: list[int] = None
    frontend_alternatives: list[int] = None

    def __post_init__(self):
        """Initialize default alternatives if not provided"""
        if self.api_alternatives is None:
            self.api_alternatives = [7273, 7274, 8747, 8823, 9456, 9789]
        if self.frontend_alternatives is None:
            self.frontend_alternatives = [6001, 6002, 6003, 5173, 5174]


class PortManager:
    """
    Centralized port management system.

    Handles port configuration from multiple sources with the following priority:
    1. Command-line arguments (if applicable)
    2. Environment variables
    3. config.yaml file
    4. Defaults

    Also provides port availability checking and conflict resolution.
    """

    def __init__(self, config_path: Path | None = None):
        """
        Initialize PortManager.

        Args:
            config_path: Path to config.yaml file (defaults to ./config.yaml)
        """
        self.config_path = config_path or Path("./config.yaml")
        self.config = PortConfiguration()

    @staticmethod
    def check_port_available(port: int, host: str = "127.0.0.1") -> bool:
        """
        Check if a port is available.

        Args:
            port: Port number to check
            host: Host to check on (default: 127.0.0.1)

        Returns:
            True if port is available (not in use), False if occupied
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                result = sock.connect_ex((host, port))
                return result != 0  # True if NOT in use (connection failed)
        except (OSError, ValueError) as e:
            logger.debug(f"Error checking port {port}: {e}")
            return False

    @staticmethod
    def find_available_port(preferred: int, alternatives: list[int | None] = None) -> int:
        """
        Find an available port, starting with preferred.

        Args:
            preferred: Preferred port number
            alternatives: List of alternative ports to try

        Returns:
            Available port number

        Raises:
            RuntimeError: If no available port can be found
        """
        # Check preferred port first
        if PortManager.check_port_available(preferred):
            return preferred

        # Try alternatives
        if alternatives:
            for port in alternatives:
                if PortManager.check_port_available(port):
                    logger.warning(f"Port {preferred} is occupied, using alternative port {port}")
                    return port

        # Last resort: find random available port in safe range
        import random

        for _ in range(10):
            port = random.randint(7200, 9999)
            if PortManager.check_port_available(port):
                logger.warning(f"Using random available port {port} (preferred {preferred} was occupied)")
                return port

        raise RuntimeError(f"Could not find available port (preferred: {preferred})")

    def load_from_config_file(self) -> bool:
        """
        Load port configuration from config.yaml.

        Returns:
            True if config was loaded successfully, False otherwise
        """
        if not self.config_path.exists():
            logger.debug(f"Config file not found: {self.config_path}")
            return False

        try:
            data = read_config(self.config_path)

            # Support both old 'server' structure and new 'services' structure
            if "services" in data:
                services = data["services"]

                # API port from services.api.port
                if "api" in services and isinstance(services["api"], dict) and "port" in services["api"]:
                    self.config.api_port = services["api"]["port"]
                    logger.debug(f"Loaded API port from services config: {self.config.api_port}")

                # Frontend port from services.frontend.port
                if "frontend" in services and isinstance(services["frontend"], dict) and "port" in services["frontend"]:
                    self.config.frontend_port = services["frontend"]["port"]
                    logger.debug(f"Loaded frontend port from services config: {self.config.frontend_port}")

                # PostgreSQL port from database.port (if in services section)
                if "database" in data and isinstance(data["database"], dict) and "port" in data["database"]:
                    self.config.postgres_port = data["database"]["port"]
                    logger.debug(f"Loaded PostgreSQL port from database config: {self.config.postgres_port}")

                logger.info(f"Loaded port configuration from {self.config_path}")
                return True

            # Fallback: old 'server' structure
            if "server" in data:
                server = data["server"]

                # Handle both flat and nested structures
                # Flat structure (v2.0): server.port
                if "port" in server and isinstance(server["port"], int):
                    self.config.api_port = server["port"]
                    logger.debug(f"Loaded unified server port from config: {self.config.api_port}")

                # Nested structure: server.api.port
                if "api" in server and isinstance(server["api"], dict) and "port" in server["api"]:
                    self.config.api_port = server["api"]["port"]
                    logger.debug(f"Loaded API port from config: {self.config.api_port}")

                # Frontend port
                if "frontend_port" in server:
                    self.config.frontend_port = server["frontend_port"]
                elif "dashboard" in server and isinstance(server["dashboard"], dict) and "port" in server["dashboard"]:
                    self.config.frontend_port = server["dashboard"]["port"]

                logger.info(f"Loaded port configuration from {self.config_path}")
                return True

            logger.debug("No 'services' or 'server' section found in config")
            return False

        except (OSError, ValueError):
            logger.exception("Error loading port configuration from {self.config_path}")
            return False

    def load_from_environment(self) -> bool:
        """
        Load port configuration from environment variables.

        Supports multiple environment variable formats for compatibility:
        - GILJO_PORT / GILJO_API_PORT / GILJO_MCP_API_PORT
        - GILJO_FRONTEND_PORT / GILJO_MCP_DASHBOARD_PORT
        - POSTGRES_PORT / DB_PORT

        Returns:
            True if any environment variables were loaded
        """
        loaded = False

        # API port (multiple names for compatibility)
        api_port_vars = ["GILJO_PORT", "GILJO_API_PORT", "GILJO_MCP_API_PORT"]
        for var_name in api_port_vars:
            if port_str := os.getenv(var_name):
                try:
                    port = int(port_str)
                    if 1024 <= port <= 65535:
                        self.config.api_port = port
                        logger.info(f"Loaded API port from {var_name}: {port}")
                        loaded = True
                        break
                except ValueError:
                    logger.warning(f"Invalid port value in {var_name}: {port_str}")

        # Frontend port
        frontend_port_vars = ["GILJO_FRONTEND_PORT", "GILJO_MCP_DASHBOARD_PORT"]
        for var_name in frontend_port_vars:
            if port_str := os.getenv(var_name):
                try:
                    port = int(port_str)
                    if 1024 <= port <= 65535:
                        self.config.frontend_port = port
                        logger.info(f"Loaded frontend port from {var_name}: {port}")
                        loaded = True
                        break
                except ValueError:
                    logger.warning(f"Invalid port value in {var_name}: {port_str}")

        # PostgreSQL port
        if port_str := os.getenv("POSTGRES_PORT") or os.getenv("DB_PORT"):
            try:
                port = int(port_str)
                if 1024 <= port <= 65535:
                    self.config.postgres_port = port
                    logger.info(f"Loaded PostgreSQL port from environment: {port}")
                    loaded = True
            except ValueError:
                logger.warning(f"Invalid PostgreSQL port value: {port_str}")

        return loaded

    def load_configuration(self) -> PortConfiguration:
        """
        Load port configuration from all sources with proper priority.

        Priority order:
        1. Environment variables (highest)
        2. config.yaml file
        3. Defaults (lowest)

        Returns:
            PortConfiguration with resolved ports
        """
        # Start with defaults (already in self.config)

        # Load from config file (overrides defaults)
        self.load_from_config_file()

        # Load from environment (overrides config file)
        self.load_from_environment()

        logger.info(
            f"Port configuration loaded - API: {self.config.api_port}, "
            f"Frontend: {self.config.frontend_port}, "
            f"PostgreSQL: {self.config.postgres_port}"
        )

        return self.config

    def get_api_port(self, check_availability: bool = False) -> int:
        """
        Get the API server port.

        Args:
            check_availability: If True, verify port is available or find alternative

        Returns:
            API port number
        """
        if not check_availability:
            return self.config.api_port

        return self.find_available_port(self.config.api_port, self.config.api_alternatives)

    def get_frontend_port(self, check_availability: bool = False) -> int:
        """
        Get the frontend development server port.

        Args:
            check_availability: If True, verify port is available or find alternative

        Returns:
            Frontend port number
        """
        if not check_availability:
            return self.config.frontend_port

        return self.find_available_port(self.config.frontend_port, self.config.frontend_alternatives)


# Convenience functions
def get_port_manager(config_path: Path | None = None) -> PortManager:
    """
    Get a PortManager instance with configuration loaded.

    Args:
        config_path: Optional path to config.yaml

    Returns:
        Configured PortManager instance
    """
    manager = PortManager(config_path)
    manager.load_configuration()
    return manager


def get_api_port(config_path: Path | None = None, check_availability: bool = False) -> int:
    """
    Convenience function to get API port.

    Args:
        config_path: Optional path to config.yaml
        check_availability: If True, ensure port is available

    Returns:
        API port number
    """
    manager = get_port_manager(config_path)
    return manager.get_api_port(check_availability)


def get_frontend_port(config_path: Path | None = None, check_availability: bool = False) -> int:
    """
    Convenience function to get frontend port.

    Args:
        config_path: Optional path to config.yaml
        check_availability: If True, ensure port is available

    Returns:
        Frontend port number
    """
    manager = get_port_manager(config_path)
    return manager.get_frontend_port(check_availability)
