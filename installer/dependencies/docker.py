"""
Docker Installer for Windows, macOS, and Linux

This module provides automated Docker installation guidance and verification
for all major platforms, including Docker Desktop and Docker Engine.
"""

import os
import sys
import json
import time
import logging
import platform
import subprocess
import tempfile
import webbrowser
from pathlib import Path
from typing import Dict, Optional, Tuple, Any, List
from dataclasses import dataclass, field
from enum import Enum


# Configure logging
logger = logging.getLogger(__name__)


class InstallationStatus(Enum):
    """Docker installation status codes."""

    NOT_STARTED = "not_started"
    CHECKING = "checking"
    DOWNLOADING = "downloading"
    INSTALLING = "installing"
    CONFIGURING = "configuring"
    TESTING = "testing"
    COMPLETED = "completed"
    FAILED = "failed"
    USER_ACTION_REQUIRED = "user_action_required"


class DockerPlatform(Enum):
    """Supported Docker platforms."""

    WINDOWS = "windows"
    MACOS = "macos"
    LINUX = "linux"


class DockerEdition(Enum):
    """Docker editions available."""

    DESKTOP = "desktop"  # Windows/Mac
    ENGINE = "engine"  # Linux
    TOOLBOX = "toolbox"  # Legacy for older Windows/Mac


@dataclass
class DockerConfig:
    """Docker installation configuration."""

    # Installation preferences
    edition: Optional[DockerEdition] = None  # Auto-detect if not specified
    install_compose: bool = True
    compose_version: str = "2.23.3"

    # Resource limits
    memory_limit: str = "2GB"
    cpu_limit: int = 2
    disk_size: str = "20GB"

    # Network configuration
    use_default_bridge: bool = True
    custom_networks: List[str] = field(default_factory=list)
    insecure_registries: List[str] = field(default_factory=list)
    registry_mirrors: List[str] = field(default_factory=list)

    # Storage
    data_root: Optional[Path] = None  # Docker data directory

    # WSL2 settings (Windows only)
    use_wsl2: bool = True
    wsl_distro: str = "docker-desktop"

    # Proxy settings
    http_proxy: Optional[str] = None
    https_proxy: Optional[str] = None
    no_proxy: Optional[str] = "localhost,127.0.0.1"

    # User settings (Linux)
    add_user_to_docker_group: bool = True
    docker_group: str = "docker"

    # Daemon configuration
    experimental: bool = False
    debug: bool = False
    log_level: str = "info"
    log_driver: str = "json-file"
    log_opts: Dict[str, str] = field(default_factory=lambda: {"max-size": "10m", "max-file": "3"})


