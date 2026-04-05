# 0950g: God-Class Split — ThinClientPromptGenerator

**Series:** 0950 (Pre-Release Quality Sprint — God-Class Splitting Track)
**Phase:** 7 of 14
**Branch:** `feature/0950-pre-release-quality`
**Edition Scope:** CE
**Priority:** High
**Effort:** Heavy (4-6 hrs)
**Depends on:** 0950f (Stale Docstrings + Dead Pass Statements)
**Status:** Not Started

### Reference Documents
- **Chain log:** `prompts/0950_chain/chain_log.json`
- **Project rules:** `CLAUDE.md`, `handovers/HANDOVER_INSTRUCTIONS.md`

---

## Context

`src/giljo_mcp/thin_prompt_generator.py` is 1676 lines. It contains Claude-specific, Codex-specific, and staging-specific prompt building mixed into a single class (`ThinClientPromptGenerator`). This violates the 1000-line class limit and the 200-line function limit. The `_build_claude_code_execution_prompt` method alone is 304 lines.

The split creates a `src/giljo_mcp/prompts/` subpackage. `ThinClientPromptGenerator` becomes a thin dispatcher: it receives the platform and delegates to the correct builder. All callers use the same import path they use today via a re-export in `__init__.py`, so zero callers need modification beyond an import path update in the rare case they import internal helpers directly.

---

## Pre-Work: Mandatory Caller Discovery

Before moving a single line of code:

```bash
grep -rn "ThinClientPromptGenerator" /media/patrik/Work/GiljoAI_MCP/src/ /media/patrik/Work/GiljoAI_MCP/api/ --include="*.py"
grep -rn "thin_prompt_generator" /media/patrik/Work/GiljoAI_MCP/src/ /media/patrik/Work/GiljoAI_MCP/api/ --include="*.py"
grep -rn "_build_claude_code_execution_prompt\|generate_staging_prompt\|_build_ch2_startup" /media/patrik/Work/GiljoAI_MCP/src/ /media/patrik/Work/GiljoAI_MCP/api/ --include="*.py"
```

Record every file and line number. Every reference must be updated as part of this handover.

---

## Scope

**Primary file:** `src/giljo_mcp/thin_prompt_generator.py` (1676 lines)

**New files to create:**
- `src/giljo_mcp/prompts/__init__.py` — re-exports `ThinClientPromptGenerator` for backward compatibility
- `src/giljo_mcp/prompts/claude_prompt_builder.py` — Claude-specific prompt construction
- `src/giljo_mcp/prompts/codex_prompt_builder.py` — Codex-specific prompt construction
- `src/giljo_mcp/prompts/staging_prompt_builder.py` — staging/CH2 prompt construction

---

## Implementation Plan

### Phase 1: Map the file

Read `src/giljo_mcp/thin_prompt_generator.py` in full. Produce a mental map of:
- Every public method (no leading underscore): its signature, line range, and which callers invoke it
- Every private helper: which public methods use it, and whether it is platform-specific or shared
- Module-level constants and imports: which belong to which builder

Do not write code yet. The map drives the extraction order.

### Phase 2: Create the subpackage scaffold

```
src/giljo_mcp/prompts/
    __init__.py
    claude_prompt_builder.py
    codex_prompt_builder.py
    staging_prompt_builder.py
```

`__init__.py` must re-export `ThinClientPromptGenerator` so any `from giljo_mcp.thin_prompt_generator import ThinClientPromptGenerator` import that has not yet been updated still works:

```python
from giljo_mcp.prompts.claude_prompt_builder import ClaudePromptBuilder
from giljo_mcp.prompts.codex_prompt_builder import CodexPromptBuilder
from giljo_mcp.prompts.staging_prompt_builder import StagingPromptBuilder
from giljo_mcp.thin_prompt_generator import ThinClientPromptGenerator

__all__ = [
    "ThinClientPromptGenerator",
    "ClaudePromptBuilder",
    "CodexPromptBuilder",
    "StagingPromptBuilder",
]
```

### Phase 3: Extract ClaudePromptBuilder

Move to `prompts/claude_prompt_builder.py`:
- `_build_claude_code_execution_prompt` (304 lines — this method alone justifies the split)
- All private helpers that are only called from Claude-specific methods
- Any module-level constants used exclusively by Claude prompt construction

`ClaudePromptBuilder` is a plain class (no FastAPI dependency injection). It takes the same constructor arguments as the extracted methods require. It must not import from `codex_prompt_builder` or `staging_prompt_builder`.

Maximum method size: 200 lines. If `_build_claude_code_execution_prompt` exceeds 200 lines after extraction, break it into named sub-methods (e.g., `_build_tool_section`, `_build_context_section`). Name sub-methods descriptively — no `_part1`, `_part2`.

### Phase 4: Extract CodexPromptBuilder

Move to `prompts/codex_prompt_builder.py`:
- All Codex-specific prompt building methods and their private helpers
- Codex-specific constants

