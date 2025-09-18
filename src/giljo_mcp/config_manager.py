"""
Enhanced Configuration Manager for GiljoAI MCP.

This module provides a robust configuration system that:
- Loads configuration from YAML files
- Supports environment variable overrides
- Implements mode detection (local/LAN/WAN)
- Validates configuration on load
- Provides smart defaults
- Supports hot-reloading of configuration
"""

import ipaddress
import logging
import os
import socket
import threading
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional

import yaml
from watchdog.events import FileModifiedEvent, FileSystemEventHandler
from watchdog.observers import Observer

# Import from centralized exceptions
from .exceptions import ConfigValidationError


logger = logging.getLogger(__name__)


class DeploymentMode(Enum):
    """Deployment modes for the application."""

    LOCAL = "local"  # Single machine, localhost only
    LAN = "lan"  # Local network, API key auth
    WAN = "wan"  # Internet accessible, OAuth/TLS


@dataclass
class ServerConfig:
    """Server configuration settings."""

    mode: DeploymentMode = DeploymentMode.LOCAL
    debug: bool = False

    # MCP Server
    mcp_host: str = "127.0.0.1"
    mcp_port: int = 6001
    mcp_transport: str = "stdio"

    # REST API  
    api_host: str = "127.0.0.1"
    api_port: int = 8000  # Production default from tests
    api_cors_enabled: bool = True
    api_key: Optional[str] = None

    # WebSocket
    websocket_enabled: bool = True
    websocket_port: int = 6003

    # Dashboard
    dashboard_enabled: bool = True
    dashboard_host: str = "127.0.0.1"
    dashboard_port: int = 6000
    dashboard_dev_port: int = 5173


@dataclass
class DatabaseConfig:
    """Database configuration settings."""

    type: str = "sqlite"  # sqlite or postgresql
    database_name: str = "giljo_mcp.db"
    database_url: Optional[str] = None

    # SQLite settings
    sqlite_path: Path = field(default_factory=lambda: Path("./data/giljo_mcp.db"))

    # PostgreSQL settings
    host: str = "localhost"
    port: int = 5432
    username: str = "postgres"
    password: str = ""
    pg_pool_size: int = 10

    @property
    def database_type(self) -> str:
        """Alias for type property to match test expectations."""
        return self.type

    @database_type.setter
    def database_type(self, value: str):
        """Setter for database_type alias."""
        self.type = value

    # Legacy aliases for PostgreSQL settings
    @property
    def pg_host(self) -> str:
        return self.host

    @pg_host.setter
    def pg_host(self, value: str):
        self.host = value

    @property
    def pg_port(self) -> int:
        return self.port

    @pg_port.setter
    def pg_port(self, value: int):
        self.port = value

    @property
    def pg_database(self) -> str:
        return self.database_name

    @pg_database.setter
    def pg_database(self, value: str):
        self.database_name = value

    @property
    def pg_user(self) -> str:
        return self.username

    @pg_user.setter
    def pg_user(self, value: str):
        self.username = value

    @property
    def pg_password(self) -> str:
        return self.password

    @pg_password.setter
    def pg_password(self, value: str):
        self.password = value

    def get_connection_string(self, tenant_key: Optional[str] = None) -> str:
        """
        Generate database connection string.

        Args:
            tenant_key: Optional tenant key for multi-tenant database separation
        """
        if self.database_url:
            return self.database_url

        if self.type == "sqlite":
            # Use database_name if different from default
            if self.database_name != "giljo_mcp.db":
                base_path = self.sqlite_path.parent / self.database_name
            else:
                base_path = self.sqlite_path
                
            # Support tenant-specific SQLite databases if multi-tenant enabled
            if tenant_key:
                db_path = base_path.parent / f"tenant_{tenant_key}.db"
            else:
                db_path = base_path

            db_path.parent.mkdir(parents=True, exist_ok=True)
            return f"sqlite:///{db_path.as_posix()}"
        elif self.type == "postgresql":
            # Try to use DatabaseManager's method if available
            try:
                from giljo_mcp.database import DatabaseManager

                url = DatabaseManager.build_postgresql_url(
                    host=self.host,
                    port=self.port,
                    database=(self.database_name if not tenant_key else f"{self.database_name}_{tenant_key}"),
                    username=self.username,
                    password=self.password or os.getenv("DB_PASSWORD", ""),
                )
                return url
            except ImportError:
                # Fallback to manual URL building
                password = self.password or os.getenv("DB_PASSWORD", "")
                base_url = f"postgresql://{self.username}:{password}@{self.host}:{self.port}"

                # Support tenant-specific schemas in PostgreSQL if multi-tenant enabled
                if tenant_key:
                    # Use database name with tenant suffix for complete isolation
                    return f"{base_url}/{self.database_name}_{tenant_key}"
                return f"{base_url}/{self.database_name}"
        else:
            raise ValueError(f"Unsupported database type: {self.type}")


