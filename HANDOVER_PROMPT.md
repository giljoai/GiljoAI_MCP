# Handover Prompt - GiljoAI MCP Development Session

## Current Status (October 6, 2025)

**User**: Patrik (GiljoAI Team)
**System**: F: Drive (Windows - Server/LAN Mode Testing)
**Branch**: master
**Last Commit**: `ea7f49c` - "fix: Rollback to working installer, remove wizard complexity"

---

## What Just Happened (Critical Context)

### The Problem (Oct 5-6, 2025)
We spent 4+ hours building a complex standalone wizard that **violated core principles**:
- Moved database creation OUT of CLI installer → INTO wizard
- Created 900+ lines of unnecessary wizard code
- Added `/api/setup/create-database` endpoint (wrong approach)
- Made wizard dependent on API/database (circular dependency)
- Created 5+ wizard documentation files

### The Solution (Oct 6, 2025)
**Complete rollback to working state:**
- ✅ Reverted to commit `635a120` (Oct 5, 2:03 PM - last working installer)
- ✅ Removed all wizard complexity (900+ lines deleted)
- ✅ Deleted `/api/setup/create-database` endpoint
- ✅ Removed MCP tool injection from CLI installer
- ✅ Restored database creation to CLI installer (where it belongs)
- ✅ Updated `IMPLEMENTATION_PLAN.md` as **single source of truth**

### Current State
**CLI Installer is working correctly:**
- PostgreSQL detection
- Database creation during install
- Desktop shortcuts (OneDrive-aware)
- Dependencies installation
- Service launch
- User directed to Settings → Wizard for optional features

**User is NOW running fresh installation test** to verify everything works.

---

## Key Architectural Decisions

### ✅ CORRECT Approach (What We Have Now)

**Phase 0: CLI Installer (Localhost Mode)**
```
1. Detect PostgreSQL software
2. Create giljo_mcp database (CLI installer does this!)
3. Install Python dependencies
4. Create desktop shortcuts
5. Launch application
6. Direct user to Settings → Setup Wizard
```

**Phase 0.5: In-App Setup Wizard (Planned)**
```
Location: frontend/src/views/Settings.vue → New "Setup Wizard" tab

Features:
- Button to configure Claude Code MCP (optional)
- LAN/WAN configuration forms (future)
- Firewall setup buttons (future)
- Advanced settings (future)

NOT a standalone page
NOT part of installation flow
IS a simple tab in Settings for power users
```

### ❌ WRONG Approach (What We Reverted)

**DO NOT:**
- Move database creation to wizard
- Create API endpoints for database setup
- Make wizard standalone/complex
- Add tool injection during CLI install
- Create separate wizard documentation

---

## File Structure & Important Files

### Single Source of Truth
**`docs/IMPLEMENTATION_PLAN.md`** - THE authoritative implementation plan
- Phase 0: CLI Installer ✅ COMPLETE
- Phase 0.5: In-App Wizard (planned)
- Phase 1: Claude Code Agent Profiles (days 1-4)
- Phase 2: Dashboard & Testing (days 5-10)
- Phase 3: LAN/WAN Deployment (future)

### Critical Files Modified Today
- `installer/core/installer.py` - Removed `register_with_claude()` method
- `installer/cli/install.py` - Updated completion message
- `docs/IMPLEMENTATION_PLAN.md` - Updated with correct Phase 0

### Files Deleted (Wizard Cleanup)
- `api/endpoints/setup.py`
- `frontend/src/components/setup/DatabaseStep.vue`
- `docs/INSTALLATION_FLOW_SINGLE_SOURCE_OF_TRUTH.md`
- `docs/devlog/DATABASE_ENDPOINT_REFACTORING_COMPLETE.md`
- 3 more wizard-related session/devlog files

### Installation Runtime Files (Not in Repo)
These get created during install and are `.gitignored`:
- `venv/` - Virtual environment
- `config.yaml` - Generated config
- `.env` - Environment variables
- `*.log` - Runtime logs

**To reset for fresh install:**
```bash
# Delete runtime files
rm -rf venv/
rm -f config.yaml .env *.log

# Drop database
psql -U postgres -c "DROP DATABASE IF EXISTS giljo_mcp;"

# Run fresh install
python installer/cli/install.py
```

