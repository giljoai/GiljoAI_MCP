#!/usr/bin/env python3
"""
Dependency Management for GiljoAI MCP Setup
Handles intelligent dependency checking, installation, and virtual environment management
"""

import subprocess
import sys
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set
import json
import re
import venv
import shutil
from datetime import datetime


class DependencyManager:
    """Manages Python and system dependencies intelligently"""
    
    def __init__(self):
        self.python_exe = sys.executable
        self.requirements_file = Path('requirements.txt')
        self.core_dependencies = set()
        self.optional_dependencies = set()
        self.installed_packages = {}
        self.missing_packages = []
        self.system_dependencies = {}
        
    def parse_requirements(self, requirements_path: Optional[Path] = None) -> Dict[str, List[str]]:
        """Parse requirements.txt into core and optional dependencies"""
        if not requirements_path:
            requirements_path = self.requirements_file
        
        if not requirements_path.exists():
            return {'core': [], 'optional': [], 'dev': []}
        
        dependencies = {
            'core': [],
            'optional': [],
            'dev': [],
            'production': []
        }
        
        current_section = 'core'
        
        with open(requirements_path, 'r') as f:
            for line in f:
                line = line.strip()
                
                # Skip comments and empty lines
                if not line or line.startswith('#'):
                    # Check for section markers in comments
                    if line.startswith('# Optional'):
                        current_section = 'optional'
                    elif line.startswith('# Dev'):
                        current_section = 'dev'
                    elif line.startswith('# Production'):
                        current_section = 'production'
                    elif line.startswith('# Core'):
                        current_section = 'core'
                    continue
                
                # Parse dependency
                dep = self._parse_dependency_line(line)
                if dep:
                    dependencies[current_section].append(dep)
        
        # Categorize known dependencies
        self._categorize_dependencies(dependencies)
        
        return dependencies
    
    def _parse_dependency_line(self, line: str) -> Optional[Dict]:
        """Parse a single dependency line"""
        # Handle different formats
        # package==1.0.0
        # package>=1.0.0,<2.0.0
        # package[extra]==1.0.0
        # -e git+https://github.com/user/repo.git
        
        if line.startswith('-e '):
            # Editable install
            return {
                'name': line,
                'editable': True,
                'raw': line
            }
        
        # Extract package name and version spec
        match = re.match(r'^([a-zA-Z0-9_-]+)(\[.*?\])?(.*)$', line)
        if match:
            name = match.group(1)
            extras = match.group(2) or ''
            version_spec = match.group(3) or ''
            
            return {
                'name': name,
                'extras': extras,
                'version_spec': version_spec,
                'raw': line
            }
        
        return None
    
    def _categorize_dependencies(self, dependencies: Dict):
        """Categorize dependencies as core or optional based on package names"""
        # Known core packages for GiljoAI MCP
        core_packages = {
            'fastmcp', 'fastapi', 'sqlalchemy', 'pydantic', 'pydantic-settings',
            'uvicorn', 'httpx', 'websockets', 'pyyaml', 'python-dotenv',
            'alembic', 'asyncpg', 'aiosqlite'
        }
        
        # Optional/dev packages
        optional_packages = {
            'pytest', 'pytest-asyncio', 'pytest-cov', 'black', 'ruff',
            'mypy', 'rich', 'psycopg2', 'psycopg2-binary', 'redis',
            'celery', 'flower', 'gunicorn', 'supervisor'
        }
        
        # Move packages to correct categories
        all_deps = dependencies.get('core', []) + dependencies.get('optional', [])
        
        for dep in all_deps:
            if isinstance(dep, dict):
                name = dep.get('name', '')
                if name in core_packages:
                    self.core_dependencies.add(dep.get('raw', name))
                elif name in optional_packages:
                    self.optional_dependencies.add(dep.get('raw', name))
    
    def check_installed_packages(self) -> Dict[str, str]:
        """Check currently installed Python packages"""
        try:
            result = subprocess.run(
                [self.python_exe, '-m', 'pip', 'list', '--format=json'],
                capture_output=True, text=True, timeout=30
            )
            
            if result.returncode == 0:
                packages = json.loads(result.stdout)
                self.installed_packages = {
                    pkg['name'].lower(): pkg['version'] 
                    for pkg in packages
                }
                return self.installed_packages
        except Exception as e:
            print(f"Error checking installed packages: {e}")
        
        return {}
    
    def find_missing_dependencies(self, dependencies: Dict[str, List]) -> List[str]:
        """Find dependencies that are not installed"""
        missing = []
        installed = self.check_installed_packages()
        
        for category in dependencies:
            for dep in dependencies[category]:
                if isinstance(dep, dict):
                    name = dep.get('name', '').lower()
                    if name and name not in installed:
                        missing.append(dep.get('raw', name))
                elif isinstance(dep, str):
                    # Simple package name
                    name = dep.split('==')[0].split('>=')[0].split('[')[0].lower()
                    if name not in installed:
                        missing.append(dep)
        
        self.missing_packages = missing
        return missing
    
    def check_virtual_environment(self) -> Dict[str, any]:
        """Check if running in a virtual environment"""
        info = {
            'active': False,
            'type': None,
            'path': None,
            'base_python': sys.base_prefix,
            'current_python': sys.prefix
        }
        
        # Check for venv/virtualenv
        if hasattr(sys, 'real_prefix') or (
            hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix
        ):
            info['active'] = True
            info['type'] = 'venv'
            info['path'] = sys.prefix
        
        # Check for conda
        if os.environ.get('CONDA_DEFAULT_ENV'):
            info['active'] = True
            info['type'] = 'conda'
            info['path'] = os.environ.get('CONDA_PREFIX')
            info['env_name'] = os.environ.get('CONDA_DEFAULT_ENV')
        
        # Check for pipenv
        if os.environ.get('PIPENV_ACTIVE'):
            info['active'] = True
            info['type'] = 'pipenv'
            info['path'] = os.environ.get('VIRTUAL_ENV')
        
        # Check for poetry
        if os.environ.get('POETRY_ACTIVE'):
            info['active'] = True
            info['type'] = 'poetry'
            info['path'] = os.environ.get('VIRTUAL_ENV')
        
        return info
    
    def create_virtual_environment(self, venv_path: Path = None, 
                                 with_pip: bool = True,
                                 system_site_packages: bool = False) -> bool:
        """Create a new virtual environment"""
        if not venv_path:
            venv_path = Path.cwd() / 'venv'
        
        try:
            print(f"Creating virtual environment at: {venv_path}")
            
            venv.create(
                venv_path,
                with_pip=with_pip,
                system_site_packages=system_site_packages,
                clear=True,
                symlinks=(sys.platform != 'win32')
            )
            
            # Get activation command for user
            if sys.platform == 'win32':
                activate_cmd = str(venv_path / 'Scripts' / 'activate.bat')
            else:
                activate_cmd = f"source {venv_path / 'bin' / 'activate'}"
            
            print(f"✓ Virtual environment created")
            print(f"  Activate with: {activate_cmd}")
            
            return True
            
        except Exception as e:
            print(f"✗ Failed to create virtual environment: {e}")
            return False
    
    def install_dependencies(self, dependencies: List[str], 
                           upgrade: bool = False,
                           quiet: bool = False) -> Tuple[bool, List[str]]:
        """Install Python dependencies"""
        if not dependencies:
            return True, []
        
        failed = []
        
        # Prepare pip command
        cmd = [self.python_exe, '-m', 'pip', 'install']
        
        if upgrade:
            cmd.append('--upgrade')
        
        if quiet:
            cmd.append('-q')
        
        # Install in batches to handle failures
        batch_size = 10
        for i in range(0, len(dependencies), batch_size):
            batch = dependencies[i:i+batch_size]
            
            try:
                print(f"Installing {len(batch)} packages...")
                result = subprocess.run(
                    cmd + batch,
                    capture_output=True,
                    text=True,
                    timeout=300  # 5 minutes timeout
                )
                
                if result.returncode != 0:
                    # Try installing one by one to identify failures
                    for dep in batch:
                        try:
                            single_result = subprocess.run(
                                cmd + [dep],
                                capture_output=True,
                                text=True,
                                timeout=60
                            )
                            if single_result.returncode != 0:
                                failed.append(dep)
                                print(f"  ✗ Failed to install: {dep}")
                            else:
                                print(f"  ✓ Installed: {dep}")
                        except Exception as e:
                            failed.append(dep)
                            print(f"  ✗ Error installing {dep}: {e}")
                else:
                    for dep in batch:
                        print(f"  ✓ Installed: {dep}")
                        
            except subprocess.TimeoutExpired:
                failed.extend(batch)
                print(f"✗ Installation timed out for batch")
            except Exception as e:
                failed.extend(batch)
                print(f"✗ Installation error: {e}")
        
        success = len(failed) == 0
        return success, failed
    
    def check_system_dependencies(self) -> Dict[str, bool]:
        """Check for required system dependencies"""
        dependencies = {
            'git': shutil.which('git') is not None,
            'python3': shutil.which('python3') is not None or shutil.which('python') is not None,
            'pip': shutil.which('pip') is not None or shutil.which('pip3') is not None,
        }
        
        # Database tools
        dependencies['postgresql'] = (
            shutil.which('psql') is not None or 
            shutil.which('postgres') is not None
        )
        dependencies['sqlite3'] = shutil.which('sqlite3') is not None
        
        # Optional but recommended
        dependencies['make'] = shutil.which('make') is not None
        dependencies['docker'] = shutil.which('docker') is not None
        dependencies['node'] = shutil.which('node') is not None
        dependencies['npm'] = shutil.which('npm') is not None
        
        self.system_dependencies = dependencies
        return dependencies
    
    def get_install_commands(self, package: str) -> Dict[str, str]:
        """Get platform-specific install commands for a system package"""
        commands = {}
        
        # Import platform detector
        try:
            from setup_platform import PlatformDetector
            detector = PlatformDetector()
            managers = detector._detect_package_managers()
            
            # Map packages to platform-specific names
            package_map = {
                'postgresql': {
                    'apt': 'postgresql postgresql-contrib',
                    'yum': 'postgresql-server postgresql-contrib',
                    'dnf': 'postgresql-server postgresql-contrib',
                    'pacman': 'postgresql',
                    'brew': 'postgresql',
                    'choco': 'postgresql',
                    'winget': 'PostgreSQL.PostgreSQL'
                },
                'git': {
                    'apt': 'git',
                    'yum': 'git',
                    'dnf': 'git',
                    'pacman': 'git',
                    'brew': 'git',
                    'choco': 'git',
                    'winget': 'Git.Git'
                },
                'python3': {
                    'apt': 'python3 python3-pip python3-venv',
                    'yum': 'python3 python3-pip',
                    'dnf': 'python3 python3-pip',
                    'pacman': 'python python-pip',
                    'brew': 'python3',
                    'choco': 'python',
                    'winget': 'Python.Python.3'
                },
                'node': {
                    'apt': 'nodejs npm',
                    'yum': 'nodejs npm',
                    'dnf': 'nodejs npm',
                    'pacman': 'nodejs npm',
                    'brew': 'node',
                    'choco': 'nodejs',
                    'winget': 'OpenJS.NodeJS'
                }
            }
            
            pkg_names = package_map.get(package, {package: package})
            
            for manager_name, manager_info in managers.items():
                if manager_info.get('available'):
                    cmd = manager_info.get('command')
                    if manager_name == 'apt':
                        commands['apt'] = f"sudo apt update && sudo apt install {pkg_names.get('apt', package)}"
                    elif manager_name == 'yum':
                        commands['yum'] = f"sudo yum install {pkg_names.get('yum', package)}"
                    elif manager_name == 'dnf':
                        commands['dnf'] = f"sudo dnf install {pkg_names.get('dnf', package)}"
                    elif manager_name == 'pacman':
                        commands['pacman'] = f"sudo pacman -S {pkg_names.get('pacman', package)}"
                    elif manager_name == 'homebrew':
                        commands['brew'] = f"brew install {pkg_names.get('brew', package)}"
                    elif manager_name == 'chocolatey':
                        commands['choco'] = f"choco install {pkg_names.get('choco', package)}"
                    elif manager_name == 'winget':
                        commands['winget'] = f"winget install {pkg_names.get('winget', package)}"
        except:
            # Fallback to generic commands
            pass
        
        return commands
    
    def generate_install_script(self, output_path: Path = None) -> Path:
        """Generate platform-specific installation script"""
        if not output_path:
            output_path = Path.cwd() / 'scripts'
        
        output_path.mkdir(exist_ok=True)
        
        # Detect platform
        is_windows = sys.platform == 'win32'
        script_ext = '.bat' if is_windows else '.sh'
        script_file = output_path / f'install_deps{script_ext}'
        
        # Parse requirements
        deps = self.parse_requirements()
        
        # Check what's missing
        missing = self.find_missing_dependencies(deps)
        
        # Generate script content
        if is_windows:
            content = self._generate_windows_script(deps, missing)
        else:
            content = self._generate_unix_script(deps, missing)
        
        # Write script
        with open(script_file, 'w', newline='\n' if not is_windows else None) as f:
            f.write(content)
        
        # Make executable on Unix
        if not is_windows:
            script_file.chmod(0o755)
        
        print(f"Generated installation script: {script_file}")
        return script_file
    
    def _generate_windows_script(self, deps: Dict, missing: List) -> str:
        """Generate Windows batch script"""
        script = f"""@echo off
REM GiljoAI MCP Dependency Installation Script
REM Generated: {datetime.now().isoformat()}

echo Installing GiljoAI MCP Dependencies...
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Please install Python 3.8+
    exit /b 1
)

REM Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip

REM Install core dependencies
echo.
echo Installing core dependencies...
python -m pip install {' '.join(deps.get('core', []))}

REM Install optional dependencies
if "%1"=="--all" (
    echo.
    echo Installing optional dependencies...
    python -m pip install {' '.join(deps.get('optional', []))}
)

REM Install dev dependencies
if "%1"=="--dev" (
    echo.
    echo Installing development dependencies...
    python -m pip install {' '.join(deps.get('dev', []))}
)

echo.
echo Installation complete!
pause
"""
        return script
    
    def _generate_unix_script(self, deps: Dict, missing: List) -> str:
        """Generate Unix shell script"""
        script = f"""#!/bin/bash
# GiljoAI MCP Dependency Installation Script
# Generated: {datetime.now().isoformat()}

set -e

echo "Installing GiljoAI MCP Dependencies..."
echo

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 not found. Please install Python 3.8+"
    exit 1
fi

# Use virtual environment if exists
if [ -f "venv/bin/activate" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# Upgrade pip
echo "Upgrading pip..."
python3 -m pip install --upgrade pip

# Install core dependencies
echo
echo "Installing core dependencies..."
python3 -m pip install {' '.join(deps.get('core', []))}

# Install optional dependencies
if [ "$1" == "--all" ]; then
    echo
    echo "Installing optional dependencies..."
    python3 -m pip install {' '.join(deps.get('optional', []))}
fi

# Install dev dependencies  
if [ "$1" == "--dev" ]; then
    echo
    echo "Installing development dependencies..."
    python3 -m pip install {' '.join(deps.get('dev', []))}
fi

echo
echo "Installation complete!"
"""
        return script
    
    def smart_install(self, force_upgrade: bool = False) -> bool:
        """Smart installation with fallbacks and recommendations"""
        print("Starting smart dependency installation...")
        
        # Check virtual environment
        venv_info = self.check_virtual_environment()
        if not venv_info['active']:
            print("⚠ Not in a virtual environment. Recommended to use one.")
            response = input("Create virtual environment? (y/n): ")
            if response.lower() == 'y':
                if not self.create_virtual_environment():
                    print("Failed to create virtual environment, continuing anyway...")
        
        # Check system dependencies
        print("\nChecking system dependencies...")
        sys_deps = self.check_system_dependencies()
        missing_sys = [k for k, v in sys_deps.items() if not v and k in ['git', 'python3', 'pip']]
        
        if missing_sys:
            print(f"⚠ Missing system dependencies: {', '.join(missing_sys)}")
            for dep in missing_sys:
                commands = self.get_install_commands(dep)
                if commands:
                    print(f"\nTo install {dep}:")
                    for manager, cmd in commands.items():
                        print(f"  {manager}: {cmd}")
        
        # Parse and check Python dependencies
        print("\nChecking Python dependencies...")
        deps = self.parse_requirements()
        missing = self.find_missing_dependencies(deps)
        
        if not missing:
            print("✓ All dependencies are already installed")
            return True
        
        print(f"\nFound {len(missing)} missing packages")
        
        # Install missing dependencies
        core_missing = [m for m in missing if m in self.core_dependencies or 
                       any(m.startswith(c.split('==')[0]) for c in self.core_dependencies)]
        optional_missing = [m for m in missing if m not in core_missing]
        
        # Install core first
        if core_missing:
            print(f"\nInstalling {len(core_missing)} core dependencies...")
            success, failed = self.install_dependencies(core_missing, upgrade=force_upgrade)
            if not success:
                print(f"⚠ Failed to install some core dependencies: {failed}")
        
        # Install optional
        if optional_missing:
            print(f"\nInstalling {len(optional_missing)} optional dependencies...")
            success, failed = self.install_dependencies(optional_missing, upgrade=force_upgrade)
            if failed:
                print(f"ℹ Some optional dependencies failed (this is usually OK): {failed}")
        
        print("\n✓ Dependency installation complete")
        return True