@dataclass
class LoggingConfig:
    """Logging configuration settings."""

    level: str = "INFO"
    file: Path = field(default_factory=lambda: Path("./logs/giljo_mcp.log"))
    max_size: str = "10MB"
    max_files: int = 5

    def setup_logging(self):
        """Configure logging based on settings."""
        self.file.parent.mkdir(parents=True, exist_ok=True)

        log_level = getattr(logging, self.level.upper(), logging.INFO)

        # Configure file handler with rotation
        from logging.handlers import RotatingFileHandler

        # Parse max_size (e.g., "10MB" -> 10485760)
        size_str = self.max_size.upper()
        if size_str.endswith("MB"):
            max_bytes = int(size_str[:-2]) * 1024 * 1024
        elif size_str.endswith("KB"):
            max_bytes = int(size_str[:-2]) * 1024
        else:
            max_bytes = int(size_str)

        handler = RotatingFileHandler(self.file, maxBytes=max_bytes, backupCount=self.max_files)

        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)

        logging.basicConfig(level=log_level, handlers=[handler, logging.StreamHandler()])


@dataclass
class SessionConfig:
    """Session configuration settings."""

    timeout: int = 3600  # seconds
    max_concurrent: int = 10
    cleanup_interval: int = 300  # seconds

    # Vision chunking settings (restored from cleanup)
    vision_chunk_size: int = 50000
    vision_overlap: int = 500
    max_vision_size: int = 200000  # Maximum size before chunking required


@dataclass
class AgentConfig:
    """Agent configuration settings."""

    max_agents: int = 20
    default_context_budget: int = 150000  # tokens
    context_warning_threshold: int = 140000  # tokens

    # Legacy aliases for backwards compatibility
    @property
    def max_per_project(self) -> int:
        return self.max_agents

    @max_per_project.setter
    def max_per_project(self, value: int):
        self.max_agents = value

    @property
    def context_limit(self) -> int:
        return self.default_context_budget

    @context_limit.setter
    def context_limit(self, value: int):
        self.default_context_budget = value

    @property
    def handoff_threshold(self) -> int:
        return self.context_warning_threshold

    @handoff_threshold.setter
    def handoff_threshold(self, value: int):
        self.context_warning_threshold = value  # tokens


@dataclass
class MessageConfig:
    """Message queue configuration settings."""

    max_queue_size: int = 1000
    message_timeout: int = 300  # seconds
    max_retries: int = 3
    _batch_size: int = 10  # Internal batch size storage
    _retry_delay: float = 1.0  # Internal retry delay storage

    @property
    def batch_size(self) -> int:
        return self._batch_size

    @batch_size.setter
    def batch_size(self, value: int):
        self._batch_size = value

    @property
    def retry_attempts(self) -> int:
        return self.max_retries

    @retry_attempts.setter
    def retry_attempts(self, value: int):
        self.max_retries = value

    @property
    def retry_delay(self) -> float:
        return self._retry_delay

    @retry_delay.setter
    def retry_delay(self, value: float):
        self._retry_delay = value  # Fixed retry delay for legacy compatibility  # seconds


