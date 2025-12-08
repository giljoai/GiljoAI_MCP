# Handover 0334d: Staging Prompt Integration - Environment Pre-Flight

**Date:** 2025-12-07
**From Agent:** Documentation Manager
**To Agent:** TDD Implementor
**Parent Handover:** 0334 (Claude Code Plugin - Agent Template Bridge)
**Priority:** High
**Estimated Effort:** 2-3 hours
**Status:** Ready for Implementation

---

## Executive Summary

Update the CLI mode staging prompt in `thin_prompt_generator.py` to include comprehensive environment pre-flight checks before the orchestrator proceeds with project staging. These checks prevent local file conflicts that would interfere with plugin-managed agent templates.

**Expected Outcome:** When orchestrators launch in CLI mode, they perform three critical environment checks (local overrides, plugin installation, agent availability) before proceeding with staging workflow.

---

## Context and Background

### How We Got Here

1. **Handover 0333** simplified the staging prompt from 150+ lines to ~35 lines
2. We're adding a Claude Code plugin that fetches agent templates dynamically (Handover 0334)
3. **Critical Discovery**: Claude Code has a priority hierarchy for agent resolution:
   - **Project agents** (`.claude/agents/`) - HIGHEST priority, overrides plugin
   - **User agents** (`~/.claude/agents/`) - Overrides plugin
   - **Plugin agents** (from our plugin) - LOWEST priority

4. **Problem**: If users have existing `.md` files in `.claude/agents/` or `~/.claude/agents/`, those files will INTERFERE with our plugin-managed agents
5. **Solution**: The staging prompt must include environment verification before proceeding

### Why Environment Checks Are Critical

Without pre-flight checks, orchestrators might:
- Invoke stale agent definitions from local `.md` files instead of fresh database templates
- Fail to spawn agents if plugin is not installed
- Receive confusing errors when template names don't match expectations
- Operate with inconsistent agent behavior across different users

### What Happens If Checks Are Skipped

**Scenario: Local Override Conflict**
```
User has: ~/.claude/agents/implementer.md (outdated definition)
Plugin has: Fresh "implementer" template from database
Result: Orchestrator invokes outdated local file, ignoring plugin
Impact: Wrong instructions, wrong capabilities, workflow failure
```

**Scenario: Plugin Not Installed**
```
User runs: Task(subagent_type="implementer", ...)
Result: "Agent 'implementer' not found"
Impact: Orchestrator cannot spawn any agents
```

---

## Technical Specification

### File to Modify

**Path:** `F:\GiljoAI_MCP\src\giljo_mcp\thin_prompt_generator.py`

**Method:** `generate_staging_prompt()`

**Current Location:** Lines 1003-1008 (the `if claude_code_mode:` block)

### Current Code (from Handover 0333)

```python
# Mode-specific instructions
if claude_code_mode:
    mode_block = """CLAUDE CODE CLI MODE:
- You will spawn agents using Claude Code's Task tool
- agent_type parameter = subagent_type (MUST match template name exactly)
- Agents are hidden subprocesses - user sees progress via dashboard
- After spawning, agents call get_agent_mission() to start work"""
else:
    mode_block = """MULTI-TERMINAL MODE:
- User will manually copy/paste prompts for each agent
- Each agent has [Copy Prompt] button in the Implementation tab
- Coordinate agents via MCP messaging tools"""
```

### New Code (Environment Pre-Flight)

Replace the CLI mode block with comprehensive environment checks:

```python
# Mode-specific instructions
if claude_code_mode:
    mode_block = """CLAUDE CODE CLI MODE:

ENVIRONMENT PRE-FLIGHT:
Before proceeding, verify your agent environment is clean:

1. CHECK FOR LOCAL OVERRIDES (these will interfere with managed agents):
   Run: ls ~/.claude/agents/*.md 2>/dev/null
   Run: ls .claude/agents/*.md 2>/dev/null

   If any files found: Remove or rename them to use GiljoAI managed agents.
   Local agent files override plugin agents!

2. VERIFY PLUGIN INSTALLED:
   Run: /plugins list
   Look for: giljoai-agents

   If not found: Visit GiljoAI → My Settings → Integrations → Claude Code Setup

3. LIST AVAILABLE AGENTS:
   Run: /agents

   Should show your GiljoAI templates (orchestrator, implementer, tester, etc.)

PROCEED ONLY when:
✓ No local .md overrides exist in ~/.claude/agents/ or .claude/agents/
✓ Plugin is installed (appears in /plugins list)
✓ /agents shows your managed templates

SPAWNING AGENTS:
- Use Task tool with subagent_type matching agent name from /agents exactly
- Example: Task(subagent_type="implementer", prompt="Build the auth module")
- Agents receive their full instructions automatically from the plugin
- After spawning, agents call get_agent_mission() to start work"""
else:
    mode_block = """MULTI-TERMINAL MODE:
- User will manually copy/paste prompts for each agent
- Each agent has [Copy Prompt] button in the Implementation tab
- Coordinate agents via MCP messaging tools"""
```

### Changes Summary

| Element | Before | After |
|---------|--------|-------|
| Line count | 4 lines | ~30 lines |
| Token estimate | ~50 tokens | ~250 tokens |
| Checks included | None | 3 checks (overrides, plugin, agents) |
| Proceed conditions | Implicit | Explicit checklist |
| User guidance | Minimal | Detailed with fallback instructions |

---

## Cross-Platform Considerations

### Shell Command Compatibility

The pre-flight checks use bash syntax:
```bash
ls ~/.claude/agents/*.md 2>/dev/null
ls .claude/agents/*.md 2>/dev/null
```

**Platform Support:**
- **Works on**: macOS, Linux, WSL (Windows Subsystem for Linux)
- **May not work on**: Windows native PowerShell, cmd.exe
- **Claude Code default**: Usually runs in bash-compatible shell

### Fallback: Manual Verification Instructions

If shell commands fail, orchestrator should see the intent from the instructions:
1. Check for local agent files in user and project directories
2. Verify plugin is installed
3. Confirm agents are available

The orchestrator can then guide the user to manually verify these conditions.

### Alternative PowerShell Commands (Reference Only)

If targeting Windows PowerShell specifically (future enhancement):
```powershell
# Check user agents
Get-ChildItem -Path "$env:USERPROFILE\.claude\agents\*.md" -ErrorAction SilentlyContinue

# Check project agents
Get-ChildItem -Path ".\.claude\agents\*.md" -ErrorAction SilentlyContinue
```

**Current Decision:** Use bash syntax as primary (Claude Code standard), document limitation.

---

## Implementation Details

### Complete Code Replacement

**File:** `F:\GiljoAI_MCP\src\giljo_mcp\thin_prompt_generator.py`

**Method:** `generate_staging_prompt()` (lines 965-1048)

**Target Section:** Lines 1002-1013 (mode-specific instructions block)

**Before:**
```python
        # Mode-specific instructions
        if claude_code_mode:
            mode_block = """CLAUDE CODE CLI MODE:
- You will spawn agents using Claude Code's Task tool
- agent_type parameter = subagent_type (MUST match template name exactly)
- Agents are hidden subprocesses - user sees progress via dashboard
- After spawning, agents call get_agent_mission() to start work"""
        else:
            mode_block = """MULTI-TERMINAL MODE:
- User will manually copy/paste prompts for each agent
- Each agent has [Copy Prompt] button in the Implementation tab
- Coordinate agents via MCP messaging tools"""
```

**After:**
```python
        # Mode-specific instructions
        if claude_code_mode:
            mode_block = """CLAUDE CODE CLI MODE:

ENVIRONMENT PRE-FLIGHT:
Before proceeding, verify your agent environment is clean:

1. CHECK FOR LOCAL OVERRIDES (these will interfere with managed agents):
   Run: ls ~/.claude/agents/*.md 2>/dev/null
   Run: ls .claude/agents/*.md 2>/dev/null

   If any files found: Remove or rename them to use GiljoAI managed agents.
   Local agent files override plugin agents!

2. VERIFY PLUGIN INSTALLED:
   Run: /plugins list
   Look for: giljoai-agents

   If not found: Visit GiljoAI → My Settings → Integrations → Claude Code Setup

3. LIST AVAILABLE AGENTS:
   Run: /agents

   Should show your GiljoAI templates (orchestrator, implementer, tester, etc.)

PROCEED ONLY when:
✓ No local .md overrides exist in ~/.claude/agents/ or .claude/agents/
✓ Plugin is installed (appears in /plugins list)
✓ /agents shows your managed templates

SPAWNING AGENTS:
- Use Task tool with subagent_type matching agent name from /agents exactly
- Example: Task(subagent_type="implementer", prompt="Build the auth module")
- Agents receive their full instructions automatically from the plugin
- After spawning, agents call get_agent_mission() to start work"""
        else:
            mode_block = """MULTI-TERMINAL MODE:
- User will manually copy/paste prompts for each agent
- Each agent has [Copy Prompt] button in the Implementation tab
- Coordinate agents via MCP messaging tools"""
```