Same structural rules as Phase 3.

### Phase 5: Extract StagingPromptBuilder

Move to `prompts/staging_prompt_builder.py`:
- `generate_staging_prompt`
- `_build_ch2_startup`
- All helpers invoked exclusively from these methods

Same structural rules.

### Phase 6: Reduce ThinClientPromptGenerator to a dispatcher

After extraction, `ThinClientPromptGenerator` must:
- Instantiate (or accept as constructor arguments) `ClaudePromptBuilder`, `CodexPromptBuilder`, and `StagingPromptBuilder`
- Retain its original public method names and signatures (callers must not change)
- Delegate each public method call to the correct builder
- Retain any methods that are genuinely shared across platforms (shared helpers that do not belong to a single builder)
- Target: under 600 lines (hard ceiling: 800 lines)

No method in the dispatcher may exceed 200 lines.

### Phase 7: Update all imports

For every file discovered in Pre-Work:
- Update imports to point at the new location if they import internal helpers directly
- `ThinClientPromptGenerator` callers that import from `giljo_mcp.thin_prompt_generator` need no change — the class remains at that path
- Any caller importing from `giljo_mcp.prompts` needs the `__init__.py` re-export

After updating, run:
```bash
grep -rn "from giljo_mcp.thin_prompt_generator import\|from src.giljo_mcp.thin_prompt_generator import" /media/patrik/Work/GiljoAI_MCP/ --include="*.py"
```
All remaining hits must point at `ThinClientPromptGenerator` only (not internal helpers). If an internal helper is referenced directly by a caller, expose it through the appropriate builder class instead.

### Phase 8: Verification

Run after every individual split (not just at the end):

```bash
# Startup check
python -c "from api.app import create_app; print('OK')"

# Unit tests
python -m pytest tests/unit/ -q --timeout=60 --no-cov

# Lint
ruff check src/ api/
```

All three must pass before proceeding to the next extraction. If a test fails, fix it or delete it (if it tested a removed private helper that no longer exists at its old path). Never skip tests.

---

## Constraints

- No commented-out code. Delete removed code. Git has the history.
- No dict-return patterns introduced. All error paths raise exceptions.
- No function may exceed 200 lines in any of the new files.
- No class may exceed 1000 lines.
- The public interface of `ThinClientPromptGenerator` must not change. External callers must not require modification.
- Every tenant_key-filtering query (if any exist inside prompt builders) must retain the filter after extraction — verify with grep after each split.
- No `ruff` violations in the final state.

---

## Acceptance Criteria

- [ ] `src/giljo_mcp/thin_prompt_generator.py` is under 800 lines
- [ ] No method in any file under `src/giljo_mcp/prompts/` exceeds 200 lines
- [ ] `src/giljo_mcp/prompts/__init__.py` re-exports `ThinClientPromptGenerator`
- [ ] All callers of `ThinClientPromptGenerator` public methods work without modification
- [ ] `python -c "from api.app import create_app; print('OK')"` passes
- [ ] `python -m pytest tests/unit/ -q --timeout=60 --no-cov` passes with zero new failures
- [ ] `ruff check src/ api/` reports zero issues
- [ ] No commented-out code in any modified file

---

## Rollback

```bash
git checkout -- src/giljo_mcp/thin_prompt_generator.py
rm -rf src/giljo_mcp/prompts/
```

---

## Commit Message Format

```
cleanup(0950g): split ThinClientPromptGenerator into prompts/ subpackage

- Extract ClaudePromptBuilder (_build_claude_code_execution_prompt + helpers)
- Extract CodexPromptBuilder (Codex-specific methods)
- Extract StagingPromptBuilder (generate_staging_prompt, _build_ch2_startup)
- ThinClientPromptGenerator becomes dispatcher; public interface unchanged
- thin_prompt_generator.py reduced from 1676 lines to <800
```

---

## Chain Execution Instructions

### Step 1: Read Chain Log
Read `prompts/0950_chain/chain_log.json`.
- Check `orchestrator_directives` on session `0950g` — if STOP, halt immediately.
- Read `notes_for_next` from session `0950f` before starting.

### Step 2: Mark Session Started
Update session `0950g` in chain_log.json: `"status": "in_progress"`.

### Step 3: Execute
Follow Phases 1-8 above in order. Run verification after each extraction phase.

### Step 4: Update Chain Log
Before stopping, update session `0950g` with:
- `tasks_completed`: list each extraction completed
- `deviations`: any deviation from this plan and why
- `blockers_encountered`: anything that required escalation
- `notes_for_next`: critical context for 0950h (MessageService split), especially any shared utilities discovered in this file that MessageService may also use
- `cascading_impacts`: any import path changes that 0950h-0950j agents must be aware of
- `summary`: one-paragraph summary of what was done
- `status`: `"complete"`

### Step 5: STOP
Do NOT spawn the next terminal. The orchestrator handles that.

---

## Progress Updates

*(Agent updates this section during implementation)*
