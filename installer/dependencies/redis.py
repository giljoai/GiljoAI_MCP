"""
Redis Installer for Windows

This module provides automated Redis installation for Windows systems,
including download, extraction, service configuration, and connection testing.
"""

import os
import sys
import json
import time
import logging
import hashlib
import subprocess
import tempfile
import zipfile
import urllib.request
import socket
from pathlib import Path
from typing import Dict, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum


# Configure logging
logger = logging.getLogger(__name__)


class InstallationStatus(Enum):
    """Redis installation status codes."""

    NOT_STARTED = "not_started"
    DOWNLOADING = "downloading"
    VERIFYING = "verifying"
    EXTRACTING = "extracting"
    INSTALLING = "installing"
    CONFIGURING = "configuring"
    CREATING_SERVICE = "creating_service"
    TESTING = "testing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class RedisConfig:
    """Redis installation configuration."""

    version: str = "5.0.14.1"  # Latest stable Windows build
    architecture: str = "x64"  # or "x86"
    port: int = 6379
    password: str = ""
    install_dir: Path = Path("C:/Program Files/Redis")
    data_dir: Path = Path("C:/Program Files/Redis/data")
    log_dir: Path = Path("C:/Program Files/Redis/logs")
    config_file: Path = Path("C:/Program Files/Redis/redis.windows.conf")
    service_name: str = "Redis"
    service_display_name: str = "Redis Server"
    service_description: str = "Redis in-memory data structure store"
    max_memory: str = "256mb"
    max_memory_policy: str = "allkeys-lru"
    save_intervals: list = None  # Default: [("900", "1"), ("300", "10"), ("60", "10000")]
    append_only: bool = False
    append_fsync: str = "everysec"
    databases: int = 16
    timeout: int = 0  # Client idle timeout (0 = disabled)
    tcp_keepalive: int = 300
    loglevel: str = "notice"
    bind_address: str = "127.0.0.1"
    protected_mode: bool = True

    def __post_init__(self):
        """Initialize default values."""
        if self.save_intervals is None:
            self.save_intervals = [
                ("900", "1"),  # Save after 900 sec if at least 1 key changed
                ("300", "10"),  # Save after 300 sec if at least 10 keys changed
                ("60", "10000"),  # Save after 60 sec if at least 10000 keys changed
            ]


