# Agent Handoff Prompt - GiljoAI MCP v3.0 Consolidation

## Quick Start for Fresh Agents

Copy and paste this prompt when starting work in a new context window:

---

# GiljoAI MCP v3.0 Consolidation - Agent Task Assignment

## Context

We are consolidating the GiljoAI MCP codebase from a three-mode architecture (LOCAL/LAN/WAN) to a unified single-product architecture. The goal is to remove 87% code duplication, simplify the user experience, and improve maintainability.

**Backup Branch:** `retired_multi_network_architecture` (already created)
**Target Release:** v3.0
**Project Plan:** `docs/SINGLEPRODUCT_RECALIBRATION.md` (read this first)

## Your Mission

You are being assigned to work on the **GiljoAI MCP v3.0 consolidation project**. Read the full plan in `docs/SINGLEPRODUCT_RECALIBRATION.md` to understand the overall strategy.

### Available Phases

**Phase 1: Core Architecture Consolidation (Week 1-2)**
- Remove DeploymentMode enum
- Implement auto-login for localhost clients (IP-based detection)
- Consolidate authentication middleware
- Update configuration system (remove mode, add feature flags)
- Migrate database schema (add system_user flag)
- Update installer (remove mode selection, add firewall config)

**Phase 2: MCP Integration System (Week 2-3)**
- Implement script generator API endpoints
- Create Windows .bat and Unix .sh templates with auto-detection
- Build frontend admin MCP settings UI
- Add secure share link generation (token-based)
- Create email templates for team distribution

**Phase 3: Testing & Validation (Week 3)**
- Write unit tests for auto-login middleware
- Write integration tests for full authentication flow
- Test on Windows 10/11, macOS 12+, Ubuntu 22.04+
- Test tool detection (Claude Code, Cursor, Windsurf)
- Validate migration script (v2.x → v3.0)

**Phase 4: Documentation & Release (Week 4)**
- Write migration guide (v2.x → v3.0 breaking changes)
- Write MCP integration user guide
- Write admin setup guide (script distribution)
- Write firewall configuration guide (OS-specific)
- Prepare release notes and changelog

## Instructions for Specialized Agents

When working on this project, **use specialized agents** via the Task tool:

1. **system-architect**: For architecture decisions, component dependencies, code reviews
2. **database-expert**: For database schema changes, migrations, query optimization
3. **tdd-implementor**: For implementing features following TDD workflow
4. **backend-integration-tester**: For testing API endpoints and backend logic
5. **frontend-tester**: For testing UI components and user workflows
6. **documentation-manager**: For writing docs, guides, and release notes

## Getting Started

1. **Read the full plan:**
   ```bash
   Read: docs/SINGLEPRODUCT_RECALIBRATION.md
   ```

2. **Understand the current architecture:**
   - 3 modes: LOCAL (localhost), LAN (network), WAN (internet)
   - 87% code duplication between modes
   - Multi-tenant infrastructure bleeds into LOCAL mode (unused)
   - Goal: Consolidate to single product with firewall-based network control

3. **Understand the target architecture:**
   - Single codebase, no mode enum
   - Auto-login for 127.0.0.1 clients (preserves localhost UX)
   - JWT + API keys for network clients
   - OS firewall controls network access (not app binding)
   - MCP integration via downloadable scripts (all platforms)

4. **Check current state:**
   ```bash
   git branch  # Should show retired_multi_network_architecture exists
   git status  # Should be on master branch
   ```

5. **Announce your focus:**
   ```
   I've read docs/SINGLEPRODUCT_RECALIBRATION.md and understand the consolidation goals.

   I'm working on: [Phase X - Phase Name]

   Starting with: [specific task from phase]
   ```

## Key Implementation Details

### Phase 1 Highlights

**Auto-Login Middleware:**
```python
# api/middleware/auto_login.py
if request.client.host in ("127.0.0.1", "::1"):
    request.state.user = await get_or_create_localhost_user()
    request.state.authenticated = True
else:
    await validate_jwt_or_api_key(request)
```

