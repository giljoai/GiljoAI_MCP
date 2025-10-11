# Documentation Update Handoff Document
## From: Project Manager (Orchestrator)
## To: Documentation-Architect Agent
## Date: 2025-10-01

---

## PROJECT MISSION

Update ALL project documentation to reflect the new CLI-only installation system with PostgreSQL 18 as the sole database option. This is a complete documentation alignment effort working in PARALLEL with the implementation team.

## CRITICAL CONTEXT

The project has been refactored to:
- **CLI installer ONLY** (no GUI)
- **Two modes only**: localhost (developer) and server (team deployment)
- **PostgreSQL 18** as the ONLY database
- **Simplified architecture** removing enterprise complexity

## YOUR PRIMARY TASKS

### TASK 1: Update Root Documentation Files (HIGHEST PRIORITY)

#### 1.1 README.md (C:\Projects\GiljoAI_MCP\README.md)
**Current Issues**:
- Lines 121-127: References GUI installer with `install.bat`, `quickstart.sh`, `bootstrap.py`
- Lines 153-158: Shows three modes (Developer/Team/Enterprise) instead of two
- Lines 94-96: Mentions multiple database options
- Throughout: References to GUI installer

**Required Changes**:
```markdown
# Change installation section to:
# 2. Run the CLI installer (3 minutes)
python install.py        # Interactive CLI installer

# Update modes table to:
| Mode         | Best For                        | Database    | Auth      | Network            |
| ------------ | ------------------------------- | ----------- | --------- | ------------------ |
| **Localhost** | Individual development          | PostgreSQL 18 | None      | Localhost only     |
| **Server**   | Teams, LAN/WAN deployment       | PostgreSQL 18 | API Keys  | Network accessible |

# Remove all references to:
- GUI installer
- SQLite/MySQL
- Enterprise tier
- bootstrap.py launching GUI
```

#### 1.2 requirements.txt (C:\Projects\GiljoAI_MCP\requirements.txt)
**Current Issues**:
- Line 52: `pillow>=10.0.0` for GUI installer logo
- No explicit GUI dependencies but need to verify

**Required Changes**:
- Remove `pillow` if only used for GUI
- Ensure only PostgreSQL drivers: `psycopg2-binary`, `asyncpg`
- Add if missing: `click>=8.1.0` for CLI

#### 1.3 INSTALL.md (C:\Projects\GiljoAI_MCP\INSTALL.md)
**Current Issues**:
- Lines 33-42: Shows GUI flow with bootstrap.py → setup_gui.py
- Line 23: Optional PostgreSQL instead of required
- Entire quick start section assumes GUI

**Required Changes**:
- Complete rewrite for CLI-only flow
- PostgreSQL 18 as REQUIRED prerequisite
- Document both installation modes clearly
- Include fallback script instructions for elevation issues

#### 1.4 CLAUDE.md (C:\Projects\GiljoAI_MCP\CLAUDE.md)
**Current Issues**:
- Line 20: "Enterprise Network Mode" should be "Server Mode"
- Lines 33-35: References GUI installer
- Line 40: References setup.py without clarifying it's CLI

**Required Changes**:
- Rename "Enterprise Network Mode" to "Server Mode"
- Update installation commands to CLI-only
- Remove GUI references
- Clarify setup.py is CLI interactive

### TASK 2: Update Technical Documentation

#### 2.1 docs/TECHNICAL_ARCHITECTURE.md
**Focus Areas**:
- Remove all multi-database abstraction sections
- Document PostgreSQL 18 as the strategic choice
- Remove GUI architecture components
- Simplify to two deployment modes
- Remove unimplemented enterprise features

#### 2.2 docs/PROJECT_ORCHESTRATION_PLAN.md
**Focus Areas**:
- Update to reflect 5-agent orchestration team (not 11)
- Remove any GUI-specific agent references
- Update installation flow to CLI-only process
- Ensure PostgreSQL-only architecture throughout

