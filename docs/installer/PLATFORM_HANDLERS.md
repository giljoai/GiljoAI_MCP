# Platform Handler Architecture

**Version**: 3.1.0+
**Status**: Production Ready
**Last Updated**: 2025-10-19

---

## Overview

GiljoAI MCP v3.1.0+ uses the **Strategy pattern** to isolate platform-specific installation code into concrete platform handlers. This enables a single unified installer (`install.py`) to work seamlessly across Windows, Linux, and macOS.

### Design Goals

1. **Single Installer**: One `python install.py` command works on all platforms
2. **Platform Isolation**: All OS-specific code contained in dedicated handlers
3. **Extensibility**: Easy to add new platforms (e.g., Docker, WSL)
4. **Maintainability**: Bug fixes apply to all platforms automatically
5. **Testability**: Platform-specific logic can be tested in isolation

---

## Architecture

### Component Structure

```
installer/
├── core/                      # Platform-agnostic modules
│   ├── database.py           # PostgreSQL setup (unified)
│   └── config.py             # Configuration generation (unified)
├── shared/                    # Shared utilities
│   ├── postgres.py           # PostgreSQL discovery
│   └── network.py            # Network utilities
└── platforms/                 # Platform-specific handlers
    ├── __init__.py           # Auto-detection factory
    ├── base.py               # Abstract PlatformHandler interface
    ├── windows.py            # Windows implementation
    ├── linux.py              # Linux implementation
    └── macos.py              # macOS implementation
```

### Class Hierarchy

```
PlatformHandler (ABC)
├── WindowsPlatformHandler
├── LinuxPlatformHandler
└── MacOSPlatformHandler
```

---

## Abstract Base Class

**File**: `installer/platforms/base.py`

Defines the contract that all platform handlers must implement:

### Required Methods (11 total)

**1. Platform Identification**:
```python
@property
@abstractmethod
def platform_name(self) -> str:
    """Return: 'Windows', 'Linux', or 'macOS'"""
    pass
```

**2. Virtual Environment Paths**:
```python
@abstractmethod
def get_venv_python(self, venv_dir: Path) -> Path:
    """Return: Path to venv Python executable"""
    pass

@abstractmethod
def get_venv_pip(self, venv_dir: Path) -> Path:
    """Return: Path to venv pip executable"""
    pass
```

**3. PostgreSQL Discovery**:
```python
@abstractmethod
def get_postgresql_scan_paths(self) -> List[Path]:
    """Return: List of paths to scan for psql executable"""
    pass

@abstractmethod
def get_postgresql_install_guide(self, recommended_version: int = 18) -> str:
    """Return: Platform-specific PostgreSQL installation instructions"""
    pass
```

**4. Desktop Integration**:
```python
@abstractmethod
def supports_desktop_shortcuts(self) -> bool:
    """Return: True if platform supports desktop shortcut creation"""
    pass

@abstractmethod
def create_desktop_shortcuts(self, install_dir: Path, venv_dir: Path) -> Dict[str, Any]:
    """Create platform-specific desktop shortcuts/launchers"""
    pass
```

**5. Package Management**:
```python
@abstractmethod
def run_npm_command(self, cmd: List[str], cwd: Path, timeout: int = 300) -> Dict[str, Any]:
    """Run npm command with platform-specific shell handling"""
    pass
```

**6. Network Utilities**:
```python
@abstractmethod
def get_network_ips(self) -> List[str]:
    """Return: List of non-localhost IPv4 addresses on this machine"""
    pass
```

**7. User Interface**:
```python
@abstractmethod
def welcome_screen(self) -> None:
    """Print platform-specific welcome screen with yellow branding"""
    pass

@abstractmethod
def get_platform_specific_warnings(self) -> List[str]:
    """Return: List of platform-specific warnings to show user"""
    pass
```

---

## Platform Implementations

### Windows Platform Handler

