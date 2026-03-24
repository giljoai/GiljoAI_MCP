# Handover 0836d: Two-Phase Install Pattern & Codex Skill Rewrite

**Date:** 2026-03-23
**From Agent:** Session coordinator (continuation agent)
**To Agent:** Same session — executing immediately
**Priority:** Critical
**Estimated Complexity:** 2-3 hours
**Status:** Not Started
**Edition Scope:** CE

---

## Task Summary

Standardize all three platforms (Claude Code, Gemini CLI, Codex CLI) to a two-phase install pattern: bootstrap installs commands/skills only, then user restarts and runs the agent installer slash command/skill. Also replace the Codex CLI skill (`GIL_GET_AGENTS_CODEX_SKILL_MD`) with battle-tested content from live Codex testing.

---

## Context and Background

### The Problem

During 0836 integration testing, two issues emerged:

1. **Bootstrap/slash command duplication:** The bootstrap prompts (Setup button clipboard copy) duplicated model selection logic that `/gil_get_agents` already handles. This caused a sync bug — bootstraps were installing agents without asking for model preference. We patched it (commit `b58b9ed9`) by adding model selection to bootstraps, but this created a maintenance burden: model selection logic now lives in TWO places per platform.

2. **Codex CLI skill was untested and thin.** Live testing on Codex CLI v0.116.0 (2026-03-22) revealed critical issues:
   - Built-in roles (`analyzer`, `documenter`) shadow custom roles with the same name — agents must use `gil-` prefix
   - `config_file` paths in `config.toml` must be RELATIVE (`agents/gil-foo.toml`), not absolute or tilde-prefixed
   - The current `GIL_GET_AGENTS_CODEX_SKILL_MD` (26 lines) lacks the format reference, naming rules, merge protocol, and verification step

### The Decision

Align all platforms to the Codex two-phase pattern:

| Phase | What Happens |
|-------|-------------|
| **Phase 1: Bootstrap (Setup button)** | Install slash commands/skills ONLY. Tell user to restart. |
| **Phase 2: Slash command/skill** | User runs `/gil_get_agents` (or `$gil-get-agents`). Full agent install with model selection, location choice, backups. |

**Why this is better:**
- Model selection logic lives in exactly ONE place per platform (the slash command/skill)
- No sync burden between bootstrap and slash command
- Consistent UX across all three platforms
- Bootstrap becomes trivially simple — download, extract, restart

---

## Technical Details

### Files to Modify

| File | Change |
|------|--------|
| `src/giljo_mcp/tools/slash_command_templates.py` | Replace `GIL_GET_AGENTS_CODEX_SKILL_MD` with battle-tested version. Simplify `BOOTSTRAP_CLAUDE_CODE`, `BOOTSTRAP_GEMINI_CLI`, `BOOTSTRAP_CODEX_CLI` to commands/skills-only. |
| `frontend/src/components/AgentExport.vue` | Sync bootstrap template copies with backend. |
| `tests/integration/test_multi_platform_export.py` | Update bootstrap assertions (remove model selection test, add restart-then-run assertions). |
| `tests/test_slash_command_templates.py` | Update if Codex skill content assertions exist. |

### What Changes Per Platform

**Claude Code Bootstrap (BEFORE):**
- Step 1: Install slash commands
- Step 2: Install agents (with location choice)
- Step 3: Configure model preference

**Claude Code Bootstrap (AFTER):**
- Step 1: Install slash commands
- Step 2: Restart Claude Code, then run `/gil_get_agents`

**Gemini CLI Bootstrap:** Same simplification as Claude Code.

**Codex CLI Bootstrap:** Already two-phase — just needs minor wording cleanup to match.

**Codex Skill (`GIL_GET_AGENTS_CODEX_SKILL_MD`):** Full rewrite from `handovers/gil-get-agents-SKILL.md` incorporating:
- `gil-` prefix requirement (line 21-33 of source)
- Relative `config_file` paths (line 75-76)
- Exact `.toml` file format reference (lines 44-71)
- `config.toml` merge rules (lines 127-134)
- Verification step (lines 136-148)

---

## Implementation Plan

### Phase 1: Replace Codex Skill
1. Replace `GIL_GET_AGENTS_CODEX_SKILL_MD` in `slash_command_templates.py` with content from `handovers/gil-get-agents-SKILL.md`
2. Verify tests pass

### Phase 2: Simplify All Three Bootstraps
1. Rewrite `BOOTSTRAP_CLAUDE_CODE` — slash commands only, then "restart and run `/gil_get_agents`"
2. Rewrite `BOOTSTRAP_GEMINI_CLI` — custom commands only, then "restart and run `/gil_get_agents`"
3. Confirm `BOOTSTRAP_CODEX_CLI` — skills only, then "restart and run `$gil-get-agents`" (should already be correct)
4. Sync frontend `AgentExport.vue` copies

### Phase 3: Update Tests
1. Update bootstrap content assertions
2. Add test: Codex skill mentions `gil-` prefix
3. Add test: All bootstraps do NOT contain model selection (enforces two-phase pattern)
4. Run full test suite

---

## Testing Requirements

**Unit Tests:**
- All bootstrap templates contain only command/skill install instructions (no model selection)
- All bootstraps mention restart + run agent installer
- Codex skill contains `gil-` prefix instructions
- Codex skill contains relative `config_file` path instructions

**Manual Testing:**
- Claude Code: Setup button → paste → installs slash commands only → restart → `/gil_get_agents` → model selection → agents installed
- Codex CLI: Setup button → paste → installs skills only → restart → `$gil-get-agents` → model selection + config.toml merge → agents installed
- Gemini CLI: Setup button → paste → installs commands only → restart → `/gil_get_agents` → model selection → agents installed

---

## Success Criteria

- [ ] All three bootstraps are commands/skills-only (no agent download, no model selection)
- [ ] Codex skill includes `gil-` prefix, relative paths, format reference, merge rules, verification
- [ ] Model selection logic exists in exactly ONE place per platform
- [ ] Frontend and backend bootstrap copies are in sync
- [ ] All tests pass
- [ ] No regressions in existing Claude Code flow