@dataclass
class TenantConfig:
    """Multi-tenant configuration settings."""

    enable_multi_tenant: bool = True
    default_tenant_key: Optional[str] = None
    tenant_isolation_level: str = "strict"
    key_header: str = "X-Tenant-Key"

    # Legacy alias for backwards compatibility
    @property
    def enabled(self) -> bool:
        return self.enable_multi_tenant

    @enabled.setter
    def enabled(self, value: bool):
        self.enable_multi_tenant = value

    @property
    def default_key(self) -> Optional[str]:
        return self.default_tenant_key

    @default_key.setter
    def default_key(self, value: Optional[str]):
        self.default_tenant_key = value

    @property
    def isolation_strict(self) -> bool:
        return self.tenant_isolation_level == "strict"

    @isolation_strict.setter
    def isolation_strict(self, value: bool):
        self.tenant_isolation_level = "strict" if value else "relaxed"


@dataclass
class FeatureFlags:
    """Feature flags for enabling/disabling functionality."""

    vision_chunking: bool = True
    multi_tenant: bool = True
    enable_websockets: bool = True
    auto_handoff: bool = True
    dynamic_discovery: bool = True

    # Legacy aliases for backwards compatibility
    @property
    def websocket_updates(self) -> bool:
        return self.enable_websockets

    @websocket_updates.setter
    def websocket_updates(self, value: bool):
        self.enable_websockets = value


class ConfigFileWatcher(FileSystemEventHandler):
    """Watch config file for changes and trigger reload."""

    def __init__(self, config_manager: "ConfigManager"):
        self.config_manager = config_manager

    def on_modified(self, event: FileModifiedEvent):
        if not event.is_directory and event.src_path.endswith(".yaml"):
            logger.info(f"Config file changed: {event.src_path}")
            self.config_manager.reload()