**File**: `installer/platforms/windows.py`

**Key Features**:
- PostgreSQL paths: `C:\Program Files\PostgreSQL\*\bin\psql.exe`
- Virtual environment: `venv\Scripts\python.exe`
- Desktop shortcuts: `.lnk` files using win32com
- npm execution: Requires `shell=True`
- Network detection: Uses `ipconfig` as fallback

**Example**:
```python
class WindowsPlatformHandler(PlatformHandler):
    def get_venv_python(self, venv_dir: Path) -> Path:
        return venv_dir / 'Scripts' / 'python.exe'

    def get_postgresql_scan_paths(self) -> List[Path]:
        paths = []
        pg_base = Path("C:/Program Files/PostgreSQL")
        if pg_base.exists():
            for version_dir in sorted(pg_base.glob("*"), reverse=True):
                psql_path = version_dir / "bin" / "psql.exe"
                if psql_path.exists():
                    paths.append(psql_path)
        return paths

    def run_npm_command(self, cmd: List[str], cwd: Path, timeout: int = 300):
        return subprocess.run(
            cmd, cwd=str(cwd), shell=True,  # CRITICAL: shell=True required
            capture_output=True, text=True, timeout=timeout
        )
```

### Linux Platform Handler

**File**: `installer/platforms/linux.py`

**Key Features**:
- PostgreSQL paths: `/usr/lib/postgresql/*/bin/psql`, `/usr/bin/psql`
- Virtual environment: `venv/bin/python`
- Desktop shortcuts: `.desktop` files with gio trust
- Distribution detection: Ubuntu, Fedora, Debian specific guides
- npm execution: Direct execution (no shell=True)
- Network detection: Uses `ip -4 addr show` as fallback

**Example**:
```python
class LinuxPlatformHandler(PlatformHandler):
    def get_venv_python(self, venv_dir: Path) -> Path:
        return venv_dir / 'bin' / 'python'

    def get_postgresql_install_guide(self, recommended_version: int = 18) -> str:
        distro = self._detect_linux_distro()
        if distro == 'ubuntu':
            return self._get_ubuntu_postgresql_guide(recommended_version)
        elif distro == 'fedora':
            return self._get_fedora_postgresql_guide(recommended_version)
        else:
            return self._get_generic_linux_postgresql_guide(recommended_version)

    def create_desktop_shortcuts(self, install_dir: Path, venv_dir: Path):
        desktop_dir = Path.home() / ".local" / "share" / "applications"
        desktop_dir.mkdir(parents=True, exist_ok=True)

        desktop_file = desktop_dir / "GiljoAI-Dashboard.desktop"
        desktop_content = f"""[Desktop Entry]
Version=1.0
Type=Application
Name=GiljoAI Dashboard
Exec={venv_dir / 'bin' / 'python'} {install_dir / 'startup.py'}
Icon={install_dir / 'frontend' / 'public' / 'favicon.ico'}
Terminal=false
Categories=Development;
"""
        desktop_file.write_text(desktop_content)
        desktop_file.chmod(0o755)

        # Trust the desktop file (GNOME requirement)
        subprocess.run(['gio', 'set', str(desktop_file), 'metadata::trusted', 'true'])
```

### macOS Platform Handler

**File**: `installer/platforms/macos.py`

**Key Features**:
- PostgreSQL paths: Homebrew (ARM: `/opt/homebrew/`, Intel: `/usr/local/`)
- Postgres.app detection: `/Applications/Postgres.app/`
- Virtual environment: `venv/bin/python`
- Desktop shortcuts: Not yet supported (future: .app bundles)
- npm execution: Direct execution (like Linux)
- Network detection: Uses `ifconfig` as fallback