### No Other Changes Required

- The multi-terminal mode block remains unchanged
- The prompt assembly logic (lines 1015-1048) remains unchanged
- No new methods or imports required
- No database schema changes

---

## TDD Test Requirements

### Test File

**Path:** `F:\GiljoAI_MCP\tests\unit\test_staging_prompt.py`

**Action:** Add new test cases to existing file (do not create new file)

### Test Cases to Add

#### Test 1: CLI Mode Includes Environment Pre-Flight

```python
@pytest.mark.asyncio
async def test_cli_mode_includes_environment_preflight(prompt_generator, mock_project, mock_product):
    """Verify CLI mode prompt includes ENVIRONMENT PRE-FLIGHT section."""
    with patch.object(prompt_generator, '_fetch_project', return_value=mock_project), \
         patch.object(prompt_generator, '_fetch_product', return_value=mock_product):

        prompt = await prompt_generator.generate_staging_prompt(
            orchestrator_id=str(uuid4()),
            project_id=mock_project.id,
            claude_code_mode=True
        )

        assert "ENVIRONMENT PRE-FLIGHT" in prompt, \
            "CLI mode must include ENVIRONMENT PRE-FLIGHT section"
```

#### Test 2: CLI Mode Includes Local Override Check

```python
@pytest.mark.asyncio
async def test_cli_mode_includes_local_override_check(prompt_generator, mock_project, mock_product):
    """Verify CLI mode prompt includes local override check instructions."""
    with patch.object(prompt_generator, '_fetch_project', return_value=mock_project), \
         patch.object(prompt_generator, '_fetch_product', return_value=mock_product):

        prompt = await prompt_generator.generate_staging_prompt(
            orchestrator_id=str(uuid4()),
            project_id=mock_project.id,
            claude_code_mode=True
        )

        assert "CHECK FOR LOCAL OVERRIDES" in prompt, \
            "CLI mode must include local override check"
        assert "~/.claude/agents/" in prompt, \
            "CLI mode must check user agents directory"
        assert ".claude/agents/" in prompt, \
            "CLI mode must check project agents directory"
```

#### Test 3: CLI Mode Includes Plugin Verification

```python
@pytest.mark.asyncio
async def test_cli_mode_includes_plugin_verification(prompt_generator, mock_project, mock_product):
    """Verify CLI mode prompt includes plugin verification instructions."""
    with patch.object(prompt_generator, '_fetch_project', return_value=mock_project), \
         patch.object(prompt_generator, '_fetch_product', return_value=mock_product):

        prompt = await prompt_generator.generate_staging_prompt(
            orchestrator_id=str(uuid4()),
            project_id=mock_project.id,
            claude_code_mode=True
        )

        assert "VERIFY PLUGIN INSTALLED" in prompt, \
            "CLI mode must include plugin verification"
        assert "/plugins list" in prompt, \
            "CLI mode must instruct to check /plugins list"
        assert "giljoai-agents" in prompt, \
            "CLI mode must reference giljoai-agents plugin name"
```

#### Test 4: CLI Mode Includes Agent List Check

