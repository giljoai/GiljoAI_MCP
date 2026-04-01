# 0874 — Inline Style Final Sweep

**Edition Scope:** CE
**Branch:** feature/0873-style-centralization
**Prerequisite:** 0873a-o complete (all on same branch)
**Goal:** Zero visual change. Replace remaining hardcoded inline values with existing tokens/classes.

---

## 0874a — Agent/Status Color Tokens in Templates

**Goal:** Replace ~45 hardcoded agent/status hex colors in template `style=` attributes with dynamic bindings using existing utilities.

**Pattern to find:**
```bash
grep -rn 'style="background: rgba(' frontend/src/views/ frontend/src/components/ --include="*.vue"
grep -rn "style=\"color: #" frontend/src/views/ frontend/src/components/ --include="*.vue"
```

**Files to fix (from audit):**
1. `ProductDetailsDialog.vue` (~13 inline styles) — summary level badges use hardcoded `rgba(103,189,109,0.15); color: #67bd6d` etc. Replace with `:style` using `hexToRgba()` from `@/utils/colorUtils` + agent color tokens from `agentColors.js`
2. `MessageItem.vue` (~6) — status/priority colors hardcoded. Use existing status color mappings.
3. `RecentMemoriesList.vue` (~5) — memory type colors. Use agent color tokens.
4. `BroadcastPanel.vue` (~4) — delivery status colors. Use status tokens.
5. `RoleBadge.vue` (~2) — role colors hardcoded in template. Move to computed or scoped class.

**Strategy per file:**
- If the color maps to an agent color → use `getAgentColor()` or CSS `var(--agent-*-primary)`
- If the color maps to a status color → create a computed map or scoped classes
- For `rgba(color, 0.15)` badge backgrounds → use `hexToRgba()` with the token value
- If a pattern repeats 3+ times in one file → extract to a scoped CSS class

**Do NOT touch:**
- Dynamic `:style` bindings that compute from database values (e.g., `agent.color`, `item.project_type?.color`)
- Inline styles in `<style>` blocks (those are already tokenized)

**Tests:** Run full Vitest suite.

---

## 0874b — Layout Utilities + Whitespace + Final Verification

**Goal:** Replace ~39 layout inline styles with Vuetify utility classes and ~35 whitespace styles with utility classes.

### Sub-task 1: Layout inline styles → Vuetify classes

**Find:**
```bash
grep -rn 'style="display: flex' frontend/src/views/ frontend/src/components/ --include="*.vue"
grep -rn 'style="gap:' frontend/src/views/ frontend/src/components/ --include="*.vue"
```

**Vuetify class mappings:**
| Inline Style | Vuetify Class |
|-------------|---------------|
| `display: flex` | `d-flex` |
| `align-items: center` | `align-center` |
| `justify-content: space-between` | `justify-space-between` |
| `justify-content: center` | `justify-center` |
| `flex-direction: column` | `flex-column` |
| `flex-wrap: wrap` | `flex-wrap` |
| `gap: Xpx` | `ga-X` (Vuetify 3.4+) or keep if no class exists |
| `max-width: Xpx` | Keep inline if one-off, extract to scoped class if repeated |

**Key files:** AppBar.vue, ContextPriorityConfig.vue, AgentExport.vue, AiToolConfigWizard.vue

### Sub-task 2: Whitespace utility classes

**Find:**
```bash
grep -rn 'white-space:' frontend/src/views/ frontend/src/components/ --include="*.vue" | grep 'style='
```

**If 3+ usages of same value:** Create utility class in main.scss (e.g., `.text-pre-wrap`, `.text-nowrap`).
**If 1-2 usages:** Leave inline — not worth a class.

### Sub-task 3: Final inline style count

Run the same audit that produced the 142/81 counts. Report new totals. Target: <100 static, <60 dynamic (remaining should all be data-driven or one-off layout).

**Tests:** Run full Vitest suite.

---

## Chain Execution Instructions (Both Sessions)

### Step 1: Read Chain Log
Read `prompts/0874_chain/chain_log.json`
- Check `orchestrator_directives` — if STOP, halt immediately
- Review previous session's `notes_for_next`

### Step 2: Mark Session Started
Update your session: `"status": "in_progress", "started_at": "<timestamp>"`

### Step 3: Execute Handover Tasks

### Step 4: Update Chain Log
Update your session with all fields: tasks_completed, deviations, blockers_encountered, notes_for_next, cascading_impacts, summary, status: "complete", completed_at

### Step 5: STOP
Do NOT spawn the next terminal. The orchestrator will review and spawn the next session.
Commit your chain log update and exit.
