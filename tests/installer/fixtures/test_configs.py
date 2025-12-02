"""
Test configuration fixtures for installer tests
"""

import tempfile
from dataclasses import dataclass
from pathlib import Path

from tests.helpers.test_db_helper import PostgreSQLTestHelper


@dataclass
class TestEnvironment:
    """Test environment configuration"""

    temp_dir: Path
    config_dir: Path
    data_dir: Path
    logs_dir: Path

    def cleanup(self):
        """Clean up test environment"""
        import shutil

        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)


def create_test_env() -> TestEnvironment:
    """Create a temporary test environment"""
    temp_dir = Path(tempfile.mkdtemp(prefix="giljo_test_"))

    return TestEnvironment(
        temp_dir=temp_dir, config_dir=temp_dir / "config", data_dir=temp_dir / "data", logs_dir=temp_dir / "logs"
    )


# Sample configurations for testing
SAMPLE_CONFIGS = {
    "developer": {
        "APP_NAME": "GiljoAI_MCP",
        "APP_ENV": "development",
        "DEBUG": True,
        "DATABASE_URL": PostgreSQLTestHelper.get_test_db_url(async_driver=False),
        "API_PORT": 8000,
        "REDIS_ENABLED": False,
        "AUTH_ENABLED": False,
    },
    "team": {
        "APP_NAME": "GiljoAI_MCP",
        "APP_ENV": "staging",
        "DEBUG": False,
        "DATABASE_URL": "postgresql://test_user:test_pass@localhost:5432/test_db",
        "API_PORT": 8000,
        "REDIS_ENABLED": True,
        "AUTH_ENABLED": True,
        "TEAM_NAME": "Test Team",
        "TEAM_SIZE": 5,
    },
    "enterprise": {
        "APP_NAME": "GiljoAI_MCP",
        "APP_ENV": "production",
        "DEBUG": False,
        "DATABASE_URL": "postgresql://enterprise_user:secure_pass@db.example.com:5432/enterprise_db",
        "API_PORT": 8000,
        "REDIS_ENABLED": True,
        "AUTH_ENABLED": True,
        "AUTH_METHOD": "oauth",
        "ENTERPRISE_NAME": "Test Corp",
        "SECURE_COOKIES": True,
    },
}

# Connection strings for testing
TEST_CONNECTION_STRINGS = {
    "postgresql": "postgresql://test_user:test_pass@localhost:5432/test_db",
    "redis": "redis://localhost:6379/1",
}

# Mock external service responses
MOCK_RESPONSES = {
    "postgresql_version": "PostgreSQL 15.4",
    "redis_info": {"redis_version": "7.0.0", "used_memory": 1048576, "connected_clients": 1, "uptime_in_seconds": 3600},
    "docker_version": {"Version": "24.0.0", "ApiVersion": "1.43", "Os": "linux", "Arch": "amd64"},
}

# Test database configurations
TEST_DB_CONFIGS = {
    "postgresql": {
        "url": PostgreSQLTestHelper.get_test_db_url(async_driver=False),
        "type": "postgresql",
        "host": "localhost",
        "port": 5432,
        "database": "giljo_mcp_test",
        "user": "postgres",
        "password": "4010",
    },
}

# Service configuration for testing
TEST_SERVICE_CONFIGS = {
    "postgresql": {
        "name": "postgresql-test",
        "display_name": "PostgreSQL Test Server",
        "description": "PostgreSQL database server for testing",
        "executable": "pg_ctl",
        "user": "postgres",
        "dependencies": [],
    },
    "redis": {
        "name": "redis-test",
        "display_name": "Redis Test Server",
        "description": "Redis cache server for testing",
        "executable": "redis-server",
        "user": "redis",
        "dependencies": [],
    },
    "giljo": {
        "name": "giljo-mcp-test",
        "display_name": "GiljoAI MCP Test",
        "description": "GiljoAI MCP test service",
        "executable": "python",
        "args": ["-m", "giljo_mcp.main"],
        "user": "giljo",
        "dependencies": ["postgresql-test", "redis-test"],
    },
}
