# Handover 0842f: Agent Lab — Chain Strategy Template Download

**Date:** 2026-03-27
**Edition Scope:** CE
**From Agent:** Planning Session
**To Agent:** ux-designer
**Priority:** Medium
**Estimated Complexity:** 0.5 hours
**Status:** Not Started
**Standalone handover** (not part of the 0842a-e chain — the chain is complete)
**Depends on:** None

---

## Task Summary

Add a third chapter to the Agent Lab dialog (`AgentTipsDialog.vue`) with a downloadable chain strategy template — a generalized, tool-agnostic markdown file that any developer can customize for their own multi-terminal chain projects.

---

## Context and Background

The Agent Lab dialog (`frontend/src/components/common/AgentTipsDialog.vue`) currently has two accordion chapters:

1. **Monitoring Agents** — polling tip with copy button
2. **Multi-Terminal Chains** — spawn commands for Claude/Codex/Gemini with tool selector chips

Chapter 2 covers the *mechanics* (spawn syntax, colors, flags) but offers no strategic planning template. Developers who want to set up a chain still need to figure out the coordination pattern themselves. A downloadable template gives them a head start.

This is an **experimental/suggestions-only feature** — no server integration, no auto-generation. Just a static file the user downloads and customizes.

---

## Technical Details

### New Chapter 3: "Chain Strategy Template"

Add a new `v-expansion-panel` after Chapter 2 in the accordion.

**Icon:** `mdi-file-tree`
**Title:** "Chain Strategy Template"

**Content:**
- 2-3 sentence explanation: "For complex features, break work into sequenced phases with a shared communication file. Download this template, customize it for your project, and point your agents to it."
- Brief bullet list of what the template covers (pre-chain setup, chain log schema, phase planning, orchestrator review checklist)
- **Download button** (`v-btn` with `mdi-download` icon): triggers browser download of the template `.md` file
- Caption: "Works with any MCP-compatible AI coding tool (Claude Code, Codex CLI, Gemini CLI)."

### Template File

Store at: `frontend/public/templates/chain_strategy_template.md`

This is a **static asset** served directly by Vite. The download button creates an `<a>` element with `download` attribute pointing to `/templates/chain_strategy_template.md`.

**Template content requirements:**
- Tool-agnostic — no mention of specific CLI tools except as examples
- Scrubbed of ALL GiljoAI-specific references (no handover numbers, no internal file paths, no product names)
- Generalized — uses placeholder names like `{project}`, `{phase_1_title}`, etc.
- Includes:
  - Pre-chain setup checklist (commit, branch, create chain log)
  - Chain log JSON schema (blank template with field descriptions)
  - Orchestrator-gated workflow diagram
  - Dynamic sleep heuristics table
  - Agent handover template (what to put in each phase's instructions)
  - Phase planning table template
  - Orchestrator review checklist between phases
  - Lessons learned section (common pitfalls)
- Total length: ~150-200 lines. Concise and practical, not a wall of text.

### Download Implementation

```javascript
const downloadTemplate = () => {
  const link = document.createElement('a')
  link.href = '/templates/chain_strategy_template.md'
  link.download = 'chain_strategy_template.md'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}
```

### Files to Create/Modify

| File | Change |
|------|--------|
| `frontend/public/templates/chain_strategy_template.md` | **NEW** — the downloadable template |
| `frontend/src/components/common/AgentTipsDialog.vue` | Add Chapter 3 expansion panel with download button |

### Key Existing Code

- **AgentTipsDialog.vue**: `frontend/src/components/common/AgentTipsDialog.vue` (317 lines) — accordion with 2 chapters, `copyText()` helper, `useClipboard` composable
- **Styling**: scoped SCSS with `lab-*` and `tip-*` class prefixes
- **Clipboard composable**: `frontend/src/composables/useClipboard.js`

---

## Implementation Plan

### Phase 1: Write the Template File

1. Create `frontend/public/templates/chain_strategy_template.md`
2. Write generalized chain strategy content (see requirements above)
3. Scrub all GiljoAI-specific references

### Phase 2: Add Chapter 3 to Agent Lab Dialog

1. Add new `v-expansion-panel` in `AgentTipsDialog.vue` after Chapter 2
2. Add explanation text, bullet list, and download button
3. Implement `downloadTemplate()` function
4. Style consistently with existing chapters

---

## Testing Requirements

- Download button triggers file download (manual test)
- Template file is accessible at `/templates/chain_strategy_template.md` (manual test)
- Dialog still renders correctly with 3 chapters (manual test)
- Existing Chapter 1 and 2 functionality unchanged

## Success Criteria

- [ ] Chapter 3 "Chain Strategy Template" visible in Agent Lab dialog
- [ ] Download button saves `.md` file to user's machine
- [ ] Template is tool-agnostic (no GiljoAI-specific content)
- [ ] Template includes: setup checklist, chain log schema, orchestrator workflow, sleep heuristics, agent template, review checklist
- [ ] Existing Agent Lab chapters unchanged
- [ ] No `!important` CSS overrides, `smooth-border` on rounded elements

## Rollback Plan

- Remove the expansion panel from AgentTipsDialog.vue
- Delete the template file from `frontend/public/templates/`
- Purely additive — no existing functionality affected

---

## MANDATORY: Pre-Work Reading

Before writing ANY code, you MUST read these documents:

1. `handovers/HANDOVER_INSTRUCTIONS.md` — quality gates, code discipline
2. `handovers/Reference_docs/MULTI_TERMINAL_CHAIN_STRATEGY.md` — the source material to generalize from (v3)

**CRITICAL: Use the `ux-designer` subagent for ALL implementation work.**

