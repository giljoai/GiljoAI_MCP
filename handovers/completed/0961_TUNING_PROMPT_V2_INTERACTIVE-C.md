# Handover 0961: Tuning Prompt v2 — Interactive Codebase-Aware Review

**Date:** 2026-04-07
**Edition Scope:** CE
**From Agent:** Claude Opus 4.6 (design session with product owner)
**To Agent:** Next implementing session
**Priority:** High
**Estimated Complexity:** 2-3 days
**Status:** COMPLETE

---

## Task Summary

Upgrade the product context tuning prompt from a batch-submit model (agent analyzes silently, dumps all proposals at once via MCP tool) to an **interactive, phased model** where the agent researches the actual codebase, presents a quick scan summary, then walks the user through each drifted section one-at-a-time for approval before submitting.

**Why it matters:** The current prompt tells the agent to analyze 360 memory and submit structured proposals silently. In practice, this produces low-confidence proposals because the agent only sees memory summaries, not the actual code. Worse, the user has no control over what gets submitted — they review proposals after the fact in a separate UI. The new flow puts the user in the loop during analysis, lets the agent ground its findings in real code, and only submits what the user explicitly approved.

**What changes:** Only the prompt template and backend serialization. The `submit_tuning_review` MCP tool, the `ProductTuningReview` UI, and the proposal storage model remain unchanged. The frontend `ProductTuningMenu.vue` and `ProductTuningDialog.vue` require no changes — they already generate/preview/copy correctly.

---

## Context: What Exists Today (0831 Baseline)

### Current Prompt Flow
1. User selects sections, clicks "Generate Tuning Prompt"
2. Backend assembles prompt with current product context + serialized 360 memory entries
3. Prompt instructs agent: "Do NOT output the analysis as text. Call the MCP tool with structured results."
4. Agent analyzes memory-only (no codebase access), calls `submit_tuning_review` silently
5. Proposals land in `product.tuning_state.pending_proposals`
6. User reviews proposals in `ProductTuningReview.vue` (accept/edit/dismiss per section)

### Current Prompt Template (in `product_tuning_service.py:92-131`)
- Provides current context + 360 memory + git section
- Instructions focus on comparing context claims vs. project history
- Ends with "Do NOT output the analysis as text. Call the MCP tool with structured results."

### Infrastructure That Stays Unchanged
- **`submit_tuning_review` MCP tool** (`src/giljo_mcp/tools/submit_tuning_review.py`) — already accepts the proposals array
- **`ProductTuningReview.vue`** — drift badges, confidence chips, accept/edit/dismiss UI
- **`ProductTuningMenu.vue`** — section checkboxes, generate button, preview+copy display
- **`ProductTuningDialog.vue`** — dialog wrapper with proposals + generate sections
- **`SECTION_FIELD_MAP`** — maps section keys to product fields/relations
- **`_serialize_current_context()`** — serializes product fields for selected sections
- **Endpoint** `POST /api/v1/products/{id}/tuning/generate-prompt` — unchanged contract

---

## Design: New 4-Phase Interactive Prompt

### Phase 1: RESEARCH (silent — no output to user)

The agent grounds itself in the actual codebase before making judgments:

1. **File structure** — `ls` project root, static dirs
2. **Dependencies** — Read `requirements.txt` / `package.json` / `go.mod`
3. **Entry point** — Read first 60 lines of main backend file (imports, config, patterns)
4. **Tests** — Test discovery only (`pytest --co -q` or equivalent), no execution
5. **Git history** — `git log --oneline -15` for recent changes
6. **Project memory** — `fetch_context(categories=["memory_360"], product_id="...")` for closeout history

This phase is silent — the agent does not present findings yet.

### Phase 2: QUICK SCAN (brief output)

Agent summarizes findings in a structured format:

```
Scanned the codebase and project history.

Sections with likely drift:
- <section>: <one-line reason>

Sections that look current:
- <section>, <section>, ...

Want to review the flagged sections? Or walk through all of them?
```

Agent **waits for user response** before continuing.

### Phase 3: INTERACTIVE REVIEW (one section at a time)

For each section the user wants to review:

```
### <Section Name>

**Current value:**
<the stored value as-is>

**What I found:**
<evidence from code, git log, or project memory>

**Drift detected:** Yes / No

**Proposed update:**
<full replacement text — or "No change needed">

Does this look right? Want to adjust the wording before I save it?
```

**Rules:**
- Wait for user approval before moving to next section
- If user provides alternative wording, use their version
- If user says "skip", exclude from final submission
- If user says "looks good", mark approved and move on
- Write COMPLETE replacement values, not diffs
- Keep proposed values factual and concise — no marketing language

### Phase 4: SUBMIT

After all sections reviewed:

```
Ready to submit N approved updates:
- <section>: <brief change summary>

Submitting now.
```

Then call `submit_tuning_review()` with only the approved proposals.

### Vision Documents: Special Handling

When "Vision Documents" is a selected section, append this instruction:

```
NOTE: Vision Documents are historical records of original product intent.
Do NOT propose replacing them. Instead, note any divergence between the
vision and current reality, and suggest updates to other sections
(like Description or Core Features) to reflect the current state.
```

---

## Implementation Plan

### Step 1: Replace the Prompt Template

**File:** `src/giljo_mcp/services/product_tuning_service.py`

Replace `TUNING_PROMPT_TEMPLATE` (lines 92-131) with the new 4-phase template.

Template variables (same `str.format()` pattern):
- `{product_name}` — **NEW**, add to template vars
- `{product_id}` — existing
- `{current_context}` — existing (serialized sections)
- `{section_keys}` — existing
- `{vision_note}` — **NEW**, conditional vision documents instruction