```python
@pytest.mark.asyncio
async def test_cli_mode_includes_agent_list_check(prompt_generator, mock_project, mock_product):
    """Verify CLI mode prompt includes agent list check instructions."""
    with patch.object(prompt_generator, '_fetch_project', return_value=mock_project), \
         patch.object(prompt_generator, '_fetch_product', return_value=mock_product):

        prompt = await prompt_generator.generate_staging_prompt(
            orchestrator_id=str(uuid4()),
            project_id=mock_project.id,
            claude_code_mode=True
        )

        assert "LIST AVAILABLE AGENTS" in prompt, \
            "CLI mode must include agent list check"
        assert "/agents" in prompt, \
            "CLI mode must instruct to check /agents"
```

#### Test 5: CLI Mode Includes Proceed Conditions

```python
@pytest.mark.asyncio
async def test_cli_mode_includes_proceed_conditions(prompt_generator, mock_project, mock_product):
    """Verify CLI mode prompt includes explicit proceed conditions."""
    with patch.object(prompt_generator, '_fetch_project', return_value=mock_project), \
         patch.object(prompt_generator, '_fetch_product', return_value=mock_product):

        prompt = await prompt_generator.generate_staging_prompt(
            orchestrator_id=str(uuid4()),
            project_id=mock_project.id,
            claude_code_mode=True
        )

        assert "PROCEED ONLY" in prompt, \
            "CLI mode must include explicit proceed conditions"
        # Check for checklist indicators
        assert "✓" in prompt or "- [ ]" in prompt, \
            "CLI mode should include checklist indicators"
```

#### Test 6: Multi-Terminal Mode Unchanged

```python
@pytest.mark.asyncio
async def test_multi_terminal_mode_unchanged(prompt_generator, mock_project, mock_product):
    """Verify multi-terminal mode does NOT include environment pre-flight checks."""
    with patch.object(prompt_generator, '_fetch_project', return_value=mock_project), \
         patch.object(prompt_generator, '_fetch_product', return_value=mock_product):

        prompt = await prompt_generator.generate_staging_prompt(
            orchestrator_id=str(uuid4()),
            project_id=mock_project.id,
            claude_code_mode=False
        )

        assert "ENVIRONMENT PRE-FLIGHT" not in prompt, \
            "Multi-terminal mode should NOT include environment pre-flight"
        assert "MULTI-TERMINAL MODE" in prompt, \
            "Multi-terminal mode should include its own mode block"
```

#### Test 7: Prompt Length Reasonable

```python
@pytest.mark.asyncio
async def test_cli_mode_prompt_length_reasonable(prompt_generator, mock_project, mock_product):
    """Verify CLI mode prompt is reasonable length (~80-120 lines)."""
    with patch.object(prompt_generator, '_fetch_project', return_value=mock_project), \
         patch.object(prompt_generator, '_fetch_product', return_value=mock_product):

        prompt = await prompt_generator.generate_staging_prompt(
            orchestrator_id=str(uuid4()),
            project_id=mock_project.id,
            claude_code_mode=True
        )

        line_count = len(prompt.split('\n'))

        # Target: ~80-120 lines (with pre-flight checks)
        assert line_count >= 60, \
            f"Prompt too short: {line_count} lines (expected 80-120)"
        assert line_count <= 150, \
            f"Prompt too long: {line_count} lines (expected 80-120)"
```

### Running Tests

```bash
# Run all staging prompt tests
pytest tests/unit/test_staging_prompt.py -v

# Run specific test class
pytest tests/unit/test_staging_prompt.py::TestEnvironmentPreFlight -v

# Run with coverage
pytest tests/unit/test_staging_prompt.py --cov=src.giljo_mcp.thin_prompt_generator --cov-report=term-missing
```

---

## User Experience Flow

### Happy Path: Clean Environment

**Step 1: Orchestrator Starts**
```
I am Orchestrator for GiljoAI Project "Auth Module".

IDENTITY:
- Orchestrator ID: orch-abc123
- Project ID: proj-xyz789
- Tenant Key: tk_user123
- Execution Mode: Claude Code CLI

STARTUP SEQUENCE:
1. Verify MCP: health_check()
   ✓ MCP server running at http://192.168.1.100:7272
...
```

