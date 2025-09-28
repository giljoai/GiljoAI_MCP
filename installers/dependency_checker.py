#!/usr/bin/env python3
"""
Dependency Checker for GiljoAI MCP
===================================

Detects and reports on system dependencies required for GiljoAI MCP.
Works cross-platform (Windows, Mac, Linux) using only standard library.
"""

import os
import sys
import platform
import subprocess
import json
import shutil
import socket
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from enum import Enum


class DependencyStatus(Enum):
    """Status of a dependency"""

    INSTALLED = "installed"
    NOT_FOUND = "not_found"
    OUTDATED = "outdated"
    ERROR = "error"


@dataclass
class DependencyInfo:
    """Information about a dependency"""

    name: str
    status: str  # Will use DependencyStatus.value
    version: Optional[str] = None
    path: Optional[str] = None
    required_version: Optional[str] = None
    install_command: Optional[str] = None
    notes: Optional[str] = None
    is_required: bool = True


@dataclass
class PortInfo:
    """Information about a network port"""

    port: int
    status: str  # 'free', 'in_use', 'error'
    process: Optional[str] = None
    service: str = ""


@dataclass
class DiskSpaceInfo:
    """Disk space information"""

    total_gb: float
    free_gb: float
    used_gb: float
    percent_used: float
    has_required_space: bool