class RedisInstaller:
    """
    Redis installer for Windows systems.

    Handles download, extraction, configuration, and service setup
    of Redis for the GiljoAI MCP system using community Windows builds.
    """

    # Redis Windows build download URLs (from GitHub releases)
    DOWNLOAD_URLS = {
        "5.0.14.1": {
            "x64": "https://github.com/tporadowski/redis/releases/download/v5.0.14.1/Redis-x64-5.0.14.1.zip",
            "x86": "https://github.com/tporadowski/redis/releases/download/v5.0.14.1/Redis-x86-5.0.14.1.zip",
        },
        "5.0.10": {
            "x64": "https://github.com/tporadowski/redis/releases/download/v5.0.10/Redis-x64-5.0.10.zip",
            "x86": "https://github.com/tporadowski/redis/releases/download/v5.0.10/Redis-x86-5.0.10.zip",
        },
        "3.2.100": {  # Older MSOpenTech build
            "x64": "https://github.com/microsoftarchive/redis/releases/download/win-3.2.100/Redis-x64-3.2.100.zip",
            "x86": "https://github.com/microsoftarchive/redis/releases/download/win-3.2.100/Redis-x86-3.2.100.zip",
        },
    }

    # Alternative Memurai URLs (Redis-compatible, Windows-optimized)
    MEMURAI_URLS = {"latest": {"x64": "https://www.memurai.com/get-memurai"}}

    def __init__(self, config: Optional[RedisConfig] = None):
        """
        Initialize Redis installer.

        Args:
            config: Optional configuration object. Uses defaults if not provided.
        """
        self.config = config or RedisConfig()
        self.status = InstallationStatus.NOT_STARTED
        self.progress = 0
        self.message = ""
        self.archive_path: Optional[Path] = None
        self.connection_info: Optional[Dict[str, Any]] = None

        # Ensure required directories exist
        self.temp_dir = Path(tempfile.gettempdir()) / "giljo_mcp_installer"
        self.temp_dir.mkdir(parents=True, exist_ok=True)

        # Set up logging
        self._setup_logging()

    def _setup_logging(self):
        """Configure logging for the installer."""
        log_file = self.temp_dir / "redis_install.log"
        handler = logging.FileHandler(log_file)
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)

    def is_redis_installed(self) -> bool:
        """
        Check if Redis is already installed.

        Returns:
            True if Redis is installed, False otherwise.
        """
        # Check if installation directory exists
        if self.config.install_dir.exists():
            # Check for redis-server executable
            redis_server = self.config.install_dir / "redis-server.exe"
            if redis_server.exists():
                logger.info(f"Redis found at {self.config.install_dir}")
                return True

        # Check if Redis service exists
        try:
            result = subprocess.run(["sc", "query", self.config.service_name], capture_output=True, text=True)
            if result.returncode == 0:
                logger.info(f"Redis service '{self.config.service_name}' found")
                return True
        except Exception:
            pass

        # Check common installation paths
        common_paths = [
            Path("C:/Redis"),
            Path("C:/Program Files/Redis"),
            Path("C:/Program Files (x86)/Redis"),
            Path("C:/tools/redis"),  # Chocolatey installation
        ]

        for path in common_paths:
            if path.exists():
                redis_server = path / "redis-server.exe"
                if redis_server.exists():
                    logger.info(f"Redis found at {path}")
                    self.config.install_dir = path
                    return True

        return False

    def get_system_architecture(self) -> str:
        """
        Determine system architecture.

        Returns:
            "x64" for 64-bit systems, "x86" for 32-bit systems.
        """
        import platform

        machine = platform.machine().lower()
        if machine in ["amd64", "x86_64", "x64"]:
            return "x64"
        return "x86"

    def download_redis(self, progress_callback=None) -> Path:
        """
        Download Redis for Windows.

        Args:
            progress_callback: Optional callback for progress updates.

        Returns:
            Path to downloaded archive.

        Raises:
            Exception: If download fails.
        """
        self.status = InstallationStatus.DOWNLOADING
        self.message = "Downloading Redis for Windows..."
        logger.info(self.message)

        # Get download URL
        arch = self.config.architecture or self.get_system_architecture()
        version = self.config.version

        if version not in self.DOWNLOAD_URLS:
            # Try to use the latest version if specified version not found
            logger.warning(f"Version {version} not found, using 5.0.14.1")
            version = "5.0.14.1"

        if arch not in self.DOWNLOAD_URLS[version]:
            raise ValueError(f"Unsupported architecture: {arch}")

        url = self.DOWNLOAD_URLS[version][arch]
        filename = Path(url).name
        archive_path = self.temp_dir / filename

        # Skip download if archive already exists
        if archive_path.exists():
            logger.info(f"Archive already exists at {archive_path}")
            self.archive_path = archive_path
            return archive_path

        try:
            # Download with progress tracking
            def download_hook(block_num, block_size, total_size):
                if total_size > 0:
                    downloaded = block_num * block_size
                    progress = min(100, int(downloaded * 100 / total_size))
                    self.progress = int(progress * 0.5)  # Download is 50% of total
                    if progress_callback:
                        progress_callback(self.progress, f"Downloading... {progress}%")

            logger.info(f"Downloading from {url}")
            # Set timeout for download
            old_timeout = socket.getdefaulttimeout()
            socket.setdefaulttimeout(30.0)
            try:
                urllib.request.urlretrieve(url, archive_path, download_hook)
            finally:
                socket.setdefaulttimeout(old_timeout)

            self.archive_path = archive_path
            logger.info(f"Downloaded Redis to {archive_path}")
            return archive_path

        except Exception as e:
            self.status = InstallationStatus.FAILED
            self.message = f"Download failed: {str(e)}"
            logger.error(self.message)
            raise

    def verify_archive(self) -> bool:
        """
        Verify downloaded archive integrity.

        Returns:
            True if archive is valid, False otherwise.
        """
        if not self.archive_path or not self.archive_path.exists():
            logger.error("No archive file to verify")
            return False

        self.status = InstallationStatus.VERIFYING
        self.message = "Verifying archive integrity..."
        logger.info(self.message)

        try:
            # Check if it's a valid zip file
            with zipfile.ZipFile(self.archive_path, "r") as zip_file:
                # Test archive integrity
                bad_file = zip_file.testzip()
                if bad_file:
                    logger.error(f"Archive contains bad file: {bad_file}")
                    return False

                # Check for required files
                required_files = ["redis-server.exe", "redis-cli.exe"]
                file_list = zip_file.namelist()

                for required in required_files:
                    if not any(required in f for f in file_list):
                        logger.error(f"Required file '{required}' not found in archive")
                        return False

            logger.info("Archive verification passed")
            return True

        except Exception as e:
            logger.error(f"Archive verification failed: {str(e)}")
            return False

    def extract_redis(self, progress_callback=None) -> bool:
        """
        Extract Redis archive to installation directory.

        Args:
            progress_callback: Optional callback for progress updates.

        Returns:
            True if extraction succeeds, False otherwise.
        """
        if not self.archive_path or not self.archive_path.exists():
            logger.error("No archive file to extract")
            return False

        self.status = InstallationStatus.EXTRACTING
        self.message = "Extracting Redis files..."
        logger.info(self.message)

        try:
            # Create installation directory
            self.config.install_dir.mkdir(parents=True, exist_ok=True)

            # Extract archive
            with zipfile.ZipFile(self.archive_path, "r") as zip_file:
                total_files = len(zip_file.namelist())

                for i, member in enumerate(zip_file.namelist()):
                    # Update progress
                    progress = 50 + int((i + 1) * 25 / total_files)  # 50-75% range
                    self.progress = progress
                    if progress_callback:
                        progress_callback(progress, f"Extracting... {i+1}/{total_files}")

                    # Extract file
                    zip_file.extract(member, self.config.install_dir)

            logger.info(f"Extracted Redis to {self.config.install_dir}")

            # Create data and log directories
            self.config.data_dir.mkdir(parents=True, exist_ok=True)
            self.config.log_dir.mkdir(parents=True, exist_ok=True)

            return True

        except Exception as e:
            self.status = InstallationStatus.FAILED
            self.message = f"Extraction failed: {str(e)}"
            logger.error(self.message)
            return False

    def generate_password(self):
        """Generate secure password if not provided."""
        if not self.config.password:
            import secrets
            import string

            alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
            self.config.password = "".join(secrets.choice(alphabet) for _ in range(16))
            logger.info("Generated Redis password")

    def configure_redis(self) -> bool:
        """
        Create and configure redis.windows.conf file.

        Returns:
            True if configuration succeeds, False otherwise.
        """
        self.status = InstallationStatus.CONFIGURING
        self.message = "Configuring Redis..."
        logger.info(self.message)

        try:
            # Generate password if needed
            self.generate_password()

            # Create configuration file
            config_content = f"""# Redis configuration file for Windows
# Generated by GiljoAI MCP Installer

# Network
bind {self.config.bind_address}
protected-mode {"yes" if self.config.protected_mode else "no"}
port {self.config.port}
tcp-backlog 511
timeout {self.config.timeout}
tcp-keepalive {self.config.tcp_keepalive}

# General
daemonize no
supervised no
pidfile redis.pid
loglevel {self.config.loglevel}
logfile "{self.config.log_dir / 'redis.log'}"
databases {self.config.databases}

# Persistence - RDB
"""
            # Add save intervals
            for seconds, changes in self.config.save_intervals:
                config_content += f"save {seconds} {changes}\n"

            config_content += f"""
stop-writes-on-bgsave-error yes
rdbcompression yes
rdbchecksum yes
dbfilename dump.rdb
dir "{self.config.data_dir}"

# Persistence - AOF
appendonly {"yes" if self.config.append_only else "no"}
appendfilename "appendonly.aof"
appendfsync {self.config.append_fsync}
no-appendfsync-on-rewrite no
auto-aof-rewrite-percentage 100
auto-aof-rewrite-min-size 64mb
aof-load-truncated yes
aof-use-rdb-preamble yes

# Memory management
maxmemory {self.config.max_memory}
maxmemory-policy {self.config.max_memory_policy}

# Security
requirepass {self.config.password}

# Clients
maxclients 10000

# Slow log
slowlog-log-slower-than 10000
slowlog-max-len 128

# Advanced config
hash-max-ziplist-entries 512
hash-max-ziplist-value 64
list-max-ziplist-size -2
list-compress-depth 0
set-max-intset-entries 512
zset-max-ziplist-entries 128
zset-max-ziplist-value 64
hll-sparse-max-bytes 3000
stream-node-max-bytes 4096
stream-node-max-entries 100
activerehashing yes
client-output-buffer-limit normal 0 0 0
client-output-buffer-limit replica 256mb 64mb 60
client-output-buffer-limit pubsub 32mb 8mb 60
hz 10
dynamic-hz yes
aof-rewrite-incremental-fsync yes
rdb-save-incremental-fsync yes
"""

            # Write configuration file
            with open(self.config.config_file, "w") as f:
                f.write(config_content)

            logger.info(f"Created configuration file at {self.config.config_file}")

            # Create a Windows-compatible startup script
            startup_script = self.config.install_dir / "start-redis.bat"
            script_content = f"""@echo off
cd /d "{self.config.install_dir}"
redis-server.exe "{self.config.config_file}"
"""
            with open(startup_script, "w") as f:
                f.write(script_content)

            logger.info(f"Created startup script at {startup_script}")

            return True

        except Exception as e:
            self.status = InstallationStatus.FAILED
            self.message = f"Configuration failed: {str(e)}"
            logger.error(self.message)
            return False

    def create_windows_service(self) -> bool:
        """
        Create Windows service for Redis.

        Returns:
            True if service creation succeeds, False otherwise.
        """
        self.status = InstallationStatus.CREATING_SERVICE
        self.message = "Creating Windows service..."
        logger.info(self.message)

        try:
            redis_server = self.config.install_dir / "redis-server.exe"

            # Check if service already exists
            check_cmd = ["sc", "query", self.config.service_name]
            result = subprocess.run(check_cmd, capture_output=True, text=True)

            if result.returncode == 0:
                logger.info(f"Service '{self.config.service_name}' already exists")
                # Stop and delete existing service
                subprocess.run(["sc", "stop", self.config.service_name], capture_output=True)
                time.sleep(2)
                subprocess.run(["sc", "delete", self.config.service_name], capture_output=True)
                time.sleep(2)

            # Create new service using redis-server --service-install
            install_cmd = [
                str(redis_server),
                "--service-install",
                str(self.config.config_file),
                "--service-name",
                self.config.service_name,
                "--loglevel",
                self.config.loglevel,
                "--log-file",
                str(self.config.log_dir / "redis.log"),
            ]

            result = subprocess.run(install_cmd, capture_output=True, text=True, cwd=str(self.config.install_dir))

            if result.returncode != 0:
                # Fallback: Create service manually with sc command
                logger.warning("redis-server --service-install failed, trying sc create")

                service_cmd = [
                    "sc",
                    "create",
                    self.config.service_name,
                    f'DisplayName= "{self.config.service_display_name}"',
                    f'binPath= ""{redis_server}" "{self.config.config_file}""',
                    "start= auto",
                ]

                result = subprocess.run(service_cmd, capture_output=True, text=True)

                if result.returncode != 0:
                    logger.error(f"Failed to create service: {result.stderr}")
                    return False

                # Set service description
                desc_cmd = ["sc", "description", self.config.service_name, f'"{self.config.service_description}"']
                subprocess.run(desc_cmd, capture_output=True)

            # Configure service recovery options
            failure_cmd = [
                "sc",
                "failure",
                self.config.service_name,
                "reset= 86400",
                "actions= restart/5000/restart/10000/restart/30000",
            ]
            subprocess.run(failure_cmd, capture_output=True)

            # Start the service
            logger.info(f"Starting service '{self.config.service_name}'")
            start_cmd = ["sc", "start", self.config.service_name]
            result = subprocess.run(start_cmd, capture_output=True, text=True)

            if result.returncode != 0:
                # Try alternative start method
                result = subprocess.run(["net", "start", self.config.service_name], capture_output=True, text=True)

                if result.returncode != 0:
                    logger.error(f"Failed to start service: {result.stderr}")
                    return False

            # Wait for service to be running
            time.sleep(3)

            # Verify service is running
            query_cmd = ["sc", "query", self.config.service_name]
            result = subprocess.run(query_cmd, capture_output=True, text=True)

            if "RUNNING" in result.stdout:
                logger.info(f"Service '{self.config.service_name}' is running")
                return True
            else:
                logger.error(f"Service not in running state: {result.stdout}")
                return False

        except Exception as e:
            self.status = InstallationStatus.FAILED
            self.message = f"Service creation failed: {str(e)}"
            logger.error(self.message)
            return False

    def test_connection(self) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Test Redis connection using redis-cli.

        Returns:
            Tuple of (success, connection_info).
        """
        self.status = InstallationStatus.TESTING
        self.message = "Testing Redis connection..."
        logger.info(self.message)

        try:
            redis_cli = self.config.install_dir / "redis-cli.exe"

            # Build connection info
            self.connection_info = {
                "host": self.config.bind_address,
                "port": self.config.port,
                "password": self.config.password,
                "database": 0,
                "connection_string": f"redis://:{self.config.password}@{self.config.bind_address}:{self.config.port}/0",
                "install_dir": str(self.config.install_dir),
                "data_dir": str(self.config.data_dir),
                "config_file": str(self.config.config_file),
                "service_name": self.config.service_name,
            }

            # Test PING command
            ping_cmd = [
                str(redis_cli),
                "-h",
                self.config.bind_address,
                "-p",
                str(self.config.port),
                "-a",
                self.config.password,
                "PING",
            ]

            result = subprocess.run(ping_cmd, capture_output=True, text=True, timeout=10)

            if result.returncode == 0 and "PONG" in result.stdout:
                logger.info("Redis PING successful")

                # Get Redis info
                info_cmd = [
                    str(redis_cli),
                    "-h",
                    self.config.bind_address,
                    "-p",
                    str(self.config.port),
                    "-a",
                    self.config.password,
                    "INFO",
                    "server",
                ]

                info_result = subprocess.run(info_cmd, capture_output=True, text=True, timeout=10)

                if info_result.returncode == 0:
                    # Parse version from INFO output
                    for line in info_result.stdout.split("\n"):
                        if line.startswith("redis_version:"):
                            version = line.split(":")[1].strip()
                            self.connection_info["version"] = version
                            logger.info(f"Redis version: {version}")
                            break

                # Test SET/GET operations
                test_key = "giljo:test:key"
                test_value = "installation_successful"

                # SET command
                set_cmd = [
                    str(redis_cli),
                    "-h",
                    self.config.bind_address,
                    "-p",
                    str(self.config.port),
                    "-a",
                    self.config.password,
                    "SET",
                    test_key,
                    test_value,
                ]

                result = subprocess.run(set_cmd, capture_output=True, text=True, timeout=10)

                if result.returncode == 0:
                    # GET command
                    get_cmd = [
                        str(redis_cli),
                        "-h",
                        self.config.bind_address,
                        "-p",
                        str(self.config.port),
                        "-a",
                        self.config.password,
                        "GET",
                        test_key,
                    ]

                    result = subprocess.run(get_cmd, capture_output=True, text=True, timeout=10)

                    if result.returncode == 0 and test_value in result.stdout:
                        logger.info("Redis SET/GET test successful")

                        # Clean up test key
                        del_cmd = [
                            str(redis_cli),
                            "-h",
                            self.config.bind_address,
                            "-p",
                            str(self.config.port),
                            "-a",
                            self.config.password,
                            "DEL",
                            test_key,
                        ]
                        subprocess.run(del_cmd, capture_output=True, timeout=10)

                        self.status = InstallationStatus.COMPLETED
                        self.message = "Redis installation completed successfully"
                        self.progress = 100
                        return True, self.connection_info
                    else:
                        logger.error(f"GET command failed: {result.stderr}")
                else:
                    logger.error(f"SET command failed: {result.stderr}")
            else:
                logger.error(f"PING command failed: {result.stderr}")

            self.status = InstallationStatus.FAILED
            self.message = "Connection test failed"
            return False, None

        except Exception as e:
            logger.error(f"Connection test error: {str(e)}")
            self.status = InstallationStatus.FAILED
            self.message = f"Connection test error: {str(e)}"
            return False, None

    def install(self, progress_callback=None) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Main installation entry point.

        Performs complete Redis installation and configuration.

        Args:
            progress_callback: Optional callback for progress updates.

        Returns:
            Tuple of (success, connection_info).
        """
        logger.info("Starting Redis installation process")

        try:
            # Check if already installed
            if self.is_redis_installed():
                logger.info("Redis is already installed")
                # Try to connect with existing installation
                success, conn_info = self.test_connection()
                if success:
                    return True, conn_info
                # If connection fails, try to reconfigure
                if self.configure_redis() and self.create_windows_service():
                    return self.test_connection()
                return False, None

            # Download Redis
            self.download_redis(progress_callback)

            # Verify archive
            if not self.verify_archive():
                return False, None

            # Extract Redis
            if not self.extract_redis(progress_callback):
                return False, None

            # Configure Redis
            if not self.configure_redis():
                return False, None

            # Create Windows service
            if not self.create_windows_service():
                return False, None

            # Test connection
            return self.test_connection()

        except Exception as e:
            logger.error(f"Installation failed: {str(e)}")
            self.status = InstallationStatus.FAILED
            self.message = f"Installation failed: {str(e)}"
            return False, None

    def uninstall(self) -> bool:
        """
        Uninstall Redis.

        Returns:
            True if uninstallation succeeds, False otherwise.
        """
        logger.info("Starting Redis uninstallation")

        try:
            # Stop service
            subprocess.run(["sc", "stop", self.config.service_name], capture_output=True, timeout=30)
            time.sleep(2)

            # Delete service
            subprocess.run(["sc", "delete", self.config.service_name], capture_output=True, timeout=30)

            # Remove installation directory
            if self.config.install_dir.exists():
                import shutil

                shutil.rmtree(self.config.install_dir)
                logger.info(f"Removed installation directory: {self.config.install_dir}")

            logger.info("Redis uninstalled successfully")
            return True

        except Exception as e:
            logger.error(f"Uninstallation failed: {str(e)}")
            return False

    def get_status(self) -> Dict[str, Any]:
        """
        Get current installation status.

        Returns:
            Dictionary with status information.
        """
        return {
            "status": self.status.value,
            "progress": self.progress,
            "message": self.message,
            "connection_info": self.connection_info,
            "config": {
                "version": self.config.version,
                "port": self.config.port,
                "password": self.config.password,
                "install_dir": str(self.config.install_dir),
                "data_dir": str(self.config.data_dir),
                "config_file": str(self.config.config_file),
                "service_name": self.config.service_name,
                "max_memory": self.config.max_memory,
                "persistence": {"append_only": self.config.append_only, "save_intervals": self.config.save_intervals},
            },
        }


def main():
    """Main function for testing the installer."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # Create installer with custom configuration
    config = RedisConfig(
        version="5.0.14.1",
        port=6379,
        max_memory="512mb",
        append_only=True,  # Enable AOF persistence
    )

    installer = RedisInstaller(config)

    # Define progress callback
    def progress_callback(progress, message):
        print(f"Progress: {progress}% - {message}")

    # Run installation
    print("Starting Redis installation...")
    success, connection_info = installer.install(progress_callback)

    if success:
        print(f"Installation successful!")
        print(f"\nConnection details:")
        print(f"  Host: {connection_info['host']}")
        print(f"  Port: {connection_info['port']}")
        print(f"  Password: {connection_info['password']}")
        print(f"  Connection string: {connection_info['connection_string']}")
        print(f"  Version: {connection_info.get('version', 'unknown')}")
        print(f"\nConfiguration:")
        status = installer.get_status()
        print(f"  Install directory: {status['config']['install_dir']}")
        print(f"  Data directory: {status['config']['data_dir']}")
        print(f"  Service name: {status['config']['service_name']}")
        print(f"  Max memory: {status['config']['max_memory']}")
    else:
        print(f"Installation failed: {installer.message}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