**Step 2: Environment Pre-Flight**
```
Orchestrator: Running environment pre-flight checks...

1. Checking for local agent overrides:
   $ ls ~/.claude/agents/*.md 2>/dev/null
   (no output - clean)

   $ ls .claude/agents/*.md 2>/dev/null
   (no output - clean)

   ✓ No local overrides found

2. Verifying plugin installation:
   $ /plugins list
   giljoai-agents v1.0.0

   ✓ Plugin installed

3. Listing available agents:
   $ /agents
   - orchestrator: Project Orchestrator
   - implementer: Code Implementation Specialist
   - tester: Testing Specialist
   - architect: System Architect

   ✓ Agents available

All pre-flight checks passed. Proceeding with staging...
```

**Step 3: Staging Proceeds Normally**
```
Orchestrator: Fetching project context...
Orchestrator: Creating mission plan...
Orchestrator: Spawning agents:
  - Implementer (job_id: job-123)
  - Tester (job_id: job-456)
Staging complete.
```

### Unhappy Path: Local Override Detected

**Step 1: Orchestrator Starts**
```
(Same as happy path)
```

**Step 2: Environment Pre-Flight Fails**
```
Orchestrator: Running environment pre-flight checks...

1. Checking for local agent overrides:
   $ ls ~/.claude/agents/*.md 2>/dev/null
   ~/.claude/agents/implementer.md
   ~/.claude/agents/tester.md

   ⚠️ WARNING: Local agent files found!

   These files will OVERRIDE the plugin-managed agents.
   You must remove or rename them to use GiljoAI managed templates.

   Files detected:
   - ~/.claude/agents/implementer.md
   - ~/.claude/agents/tester.md

   Action required: Move these files or rename them (e.g., implementer.md.backup)
   Then restart staging.
```

**Step 3: User Resolves Conflict**
```
User: $ mv ~/.claude/agents/implementer.md ~/.claude/agents/implementer.md.backup
User: $ mv ~/.claude/agents/tester.md ~/.claude/agents/tester.md.backup
User: (pastes staging prompt again)
```

**Step 4: Staging Proceeds After Resolution**
```
Orchestrator: Running environment pre-flight checks...
   ✓ No local overrides found
   ✓ Plugin installed
   ✓ Agents available
Proceeding with staging...
```

### Unhappy Path: Plugin Not Installed

**Step 1: Orchestrator Starts**
```
(Same as happy path)
```

**Step 2: Environment Pre-Flight Fails**
```
Orchestrator: Running environment pre-flight checks...

1. Checking for local agent overrides:
   ✓ No local overrides found

2. Verifying plugin installation:
   $ /plugins list
   (no giljoai-agents plugin found)

   ⚠️ ERROR: Plugin not installed!

   The giljoai-agents plugin is required for CLI mode.

   Installation steps:
   1. Visit: GiljoAI → My Settings → Integrations → Claude Code Setup
   2. Copy the install command (includes your tenant key)
   3. Run the command in this terminal
   4. Verify with: /plugins list
   5. Restart staging

   Cannot proceed without plugin installation.
```

**Step 3: User Installs Plugin**
```
User: (visits setup page)
User: (copies install command)
User: $ /plugin install giljoai-agents --config server_url=http://192.168.1.100:7272 --config tenant_key=tk_user123
User: (pastes staging prompt again)
```

**Step 4: Staging Proceeds After Installation**
```
Orchestrator: Running environment pre-flight checks...
   ✓ No local overrides found
   ✓ Plugin installed
   ✓ Agents available
Proceeding with staging...
```

---

## Success Criteria Checklist

Implementation is complete when:

- [ ] CLI mode staging prompt includes "ENVIRONMENT PRE-FLIGHT" section
- [ ] Local override check instructions are clear and actionable
- [ ] Plugin verification instructions reference `/plugins list` command
- [ ] Agent list check instructions reference `/agents` command
- [ ] Proceed conditions are explicit with checklist format
- [ ] Multi-terminal mode block is unchanged
- [ ] All 7 test cases pass
- [ ] Prompt length is reasonable (80-120 lines)
- [ ] Manual testing confirms orchestrator follows checks
- [ ] Documentation updated if needed

---

## Dependencies

### Depends On (Must Be Complete First)

None - this handover can proceed independently.

### Blocks (Cannot Start Until This Is Done)

