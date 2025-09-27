"""
Cross-platform Service Manager for GiljoAI MCP

This module provides unified service management across Windows, macOS, and Linux,
handling PostgreSQL, Redis, and GiljoAI application services.
"""

import os
import sys
import platform
import subprocess
import logging
import json
import time
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum


# Configure logging
logger = logging.getLogger(__name__)


class ServiceStatus(Enum):
    """Service status enumeration."""

    RUNNING = "running"
    STOPPED = "stopped"
    STARTING = "starting"
    STOPPING = "stopping"
    FAILED = "failed"
    UNKNOWN = "unknown"
    NOT_INSTALLED = "not_installed"


class ServiceType(Enum):
    """Types of services managed."""

    POSTGRESQL = "postgresql"
    REDIS = "redis"
    GILJO_APP = "giljo_app"
    GILJO_WORKER = "giljo_worker"
    NGINX = "nginx"
    CUSTOM = "custom"


@dataclass
class ServiceConfig:
    """Service configuration."""

    name: str
    display_name: str
    description: str
    service_type: ServiceType
    executable: Path
    arguments: List[str] = None
    working_directory: Path = None
    environment: Dict[str, str] = None
    user: str = None
    group: str = None
    auto_start: bool = True
    restart_on_failure: bool = True
    restart_delay: int = 5
    dependencies: List[str] = None
    log_file: Path = None
    pid_file: Path = None

    def __post_init__(self):
        """Initialize default values."""
        if self.arguments is None:
            self.arguments = []
        if self.environment is None:
            self.environment = {}
        if self.dependencies is None:
            self.dependencies = []


