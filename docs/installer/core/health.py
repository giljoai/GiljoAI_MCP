"""
Health Check System for GiljoAI MCP Installer

Comprehensive health checking for all system dependencies and services.
Provides fast, reliable checks with clear status reporting.
"""

import asyncio
import platform
import shutil
import socket
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional


try:
    import psycopg2

    HAS_PSYCOPG2 = True
except ImportError:
    HAS_PSYCOPG2 = False

try:
    import redis

    HAS_REDIS = True
except ImportError:
    HAS_REDIS = False

try:
    import docker

    HAS_DOCKER = True
except ImportError:
    HAS_DOCKER = False


class HealthStatus(Enum):
    """Health check status levels"""

    HEALTHY = "healthy"
    WARNING = "warning"
    ERROR = "error"
    UNKNOWN = "unknown"
    NOT_INSTALLED = "not_installed"


@dataclass
class ComponentHealth:
    """Health status for a single component"""

    name: str
    status: HealthStatus
    message: str
    details: dict[str, Any] = field(default_factory=dict)
    check_time: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "details": self.details,
            "check_time": self.check_time,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class HealthReport:
    """Comprehensive health check report"""

    overall_status: HealthStatus
    components: list[ComponentHealth]
    total_check_time: float
    timestamp: datetime = field(default_factory=datetime.now)
    system_info: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "overall_status": self.overall_status.value,
            "components": [c.to_dict() for c in self.components],
            "total_check_time": self.total_check_time,
            "timestamp": self.timestamp.isoformat(),
            "system_info": self.system_info,
        }

    def get_summary(self) -> str:
        """Get human-readable summary"""
        lines = [
            f"Health Check Report - {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
            f"Overall Status: {self.overall_status.value.upper()}",
            f"Total Check Time: {self.total_check_time:.2f}s",
            "",
            "Component Status:",
        ]

        for comp in self.components:
            # Use ASCII-safe symbols for better compatibility
            status_symbol = {
                HealthStatus.HEALTHY: "[OK]",
                HealthStatus.WARNING: "[WARN]",
                HealthStatus.ERROR: "[ERR]",
                HealthStatus.UNKNOWN: "[?]",
                HealthStatus.NOT_INSTALLED: "[N/A]",
            }.get(comp.status, "[?]")

            lines.append(f"  {status_symbol} {comp.name}: {comp.message} ({comp.check_time:.3f}s)")

            if comp.details:
                for key, value in comp.details.items():
                    lines.append(f"    - {key}: {value}")

        return "\n".join(lines)


