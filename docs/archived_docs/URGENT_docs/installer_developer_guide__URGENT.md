# GiljoAI MCP Developer Guide (CLI Installation)

## Overview

This guide provides comprehensive instructions for developers working with the GiljoAI MCP CLI installer and development environment.

## Development Environment Setup

### Prerequisites

- Python 3.9+ (64-bit)
- PostgreSQL 18
- Click library for CLI management
- Minimum 8GB RAM
- 10GB free disk space

### Installation

```bash
# Clone the repository
git clone https://github.com/GiljoAI/mcp.git
cd mcp

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`

# Install development dependencies
pip install -r requirements-dev.txt
```

## CLI Development

### Installer Architecture

The CLI installer is built using:
- Python
- Click library for command parsing
- PostgreSQL 18 as primary database
- Custom health checking system

### Key Components

- `install.py`: Main entry point for installation
- `giljo_mcp/installer/`: Core installation logic
- `giljo_mcp/health/`: System health validation

### Custom Installation Modes

```python
@click.command()
@click.option('--mode', type=click.Choice(['localhost', 'server']))
@click.option('--db-port', default=5432)
def install(mode, db_port):
    """CLI installation with custom configuration"""
    if mode == 'localhost':
        configure_localhost(db_port)
    elif mode == 'server':
        configure_server(db_port)
```

## Development Workflow

### Running Installer in Development Mode

```bash
# Interactive development installation
python install.py --dev

# Non-interactive development installation
python install.py --dev --non-interactive
```

### Configuration Management

Configuration is managed through:
- `config.yaml`: Main configuration file
- Environment variables
- CLI parameters

Example configuration:

```yaml
development:
  database:
    type: postgresql
    version: 18
    host: localhost
    port: 5432
  server:
    host: localhost
    port: 8000
```

## Testing

### Running Tests

```bash
# Run all tests
pytest tests/installer/

# Run specific test suite
pytest tests/installer/test_postgresql.py

# Generate coverage report
pytest --cov=giljo_mcp tests/
```

### Test Categories

- Unit Tests: Individual component testing
- Integration Tests: Database and service interactions
- Health Check Tests: System validation

## Logging and Debugging

Logs are stored in:
- Windows: `%USERPROFILE%\.giljo-mcp\logs\`
- Mac/Linux: `~/.giljo-mcp/logs/`

Logging levels:
- DEBUG: Detailed development information
- INFO: General installation steps
- WARNING: Potential configuration issues
- ERROR: Installation failures

## Contribution Guidelines

1. Fork the repository
2. Create feature branch
3. Implement changes
4. Write comprehensive tests
5. Update documentation
6. Submit pull request

## Performance Optimization

- Use async PostgreSQL connections
- Minimize file system interactions
- Implement efficient configuration parsing

## Troubleshooting

### Common Development Issues

1. PostgreSQL Connection Failures
   - Verify PostgreSQL 18 is running
   - Check connection parameters
   - Validate user permissions

2. Python Dependency Conflicts
   - Use virtual environments
   - Regularly update `requirements.txt`

## Advanced Development

### Custom Extension Points

Developers can extend the installer by:
- Implementing custom health checks
- Adding new configuration parsers
- Creating database migration scripts

## Support

- GitHub Issues: https://github.com/GiljoAI/mcp/issues
- Developer Documentation: https://docs.giljo-mcp.com/dev