class ServiceManager(ABC):
    """Abstract base class for platform-specific service managers."""

    def __init__(self):
        """Initialize service manager."""
        self.platform = platform.system().lower()
        self.services: Dict[str, ServiceConfig] = {}
        self._setup_logging()

    def _setup_logging(self):
        """Configure logging."""
        log_dir = Path.home() / ".giljo_mcp" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)

        log_file = log_dir / "service_manager.log"
        handler = logging.FileHandler(log_file)
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)

    def register_service(self, config: ServiceConfig) -> bool:
        """
        Register a service configuration.

        Args:
            config: Service configuration object.

        Returns:
            True if registration successful, False otherwise.
        """
        try:
            self.services[config.name] = config
            logger.info(f"Registered service: {config.name}")
            return True
        except Exception as e:
            logger.error(f"Failed to register service {config.name}: {str(e)}")
            return False

    @abstractmethod
    def install_service(self, service_name: str) -> bool:
        """
        Install a service on the system.

        Args:
            service_name: Name of the service to install.

        Returns:
            True if installation successful, False otherwise.
        """
        pass

    @abstractmethod
    def uninstall_service(self, service_name: str) -> bool:
        """
        Uninstall a service from the system.

        Args:
            service_name: Name of the service to uninstall.

        Returns:
            True if uninstallation successful, False otherwise.
        """
        pass

    @abstractmethod
    def start_service(self, service_name: str) -> bool:
        """
        Start a service.

        Args:
            service_name: Name of the service to start.

        Returns:
            True if service started successfully, False otherwise.
        """
        pass

    @abstractmethod
    def stop_service(self, service_name: str) -> bool:
        """
        Stop a service.

        Args:
            service_name: Name of the service to stop.

        Returns:
            True if service stopped successfully, False otherwise.
        """
        pass

    @abstractmethod
    def restart_service(self, service_name: str) -> bool:
        """
        Restart a service.

        Args:
            service_name: Name of the service to restart.

        Returns:
            True if service restarted successfully, False otherwise.
        """
        pass

    @abstractmethod
    def get_service_status(self, service_name: str) -> ServiceStatus:
        """
        Get the status of a service.

        Args:
            service_name: Name of the service to check.

        Returns:
            ServiceStatus enum value.
        """
        pass

    @abstractmethod
    def enable_service(self, service_name: str) -> bool:
        """
        Enable a service to start at boot.

        Args:
            service_name: Name of the service to enable.

        Returns:
            True if service enabled successfully, False otherwise.
        """
        pass

    @abstractmethod
    def disable_service(self, service_name: str) -> bool:
        """
        Disable a service from starting at boot.

        Args:
            service_name: Name of the service to disable.

        Returns:
            True if service disabled successfully, False otherwise.
        """
        pass

    def get_all_services(self) -> Dict[str, ServiceStatus]:
        """
        Get status of all registered services.

        Returns:
            Dictionary mapping service names to their status.
        """
        status_dict = {}
        for service_name in self.services:
            status_dict[service_name] = self.get_service_status(service_name)
        return status_dict

    def start_all_services(self) -> Dict[str, bool]:
        """
        Start all registered services in dependency order.

        Returns:
            Dictionary mapping service names to start success status.
        """
        results = {}
        ordered_services = self._order_by_dependencies()

        for service_name in ordered_services:
            results[service_name] = self.start_service(service_name)
            if results[service_name]:
                time.sleep(2)  # Give service time to start

        return results

    def stop_all_services(self) -> Dict[str, bool]:
        """
        Stop all registered services in reverse dependency order.

        Returns:
            Dictionary mapping service names to stop success status.
        """
        results = {}
        ordered_services = list(reversed(self._order_by_dependencies()))

        for service_name in ordered_services:
            results[service_name] = self.stop_service(service_name)

        return results

    def _order_by_dependencies(self) -> List[str]:
        """
        Order services by their dependencies.

        Returns:
            List of service names in dependency order.
        """
        ordered = []
        visited = set()

        def visit(name: str):
            if name in visited:
                return
            visited.add(name)

            if name in self.services:
                for dep in self.services[name].dependencies:
                    visit(dep)
                ordered.append(name)

        for service_name in self.services:
            visit(service_name)

        return ordered

    def setup_services(self, install_dir: Path, auto_start: bool = False) -> bool:
        """
        Set up default GiljoAI services.

        Args:
            install_dir: Installation directory
            auto_start: Whether to auto-start services

        Returns:
            True if setup successful
        """
        try:
            # Create default service configurations
            services = create_giljo_services()

            # Update service paths to use install_dir
            for service_config in services.values():
                if service_config.service_type == ServiceType.GILJO_APP:
                    service_config.working_directory = install_dir
                    service_config.arguments = ["-m", "src.giljo_mcp.server"]
                    service_config.environment.update({
                        "GILJO_CONFIG_DIR": str(install_dir / "config"),
                        "GILJO_DATA_DIR": str(install_dir / "data"),
                        "GILJO_LOG_DIR": str(install_dir / "logs"),
                    })

            # Register all services
            for service_config in services.values():
                service_config.auto_start = auto_start
                self.register_service(service_config)

            logger.info("Services configured successfully")
            return True

        except Exception as e:
            logger.error(f"Service setup failed: {e}")
            return False

    def create_launchers(self, install_dir: Path) -> bool:
        """
        Create launcher scripts for the application.

        Args:
            install_dir: Installation directory

        Returns:
            True if launchers created successfully
        """
        try:
            scripts_dir = install_dir / "scripts"
            scripts_dir.mkdir(exist_ok=True)

            if self.platform == "windows":
                # Create Windows batch files
                start_script = scripts_dir / "start_giljo.bat"
                start_script.write_text(f"""@echo off
cd /d "{install_dir}"
python -m src.giljo_mcp.server
pause
""")

                stop_script = scripts_dir / "stop_giljo.bat"
                stop_script.write_text("""@echo off
taskkill /f /im python.exe /fi "WINDOWTITLE eq GiljoAI*"
echo GiljoAI MCP stopped
pause
""")

            else:
                # Create Unix shell scripts
                start_script = scripts_dir / "start_giljo.sh"
                start_script.write_text(f"""#!/bin/bash
cd "{install_dir}"
python -m src.giljo_mcp.server
""")

                stop_script = scripts_dir / "stop_giljo.sh"
                stop_script.write_text("""#!/bin/bash
pkill -f "src.giljo_mcp.server"
echo "GiljoAI MCP stopped"
""")

                # Make executable
                start_script.chmod(0o755)
                stop_script.chmod(0o755)

            logger.info("Launcher scripts created successfully")
            return True

        except Exception as e:
            logger.error(f"Launcher creation failed: {e}")
            return False

    def wait_for_service(self, service_name: str, timeout: int = 30) -> bool:
        """
        Wait for a service to reach running state.

        Args:
            service_name: Name of the service to wait for.
            timeout: Maximum time to wait in seconds.

        Returns:
            True if service is running, False if timeout.
        """
        start_time = time.time()

        while time.time() - start_time < timeout:
            status = self.get_service_status(service_name)
            if status == ServiceStatus.RUNNING:
                return True
            elif status == ServiceStatus.FAILED:
                return False

            time.sleep(1)

        return False


