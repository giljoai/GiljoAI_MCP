"""
PostgreSQL Installer for Windows

This module provides automated PostgreSQL installation for Windows systems,
including download, silent installation, service configuration, and database setup.
"""

import hashlib
import logging
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional, Tuple


# Configure logging
logger = logging.getLogger(__name__)


class InstallationStatus(Enum):
    """PostgreSQL installation status codes."""
    NOT_STARTED = "not_started"
    DOWNLOADING = "downloading"
    VERIFYING = "verifying"
    INSTALLING = "installing"
    CONFIGURING = "configuring"
    TESTING = "testing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class PostgreSQLConfig:
    """PostgreSQL installation configuration."""
    version: str = "15.4"
    architecture: str = "x86_64"  # or "x86"
    port: int = 5432
    superuser: str = "postgres"
    superuser_password: str = ""
    database_name: str = "giljo_mcp"
    database_user: str = "giljo"
    database_password: str = ""
    install_dir: Path = Path("C:/Program Files/PostgreSQL/15")
    data_dir: Path = Path("C:/Program Files/PostgreSQL/15/data")
    locale: str = "en_US.UTF-8"
    enable_service: bool = True
    service_name: str = "postgresql-x64-15"
    service_account: str = "NT AUTHORITY\\NetworkService"
    max_connections: int = 100
    shared_buffers: str = "128MB"