**Remove** from the template:
- `{lookback_count}` — no longer needed (agent fetches via `fetch_context` MCP tool)
- `{memory_entries}` — no longer needed (agent calls `fetch_context` directly)
- `{git_section}` — no longer needed (agent runs `git log` directly)

### Step 2: Simplify `assemble_tuning_prompt()`

**File:** `src/giljo_mcp/services/product_tuning_service.py`, method `assemble_tuning_prompt`

The current method fetches 360 memory entries and serializes them into the prompt. With the new template, the agent fetches its own context via MCP tools and codebase commands. This means:

1. **Remove** the `_memory_repo.get_entries_for_context()` call
2. **Remove** the `_serialize_memory_entries()` call
3. **Remove** the `_serialize_git_section()` call
4. **Remove** the depth config lookup (`depths.get("memory_last_n_projects")`)
5. **Keep** the `_serialize_current_context()` call (still needed for "Current value" display)
6. **Keep** the `_get_product()` call (with selectinload fix from earlier today)
7. **Add** product name to the template format call
8. **Add** conditional vision note based on whether `"vision_documents"` is in `valid_sections`

The return dict shape stays the same: `{prompt, sections_included, lookback_depth, git_enabled}`. Set `lookback_depth` to `None` and `git_enabled` to `False` since the agent handles these itself now.

### Step 3: Expand `SECTION_FIELD_MAP` with Missing Sections

The agent's spec references sections that exist in `SECTION_EVIDENCE_SOURCES` but are missing from `SECTION_FIELD_MAP`:

| Section Key | Missing From | Product Field |
|---|---|---|
| `codebase_structure` | `SECTION_FIELD_MAP` | `product.codebase_structure` (direct field or config_data) |
| `database_type` | `SECTION_FIELD_MAP` | `product.database_type` |
| `backend_framework` | `SECTION_FIELD_MAP` | Nested in tech_stack relation |
| `frontend_framework` | `SECTION_FIELD_MAP` | Nested in tech_stack relation |
| `vision_documents` | `SECTION_FIELD_MAP` | VisionDocument model (special handling) |

**Action:** Verify which of these exist as actual Product model fields vs. config_data keys. Add them to `SECTION_FIELD_MAP` only if they have real backing fields. For sections that map to sub-fields of existing relations (e.g., `backend_framework` is inside `tech_stack`), decide whether to expose them as standalone tuning targets or keep them grouped under their parent section.

**Decision needed:** The original 0831 handover listed 11 section targets but `SECTION_FIELD_MAP` only has 7. This was likely intentional scope reduction during implementation. The new prompt should work with whatever sections `SECTION_FIELD_MAP` currently supports. Expanding the map is a stretch goal, not a blocker.

### Step 4: Update Tests

**Files:**
- `tests/unit/test_product_tuning_service.py` (or wherever tuning service tests live)
- Any test that asserts on the prompt template content

Update tests to verify:
1. New template includes Phase 1-4 structure
2. Product name is injected
3. Vision note appears only when `vision_documents` is in selected sections
4. 360 memory / git section no longer serialized into prompt
5. `submit_tuning_review` call structure in prompt matches existing MCP tool schema

### Step 5: Fix the selectinload Bug (ALREADY DONE)

The `_get_product()` method needs `selectinload` for `Product.tech_stack`, `Product.architecture`, and `Product.test_config` to avoid the `MissingGreenlet` error. This fix was applied earlier in this session — verify it's committed.

---

## What NOT to Change

- **`submit_tuning_review` MCP tool** — The proposals schema is identical. The agent still calls the same tool with the same structure. Only difference: proposals now contain only user-approved items.
- **`ProductTuningReview.vue`** — Still renders proposals the same way. Approved-only proposals may mean fewer proposals arrive, but the UI handles empty/partial states already.
- **`ProductTuningMenu.vue`** — No changes. Preview+copy flow is correct as-is.
- **`ProductTuningDialog.vue`** — No changes.
- **Endpoint contract** — Same request/response shape.

---

## Confidence Level Impact

The current approach produces mostly "medium" or "low" confidence proposals because the agent only has 360 memory summaries. The new approach:
- **"high"** = agent read actual code files or ran commands to verify
- **"medium"** = inferred from project memory / git log only
- **"low"** = best guess, could not verify

Expect significantly more "high" confidence proposals with codebase access.

---

## Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Agent may not have filesystem access (e.g., web-based agent) | Phase 1 instructions are best-effort. If agent can't run commands, it falls back to 360 memory via `fetch_context`. The prompt should include a fallback note. |
| Longer user interaction time vs. silent batch | This is the point — user control over what gets submitted. The quick scan (Phase 2) lets users skip sections that look current. |
| Agent may not wait for user input between sections | The prompt explicitly says "Wait for user approval before moving to the next section." Most coding agents (Claude Code, Gemini CLI) respect this. |

---

## Quality Gates

- [ ] `TUNING_PROMPT_TEMPLATE` replaced with 4-phase interactive version
- [ ] `assemble_tuning_prompt()` no longer serializes 360 memory / git into prompt
- [ ] Product name injected into prompt
- [ ] Vision documents special handling conditional is present
- [ ] `selectinload` fix verified on `_get_product()`
- [ ] Existing tests updated, all pass
- [ ] Manual test: generate prompt, paste into coding agent, verify interactive flow works
- [ ] `submit_tuning_review` still receives valid proposals and stores correctly
- [ ] No changes to frontend components