**Example**:
```python
class MacOSPlatformHandler(PlatformHandler):
    def get_postgresql_scan_paths(self) -> List[Path]:
        paths = []

        # Homebrew paths (Intel and ARM)
        homebrew_paths = [
            Path("/usr/local/opt/postgresql@18/bin/psql"),  # Intel
            Path("/opt/homebrew/opt/postgresql@18/bin/psql")  # ARM (M1/M2)
        ]
        paths.extend([p for p in homebrew_paths if p.exists()])

        # Postgres.app paths
        paths.extend(Path("/Applications").glob("Postgres.app/Contents/Versions/*/bin/psql"))

        return paths

    def get_postgresql_install_guide(self, recommended_version: int = 18) -> str:
        return f"""
        macOS PostgreSQL {recommended_version} Installation:

        Option 1: Homebrew (Recommended)
           brew install postgresql@{recommended_version}
           brew services start postgresql@{recommended_version}

        Option 2: Postgres.app
           Download from https://postgresapp.com/
        """
```

---

## Auto-Detection Factory

**File**: `installer/platforms/__init__.py`

Automatically detects the current platform and returns the appropriate handler:

```python
import platform
from .base import PlatformHandler
from .windows import WindowsPlatformHandler
from .linux import LinuxPlatformHandler
from .macos import MacOSPlatformHandler

def get_platform_handler() -> PlatformHandler:
    """
    Auto-detect platform and return appropriate handler

    Returns:
        PlatformHandler: Platform-specific handler instance

    Raises:
        RuntimeError: If platform is unsupported
    """
    system = platform.system()

    handlers = {
        'Windows': WindowsPlatformHandler,
        'Linux': LinuxPlatformHandler,
        'Darwin': MacOSPlatformHandler
    }

    handler_class = handlers.get(system)
    if handler_class is None:
        raise RuntimeError(
            f"Unsupported platform: {system}. "
            f"Supported platforms: {', '.join(handlers.keys())}"
        )

    return handler_class()
```

**Usage**:
```python
from installer.platforms import get_platform_handler

# Automatically get correct handler
platform = get_platform_handler()

# Use platform-specific methods
venv_python = platform.get_venv_python(Path.cwd() / 'venv')
psql_paths = platform.get_postgresql_scan_paths()
platform.create_desktop_shortcuts(Path.cwd(), Path.cwd() / 'venv')
```

---

## Usage in Main Installer

**File**: `install.py`

The main installer orchestrator uses platform handlers for all OS-specific operations:

```python
from installer.platforms import get_platform_handler

class UnifiedInstaller:
    def __init__(self, settings: Dict[str, Any]):
        self.platform = get_platform_handler()  # Auto-detect
        self.install_dir = Path(settings['install_dir'])
        self.venv_dir = self.install_dir / 'venv'

    def _create_virtualenv(self):
        subprocess.run([sys.executable, '-m', 'venv', str(self.venv_dir)])

    def _install_dependencies(self):
        pip_executable = self.platform.get_venv_pip(self.venv_dir)
        subprocess.run([str(pip_executable), 'install', '-r', 'requirements.txt'])

    def _discover_postgresql(self):
        from installer.shared.postgres import PostgreSQLDiscovery
        discovery = PostgreSQLDiscovery(platform=self.platform)
        result = discovery.discover()
        if not result['found']:
            print(self.platform.get_postgresql_install_guide())
```

---

## Adding a New Platform

To add support for a new platform:

### 1. Create Platform Handler

Create `installer/platforms/your_platform.py`:

```python
from pathlib import Path
from typing import List, Dict, Any
from .base import PlatformHandler

class YourPlatformHandler(PlatformHandler):
    @property
    def platform_name(self) -> str:
        return "YourPlatform"

    # Implement all 11 abstract methods
    def get_venv_python(self, venv_dir: Path) -> Path:
        # Your implementation
        pass

    # ... (implement remaining methods)
```

### 2. Register in Factory

Update `installer/platforms/__init__.py`:

```python
from .your_platform import YourPlatformHandler

def get_platform_handler() -> PlatformHandler:
    system = platform.system()

    handlers = {
        'Windows': WindowsPlatformHandler,
        'Linux': LinuxPlatformHandler,
        'Darwin': MacOSPlatformHandler,
        'YourPlatform': YourPlatformHandler  # Add here
    }

    # ... (rest of function)
```

### 3. Add Tests

Create `tests/installer/test_your_platform.py`:

```python
import pytest
from pathlib import Path
from installer.platforms.your_platform import YourPlatformHandler

def test_your_platform_venv_python():
    handler = YourPlatformHandler()
    venv_dir = Path("/path/to/venv")
    python = handler.get_venv_python(venv_dir)
    assert python == venv_dir / "expected" / "python"

# ... (test all 11 methods)
```

### 4. Update Documentation

Update this file with your platform's specifics.

---

## Testing Strategy

### Unit Tests

Test each platform handler in isolation:

```python
def test_windows_postgresql_scan_paths():
    handler = WindowsPlatformHandler()
    paths = handler.get_postgresql_scan_paths()

    # Verify expected paths are checked
    assert any("Program Files" in str(p) for p in paths)

def test_linux_desktop_shortcuts():
    handler = LinuxPlatformHandler()
    result = handler.create_desktop_shortcuts(
        install_dir=Path("/opt/giljo"),
        venv_dir=Path("/opt/giljo/venv")
    )

    assert result['success'] is True
    assert 'GiljoAI-Dashboard.desktop' in result['shortcuts_created']
```

### Integration Tests

Test platform handler with real installer:

```python
@pytest.mark.integration
async def test_unified_installer_all_platforms():
    for platform_name in ['Windows', 'Linux', 'Darwin']:
        with mock.patch('platform.system', return_value=platform_name):
            installer = UnifiedInstaller(settings={...})
            result = installer.run()
            assert result['success'] is True
```

---

## Platform Comparison

| Feature | Windows | Linux | macOS |
|---------|---------|-------|-------|
| venv path | `Scripts\python.exe` | `bin/python` | `bin/python` |
| PostgreSQL | Program Files | `/usr/lib/postgresql` | Homebrew |
| Desktop shortcuts | `.lnk` (win32com) | `.desktop` (gio) | Not supported |
| npm shell | `shell=True` | Direct | Direct |
| Network fallback | `ipconfig` | `ip -4 addr` | `ifconfig` |
| Package manager | Chocolatey | apt/dnf/pacman | Homebrew |

---

## Troubleshooting

### Platform Not Detected

**Error**: `RuntimeError: Unsupported platform: FreeBSD`

**Solution**: Create a handler for the new platform or map to existing handler

### PostgreSQL Not Found

**Error**: PostgreSQL discovery returns empty list

**Debug**:
```python
platform = get_platform_handler()
paths = platform.get_postgresql_scan_paths()
print(f"Scanned paths: {paths}")
print(f"Install guide:\n{platform.get_postgresql_install_guide()}")
```

### Desktop Shortcuts Not Created

**Windows**: Check if win32com is installed (`pip install pywin32`)
**Linux**: Check if gio command is available (`which gio`)
**macOS**: Desktop shortcuts not yet implemented

---

## References

**Design Patterns**:
- Strategy Pattern: https://refactoring.guru/design-patterns/strategy
- Factory Pattern: https://refactoring.guru/design-patterns/factory-method

**Related Documentation**:
- [Installation Flow & Process](../INSTALLATION_FLOW_PROCESS.md)
- [Handover 0035](../../handovers/0035_HANDOVER_20251019_UNIFIED_CROSS_PLATFORM_INSTALLER.md)
- [CLAUDE.md](../../CLAUDE.md)

**Test Files**:
- `tests/installer/test_platform_handlers.py` - 45 platform handler tests
- `tests/installer/test_unified_installer.py` - 20 integration tests

---

**Last Updated**: 2025-10-19 (v3.1.0)