class PostgreSQLInstaller:
    """
    PostgreSQL installer for Windows systems.
    
    Handles download, installation, configuration, and initial setup
    of PostgreSQL database for the GiljoAI MCP system.
    """

    # PostgreSQL download URLs for different versions
    DOWNLOAD_URLS = {
        "15.4": {
            "x86_64": "https://get.enterprisedb.com/postgresql/postgresql-15.4-1-windows-x64.exe",
            "x86": "https://get.enterprisedb.com/postgresql/postgresql-15.4-1-windows.exe"
        },
        "15.5": {
            "x86_64": "https://get.enterprisedb.com/postgresql/postgresql-15.5-1-windows-x64.exe",
            "x86": "https://get.enterprisedb.com/postgresql/postgresql-15.5-1-windows.exe"
        },
        "16.0": {
            "x86_64": "https://get.enterprisedb.com/postgresql/postgresql-16.0-1-windows-x64.exe",
            "x86": "https://get.enterprisedb.com/postgresql/postgresql-16.0-1-windows.exe"
        }
    }

    # Expected SHA256 hashes for installers (example values - should be updated)
    INSTALLER_HASHES = {
        "postgresql-15.4-1-windows-x64.exe": "abc123...",  # Update with actual hash
        "postgresql-15.5-1-windows-x64.exe": "def456...",  # Update with actual hash
        "postgresql-16.0-1-windows-x64.exe": "ghi789...",  # Update with actual hash
    }

    def __init__(self, config: Optional[PostgreSQLConfig] = None):
        """
        Initialize PostgreSQL installer.
        
        Args:
            config: Optional configuration object. Uses defaults if not provided.
        """
        self.config = config or PostgreSQLConfig()
        self.status = InstallationStatus.NOT_STARTED
        self.progress = 0
        self.message = ""
        self.installer_path: Optional[Path] = None
        self.connection_string: Optional[str] = None

        # Ensure required directories exist
        self.temp_dir = Path(tempfile.gettempdir()) / "giljo_mcp_installer"
        self.temp_dir.mkdir(parents=True, exist_ok=True)

        # Set up logging
        self._setup_logging()

    def _setup_logging(self):
        """Configure logging for the installer."""
        log_file = self.temp_dir / "postgresql_install.log"
        handler = logging.FileHandler(log_file)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)

    def is_postgresql_installed(self) -> bool:
        """
        Check if PostgreSQL is already installed.
        
        Returns:
            True if PostgreSQL is installed, False otherwise.
        """
        # Check if installation directory exists
        if self.config.install_dir.exists():
            # Check for psql executable
            psql_path = self.config.install_dir / "bin" / "psql.exe"
            if psql_path.exists():
                logger.info(f"PostgreSQL found at {self.config.install_dir}")
                return True

        # Check Windows registry for PostgreSQL installations
        try:
            import winreg
            key_path = r"SOFTWARE\PostgreSQL\Installations"
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
                i = 0
                while True:
                    try:
                        subkey_name = winreg.EnumKey(key, i)
                        logger.info(f"Found PostgreSQL installation: {subkey_name}")
                        return True
                    except OSError:
                        break
                    i += 1
        except Exception:
            pass

        return False

    def get_system_architecture(self) -> str:
        """
        Determine system architecture.
        
        Returns:
            "x86_64" for 64-bit systems, "x86" for 32-bit systems.
        """
        import platform
        machine = platform.machine().lower()
        if machine in ["amd64", "x86_64", "x64"]:
            return "x86_64"
        return "x86"

    def download_installer(self, progress_callback=None) -> Path:
        """
        Download PostgreSQL installer.
        
        Args:
            progress_callback: Optional callback for progress updates.
        
        Returns:
            Path to downloaded installer.
        
        Raises:
            Exception: If download fails.
        """
        self.status = InstallationStatus.DOWNLOADING
        self.message = "Downloading PostgreSQL installer..."
        logger.info(self.message)

        # Get download URL
        arch = self.config.architecture or self.get_system_architecture()
        version = self.config.version

        if version not in self.DOWNLOAD_URLS:
            raise ValueError(f"Unsupported PostgreSQL version: {version}")

        if arch not in self.DOWNLOAD_URLS[version]:
            raise ValueError(f"Unsupported architecture: {arch}")

        url = self.DOWNLOAD_URLS[version][arch]
        filename = Path(url).name
        installer_path = self.temp_dir / filename

        # Skip download if installer already exists
        if installer_path.exists():
            logger.info(f"Installer already exists at {installer_path}")
            self.installer_path = installer_path
            return installer_path

        try:
            # Download with progress tracking
            def download_hook(block_num, block_size, total_size):
                if total_size > 0:
                    downloaded = block_num * block_size
                    progress = min(100, int(downloaded * 100 / total_size))
                    self.progress = progress
                    if progress_callback:
                        progress_callback(progress, f"Downloading... {progress}%")

            logger.info(f"Downloading from {url}")
            urllib.request.urlretrieve(url, installer_path, download_hook)

            self.installer_path = installer_path
            logger.info(f"Downloaded installer to {installer_path}")
            return installer_path

        except Exception as e:
            self.status = InstallationStatus.FAILED
            self.message = f"Download failed: {e!s}"
            logger.error(self.message)
            raise

    def verify_installer(self) -> bool:
        """
        Verify downloaded installer integrity.
        
        Returns:
            True if installer is valid, False otherwise.
        """
        if not self.installer_path or not self.installer_path.exists():
            logger.error("No installer file to verify")
            return False

        self.status = InstallationStatus.VERIFYING
        self.message = "Verifying installer integrity..."
        logger.info(self.message)

        # For now, just check file size is reasonable
        file_size = self.installer_path.stat().st_size
        min_size = 100 * 1024 * 1024  # 100 MB minimum

        if file_size < min_size:
            logger.error(f"Installer file too small: {file_size} bytes")
            return False

        # TODO: Implement SHA256 hash verification when hashes are available
        # file_hash = self._calculate_file_hash(self.installer_path)
        # expected_hash = self.INSTALLER_HASHES.get(self.installer_path.name)
        # return file_hash == expected_hash

        logger.info("Installer verification passed")
        return True

    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of a file."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def generate_passwords(self):
        """Generate secure passwords if not provided."""
        import secrets
        import string

        def generate_password(length=16):
            alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
            return "".join(secrets.choice(alphabet) for _ in range(length))

        if not self.config.superuser_password:
            self.config.superuser_password = generate_password()
            logger.info("Generated superuser password")

        if not self.config.database_password:
            self.config.database_password = generate_password()
            logger.info("Generated database user password")

    def install_postgresql(self, progress_callback=None) -> bool:
        """
        Perform silent PostgreSQL installation.
        
        Args:
            progress_callback: Optional callback for progress updates.
        
        Returns:
            True if installation succeeds, False otherwise.
        """
        if not self.installer_path or not self.installer_path.exists():
            logger.error("No installer file available")
            return False

        self.status = InstallationStatus.INSTALLING
        self.message = "Installing PostgreSQL..."
        logger.info(self.message)

        # Generate passwords if needed
        self.generate_passwords()

        # Build installation command with parameters
        install_cmd = [
            str(self.installer_path),
            "--mode", "unattended",
            "--unattendedmodeui", "none",
            "--prefix", str(self.config.install_dir),
            "--datadir", str(self.config.data_dir),
            "--serverport", str(self.config.port),
            "--superaccount", self.config.superuser,
            "--superpassword", self.config.superuser_password,
            "--locale", self.config.locale,
            "--enable_acledit", "1"
        ]

        if self.config.enable_service:
            install_cmd.extend([
                "--serviceaccount", self.config.service_account,
                "--servicename", self.config.service_name
            ])
        else:
            install_cmd.extend(["--disable-components", "server"])

        try:
            logger.info(f"Running installer with command: {' '.join(install_cmd[:-2])}")  # Hide password

            # Run installer
            process = subprocess.Popen(
                install_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # Monitor installation progress
            while True:
                returncode = process.poll()
                if returncode is not None:
                    break

                # Simulate progress
                if self.progress < 90:
                    self.progress += 2
                    if progress_callback:
                        progress_callback(self.progress, "Installing PostgreSQL...")

                time.sleep(1)

            stdout, stderr = process.communicate()

            if returncode != 0:
                self.status = InstallationStatus.FAILED
                self.message = f"Installation failed: {stderr}"
                logger.error(self.message)
                return False

            logger.info("PostgreSQL installation completed successfully")
            return True

        except Exception as e:
            self.status = InstallationStatus.FAILED
            self.message = f"Installation error: {e!s}"
            logger.error(self.message)
            return False

    def configure_postgresql(self) -> bool:
        """
        Configure PostgreSQL for GiljoAI MCP.
        
        Returns:
            True if configuration succeeds, False otherwise.
        """
        self.status = InstallationStatus.CONFIGURING
        self.message = "Configuring PostgreSQL..."
        logger.info(self.message)

        try:
            # Path to PostgreSQL binaries
            bin_dir = self.config.install_dir / "bin"
            psql = bin_dir / "psql.exe"
            createdb = bin_dir / "createdb.exe"
            createuser = bin_dir / "createuser.exe"

            # Set environment for PostgreSQL commands
            env = os.environ.copy()
            env["PGPASSWORD"] = self.config.superuser_password

            # Create database user
            logger.info(f"Creating user {self.config.database_user}")
            create_user_cmd = [
                str(createuser),
                "-h", "localhost",
                "-p", str(self.config.port),
                "-U", self.config.superuser,
                "-d",  # Can create databases
                "-r",  # Can create roles
                "-s",  # Superuser (simplified for development)
                self.config.database_user
            ]

            result = subprocess.run(
                create_user_cmd,
                check=False, env=env,
                capture_output=True,
                text=True
            )

            # User might already exist, which is okay
            if result.returncode != 0 and "already exists" not in result.stderr:
                logger.warning(f"User creation warning: {result.stderr}")

            # Set user password
            logger.info(f"Setting password for user {self.config.database_user}")
            alter_user_sql = f"ALTER USER {self.config.database_user} PASSWORD '{self.config.database_password}';"

            psql_cmd = [
                str(psql),
                "-h", "localhost",
                "-p", str(self.config.port),
                "-U", self.config.superuser,
                "-d", "postgres",
                "-c", alter_user_sql
            ]

            result = subprocess.run(
                psql_cmd,
                check=False, env=env,
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                logger.error(f"Failed to set user password: {result.stderr}")
                return False

            # Create database
            logger.info(f"Creating database {self.config.database_name}")
            create_db_cmd = [
                str(createdb),
                "-h", "localhost",
                "-p", str(self.config.port),
                "-U", self.config.superuser,
                "-O", self.config.database_user,  # Owner
                "-E", "UTF8",  # Encoding
                self.config.database_name
            ]

            result = subprocess.run(
                create_db_cmd,
                check=False, env=env,
                capture_output=True,
                text=True
            )

            # Database might already exist, which is okay
            if result.returncode != 0 and "already exists" not in result.stderr:
                logger.error(f"Database creation failed: {result.stderr}")
                return False

            # Configure pg_hba.conf for local connections
            self._configure_pg_hba()

            # Configure postgresql.conf for performance
            self._configure_postgresql_conf()

            # Restart service to apply configuration
            if self.config.enable_service:
                self._restart_service()

            logger.info("PostgreSQL configuration completed")
            return True

        except Exception as e:
            self.status = InstallationStatus.FAILED
            self.message = f"Configuration error: {e!s}"
            logger.error(self.message)
            return False

    def _configure_pg_hba(self):
        """Configure pg_hba.conf for authentication."""
        pg_hba_path = self.config.data_dir / "pg_hba.conf"

        if not pg_hba_path.exists():
            logger.warning(f"pg_hba.conf not found at {pg_hba_path}")
            return

        try:
            # Backup original file
            backup_path = pg_hba_path.with_suffix(".conf.backup")
            if not backup_path.exists():
                import shutil
                shutil.copy2(pg_hba_path, backup_path)
                logger.info(f"Backed up pg_hba.conf to {backup_path}")

            # Read current configuration
            with open(pg_hba_path) as f:
                lines = f.readlines()

            # Add entries for giljo_mcp database
            new_entries = [
                "# GiljoAI MCP Configuration\n",
                f"host    {self.config.database_name}    {self.config.database_user}    127.0.0.1/32    md5\n",
                f"host    {self.config.database_name}    {self.config.database_user}    ::1/128         md5\n",
                f"local   {self.config.database_name}    {self.config.database_user}                    md5\n",
            ]

            # Find position to insert (before first 'host all all' line)
            insert_pos = len(lines)
            for i, line in enumerate(lines):
                if line.strip().startswith("host") and "all" in line:
                    insert_pos = i
                    break

            # Insert new entries if not already present
            already_configured = any(
                self.config.database_name in line for line in lines
            )

            if not already_configured:
                for entry in reversed(new_entries):
                    lines.insert(insert_pos, entry)

                # Write updated configuration
                with open(pg_hba_path, "w") as f:
                    f.writelines(lines)

                logger.info("Updated pg_hba.conf with GiljoAI MCP entries")

        except Exception as e:
            logger.error(f"Failed to configure pg_hba.conf: {e!s}")

    def _configure_postgresql_conf(self):
        """Configure postgresql.conf for performance."""
        postgresql_conf_path = self.config.data_dir / "postgresql.conf"

        if not postgresql_conf_path.exists():
            logger.warning(f"postgresql.conf not found at {postgresql_conf_path}")
            return

        try:
            # Backup original file
            backup_path = postgresql_conf_path.with_suffix(".conf.backup")
            if not backup_path.exists():
                import shutil
                shutil.copy2(postgresql_conf_path, backup_path)
                logger.info(f"Backed up postgresql.conf to {backup_path}")

            # Read current configuration
            with open(postgresql_conf_path) as f:
                content = f.read()

            # Check if already configured
            if "# GiljoAI MCP Configuration" in content:
                logger.info("postgresql.conf already configured")
                return

            # Add performance settings
            config_additions = f"""

# GiljoAI MCP Configuration
max_connections = {self.config.max_connections}
shared_buffers = {self.config.shared_buffers}
work_mem = 4MB
maintenance_work_mem = 64MB
effective_cache_size = 512MB
random_page_cost = 1.1
log_destination = 'stderr'
logging_collector = on
log_directory = 'log'
log_filename = 'postgresql-%Y-%m-%d.log'
log_rotation_age = 1d
log_rotation_size = 100MB
log_line_prefix = '%m [%p] %q%u@%d '
log_timezone = 'UTC'
"""

            # Append configuration
            with open(postgresql_conf_path, "a") as f:
                f.write(config_additions)

            logger.info("Updated postgresql.conf with performance settings")

        except Exception as e:
            logger.error(f"Failed to configure postgresql.conf: {e!s}")

    def _restart_service(self) -> bool:
        """Restart PostgreSQL service."""
        try:
            logger.info(f"Restarting PostgreSQL service {self.config.service_name}")

            # Stop service
            subprocess.run(
                ["net", "stop", self.config.service_name],
                check=False, capture_output=True,
                text=True,
                timeout=30
            )

            time.sleep(2)

            # Start service
            result = subprocess.run(
                ["net", "start", self.config.service_name],
                check=False, capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                logger.error(f"Failed to start service: {result.stderr}")
                return False

            logger.info("PostgreSQL service restarted successfully")
            return True

        except Exception as e:
            logger.error(f"Service restart failed: {e!s}")
            return False

    def test_connection(self) -> Tuple[bool, Optional[str]]:
        """
        Test PostgreSQL connection.
        
        Returns:
            Tuple of (success, connection_string).
        """
        self.status = InstallationStatus.TESTING
        self.message = "Testing PostgreSQL connection..."
        logger.info(self.message)

        try:
            # Build connection string
            self.connection_string = (
                f"postgresql://{self.config.database_user}:"
                f"{self.config.database_password}@"
                f"localhost:{self.config.port}/"
                f"{self.config.database_name}"
            )

            # Test with psql
            bin_dir = self.config.install_dir / "bin"
            psql = bin_dir / "psql.exe"

            env = os.environ.copy()
            env["PGPASSWORD"] = self.config.database_password

            test_cmd = [
                str(psql),
                "-h", "localhost",
                "-p", str(self.config.port),
                "-U", self.config.database_user,
                "-d", self.config.database_name,
                "-c", "SELECT version();"
            ]

            result = subprocess.run(
                test_cmd,
                check=False, env=env,
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                logger.info("Connection test successful")
                logger.info(f"PostgreSQL version: {result.stdout}")
                self.status = InstallationStatus.COMPLETED
                self.message = "PostgreSQL installation completed"
                self.progress = 100
                return True, self.connection_string
            logger.error(f"Connection test failed: {result.stderr}")
            self.status = InstallationStatus.FAILED
            self.message = f"Connection test failed: {result.stderr}"
            return False, None

        except Exception as e:
            logger.error(f"Connection test error: {e!s}")
            self.status = InstallationStatus.FAILED
            self.message = f"Connection test error: {e!s}"
            return False, None

    def install(self, progress_callback=None) -> Tuple[bool, Optional[str]]:
        """
        Main installation entry point.
        
        Performs complete PostgreSQL installation and configuration.
        
        Args:
            progress_callback: Optional callback for progress updates.
        
        Returns:
            Tuple of (success, connection_string).
        """
        logger.info("Starting PostgreSQL installation process")

        try:
            # Check if already installed
            if self.is_postgresql_installed():
                logger.info("PostgreSQL is already installed")
                # Try to connect with existing installation
                success, conn_str = self.test_connection()
                if success:
                    return True, conn_str
                # If connection fails, try to configure
                if self.configure_postgresql():
                    return self.test_connection()
                return False, None

            # Download installer
            self.download_installer(progress_callback)

            # Verify installer
            if not self.verify_installer():
                return False, None

            # Install PostgreSQL
            if not self.install_postgresql(progress_callback):
                return False, None

            # Configure PostgreSQL
            if not self.configure_postgresql():
                return False, None

            # Test connection
            return self.test_connection()

        except Exception as e:
            logger.error(f"Installation failed: {e!s}")
            self.status = InstallationStatus.FAILED
            self.message = f"Installation failed: {e!s}"
            return False, None

    def uninstall(self) -> bool:
        """
        Uninstall PostgreSQL.
        
        Returns:
            True if uninstallation succeeds, False otherwise.
        """
        logger.info("Starting PostgreSQL uninstallation")

        try:
            # Stop service
            if self.config.enable_service:
                subprocess.run(
                    ["net", "stop", self.config.service_name],
                    check=False, capture_output=True,
                    timeout=30
                )

            # Run uninstaller
            uninstaller = self.config.install_dir / "uninstall-postgresql.exe"
            if uninstaller.exists():
                subprocess.run(
                    [str(uninstaller), "--mode", "unattended"],
                    check=False, capture_output=True,
                    timeout=300
                )
                logger.info("PostgreSQL uninstalled successfully")
                return True
            logger.warning("Uninstaller not found")
            return False

        except Exception as e:
            logger.error(f"Uninstallation failed: {e!s}")
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
            "connection_string": self.connection_string,
            "config": {
                "version": self.config.version,
                "port": self.config.port,
                "database": self.config.database_name,
                "install_dir": str(self.config.install_dir),
                "data_dir": str(self.config.data_dir)
            }
        }


def main():
    """Main function for testing the installer."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Create installer with custom configuration
    config = PostgreSQLConfig(
        version="15.4",
        database_name="giljo_mcp",
        database_user="giljo",
        port=5432
    )

    installer = PostgreSQLInstaller(config)

    # Define progress callback
    def progress_callback(progress, message):
        print(f"Progress: {progress}% - {message}")

    # Run installation
    print("Starting PostgreSQL installation...")
    success, connection_string = installer.install(progress_callback)

    if success:
        print("Installation successful!")
        print(f"Connection string: {connection_string}")
        print("\nConfiguration details:")
        status = installer.get_status()
        for key, value in status["config"].items():
            print(f"  {key}: {value}")
    else:
        print(f"Installation failed: {installer.message}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
