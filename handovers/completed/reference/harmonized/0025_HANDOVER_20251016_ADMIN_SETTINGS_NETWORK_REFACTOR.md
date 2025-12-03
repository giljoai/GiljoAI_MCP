# 0025_HANDOVER_20251016_ADMIN_SETTINGS_NETWORK_REFACTOR.md

## Project Overview
**Handover ID**: 0025  
**Date Created**: 2025-10-16  
**Status**: ACTIVE  
**Priority**: HIGH  
**Type**: Refactor/Architecture Alignment  

## Objective
Refactor the Admin Settings Network section to align with v3.0 unified architecture by:
- Removing deprecated MODE setting and localhost references
- Updating API server host binding display and configuration
- Enhancing CORS section with proper labeling
- Removing deprecated functions (Re-Run Wizard, API information, deployment mode)

## Background Context
GiljoAI MCP has moved to a unified v3.0 architecture where:
- Application always binds to 0.0.0.0 (all interfaces)
- OS firewall controls access (localhost-only by default)
- ONE authentication flow for all connections
- No deployment modes - single codebase for all contexts
- Default credentials (admin/admin) with forced password change

The current Admin Settings still contains legacy localhost/deployment mode concepts that need removal.

## Scope of Work

### 1. Remove MODE Setting Functionality
- [ ] Remove green badge showing "LOCALHOST" 
- [ ] Remove all mode-related UI components
- [ ] Clean up backend code managing localhost mode
- [ ] Scrub codebase for localhost references as deployment identifier

### 2. Update API Server Host Binding
- [ ] Show user-configured binding from install.py (yaml/env file)
- [ ] Remove "localhost or specific IP" instructions
- [ ] Add change button for IP address configuration
- [ ] Implement port change functionality (if not hardcoded)

### 3. Enhance CORS Section
- [ ] Add labels: "API server" and "Frontend application server"
- [ ] Make IP addresses dynamic based on user configuration
- [ ] Clarify "Add new origin" functionality
- [ ] Remove API information (handled elsewhere)

### 4. Remove Deprecated Functions
- [ ] Remove "Change deployment mode" and related functions
- [ ] Remove "Re-Run Wizard" 
- [ ] Identify reused functions (avatar → user/admin settings)
- [ ] Preserve functions used elsewhere, remove duplicates

## Technical Requirements

### Files to Analyze/Modify
- `frontend/src/views/SystemSettings.vue` (confirmed modified in git status)
- Backend configuration files (config.yaml, .env handling)
- API endpoints for network configuration
- Related Vue components for settings management

### Configuration Sources
- `config.yaml` - System configuration
- `.env` - Environment variables
- `install.py` - Installation configuration generation

## Questions to Resolve
1. Is backend port hardcoded or configurable?
2. What does "Add new origin" mean in CORS context?
3. Which functions are reused elsewhere and should be preserved?
4. How are IP/port changes applied (restart required?)?

## Acceptance Criteria
- [ ] No MODE setting or localhost deployment references
- [ ] Clear API server binding display with change functionality
- [ ] Enhanced CORS section with proper labeling
- [ ] Removed deprecated functions without breaking reused components
- [ ] Updated documentation reflecting v3.0 architecture
- [ ] All changes tested and working

## Notes
- Follow cross-platform coding standards (pathlib.Path)
- Maintain multi-tenant isolation principles
- Ensure authentication always enabled
- Document any breaking changes

## Dependencies
- Understanding current SystemSettings.vue implementation
- Backend configuration management system
- CORS handling in FastAPI application

---

**Next Steps**: Analyze current Admin Settings Network implementation to understand scope of changes needed.