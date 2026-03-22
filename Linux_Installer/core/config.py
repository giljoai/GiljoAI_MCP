"""
v3.0 Configuration file generation for .env and config.yaml
Unified architecture: Always binds to 0.0.0.0, firewall controls access
Authentication always enabled with IP-based auto-login for localhost
"""

import logging
import os
import platform
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


class ConfigManager:
    """
    Generate and manage configuration files for v3.0 unified architecture.

    Key v3.0 principles:
    - No deployment modes (local/server/lan/wan)
    - Always bind to 0.0.0.0 (firewall controls access)
    - Database always on localhost (security principle)
    - Authentication always enabled (IP-based auto-login for 127.0.0.1)
    - deployment_context is metadata only (not a mode)
    """

    def __init__(self, settings: Dict[str, Any]):
        self.settings = settings
        self.logger = logging.getLogger(self.__class__.__name__)

        # Allow override of file paths for testing
        self.config_file = Path("config.yaml")
        self.env_file = Path(".env")

    def generate_all(self) -> Dict[str, Any]:
        """
        Generate all configuration files for v3.0 unified architecture.

        Returns:
            Result dict with success status and any errors
        """
        result = {"success": False, "errors": []}

        try:
            # Generate .env file
            self.logger.info("Generating .env file...")
            env_result = self.generate_env_file()
            if not env_result["success"]:
                result["errors"].extend(env_result.get("errors", []))
                return result

            # Generate config.yaml
            self.logger.info("Generating config.yaml...")
            yaml_result = self.generate_config_yaml()
            if not yaml_result["success"]:
                result["errors"].extend(yaml_result.get("errors", []))
                return result

            result["success"] = True
            self.logger.info("All configuration files generated successfully")
            return result

        except Exception as e:
            result["errors"].append(str(e))
            self.logger.error(f"Configuration generation failed: {e}")
            return result

    def generate_env(self) -> Dict[str, Any]:
        """Alias for generate_env_file for testing compatibility"""
        return self.generate_env_file()

    def _read_latest_credentials(self) -> Optional[Dict[str, str]]:
        """
        Read the most recent database credentials file.

        Returns:
            Dictionary with credential keys and values, or None if not found
        """
        try:
            credentials_dir = Path("Linux_Installer/credentials")

            if not credentials_dir.exists():
                self.logger.warning(f"Credentials directory not found: {credentials_dir}")
                return None

            # Find all credential files
            credential_files = list(credentials_dir.glob("db_credentials_*.txt"))

            if not credential_files:
                self.logger.warning("No credential files found in Linux_Installer/credentials/")
                return None

            # Get the most recent file (by modification time)
            latest_file = max(credential_files, key=lambda p: p.stat().st_mtime)
            self.logger.info(f"Reading credentials from: {latest_file}")

            # Parse the credentials file
            credentials = {}
            with open(latest_file) as f:
                for line in f:
                    line = line.strip()
                    # Skip comments and empty lines
                    if not line or line.startswith("#"):
                        continue
                    # Parse key=value pairs
                    if "=" in line:
                        key, value = line.split("=", 1)
                        credentials[key.strip()] = value.strip()

            return credentials

        except Exception as e:
            self.logger.error(f"Failed to read credentials file: {e}")
            return None

    def generate_config(self) -> Dict[str, Any]:
        """Alias for generate_config_yaml for testing compatibility"""
        return self.generate_config_yaml()

    def generate_env_file(self) -> Dict[str, Any]:
        """
        Generate .env file for v3.0 unified architecture.

        v3.0 changes:
        - Always binds to 0.0.0.0 (no mode-based branching)
        - DEPLOYMENT_CONTEXT is metadata only
        - Authentication always enabled

        Returns:
            Result dict with success status and any errors
        """
        result = {"success": False, "errors": []}

        try:
            # Get database credentials - try multiple sources
            owner_password = None
            user_password = None

            # Source 1: From settings (if passed from DatabaseInstaller)
            if "owner_password" in self.settings and "user_password" in self.settings:
                owner_password = self.settings.get("owner_password")
                user_password = self.settings.get("user_password")
                self.logger.info("Using database passwords from settings")

            # Source 2: Read from most recent credentials file
            if not owner_password or not user_password:
                credentials = self._read_latest_credentials()
                if credentials:
                    owner_password = credentials.get("OWNER_PASSWORD")
                    user_password = credentials.get("USER_PASSWORD")
                    self.logger.info("Using database passwords from credentials file")

            # Source 3: Raise error if password missing (production security)
            if not owner_password:
                raise ValueError("Owner password is required - no defaults allowed for production security")
            if not user_password:
                raise ValueError("User password is required - no defaults allowed for production security")

            # Get configuration values with correct defaults
            pg_host = self.settings.get("pg_host", "localhost")  # ALWAYS localhost
            pg_port = self.settings.get("pg_port", 5432)
            api_port = self.settings.get("api_port", 7272)
            frontend_port = self.settings.get("dashboard_port", 7274)

            # v3.0: Always bind to 0.0.0.0 (firewall controls access)
            bind_address = "0.0.0.0"
            api_url_host = "localhost"  # Default for frontend connections
            ssl_enabled = self.settings.get("ssl_enabled", False)
            http_proto = "https" if ssl_enabled else "http"
            ws_proto = "wss" if ssl_enabled else "ws"

            env_content = f"""# GiljoAI MCP Environment Configuration v3.0
# Generated: {datetime.now().isoformat()}
# Deployment Context: localhost (informational only - not a mode)

# =============================================================================
# PORT CONFIGURATION (v2.0+ Unified Architecture)
# =============================================================================
# Main API Server Port (handles API + WebSocket + MCP tools)
GILJO_API_PORT={api_port}
GILJO_PORT={api_port}

# Frontend Development Server Port
GILJO_FRONTEND_PORT={frontend_port}
VITE_FRONTEND_PORT={frontend_port}

# PostgreSQL Database Port
POSTGRES_PORT={pg_port}
DB_PORT={pg_port}

# =============================================================================
# DATABASE CONFIGURATION
# =============================================================================
# PostgreSQL specific configuration
POSTGRES_HOST={pg_host}
POSTGRES_DB=giljo_mcp
POSTGRES_USER=giljo_user
POSTGRES_PASSWORD={user_password}

# Database Owner (for migrations only)
POSTGRES_OWNER_USER=giljo_owner
POSTGRES_OWNER_PASSWORD={owner_password}

# Generic database configuration (for application compatibility)
DB_TYPE=postgresql
DB_HOST={pg_host}
DB_NAME=giljo_mcp
DB_USER=giljo_user
DB_PASSWORD={user_password}

# Full database URL (optional - app will use this if present)
DATABASE_URL=postgresql://giljo_user:{user_password}@{pg_host}:{pg_port}/giljo_mcp

# =============================================================================
# SERVER CONFIGURATION (v3.0)
# =============================================================================
# Deployment context (informational only - not a mode)
DEPLOYMENT_CONTEXT=localhost

# API Host (v3.0: Always binds to 0.0.0.0, firewall controls access)
GILJO_API_HOST=0.0.0.0
SERVICE_BIND=0.0.0.0

# =============================================================================
# FRONTEND CONFIGURATION
# =============================================================================
# API URL for frontend (WebSocket uses same port in v2.0)
VITE_API_URL={http_proto}://{api_url_host}:{api_port}
VITE_WS_URL={ws_proto}://{api_url_host}:{api_port}
VITE_APP_MODE=localhost
VITE_API_PORT={api_port}

# =============================================================================
# ENVIRONMENT SETTINGS
# =============================================================================
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG
LOG_FILE=./logs/giljo_mcp.log

# =============================================================================
# SECURITY (v3.0: Authentication always enabled)
# =============================================================================
# API Key for network clients (optional - generated at runtime if needed)
GILJO_MCP_API_KEY=

# Default tenant key (generated during installation)
DEFAULT_TENANT_KEY={self.settings.get("default_tenant_key", "")}

# Secret keys for session management
GILJO_MCP_SECRET_KEY={self.generate_secret_key()}
SECRET_KEY={self.generate_secret_key()}
JWT_SECRET={self.generate_secret_key()}
SESSION_SECRET={self.generate_secret_key()}

# =============================================================================
# CORS CONFIGURATION
# =============================================================================
CORS_ORIGINS=http://localhost:*,http://127.0.0.1:*

# =============================================================================
# FEATURE FLAGS (v3.0: Core features always enabled)
# =============================================================================
# Core features
ENABLE_VISION_CHUNKING=true
ENABLE_MULTI_TENANT=true
ENABLE_WEBSOCKET=true
ENABLE_AUTO_HANDOFF=true
ENABLE_DYNAMIC_DISCOVERY=true

# Security features (v3.0: Authentication always enabled, IP-based auto-login)
ENABLE_AUTHENTICATION=true
ENABLE_AUTO_LOGIN_LOCALHOST=true
ENABLE_SSL=false
ENABLE_API_KEYS=false
ENABLE_MULTI_USER=false

# =============================================================================
# AGENT CONFIGURATION
# =============================================================================
MAX_AGENTS_PER_PROJECT=20
AGENT_CONTEXT_LIMIT=150000
AGENT_HANDOFF_THRESHOLD=140000

# =============================================================================
# SESSION CONFIGURATION
# =============================================================================
SESSION_TIMEOUT=3600
MAX_CONCURRENT_SESSIONS=10
SESSION_CLEANUP_INTERVAL=300

# =============================================================================
# MESSAGE QUEUE CONFIGURATION
# =============================================================================
MAX_QUEUE_SIZE=1000
MESSAGE_BATCH_SIZE=10
MESSAGE_RETRY_ATTEMPTS=3
MESSAGE_RETRY_DELAY=1.0

# =============================================================================
# PATHS
# =============================================================================
DATA_DIR=./data
LOGS_DIR=./logs
UPLOAD_DIR=./uploads
TEMP_DIR=./temp

# =============================================================================
# PERFORMANCE
# =============================================================================
WORKER_COUNT=1
CONNECTION_POOL_SIZE=5

# =============================================================================
# DOCKER BUILD CONFIGURATION
# =============================================================================
BUILD_TARGET=development

# =============================================================================
# ACTIVE PRODUCT
# =============================================================================
ACTIVE_PRODUCT=GiljoAI-MCP Coding Orchestrator
"""

            # Write .env file (use configured path)
            self.env_file.write_text(env_content)

            # Set restrictive permissions in Linux environments
            os.chmod(self.env_file, 0o600)

            result["success"] = True
            self.logger.info(f"Created .env file: {self.env_file.absolute()}")
            return result

        except Exception as e:
            result["errors"].append(str(e))
            self.logger.error(f"Failed to generate .env: {e}")
            return result

    def generate_config_yaml(self) -> Dict[str, Any]:
        """
        Generate config.yaml for v3.0 unified architecture.

        v3.0 changes:
        - No mode field anywhere
        - deployment_context is metadata only
        - Always bind to 0.0.0.0
        - Database always on localhost
        - Authentication always enabled

        Returns:
            Result dict with success status and any errors
        """
        result = {"success": False, "errors": []}

        try:
            # Get correct port values
            api_port = self.settings.get("api_port", 7272)
            frontend_port = self.settings.get("dashboard_port", 7274)

            # Get install directory
            install_dir = self.settings.get("install_dir", str(Path.cwd()))

            config = {
                "version": "3.0.0",  # v3.0: Unified authentication architecture
                "deployment_context": "localhost",  # Informational only (not a mode)
                "installation": {
                    # NO MODE FIELD in v3.0
                    "timestamp": datetime.now().isoformat(),
                    "platform": platform.system(),
                    "python_version": platform.python_version(),
                    "install_dir": install_dir,
                },
                "database": {
                    "type": "postgresql",
                    "version": "18",  # PostgreSQL 18
                    # CRITICAL: Database host is ALWAYS localhost (security principle)
                    # The database is co-located with the backend and NEVER exposed to network
                    # Only the API layer is network-accessible (binds to 0.0.0.0)
                    "host": "localhost",  # ALWAYS localhost (never changes)
                    "port": self.settings.get("pg_port", 5432),
                    "name": "giljo_mcp",
                    "user": "giljo_user",
                    "owner": "giljo_owner",
                    "pool_size": 5,  # v3.0: Fixed pool size (no mode-based scaling)
                },
                "server": {
                    # v3.0: Always bind to 0.0.0.0 (all interfaces)
                    # Firewall controls access (localhost-only by default)
                    "api_host": "0.0.0.0",
                    "api_port": api_port,
                    "dashboard_host": "0.0.0.0",
                    "dashboard_port": frontend_port,
                    "mcp_host": "0.0.0.0",
                    "mcp_port": api_port,  # MCP uses same port as API in v2.0+
                    "api_key": None,  # Generated on first run if needed
                },
                "services": {
                    "api": {
                        "host": "0.0.0.0",  # v3.0: Always bind all interfaces
                        "port": api_port,
                        "unified_port": True,  # v2.0 uses single port for API+WebSocket
                        "description": "Main API server (REST + WebSocket + MCP)",
                    },
                    "frontend": {
                        "port": frontend_port,
                        "dev_server": True,
                        "auto_open": self.settings.get("open_browser", True),
                    },
                    "external_host": self.settings.get("external_host", "localhost"),  # Host for frontend connections
                },
                "features": {
                    # v3.0 feature flags
                    "authentication": True,  # Always enabled in v3.0
                    "auto_login_localhost": True,  # IP-based auto-login for 127.0.0.1
                    "firewall_configured": self.settings.get("configure_firewall", False),
                    # Core features
                    "multi_tenant": True,
                    "websocket": True,
                    # Security features (optional)
                    "ssl_enabled": self.settings.get("features", {}).get("ssl", False),
                },
                "paths": {
                    "install_dir": install_dir,
                    "data": str(Path(install_dir) / "data"),
                    "logs": str(Path(install_dir) / "logs"),
                    "uploads": str(Path(install_dir) / "uploads"),
                    "temp": str(Path(install_dir) / "temp"),
                    "static": str(Path(install_dir) / "frontend" / "dist"),
                    "templates": str(Path(install_dir) / "frontend" / "templates"),
                    "certs": None,  # v3.0: SSL cert path removed (use docs for SSL setup)
                },
                "logging": {
                    "level": "DEBUG",  # v3.0: Default to DEBUG for localhost
                    "file": "./logs/giljo_mcp.log",
                    "max_size": "10MB",
                    "backup_count": 5,
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                },
                "agent": {
                    "max_per_project": 20,
                    "context_limit": 150000,
                    "handoff_threshold": 140000,
                    "default_role": "orchestrator",
                },
                "session": {
                    "timeout_seconds": 3600,
                    "max_concurrent": 10,
                    "cleanup_interval": 300,
                    "cookie_secure": False,  # v3.0: Set to False for localhost
                },
                "message_queue": {
                    "max_size": 1000,
                    "batch_size": 10,
                    "retry_attempts": 3,
                    "retry_delay": 1.0,
                    "priority_levels": ["low", "normal", "high", "critical"],
                },
                "status": {
                    "installation_complete": True,
                    "database_created": True,
                    "migrations_run": False,  # Will be updated after migrations
                    "services_configured": True,
                    "ready_to_launch": True,
                },
            }

            # Add tenant configuration (tenant key from installation)
            tenant_key = self.settings.get("default_tenant_key", "")
            if tenant_key:
                config["tenant"] = {
                    "enabled": True,
                    "default_key": tenant_key,
                    "key_header": "X-Tenant-Key",
                }

            # Add security configuration (v3.0: Always included, no mode dependency)
            config["security"] = self._generate_security_config()

            # Write config.yaml (use configured path)
            with open(self.config_file, "w") as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)

            result["success"] = True
            self.logger.info(f"Created config.yaml: {self.config_file.absolute()}")
            return result

        except Exception as e:
            result["errors"].append(str(e))
            self.logger.error(f"Failed to generate config.yaml: {e}")
            return result

    def _generate_security_config(self) -> Dict[str, Any]:
        """
        Generate security configuration for v3.0 unified architecture.

        v3.0 changes:
        - No mode-based branching
        - CORS defaults to localhost only
        - API keys optional (generated at runtime if needed)

        Returns:
            Security configuration dictionary with CORS, API keys, and rate limiting
        """
        # Get API and frontend ports
        api_port = self.settings.get("api_port", 7272)
        frontend_port = self.settings.get("dashboard_port", 7274)

        # v3.0: Default CORS to localhost only (firewall controls network access)
        cors_origins = [
            f"http://127.0.0.1:{frontend_port}",
            f"http://localhost:{frontend_port}",
            f"http://127.0.0.1:{api_port}",
            f"http://localhost:{api_port}",
        ]

        # Include installer-selected external host (LAN/WAN) for direct access
        external_host = self.settings.get("external_host", "localhost")
        if external_host and external_host not in ("localhost", "127.0.0.1"):
            external_frontend = f"http://{external_host}:{frontend_port}"
            external_api = f"http://{external_host}:{api_port}"
            if external_frontend not in cors_origins:
                cors_origins.append(external_frontend)
            if external_api not in cors_origins:
                cors_origins.append(external_api)

        # Add custom origins if provided (advanced users)
        custom_origins = self.settings.get("cors_origins", [])
        if custom_origins:
            cors_origins.extend(custom_origins)

        security_config = {
            "cors": {
                "allowed_origins": cors_origins
                # Note: Do NOT use wildcards like 'http://10.1.0.*:7274' - they don't work
                # Add specific IPs instead: 'http://192.168.1.100:7274'
            },
            "api_keys": {
                # API keys documentation (not enforced in v3.0 localhost mode)
                "info": "API keys optional for localhost (auto-login enabled)",
                "generate_command": "python -c \"import secrets; print(f'giljo_{secrets.token_urlsafe(32)}')\"",
            },
            "rate_limiting": {
                "enabled": True,
                "requests_per_minute": 60,
                # Adjust per-endpoint limits in api/middleware.py if needed
            },
        }

        return security_config

    def generate_secret_key(self, length: int = 32) -> str:
        """Generate a secure random secret key"""
        import secrets

        return secrets.token_urlsafe(length)

    def validate_config(self) -> Dict[str, Any]:
        """Validate that generated configuration is compatible with application"""
        result = {"valid": True, "issues": []}

        # Check .env file
        if self.env_file.exists():
            env_content = self.env_file.read_text()

            # Check for required variables
            required_vars = [
                "GILJO_API_PORT",
                "GILJO_PORT",
                "DB_HOST",
                "DB_NAME",
                "DB_USER",
                "DB_PASSWORD",
                "VITE_API_URL",
                "VITE_WS_URL",
            ]

            for var in required_vars:
                if f"{var}=" not in env_content:
                    result["valid"] = False
                    result["issues"].append(f"Missing required variable: {var}")
        else:
            result["valid"] = False
            result["issues"].append(".env file not found")

        # Check config.yaml
        if self.config_file.exists():
            with open(self.config_file) as f:
                config = yaml.safe_load(f)

            # Validate structure
            if "services" not in config:
                result["valid"] = False
                result["issues"].append("Missing 'services' section in config.yaml")

            if "database" not in config:
                result["valid"] = False
                result["issues"].append("Missing 'database' section in config.yaml")
        else:
            result["valid"] = False
            result["issues"].append("config.yaml file not found")

        return result


