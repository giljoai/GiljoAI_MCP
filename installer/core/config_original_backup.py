"""
Configuration file generation for .env and config.yaml
Handles both localhost and server mode configurations
"""

import os
import platform
import yaml
import logging
from pathlib import Path
from typing import Dict, Any
from datetime import datetime


class ConfigManager:
    """Generate and manage configuration files"""

    def __init__(self, settings: Dict[str, Any]):
        self.settings = settings
        self.mode = settings.get('mode', 'localhost')
        self.logger = logging.getLogger(self.__class__.__name__)

        # Allow override of file paths for testing
        self.config_file = Path("config.yaml")
        self.env_file = Path(".env")

    def generate_all(self) -> Dict[str, Any]:
        """Generate all configuration files"""
        result = {'success': False, 'errors': []}

        try:
            # Generate .env file
            self.logger.info("Generating .env file...")
            env_result = self.generate_env_file()
            if not env_result['success']:
                result['errors'].extend(env_result.get('errors', []))
                return result

            # Generate config.yaml
            self.logger.info("Generating config.yaml...")
            yaml_result = self.generate_config_yaml()
            if not yaml_result['success']:
                result['errors'].extend(yaml_result.get('errors', []))
                return result

            # Generate additional configs for server mode
            if self.mode == 'server':
                server_result = self.generate_server_configs()
                if not server_result['success']:
                    result['errors'].extend(server_result.get('errors', []))
                    return result

            result['success'] = True
            self.logger.info("All configuration files generated successfully")
            return result

        except Exception as e:
            result['errors'].append(str(e))
            self.logger.error(f"Configuration generation failed: {e}")
            return result

    def generate_env(self) -> Dict[str, Any]:
        """Alias for generate_env_file for testing compatibility"""
        return self.generate_env_file()

    def generate_config(self) -> Dict[str, Any]:
        """Alias for generate_config_yaml for testing compatibility"""
        return self.generate_config_yaml()

    def generate_env_file(self) -> Dict[str, Any]:
        """Generate .env file with secure defaults"""
        result = {'success': False, 'errors': []}

        try:
            # Get database credentials
            owner_password = self.settings.get('owner_password', 'change_me')
            user_password = self.settings.get('user_password', 'change_me')

            env_content = f"""# GiljoAI MCP Environment Configuration
# Generated: {datetime.now().isoformat()}
# Mode: {self.mode}

# Database Configuration
POSTGRES_HOST={self.settings.get('pg_host', 'localhost')}
POSTGRES_PORT={self.settings.get('pg_port', 5432)}
POSTGRES_DB=giljo_mcp
POSTGRES_USER=giljo_user
POSTGRES_PASSWORD={user_password}

# Database Owner (for migrations only)
POSTGRES_OWNER_USER=giljo_owner
POSTGRES_OWNER_PASSWORD={owner_password}

# Environment Settings
ENVIRONMENT={'development' if self.mode == 'localhost' else 'production'}
DEBUG={'True' if self.mode == 'localhost' else 'False'}
LOG_LEVEL={'DEBUG' if self.mode == 'localhost' else 'INFO'}

# Service Ports
API_PORT={self.settings.get('api_port', 8000)}
WEBSOCKET_PORT={self.settings.get('ws_port', 7273)}
DASHBOARD_PORT={self.settings.get('dashboard_port', 7274)}

# Service Binding
SERVICE_BIND={self.settings.get('bind', '127.0.0.1' if self.mode == 'localhost' else '0.0.0.0')}

# Security
SECRET_KEY={self.generate_secret_key()}
JWT_SECRET={self.generate_secret_key()}
SESSION_SECRET={self.generate_secret_key()}

# CORS Settings
CORS_ORIGINS={'["http://localhost:3000"]' if self.mode == 'localhost' else '["*"]'}

# Feature Flags
ENABLE_SSL={'false' if self.mode == 'localhost' else str(self.settings.get('features', {}).get('ssl', False)).lower()}
ENABLE_API_KEYS={'false' if self.mode == 'localhost' else str(self.settings.get('features', {}).get('api_keys', False)).lower()}
ENABLE_MULTI_USER={'false' if self.mode == 'localhost' else str(self.settings.get('features', {}).get('multi_user', False)).lower()}

# Paths
DATA_DIR=./data
LOGS_DIR=./logs
UPLOAD_DIR=./uploads
TEMP_DIR=./temp

# Performance
WORKER_COUNT={'1' if self.mode == 'localhost' else '4'}
CONNECTION_POOL_SIZE={'5' if self.mode == 'localhost' else '20'}
"""

            # Add server-specific settings
            if self.mode == 'server':
                env_content += f"""
# Server Mode Settings
ADMIN_USER={self.settings.get('admin_username', 'admin')}
ADMIN_EMAIL={self.settings.get('admin_email', 'admin@localhost')}
SERVER_NAME={self.settings.get('server_name', 'GiljoAI MCP Server')}
ALLOWED_HOSTS={self.settings.get('allowed_hosts', '["*"]')}

# SSL Configuration
SSL_CERT_PATH={self.settings.get('ssl_cert_path', '')}
SSL_KEY_PATH={self.settings.get('ssl_key_path', '')}
"""

            # Write .env file (use configured path)
            self.env_file.write_text(env_content)

            # Set restrictive permissions on Unix
            if platform.system() != "Windows":
                os.chmod(self.env_file, 0o600)

            result['success'] = True
            self.logger.info(f"Created .env file: {self.env_file.absolute()}")
            return result

        except Exception as e:
            result['errors'].append(str(e))
            self.logger.error(f"Failed to generate .env: {e}")
            return result

    def generate_config_yaml(self) -> Dict[str, Any]:
        """Generate config.yaml with installation details"""
        result = {'success': False, 'errors': []}

        try:
            config = {
                'installation': {
                    'version': '2.0.0',
                    'mode': self.mode,
                    'timestamp': datetime.now().isoformat(),
                    'platform': platform.system(),
                    'python_version': platform.python_version()
                },
                'database': {
                    'type': 'postgresql',
                    'version': '18',
                    'host': self.settings.get('pg_host', 'localhost'),
                    'port': self.settings.get('pg_port', 5432),
                    'name': 'giljo_mcp',
                    'user': 'giljo_user',
                    'pool_size': 5 if self.mode == 'localhost' else 20
                },
                'services': {
                    'bind': self.settings.get('bind', '127.0.0.1' if self.mode == 'localhost' else '0.0.0.0'),
                    'api_port': self.settings.get('api_port', 8000),
                    'websocket_port': self.settings.get('ws_port', 7273),
                    'dashboard_port': self.settings.get('dashboard_port', 7274)
                },
                'features': {
                    'auto_start_browser': self.settings.get('open_browser', True),
                    'ssl_enabled': self.settings.get('features', {}).get('ssl', False),
                    'api_keys_required': self.settings.get('features', {}).get('api_keys', False),
                    'multi_user': self.settings.get('features', {}).get('multi_user', False)
                },
                'paths': {
                    'data': './data',
                    'logs': './logs',
                    'uploads': './uploads',
                    'temp': './temp',
                    'static': './frontend/static',
                    'templates': './frontend/templates'
                },
                'logging': {
                    'level': 'DEBUG' if self.mode == 'localhost' else 'INFO',
                    'file': './logs/giljo.log',
                    'max_size': '10MB',
                    'backup_count': 5
                },
                'status': {
                    'installation_complete': True,
                    'database_created': True,
                    'migrations_run': False,  # Will be updated after migrations
                    'ready_to_launch': True
                }
            }

            # Add server-specific configuration
            if self.mode == 'server':
                config['server'] = {
                    'admin_user': self.settings.get('admin_username', 'admin'),
                    'allowed_ips': self.settings.get('allowed_ips', []),
                    'rate_limiting': {
                        'enabled': True,
                        'requests_per_minute': 60
                    },
                    'session': {
                        'timeout_minutes': 30,
                        'remember_me_days': 30
                    }
                }

                if config['features']['ssl_enabled']:
                    config['ssl'] = {
                        'cert_path': self.settings.get('ssl_cert_path', './certs/server.crt'),
                        'key_path': self.settings.get('ssl_key_path', './certs/server.key'),
                        'self_signed': self.settings.get('ssl', {}).get('type') == 'self-signed'
                    }

            # Write config.yaml (use configured path)
            with open(self.config_file, 'w') as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)

            result['success'] = True
            self.logger.info(f"Created config.yaml: {self.config_file.absolute()}")
            return result

        except Exception as e:
            result['errors'].append(str(e))
            self.logger.error(f"Failed to generate config.yaml: {e}")
            return result

    def generate_server_configs(self) -> Dict[str, Any]:
        """Generate additional configuration files for server mode"""
        result = {'success': False, 'errors': []}

        try:
            # Generate nginx config example
            self.generate_nginx_config()

            # Generate systemd service file
            self.generate_systemd_service()

            # Generate API keys file if enabled
            if self.settings.get('features', {}).get('api_keys', False):
                self.generate_api_keys()

            result['success'] = True
            return result

        except Exception as e:
            result['errors'].append(str(e))
            self.logger.error(f"Failed to generate server configs: {e}")
            return result

    def generate_nginx_config(self):
        """Generate example nginx configuration"""
        nginx_config = f"""# GiljoAI MCP Nginx Configuration Example
# Place this in /etc/nginx/sites-available/giljo-mcp

upstream giljo_api {{
    server 127.0.0.1:{self.settings.get('api_port', 8000)};
}}

upstream giljo_websocket {{
    server 127.0.0.1:{self.settings.get('ws_port', 7273)};
}}

server {{
    listen 80;
    server_name _;  # Replace with your domain

    # Dashboard
    location / {{
        proxy_pass http://127.0.0.1:{self.settings.get('dashboard_port', 7274)};
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}

    # API
    location /api {{
        proxy_pass http://giljo_api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}

    # WebSocket
    location /ws {{
        proxy_pass http://giljo_websocket;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}
}}
"""
        config_dir = Path("installer/configs")
        config_dir.mkdir(exist_ok=True)

        nginx_path = config_dir / "nginx.conf.example"
        nginx_path.write_text(nginx_config)
        self.logger.info(f"Generated nginx config example: {nginx_path}")

    def generate_systemd_service(self):
        """Generate systemd service file"""
        service_content = f"""[Unit]
Description=GiljoAI MCP Service
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=simple
User=giljo
Group=giljo
WorkingDirectory=/opt/giljo-mcp
Environment="PATH=/opt/giljo-mcp/venv/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=/opt/giljo-mcp/venv/bin/python /opt/giljo-mcp/launchers/start_giljo.py
Restart=always
RestartSec=10

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
            'keys': [
                {
                    'name': 'default',
                    'key': secrets.token_urlsafe(32),
                    'created': datetime.now().isoformat(),
                    'permissions': ['read', 'write']
                }
            ]
        }

        keys_path = Path("api_keys.yaml")
        with open(keys_path, 'w') as f:
            yaml.dump(api_keys, f, default_flow_style=False)

        # Secure the file
        if platform.system() != "Windows":
            os.chmod(keys_path, 0o600)

        self.logger.info(f"Generated API keys file: {keys_path}")

    def generate_secret_key(self, length: int = 32) -> str:
        """Generate a secure random secret key"""
        import secrets
        return secrets.token_urlsafe(length)
