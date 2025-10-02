"""
Health checker module for installation validation
"""

import os
import socket
from pathlib import Path
from typing import Tuple, Dict, Any


class HealthChecker:
    """Simple health checker for installation validation"""

    def __init__(self):
        self.root_path = Path(__file__).parent.parent

    def check_postgresql(self, should_exist: bool = False) -> Tuple[bool, str]:
        """Check PostgreSQL availability"""
        # PostgreSQL is always required now - SQLite has been completely removed
        # Always check PostgreSQL regardless of should_exist parameter

        try:
            import psycopg2
            # Try to connect to default PostgreSQL
            try:
                conn = psycopg2.connect(
                    host="localhost",
                    port=5432,
                    database="postgres",
                    user="postgres",
                    connect_timeout=3
                )
                conn.close()
                return True, "PostgreSQL is running and accessible"
            except:
                return False, "PostgreSQL is not accessible (may need to be started or installed)"
        except ImportError:
            return False, "PostgreSQL driver not installed (psycopg2)"

    def check_redis(self, should_exist: bool = False) -> Tuple[bool, str]:
        """Check Redis availability - Redis has been removed from the installation"""
        return True, "Redis not required (removed from installation)"

    def check_ports(self, config: Dict[str, Any]) -> Tuple[bool, str]:
        """Check if required ports are available"""
        ports_to_check = [
            ("API", config.get("api_port", 6002)),
            ("WebSocket", config.get("websocket_port", 6003)),
            ("Dashboard", config.get("dashboard_port", 6000)),
            ("Server", config.get("server_port", 6001))
        ]

        blocked_ports = []
        for name, port in ports_to_check:
            if self._is_port_in_use(port):
                blocked_ports.append(f"{name}:{port}")

        if blocked_ports:
            return False, f"Ports in use: {', '.join(blocked_ports)}"
        return True, "All ports configured correctly"

    def check_filesystem(self) -> Tuple[bool, str]:
        """Check file system requirements"""
        required_dirs = [
            "data",
            "logs",
            "src/giljo_mcp",
            "api"
        ]

        required_files = [
            ".env",
            "config.yaml"
        ]

        missing_dirs = []
        missing_files = []

        for dir_path in required_dirs:
            full_path = self.root_path / dir_path
            if not full_path.exists():
                missing_dirs.append(dir_path)

        for file_path in required_files:
            full_path = self.root_path / file_path
            if not full_path.exists():
                missing_files.append(file_path)

        if missing_dirs or missing_files:
            missing = []
            if missing_dirs:
                missing.append(f"dirs: {', '.join(missing_dirs)}")
            if missing_files:
                missing.append(f"files: {', '.join(missing_files)}")
            return False, f"Missing required {' and '.join(missing)}"

        return True, "All required files and directories present"

    def _is_port_in_use(self, port: int, host: str = "127.0.0.1") -> bool:
        """Check if a port is already in use"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        try:
            result = sock.connect_ex((host, port))
            return result == 0
        except:
            return False
        finally:
            sock.close()

    def check_python_version(self) -> Tuple[bool, str]:
        """Check Python version compatibility"""
        import sys
        version = sys.version_info

        if version.major < 3 or (version.major == 3 and version.minor < 10):
            return False, f"Python {version.major}.{version.minor} detected, requires 3.10+"

        return True, f"Python {version.major}.{version.minor}.{version.micro} is compatible"

    def check_dependencies(self) -> Tuple[bool, str]:
        """Check if critical dependencies are installed"""
        critical_deps = [
            'fastapi',
            'sqlalchemy',
            'pydantic',
            'httpx',
            'websockets'
        ]

        missing = []
        for dep in critical_deps:
            try:
                __import__(dep)
            except ImportError:
                missing.append(dep)

        if missing:
            return False, f"Missing dependencies: {', '.join(missing)}"

        return True, "All critical dependencies installed"

    def run_all_checks(self, profile: str = "developer") -> Dict[str, Tuple[bool, str]]:
        """Run all health checks and return results"""
        results = {}

        # Python version check
        results["Python"] = self.check_python_version()

        # Dependencies check
        results["Dependencies"] = self.check_dependencies()

        # Database checks based on profile
        if profile in ["team", "enterprise"]:
            results["PostgreSQL"] = self.check_postgresql(True)
        else:
            results["PostgreSQL"] = self.check_postgresql(False)

        # Redis check (optional for all profiles except minimal)
        # Redis removed - not checking anymore

        # Port checks
        config = {
            "api_port": 6002,
            "websocket_port": 6003,
            "dashboard_port": 6000,
            "server_port": 6001
        }
        results["Ports"] = self.check_ports(config)

        # File system checks
        results["FileSystem"] = self.check_filesystem()

        return results