- **0334b** (Plugin Package Creation): Plugin verification instructions reference "giljoai-agents" name
- **0334c** (Profile Setup UI): Pre-flight instructions direct users to setup page

### Related Handovers

- **0333**: Staging Prompt Architecture Correction (source of current implementation)
- **0334**: Parent handover (Claude Code Plugin - Agent Template Bridge)
- **0334a**: Backend API endpoint (provides `/api/v1/agent-templates/plugin`)
- **0334e**: Testing & Documentation (will include E2E testing of pre-flight flow)

---

## Files Summary

### Modified Files

**1. `F:\GiljoAI_MCP\src\giljo_mcp\thin_prompt_generator.py`**
- Lines changed: 1003-1008 (replace 6 lines with ~30 lines)
- Method: `generate_staging_prompt()`
- Change type: Expand CLI mode block with environment checks

### Test Files

**2. `F:\GiljoAI_MCP\tests\unit\test_staging_prompt.py`**
- Action: Add 7 new test cases
- Test class: `TestEnvironmentPreFlight` (new class)
- Coverage target: >95% for `generate_staging_prompt()` CLI mode path

### No New Files

This handover modifies existing files only.

---

## Rollback Plan

If environment pre-flight checks cause issues:

1. **Quick Rollback**: Revert `thin_prompt_generator.py` to commit before this change
2. **Database Impact**: None (no schema changes)
3. **Frontend Impact**: None (no UI changes in this handover)
4. **Testing Impact**: Remove added test cases from `test_staging_prompt.py`

**Rollback Command:**
```bash
git checkout HEAD~1 -- src/giljo_mcp/thin_prompt_generator.py
git checkout HEAD~1 -- tests/unit/test_staging_prompt.py
```

---

## Implementation Checklist

**Phase 1: Code Changes (30 minutes)**
- [ ] Read `thin_prompt_generator.py` lines 1000-1015
- [ ] Replace CLI mode block (lines 1003-1008) with new environment pre-flight block
- [ ] Verify indentation and formatting match file style
- [ ] Verify multi-terminal mode block unchanged (lines 1010-1013)
- [ ] Save file

**Phase 2: Test Implementation (60 minutes)**
- [ ] Read existing `test_staging_prompt.py` structure
- [ ] Add new test class `TestEnvironmentPreFlight`
- [ ] Implement Test 1: Environment pre-flight section exists
- [ ] Implement Test 2: Local override check present
- [ ] Implement Test 3: Plugin verification present
- [ ] Implement Test 4: Agent list check present
- [ ] Implement Test 5: Proceed conditions present
- [ ] Implement Test 6: Multi-terminal mode unchanged
- [ ] Implement Test 7: Prompt length reasonable
- [ ] Save test file

**Phase 3: Test Execution (15 minutes)**
- [ ] Run: `pytest tests/unit/test_staging_prompt.py -v`
- [ ] Verify all new tests pass
- [ ] Verify existing tests still pass
- [ ] Check coverage: `pytest tests/unit/test_staging_prompt.py --cov=src.giljo_mcp.thin_prompt_generator`
- [ ] Ensure >95% coverage for modified method

**Phase 4: Manual Verification (15 minutes)**
- [ ] Create test project in GiljoAI
- [ ] Click "Stage Project" with CLI mode enabled
- [ ] Copy generated prompt
- [ ] Verify environment pre-flight section present
- [ ] Verify all three checks documented
- [ ] Verify proceed conditions explicit

**Phase 5: Documentation (30 minutes)**
- [ ] Update commit message with handover reference
- [ ] Add inline code comments if needed
- [ ] Update this handover status to "Complete"
- [ ] Create completion summary

**Total Estimated Time:** 2.5 hours

---

## Testing Verification

### Unit Test Coverage

**Target:** >95% for `generate_staging_prompt()` method

**Test Coverage Report:**
```bash
# Run with coverage
pytest tests/unit/test_staging_prompt.py \
  --cov=src.giljo_mcp.thin_prompt_generator \
  --cov-report=term-missing \
  --cov-report=html

# Expected output:
# src/giljo_mcp/thin_prompt_generator.py
#   generate_staging_prompt()    95%   (1003-1050)
```

### Manual Testing Checklist