**Remove DeploymentMode Enum:**
```python
# BEFORE: src/giljo_mcp/config_manager.py
class DeploymentMode(Enum):
    LOCAL = "local"
    LAN = "lan"
    WAN = "wan"

# AFTER: Remove enum, use feature flags
@dataclass
class ServerConfig:
    authentication_enabled: bool = True
    network_binding: str = "0.0.0.0"
```

**Config Migration:**
```yaml
# BEFORE (v2.x)
installation:
  mode: local

# AFTER (v3.0)
installation:
  version: 3.0.0
  deployment_context: localhost  # Descriptive only

features:
  authentication: true
  auto_login_localhost: true
```

### Phase 2 Highlights

**Script Generator API:**
```python
# api/endpoints/mcp_installer.py
@router.get("/api/mcp-installer/windows")
async def download_windows_installer(user: User = Depends(get_current_user)):
    # Generate .bat with embedded server URL + API key
    return Response(content=script, media_type="application/bat")

@router.post("/api/mcp-installer/share-link")
async def generate_share_link(user: User = Depends(get_current_user)):
    # Generate 7-day token for email distribution
    return {"windows_url": "...", "unix_url": "..."}
```

**Script Template Features:**
- Auto-detect Claude Code, Cursor, Windsurf
- Backup existing configs before modification
- Use PowerShell (Windows) / jq/Python (Unix) for safe JSON merging
- Show success summary with configured tools

## Testing Requirements

All code must have tests:

- **Unit tests:** Auto-login logic, config migration, script generation
- **Integration tests:** Full auth flow, localhost vs network access
- **Cross-platform tests:** Windows 10/11, macOS 12+, Ubuntu 22.04+
- **Tool detection tests:** Claude Code, Cursor, Windsurf paths

## Success Criteria

Your work is complete when:

- [ ] All code changes implemented per plan
- [ ] All tests written and passing (≥90% coverage)
- [ ] Documentation updated (if applicable)
- [ ] Code reviewed by system-architect agent
- [ ] No breaking changes without migration path
- [ ] Backward compatibility validated (v2.x → v3.0)

## Migration Safety

**Critical:** Ensure existing users can upgrade safely:

1. **Create migration script:** `scripts/migrate_config_v3.py`
2. **Test migration:** On real v2.x configs (LOCAL, LAN, WAN)
3. **Preserve data:** Database contents must survive upgrade
4. **Document breaking changes:** In docs/MIGRATION_GUIDE_V3.md
5. **Provide rollback:** Instructions to revert to v2.x if needed

## Common Pitfalls

1. **Don't break localhost UX:** Auto-login must be seamless (0-click)
2. **Don't skip tests:** Every feature needs unit + integration tests
3. **Don't ignore cross-platform:** Test on Windows, macOS, Linux
4. **Don't hardcode paths:** Use pathlib and OS detection
5. **Don't forget docs:** Update all affected documentation

## Questions?

If you encounter ambiguity:

1. **Check the full plan:** `docs/SINGLEPRODUCT_RECALIBRATION.md`
2. **Review session memories:** `docs/sessions/` for context
3. **Consult system-architect:** Launch agent for architectural guidance
4. **Ask the user:** If genuinely unclear, ask for clarification

## Progress Tracking

Use TodoWrite to track your work:

```python
# Example todo list
todos = [
    {"content": "Read SINGLEPRODUCT_RECALIBRATION.md", "status": "completed"},
    {"content": "Implement auto-login middleware", "status": "in_progress"},
    {"content": "Write unit tests for auto-login", "status": "pending"},
    {"content": "Update config migration script", "status": "pending"}
]
```

## Let's Build!

This consolidation will:

✅ Remove 500+ lines of duplicate code
✅ Simplify user experience (no mode confusion)
✅ Improve security (firewall + auth layers)
✅ Enable future growth (1 to N users, same code)
✅ Reduce maintenance burden (single test matrix)

**We're making the product better by making the architecture simpler.**

---

**Ready to start? Read `docs/SINGLEPRODUCT_RECALIBRATION.md` and announce your phase!**