---

## Multi-System Development Workflow

**CRITICAL**: This project uses TWO systems with ONE GitHub repo

**System 1 - C: Drive (Localhost Mode)**
- Location: `C:\Projects\GiljoAI_MCP`
- Mode: `localhost` in config.yaml
- Purpose: Development, rapid iteration
- Database: PostgreSQL localhost only
- API: Binds to 127.0.0.1
- No API key required

**System 2 - F: Drive (Server/LAN Mode)** ← **YOU ARE HERE**
- Location: `F:\GiljoAI_MCP`
- Mode: `server` in config.yaml
- Purpose: LAN/server testing, multi-client
- Database: PostgreSQL localhost (always!)
- API: Binds to 0.0.0.0 (network accessible)
- API key required

**Git Workflow (MANDATORY):**
```bash
# Always pull before work
git pull

# Work and commit
git add .
git commit -m "feat: description"
git push

# Other system pulls
git pull
```

**Cross-Platform Rules:**
- ✅ Always use `pathlib.Path()` for file paths
- ✅ Never hardcode drive letters or path separators
- ✅ Config-driven mode differences (localhost vs server)
- ❌ Never commit: .env, config.yaml, venv/, logs/

---

## Database Information

**PostgreSQL Version**: 18 (recommended)
**Database Name**: `giljo_mcp`
**Admin Password**: `4010` (development)

**Roles:**
- `giljo_owner` - Database owner, runs migrations
- `giljo_user` - Application user, limited privileges

**Connection:**
```bash
# List databases
PGPASSWORD=4010 psql -U postgres -l | grep giljo

# Connect
PGPASSWORD=4010 psql -U postgres -d giljo_mcp

# Drop database (fresh install)
PGPASSWORD=4010 psql -U postgres -c "DROP DATABASE IF EXISTS giljo_mcp;"
```

---

## User Preferences & Context

### User's Communication Style
- Direct, no-nonsense
- Prefers concise answers
- Values honesty over agreement
- Will interrupt if going wrong direction

### User's Expectations
- **Production-grade code only** (no "v2" variants, no band-aids)
- Chef's Kiss quality
- Single source of truth for docs
- Cross-platform compatibility (Windows/Linux/macOS)
- No emojis unless requested

### What the User Values
- **Simplicity over complexity**
- CLI installer handles essentials
- In-app wizard for advanced features
- Clear separation of concerns
- Maintainable, understandable code

### What Frustrates the User
- Circular dependencies
- Moving core functionality to UI
- Creating unnecessary complexity
- Multiple "source of truth" documents
- Agents implementing when they should coordinate

---

## Current Task: Fresh Installation Test

**User is NOW testing** the corrected CLI installer to verify:
1. PostgreSQL detection works
2. Database creation succeeds
3. Dependencies install properly
4. Desktop shortcuts created
5. Application launches
6. Frontend accessible
7. No wizard complexity

**If test succeeds:**
- Continue with Phase 1 (Claude Code integration)
- Build simple in-app wizard (Settings tab)

**If test fails:**
- Debug installer issues
- Fix root cause
- Do NOT add wizard complexity

---

## Agent Coordination Rules

### When to Use Specific Agents

**orchestrator-coordinator**: Strategic planning, multi-agent coordination
**system-architect**: Understanding dependencies, architectural decisions
**database-expert**: Database schema, migrations, PostgreSQL
**tdd-implementor**: Feature implementation (after architecture decided)
**backend-integration-tester**: API testing, integration validation
**frontend-tester**: UI component testing
**documentation-manager**: Session memories, devlogs, documentation
**deep-researcher**: Technology evaluation, best practices research

### CRITICAL Agent Rules
- ❌ **Orchestrator does NOT implement** - they coordinate
- ✅ **TDD implementor implements** - after design is clear
- ✅ **Always use specialized agents** - don't do their work
- ✅ **One agent in_progress at a time** - don't batch completions

---

## Next Steps (After Install Test Completes)

### Immediate (Phase 1 - Days 1-4)
1. Create Claude Code agent profiles (8 files)
2. Implement prompt generator for orchestrator
3. Add project activation API endpoint
4. Test end-to-end orchestration flow