class DockerInstaller:
    """
    Docker installer for Windows, macOS, and Linux systems.

    Handles Docker Desktop installation guidance for Windows/Mac
    and Docker Engine installation for Linux systems.
    """

    # Docker Desktop download URLs
    DOCKER_DESKTOP_URLS = {
        "windows": {
            "stable": "https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe",
            "edge": "https://desktop.docker.com/win/edge/amd64/Docker%20Desktop%20Installer.exe",
        },
        "macos": {
            "intel": "https://desktop.docker.com/mac/main/amd64/Docker.dmg",
            "apple": "https://desktop.docker.com/mac/main/arm64/Docker.dmg",
            "edge_intel": "https://desktop.docker.com/mac/edge/amd64/Docker.dmg",
            "edge_apple": "https://desktop.docker.com/mac/edge/arm64/Docker.dmg",
        },
    }

    # Docker Compose download URLs
    COMPOSE_URLS = {
        "windows": "https://github.com/docker/compose/releases/download/v{version}/docker-compose-windows-x86_64.exe",
        "linux": "https://github.com/docker/compose/releases/download/v{version}/docker-compose-linux-x86_64",
        "macos_intel": "https://github.com/docker/compose/releases/download/v{version}/docker-compose-darwin-x86_64",
        "macos_apple": "https://github.com/docker/compose/releases/download/v{version}/docker-compose-darwin-aarch64",
    }

    # Documentation URLs
    DOCS_URLS = {
        "windows_install": "https://docs.docker.com/desktop/install/windows-install/",
        "mac_install": "https://docs.docker.com/desktop/install/mac-install/",
        "linux_install": "https://docs.docker.com/engine/install/",
        "compose_install": "https://docs.docker.com/compose/install/",
        "troubleshooting": "https://docs.docker.com/desktop/troubleshoot/overview/",
    }

    def __init__(self, config: Optional[DockerConfig] = None):
        """
        Initialize Docker installer.

        Args:
            config: Optional configuration object. Uses defaults if not provided.
        """
        self.config = config or DockerConfig()
        self.status = InstallationStatus.NOT_STARTED
        self.progress = 0
        self.message = ""
        self.platform = self._detect_platform()
        self.docker_info: Optional[Dict[str, Any]] = None

        # Set appropriate edition based on platform
        if not self.config.edition:
            if self.platform in [DockerPlatform.WINDOWS, DockerPlatform.MACOS]:
                self.config.edition = DockerEdition.DESKTOP
            else:
                self.config.edition = DockerEdition.ENGINE

        # Ensure required directories exist
        self.temp_dir = Path(tempfile.gettempdir()) / "giljo_mcp_installer"
        self.temp_dir.mkdir(parents=True, exist_ok=True)

        # Set up logging
        self._setup_logging()

    def _setup_logging(self):
        """Configure logging for the installer."""
        log_file = self.temp_dir / "docker_install.log"
        handler = logging.FileHandler(log_file)
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)

    def _detect_platform(self) -> DockerPlatform:
        """
        Detect the current operating system platform.

        Returns:
            DockerPlatform enum value.
        """
        system = platform.system().lower()

        if system == "windows":
            return DockerPlatform.WINDOWS
        elif system == "darwin":
            return DockerPlatform.MACOS
        elif system == "linux":
            return DockerPlatform.LINUX
        else:
            raise ValueError(f"Unsupported platform: {system}")

    def is_docker_installed(self) -> bool:
        """
        Check if Docker is already installed.

        Returns:
            True if Docker is installed, False otherwise.
        """
        self.status = InstallationStatus.CHECKING
        self.message = "Checking for existing Docker installation..."
        logger.info(self.message)

        try:
            # Try to run docker version command
            result = subprocess.run(
                ["docker", "version", "--format", "json"], capture_output=True, text=True, timeout=10
            )

            if result.returncode == 0:
                logger.info("Docker is installed")

                # Parse version info
                try:
                    version_info = json.loads(result.stdout)
                    self.docker_info = version_info
                    logger.info(f"Docker version: {version_info.get('Client', {}).get('Version', 'unknown')}")
                except json.JSONDecodeError:
                    # Try non-JSON format
                    result = subprocess.run(["docker", "version"], capture_output=True, text=True, timeout=10)
                    logger.info(f"Docker version output: {result.stdout}")

                return True
            else:
                logger.info("Docker command failed, not installed or not in PATH")
                return False

        except FileNotFoundError:
            logger.info("Docker executable not found")
            return False
        except subprocess.TimeoutExpired:
            logger.warning("Docker version check timed out")
            return False
        except Exception as e:
            logger.error(f"Error checking Docker installation: {str(e)}")
            return False

    def is_docker_running(self) -> bool:
        """
        Check if Docker daemon is running.

        Returns:
            True if Docker daemon is running, False otherwise.
        """
        if not self.is_docker_installed():
            return False

        try:
            # Try to connect to Docker daemon
            result = subprocess.run(["docker", "info"], capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                logger.info("Docker daemon is running")
                return True
            else:
                logger.info(f"Docker daemon not running: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            logger.warning("Docker info check timed out")
            return False
        except Exception as e:
            logger.error(f"Error checking Docker daemon: {str(e)}")
            return False

    def is_compose_installed(self) -> Tuple[bool, Optional[str]]:
        """
        Check if docker-compose is installed.

        Returns:
            Tuple of (installed, version).
        """
        # Try docker compose (v2)
        try:
            result = subprocess.run(["docker", "compose", "version"], capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                # Parse version from output
                output = result.stdout.strip()
                if "version" in output.lower():
                    version = output.split()[-1]
                    logger.info(f"Docker Compose v2 found: {version}")
                    return True, version
        except:
            pass

        # Try docker-compose (v1)
        try:
            result = subprocess.run(["docker-compose", "--version"], capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                # Parse version from output
                output = result.stdout.strip()
                if "version" in output.lower():
                    version = output.split()[2].rstrip(",")
                    logger.info(f"Docker Compose v1 found: {version}")
                    return True, version
        except:
            pass

        logger.info("Docker Compose not found")
        return False, None

    def get_installation_guide(self) -> Dict[str, Any]:
        """
        Get platform-specific installation guide.

        Returns:
            Dictionary with installation instructions and URLs.
        """
        guide = {
            "platform": self.platform.value,
            "edition": self.config.edition.value,
            "steps": [],
            "urls": {},
            "requirements": [],
            "notes": [],
        }

        if self.platform == DockerPlatform.WINDOWS:
            guide["requirements"] = [
                "Windows 10 64-bit: Pro, Enterprise, or Education (Build 19041 or higher)",
                "Or Windows 11 64-bit",
                "Enable WSL 2 feature",
                "64-bit processor with SLAT",
                "4GB RAM minimum",
                "BIOS virtualization enabled",
            ]

            guide["steps"] = [
                "Download Docker Desktop Installer",
                "Run installer as Administrator",
                "Follow installation wizard",
                "Enable WSL 2 when prompted",
                "Restart computer when required",
                "Start Docker Desktop from Start menu",
                "Wait for Docker to initialize",
                "Verify installation with 'docker version'",
            ]

            guide["urls"] = {
                "download": self.DOCKER_DESKTOP_URLS["windows"]["stable"],
                "documentation": self.DOCS_URLS["windows_install"],
                "wsl_install": "https://docs.microsoft.com/en-us/windows/wsl/install",
            }

            guide["notes"] = [
                "WSL 2 provides better performance than Hyper-V backend",
                "Docker Desktop includes Docker Compose",
                "May require Windows restart after installation",
            ]

        elif self.platform == DockerPlatform.MACOS:
            # Detect Apple Silicon vs Intel
            is_apple_silicon = platform.processor() == "arm"

            guide["requirements"] = [
                "macOS 11 Big Sur or newer" if is_apple_silicon else "macOS 10.15 Catalina or newer",
                "4GB RAM minimum",
                "VirtualBox prior to version 4.3.30 must NOT be installed",
            ]

            guide["steps"] = [
                "Download Docker Desktop for Mac",
                "Double-click Docker.dmg to open installer",
                "Drag Docker.app to Applications folder",
                "Open Docker.app from Applications",
                "Authorize Docker with your system password",
                "Wait for Docker to start",
                "Click Docker icon in menu bar to verify",
                "Test with 'docker version' in Terminal",
            ]

            download_key = "apple" if is_apple_silicon else "intel"
            guide["urls"] = {
                "download": self.DOCKER_DESKTOP_URLS["macos"][download_key],
                "documentation": self.DOCS_URLS["mac_install"],
            }

            guide["notes"] = [
                f"Using {'Apple Silicon' if is_apple_silicon else 'Intel'} version",
                "Docker Desktop includes Docker Compose",
                "Requires macOS administrator access",
            ]

        elif self.platform == DockerPlatform.LINUX:
            # Detect Linux distribution
            distro = self._detect_linux_distro()

            guide["requirements"] = [
                "64-bit Linux kernel 3.10 or higher",
                "iptables 1.4 or higher",
                "git 1.7 or higher",
                "xz-utils",
                "sudo privileges",
            ]

            if distro in ["ubuntu", "debian"]:
                guide["steps"] = [
                    "Update package index: sudo apt-get update",
                    "Install prerequisites: sudo apt-get install ca-certificates curl gnupg lsb-release",
                    "Add Docker's GPG key: curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg",
                    "Set up stable repository",
                    "Install Docker Engine: sudo apt-get install docker-ce docker-ce-cli containerd.io",
                    "Add user to docker group: sudo usermod -aG docker $USER",
                    "Log out and back in for group changes",
                    "Verify: docker run hello-world",
                ]
            elif distro in ["centos", "rhel", "fedora"]:
                guide["steps"] = [
                    "Remove old versions: sudo yum remove docker docker-client docker-client-latest docker-common docker-latest docker-latest-logrotate docker-logrotate docker-engine",
                    "Install yum-utils: sudo yum install -y yum-utils",
                    "Add Docker repository: sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo",
                    "Install Docker Engine: sudo yum install docker-ce docker-ce-cli containerd.io",
                    "Start Docker: sudo systemctl start docker",
                    "Enable Docker: sudo systemctl enable docker",
                    "Add user to docker group: sudo usermod -aG docker $USER",
                    "Verify: docker run hello-world",
                ]
            else:
                guide["steps"] = [
                    "Visit Docker documentation for your distribution",
                    "Follow distribution-specific installation steps",
                    "Install Docker Engine and containerd",
                    "Configure Docker daemon",
                    "Add user to docker group",
                    "Start and enable Docker service",
                    "Verify installation",
                ]

            guide["urls"] = {
                "documentation": self.DOCS_URLS["linux_install"],
                "compose": self.DOCS_URLS["compose_install"],
            }

            guide["notes"] = [
                f"Detected distribution: {distro}",
                "Docker Compose must be installed separately on Linux",
                "Requires logout/login after adding user to docker group",
            ]

        return guide

    def _detect_linux_distro(self) -> str:
        """
        Detect Linux distribution.

        Returns:
            Distribution name or "unknown".
        """
        try:
            # Try to read /etc/os-release
            if Path("/etc/os-release").exists():
                with open("/etc/os-release", "r") as f:
                    lines = f.readlines()
                    for line in lines:
                        if line.startswith("ID="):
                            distro = line.split("=")[1].strip().strip('"')
                            return distro.lower()

            # Fallback to platform module
            import distro

            return distro.id().lower()
        except:
            return "unknown"

    def open_download_page(self) -> bool:
        """
        Open Docker download page in default browser.

        Returns:
            True if page opened successfully, False otherwise.
        """
        guide = self.get_installation_guide()

        if "download" in guide.get("urls", {}):
            url = guide["urls"]["download"]
            logger.info(f"Opening download page: {url}")

            try:
                webbrowser.open(url)
                self.status = InstallationStatus.USER_ACTION_REQUIRED
                self.message = "Download page opened. Please follow installation instructions."
                return True
            except Exception as e:
                logger.error(f"Failed to open download page: {str(e)}")
                return False

        return False

    def wait_for_installation(self, timeout: int = 1800, check_interval: int = 30, progress_callback=None) -> bool:
        """
        Wait for user to complete Docker installation.

        Args:
            timeout: Maximum time to wait in seconds (default 30 minutes).
            check_interval: How often to check for installation in seconds.
            progress_callback: Optional callback for progress updates.

        Returns:
            True if Docker is installed and running, False otherwise.
        """
        self.status = InstallationStatus.USER_ACTION_REQUIRED
        self.message = "Waiting for Docker installation to complete..."
        logger.info(self.message)

        start_time = time.time()

        while time.time() - start_time < timeout:
            # Check if Docker is now installed
            if self.is_docker_installed():
                self.message = "Docker installed! Waiting for daemon to start..."
                logger.info(self.message)

                # Give Docker time to start
                daemon_start_time = time.time()
                while time.time() - daemon_start_time < 120:  # 2 minutes for daemon
                    if self.is_docker_running():
                        self.status = InstallationStatus.COMPLETED
                        self.message = "Docker is installed and running!"
                        self.progress = 100
                        if progress_callback:
                            progress_callback(100, self.message)
                        return True

                    time.sleep(5)
                    if progress_callback:
                        elapsed = int(time.time() - daemon_start_time)
                        progress_callback(50 + int(elapsed * 50 / 120), f"Waiting for Docker daemon... {elapsed}s")

                # Docker installed but daemon won't start
                self.status = InstallationStatus.FAILED
                self.message = "Docker installed but daemon failed to start"
                logger.error(self.message)
                return False

            # Update progress
            elapsed = int(time.time() - start_time)
            self.progress = min(50, int(elapsed * 50 / timeout))

            if progress_callback:
                remaining = timeout - elapsed
                progress_callback(self.progress, f"Waiting for installation... {remaining}s remaining")

            time.sleep(check_interval)

        self.status = InstallationStatus.FAILED
        self.message = "Installation timeout - Docker not detected"
        logger.error(self.message)
        return False

    def install_compose(self, progress_callback=None) -> bool:
        """
        Install Docker Compose if not present.

        Args:
            progress_callback: Optional callback for progress updates.

        Returns:
            True if Compose is installed, False otherwise.
        """
        # Check if already installed
        installed, version = self.is_compose_installed()
        if installed:
            logger.info(f"Docker Compose already installed: {version}")
            return True

        if self.platform == DockerPlatform.LINUX:
            self.message = "Installing Docker Compose..."
            logger.info(self.message)

            try:
                # Determine architecture
                machine = platform.machine().lower()
                if machine in ["amd64", "x86_64"]:
                    compose_url = self.COMPOSE_URLS["linux"].format(version=self.config.compose_version)
                else:
                    logger.error(f"Unsupported architecture for Compose: {machine}")
                    return False

                # Download docker-compose
                import urllib.request
                import socket

                compose_path = Path("/usr/local/bin/docker-compose")
                temp_path = self.temp_dir / "docker-compose"

                if progress_callback:
                    progress_callback(10, "Downloading Docker Compose...")

                # Set timeout for download
                old_timeout = socket.getdefaulttimeout()
                socket.setdefaulttimeout(30.0)
                try:
                    urllib.request.urlretrieve(compose_url, temp_path)
                finally:
                    socket.setdefaulttimeout(old_timeout)

                if progress_callback:
                    progress_callback(50, "Installing Docker Compose...")

                # Make executable and move to /usr/local/bin
                subprocess.run(["chmod", "+x", str(temp_path)], check=True)
                subprocess.run(["sudo", "mv", str(temp_path), str(compose_path)], check=True)

                if progress_callback:
                    progress_callback(90, "Verifying Docker Compose...")

                # Verify installation
                installed, version = self.is_compose_installed()
                if installed:
                    logger.info(f"Docker Compose installed successfully: {version}")
                    if progress_callback:
                        progress_callback(100, "Docker Compose installed!")
                    return True
                else:
                    logger.error("Docker Compose installation verification failed")
                    return False

            except Exception as e:
                logger.error(f"Failed to install Docker Compose: {str(e)}")
                return False
        else:
            # Docker Desktop includes Compose
            logger.info("Docker Compose included with Docker Desktop")
            return True

    def test_docker(self) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Test Docker installation by running a test container.

        Returns:
            Tuple of (success, test_results).
        """
        self.status = InstallationStatus.TESTING
        self.message = "Testing Docker installation..."
        logger.info(self.message)

        test_results = {
            "docker_installed": False,
            "daemon_running": False,
            "compose_installed": False,
            "container_test": False,
            "version": None,
            "compose_version": None,
            "errors": [],
        }

        # Test Docker installation
        test_results["docker_installed"] = self.is_docker_installed()
        if not test_results["docker_installed"]:
            test_results["errors"].append("Docker not installed or not in PATH")
            return False, test_results

        # Test Docker daemon
        test_results["daemon_running"] = self.is_docker_running()
        if not test_results["daemon_running"]:
            test_results["errors"].append("Docker daemon not running")
            return False, test_results

        # Get Docker version
        try:
            result = subprocess.run(
                ["docker", "version", "--format", "{{.Server.Version}}"], capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                test_results["version"] = result.stdout.strip()
        except:
            pass

        # Test Docker Compose
        installed, version = self.is_compose_installed()
        test_results["compose_installed"] = installed
        test_results["compose_version"] = version

        # Test container creation
        try:
            logger.info("Running hello-world container test")
            result = subprocess.run(
                ["docker", "run", "--rm", "hello-world"], capture_output=True, text=True, timeout=60
            )

            if result.returncode == 0 and "Hello from Docker!" in result.stdout:
                test_results["container_test"] = True
                logger.info("Container test successful")
            else:
                test_results["errors"].append("Container test failed")
                logger.error(f"Container test failed: {result.stderr}")
        except subprocess.TimeoutExpired:
            test_results["errors"].append("Container test timeout")
            logger.error("Container test timed out")
        except Exception as e:
            test_results["errors"].append(f"Container test error: {str(e)}")
            logger.error(f"Container test error: {str(e)}")

        # Overall success
        success = all(
            [test_results["docker_installed"], test_results["daemon_running"], test_results["container_test"]]
        )

        if success:
            self.status = InstallationStatus.COMPLETED
            self.message = "Docker installation verified successfully"
            self.progress = 100
        else:
            self.status = InstallationStatus.FAILED
            self.message = f"Docker test failed: {', '.join(test_results['errors'])}"

        return success, test_results

    def configure_docker(self) -> bool:
        """
        Apply Docker daemon configuration.

        Returns:
            True if configuration succeeds, False otherwise.
        """
        self.status = InstallationStatus.CONFIGURING
        self.message = "Configuring Docker daemon..."
        logger.info(self.message)

        daemon_config = {
            "debug": self.config.debug,
            "experimental": self.config.experimental,
            "log-level": self.config.log_level,
            "log-driver": self.config.log_driver,
            "log-opts": self.config.log_opts,
            "max-concurrent-downloads": 3,
            "max-concurrent-uploads": 5,
            "default-address-pools": [{"base": "172.30.0.0/16", "size": 24}, {"base": "172.31.0.0/16", "size": 24}],
        }

        # Add optional configurations
        if self.config.data_root:
            daemon_config["data-root"] = str(self.config.data_root)

        if self.config.insecure_registries:
            daemon_config["insecure-registries"] = self.config.insecure_registries

        if self.config.registry_mirrors:
            daemon_config["registry-mirrors"] = self.config.registry_mirrors

        # Platform-specific configuration paths
        if self.platform == DockerPlatform.WINDOWS:
            config_path = Path.home() / ".docker" / "daemon.json"
        elif self.platform == DockerPlatform.MACOS:
            config_path = Path.home() / ".docker" / "daemon.json"
        else:  # Linux
            config_path = Path("/etc/docker/daemon.json")

        try:
            # Backup existing configuration
            if config_path.exists():
                backup_path = config_path.with_suffix(".json.backup")
                import shutil

                shutil.copy2(config_path, backup_path)
                logger.info(f"Backed up existing config to {backup_path}")

                # Merge with existing config
                with open(config_path, "r") as f:
                    existing = json.load(f)
                    daemon_config.update(existing)

            # Write configuration
            config_path.parent.mkdir(parents=True, exist_ok=True)

            with open(config_path, "w") as f:
                json.dump(daemon_config, f, indent=2)

            logger.info(f"Docker daemon configuration written to {config_path}")

            # Restart Docker to apply configuration
            if self.platform == DockerPlatform.LINUX:
                try:
                    subprocess.run(["sudo", "systemctl", "restart", "docker"], check=True)
                    logger.info("Docker daemon restarted")
                except:
                    logger.warning("Could not restart Docker daemon automatically")

            return True

        except Exception as e:
            logger.error(f"Failed to configure Docker: {str(e)}")
            return False

    def install(self, progress_callback=None) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Main installation entry point.

        Guides user through Docker installation process.

        Args:
            progress_callback: Optional callback for progress updates.

        Returns:
            Tuple of (success, docker_info).
        """
        logger.info("Starting Docker installation process")

        try:
            # Check if already installed
            if self.is_docker_installed() and self.is_docker_running():
                logger.info("Docker is already installed and running")
                success, test_results = self.test_docker()
                if success:
                    return True, test_results

            # Get installation guide
            guide = self.get_installation_guide()

            # Platform-specific installation
            if self.platform in [DockerPlatform.WINDOWS, DockerPlatform.MACOS]:
                # Docker Desktop - guide user to download
                logger.info("Docker Desktop installation required - opening download page")

                if progress_callback:
                    progress_callback(10, "Opening Docker download page...")

                # Open download page
                if not self.open_download_page():
                    self.status = InstallationStatus.FAILED
                    self.message = "Failed to open download page"
                    return False, None

                # Wait for user to install
                if not self.wait_for_installation(progress_callback=progress_callback):
                    return False, None

            else:  # Linux
                # Provide installation instructions
                self.status = InstallationStatus.USER_ACTION_REQUIRED
                self.message = "Please follow Linux installation instructions"
                logger.info("Linux installation requires manual steps")

                # User needs to run commands manually
                print("\n" + "=" * 60)
                print("DOCKER INSTALLATION REQUIRED")
                print("=" * 60)
                print("\nPlease run the following commands to install Docker:\n")

                for i, step in enumerate(guide["steps"], 1):
                    print(f"{i}. {step}")

                print("\n" + "=" * 60)
                print("After installation, this installer will continue automatically")
                print("=" * 60 + "\n")

                # Wait for installation
                if not self.wait_for_installation(timeout=3600, progress_callback=progress_callback):
                    return False, None

            # Install Docker Compose if needed
            if self.config.install_compose:
                if progress_callback:
                    progress_callback(80, "Checking Docker Compose...")

                self.install_compose(progress_callback)

            # Configure Docker
            if progress_callback:
                progress_callback(90, "Configuring Docker...")

            self.configure_docker()

            # Test installation
            if progress_callback:
                progress_callback(95, "Testing Docker installation...")

            return self.test_docker()

        except Exception as e:
            logger.error(f"Installation failed: {str(e)}")
            self.status = InstallationStatus.FAILED
            self.message = f"Installation failed: {str(e)}"
            return False, None

    def get_status(self) -> Dict[str, Any]:
        """
        Get current installation status.

        Returns:
            Dictionary with status information.
        """
        compose_installed, compose_version = self.is_compose_installed()

        return {
            "status": self.status.value,
            "progress": self.progress,
            "message": self.message,
            "platform": self.platform.value,
            "edition": self.config.edition.value,
            "docker_info": self.docker_info,
            "checks": {
                "docker_installed": self.is_docker_installed(),
                "daemon_running": self.is_docker_running() if self.is_docker_installed() else False,
                "compose_installed": compose_installed,
                "compose_version": compose_version,
            },
            "config": {
                "use_wsl2": self.config.use_wsl2 if self.platform == DockerPlatform.WINDOWS else None,
                "memory_limit": self.config.memory_limit,
                "cpu_limit": self.config.cpu_limit,
                "disk_size": self.config.disk_size,
            },
        }


def main():
    """Main function for testing the installer."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # Create installer
    config = DockerConfig(install_compose=True, memory_limit="4GB", cpu_limit=4)

    installer = DockerInstaller(config)

    # Define progress callback
    def progress_callback(progress, message):
        print(f"Progress: {progress}% - {message}")

    # Check current status
    print("Checking Docker status...")
    status = installer.get_status()
    print(f"Platform: {status['platform']}")
    print(f"Docker installed: {status['checks']['docker_installed']}")
    print(f"Docker running: {status['checks']['daemon_running']}")
    print(f"Compose installed: {status['checks']['compose_installed']}")

    if not status["checks"]["docker_installed"]:
        # Get installation guide
        guide = installer.get_installation_guide()

        print("\n" + "=" * 60)
        print("DOCKER INSTALLATION GUIDE")
        print("=" * 60)

        print("\nRequirements:")
        for req in guide["requirements"]:
            print(f"  • {req}")

        print("\nInstallation Steps:")
        for i, step in enumerate(guide["steps"], 1):
            print(f"  {i}. {step}")

        print("\nURLs:")
        for name, url in guide["urls"].items():
            print(f"  {name}: {url}")

        print("\nNotes:")
        for note in guide["notes"]:
            print(f"  • {note}")

        print("\n" + "=" * 60)

        # Run installation
        print("\nStarting Docker installation...")
        success, docker_info = installer.install(progress_callback)

        if success:
            print("\n✓ Docker installation successful!")
            print(f"  Version: {docker_info.get('version', 'unknown')}")
            print(f"  Compose: {docker_info.get('compose_version', 'not installed')}")
        else:
            print("\n✗ Docker installation failed!")
            if docker_info and docker_info.get("errors"):
                print("  Errors:")
                for error in docker_info["errors"]:
                    print(f"    - {error}")
            return 1
    else:
        print("\n✓ Docker is already installed and running!")

        # Test Docker
        success, test_results = installer.test_docker()
        if success:
            print("  All tests passed!")
        else:
            print("  Some tests failed:")
            for error in test_results.get("errors", []):
                print(f"    - {error}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