#### 2.3 docs/PROJECT_CARDS.md and docs/PROJECT_FLOW_VISUAL.md
**Focus Areas**:
- Update all visual flows to show CLI installation
- Remove GUI wizard cards/flows
- Simplify user journey to CLI prompts
- Update any architecture diagrams

### TASK 3: Clean Up Deprecated Documentation

**Files to Remove or Archive**:
```
# GUI-specific docs to remove:
- Any setup_gui*.md files
- GUI development guides
- PyQt6 or tkinter references

# Enterprise features to remove:
- SSO/LDAP integration guides
- Multi-database migration guides
- Complex RBAC documentation

# Outdated installation docs:
- docs/installer_ux_redesign_plan.md (if GUI-focused)
- docs/gui_parallel_installer_integration.md
- docs/gui_profile_enhancement_summary.md
```

### TASK 4: Global Search and Replace

**Required Replacements**:
```
"GUI installer" → "CLI installer"
"installation wizard" → "installation command"
"graphical installer" → "command-line installer"
"SQLite/MySQL/PostgreSQL" → "PostgreSQL 18"
"SQLite, MySQL, or PostgreSQL" → "PostgreSQL 18"
"Developer/Team/Enterprise" → "Localhost/Server"
"three profiles" → "two modes"
"bootstrap.py" → "install.py" (when referring to installation)
"setup_gui.py" → "install.py"
"PyQt6" → [remove entire reference]
"tkinter" → [remove entire reference]
```

### TASK 5: Configuration Examples Update

**All configuration examples must show**:
```yaml
# Localhost mode
mode: localhost
database:
  type: postgresql  # Only option
  host: localhost
  port: 5432

# Server mode
mode: server
database:
  type: postgresql  # Only option
  host: localhost
  port: 5432
security:
  api_keys: true
  ssl: true  # Optional but recommended
```

## VALIDATION CHECKLIST

After completing updates, ensure:
- [ ] No GUI installer references remain
- [ ] PostgreSQL 18 is the only database mentioned
- [ ] Only two modes documented (localhost/server)
- [ ] All code examples use `python install.py`
- [ ] Configuration examples match new schema
- [ ] No enterprise features presented as current
- [ ] Fallback scripts documented for elevation
- [ ] Installation time estimates are realistic (5min/10min)

## COORDINATION PROTOCOL

1. **Start with README.md** - This is the highest priority
2. **Report progress** after completing each major file
3. **Flag any issues** where documentation doesn't match reality
4. **Ask for clarification** if anything is unclear
5. **Track changes** in a summary document

## IMPORTANT NOTES

- We are working IN PARALLEL with implementation team
- Document the PLANNED architecture even if not fully implemented
- If you find code that contradicts documentation, document the INTENDED behavior and note the discrepancy
- Focus on user-facing documentation first
- Internal development docs can be updated later

## FILES REFERENCE

Key documentation files identified:
- Root: README.md, INSTALL.md, INSTALLATION.md, CLAUDE.md, requirements.txt
- Technical: docs/TECHNICAL_ARCHITECTURE.md, docs/ARCHITECTURE_V2.md
- Project: docs/PROJECT_ORCHESTRATION_PLAN.md, docs/PROJECT_CARDS.md
- Install: docs/install_project/*.md (these are already aligned - use as reference)

## SUCCESS CRITERIA

Your work is complete when:
1. A new user can install using ONLY the updated documentation
2. No confusion exists about GUI vs CLI
3. PostgreSQL 18 is consistently presented as the only option
4. The two modes (localhost/server) are clearly explained
5. All examples work with the actual CLI installer

## BEGIN WITH

Start with **README.md** as it's the first thing users see. Make it perfect, then move to INSTALL.md, then requirements.txt, then CLAUDE.md, then technical docs.

---

**Note**: The documentation in `docs/install_project/` is already aligned with the new architecture and can be used as a reference for how things should be described.

Good luck! Report back after updating README.md for review.