class DependencyChecker:
    """Check system dependencies for GiljoAI MCP"""

    # Minimum versions required
    MIN_PYTHON = (3, 8)
    MIN_NODE = "18.0.0"
    MIN_NPM = "8.0.0"
    MIN_DOCKER = "20.0.0"
    MIN_POSTGRESQL = "14.0"
    MIN_GIT = "2.0.0"

    # Required disk space in GB
    REQUIRED_DISK_SPACE = 10.0

    # Default ports used by the application
    DEFAULT_PORTS = {
        6000: "Frontend (Vue.js)",
        6001: "MCP Server",
        6002: "API Server",
        5432: "PostgreSQL (optional)",
        # 6379: "Redis (removed - not implemented)",
    }

    def __init__(self):
        self.os_type = platform.system().lower()
        self.os_version = platform.version()
        self.architecture = platform.machine()
        self.dependencies: List[DependencyInfo] = []
        self.ports: List[PortInfo] = []
        self.disk_space: Optional[DiskSpaceInfo] = None

    def check_all(self) -> Dict[str, Any]:
        """Check all dependencies and return complete report"""
        report = {
            "timestamp": self._get_timestamp(),
            "system": self._get_system_info(),
            "dependencies": {},
            "ports": {},
            "disk_space": None,
            "summary": {"ready": False, "missing_required": [], "missing_optional": [], "issues": []},
        }

        # Check each dependency (convert to dict)
        report["dependencies"]["python"] = asdict(self.check_python())
        report["dependencies"]["nodejs"] = asdict(self.check_nodejs())
        report["dependencies"]["npm"] = asdict(self.check_npm())
        report["dependencies"]["git"] = asdict(self.check_git())
        report["dependencies"]["docker"] = asdict(self.check_docker())
        report["dependencies"]["postgresql"] = asdict(self.check_postgresql())
        # Redis removed - not actually implemented
        # report["dependencies"]["redis"] = asdict(self.check_redis())

        # Check ports (convert to dicts)
        report["ports"] = [asdict(p) for p in self.check_ports()]

        # Check disk space (convert to dict)
        disk_info = self.check_disk_space()
        report["disk_space"] = asdict(disk_info) if disk_info else None

        # Generate summary
        report["summary"] = self._generate_summary(report)

        return report

    def check_python(self) -> DependencyInfo:
        """Check Python installation"""
        current = sys.version_info
        version = f"{current.major}.{current.minor}.{current.micro}"

        if (current.major, current.minor) >= self.MIN_PYTHON:
            status = DependencyStatus.INSTALLED.value
        else:
            status = DependencyStatus.OUTDATED.value

        return DependencyInfo(
            name="Python",
            status=status,
            version=version,
            path=sys.executable,
            required_version=f"{self.MIN_PYTHON[0]}.{self.MIN_PYTHON[1]}+",
            install_command=self._get_install_command("python"),
            is_required=True,
        )

    def check_nodejs(self) -> DependencyInfo:
        """Check Node.js installation"""
        try:
            result = subprocess.run(["node", "--version"], capture_output=True, text=True, timeout=5)

            if result.returncode == 0:
                version = result.stdout.strip().lstrip("v")
                if self._compare_versions(version, self.MIN_NODE) >= 0:
                    status = DependencyStatus.INSTALLED.value
                else:
                    status = DependencyStatus.OUTDATED.value

                # Get path
                path_result = subprocess.run(
                    ["where", "node"] if self.os_type == "windows" else ["which", "node"],
                    capture_output=True,
                    text=True,
                )
                path = path_result.stdout.strip().split("\n")[0] if path_result.returncode == 0 else None

                return DependencyInfo(
                    name="Node.js",
                    status=status,
                    version=version,
                    path=path,
                    required_version=self.MIN_NODE,
                    install_command=self._get_install_command("nodejs"),
                    is_required=False,
                    notes="Required for frontend development",
                )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return DependencyInfo(
                name="Node.js",
                status=DependencyStatus.NOT_FOUND.value,
                required_version=self.MIN_NODE,
                install_command=self._get_install_command("nodejs"),
                is_required=False,
                notes="Required for frontend development",
            )

    def check_npm(self) -> DependencyInfo:
        """Check npm installation"""
        try:
            result = subprocess.run(["npm", "--version"], capture_output=True, text=True, timeout=5)

            if result.returncode == 0:
                version = result.stdout.strip()
                if self._compare_versions(version, self.MIN_NPM) >= 0:
                    status = DependencyStatus.INSTALLED.value
                else:
                    status = DependencyStatus.OUTDATED.value

                return DependencyInfo(
                    name="npm",
                    status=status,
                    version=version,
                    required_version=self.MIN_NPM,
                    is_required=False,
                    notes="Comes with Node.js",
                )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return DependencyInfo(
                name="npm",
                status=DependencyStatus.NOT_FOUND.value,
                required_version=self.MIN_NPM,
                install_command="Installed with Node.js",
                is_required=False,
            )

    def check_git(self) -> DependencyInfo:
        """Check Git installation"""
        try:
            result = subprocess.run(["git", "--version"], capture_output=True, text=True, timeout=5)

            if result.returncode == 0:
                # Parse version from "git version 2.34.1"
                version_str = result.stdout.strip()
                version = version_str.split()[-1]

                if self._compare_versions(version, self.MIN_GIT) >= 0:
                    status = DependencyStatus.INSTALLED.value
                else:
                    status = DependencyStatus.OUTDATED.value

                # Get path
                path_result = subprocess.run(
                    ["where", "git"] if self.os_type == "windows" else ["which", "git"], capture_output=True, text=True
                )
                path = path_result.stdout.strip().split("\n")[0] if path_result.returncode == 0 else None

                return DependencyInfo(
                    name="Git",
                    status=status,
                    version=version,
                    path=path,
                    required_version=self.MIN_GIT,
                    install_command=self._get_install_command("git"),
                    is_required=False,
                    notes="Useful for updates and version control",
                )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return DependencyInfo(
                name="Git",
                status=DependencyStatus.NOT_FOUND.value,
                required_version=self.MIN_GIT,
                install_command=self._get_install_command("git"),
                is_required=False,
                notes="Useful for updates and version control",
            )

    def check_docker(self) -> DependencyInfo:
        """Check Docker installation"""
        try:
            result = subprocess.run(["docker", "--version"], capture_output=True, text=True, timeout=5)

            if result.returncode == 0:
                # Parse version from "Docker version 20.10.21, build baeda1f"
                version_str = result.stdout.strip()
                version = version_str.split()[2].rstrip(",")

                if self._compare_versions(version, self.MIN_DOCKER) >= 0:
                    status = DependencyStatus.INSTALLED.value

                    # Check if Docker daemon is running
                    daemon_result = subprocess.run(["docker", "info"], capture_output=True, text=True, timeout=5)

                    if daemon_result.returncode != 0:
                        notes = "Docker installed but daemon not running"
                    else:
                        notes = "Docker is running"
                else:
                    status = DependencyStatus.OUTDATED.value
                    notes = None

                return DependencyInfo(
                    name="Docker",
                    status=status,
                    version=version,
                    required_version=self.MIN_DOCKER,
                    install_command=self._get_install_command("docker"),
                    is_required=False,
                    notes=notes or "Optional for containerized deployment",
                )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return DependencyInfo(
                name="Docker",
                status=DependencyStatus.NOT_FOUND.value,
                required_version=self.MIN_DOCKER,
                install_command=self._get_install_command("docker"),
                is_required=False,
                notes="Optional for containerized deployment",
            )

    def check_postgresql(self) -> DependencyInfo:
        """Check PostgreSQL installation"""
        commands = ["psql", "postgres"]  # Try different command names

        for cmd in commands:
            try:
                result = subprocess.run([cmd, "--version"], capture_output=True, text=True, timeout=5)

                if result.returncode == 0:
                    # Parse version from "psql (PostgreSQL) 14.5"
                    version_str = result.stdout.strip()
                    parts = version_str.split()
                    version = parts[-1] if parts else "unknown"

                    if self._compare_versions(version, self.MIN_POSTGRESQL) >= 0:
                        status = DependencyStatus.INSTALLED.value

                        # Check if PostgreSQL service is running
                        if self._check_port_availability(5432):
                            notes = "PostgreSQL installed but not running on port 5432"
                        else:
                            notes = "PostgreSQL is running on port 5432"
                    else:
                        status = DependencyStatus.OUTDATED.value
                        notes = None

                    return DependencyInfo(
                        name="PostgreSQL",
                        status=status,
                        version=version,
                        required_version=self.MIN_POSTGRESQL,
                        install_command=self._get_install_command("postgresql"),
                        is_required=False,
                        notes=notes or "Optional for production deployment",
                    )
            except (subprocess.TimeoutExpired, FileNotFoundError):
                continue

        return DependencyInfo(
            name="PostgreSQL",
            status=DependencyStatus.NOT_FOUND.value,
            required_version=self.MIN_POSTGRESQL,
            install_command=self._get_install_command("postgresql"),
            is_required=False,
            notes="Optional for production deployment (SQLite used by default)",
        )

    # Redis removed - not actually implemented in codebase
    # def check_redis(self) -> DependencyInfo:
    #     """Check Redis installation"""
    #     # Removed - Redis was never actually used in the codebase
    #     # Only in-memory caching is implemented
    #     pass

    def check_ports(self) -> List[PortInfo]:
        """Check availability of required ports"""
        ports = []

        for port, service in self.DEFAULT_PORTS.items():
            if self._check_port_availability(port):
                status = "free"
                process = None
            else:
                status = "in_use"
                process = self._get_port_process(port)

            ports.append(PortInfo(port=port, status=status, process=process, service=service))

        return ports

    def check_disk_space(self) -> DiskSpaceInfo:
        """Check available disk space"""
        path = Path.cwd()

        if self.os_type == "windows":
            import ctypes

            free_bytes = ctypes.c_ulonglong(0)
            total_bytes = ctypes.c_ulonglong(0)
            ctypes.windll.kernel32.GetDiskFreeSpaceExW(
                ctypes.c_wchar_p(str(path)), ctypes.pointer(free_bytes), ctypes.pointer(total_bytes), None
            )

            free_gb = free_bytes.value / (1024**3)
            total_gb = total_bytes.value / (1024**3)
        else:
            # Unix-like systems
            import shutil

            stat = shutil.disk_usage(path)
            free_gb = stat.free / (1024**3)
            total_gb = stat.total / (1024**3)

        used_gb = total_gb - free_gb
        percent_used = (used_gb / total_gb) * 100 if total_gb > 0 else 0

        return DiskSpaceInfo(
            total_gb=round(total_gb, 2),
            free_gb=round(free_gb, 2),
            used_gb=round(used_gb, 2),
            percent_used=round(percent_used, 1),
            has_required_space=free_gb >= self.REQUIRED_DISK_SPACE,
        )

    def _check_port_availability(self, port: int) -> bool:
        """Check if a port is available (True if free, False if in use)"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind(("", port))
                return True
            except (OSError, socket.error):
                return False

    def _get_port_process(self, port: int) -> Optional[str]:
        """Try to identify what process is using a port"""
        try:
            if self.os_type == "windows":
                result = subprocess.run(["netstat", "-ano"], capture_output=True, text=True, timeout=5)

                for line in result.stdout.split("\n"):
                    if f":{port}" in line and "LISTENING" in line:
                        parts = line.split()
                        if parts:
                            pid = parts[-1]
                            # Try to get process name
                            task_result = subprocess.run(
                                ["tasklist", "/FI", f"PID eq {pid}"], capture_output=True, text=True
                            )
                            for task_line in task_result.stdout.split("\n"):
                                if pid in task_line:
                                    return task_line.split()[0]
                            return f"PID {pid}"
            else:
                # Unix-like systems
                result = subprocess.run(["lsof", f"-i:{port}"], capture_output=True, text=True, timeout=5)

                lines = result.stdout.strip().split("\n")
                if len(lines) > 1:
                    # Parse the command name from lsof output
                    parts = lines[1].split()
                    if parts:
                        return parts[0]
        except:
            pass

        return "Unknown process"

    def _compare_versions(self, version1: str, version2: str) -> int:
        """Compare two version strings (returns -1, 0, or 1)"""

        def parse_version(v):
            return [int(x) for x in v.split(".") if x.isdigit()]

        v1 = parse_version(version1)
        v2 = parse_version(version2)

        for i in range(max(len(v1), len(v2))):
            val1 = v1[i] if i < len(v1) else 0
            val2 = v2[i] if i < len(v2) else 0

            if val1 < val2:
                return -1
            elif val1 > val2:
                return 1

        return 0

    def _get_install_command(self, dependency: str) -> str:
        """Get platform-specific install command for a dependency"""
        commands = {
            "windows": {
                "python": "Download from https://www.python.org/downloads/",
                "nodejs": "winget install OpenJS.NodeJS OR download from https://nodejs.org/",
                "git": "winget install Git.Git OR download from https://git-scm.com/",
                "docker": "Download Docker Desktop from https://www.docker.com/products/docker-desktop/",
                "postgresql": "Download from https://www.postgresql.org/download/windows/",
                # "redis": "Download from https://github.com/microsoftarchive/redis/releases",  # Removed - not implemented
            },
            "darwin": {  # macOS
                "python": "brew install python3 OR download from https://www.python.org/",
                "nodejs": "brew install node OR download from https://nodejs.org/",
                "git": "brew install git OR xcode-select --install",
                "docker": "Download Docker Desktop from https://www.docker.com/products/docker-desktop/",
                "postgresql": "brew install postgresql",
                # "redis": "brew install redis",  # Removed - not implemented
            },
            "linux": {
                "python": "sudo apt install python3 (Ubuntu/Debian) OR sudo yum install python3 (RHEL/CentOS)",
                "nodejs": "curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash - && sudo apt install nodejs",
                "git": "sudo apt install git (Ubuntu/Debian) OR sudo yum install git (RHEL/CentOS)",
                "docker": "curl -fsSL https://get.docker.com | sh",
                "postgresql": "sudo apt install postgresql (Ubuntu/Debian) OR sudo yum install postgresql-server (RHEL/CentOS)",
                # "redis": "sudo apt install redis (Ubuntu/Debian) OR sudo yum install redis (RHEL/CentOS)",  # Removed - not implemented
            },
        }

        os_commands = commands.get(self.os_type, commands.get("linux"))
        return os_commands.get(dependency, f"Please install {dependency} manually")

    def _get_system_info(self) -> Dict[str, str]:
        """Get system information"""
        return {
            "os": platform.system(),
            "os_version": platform.version(),
            "architecture": platform.machine(),
            "processor": platform.processor(),
            "python_implementation": platform.python_implementation(),
            "hostname": socket.gethostname(),
        }

    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        from datetime import datetime

        return datetime.now().isoformat()

    def _generate_summary(self, report: Dict) -> Dict:
        """Generate summary from the full report"""
        missing_required = []
        missing_optional = []
        issues = []

        # Check dependencies
        for name, dep in report["dependencies"].items():
            if isinstance(dep, dict):
                if dep.get("status") == "not_found":
                    if dep.get("is_required", False):
                        missing_required.append(name)
                    else:
                        missing_optional.append(name)
                elif dep.get("status") == "outdated":
                    issues.append(
                        f"{name} is outdated (found {dep.get('version')}, need {dep.get('required_version')})"
                    )

        # Check ports
        for port_info in report["ports"]:
            if port_info["status"] == "in_use":
                issues.append(
                    f"Port {port_info['port']} ({port_info['service']}) is in use by {port_info.get('process', 'unknown')}"
                )

        # Check disk space
        if report["disk_space"] and not report["disk_space"]["has_required_space"]:
            issues.append(
                f"Insufficient disk space (need {self.REQUIRED_DISK_SPACE}GB, have {report['disk_space']['free_gb']}GB)"
            )

        # Determine if ready
        ready = len(missing_required) == 0 and (
            report["disk_space"]["has_required_space"] if report["disk_space"] else True
        )

        return {
            "ready": ready,
            "missing_required": missing_required,
            "missing_optional": missing_optional,
            "issues": issues,
        }

    def print_report(self, report: Dict, use_colors: bool = True):
        """Print a formatted dependency report"""
        if use_colors and sys.platform != "win32":
            GREEN = "\033[92m"
            YELLOW = "\033[93m"
            RED = "\033[91m"
            BLUE = "\033[94m"
            BOLD = "\033[1m"
            ENDC = "\033[0m"
        else:
            GREEN = YELLOW = RED = BLUE = BOLD = ENDC = ""

        print(f"\n{BOLD}=== GiljoAI MCP Dependency Report ==={ENDC}")
        print(f"Generated: {report['timestamp']}")
        print(f"System: {report['system']['os']} {report['system']['architecture']}")

        print(f"\n{BOLD}Dependencies:{ENDC}")
        for name, dep in report["dependencies"].items():
            if isinstance(dep, dict):
                status_symbol = {
                    "installed": f"{GREEN}[OK]{ENDC}",
                    "not_found": f"{RED}[X]{ENDC}",
                    "outdated": f"{YELLOW}[!]{ENDC}",
                    "error": f"{RED}[E]{ENDC}",
                }.get(dep["status"], "[?]")

                req_tag = " (REQUIRED)" if dep.get("is_required") else ""
                version = f" v{dep['version']}" if dep.get("version") else ""

                print(f"  {status_symbol} {dep['name']}{version}{req_tag}")

                if dep.get("notes"):
                    print(f"      {dep['notes']}")

                if dep["status"] in ["not_found", "outdated"] and dep.get("install_command"):
                    print(f"      Install: {BLUE}{dep['install_command']}{ENDC}")

        print(f"\n{BOLD}Ports:{ENDC}")
        for port in report["ports"]:
            if port["status"] == "free":
                symbol = f"{GREEN}[OK]{ENDC}"
            else:
                symbol = f"{YELLOW}[!]{ENDC}"

            status = f" - IN USE by {port.get('process', 'unknown')}" if port["status"] == "in_use" else ""
            print(f"  {symbol} Port {port['port']} ({port['service']}){status}")

        print(f"\n{BOLD}Disk Space:{ENDC}")
        if report["disk_space"]:
            disk = report["disk_space"]
            symbol = f"{GREEN}[OK]{ENDC}" if disk["has_required_space"] else f"{RED}[X]{ENDC}"
            print(f"  {symbol} {disk['free_gb']}GB free of {disk['total_gb']}GB ({disk['percent_used']}% used)")
            print(f"      Required: {self.REQUIRED_DISK_SPACE}GB")

        print(f"\n{BOLD}Summary:{ENDC}")
        summary = report["summary"]

        if summary["ready"]:
            print(f"  {GREEN}System is ready for installation!{ENDC}")
        else:
            print(f"  {RED}System is not ready for installation.{ENDC}")

        if summary["missing_required"]:
            print(f"\n  {RED}Missing required dependencies:{ENDC}")
            for dep in summary["missing_required"]:
                print(f"    - {dep}")

        if summary["missing_optional"]:
            print(f"\n  {YELLOW}Missing optional dependencies:{ENDC}")
            for dep in summary["missing_optional"]:
                print(f"    - {dep}")

        if summary["issues"]:
            print(f"\n  {YELLOW}Issues to address:{ENDC}")
            for issue in summary["issues"]:
                print(f"    - {issue}")


def main():
    """Main function for testing the dependency checker"""
    checker = DependencyChecker()
    report = checker.check_all()
    checker.print_report(report)

    # Save report to file
    with open("dependency_report.json", "w") as f:
        # Convert dataclasses to dicts for JSON serialization
        json_report = json.dumps(report, default=str, indent=2)
        f.write(json_report)

    print("\n[i] Full report saved to dependency_report.json")

    return 0 if report["summary"]["ready"] else 1


if __name__ == "__main__":
    sys.exit(main())
