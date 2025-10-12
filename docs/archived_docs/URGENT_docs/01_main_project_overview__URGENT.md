# GiljoAI MCP Installation System - CLI Project Overview

## Executive Summary

Ship a professional, cross-platform CLI installation system that delivers zero post-install launch for both localhost development and server deployments. The system standardizes on PostgreSQL 18, provides elevation fallback strategies, and maintains a clean architecture ready for future SaaS expansion without current complexity.

## Project Vision

"Professional installation that just works - localhost or server, no friction"
- < 5 minutes to working system on localhost
- < 10 minutes for server deployment with network configuration
- Foundation for SaaS without the overhead

## Core Architecture Updates (2025-10-02)

### Virtual Environment Implementation
- **Critical Change**: All dependencies now installed in isolated virtual environment
- Uses Python's `venv` module for cross-platform compatibility
- Upgrades pip automatically in new environment
- Venv path: `{install_dir}/venv`

### MCP Registration
- New method `register_with_claude()` added
- Registers MCP server with Claude Code
- Non-blocking registration (warns on failure)
- Uses venv Python path for registration

### Installation Workflow Update
New 8-step installation process:
1. Create Virtual Environment
2. Setup Database
3. Generate Configuration Files
4. Install Dependencies (in venv)
5. Create Launchers
6. Mode-Specific Setup
7. Register with Claude Code
8. Post-Installation Validation

### Claude Code Exclusivity
- Current version supports Claude Code only
- Codex and Gemini support disabled
- Planned re-enablement in 2026
- Clear notices added to installer

### Remaining Technical Debt (5%)
1. Database Migrations (2%)
   - Verify Alembic migrations
   - Standardize schema creation
2. Multi-Tool Support (2%)
   - Codex/Gemini adapters exist but disabled
3. Advanced Validation (1%)
   - Enhanced pre-install checks
   - Network connectivity tests
   - Disk space validation

## Unchanged Core Architecture (Rest of document remains the same from previous version)

## Success Criteria Update

- [x] Virtual environment creation
- [x] Venv-isolated dependencies
- [x] MCP registration integrated
- [x] Auto-start working
- [x] User notifications
- [x] Configuration harmony
- [x] Cross-platform support
- [x] Proper error handling
- [x] Comprehensive logging

*Last Updated: 2025-10-02*
*Implementation Stage: Ready for Testing*