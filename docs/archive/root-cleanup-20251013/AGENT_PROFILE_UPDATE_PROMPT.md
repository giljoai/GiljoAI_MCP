# Agent Profile Architecture Update Mission

## Objective
Update all agent profiles in `.claude/agents/` to align with GiljoAI MCP v3.0 architecture while maintaining their professional expertise and critical thinking abilities.

## Critical Architectural Changes (v3.0)

### 1. Database Architecture - NO ALEMBIC
**OLD (WRONG)**: References to Alembic migrations, `alembic revision`, `alembic upgrade`
**NEW (CORRECT)**: Direct table creation via `DatabaseManager.create_tables_async()`

```python
# How the project ACTUALLY works:
# In install.py (~line 450):
await db_manager.create_tables_async()

# In api/app.py (line 186):
await state.db_manager.create_tables_async()

# In database.py:
async def create_tables_async(self):
    async with self.async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
```

**Schema Changes**: Modify `src/giljo_mcp/models.py`, then drop/recreate DB (dev) or manual ALTER (prod)

### 2. Installer Architecture - Root install.py ONLY
**OLD (WRONG)**: References to `installer/cli/install.py`, `installer/core/config.py`
**NEW (CORRECT)**: Root `install.py` is the ONLY installer

```bash
# Correct command:
python install.py

# DEPRECATED (don't reference):
python installer/cli/install.py  # NO LONGER USED
```

### 3. v3.0 Unified Authentication - ONE FLOW
**OLD (WRONG)**: Deployment modes (LOCAL/LAN/WAN), localhost auto-login, mode-based conditional binding
**NEW (CORRECT)**: Single unified architecture

```yaml
# v3.0 Architecture:
- Application ALWAYS binds to 0.0.0.0 (all interfaces)
- OS firewall controls access (defense in depth)
- Authentication ALWAYS enabled (no bypass)
- ONE authentication flow for localhost, LAN, WAN
- Default credentials: admin/admin with FORCED password change
- Database ALWAYS on localhost (never exposed to network)
```

### 4. Configuration Management
**Location**: `config.yaml` at project root (gitignored, system-specific)
**Generation**: Within root `install.py` (not separate installer modules)

## Agent Profile Update Guidelines

### What to Update

1. **Remove ALL references to**:
   - Alembic migrations (`alembic revision`, `alembic upgrade`, migration files)
   - `installer/cli/install.py` or `installer/core/` modules
   - Deployment modes (LOCAL/LAN/WAN as distinct code paths)
   - Localhost auto-login or IP-based authentication bypass

2. **Replace with correct v3.0 information**:
   - Database: "Direct table creation via `DatabaseManager.create_tables_async()`"
   - Installer: "Root `install.py` using same table creation as api/app.py:186"
   - Architecture: "v3.0 unified - binds 0.0.0.0, firewall controls access, ONE auth flow"
   - Schema changes: "Update models.py, then drop/recreate (dev) or ALTER TABLE (prod)"

3. **Example descriptions to fix**:
   ```markdown
   # WRONG:
   "I'll use the database-expert agent to create the Alembic migration"

   # CORRECT:
   "I'll use the database-expert agent to update the schema in models.py"
   ```

### What NOT to Change

**CRITICAL**: Preserve the agent's professional judgment and code verification abilities:

1. **Keep professional skepticism**: Agents MUST be able to read actual code and verify their context
2. **Maintain "Explore → Plan → Confirm → Commit" workflow**: This ensures agents check reality before acting
3. **Preserve code review capabilities**: Agents should ALWAYS verify by reading source when uncertain
4. **Keep domain expertise intact**: Database expert still knows PostgreSQL, architect still understands system design
5. **Don't overshadow with context**: Architecture facts are GUIDELINES, not absolute truth - agents should verify

**Good pattern to maintain**:
```markdown
### STEP 1: EXPLORE
- Review existing source code in src/giljo_mcp/, api/, frontend/
- Verify current implementation patterns
- Check actual database creation method in database.py
- Trace how tables are actually created (don't assume)
```

**Bad pattern to avoid**:
```markdown
# Don't make agents blindly trust context:
"Always use Alembic migrations" ❌
"The installer is installer/cli/install.py" ❌

# Instead, teach them to verify:
"Check how the project creates tables - look at database.py and api/app.py" ✓
"Verify the installer location - check which install.py is actually used" ✓
```

## Files to Update

**Agent profiles in `.claude/agents/`**:
- database-expert.md (HIGH PRIORITY - lots of Alembic references)
- system-architect.md (mentions Alembic in line 84)
- orchestrator-coordinator.md (may reference deployment modes)
- backend-integration-tester.md (check for Alembic/installer refs)
- deep-researcher.md (check for outdated architecture)
- documentation-manager.md (check for installer refs)
- frontend-tester.md (check for deployment mode refs)
- network-security-engineer.md (check for deployment mode refs)
- version-manager.md (check for installer/migration refs)
- tdd-implementor.md (check for database refs)
- ux-designer.md (likely clean, but verify)

## Update Process

For each agent profile:

1. **Read the entire profile** - Understand the agent's role and expertise
2. **Search for outdated patterns**:
   - `grep -i "alembic\|migration\|installer/cli\|deployment.*mode\|localhost.*auto" filename.md`
3. **Update architecture facts** while preserving agent personality and workflow
4. **Add verification reminders** where agents should check actual code
5. **Test mentally**: Would this agent catch if we reverted to Alembic? (They should!)

## Example Fix

**BEFORE (database-expert.md)**:
```markdown
### STEP 4: COMMIT
Implement the database changes:
- Create Alembic migration file
- Test migration thoroughly (both upgrade and downgrade)
- Update SQLAlchemy ORM models
```

**AFTER (database-expert.md)**:
```markdown
### STEP 4: COMMIT
Implement the database changes:
- **Update SQLAlchemy ORM models in src/giljo_mcp/models.py**
- **Tables auto-created via DatabaseManager.create_tables_async()** on API startup
- **Verify by checking**: `api/app.py:186` and `database.py:create_tables_async()`
- For existing databases: Document migration steps in comments
- **Test with fresh database**: `psql -U postgres -c "DROP DATABASE IF EXISTS giljo_mcp;" && python install.py`
```

**Key change**: Removed Alembic, added verification step, maintained professional workflow

## Success Criteria

✅ All agent profiles reference correct v3.0 architecture
✅ No mentions of Alembic, installer/cli, or deployment modes
✅ Agents maintain "Explore" phase with code verification
✅ Agents preserve professional skepticism and code review abilities
✅ Architecture context is a guide, not gospel - agents verify when uncertain
✅ Each agent's domain expertise and personality preserved

## Quality Check

After updates, verify:
- [ ] Can agents still catch architectural mistakes? (Yes - they verify code)
- [ ] Do agents blindly trust their context? (No - they explore and confirm)
- [ ] Is v3.0 architecture correctly documented? (Yes - no Alembic, unified auth, root installer)
- [ ] Are agent workflows intact? (Yes - Explore → Plan → Confirm → Commit)
- [ ] Do agents know HOW to verify? (Yes - "Check database.py", "Read api/app.py:186")

---

**Remember**: These agents are professionals who read code and verify their understanding. Update their reference material, but don't turn them into parrots. They should be BETTER equipped to catch mistakes BECAUSE they know where to look for truth.
