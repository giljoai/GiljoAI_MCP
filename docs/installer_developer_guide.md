# GiljoAI MCP Installer - Developer Guide

## Architecture Overview

The GiljoAI MCP installer is built as a modular, cross-platform system with the following architecture:

```
installer/
├── core/                   # Core system components
│   ├── profile.py         # Profile management system
│   ├── health.py          # Health checking framework
│   └── health_integration.py  # Health check integration
├── dependencies/          # Component installers
│   ├── postgresql.py      # PostgreSQL installer
│   ├── redis.py          # Redis installer
│   └── docker.py         # Docker installer
├── services/             # Service management
│   ├── service_manager.py # Cross-platform service control
│   └── windows/          # Windows-specific services
│   └── macos/            # macOS-specific services
│   └── linux/            # Linux-specific services
├── config/               # Configuration management
│   ├── config_manager.py # Configuration generation
│   └── templates/        # Configuration templates
└── docker/               # Docker configurations
```

## Core Components

### Profile System (`installer/core/profile.py`)

The profile system provides deployment type management:

```python
from installer.core.profile import ProfileManager, ProfileType

# Initialize profile manager
profile_mgr = ProfileManager()

# Create profile
profile = profile_mgr.create_profile(
    name="my-project",
    profile_type=ProfileType.DEVELOPER,
    settings={
        'database_type': 'sqlite',
        'enable_redis': False
    }
)

# Get profile requirements
deps = profile_mgr.get_dependencies(profile)
```

#### Profile Types

- `DEVELOPER`: Local development setup
- `TEAM`: Multi-user team environment
- `ENTERPRISE`: Production enterprise deployment
- `RESEARCH`: High-performance research environment

### Health Check System (`installer/core/health.py`)

Comprehensive health monitoring framework:

```python
from installer.core.health import HealthChecker

# Initialize health checker
health = HealthChecker()

# Add health check
health.add_check(
    name="database_connection",
    check_func=check_database,
    required=True
)

# Run all checks
results = health.run_all_checks()
```

### Configuration Manager (`installer/config/config_manager.py`)

Profile-based configuration generation:

```python
from installer.config.config_manager import ConfigurationManager

# Initialize config manager
config_mgr = ConfigurationManager()

# Generate configuration
success = config_mgr.generate_config(
    profile_type='developer',
    user_inputs={
        'host': 'localhost',
        'port': 8000,
        'database_type': 'sqlite'
    },
    output_dir=Path('.')
)
```

#### Generated Files

- `config.yaml`: Main application configuration
- `.env`: Environment variables
- Service-specific configurations

## Component Installers

### PostgreSQL Installer (`installer/dependencies/postgresql.py`)

Handles PostgreSQL installation and configuration:

```python
from installer.dependencies.postgresql import PostgreSQLInstaller

# Initialize installer
pg_installer = PostgreSQLInstaller()

# Check if already installed
if pg_installer.is_installed():
    print("PostgreSQL already available")
else:
    # Install PostgreSQL
    success = pg_installer.install()

# Verify installation
health = pg_installer.health_check()
```

#### Features

- Cross-platform installation detection
- Automated service creation
- Connection testing
- Configuration optimization

### Redis Installer (`installer/dependencies/redis.py`)

Redis installation with Windows automation:

```python
from installer.dependencies.redis import RedisInstaller

redis_installer = RedisInstaller()

# Install Redis (Windows automation included)
success = redis_installer.install()

# Configure Redis service
redis_installer.configure_service()

# Test connection
connected = redis_installer.test_connection()
```

#### Features

- Windows Redis automation
- Service installation
- Memory configuration
- Connection validation

### Docker Installer (`installer/dependencies/docker.py`)

Docker Desktop and Engine management:

```python
from installer.dependencies.docker import DockerInstaller

docker_installer = DockerInstaller()

# Check Docker availability
status = docker_installer.check_installation()

# Guide user through Docker setup
if not docker_installer.is_installed():
    docker_installer.install_guide()

# Verify Docker daemon
daemon_running = docker_installer.is_daemon_running()
```

#### Features

- Docker Desktop download guidance
- Docker Engine installation (Linux)
- Daemon health monitoring
- Container runtime testing

## Service Management

### Service Manager (`installer/services/service_manager.py`)

Cross-platform service lifecycle management:

```python
from installer.services.service_manager import ServiceManager

service_mgr = ServiceManager()

# Install service
service_mgr.install_service(
    name="giljo-mcp",
    executable="/path/to/python",
    args=["-m", "src.giljo_mcp.server"],
    description="GiljoAI MCP Orchestrator"
)

# Control service
service_mgr.start_service("giljo-mcp")
service_mgr.stop_service("giljo-mcp")
service_mgr.restart_service("giljo-mcp")

# Check status
status = service_mgr.get_service_status("giljo-mcp")
```

#### Platform Support

- **Windows**: Windows Service using `pywin32`
- **macOS**: launchd plist files
- **Linux**: systemd service files

#### Features

- Service installation/uninstallation
- Start/stop/restart operations
- Status monitoring
- Auto-start configuration
- Dependency ordering

## Integration Points

### Bootstrap Integration (`bootstrap.py`)

The bootstrap system integrates all components:

```python
# Component availability check
from installer.core.health import HealthChecker
from installer.config.config_manager import ConfigurationManager
from installer.services.service_manager import ServiceManager

# Integrated dependency checking
def check_integrated_dependencies():
    components = {
        'postgresql': PostgreSQLInstaller,
        'redis': RedisInstaller,
        'docker': DockerInstaller,
        'service_manager': ServiceManager,
        'config_manager': ConfigurationManager
    }

    for name, component in components.items():
        try:
            instance = component()
            print(f"✓ {name} available")
        except Exception as e:
            print(f"✗ {name} error: {e}")
```