class HealthChecker:
    """Main health checker for system dependencies"""

    def __init__(self, config: Optional[dict[str, Any]] = None):
        """Initialize health checker with optional configuration"""
        self.config = config or {}
        self.components: list[ComponentHealth] = []

    async def check_database_services(self) -> HealthReport:
        """
        Quick check for database services (PostgreSQL and Redis)

        Returns:
            Health report focused on database services
        """
        return await self.check_all(["postgresql", "redis", "ports"])

    async def check_installation_readiness(self) -> HealthReport:
        """
        Check if system is ready for installation

        Returns:
            Health report for installation prerequisites
        """
        return await self.check_all(["system", "python", "network", "ports"])

    async def check_all(self, components: Optional[list[str]] = None) -> HealthReport:
        """
        Run all health checks or specified components

        Args:
            components: Optional list of component names to check

        Returns:
            Comprehensive health report
        """
        start_time = time.time()
        self.components = []

        # Determine which checks to run
        if components:
            checks_to_run = components
        else:
            checks_to_run = ["system", "postgresql", "redis", "docker", "ports", "services", "python", "network"]

        # Run checks
        check_tasks = []
        for check_name in checks_to_run:
            if check_name == "system":
                check_tasks.append(self._check_system())
            elif check_name == "postgresql":
                check_tasks.append(self._check_postgresql())
            elif check_name == "redis":
                check_tasks.append(self._check_redis())
            elif check_name == "docker":
                check_tasks.append(self._check_docker())
            elif check_name == "ports":
                check_tasks.append(self._check_ports())
            elif check_name == "services":
                check_tasks.append(self._check_services())
            elif check_name == "python":
                check_tasks.append(self._check_python())
            elif check_name == "network":
                check_tasks.append(self._check_network())

        # Execute all checks concurrently
        if check_tasks:
            await asyncio.gather(*check_tasks, return_exceptions=True)

        # Determine overall status
        overall_status = self._calculate_overall_status()

        # Create report
        report = HealthReport(
            overall_status=overall_status,
            components=self.components,
            total_check_time=time.time() - start_time,
            system_info=self._get_system_info(),
        )

        return report

    async def _check_system(self) -> None:
        """Check basic system requirements"""
        start_time = time.time()

        try:
            details = {
                "platform": platform.system(),
                "version": platform.version(),
                "architecture": platform.machine(),
                "python_version": platform.python_version(),
            }

            # Check disk space
            home_path = Path.home()
            if home_path.exists():
                stats = shutil.disk_usage(home_path)
                details["disk_free_gb"] = round(stats.free / (1024**3), 2)
                details["disk_total_gb"] = round(stats.total / (1024**3), 2)
                details["disk_usage_percent"] = round((stats.used / stats.total) * 100, 2)

            status = HealthStatus.HEALTHY
            message = f"System {platform.system()} is operational"

            # Check minimum disk space (1GB free)
            if details.get("disk_free_gb", 0) < 1:
                status = HealthStatus.WARNING
                message = "Low disk space available"

        except Exception as e:
            status = HealthStatus.ERROR
            message = f"System check failed: {e!s}"
            details = {}

        self.components.append(
            ComponentHealth(
                name="System", status=status, message=message, details=details, check_time=time.time() - start_time
            )
        )

    async def _check_postgresql(self) -> None:
        """Check PostgreSQL connectivity and status"""
        start_time = time.time()

        # Try to use PostgreSQL installer for enhanced checks
        try:
            from installer.dependencies.postgresql import PostgreSQLInstaller, PostgreSQLConfig

            # Use installer's test method if available
            pg_config = PostgreSQLConfig()
            installer = PostgreSQLInstaller(pg_config)

            if installer.is_postgresql_installed():
                # Test connection using installer
                conn_result = installer.test_connection()
                if conn_result["success"]:
                    self.components.append(
                        ComponentHealth(
                            name="PostgreSQL",
                            status=HealthStatus.HEALTHY,
                            message=f"PostgreSQL {conn_result.get('version', 'unknown')} is operational",
                            details=conn_result.get("details", {}),
                            check_time=time.time() - start_time,
                        )
                    )
                    return
        except ImportError:
            pass  # Fall back to standard check

        if not HAS_PSYCOPG2:
            self.components.append(
                ComponentHealth(
                    name="PostgreSQL",
                    status=HealthStatus.NOT_INSTALLED,
                    message="psycopg2 module not installed",
                    check_time=time.time() - start_time,
                )
            )
            return

        try:
            # Get connection parameters from config
            pg_config = self.config.get("postgresql", {})
            host = pg_config.get("host", "localhost")
            port = pg_config.get("port", 5432)
            database = pg_config.get("database", "postgres")
            user = pg_config.get("user", "postgres")
            password = pg_config.get("password", "")

            # Try to connect
            conn = psycopg2.connect(
                host=host, port=port, database=database, user=user, password=password, connect_timeout=1
            )

            # Get version info
            cursor = conn.cursor()
            cursor.execute("SELECT version()")
            version = cursor.fetchone()[0]

            # Get database size
            cursor.execute(
                """
                SELECT pg_database_size(current_database()) as size,
                       current_database() as name
            """
            )
            db_info = cursor.fetchone()

            cursor.close()
            conn.close()

            details = {
                "version": version.split()[1] if version else "unknown",
                "host": host,
                "port": port,
                "database": database,
                "size_mb": round(db_info[0] / (1024 * 1024), 2) if db_info else 0,
            }

            self.components.append(
                ComponentHealth(
                    name="PostgreSQL",
                    status=HealthStatus.HEALTHY,
                    message=f"Connected to PostgreSQL at {host}:{port}",
                    details=details,
                    check_time=time.time() - start_time,
                )
            )

        except psycopg2.OperationalError as e:
            # Check if PostgreSQL is installed but not running
            if shutil.which("psql"):
                status = HealthStatus.ERROR
                message = "PostgreSQL installed but not accessible"
            else:
                status = HealthStatus.NOT_INSTALLED
                message = "PostgreSQL not installed"

            self.components.append(
                ComponentHealth(
                    name="PostgreSQL",
                    status=status,
                    message=message,
                    details={"error": str(e)},
                    check_time=time.time() - start_time,
                )
            )

        except Exception as e:
            self.components.append(
                ComponentHealth(
                    name="PostgreSQL",
                    status=HealthStatus.ERROR,
                    message="PostgreSQL check failed",
                    details={"error": str(e)},
                    check_time=time.time() - start_time,
                )
            )

    async def _check_redis(self) -> None:
        """Check Redis connectivity and status"""
        start_time = time.time()

        if not HAS_REDIS:
            self.components.append(
                ComponentHealth(
                    name="Redis",
                    status=HealthStatus.NOT_INSTALLED,
                    message="redis module not installed",
                    check_time=time.time() - start_time,
                )
            )
            return

        try:
            # Get connection parameters from config
            redis_config = self.config.get("redis", {})
            host = redis_config.get("host", "localhost")
            port = redis_config.get("port", 6379)
            db = redis_config.get("db", 0)
            password = redis_config.get("password")

            # Try to connect
            client = redis.Redis(
                host=host, port=port, db=db, password=password, socket_connect_timeout=1, socket_timeout=1
            )

            # Ping server
            client.ping()

            # Get info
            info = client.info()

            details = {
                "version": info.get("redis_version", "unknown"),
                "host": host,
                "port": port,
                "used_memory_mb": round(info.get("used_memory", 0) / (1024 * 1024), 2),
                "connected_clients": info.get("connected_clients", 0),
                "uptime_days": round(info.get("uptime_in_seconds", 0) / 86400, 2),
            }

            client.close()

            self.components.append(
                ComponentHealth(
                    name="Redis",
                    status=HealthStatus.HEALTHY,
                    message=f"Connected to Redis at {host}:{port}",
                    details=details,
                    check_time=time.time() - start_time,
                )
            )

        except redis.ConnectionError as e:
            # Check if Redis is installed but not running
            if shutil.which("redis-server"):
                status = HealthStatus.ERROR
                message = "Redis installed but not accessible"
            else:
                status = HealthStatus.NOT_INSTALLED
                message = "Redis not installed"

            self.components.append(
                ComponentHealth(
                    name="Redis",
                    status=status,
                    message=message,
                    details={"error": str(e)},
                    check_time=time.time() - start_time,
                )
            )

        except Exception as e:
            self.components.append(
                ComponentHealth(
                    name="Redis",
                    status=HealthStatus.ERROR,
                    message="Redis check failed",
                    details={"error": str(e)},
                    check_time=time.time() - start_time,
                )
            )

    async def _check_docker(self) -> None:
        """Check Docker daemon status"""
        start_time = time.time()

        if not HAS_DOCKER:
            # Try command line check as fallback
            if shutil.which("docker"):
                try:
                    result = subprocess.run(
                        ["docker", "version", "--format", "{{.Server.Version}}"],
                        check=False,
                        capture_output=True,
                        text=True,
                        timeout=1,
                    )
                    if result.returncode == 0:
                        self.components.append(
                            ComponentHealth(
                                name="Docker",
                                status=HealthStatus.HEALTHY,
                                message="Docker CLI available",
                                details={"version": result.stdout.strip()},
                                check_time=time.time() - start_time,
                            )
                        )
                        return
                except:
                    pass

            self.components.append(
                ComponentHealth(
                    name="Docker",
                    status=HealthStatus.NOT_INSTALLED,
                    message="Docker module not installed",
                    check_time=time.time() - start_time,
                )
            )
            return

        try:
            # Connect to Docker daemon
            client = docker.from_env()

            # Get version info
            version = client.version()

            # Get container and image counts
            containers = client.containers.list(all=True)
            images = client.images.list()

            details = {
                "version": version.get("Version", "unknown"),
                "api_version": version.get("ApiVersion", "unknown"),
                "os": version.get("Os", "unknown"),
                "arch": version.get("Arch", "unknown"),
                "containers_total": len(containers),
                "containers_running": len([c for c in containers if c.status == "running"]),
                "images": len(images),
            }

            client.close()

            self.components.append(
                ComponentHealth(
                    name="Docker",
                    status=HealthStatus.HEALTHY,
                    message="Docker daemon is running",
                    details=details,
                    check_time=time.time() - start_time,
                )
            )

        except docker.errors.DockerException as e:
            # Check if Docker is installed but not running
            if shutil.which("docker"):
                status = HealthStatus.ERROR
                message = "Docker installed but daemon not running"
            else:
                status = HealthStatus.NOT_INSTALLED
                message = "Docker not installed"

            self.components.append(
                ComponentHealth(
                    name="Docker",
                    status=status,
                    message=message,
                    details={"error": str(e)},
                    check_time=time.time() - start_time,
                )
            )

        except Exception as e:
            self.components.append(
                ComponentHealth(
                    name="Docker",
                    status=HealthStatus.ERROR,
                    message="Docker check failed",
                    details={"error": str(e)},
                    check_time=time.time() - start_time,
                )
            )

    async def _check_ports(self) -> None:
        """Check port availability for services"""
        start_time = time.time()

        # Default ports to check
        ports_to_check = self.config.get(
            "ports", {"api": 8000, "frontend": 7274, "postgresql": 5432, "redis": 6379, "websocket": 7273}
        )

        details = {}
        blocked_ports = []

        for service, port in ports_to_check.items():
            is_available = await self._is_port_available("localhost", port)
            details[f"{service}_port_{port}"] = "available" if is_available else "in_use"
            if not is_available:
                blocked_ports.append(f"{service}:{port}")

        if blocked_ports:
            status = HealthStatus.WARNING
            message = f"Some ports are in use: {', '.join(blocked_ports)}"
        else:
            status = HealthStatus.HEALTHY
            message = "All required ports are available"

        self.components.append(
            ComponentHealth(
                name="Ports", status=status, message=message, details=details, check_time=time.time() - start_time
            )
        )

    async def _check_services(self) -> None:
        """Check status of system services"""
        start_time = time.time()
        details = {}

        # Services to check based on platform
        if platform.system() == "Windows":
            services_to_check = self.config.get("services", [])
            if not services_to_check and self._is_service_available("sc"):
                # Check common Windows services
                for service_name in ["postgresql-x64-14", "redis"]:
                    try:
                        result = subprocess.run(
                            ["sc", "query", service_name], check=False, capture_output=True, text=True, timeout=1
                        )
                        if result.returncode == 0:
                            if "RUNNING" in result.stdout:
                                details[service_name] = "running"
                            elif "STOPPED" in result.stdout:
                                details[service_name] = "stopped"
                            else:
                                details[service_name] = "unknown"
                        else:
                            details[service_name] = "not_found"
                    except:
                        details[service_name] = "check_failed"

        elif platform.system() in ["Linux", "Darwin"]:
            services_to_check = self.config.get("services", ["postgresql", "redis", "docker"])

            for service_name in services_to_check:
                if self._is_service_available("systemctl"):
                    # Linux with systemd
                    try:
                        result = subprocess.run(
                            ["systemctl", "is-active", service_name],
                            check=False,
                            capture_output=True,
                            text=True,
                            timeout=1,
                        )
                        details[service_name] = result.stdout.strip()
                    except:
                        details[service_name] = "check_failed"

                elif self._is_service_available("launchctl") and platform.system() == "Darwin":
                    # macOS
                    try:
                        result = subprocess.run(
                            ["launchctl", "list"], check=False, capture_output=True, text=True, timeout=1
                        )
                        if service_name in result.stdout:
                            details[service_name] = "loaded"
                        else:
                            details[service_name] = "not_loaded"
                    except:
                        details[service_name] = "check_failed"

        if details:
            running = [s for s, status in details.items() if status in ["running", "active", "loaded"]]
            stopped = [s for s, status in details.items() if status in ["stopped", "inactive"]]

            if stopped:
                status = HealthStatus.WARNING
                message = f"Some services not running: {', '.join(stopped)}"
            elif running:
                status = HealthStatus.HEALTHY
                message = f"Services operational: {', '.join(running)}"
            else:
                status = HealthStatus.UNKNOWN
                message = "No services detected"
        else:
            status = HealthStatus.UNKNOWN
            message = "Service checks not available on this platform"

        self.components.append(
            ComponentHealth(
                name="Services", status=status, message=message, details=details, check_time=time.time() - start_time
            )
        )

    async def _check_python(self) -> None:
        """Check Python environment and packages"""
        start_time = time.time()

        try:
            import sys

            details = {
                "version": platform.python_version(),
                "executable": sys.executable,
                "prefix": sys.prefix,
                "path_entries": len(sys.path),
            }

            # Check for required packages
            required_packages = {"fastmcp": None, "fastapi": None, "sqlalchemy": None, "httpx": None, "pyyaml": None}

            for package_name in required_packages:
                try:
                    module = __import__(package_name)
                    if hasattr(module, "__version__"):
                        required_packages[package_name] = module.__version__
                    else:
                        required_packages[package_name] = "installed"
                except ImportError:
                    required_packages[package_name] = "not_installed"

            details["packages"] = required_packages

            missing = [p for p, v in required_packages.items() if v == "not_installed"]

            if missing:
                status = HealthStatus.WARNING
                message = f"Missing packages: {', '.join(missing)}"
            else:
                status = HealthStatus.HEALTHY
                message = f"Python {platform.python_version()} with all required packages"

        except Exception as e:
            status = HealthStatus.ERROR
            message = f"Python check failed: {e!s}"
            details = {}

        self.components.append(
            ComponentHealth(
                name="Python", status=status, message=message, details=details, check_time=time.time() - start_time
            )
        )

    async def _check_network(self) -> None:
        """Check network connectivity"""
        start_time = time.time()

        try:
            # Check localhost
            localhost_ok = await self._can_connect("127.0.0.1", 80, timeout=0.5)

            # Check external connectivity (Google DNS)
            external_ok = await self._can_connect("8.8.8.8", 53, timeout=1)

            details = {
                "localhost": "reachable" if localhost_ok else "unreachable",
                "external": "reachable" if external_ok else "unreachable",
            }

            if localhost_ok and external_ok:
                status = HealthStatus.HEALTHY
                message = "Network connectivity is good"
            elif localhost_ok:
                status = HealthStatus.WARNING
                message = "No external network connectivity"
            else:
                status = HealthStatus.ERROR
                message = "Network connectivity issues detected"

        except Exception as e:
            status = HealthStatus.ERROR
            message = f"Network check failed: {e!s}"
            details = {}

        self.components.append(
            ComponentHealth(
                name="Network", status=status, message=message, details=details, check_time=time.time() - start_time
            )
        )

    async def _is_port_available(self, host: str, port: int) -> bool:
        """Check if a port is available for binding"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.5)
        try:
            # Try to connect - if successful, port is in use
            result = sock.connect_ex((host, port))
            return result != 0
        except:
            return True
        finally:
            sock.close()

    async def _can_connect(self, host: str, port: int, timeout: float = 1.0) -> bool:
        """Check if we can connect to a host:port"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        try:
            result = sock.connect_ex((host, port))
            return result == 0
        except:
            return False
        finally:
            sock.close()

    def _is_service_available(self, command: str) -> bool:
        """Check if a system command is available"""
        return shutil.which(command) is not None

    def _calculate_overall_status(self) -> HealthStatus:
        """Calculate overall health status from component statuses"""
        if not self.components:
            return HealthStatus.UNKNOWN

        statuses = [c.status for c in self.components]

        if any(s == HealthStatus.ERROR for s in statuses):
            return HealthStatus.ERROR
        if any(s == HealthStatus.WARNING for s in statuses):
            return HealthStatus.WARNING
        if all(s == HealthStatus.HEALTHY for s in statuses):
            return HealthStatus.HEALTHY
        return HealthStatus.WARNING

    def _get_system_info(self) -> dict[str, Any]:
        """Get system information"""
        return {
            "platform": platform.system(),
            "platform_version": platform.version(),
            "architecture": platform.machine(),
            "processor": platform.processor(),
            "python_version": platform.python_version(),
            "hostname": socket.gethostname(),
        }


async def run_health_check(
    config: Optional[dict[str, Any]] = None, components: Optional[list[str]] = None, output_format: str = "summary"
) -> HealthReport:
    """
    Convenience function to run health checks

    Args:
        config: Optional configuration dict
        components: Optional list of components to check
        output_format: Output format ('summary', 'json', 'dict')

    Returns:
        Health report
    """
    checker = HealthChecker(config)
    report = await checker.check_all(components)

    if output_format == "summary":
        print(report.get_summary())
    elif output_format == "json":
        import json

        print(json.dumps(report.to_dict(), indent=2))
    elif output_format == "dict":
        print(report.to_dict())

    return report


if __name__ == "__main__":
    # Example usage and testing
    import sys

    # Parse command line arguments
    components_to_check = None
    if len(sys.argv) > 1:
        components_to_check = sys.argv[1].split(",")

    # Run health check
    print("Running health checks...")
    print("-" * 60)

    # Run async health check
    report = asyncio.run(run_health_check(components=components_to_check, output_format="summary"))

    # Exit with appropriate code
    if report.overall_status == HealthStatus.ERROR:
        sys.exit(1)
    elif report.overall_status == HealthStatus.WARNING:
        sys.exit(2)
    else:
        sys.exit(0)