def seed_default_orchestrator_template(db_manager, tenant_key: str) -> Dict[str, Any]:
    """
    Seed the default orchestrator template for a tenant.

    Args:
        db_manager: Database manager instance
        tenant_key: Tenant key for multi-tenant isolation

    Returns:
        Result dictionary with success status
    """
    from datetime import datetime, timezone

    from src.giljo_mcp.models import AgentTemplate
    from src.giljo_mcp.template_manager import UnifiedTemplateManager

    logger = logging.getLogger(__name__)
    result = {"success": False, "errors": []}

    try:
        logger.info("Seeding default orchestrator template...")

        # Get orchestrator template from UnifiedTemplateManager
        template_mgr = UnifiedTemplateManager()
        orchestrator_content = template_mgr._legacy_templates["orchestrator"]

        # Use synchronous session (installer context)
        with db_manager.get_session() as session:
            # Check if orchestrator template already exists
            existing = (
                session.query(AgentTemplate)
                .filter(
                    AgentTemplate.tenant_key == tenant_key,
                    AgentTemplate.role == "orchestrator",
                    AgentTemplate.is_default == True,
                )
                .first()
            )

            if existing:
                logger.info("Default orchestrator template already exists")
                result["success"] = True
                result["message"] = "Template already exists"
                return result

            # Create template
            template = AgentTemplate(
                tenant_key=tenant_key,
                product_id=None,  # Global template (all products)
                name="orchestrator",
                category="role",
                role="orchestrator",
                template_content=orchestrator_content,
                variables=["project_name", "project_mission", "product_name"],
                behavioral_rules=[
                    "Coordinate all agents effectively",
                    "Ensure project goals are met through delegation",
                    "Handle conflicts and blockers",
                    "Maintain project momentum",
                    "Read vision document completely (all parts)",
                    "Challenge scope drift",
                    "Enforce 3-tool rule (delegate if using >3 tools)",
                    "Create specific missions based on discoveries",
                    "Create 3 documentation artifacts at project close",
                ],
                success_criteria=[
                    "Vision document fully read (all parts if chunked)",
                    "All product config_data reviewed",
                    "Serena MCP discoveries documented",
                    "All agents spawned with SPECIFIC missions",
                    "Project goals achieved and validated",
                    "Handoffs completed successfully",
                    "Three documentation artifacts created",
                ],
                is_default=True,  # Default orchestrator template
                is_active=True,
                description="Enhanced orchestrator template with discovery-first workflow, 30-80-10 principle, and 3-tool delegation rule",
                version="2.0.0",
                tags=["orchestrator", "discovery", "delegation", "default"],
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )

            session.add(template)
            session.commit()

            logger.info("✓ Default orchestrator template seeded successfully")
            result["success"] = True
            result["message"] = "Template seeded successfully"
            return result

    except Exception as e:
        logger.error(f"Failed to seed orchestrator template: {e}")
        result["errors"].append(str(e))
        return result