### Short-term (Phase 2 - Days 5-10)
1. Add "Activate Project" button to dashboard
2. Create orchestrator prompt dialog
3. Enhance WebSocket agent updates
4. Build simple in-app wizard (Settings tab)

### Long-term (Phase 3 - Future)
1. LAN deployment enhancements
2. WAN deployment support
3. Multi-tool support (beyond Claude Code)

---

## Important Commands

### Installation
```bash
python installer/cli/install.py      # Fresh install
install.bat                          # Windows wrapper
```

### Development
```bash
# Start services
python start_giljo.py
start_giljo.bat

# Backend only
python api/run_api.py

# Frontend only
cd frontend && npm run dev
```

### Testing
```bash
pytest tests/                        # All tests
pytest tests/unit/                   # Unit tests
pytest tests/integration/            # Integration tests
```

### Git
```bash
git status
git add .
git commit -m "type: description"
git push
git pull
```

---

## Red Flags to Watch For

🚨 **If you find yourself doing these, STOP:**
- Moving database creation out of CLI installer
- Creating standalone wizard pages
- Adding API endpoints for installation tasks
- Building complex multi-step wizard flows
- Creating multiple "source of truth" documents
- Implementing without consulting system-architect
- Using orchestrator to implement instead of coordinate

✅ **Instead:**
- Keep CLI installer simple and database-focused
- Build in-app wizard as Settings tab
- Use IMPLEMENTATION_PLAN.md as single source
- Consult specialized agents for their domains
- Ask user for clarification if unsure

---

## Lessons Learned (Oct 5-6, 2025)

1. **CLI installer MUST create database** - Never move to UI
2. **Keep wizards simple** - Settings tab, not standalone page
3. **Don't move core functionality to UI** - Installation ≠ Configuration
4. **Single source of truth** - IMPLEMENTATION_PLAN.md only
5. **User's vision is right** - Listen when they correct direction
6. **Agents have roles** - Orchestrator coordinates, doesn't implement
7. **Simplicity wins** - 200 lines > 1000+ lines of complexity

---

## Files to Reference

### Must Read
- `docs/IMPLEMENTATION_PLAN.md` - Single source of truth
- `CLAUDE.md` - Project instructions for Claude Code
- `docs/TECHNICAL_ARCHITECTURE.md` - System architecture

### Important Context
- `docs/deployment/LAN_DEPLOYMENT_RUNBOOK.md` - LAN deployment
- `docs/manuals/MCP_TOOLS_MANUAL.md` - MCP tools reference

### Recent Work
- `docs/sessions/2025-10-06_installation_rollback_session.md` - This session
- `docs/devlog/2025-10-06_installation_rollback_complete.md` - This devlog

---

## Quick Reference: What's Working Now

✅ CLI installer (localhost mode)
✅ PostgreSQL detection
✅ Database creation during install
✅ Desktop shortcuts
✅ Virtual environment setup
✅ Dependency installation
✅ Service launch
✅ Cross-platform paths (pathlib.Path)
✅ Multi-system git workflow
✅ IMPLEMENTATION_PLAN.md as single source

❌ Wizard complexity (removed)
❌ Tool injection during install (removed)
❌ API database creation endpoint (removed)
❌ Multiple source of truth docs (consolidated)

---

## Final Notes

**The user is testing the installer RIGHT NOW.** When they return:

1. **If successful**: Celebrate! Ask about Phase 1 (Claude Code integration)
2. **If failed**: Debug calmly, fix root cause, no band-aids
3. **If confused**: Read IMPLEMENTATION_PLAN.md line 1-200
4. **If unsure**: Ask user directly, don't assume

**Remember**: This user values **simplicity, honesty, and production-grade code**. When in doubt, ask. They'd rather you ask than go down the wrong path for hours.

Good luck! 🚀

---

**Handover Date**: October 6, 2025
**Handover Time**: ~1:30 AM EST
**Session Duration**: ~2.5 hours
**Lines Changed**: +3817 / -2785
**Commits**: 1 (ea7f49c)
**Status**: ✅ Installer running, awaiting test results
