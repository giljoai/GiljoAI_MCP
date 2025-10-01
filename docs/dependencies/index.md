# Dependencies Index

Welcome to the GiljoAI MCP dependencies documentation. This section provides detailed information about all dependencies used in the project, organized by functionality.

## Quick Navigation

### 📋 [Complete Dependencies Guide](../DEPENDENCIES.md)

Comprehensive list of all dependencies with versions, purposes, and installation instructions.

### 🔗 Communication & WebSocket Dependencies

- [WebSocket Dependencies](./websocket.md) - aiohttp, websockets, communication protocols
- [API Dependencies](./api.md) - FastAPI, HTTP clients, REST endpoints

### 🗄️ Database Dependencies

- [Database Dependencies](./database.md) - SQLAlchemy, drivers, migrations

### 🔐 Security Dependencies

- [Authentication & Security](./security.md) - JWT, password hashing, encryption

### 🤖 AI Integration Dependencies

- [AI & ML Dependencies](./ai.md) - OpenAI, Anthropic, token counting

### 🛠️ Development Dependencies

- [Development Tools](./development.md) - Testing, linting, code quality

### 🎨 Frontend Dependencies

- [Frontend Dependencies](./frontend.md) - Vue.js, dashboard components

## Critical Dependencies Overview

### Core Runtime (Always Required)

| Component      | Purpose                        | Documentation                     |
| -------------- | ------------------------------ | --------------------------------- |
| **aiohttp**    | WebSocket client communication | [WebSocket Guide](./websocket.md) |
| **fastapi**    | REST API & WebSocket server    | [API Guide](./api.md)             |
| **sqlalchemy** | Database ORM                   | [Database Guide](./database.md)   |
| **pydantic**   | Data validation                | [API Guide](./api.md)             |

### Communication Stack

| Component      | Purpose            | Documentation                     |
| -------------- | ------------------ | --------------------------------- |
| **websockets** | WebSocket protocol | [WebSocket Guide](./websocket.md) |
| **httpx**      | HTTP client        | [API Guide](./api.md)             |

### Database Stack

| Component     | Purpose                 | Documentation                   |
| ------------- | ----------------------- | ------------------------------- |
| **aiopostgresql** | PostgreSQL async driver     | [Database Guide](./database.md) |
| **asyncpg**   | PostgreSQL async driver | [Database Guide](./database.md) |

## Installation Overview

All dependencies are automatically installed via the installer:

```bash
# Automatic installation (recommended)
python bootstrap.py

# Manual installation
pip install -r requirements.txt
```

## Platform-Specific Notes

### Windows

- Requires **pywin32** for service management
- Some packages may need Visual C++ Build Tools

### macOS

- Standard installation via pip
- May require Xcode Command Line Tools

### Linux

- May require development headers for PostgreSQL
- Package manager specific instructions in each guide

## Version Compatibility

### Python Support

- **Minimum:** Python 3.8
- **Recommended:** Python 3.10+
- **Tested:** 3.8, 3.9, 3.10, 3.11, 3.12

### Package Versioning

All packages use minimum version specifications (`>=`) to ensure compatibility while allowing updates.

## Troubleshooting

### Common Issues

1. **Import errors** - Check [Complete Dependencies Guide](../DEPENDENCIES.md#troubleshooting)
2. **WebSocket connection issues** - See [WebSocket Guide](./websocket.md#troubleshooting)
3. **Database connection problems** - See [Database Guide](./database.md#troubleshooting)

### Getting Help

- [Main Dependencies Guide](../DEPENDENCIES.md)
- [Installation Guide](../../README.md#dependencies)
- [Issue Tracker](https://github.com/patrik-giljoai/GiljoAI-MCP/issues)

## Contributing

When adding new dependencies:

1. Update the appropriate category documentation
2. Add to the main [DEPENDENCIES.md](../DEPENDENCIES.md)
3. Update installer validation
4. Test across all supported platforms

---

_This documentation is automatically validated against the actual requirements.txt file._
