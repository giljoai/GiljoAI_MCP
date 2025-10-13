# Phase 0: Installer/Wizard Architecture Harmonization

**Version:** 1.0 | **Date:** October 5, 2025 | **Status:** Design Complete

## Executive Summary

Architectural split between CLI installer (minimal setup) and frontend wizard (user configuration) for GiljoAI MCP Phase 0.

### Problem

Current CLI installer attempts tasks that are impossible/unreliable:
- Cannot auto-configure firewall (requires elevation)
- Cannot reliably detect AI tools
- Cannot access correct user home directory for MCP registration
- Cannot test if MCP connection works

### Solution

**CLI**: Minimal setup (database, venv, config files)
**Wizard**: User configuration (deployment mode, MCP registration, testing)

## Architecture

```
CLI Installer → Creates minimal localhost setup
      ↓
Opens Browser → http://localhost:7274/setup
      ↓  
Frontend Wizard → User configures deployment, MCP, network
      ↓
Backend API → /api/setup/* endpoints
      ↓
PostgreSQL Database → Ready for use
```

## Key Decisions

1. **PostgreSQL**: Manual install (redirect to download if missing)
2. **Firewall**: Show instructions only (cannot auto-configure)
3. **MCP Registration**: Frontend wizard in user context
4. **Database Testing**: Extract component from SettingsView, reuse in wizard
5. **Localhost First**: Default to localhost, allow LAN upgrade via wizard

See related documents for details:
- `installer_responsibilities.md`
- `wizard_responsibilities.md`
- `api_endpoints_specification.md`
- `component_extraction_design.md`