class WindowsServiceManager(ServiceManager):
    """Windows service manager using Windows Service Control Manager."""

    def __init__(self):
        """Initialize Windows service manager."""
        super().__init__()
        self.service_script_dir = Path(__file__).parent / "windows"

    def install_service(self, service_name: str) -> bool:
        """Install a Windows service."""
        if service_name not in self.services:
            logger.error(f"Service {service_name} not registered")
            return False

        config = self.services[service_name]

        try:
            # Create service using sc.exe
            cmd = [
                "sc",
                "create",
                service_name,
                f'DisplayName="{config.display_name}"',
                f'binPath="{config.executable} {" ".join(config.arguments)}"',
                "start=",
                "auto" if config.auto_start else "demand",
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode != 0:
                logger.error(f"Failed to create service: {result.stderr}")
                return False

            # Set service description
            desc_cmd = ["sc", "description", service_name, f'"{config.description}"']
            subprocess.run(desc_cmd, capture_output=True)

            # Configure recovery options if restart_on_failure is True
            if config.restart_on_failure:
                recovery_cmd = [
                    "sc",
                    "failure",
                    service_name,
                    "reset=",
                    "86400",
                    "actions=",
                    f"restart/{config.restart_delay * 1000}/restart/{config.restart_delay * 2000}/restart/{config.restart_delay * 3000}",
                ]
                subprocess.run(recovery_cmd, capture_output=True)

            # Set dependencies
            if config.dependencies:
                depend_cmd = ["sc", "config", service_name, f'depend="{"/".join(config.dependencies)}"']
                subprocess.run(depend_cmd, capture_output=True)

            logger.info(f"Service {service_name} installed successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to install service {service_name}: {str(e)}")
            return False

    def uninstall_service(self, service_name: str) -> bool:
        """Uninstall a Windows service."""
        try:
            # Stop service first
            self.stop_service(service_name)
            time.sleep(2)

            # Delete service
            cmd = ["sc", "delete", service_name]
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                logger.info(f"Service {service_name} uninstalled successfully")
                return True
            else:
                logger.error(f"Failed to uninstall service: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"Failed to uninstall service {service_name}: {str(e)}")
            return False

    def start_service(self, service_name: str) -> bool:
        """Start a Windows service."""
        try:
            cmd = ["sc", "start", service_name]
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0 or "already running" in result.stderr.lower():
                logger.info(f"Service {service_name} started")
                return True
            else:
                logger.error(f"Failed to start service: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"Failed to start service {service_name}: {str(e)}")
            return False

    def stop_service(self, service_name: str) -> bool:
        """Stop a Windows service."""
        try:
            cmd = ["sc", "stop", service_name]
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0 or "not started" in result.stderr.lower():
                logger.info(f"Service {service_name} stopped")
                return True
            else:
                logger.error(f"Failed to stop service: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"Failed to stop service {service_name}: {str(e)}")
            return False

    def restart_service(self, service_name: str) -> bool:
        """Restart a Windows service."""
        if self.stop_service(service_name):
            time.sleep(2)
            return self.start_service(service_name)
        return False

    def get_service_status(self, service_name: str) -> ServiceStatus:
        """Get the status of a Windows service."""
        try:
            cmd = ["sc", "query", service_name]
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode != 0:
                if "service does not exist" in result.stderr.lower():
                    return ServiceStatus.NOT_INSTALLED
                return ServiceStatus.UNKNOWN

            output = result.stdout.lower()

            if "running" in output:
                return ServiceStatus.RUNNING
            elif "stopped" in output:
                return ServiceStatus.STOPPED
            elif "start_pending" in output:
                return ServiceStatus.STARTING
            elif "stop_pending" in output:
                return ServiceStatus.STOPPING
            elif "failed" in output:
                return ServiceStatus.FAILED
            else:
                return ServiceStatus.UNKNOWN

        except Exception as e:
            logger.error(f"Failed to get service status: {str(e)}")
            return ServiceStatus.UNKNOWN

    def enable_service(self, service_name: str) -> bool:
        """Enable a Windows service to start at boot."""
        try:
            cmd = ["sc", "config", service_name, "start=", "auto"]
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                logger.info(f"Service {service_name} enabled for auto-start")
                return True
            else:
                logger.error(f"Failed to enable service: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"Failed to enable service {service_name}: {str(e)}")
            return False

    def disable_service(self, service_name: str) -> bool:
        """Disable a Windows service from starting at boot."""
        try:
            cmd = ["sc", "config", service_name, "start=", "disabled"]
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                logger.info(f"Service {service_name} disabled")
                return True
            else:
                logger.error(f"Failed to disable service: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"Failed to disable service {service_name}: {str(e)}")
            return False


class MacOSServiceManager(ServiceManager):
    """macOS service manager using launchd."""

    def __init__(self):
        """Initialize macOS service manager."""
        super().__init__()
        self.plist_dir = Path.home() / "Library" / "LaunchAgents"
        self.plist_dir.mkdir(parents=True, exist_ok=True)
        self.service_script_dir = Path(__file__).parent / "macos"

    def _generate_plist(self, config: ServiceConfig) -> str:
        """Generate launchd plist content."""
        plist_dict = {
            "Label": config.name,
            "ProgramArguments": [str(config.executable)] + config.arguments,
            "RunAtLoad": config.auto_start,
            "KeepAlive": config.restart_on_failure,
            "StandardOutPath": (
                str(config.log_file) if config.log_file else str(Path(tempfile.gettempdir()) / f"{config.name}.out")
            ),
            "StandardErrorPath": (
                str(config.log_file) if config.log_file else str(Path(tempfile.gettempdir()) / f"{config.name}.err")
            ),
        }

        if config.working_directory:
            plist_dict["WorkingDirectory"] = str(config.working_directory)

        if config.environment:
            plist_dict["EnvironmentVariables"] = config.environment

        if config.user:
            plist_dict["UserName"] = config.user

        if config.group:
            plist_dict["GroupName"] = config.group

        # Convert to plist XML format
        import plistlib

        return plistlib.dumps(plist_dict).decode("utf-8")

    def install_service(self, service_name: str) -> bool:
        """Install a launchd service."""
        if service_name not in self.services:
            logger.error(f"Service {service_name} not registered")
            return False

        config = self.services[service_name]

        try:
            # Generate plist content
            plist_content = self._generate_plist(config)

            # Write plist file
            plist_path = self.plist_dir / f"com.giljo.{service_name}.plist"
            with open(plist_path, "w") as f:
                f.write(plist_content)

            # Load the service
            cmd = ["launchctl", "load", str(plist_path)]
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                logger.info(f"Service {service_name} installed successfully")
                return True
            else:
                logger.error(f"Failed to load service: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"Failed to install service {service_name}: {str(e)}")
            return False

    def uninstall_service(self, service_name: str) -> bool:
        """Uninstall a launchd service."""
        try:
            plist_path = self.plist_dir / f"com.giljo.{service_name}.plist"

            # Unload the service
            if plist_path.exists():
                cmd = ["launchctl", "unload", str(plist_path)]
                subprocess.run(cmd, capture_output=True, text=True)

                # Remove plist file
                plist_path.unlink()

            logger.info(f"Service {service_name} uninstalled successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to uninstall service {service_name}: {str(e)}")
            return False

    def start_service(self, service_name: str) -> bool:
        """Start a launchd service."""
        try:
            cmd = ["launchctl", "start", f"com.giljo.{service_name}"]
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                logger.info(f"Service {service_name} started")
                return True
            else:
                logger.error(f"Failed to start service: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"Failed to start service {service_name}: {str(e)}")
            return False

    def stop_service(self, service_name: str) -> bool:
        """Stop a launchd service."""
        try:
            cmd = ["launchctl", "stop", f"com.giljo.{service_name}"]
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                logger.info(f"Service {service_name} stopped")
                return True
            else:
                logger.error(f"Failed to stop service: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"Failed to stop service {service_name}: {str(e)}")
            return False

    def restart_service(self, service_name: str) -> bool:
        """Restart a launchd service."""
        if self.stop_service(service_name):
            time.sleep(2)
            return self.start_service(service_name)
        return False

    def get_service_status(self, service_name: str) -> ServiceStatus:
        """Get the status of a launchd service."""
        try:
            cmd = ["launchctl", "list", f"com.giljo.{service_name}"]
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode != 0:
                plist_path = self.plist_dir / f"com.giljo.{service_name}.plist"
                if not plist_path.exists():
                    return ServiceStatus.NOT_INSTALLED
                return ServiceStatus.STOPPED

            # Parse output to determine status
            # launchctl list output format: PID Status Label
            lines = result.stdout.strip().split("\n")
            if len(lines) > 0:
                parts = lines[0].split("\t")
                if len(parts) >= 1:
                    pid = parts[0]
                    if pid != "-":
                        return ServiceStatus.RUNNING

            return ServiceStatus.STOPPED

        except Exception as e:
            logger.error(f"Failed to get service status: {str(e)}")
            return ServiceStatus.UNKNOWN

    def enable_service(self, service_name: str) -> bool:
        """Enable a launchd service to start at boot."""
        if service_name not in self.services:
            return False

        config = self.services[service_name]
        config.auto_start = True

        # Reinstall with updated config
        self.uninstall_service(service_name)
        return self.install_service(service_name)

    def disable_service(self, service_name: str) -> bool:
        """Disable a launchd service from starting at boot."""
        if service_name not in self.services:
            return False

        config = self.services[service_name]
        config.auto_start = False

        # Reinstall with updated config
        self.uninstall_service(service_name)
        return self.install_service(service_name)


class LinuxServiceManager(ServiceManager):
    """Linux service manager using systemd."""

    def __init__(self):
        """Initialize Linux service manager."""
        super().__init__()
        self.unit_dir = Path("/etc/systemd/system")
        self.user_unit_dir = Path.home() / ".config" / "systemd" / "user"
        self.service_script_dir = Path(__file__).parent / "linux"

        # Detect if running with sudo/root
        self.is_root = os.geteuid() == 0

        if not self.is_root:
            self.user_unit_dir.mkdir(parents=True, exist_ok=True)

    def _generate_unit_file(self, config: ServiceConfig) -> str:
        """Generate systemd unit file content."""
        unit_content = f"""[Unit]
Description={config.description}
After=network.target
"""

        # Add dependencies
        if config.dependencies:
            for dep in config.dependencies:
                unit_content += f"After={dep}.service\n"
                unit_content += f"Wants={dep}.service\n"

        unit_content += f"""
[Service]
Type=simple
ExecStart={config.executable} {' '.join(config.arguments)}
Restart={'always' if config.restart_on_failure else 'no'}
RestartSec={config.restart_delay}
"""

        if config.working_directory:
            unit_content += f"WorkingDirectory={config.working_directory}\n"

        if config.user:
            unit_content += f"User={config.user}\n"

        if config.group:
            unit_content += f"Group={config.group}\n"

        if config.environment:
            for key, value in config.environment.items():
                unit_content += f'Environment="{key}={value}"\n'

        if config.pid_file:
            unit_content += f"PIDFile={config.pid_file}\n"

        unit_content += f"""
StandardOutput=journal
StandardError=journal

[Install]
WantedBy={'multi-user.target' if self.is_root else 'default.target'}
"""

        return unit_content

    def install_service(self, service_name: str) -> bool:
        """Install a systemd service."""
        if service_name not in self.services:
            logger.error(f"Service {service_name} not registered")
            return False

        config = self.services[service_name]

        try:
            # Generate unit file content
            unit_content = self._generate_unit_file(config)

            # Determine unit file path
            if self.is_root:
                unit_path = self.unit_dir / f"{service_name}.service"
            else:
                unit_path = self.user_unit_dir / f"{service_name}.service"

            # Write unit file
            with open(unit_path, "w") as f:
                f.write(unit_content)

            # Reload systemd
            systemctl_cmd = ["systemctl"] if self.is_root else ["systemctl", "--user"]
            reload_cmd = systemctl_cmd + ["daemon-reload"]
            subprocess.run(reload_cmd, capture_output=True)

            # Enable service if auto_start is True
            if config.auto_start:
                enable_cmd = systemctl_cmd + ["enable", f"{service_name}.service"]
                subprocess.run(enable_cmd, capture_output=True)

            logger.info(f"Service {service_name} installed successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to install service {service_name}: {str(e)}")
            return False

    def uninstall_service(self, service_name: str) -> bool:
        """Uninstall a systemd service."""
        try:
            systemctl_cmd = ["systemctl"] if self.is_root else ["systemctl", "--user"]

            # Stop and disable service
            self.stop_service(service_name)
            disable_cmd = systemctl_cmd + ["disable", f"{service_name}.service"]
            subprocess.run(disable_cmd, capture_output=True)

            # Remove unit file
            if self.is_root:
                unit_path = self.unit_dir / f"{service_name}.service"
            else:
                unit_path = self.user_unit_dir / f"{service_name}.service"

            if unit_path.exists():
                unit_path.unlink()

            # Reload systemd
            reload_cmd = systemctl_cmd + ["daemon-reload"]
            subprocess.run(reload_cmd, capture_output=True)

            logger.info(f"Service {service_name} uninstalled successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to uninstall service {service_name}: {str(e)}")
            return False

    def start_service(self, service_name: str) -> bool:
        """Start a systemd service."""
        try:
            systemctl_cmd = ["systemctl"] if self.is_root else ["systemctl", "--user"]
            cmd = systemctl_cmd + ["start", f"{service_name}.service"]
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                logger.info(f"Service {service_name} started")
                return True
            else:
                logger.error(f"Failed to start service: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"Failed to start service {service_name}: {str(e)}")
            return False

    def stop_service(self, service_name: str) -> bool:
        """Stop a systemd service."""
        try:
            systemctl_cmd = ["systemctl"] if self.is_root else ["systemctl", "--user"]
            cmd = systemctl_cmd + ["stop", f"{service_name}.service"]
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                logger.info(f"Service {service_name} stopped")
                return True
            else:
                logger.error(f"Failed to stop service: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"Failed to stop service {service_name}: {str(e)}")
            return False

    def restart_service(self, service_name: str) -> bool:
        """Restart a systemd service."""
        try:
            systemctl_cmd = ["systemctl"] if self.is_root else ["systemctl", "--user"]
            cmd = systemctl_cmd + ["restart", f"{service_name}.service"]
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                logger.info(f"Service {service_name} restarted")
                return True
            else:
                logger.error(f"Failed to restart service: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"Failed to restart service {service_name}: {str(e)}")
            return False

    def get_service_status(self, service_name: str) -> ServiceStatus:
        """Get the status of a systemd service."""
        try:
            systemctl_cmd = ["systemctl"] if self.is_root else ["systemctl", "--user"]
            cmd = systemctl_cmd + ["is-active", f"{service_name}.service"]
            result = subprocess.run(cmd, capture_output=True, text=True)

            status = result.stdout.strip().lower()

            if status == "active":
                return ServiceStatus.RUNNING
            elif status == "inactive":
                return ServiceStatus.STOPPED
            elif status == "activating":
                return ServiceStatus.STARTING
            elif status == "deactivating":
                return ServiceStatus.STOPPING
            elif status == "failed":
                return ServiceStatus.FAILED
            else:
                # Check if service exists
                check_cmd = systemctl_cmd + ["status", f"{service_name}.service"]
                check_result = subprocess.run(check_cmd, capture_output=True, text=True)

                if "could not be found" in check_result.stderr.lower():
                    return ServiceStatus.NOT_INSTALLED

                return ServiceStatus.UNKNOWN

        except Exception as e:
            logger.error(f"Failed to get service status: {str(e)}")
            return ServiceStatus.UNKNOWN

    def enable_service(self, service_name: str) -> bool:
        """Enable a systemd service to start at boot."""
        try:
            systemctl_cmd = ["systemctl"] if self.is_root else ["systemctl", "--user"]
            cmd = systemctl_cmd + ["enable", f"{service_name}.service"]
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                logger.info(f"Service {service_name} enabled")
                return True
            else:
                logger.error(f"Failed to enable service: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"Failed to enable service {service_name}: {str(e)}")
            return False

    def disable_service(self, service_name: str) -> bool:
        """Disable a systemd service from starting at boot."""
        try:
            systemctl_cmd = ["systemctl"] if self.is_root else ["systemctl", "--user"]
            cmd = systemctl_cmd + ["disable", f"{service_name}.service"]
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                logger.info(f"Service {service_name} disabled")
                return True
            else:
                logger.error(f"Failed to disable service: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"Failed to disable service {service_name}: {str(e)}")
            return False


def get_platform_service_manager() -> ServiceManager:
    """
    Factory function to get the appropriate service manager for the current platform.

    Returns:
        Platform-specific ServiceManager instance.
    """
    system = platform.system().lower()

    if system == "windows":
        return WindowsServiceManager()
    elif system == "darwin":
        return MacOSServiceManager()
    elif system == "linux":
        return LinuxServiceManager()
    else:
        raise NotImplementedError(f"Unsupported platform: {system}")


def create_giljo_services() -> Dict[str, ServiceConfig]:
    """
    Create default service configurations for GiljoAI MCP components.

    Returns:
        Dictionary of service configurations.
    """
    base_path = Path.home() / ".giljo_mcp"

    services = {
        "giljo_postgresql": ServiceConfig(
            name="giljo_postgresql",
            display_name="GiljoAI PostgreSQL",
            description="PostgreSQL database for GiljoAI MCP",
            service_type=ServiceType.POSTGRESQL,
            executable=(
                Path("C:/Program Files/PostgreSQL/15/bin/pg_ctl.exe")
                if platform.system() == "Windows"
                else Path("/usr/lib/postgresql/15/bin/pg_ctl")
            ),
            arguments=["start", "-D", str(base_path / "data" / "postgresql")],
            working_directory=base_path / "data" / "postgresql",
            environment={"PGDATA": str(base_path / "data" / "postgresql")},
            log_file=base_path / "logs" / "postgresql.log",
            pid_file=base_path / "run" / "postgresql.pid",
        ),
        "giljo_redis": ServiceConfig(
            name="giljo_redis",
            display_name="GiljoAI Redis",
            description="Redis cache for GiljoAI MCP",
            service_type=ServiceType.REDIS,
            executable=(
                Path("C:/Program Files/Redis/redis-server.exe")
                if platform.system() == "Windows"
                else Path("/usr/bin/redis-server")
            ),
            arguments=[str(base_path / "config" / "redis.conf")],
            working_directory=base_path / "data" / "redis",
            log_file=base_path / "logs" / "redis.log",
            pid_file=base_path / "run" / "redis.pid",
        ),
        "giljo_app": ServiceConfig(
            name="giljo_app",
            display_name="GiljoAI MCP Application",
            description="Main GiljoAI MCP application server",
            service_type=ServiceType.GILJO_APP,
            executable=sys.executable,
            arguments=["-m", "src.giljo_mcp.server"],
            working_directory=base_path,
            environment={
                "GILJO_CONFIG_DIR": str(base_path / "config"),
                "GILJO_DATA_DIR": str(base_path / "data"),
                "GILJO_LOG_DIR": str(base_path / "logs"),
            },
            dependencies=["giljo_postgresql", "giljo_redis"],
            log_file=base_path / "logs" / "giljo_app.log",
            pid_file=base_path / "run" / "giljo_app.pid",
        ),
        "giljo_worker": ServiceConfig(
            name="giljo_worker",
            display_name="GiljoAI MCP Worker",
            description="Background worker for GiljoAI MCP",
            service_type=ServiceType.GILJO_WORKER,
            executable=sys.executable,
            arguments=["-m", "src.giljo_mcp.worker"],
            working_directory=base_path,
            environment={
                "GILJO_CONFIG_DIR": str(base_path / "config"),
                "GILJO_DATA_DIR": str(base_path / "data"),
                "GILJO_LOG_DIR": str(base_path / "logs"),
            },
            dependencies=["giljo_postgresql", "giljo_redis", "giljo_app"],
            log_file=base_path / "logs" / "giljo_worker.log",
            pid_file=base_path / "run" / "giljo_worker.pid",
            auto_start=False,  # Worker is optional
        ),
    }

    return services


def main():
    """Main function for testing the service manager."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # Get platform-specific service manager
    manager = get_platform_service_manager()
    print(f"Using {manager.__class__.__name__} on {platform.system()}")

    # Create default service configurations
    services = create_giljo_services()

    # Register services
    for service_config in services.values():
        manager.register_service(service_config)

    # Display service status
    print("\nRegistered Services:")
    print("-" * 40)

    statuses = manager.get_all_services()
    for name, status in statuses.items():
        print(f"{name:20} {status.value}")

    # Interactive menu
    while True:
        print("\n" + "=" * 40)
        print("Service Manager Menu")
        print("=" * 40)
        print("1. Install all services")
        print("2. Start all services")
        print("3. Stop all services")
        print("4. Check service status")
        print("5. Start specific service")
        print("6. Stop specific service")
        print("7. Uninstall all services")
        print("0. Exit")

        choice = input("\nEnter choice: ").strip()

        if choice == "0":
            break
        elif choice == "1":
            print("\nInstalling services...")
            for service_name in services:
                result = manager.install_service(service_name)
                print(f"  {service_name}: {'✓' if result else '✗'}")
        elif choice == "2":
            print("\nStarting services...")
            results = manager.start_all_services()
            for name, success in results.items():
                print(f"  {name}: {'✓' if success else '✗'}")
        elif choice == "3":
            print("\nStopping services...")
            results = manager.stop_all_services()
            for name, success in results.items():
                print(f"  {name}: {'✓' if success else '✗'}")
        elif choice == "4":
            print("\nService Status:")
            statuses = manager.get_all_services()
            for name, status in statuses.items():
                print(f"  {name:20} {status.value}")
        elif choice == "5":
            service = input("Enter service name: ").strip()
            if service in services:
                result = manager.start_service(service)
                print(f"Start {service}: {'✓' if result else '✗'}")
            else:
                print(f"Unknown service: {service}")
        elif choice == "6":
            service = input("Enter service name: ").strip()
            if service in services:
                result = manager.stop_service(service)
                print(f"Stop {service}: {'✓' if result else '✗'}")
            else:
                print(f"Unknown service: {service}")
        elif choice == "7":
            print("\nUninstalling services...")
            for service_name in reversed(list(services.keys())):
                result = manager.uninstall_service(service_name)
                print(f"  {service_name}: {'✓' if result else '✗'}")
        else:
            print("Invalid choice")


if __name__ == "__main__":
    sys.exit(main())
