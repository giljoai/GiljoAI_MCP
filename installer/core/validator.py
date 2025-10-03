"""
Pre and post installation validators
Ensures system requirements are met and installation is successful
"""

import os
import sys
import platform
import socket
import subprocess
import shutil
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional


class PreInstallValidator:
    """Validate system requirements before installation"""

    def __init__(self, settings: Dict[str, Any]):
        self.settings = settings
        self.logger = logging.getLogger(self.__class__.__name__)

    def validate(self) -> Dict[str, Any]:
        """Run all pre-installation validations"""
        result = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'fixes': []
        }

        # Check Python version
        py_check = self.check_python_version()
        if not py_check['valid']:
            result['valid'] = False
            result['errors'].extend(py_check['errors'])

        # Check disk space
        disk_check = self.check_disk_space()
        if not disk_check['valid']:
            result['valid'] = False
            result['errors'].extend(disk_check['errors'])

        # Check port availability
        port_check = self.check_ports()
        if not port_check['valid']:
            result['valid'] = False
            result['errors'].extend(port_check['errors'])
            result['fixes'].extend(port_check.get('fixes', []))

        # Check PostgreSQL
        pg_check = self.check_postgresql()
        if not pg_check['valid']:
            result['warnings'].extend(pg_check['warnings'])

        # Check for existing installation
        existing_check = self.check_existing_installation()
        if existing_check['exists']:
            result['warnings'].append("Existing installation detected")
            if existing_check.get('backup_recommended'):
                result['fixes'].append("Backup existing configuration")

        # Check dependencies
        dep_check = self.check_dependencies()
        if not dep_check['valid']:
            result['warnings'].extend(dep_check['warnings'])
            result['fixes'].extend(dep_check.get('fixes', []))

        return result

    def check_python_version(self) -> Dict[str, Any]:
        """Ensure Python version is 3.8+"""
        result = {'valid': True, 'errors': []}

        version = sys.version_info
        if version.major < 3 or (version.major == 3 and version.minor < 8):
            result['valid'] = False
            result['errors'].append(
                f"Python 3.8+ required, found {version.major}.{version.minor}.{version.micro}"
            )

        return result

    def check_disk_space(self, required_mb: int = 500) -> Dict[str, Any]:
        """Check available disk space"""
        result = {'valid': True, 'errors': []}

        try:
            if platform.system() == "Windows":
                import ctypes
                free_bytes = ctypes.c_ulonglong(0)
                ctypes.windll.kernel32.GetDiskFreeSpaceExW(
                    ctypes.c_wchar_p(os.getcwd()),
                    ctypes.pointer(free_bytes),
                    None, None
                )
                free_mb = free_bytes.value / 1024 / 1024
            else:
                stat = os.statvfs(os.getcwd())
                free_mb = (stat.f_bavail * stat.f_frsize) / 1024 / 1024

            if free_mb < required_mb:
                result['valid'] = False
                result['errors'].append(
                    f"Insufficient disk space: {free_mb:.0f}MB available, {required_mb}MB required"
                )

        except Exception as e:
            self.logger.warning(f"Could not check disk space: {e}")

        return result

    def check_ports(self) -> Dict[str, Any]:
        """Check if required ports are available"""
        result = {'valid': True, 'errors': [], 'fixes': []}

        ports_to_check = [
            ('API', self.settings.get('api_port', 8000)),
            ('WebSocket', self.settings.get('ws_port', 7273)),
            ('Dashboard', self.settings.get('dashboard_port', 7274))
        ]

        for service, port in ports_to_check:
            if not self.is_port_available(port):
                result['valid'] = False
                result['errors'].append(f"Port {port} ({service}) is already in use")
                result['fixes'].append(f"Stop service using port {port} or choose a different port")

        return result

    def is_port_available(self, port: int, host: str = '127.0.0.1') -> bool:
        """Check if a specific port is available"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            sock.close()
            return result != 0
        except Exception:
            return True

    def check_postgresql(self) -> Dict[str, Any]:
        """Check PostgreSQL availability and version"""
        result = {'valid': True, 'warnings': []}

        # Check if PostgreSQL client is available
        psql_available = shutil.which('psql') is not None

        if not psql_available:
            result['warnings'].append(
                "PostgreSQL client (psql) not found in PATH. "
                "This may indicate PostgreSQL is not installed."
            )
            return result

        # Try to get PostgreSQL version
        try:
            proc = subprocess.run(
                ['psql', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )

            if proc.returncode == 0:
                version_str = proc.stdout
                if '18' not in version_str and '17' not in version_str and '16' not in version_str:
                    result['warnings'].append(
                        f"PostgreSQL 18 recommended, found: {version_str.strip()}"
                    )
            else:
                result['warnings'].append("Could not determine PostgreSQL version")

        except Exception as e:
            self.logger.warning(f"PostgreSQL version check failed: {e}")

        return result

    def check_existing_installation(self) -> Dict[str, Any]:
        """Check for existing GiljoAI installation"""
        result = {'exists': False, 'backup_recommended': False}

        # Check for existing config files
        config_files = ['.env', 'config.yaml', 'api_keys.yaml']
        existing_files = []

        for file in config_files:
            if Path(file).exists():
                existing_files.append(file)

        if existing_files:
            result['exists'] = True
            result['existing_files'] = existing_files
            result['backup_recommended'] = True

        # Check for existing database (if psycopg2 available)
        try:
            import psycopg2
            conn = psycopg2.connect(
                host=self.settings.get('pg_host', 'localhost'),
                port=self.settings.get('pg_port', 5432),
                database='giljo_mcp',
                user='postgres',
                password=self.settings.get('pg_password', '')
            )
            conn.close()
            result['database_exists'] = True
            result['backup_recommended'] = True
        except:
            pass

        return result

    def check_dependencies(self) -> Dict[str, Any]:
        """Check for required system dependencies"""
        result = {'valid': True, 'warnings': [], 'fixes': []}

        # Check for git (optional but recommended)
        if not shutil.which('git'):
            result['warnings'].append("Git not found - recommended for version control")
            result['fixes'].append("Install Git from https://git-scm.com")

        # Check for required Python packages
        required_packages = ['pip', 'venv']
        for package in required_packages:
            try:
                __import__(package)
            except ImportError:
                result['warnings'].append(f"Python package '{package}' not found")
                result['fixes'].append(f"Install {package}: python -m pip install {package}")

        return result


class PostInstallValidator:
    """Validate installation success"""

    def __init__(self, settings: Dict[str, Any]):
        self.settings = settings
        self.logger = logging.getLogger(self.__class__.__name__)

    def validate(self) -> Dict[str, Any]:
        """Run post-installation validation"""
        result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }

        # Check configuration files
        config_check = self.check_config_files()
        if not config_check['valid']:
            result['valid'] = False
            result['errors'].extend(config_check['errors'])

        # Check database connectivity
        db_check = self.check_database()
        if not db_check['valid']:
            result['valid'] = False
            result['errors'].extend(db_check['errors'])

        # Check launcher scripts
        launcher_check = self.check_launchers()
        if not launcher_check['valid']:
            result['warnings'].extend(launcher_check['warnings'])

        # Check directory structure
        dir_check = self.check_directories()
        if not dir_check['valid']:
            result['warnings'].extend(dir_check['warnings'])

        # Verify installation status
        status_check = self.check_installation_status()
        if not status_check['valid']:
            result['warnings'].extend(status_check['warnings'])

        return result

    def check_config_files(self) -> Dict[str, Any]:
        """Verify all required configuration files exist"""
        result = {'valid': True, 'errors': []}

        required_files = {
            '.env': 'Environment configuration',
            'config.yaml': 'Application configuration'
        }

        for file, description in required_files.items():
            if not Path(file).exists():
                result['valid'] = False
                result['errors'].append(f"Missing {description}: {file}")
            else:
                # Check file is not empty
                if Path(file).stat().st_size == 0:
                    result['valid'] = False
                    result['errors'].append(f"Empty configuration file: {file}")

        return result

    def check_database(self) -> Dict[str, Any]:
        """Verify database connectivity"""
        result = {'valid': True, 'errors': []}

        # Try to import psycopg2 and test connection
        try:
            import psycopg2
            from dotenv import load_dotenv

            load_dotenv()

            conn = psycopg2.connect(
                host=os.getenv('POSTGRES_HOST', 'localhost'),
                port=os.getenv('POSTGRES_PORT', 5432),
                database=os.getenv('POSTGRES_DB', 'giljo_mcp'),
                user=os.getenv('POSTGRES_USER', 'giljo_user'),
                password=os.getenv('POSTGRES_PASSWORD', '')
            )

            # Test basic query
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()

            conn.close()

        except ImportError:
            result['errors'].append("psycopg2 not installed - database validation skipped")
        except Exception as e:
            result['valid'] = False
            result['errors'].append(f"Database connection failed: {e}")

        return result

    def check_launchers(self) -> Dict[str, Any]:
        """Verify launcher scripts exist and are executable"""
        result = {'valid': True, 'warnings': []}

        launcher_dir = Path("launchers")
        if not launcher_dir.exists():
            result['valid'] = False
            result['warnings'].append("Launchers directory not found")
            return result

        # Check for Python launcher
        py_launcher = launcher_dir / "start_giljo.py"
        if not py_launcher.exists():
            result['valid'] = False
            result['warnings'].append("Python launcher not found")

        # Check for platform-specific launcher
        if platform.system() == "Windows":
            bat_launcher = launcher_dir / "start_giljo.bat"
            if not bat_launcher.exists():
                result['warnings'].append("Windows launcher not found")
        else:
            sh_launcher = launcher_dir / "start_giljo.sh"
            if not sh_launcher.exists():
                result['warnings'].append("Unix launcher not found")
            elif not os.access(sh_launcher, os.X_OK):
                result['warnings'].append("Unix launcher not executable")

        return result

    def check_directories(self) -> Dict[str, Any]:
        """Verify required directories exist"""
        result = {'valid': True, 'warnings': []}

        required_dirs = ['data', 'logs', 'uploads', 'temp']

        for dir_name in required_dirs:
            dir_path = Path(dir_name)
            if not dir_path.exists():
                try:
                    dir_path.mkdir(parents=True, exist_ok=True)
                    self.logger.info(f"Created directory: {dir_name}")
                except Exception as e:
                    result['warnings'].append(f"Could not create directory {dir_name}: {e}")

        return result

    def check_installation_status(self) -> Dict[str, Any]:
        """Check overall installation status from config.yaml"""
        result = {'valid': True, 'warnings': []}

        try:
            import yaml

            with open('config.yaml', 'r') as f:
                config = yaml.safe_load(f)

            status = config.get('status', {})

            if not status.get('installation_complete'):
                result['warnings'].append("Installation marked as incomplete")

            if not status.get('database_created'):
                result['warnings'].append("Database not marked as created")

            if not status.get('ready_to_launch'):
                result['warnings'].append("System not marked as ready to launch")

        except Exception as e:
            result['warnings'].append(f"Could not check installation status: {e}")

        return result