def main():
    """CLI interface for dependency management"""
    import argparse
    
    parser = argparse.ArgumentParser(description='GiljoAI MCP Dependency Manager')
    parser.add_argument('--check', action='store_true', help='Check dependencies only')
    parser.add_argument('--install', action='store_true', help='Install missing dependencies')
    parser.add_argument('--upgrade', action='store_true', help='Upgrade existing dependencies')
    parser.add_argument('--venv', action='store_true', help='Create virtual environment')
    parser.add_argument('--script', action='store_true', help='Generate install script')
    parser.add_argument('--smart', action='store_true', help='Smart install with recommendations')
    
    args = parser.parse_args()
    
    manager = DependencyManager()
    
    if args.check:
        deps = manager.parse_requirements()
        missing = manager.find_missing_dependencies(deps)
        
        print(f"Core dependencies: {len(deps.get('core', []))}")
        print(f"Optional dependencies: {len(deps.get('optional', []))}")
        print(f"Missing packages: {len(missing)}")
        
        if missing:
            print("\nMissing packages:")
            for pkg in missing:
                print(f"  - {pkg}")
    
    elif args.venv:
        manager.create_virtual_environment()
    
    elif args.script:
        manager.generate_install_script()
    
    elif args.smart or args.install:
        manager.smart_install(force_upgrade=args.upgrade)
    
    else:
        # Default to check
        deps = manager.parse_requirements()
        installed = manager.check_installed_packages()
        print(f"Installed packages: {len(installed)}")
        
        missing = manager.find_missing_dependencies(deps)
        if missing:
            print(f"Missing packages: {len(missing)}")
            print("Run with --install to install them")


if __name__ == "__main__":
    main()