**Test 1: Happy Path (Clean Environment)**
1. Create test project
2. Enable CLI mode
3. Stage project
4. Copy prompt
5. Verify environment pre-flight section
6. Verify all three checks documented

**Test 2: Local Override Detection**
1. Create `~/.claude/agents/test.md`
2. Stage project
3. Copy prompt
4. Read prompt carefully
5. Verify it instructs to check for local overrides
6. Delete `test.md`

**Test 3: Plugin Reference**
1. Stage project
2. Copy prompt
3. Verify it references `/plugins list`
4. Verify it references "giljoai-agents"

**Test 4: Multi-Terminal Unchanged**
1. Disable CLI mode (use multi-terminal)
2. Stage project
3. Copy prompt
4. Verify NO environment pre-flight section
5. Verify multi-terminal instructions present

---

## Open Questions (None)

All questions resolved during handover planning:

| Question | Resolution |
|----------|------------|
| What shell syntax to use? | **Bash** (Claude Code standard) |
| Include PowerShell alternative? | **No** (document limitation, add later if needed) |
| How detailed should checks be? | **Explicit** with example commands |
| Include proceed conditions? | **Yes** with checklist format |
| Update multi-terminal mode? | **No** (changes only affect CLI mode) |

---

## Related Documentation

### Existing Docs
- `docs/ORCHESTRATOR.md` - Orchestrator workflow documentation
- `docs/components/STAGING_WORKFLOW.md` - Staging workflow details
- `handovers/0333_STAGING_PROMPT_ARCHITECTURE_CORRECTION.md` - Source of current implementation

### New Docs (Future)
- `docs/user_guides/claude_code_plugin_setup.md` (created in 0334e)
- Will reference these pre-flight checks as part of troubleshooting

---

## Completion Criteria

This handover is complete when:

1. Code changes committed and pushed
2. All 7 unit tests passing
3. Manual testing confirms pre-flight checks work
4. Coverage >95% for modified method
5. No regressions in multi-terminal mode
6. This handover document updated to "Status: Complete"

**Definition of Done:**
- CLI mode prompts include environment pre-flight
- Multi-terminal mode prompts unchanged
- Tests verify all three checks present
- Orchestrators can detect and warn about conflicts
- Ready for integration with 0334b (plugin package)

---

## Notes for Implementor

### Key Implementation Tips

1. **Exact Replacement**: Replace only lines 1003-1008, leave everything else unchanged
2. **Indentation**: Match existing 4-space indentation in multiline strings
3. **Triple Quotes**: Use `"""` for multiline strings (existing pattern)
4. **No f-strings**: The mode_block is a plain string (no variable interpolation needed in this block)
5. **Preserve else Block**: Keep the `else:` block for multi-terminal mode exactly as-is

### Common Pitfalls to Avoid

1. **Don't change multi-terminal mode block** - only CLI mode changes
2. **Don't add logic outside the mode_block assignment** - just replace the string
3. **Don't modify the prompt assembly** (lines 1015-1048) - it's correct as-is
4. **Don't add new imports** - none needed for this change
5. **Don't change method signature** - parameters stay the same

### Quick Reference: Line Numbers

```
Line 965: def generate_staging_prompt(...)
Line 988: project = await self._fetch_project(...)
Line 989: product = await self._fetch_product(...)
Line 1000: execution_mode = "Claude Code CLI" if claude_code_mode else "Multi-Terminal"
Line 1002: # Mode-specific instructions
Line 1003: if claude_code_mode:
Line 1004:     mode_block = """..."""  ← REPLACE THIS MULTILINE STRING
Line 1009: else:
Line 1010:     mode_block = """..."""  ← DO NOT CHANGE THIS
Line 1015: prompt = f"""I am Orchestrator..."""
```

### Test-Driven Development Approach

1. **Read tests first** - understand what success looks like
2. **Run tests (they'll fail)** - baseline
3. **Make smallest change** - replace mode_block only
4. **Run tests again** - should pass
5. **Manual verification** - confirm prompt looks right
6. **Done** - commit with handover reference

---

**Handover Status:** Ready for Implementation
**Next Agent:** TDD Implementor
**Estimated Completion:** 2-3 hours from start