class ConfigManager:
    """
    Central configuration management for GiljoAI MCP.

    Features:
    - Hierarchical configuration (defaults -> file -> env vars)
    - Mode detection and automatic adjustment
    - Configuration validation
    - Hot-reloading support
    - Thread-safe operations
    """

    def __init__(self, config_path: Optional[Path] = None, auto_reload: bool = False):
        """
        Initialize ConfigManager.

        Args:
            config_path: Path to configuration file
            auto_reload: Enable hot-reloading of config file
        """
        self.config_path = config_path or Path("./config.yaml")
        self.auto_reload = auto_reload
        self._lock = threading.RLock()
        self._observer = None

        # Initialize configurations
        self.server = ServerConfig()
        self.database = DatabaseConfig()
        self.logging = LoggingConfig()
        self.session = SessionConfig()
        self.agent = AgentConfig()
        self.message = MessageConfig()
        self.tenant = TenantConfig()
        self.features = FeatureFlags()

        # Application metadata (restored from cleanup)
        self.app_name = "GiljoAI MCP Coding Orchestrator"
        self.app_version = "0.1.0"

        # Load configuration
        self.load()

        # Setup hot-reloading if enabled
        if auto_reload:
            self._setup_file_watcher()

    @property
    def deployment_mode(self):
        """Get deployment mode (compatibility alias for server.mode)."""
        return self.server.mode

    @deployment_mode.setter
    def deployment_mode(self, value):
        """Set deployment mode (compatibility alias for server.mode)."""
        self.server.mode = value

    def get_data_dir(self) -> Path:
        """Get application data directory (restored from cleanup)."""
        if hasattr(self, '_override_base_dir') and self._override_base_dir:
            path = self._override_base_dir / ".giljo-mcp" / "data"
        else:
            path = Path.home() / ".giljo-mcp" / "data"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def get_config_dir(self) -> Path:
        """Get configuration directory (restored from cleanup)."""
        if hasattr(self, '_override_base_dir') and self._override_base_dir:
            path = self._override_base_dir / ".giljo-mcp" / "config"
        else:
            path = Path.home() / ".giljo-mcp" / "config"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def get_log_dir(self) -> Path:
        """Get log directory (restored from cleanup)."""
        if hasattr(self, '_override_base_dir') and self._override_base_dir:
            path = self._override_base_dir / ".giljo-mcp" / "logs"
        else:
            path = Path.home() / ".giljo-mcp" / "logs"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def get_database_url(self) -> str:
        """Get database connection URL (restored from cleanup)."""
        return self.database.get_connection_string()

    def load(self):
        """Load configuration from file and environment variables."""
        with self._lock:
            # 1. Load from YAML file
            if self.config_path.exists():
                self._load_from_file()

            # 2. Override with environment variables
            self._load_from_env()

            # 3. Detect and set deployment mode
            self._detect_mode()

            # 4. Validate configuration
            self.validate()

            # 5. Apply mode-specific adjustments
            self._apply_mode_settings()

            logger.info(f"Configuration loaded: mode={self.server.mode.value}")

    def _load_from_file(self):
        """Load configuration from YAML file."""
        try:
            with open(self.config_path, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}

            # Server configuration
            if "server" in data:
                srv = data["server"]
                self.server.mode = DeploymentMode(srv.get("mode", "local"))
                self.server.debug = srv.get("debug", self.server.debug)

                if "mcp" in srv:
                    self.server.mcp_host = srv["mcp"].get("host", self.server.mcp_host)
                    self.server.mcp_port = srv["mcp"].get("port", self.server.mcp_port)
                    self.server.mcp_transport = srv["mcp"].get("transport", self.server.mcp_transport)

                if "api" in srv:
                    self.server.api_host = srv["api"].get("host", self.server.api_host)
                    self.server.api_port = srv["api"].get("port", self.server.api_port)
                    self.server.api_cors_enabled = srv["api"].get("cors_enabled", self.server.api_cors_enabled)

                if "websocket" in srv:
                    self.server.websocket_enabled = srv["websocket"].get("enabled", self.server.websocket_enabled)
                    self.server.websocket_port = srv["websocket"].get("port", self.server.websocket_port)

                if "dashboard" in srv:
                    self.server.dashboard_enabled = srv["dashboard"].get("enabled", self.server.dashboard_enabled)
                    self.server.dashboard_host = srv["dashboard"].get("host", self.server.dashboard_host)
                    self.server.dashboard_port = srv["dashboard"].get("port", self.server.dashboard_port)
                    self.server.dashboard_dev_port = srv["dashboard"].get(
                        "dev_server_port", self.server.dashboard_dev_port
                    )

            # Database configuration
            if "database" in data:
                db = data["database"]
                self.database.type = db.get("type", self.database.type)

                if "sqlite" in db:
                    self.database.sqlite_path = Path(db["sqlite"].get("path", self.database.sqlite_path))

                if "postgresql" in db:
                    pg = db["postgresql"]
                    self.database.pg_host = pg.get("host", self.database.pg_host)
                    self.database.pg_port = pg.get("port", self.database.pg_port)
                    self.database.pg_database = pg.get("database", self.database.pg_database)
                    self.database.pg_user = pg.get("user", self.database.pg_user)
                    self.database.pg_password = pg.get("password", self.database.pg_password)
                    self.database.pg_pool_size = pg.get("pool_size", self.database.pg_pool_size)

            # Logging configuration
            if "logging" in data:
                log = data["logging"]
                self.logging.level = log.get("level", self.logging.level)
                self.logging.file = Path(log.get("file", self.logging.file))
                self.logging.max_size = log.get("max_size", self.logging.max_size)
                self.logging.max_files = log.get("max_files", self.logging.max_files)

            # Session configuration
            if "session" in data:
                sess = data["session"]
                self.session.timeout = sess.get("timeout", self.session.timeout)
                self.session.max_concurrent = sess.get("max_concurrent", self.session.max_concurrent)
                self.session.cleanup_interval = sess.get("cleanup_interval", self.session.cleanup_interval)

            # Agent configuration
            if "agents" in data:
                ag = data["agents"]
                self.agent.max_per_project = ag.get("max_per_project", self.agent.max_per_project)
                self.agent.context_limit = ag.get("context_limit", self.agent.context_limit)
                self.agent.handoff_threshold = ag.get("handoff_threshold", self.agent.handoff_threshold)

            # Message configuration
            if "messages" in data:
                msg = data["messages"]
                self.message.max_queue_size = msg.get("max_queue_size", self.message.max_queue_size)
                self.message.batch_size = msg.get("batch_size", self.message.batch_size)
                self.message.retry_attempts = msg.get("retry_attempts", self.message.retry_attempts)
                self.message.retry_delay = msg.get("retry_delay", self.message.retry_delay)

            # Tenant configuration
            if "tenant" in data:
                tn = data["tenant"]
                self.tenant.enabled = tn.get("enabled", self.tenant.enabled)
                self.tenant.default_key = tn.get("default_key", self.tenant.default_key)
                self.tenant.key_header = tn.get("key_header", self.tenant.key_header)
                self.tenant.isolation_strict = tn.get("isolation_strict", self.tenant.isolation_strict)

            # Feature flags
            if "features" in data:
                feat = data["features"]
                self.features.vision_chunking = feat.get("vision_chunking", self.features.vision_chunking)
                self.features.multi_tenant = feat.get("multi_tenant", self.features.multi_tenant)
                self.features.websocket_updates = feat.get("websocket_updates", self.features.websocket_updates)
                self.features.auto_handoff = feat.get("auto_handoff", self.features.auto_handoff)
                self.features.dynamic_discovery = feat.get("dynamic_discovery", self.features.dynamic_discovery)

        except Exception as e:
            logger.exception(f"Error loading config file: {e}")
            raise ConfigValidationError(f"Failed to load config file: {e}")

    def _load_from_env(self):
        """Override configuration with environment variables."""
        # Server settings
        if mode := os.getenv("GILJO_MCP_MODE"):
            self.server.mode = DeploymentMode(mode)

        if port := os.getenv("GILJO_MCP_SERVER_PORT"):
            self.server.mcp_port = int(port)

        if port := os.getenv("GILJO_MCP_API_PORT"):
            self.server.api_port = int(port)

        if port := os.getenv("GILJO_API_PORT"):  # Alternative env var from tests
            self.server.api_port = int(port)

        if port := os.getenv("GILJO_MCP_WEBSOCKET_PORT"):
            self.server.websocket_port = int(port)

        if port := os.getenv("GILJO_MCP_DASHBOARD_PORT"):
            self.server.dashboard_port = int(port)

        if api_key := os.getenv("GILJO_MCP_API_KEY"):
            self.server.api_key = api_key

        if host := os.getenv("GILJO_API_HOST"):  # From tests
            self.server.api_host = host

        if debug := os.getenv("GILJO_DEBUG"):  # From tests
            self.server.debug = debug.lower() in ("true", "1", "yes")

        # Database settings
        if db_type := os.getenv("DB_TYPE"):
            self.database.type = db_type

        if db_type := os.getenv("GILJO_DATABASE_TYPE"):  # From tests
            self.database.type = db_type

        if db_url := os.getenv("GILJO_DATABASE_URL"):  # From tests
            self.database.database_url = db_url

        if db_host := os.getenv("DB_HOST"):
            self.database.pg_host = db_host

        if db_port := os.getenv("DB_PORT"):
            self.database.pg_port = int(db_port)

        if db_name := os.getenv("DB_NAME"):
            self.database.pg_database = db_name

        if db_user := os.getenv("DB_USER"):
            self.database.pg_user = db_user

        if db_password := os.getenv("DB_PASSWORD"):
            self.database.pg_password = db_password

        # Logging settings
        if log_level := os.getenv("LOG_LEVEL"):
            self.logging.level = log_level

        if log_file := os.getenv("LOG_FILE"):
            self.logging.file = Path(log_file)

        # Feature flags from environment
        if val := os.getenv("ENABLE_VISION_CHUNKING"):
            self.features.vision_chunking = val.lower() in ("true", "1", "yes")

        if val := os.getenv("ENABLE_MULTI_TENANT"):
            self.features.multi_tenant = val.lower() in ("true", "1", "yes")

        if val := os.getenv("ENABLE_WEBSOCKET"):
            self.features.websocket_updates = val.lower() in ("true", "1", "yes")

    def _detect_mode(self):
        """Automatically detect deployment mode based on configuration."""
        # If explicitly set, respect it
        if os.getenv("GILJO_MCP_MODE"):
            return

        # Check if we're binding to non-localhost addresses
        if self.server.api_host not in ("127.0.0.1", "localhost"):
            # Check if it's a LAN address
            try:
                ip = ipaddress.ip_address(self.server.api_host)
                if ip.is_private:
                    self.server.mode = DeploymentMode.LAN
                else:
                    self.server.mode = DeploymentMode.WAN
            except ValueError:
                # Might be a hostname, try to resolve
                try:
                    ip = socket.gethostbyname(self.server.api_host)
                    if ipaddress.ip_address(ip).is_private:
                        self.server.mode = DeploymentMode.LAN
                    else:
                        self.server.mode = DeploymentMode.WAN
                except:
                    pass

        # Check for security settings
        if self.server.api_key and self.server.mode == DeploymentMode.LOCAL:
            self.server.mode = DeploymentMode.LAN

    def _apply_mode_settings(self):
        """Apply mode-specific configuration adjustments."""
        if self.server.mode == DeploymentMode.LOCAL:
            # Local mode: localhost only, no auth required
            self.server.mcp_host = "127.0.0.1"
            self.server.api_host = "127.0.0.1"
            self.server.dashboard_host = "127.0.0.1"
            self.server.api_key = None  # No auth in local mode

        elif self.server.mode == DeploymentMode.LAN:
            # LAN mode: bind to all interfaces, require API key
            if self.server.api_host in ("127.0.0.1", "localhost"):
                self.server.api_host = "0.0.0.0"
            if self.server.dashboard_host in ("127.0.0.1", "localhost"):
                self.server.dashboard_host = "0.0.0.0"

            # Generate API key if not set
            if not self.server.api_key:
                import secrets

                self.server.api_key = secrets.token_urlsafe(32)
                logger.warning(f"Generated API key for LAN mode: {self.server.api_key}")

        elif self.server.mode == DeploymentMode.WAN:
            # WAN mode: require strong auth, recommend PostgreSQL
            if self.database.type == "sqlite":
                logger.warning("SQLite is not recommended for WAN mode. Consider using PostgreSQL.")

            if not self.server.api_key:
                raise ConfigValidationError("API key is required for WAN mode")

    def validate(self):
        """Validate configuration for correctness and consistency."""
        errors = []

        # Port validation
        ports = [
            self.server.mcp_port,
            self.server.api_port,
            self.server.websocket_port,
            self.server.dashboard_port,
        ]

        if len(ports) != len(set(ports)):
            errors.append("Port conflict: All service ports must be unique")

        for port in ports:
            if not 1024 <= port <= 65535:
                errors.append(f"Invalid port {port}: Must be between 1024 and 65535")

        # Database validation
        if self.database.type not in ("sqlite", "postgresql"):
            errors.append(f"Invalid database type: {self.database.type}")

        if self.database.type == "postgresql":
            # Only require password if no database URL is provided
            if not self.database.database_url and not self.database.pg_password and not os.getenv("DB_PASSWORD"):
                errors.append("PostgreSQL password is required")

        # Agent configuration validation
        if self.agent.handoff_threshold >= self.agent.context_limit:
            errors.append("Handoff threshold must be less than context limit")

        if self.agent.max_per_project < 1:
            errors.append("Must allow at least 1 agent per project")

        # Message configuration validation
        if self.message.retry_attempts < 0:
            errors.append("Retry attempts must be non-negative")

        if self.message.batch_size > self.message.max_queue_size:
            errors.append("Batch size cannot exceed max queue size")

        # Mode-specific validation
        if self.server.mode == DeploymentMode.WAN and not self.server.api_key:
            errors.append("API key is required for WAN mode")

        if errors:
            error_msg = "Configuration validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
            raise ConfigValidationError(error_msg)

    def reload(self):
        """Reload configuration from file and environment."""
        logger.info("Reloading configuration...")
        old_mode = self.server.mode

        try:
            self.load()

            if old_mode != self.server.mode:
                logger.warning(f"Deployment mode changed from {old_mode.value} to {self.server.mode.value}")

            logger.info("Configuration reloaded successfully")
        except Exception as e:
            logger.exception(f"Failed to reload configuration: {e}")
            raise

    def _setup_file_watcher(self):
        """Setup file watcher for hot-reloading."""
        if self._observer:
            self._observer.stop()

        self._observer = Observer()
        handler = ConfigFileWatcher(self)

        # Watch the config file's directory
        watch_dir = self.config_path.parent
        self._observer.schedule(handler, str(watch_dir), recursive=False)
        self._observer.start()

        logger.info(f"Config file watcher started for {self.config_path}")

    def stop_watching(self):
        """Stop the file watcher."""
        if self._observer:
            self._observer.stop()
            self._observer.join()
            self._observer = None

    def get_all_settings(self) -> dict[str, Any]:
        """Get all configuration settings as a dictionary."""
        return {
            "server": {
                "mode": self.server.mode.value,
                "debug": self.server.debug,
                "mcp": {
                    "host": self.server.mcp_host,
                    "port": self.server.mcp_port,
                    "transport": self.server.mcp_transport,
                },
                "api": {
                    "host": self.server.api_host,
                    "port": self.server.api_port,
                    "cors_enabled": self.server.api_cors_enabled,
                },
                "websocket": {
                    "enabled": self.server.websocket_enabled,
                    "port": self.server.websocket_port,
                },
                "dashboard": {
                    "enabled": self.server.dashboard_enabled,
                    "host": self.server.dashboard_host,
                    "port": self.server.dashboard_port,
                    "dev_server_port": self.server.dashboard_dev_port,
                },
            },
            "database": {
                "type": self.database.type,
                "sqlite": {
                    "path": str(self.database.sqlite_path),
                },
                "postgresql": {
                    "host": self.database.host,
                    "port": self.database.port,
                    "database": self.database.database_name,
                    "user": self.database.username,
                    "password": "",  # Don't save passwords to file
                    "pool_size": self.database.pg_pool_size,
                },
            },
            "logging": {
                "level": self.logging.level,
                "file": str(self.logging.file),
                "max_size": self.logging.max_size,
                "max_files": self.logging.max_files,
            },
            "session": {
                "timeout": self.session.timeout,
                "max_concurrent": self.session.max_concurrent,
                "cleanup_interval": self.session.cleanup_interval,
            },
            "agents": {
                "max_per_project": self.agent.max_per_project,
                "context_limit": self.agent.context_limit,
                "handoff_threshold": self.agent.handoff_threshold,
            },
            "messages": {
                "max_queue_size": self.message.max_queue_size,
                "batch_size": self.message.batch_size,
                "retry_attempts": self.message.retry_attempts,
                "retry_delay": self.message.retry_delay,
            },
            "tenant": {
                "enabled": self.tenant.enabled,
                "default_key": self.tenant.default_key,
                "key_header": self.tenant.key_header,
                "isolation_strict": self.tenant.isolation_strict,
            },
            "features": {
                "vision_chunking": self.features.vision_chunking,
                "multi_tenant": self.features.multi_tenant,
                "websocket_updates": self.features.websocket_updates,
                "auto_handoff": self.features.auto_handoff,
                "dynamic_discovery": self.features.dynamic_discovery,
            },
        }

    def create_database_manager(self, tenant_key: Optional[str] = None):
        """
        Create a DatabaseManager instance with current configuration.

        Args:
            tenant_key: Optional tenant key for multi-tenant database separation

        Returns:
            DatabaseManager instance configured for this environment
        """
        from giljo_mcp.database import DatabaseManager

        # Get connection string with optional tenant separation
        connection_string = self.database.get_connection_string(tenant_key)

        # Create DatabaseManager with async support for WAN mode
        is_async = self.server.mode == DeploymentMode.WAN

        return DatabaseManager(database_url=connection_string, is_async=is_async)

    def get_tenant_manager(self):
        """
        Get a TenantManager instance configured for this environment.

        Returns:
            TenantManager instance
        """
        from giljo_mcp.tenant import TenantManager

        # TenantManager uses the base database for tenant metadata
        db_manager = self.create_database_manager()

        return TenantManager(db_manager=db_manager, multi_tenant_enabled=self.features.multi_tenant)

    def save_to_file(self, path: Optional[Path] = None):
        """Save current configuration to a YAML file."""
        save_path = path or self.config_path

        with open(save_path, "w", encoding="utf-8") as f:
            yaml.dump(self.get_all_settings(), f, default_flow_style=False, sort_keys=False)

        logger.info(f"Configuration saved to {save_path}")

    @classmethod
    def load_from_file(cls, path: Path) -> "ConfigManager":
        """Load configuration from a specific file."""
        config = cls(config_path=path, auto_reload=False)
        return config

    def ensure_directories_exist(self):
        """Ensure all required directories exist."""
        self.get_data_dir()  # Creates directory
        self.get_config_dir()  # Creates directory  
        self.get_log_dir()  # Creates directory

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - stop file watcher."""
        self.stop_watching()

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by dotted key path

        Args:
            key: Dotted path to config value (e.g. 'database.url', 'server.port')
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        parts = key.split(".")
        value = self

        try:
            for part in parts:
                if hasattr(value, part):
                    value = getattr(value, part)
                else:
                    return default
            return value
        except (AttributeError, TypeError):
            return default


# Global configuration instance
_config_manager: Optional[ConfigManager] = None


def get_config() -> ConfigManager:
    """Get the global configuration manager instance."""
    global _config_manager

    if _config_manager is None:
        _config_manager = ConfigManager(auto_reload=True)
        _config_manager.logging.setup_logging()

    return _config_manager


def set_config(config: ConfigManager):
    """Set the global configuration manager instance."""
    global _config_manager
    _config_manager = config


def generate_sample_config(path: Optional[Path] = None) -> Path:
    """
    Generate a sample config.yaml file with all available options.

    Args:
        path: Optional path for the config file. Defaults to ./config.yaml

    Returns:
        Path to the generated config file
    """
    config_path = path or Path("./config.yaml")

    sample_config = {
        "server": {
            "mode": "local",  # local, lan, wan
            "mcp": {"host": "127.0.0.1", "port": 6001, "transport": "stdio"},
            "api": {"host": "127.0.0.1", "port": 6002, "cors_enabled": True},
            "websocket": {"enabled": True, "port": 6003},
            "dashboard": {
                "enabled": True,
                "host": "127.0.0.1",
                "port": 6000,
                "dev_server_port": 5173,
            },
        },
        "database": {
            "type": "sqlite",  # sqlite or postgresql
            "sqlite": {"path": "./data/giljo_mcp.db"},
            "postgresql": {
                "host": "localhost",
                "port": 5432,
                "database": "giljo_mcp_db",
                "user": "postgres",
                "password": "",  # Use DB_PASSWORD env var
                "pool_size": 10,
            },
        },
        "logging": {
            "level": "INFO",
            "file": "./logs/giljo_mcp.log",
            "max_size": "10MB",
            "max_files": 5,
        },
        "session": {"timeout": 3600, "max_concurrent": 10, "cleanup_interval": 300},
        "agents": {
            "max_per_project": 20,
            "context_limit": 150000,
            "handoff_threshold": 140000,
        },
        "messages": {
            "max_queue_size": 1000,
            "batch_size": 10,
            "retry_attempts": 3,
            "retry_delay": 1.0,
        },
        "features": {
            "vision_chunking": True,
            "multi_tenant": True,
            "websocket_updates": True,
            "auto_handoff": True,
            "dynamic_discovery": True,
        },
    }

    # Add helpful comments
    config_content = """# GiljoAI MCP Configuration
# This file configures all aspects of the GiljoAI MCP system
# Environment variables can override any setting using the format:
# GILJO_MCP_<SECTION>_<KEY> (e.g., GILJO_MCP_SERVER_MODE=lan)

"""

    # Write YAML with comments
    with open(config_path, "w", encoding="utf-8") as f:
        f.write(config_content)
        yaml.dump(sample_config, f, default_flow_style=False, sort_keys=False)

    return config_path
