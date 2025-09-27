# Configuration and Reference Files Index

This document provides a comprehensive index of all configuration, environment, and reference files in the GiljoAI MCP project.

## 🔧 Environment Configuration Files

### Root Environment Files

- **`.env`** - Main environment configuration (active)
- **`.env.example`** - Template for environment variables (use this as reference)
- **`.env.dev`** - Development environment settings
- **`.env.prod`** - Production environment settings
- **`.env.env.backup`** - Backup of environment configuration

### Frontend Environment

- **`frontend/.env.test`** - Frontend test environment configuration

## ⚙️ Application Configuration

### Core Configuration

- **`config.yaml`** - Main application configuration
- **`alembic.ini`** - Database migration configuration (Alembic)
- **`requirements.txt`** - Python dependencies specification
- **`CLAUDE.md`** - AI assistant instructions with template system documentation

### MCP Server Configuration

- **`.mcp.json`** - Primary MCP server configuration
- **`.mcp-serena.json`** - Serena MCP server configuration
- **`.serena/project.yml`** - Serena project settings

### Docker Configuration

- **`docker-compose.yml`** - Main Docker Compose configuration
- **`docker-compose.dev.yml`** - Development Docker setup
- **`docker-compose.prod.yml`** - Production Docker setup
- **`docker/nginx.conf`** - Nginx web server configuration

### Frontend Configuration

- **`frontend/package.json`** - Node.js dependencies and scripts
- **`frontend/package-lock.json`** - Locked dependency versions

## 📊 Test Results & Reports

- **`test_results.json`** - Unit test results
- **`complete_test_results.json`** - Full test suite results
- **`final_validation_results.json`** - Final validation report
- **`frontend_mock_test_results.json`** - Frontend mock test results

## 🎨 Reference Files

- **`Docs/Website colors.txt`** - Color palette reference
- **`.claude/settings.local.json`** - Claude Code editor settings

## 📍 Important File Locations

### Configuration Hierarchy

1. **Environment Variables** (`.env*` files) - Highest priority
2. **Application Config** (`config.yaml`) - Default settings
3. **Service Configs** (`.mcp.json`, `docker-compose.yml`) - Service-specific

### Where to Look for Settings

#### Database Configuration

- Check: `.env`, `config.yaml`, `alembic.ini`
- Docker: `docker-compose.yml`

#### API Configuration

- Check: `.env`, `config.yaml`
- API endpoints: See `/docs/api/api_implementation_guide.md`

#### Frontend Configuration

- Check: `frontend/.env.test`, `frontend/package.json`
- Build settings: `frontend/vite.config.js` (if exists)

#### MCP/Orchestration Settings

- Check: `.mcp.json`, `.mcp-serena.json`
- Serena: `.serena/project.yml`
- Template System: `src/giljo_mcp/template_manager.py` (single source of truth)
- Legacy Templates: `src/giljo_mcp/mission_templates.py` (deprecated)

#### Docker/Deployment Settings

- Check: `docker-compose*.yml` files
- Nginx: `docker/nginx.conf`

## 🔐 Security Notes

### Sensitive Files (Never Commit)

- `.env` (use `.env.example` as template)
- `.env.dev`
- `.env.prod`
- Any file with actual credentials

### Safe to Commit

- `.env.example`
- `*.json` configuration files (without secrets)
- `docker-compose.yml` (with placeholder values)

## 🚀 Quick Setup Guide

1. **Copy Environment Template**

   ```bash
   cp .env.example .env
   ```

2. **Edit Configuration**

   - Update `.env` with your settings
   - Modify `config.yaml` if needed

3. **Install Dependencies**

   ```bash
   pip install -r requirements.txt
   cd frontend && npm install
   ```

4. **Database Setup**
   ```bash
   alembic upgrade head
   ```

## 📝 Configuration Documentation

For detailed documentation on specific configurations:

- **Docker**: See `/docs/docker/docker_setup_guide.md`
- **API**: See `/docs/api/api_implementation_guide.md`
- **Template System**: See `/docs/api/templates.md` and `/docs/guides/template_migration.md`
- **Testing**: See `/docs/tests/CONSOLIDATED_TEST_DOCUMENTATION.md`
- **Scripts**: See `/docs/scripts/scripts_setup_guide.md`

## 🔄 Configuration Load Order

1. System environment variables
2. `.env` file variables
3. `config.yaml` defaults
4. Hard-coded defaults in code

## 📌 Best Practices

1. **Always use `.env.example`** as reference for required variables
2. **Never hardcode secrets** in configuration files
3. **Use environment-specific files** (dev/prod) for different deployments
4. **Document new configuration** when adding settings
5. **Keep test data separate** in test-specific config files

---

_Last Updated: January 2025_
_Note: This index should be updated when new configuration files are added_
