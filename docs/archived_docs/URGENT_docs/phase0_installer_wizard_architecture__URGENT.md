# Phase 0: Installer/Wizard Architecture

Version 1.0 | October 5, 2025 | System Architect

## Problem

CLI installer attempts impossible tasks:
- Cannot configure firewall (requires elevation)
- Cannot detect AI tools reliably
- Cannot access user home for MCP registration
- Cannot test MCP connections

## Solution

Split responsibilities:
- CLI: Minimal setup (database, venv, configs)
- Wizard: User configuration (deployment, MCP, testing)

## See Related Documents

- installer_responsibilities.md
- wizard_responsibilities.md
- api_endpoints_specification.md
- component_extraction_design.md
