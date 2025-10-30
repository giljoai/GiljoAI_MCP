# Agent Export Auto-Spawn Removal - Technical Note

## Issue
The orchestrator currently **auto-exports** agent templates to `.claude/agents/` during `_spawn_claude_code_agent()` calls. This behavior is **not desired** and should be removed.

## Current Behavior (WRONG)
**File**: `src/giljo_mcp/orchestrator.py`
**Method**: `_spawn_claude_code_agent()` (lines 184-290)
**Lines to Remove**: 216-258

The orchestrator currently:
1. Creates `.claude/agents/` directory
2. Exports template to `.claude/agents/<name>.md`
3. Overwrites existing files WITHOUT backup
4. Does this for EVERY spawned agent

## Desired Behavior (CORRECT)
Agent export should be **manual only** via:
- **Location**: My Settings → Integrations tab
- **UI Component**: `frontend/src/components/ClaudeCodeExport.vue`
- **API Endpoint**: `api/endpoints/claude_export.py`
- **User Control**: User decides when to export
- **Backup Protection**: Creates `.old.YYYYMMDD_HHMMSS` backups

## Code Changes Needed

### 1. Remove Auto-Export from Orchestrator
**File**: `src/giljo_mcp/orchestrator.py`

**Remove lines 216-258**:
```python
# 1. Auto-export template to .claude/agents/<role>.md
export_dir = Path.cwd() / ".claude" / "agents"
export_dir.mkdir(parents=True, exist_ok=True)

filename = f"{template.name}.md"
file_path = export_dir / filename

# Simple template export (inline implementation)
try:
    # [... export code ...]
    file_path.write_text(full_content, encoding="utf-8")
    logger.info(f"[_spawn_claude_code_agent] Exported template: {template.name} to {file_path}")
except Exception as e:
    logger.exception(f"[_spawn_claude_code_agent] Failed to export template {template.name}: {e}")
    # Continue without export - not critical
```

**Update docstring** (lines 192-215):
Remove references to "auto-export" and step 1 in the process.

### 2. Update Tests
**File**: `tests/test_orchestrator_routing.py`

**Remove or update**:
- `test_spawn_claude_code_agent_exports_template`
- `test_spawn_claude_code_agent_handles_export_failure`

These tests validate the auto-export behavior that we're removing.

### 3. Add Context Budget Warning to UI
**File**: `frontend/src/components/ClaudeCodeExport.vue`

**Add warning** near export button:
```vue
<v-alert type="warning" variant="tonal" density="compact">
  <strong>Recommended Limit:</strong> Export no more than 8 agents maximum.
  Each agent description consumes context budget, reducing available tokens
  for your project. Claude Code recommends 6-8 agents for optimal performance.
</v-alert>
```

### 4. Validate Agent Count on Export
**File**: `api/endpoints/claude_export.py`

**Add validation** in export endpoint:
```python
# Get active templates count
active_count = len([t for t in templates if t.is_active])

if active_count > 8:
    logger.warning(
        f"User exporting {active_count} agents (exceeds recommended limit of 8). "
        f"tenant={tenant_key}"
    )
    # Optional: Return warning in response
```

## Rationale

1. **User Control**: Users should decide when to export, not have it forced during workflows
2. **Safety**: Auto-export overwrites files without backup (dangerous for custom agents)
3. **Context Budget**: Users need awareness of agent count impact on Claude Code performance
4. **Simplicity**: Export is a setup task, not a runtime operation

## Testing Checklist

- [ ] Remove auto-export code from orchestrator
- [ ] Verify orchestrator still spawns agents correctly (no export dependency)
- [ ] Test manual export via My Settings → Integrations
- [ ] Verify backup creation works (.old.YYYYMMDD_HHMMSS)
- [ ] Add UI warning about 8-agent limit
- [ ] Update/remove related tests
- [ ] Test with existing custom agents in `.claude/agents/` (shouldn't be touched)

## Documentation Updates

- [x] Updated `Simple_Vision.md` to reflect manual-only export
- [ ] Update any API documentation mentioning auto-export
- [ ] Update handovers if they reference auto-export behavior
- [ ] Update CLAUDE.md if it mentions auto-export

---

**Priority**: Medium
**Estimated Effort**: 2-3 hours (code removal + test updates + UI warning)
**Related Handovers**: 0069 (MCP Integration)