### GUI Integration (`setup_gui.py`)

The GUI installer integrates with all Phase 2 components:

- **Profile Selection Page**: Uses `ProfileManager`
- **Progress Page**: Integrates all installers
- **Service Control Page**: Uses `ServiceManager`
- **Configuration Page**: Uses `ConfigurationManager`

### CLI Integration (`setup.py`)

CLI installer with Phase 2 component support:

```python
# Phase 2 component imports
from installer.core.profile import ProfileManager, ProfileType
from installer.config.config_manager import ConfigurationManager
from installer.services.service_manager import ServiceManager
# ... other imports

class GiljoSetup:
    def __init__(self):
        self.profile_manager = ProfileManager()
        self.config_manager = ConfigurationManager()
        self.service_manager = ServiceManager()
```

## Development Guidelines

### Adding New Components

1. **Create installer class**:

```python
class MyComponentInstaller:
    def __init__(self):
        self.platform = platform.system().lower()

    def is_installed(self) -> bool:
        """Check if component is installed"""
        pass

    def install(self) -> bool:
        """Install the component"""
        pass

    def health_check(self) -> bool:
        """Verify component health"""
        pass
```

2. **Add to integration tests**:

```python
def test_my_component_integration():
    installer = MyComponentInstaller()
    assert installer.is_installed() or installer.install()
    assert installer.health_check()
```

3. **Update bootstrap**:

```python
# Add to bootstrap._check_integrated_dependencies()
try:
    from installer.dependencies.my_component import MyComponentInstaller
    self.print_status("My Component available", "success")
except ImportError:
    self.print_status("My Component not available", "warning")
```

### Testing Components

#### Unit Tests

```python
# tests/installer/unit/test_my_component.py
import pytest
from installer.dependencies.my_component import MyComponentInstaller

def test_installer_init():
    installer = MyComponentInstaller()
    assert installer is not None

def test_installation_check():
    installer = MyComponentInstaller()
    result = installer.is_installed()
    assert isinstance(result, bool)
```

#### Integration Tests

```python
# tests/installer/integration/test_installation_flow.py
def test_complete_installation():
    """Test complete installation flow"""
    # Test profile creation
    # Test component installation
    # Test service configuration
    # Test health checks
```

### Code Style Guidelines

1. **Type Hints**: All functions should have type hints
2. **Docstrings**: All classes and methods need docstrings
3. **Error Handling**: Comprehensive exception handling
4. **Logging**: Use structured logging
5. **Cross-Platform**: Support Windows, macOS, and Linux

### Error Handling Patterns

```python
class InstallerError(Exception):
    """Base installer exception"""
    pass

class ComponentInstaller:
    def install(self) -> bool:
        try:
            self._perform_installation()
            return True
        except FileNotFoundError:
            logger.error("Installation files not found")
            return False
        except PermissionError:
            logger.error("Insufficient permissions")
            return False
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return False
```

## Testing Framework

### Test Structure

```
tests/installer/
├── unit/                  # Unit tests for individual components
│   ├── test_profile.py
│   ├── test_postgresql_installer.py
│   ├── test_redis_installer.py
│   ├── test_docker_installer.py
│   └── test_health_checker.py
├── integration/           # Integration tests
│   └── test_installation_flow.py
├── fixtures/              # Test data and mocks
│   ├── test_configs.py
│   └── mock_utils.py
└── conftest.py           # Pytest configuration
```

### Running Tests

```bash
# Run all tests
pytest tests/installer/

# Run specific test category
pytest tests/installer/unit/
pytest tests/installer/integration/

# Run with coverage
pytest --cov=installer tests/installer/
```

### Mock Utilities

```python
# tests/installer/fixtures/mock_utils.py
from unittest.mock import Mock, patch

def mock_postgresql_installer():
    """Mock PostgreSQL installer for testing"""
    mock = Mock()
    mock.is_installed.return_value = True
    mock.install.return_value = True
    mock.health_check.return_value = True
    return mock
```

## Debugging and Troubleshooting

### Debug Mode

```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Run installer with debug
installer = PostgreSQLInstaller()
installer.set_debug_mode(True)
```

### Common Development Issues

1. **Import Errors**: Check Python path and module structure
2. **Permission Issues**: Ensure proper privileges for installation
3. **Platform Differences**: Test on all supported platforms
4. **Service Installation**: Check service manager platform support

### Profiling Performance

```python
import cProfile
import pstats

# Profile installation
pr = cProfile.Profile()
pr.enable()

# Run installation code
installer.install()

pr.disable()
stats = pstats.Stats(pr)
stats.sort_stats('cumulative').print_stats(10)
```

## Contributing

### Development Setup

```bash
# Clone repository
git clone https://github.com/yourusername/giljo-mcp.git
cd giljo-mcp

# Create development environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install development dependencies
pip install -r requirements-dev.txt

# Install in development mode
pip install -e .
```

### Pull Request Guidelines

1. **Test Coverage**: Maintain >90% test coverage
2. **Cross-Platform**: Test on Windows, macOS, and Linux
3. **Documentation**: Update relevant documentation
4. **Backwards Compatibility**: Maintain API compatibility
5. **Performance**: No performance regressions

### Code Review Checklist

- [ ] All tests pass
- [ ] Code follows style guidelines
- [ ] Documentation updated
- [ ] Cross-platform compatibility verified
- [ ] Error handling implemented
- [ ] Logging added where appropriate
- [ ] Type hints included
- [ ] Security considerations addressed
