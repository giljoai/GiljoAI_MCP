"""
Mock utilities for installer testing
"""

from typing import Any, Optional
from unittest.mock import Mock, patch


class MockProcess:
    """Mock subprocess.Popen result"""

    def __init__(self, returncode: int = 0, stdout: str = "", stderr: str = ""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        self.args = []

    def communicate(self, input=None):
        return self.stdout.encode() if isinstance(self.stdout, str) else self.stdout, (
            self.stderr.encode() if isinstance(self.stderr, str) else self.stderr
        )

    def wait(self):
        return self.returncode


class MockSubprocessResult:
    """Mock subprocess.run result"""

    def __init__(self, returncode: int = 0, stdout: str = "", stderr: str = ""):
        self.returncode = returncode
        self.stdout = stdout.encode() if isinstance(stdout, str) else stdout
        self.stderr = stderr.encode() if isinstance(stderr, str) else stderr
        self.args = []


class MockDatabaseConnection:
    """Mock database connection for testing"""

    def __init__(self, should_fail: bool = False, version: str = "15.4"):
        self.should_fail = should_fail
        self.version = version
        self.closed = False
        self.cursor_result = None

    def cursor(self):
        if self.should_fail:
            raise Exception("Connection failed")

        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = [f"PostgreSQL {self.version}"]
        mock_cursor.execute = Mock()
        mock_cursor.close = Mock()
        return mock_cursor

    def close(self):
        self.closed = True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class MockRedisConnection:
    """Mock Redis connection for testing"""

    def __init__(self, should_fail: bool = False):
        self.should_fail = should_fail
        self.closed = False

    def ping(self):
        if self.should_fail:
            raise Exception("Redis connection failed")
        return True

    def info(self):
        if self.should_fail:
            raise Exception("Redis info failed")
        return {"redis_version": "7.0.0", "used_memory": 1048576, "connected_clients": 1, "uptime_in_seconds": 3600}

    def close(self):
        self.closed = True


class MockDockerClient:
    """Mock Docker client for testing"""

    def __init__(self, should_fail: bool = False):
        self.should_fail = should_fail
        self.containers = Mock()
        self.images = Mock()

    def version(self):
        if self.should_fail:
            raise Exception("Docker daemon not available")
        return {"Version": "24.0.0", "ApiVersion": "1.43", "Os": "linux", "Arch": "amd64"}

    def close(self):
        pass


class MockSocket:
    """Mock socket for port testing"""

    def __init__(self, should_fail: bool = False):
        self.should_fail = should_fail
        self.closed = False

    def settimeout(self, timeout):
        pass

    def connect_ex(self, address):
        # Return 0 if connection successful (port in use), non-zero if available
        if self.should_fail:
            return 1  # Port available
        return 0  # Port in use

    def close(self):
        self.closed = True


def mock_subprocess_run(command: list[str], **kwargs) -> MockProcess:
    """Mock subprocess.run based on command"""
    cmd = " ".join(command) if isinstance(command, list) else command

    # PostgreSQL commands
    if "psql" in cmd or "pg_ctl" in cmd:
        if "version" in cmd:
            return MockProcess(0, "psql (PostgreSQL) 15.4")
        if "status" in cmd:
            return MockProcess(0, "pg_ctl: server is running")
        return MockProcess(0, "OK")

    # Redis commands
    if "redis-server" in cmd or "redis-cli" in cmd:
        if "version" in cmd:
            return MockProcess(0, "Redis server v=7.0.0")
        if "ping" in cmd:
            return MockProcess(0, "PONG")
        return MockProcess(0, "OK")

    # Docker commands
    if "docker" in cmd:
        if "version" in cmd:
            return MockProcess(0, "24.0.0")
        if "ps" in cmd:
            return MockProcess(0, "CONTAINER ID   IMAGE   COMMAND   CREATED   STATUS   PORTS   NAMES")
        return MockProcess(0, "OK")

    # Service commands
    if "systemctl" in cmd or "sc" in cmd or "launchctl" in cmd:
        if "is-active" in cmd or "query" in cmd:
            return MockProcess(0, "active")
        return MockProcess(0, "OK")

    # Default success
    return MockProcess(0, "OK")


def mock_shutil_which(command: str) -> Optional[str]:
    """Mock shutil.which to simulate command availability"""
    available_commands = {
        "psql": "/usr/bin/psql",
        "pg_ctl": "/usr/bin/pg_ctl",
        "redis-server": "/usr/bin/redis-server",
        "redis-cli": "/usr/bin/redis-cli",
        "docker": "/usr/bin/docker",
        "systemctl": "/usr/bin/systemctl",
        "sc": "C:\\Windows\\System32\\sc.exe",
        "launchctl": "/bin/launchctl",
    }
    return available_commands.get(command)


class MockFileSystem:
    """Mock file system operations"""

    def __init__(self):
        self.files: dict[str, str] = {}
        self.dirs: set[str] = set()

    def write_file(self, path: str, content: str):
        self.files[path] = content

    def read_file(self, path: str) -> str:
        return self.files.get(path, "")

    def exists(self, path: str) -> bool:
        return path in self.files or path in self.dirs

    def mkdir(self, path: str):
        self.dirs.add(path)


def create_mock_patches() -> dict[str, Any]:
    """Create common mock patches for testing"""
    return {
        "subprocess.run": mock_subprocess_run,
        "subprocess.Popen": lambda *args, **kwargs: MockProcess(),
        "shutil.which": mock_shutil_which,
        "psycopg2.connect": lambda *args, **kwargs: MockDatabaseConnection(),
        "redis.Redis": lambda *args, **kwargs: MockRedisConnection(),
        "docker.from_env": lambda: MockDockerClient(),
        "socket.socket": lambda *args, **kwargs: MockSocket(),
        "pathlib.Path.exists": lambda self: True,
        "pathlib.Path.mkdir": lambda self, **kwargs: None,
        "pathlib.Path.write_text": lambda self, content: None,
        "pathlib.Path.read_text": lambda self: "mock content",
    }


def patch_network_calls():
    """Patch network-related calls for offline testing"""

    def mock_connect_ex(address):
        _host, port = address
        # Simulate some ports as in use, others as available
        in_use_ports = {5432, 6379}  # PostgreSQL, Redis
        return 0 if port in in_use_ports else 1

    return patch("socket.socket")


def patch_installer_dependencies():
    """Patch installer dependencies for testing"""
    patches = []

    # Mock external processes
    patches.append(patch("subprocess.run", side_effect=mock_subprocess_run))
    patches.append(patch("subprocess.Popen", return_value=MockProcess()))

    # Mock command availability
    patches.append(patch("shutil.which", side_effect=mock_shutil_which))

    # Mock database connections
    patches.append(patch("psycopg2.connect", return_value=MockDatabaseConnection()))
    patches.append(patch("redis.Redis", return_value=MockRedisConnection()))
    patches.append(patch("docker.from_env", return_value=MockDockerClient()))

    # Mock file system operations
    patches.append(patch("pathlib.Path.exists", return_value=True))
    patches.append(patch("pathlib.Path.mkdir"))
    patches.append(patch("pathlib.Path.write_text"))

    return patches


class TestDataGenerator:
    """Generate test data for various scenarios"""

    @staticmethod
    def create_env_content(profile: str = "developer") -> str:
        """Generate .env file content for testing"""
        from tests.installer.fixtures.test_configs import SAMPLE_CONFIGS

        config = SAMPLE_CONFIGS.get(profile, SAMPLE_CONFIGS["developer"])

        lines = ["# Test configuration"]
        for key, value in config.items():
            if isinstance(value, bool):
                value = "true" if value else "false"
            lines.append(f"{key}={value}")

        return "\n".join(lines)

    @staticmethod
    def create_invalid_config() -> dict[str, Any]:
        """Create invalid configuration for testing validation"""
        return {
            "API_PORT": 99999,  # Invalid port
            "AUTH_ENABLED": True,
            "AUTH_METHOD": "api_key",
            # Missing required API_KEY
            "DATABASE_URL": "invalid://url",
            "LOG_LEVEL": "INVALID_LEVEL",
        }
