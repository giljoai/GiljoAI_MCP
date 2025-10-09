"""
FIXED Configuration file generation for .env and config.yaml
Ensures perfect harmony with application expectations
"""

import os
import platform
import yaml
import logging
from pathlib import Path
from typing import Dict, Any
from datetime import datetime


class ConfigManager:
    """Generate and manage configuration files with application compatibility"""

    def __init__(self, settings: Dict[str, Any]):
        self.settings = settings
        self.mode = settings.get("mode", "local")
        self.logger = logging.getLogger(self.__class__.__name__)

        # Allow override of file paths for testing
        self.config_file = Path("config.yaml")
        self.env_file = Path(".env")

    def generate_all(self) -> Dict[str, Any]:
        """Generate all configuration files"""
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

            # Generate additional configs for server mode
            if self.mode == "server":
                server_result = self.generate_server_configs()
                if not server_result["success"]:
                    result["errors"].extend(server_result.get("errors", []))
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

    def generate_config(self) -> Dict[str, Any]:
        """Alias for generate_config_yaml for testing compatibility"""
        return self.generate_config_yaml()

    def generate_env_file(self) -> Dict[str, Any]:
        """Generate .env file with application-compatible variables"""
        result = {"success": False, "errors": []}

        try:
            # Get database credentials
            owner_password = self.settings.get("owner_password", "4010")
            user_password = self.settings.get("user_password", "4010")

            # Get configuration values with correct defaults
            pg_host = self.settings.get("pg_host", "localhost")
            pg_port = self.settings.get("pg_port", 5432)
            api_port = self.settings.get("api_port", 7272)  # FIXED: Correct default
            frontend_port = self.settings.get("dashboard_port", 7274)  # FIXED: Correct default

            # Determine bind address
            if self.mode == "local":
                bind_address = "127.0.0.1"
                api_url_host = "localhost"
            else:
                bind_address = self.settings.get("bind", "0.0.0.0")
                api_url_host = self.settings.get("server_name", "localhost")

            env_content = f"""# GiljoAI MCP Environment Configuration
# Generated: {datetime.now().isoformat()}
# Mode: {self.mode}

# =============================================================================
# PORT CONFIGURATION (v2.0 Unified Architecture)
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
# SERVER CONFIGURATION
# =============================================================================
# Deployment mode: LOCAL, LAN, or WAN
GILJO_MCP_MODE={'local' if self.mode == 'local' else 'lan'}

# API Host (0.0.0.0 for network access, 127.0.0.1 for localhost only)
GILJO_API_HOST={bind_address}
SERVICE_BIND={bind_address}

# =============================================================================
# FRONTEND CONFIGURATION
# =============================================================================
# API URL for frontend (WebSocket uses same port in v2.0)
VITE_API_URL=http://{api_url_host}:{api_port}
VITE_WS_URL=ws://{api_url_host}:{api_port}
VITE_APP_MODE={'local' if self.mode == 'local' else 'server'}
VITE_API_PORT={api_port}

# =============================================================================
# ENVIRONMENT SETTINGS
# =============================================================================
ENVIRONMENT={'development' if self.mode == 'local' else 'production'}
DEBUG={'true' if self.mode == 'local' else 'false'}
LOG_LEVEL={'DEBUG' if self.mode == 'local' else 'INFO'}
LOG_FILE=./logs/giljo_mcp.log

# =============================================================================
# SECURITY
# =============================================================================
# API Key for authentication (required for LAN/WAN modes)
GILJO_MCP_API_KEY={self.settings.get('api_key', '') if self.mode == 'server' else ''}

# Secret keys for session management
GILJO_MCP_SECRET_KEY={self.generate_secret_key()}
SECRET_KEY={self.generate_secret_key()}
JWT_SECRET={self.generate_secret_key()}
SESSION_SECRET={self.generate_secret_key()}

# =============================================================================
# CORS CONFIGURATION
# =============================================================================
CORS_ORIGINS=http://localhost:*

# =============================================================================
# FEATURE FLAGS
# =============================================================================
# Core features
ENABLE_VISION_CHUNKING=true
ENABLE_MULTI_TENANT=true
ENABLE_WEBSOCKET=true
ENABLE_AUTO_HANDOFF=true
ENABLE_DYNAMIC_DISCOVERY=true

# Security features
ENABLE_SSL={'true' if self.mode == 'server' and self.settings.get('features', {}).get('ssl', False) else 'false'}
ENABLE_API_KEYS={'true' if self.mode == 'server' else 'false'}
ENABLE_MULTI_USER={'true' if self.mode == 'server' else 'false'}

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
WORKER_COUNT={'1' if self.mode == 'local' else '4'}
CONNECTION_POOL_SIZE={'5' if self.mode == 'local' else '20'}

# =============================================================================
# DOCKER BUILD CONFIGURATION
# =============================================================================
BUILD_TARGET={'development' if self.mode == 'local' else 'production'}

# =============================================================================
# ACTIVE PRODUCT
# =============================================================================
ACTIVE_PRODUCT=GiljoAI-MCP Coding Orchestrator
"""

            # Add server-specific settings
            if self.mode == "server":
                env_content += f"""
# =============================================================================
# SERVER MODE ADDITIONAL SETTINGS
# =============================================================================
ADMIN_USER={self.settings.get('admin_username', 'admin')}
ADMIN_EMAIL={self.settings.get('admin_email', 'admin@localhost')}
SERVER_NAME={self.settings.get('server_name', 'GiljoAI MCP Server')}
ALLOWED_HOSTS={self.settings.get('allowed_hosts', '["*"]')}

# SSL Configuration
SSL_CERT_PATH={self.settings.get('ssl_cert_path', './certs/server.crt')}
SSL_KEY_PATH={self.settings.get('ssl_key_path', './certs/server.key')}

# Rate limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS_PER_MINUTE=60
"""

            # Write .env file (use configured path)
            self.env_file.write_text(env_content)

            # Set restrictive permissions on Unix
            if platform.system() != "Windows":
                os.chmod(self.env_file, 0o600)

            result["success"] = True
            self.logger.info(f"Created .env file: {self.env_file.absolute()}")
            return result

        except Exception as e:
            result["errors"].append(str(e))
            self.logger.error(f"Failed to generate .env: {e}")
            return result

    def generate_config_yaml(self) -> Dict[str, Any]:
        """Generate config.yaml with installation details"""
        result = {"success": False, "errors": []}

        try:
            # Get correct port values
            api_port = self.settings.get("api_port", 7272)
            frontend_port = self.settings.get("dashboard_port", 7274)

            # Get install directory
            install_dir = self.settings.get("install_dir", str(Path.cwd()))

            config = {
                "installation": {
                    "version": "2.0.0",
                    "mode": self.mode,
                    "timestamp": datetime.now().isoformat(),
                    "platform": platform.system(),
                    "python_version": platform.python_version(),
                    "install_dir": install_dir,
                },
                "database": {
                    "type": "postgresql",
                    "version": "16",  # Updated to match actual PostgreSQL version
                    # CRITICAL: Database host is ALWAYS localhost regardless of deployment mode
                    # The database is co-located with the backend and NEVER exposed to network
                    # This is a security principle - only the API layer is network-accessible
                    "host": self.settings.get("pg_host", "localhost"),  # ALWAYS localhost
                    "port": self.settings.get("pg_port", 5432),
                    "name": "giljo_mcp",
                    "user": "giljo_user",
                    "owner": "giljo_owner",
                    "pool_size": 5 if self.mode == "localhost" else 20,
                },
                "services": {
                    "api": {
                        # API host varies by deployment mode (this is WHERE users connect):
                        # - localhost mode: 127.0.0.1 (same machine only)
                        # - lan/server mode: Network adapter IP (e.g., 10.1.0.164) for LAN access
                        # - wan mode: Public IP or domain for internet access
                        # NOTE: Database ALWAYS remains on localhost regardless of this setting
                        "host": self.settings.get("bind", "127.0.0.1" if self.mode == "localhost" else "0.0.0.0"),
                        "port": api_port,
                        "unified_port": True,  # v2.0 uses single port for API+WebSocket
                        "description": "Main API server (REST + WebSocket + MCP)",
                    },
                    "frontend": {
                        "port": frontend_port,
                        "dev_server": True,
                        "auto_open": self.settings.get("open_browser", True),
                    },
                },
                "features": {
                    "vision_chunking": True,
                    "multi_tenant": True,
                    "websocket": True,
                    "auto_handoff": True,
                    "dynamic_discovery": True,
                    "ssl_enabled": self.settings.get("features", {}).get("ssl", False),
                    "api_keys_required": self.mode == "server",
                    "multi_user": self.mode == "server",
                },
                "paths": {
                    "install_dir": install_dir,
                    "data": str(Path(install_dir) / "data"),
                    "logs": str(Path(install_dir) / "logs"),
                    "uploads": str(Path(install_dir) / "uploads"),
                    "temp": str(Path(install_dir) / "temp"),
                    "static": str(Path(install_dir) / "frontend" / "dist"),
                    "templates": str(Path(install_dir) / "frontend" / "templates"),
                    "certs": str(Path(install_dir) / "certs") if self.mode == "server" else None,
                },
                "logging": {
                    "level": "DEBUG" if self.mode == "localhost" else "INFO",
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
                    "cookie_secure": self.mode == "server",
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

            # Add security configuration (ALWAYS included, mode-dependent settings)
            config["security"] = self._generate_security_config()

            # Add server-specific configuration
            if self.mode == "server":
                config["server"] = {
                    "admin_user": self.settings.get("admin_username", "admin"),
                    "admin_email": self.settings.get("admin_email", "admin@localhost"),
                    "allowed_ips": self.settings.get("allowed_ips", []),
                    "rate_limiting": {"enabled": True, "requests_per_minute": 60, "burst_size": 10},
                    "session": {"timeout_minutes": 30, "remember_me_days": 30, "secure_cookies": True},
                    "monitoring": {"enabled": True, "health_check_interval": 60, "metrics_enabled": True},
                }

                if config["features"]["ssl_enabled"]:
                    config["ssl"] = {
                        "cert_path": self.settings.get("ssl_cert_path", "./certs/server.crt"),
                        "key_path": self.settings.get("ssl_key_path", "./certs/server.key"),
                        "self_signed": self.settings.get("ssl", {}).get("type") == "self-signed",
                        "force_https": True,
                        "hsts_enabled": True,
                    }

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
        """Generate security configuration based on deployment mode

        Returns:
            Security configuration dictionary with CORS, API keys, and rate limiting
        """
        # Get API and frontend ports
        api_port = self.settings.get("api_port", 7272)
        frontend_port = self.settings.get("dashboard_port", 7274)

        # Build CORS allowed origins based on mode
        cors_origins = [f"http://127.0.0.1:{frontend_port}", f"http://localhost:{frontend_port}"]

        # Add server-specific CORS origins
        if self.mode == "server":
            # Get server IP if provided
            server_ip = self.settings.get("server_ip")
            if server_ip:
                cors_origins.append(f"http://{server_ip}:{frontend_port}")

            # Add custom origins if provided
            custom_origins = self.settings.get("cors_origins", [])
            cors_origins.extend(custom_origins)

            # Add comment for users to add more IPs
            # (Will be added as a YAML comment in future enhancement)

        security_config = {
            "cors": {
                "allowed_origins": cors_origins
                # Note: Do NOT use wildcards like 'http://10.1.0.*:7274' - they don't work
                # Add specific IPs instead: 'http://192.168.1.100:7274'
            },
            "api_keys": {
                # API keys required based on deployment mode
                "require_for_modes": ["server", "lan", "wan"]
                # Generate keys using: python -c "import secrets; print(f'giljo_lan_{secrets.token_urlsafe(32)}')"
            },
            "rate_limiting": {
                "enabled": True,
                "requests_per_minute": 60 if self.mode == "localhost" else 60,
                # Adjust per-endpoint limits in api/middleware.py if needed
            },
        }

        return security_config

    def generate_server_configs(self) -> Dict[str, Any]:
        """Generate additional configuration files for server mode"""
        result = {"success": False, "errors": []}

        try:
            # Generate nginx config example
            self.generate_nginx_config()

            # Generate systemd service file
            self.generate_systemd_service()

            # Generate API keys file if enabled
            if self.settings.get("features", {}).get("api_keys", False):
                self.generate_api_keys()

            result["success"] = True
            return result

        except Exception as e:
            result["errors"].append(str(e))
            self.logger.error(f"Failed to generate server configs: {e}")
            return result

    def generate_nginx_config(self):
        """Generate example nginx configuration for v2.0 unified architecture"""
        api_port = self.settings.get("api_port", 7272)
        frontend_port = self.settings.get("dashboard_port", 7274)

        nginx_config = f"""# GiljoAI MCP Nginx Configuration (v2.0)
# Place this in /etc/nginx/sites-available/giljo-mcp

upstream giljo_api {{
    server 127.0.0.1:{api_port};
    keepalive 64;
}}

upstream giljo_frontend {{
    server 127.0.0.1:{frontend_port};
}}

server {{
    listen 80;
    server_name _;  # Replace with your domain

    # Frontend (development server or static files)
    location / {{
        proxy_pass http://giljo_frontend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}

    # API endpoints
    location /api {{
        proxy_pass http://giljo_api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeouts for long-running operations
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }}

    # WebSocket (v2.0 uses same port as API)
    location /ws {{
        proxy_pass http://giljo_api;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket timeouts
        proxy_connect_timeout 7d;
        proxy_send_timeout 7d;
        proxy_read_timeout 7d;
    }}

    # Health check endpoint
    location /health {{
        proxy_pass http://giljo_api/health;
        access_log off;
    }}
}}

# HTTPS configuration (if SSL enabled)
server {{
    listen 443 ssl http2;
    server_name _;  # Replace with your domain

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    # Modern SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
    ssl_prefer_server_ciphers off;

    # HSTS
    add_header Strict-Transport-Security "max-age=63072000" always;

    # Same location blocks as above...
}}
"""
        config_dir = Path("installer/configs")
        config_dir.mkdir(exist_ok=True)

        nginx_path = config_dir / "nginx.conf.example"
        nginx_path.write_text(nginx_config)
        self.logger.info(f"Generated nginx config example: {nginx_path}")

    def generate_systemd_service(self):
        """Generate systemd service file for v2.0"""
        service_content = f"""[Unit]
Description=GiljoAI MCP Orchestrator Service
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=simple
User=giljo
Group=giljo
WorkingDirectory=/opt/giljo-mcp
Environment="PATH=/opt/giljo-mcp/venv/bin:/usr/local/bin:/usr/bin:/bin"
Environment="PYTHONPATH=/opt/giljo-mcp"

# Start the main orchestrator (handles API, WebSocket, and frontend)
ExecStart=/opt/giljo-mcp/venv/bin/python -m api.run_api

# Restart policy
Restart=always
RestartSec=10
StandardOutput=append:/var/log/giljo-mcp/service.log
StandardError=append:/var/log/giljo-mcp/error.log

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/giljo-mcp/data /opt/giljo-mcp/logs /opt/giljo-mcp/uploads

[Install]
WantedBy=multi-user.target
"""
        config_dir = Path("installer/configs")
        config_dir.mkdir(exist_ok=True)

        service_path = config_dir / "giljo-mcp.service"
        service_path.write_text(service_content)
        self.logger.info(f"Generated systemd service file: {service_path}")

    def generate_api_keys(self):
        """Generate initial API keys for server mode"""
        import secrets

        api_keys = {
            "version": "1.0",
            "keys": [
                {
                    "name": "default",
                    "key": secrets.token_urlsafe(32),
                    "created": datetime.now().isoformat(),
                    "permissions": ["read", "write", "admin"],
                    "rate_limit_override": None,
                }
            ],
        }

        keys_path = Path("api_keys.yaml")
        with open(keys_path, "w") as f:
            yaml.dump(api_keys, f, default_flow_style=False)

        # Secure the file
        if platform.system() != "Windows":
            os.chmod(keys_path, 0o600)

        self.logger.info(f"Generated API keys file: {keys_path}")
        self.logger.info(f"Default API key: {api_keys['keys'][0]['key']}")

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
            with open(self.config_file, "r") as f:
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
                preferred_tool="claude",
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
