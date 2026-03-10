# Handover 0813: Agent Template Context Separation

**Date:** 2026-03-10
**From Agent:** Planning session
**To Agent:** Next Session
**Priority:** High
**Estimated Complexity:** 8-12 hours
**Status:** Not Started
**Edition Scope:** CE

---

## Task Summary

Separate agent template content into three distinct contexts: **Role Identity** (baked into template file), **Operating Protocols** (delivered via `get_agent_mission()` → `full_protocol`), and **Work Order** (delivered via `get_agent_mission()` → `mission`). This eliminates the current 85% protocol duplication in exported `.md` files, fixes the `user_instructions` export gap, and produces lean role-focused templates that are portable across CLI tools (Claude Code, Codex CLI, Gemini CLI).

## Git Branching

**Create a feature branch before any code changes:**
```bash
git checkout -b 0813-template-context-separation
```
All work happens on this branch. Do NOT commit to master.

---

## Context and Background

### The Problem (Three Findings)

**Finding 1: Templates are 85% protocol boilerplate.** Examining all 5 exported `.claude/agents/*.md` files (implementer, reviewer, analyzer, tester, documenter), ~90 of ~108 lines are identical GiljoAI operating protocol (MCP Tool Usage, CHECK-IN PROTOCOL, MESSAGING, Agent Guidelines, If Blocked or Unclear, REQUESTING BROADER CONTEXT). Only ~18 lines per file are role-specific (YAML frontmatter + Behavioral Rules + Success Criteria).

**Finding 2: Protocols are delivered twice.** The same protocol content exists in both the `.md` template (loaded as system prompt at spawn) AND in `full_protocol` returned by `get_agent_mission()` (fetched on turn 1). The templates even acknowledge this: "Full protocol in `full_protocol` from `get_agent_mission()`."

**Finding 3: `user_instructions` is not exported.** The `AgentTemplate` model has a dual-field system (Handover 0106): `system_instructions` (protected, protocol content) and `user_instructions` (editable, role prose). But `template_renderer.render_claude_agent()` only puts `system_instructions` into the `.md` body. The `user_instructions` field -- which contains the actual role-specific prose -- is never exported. Role identity in exported files comes only from `behavioral_rules` and `success_criteria` JSON lists.

### The Architecture Goal (Three Contexts)

| Context | What | Where | Why |
|---|---|---|---|
| **Role Identity** | WHO -- expertise, behavioral rules, success criteria, role prose | Template file (`.md`) | Static per agent type. User-customizable. Portable across CLI formats. |
| **Operating Protocols** | HOW -- 5-phase lifecycle, MCP tool usage, messaging, check-ins, blocker escalation | `get_agent_mission()` → `full_protocol` | Already exists in `protocol_builder.py`. Single source of truth. |
| **Work Order** | WHAT -- team context, assigned tasks, dependencies | `get_agent_mission()` → `mission` | Fully dynamic per project/mission. |

### Multi-Terminal vs Claude Code CLI: How Role Identity Is Delivered

**CRITICAL: These two modes deliver role identity through completely different paths. Both must work after refactoring.**

**Multi-terminal mode** (agent has NO template file):
1. Orchestrator calls `spawn_agent_job()` which calls `_resolve_spawn_template()`
2. `_resolve_spawn_template()` queries `AgentTemplate` by `agent_name` + `tenant_key`
3. Concatenates `system_instructions + "\n\n" + user_instructions` into `template_expertise`
4. Bakes this into `AgentJob.mission` wrapped as: `AGENT EXPERTISE & PROTOCOL [template] / YOUR ASSIGNED WORK [mission]`
5. Agent later calls `get_agent_mission()` → gets `mission` (with template baked in) + `full_protocol` (5-phase lifecycle)

**Claude Code CLI mode** (agent HAS template file):
1. Orchestrator calls `spawn_agent_job()` → `_resolve_spawn_template()` **SKIPS** injection
2. Claude Code loads `.claude/agents/<name>.md` as the subagent's system prompt (role identity here)
3. Agent calls `get_agent_mission()` → gets `mission` (raw work order, NO template baked in) + `full_protocol`

**There is NO MCP tool for an individual agent to fetch its own template/role.** The `get_agent_templates` context tool (`src/giljo_mcp/tools/context_tools/get_agent_templates.py`) exists but serves the **orchestrator** during staging -- it returns metadata about ALL templates, not an individual agent's role.

**After this refactor, multi-terminal gets BETTER:**
- Currently baked: 90 lines of protocol (system_instructions) + minimal role (user_instructions was poorly populated)
- After refactor baked: 10-line bootstrap (system_instructions) + 200-400 words of rich role prose (user_instructions)
- Protocols come from `full_protocol` via `get_agent_mission()` in both modes -- removing them from the bake-in is safe

### Additional Export Gap: `get_agent_templates` Context Tool

The context tool at `src/giljo_mcp/tools/context_tools/get_agent_templates.py` (line 135) returns `system_instructions` in "full" mode but NOT `user_instructions`. This is the same export gap as the template renderer. Fix this too -- add `user_instructions` to the "full" detail response.

### Key Source Files

| File | Role in Pipeline |
|---|---|
| `src/giljo_mcp/template_seeder.py` | Seeds default templates into DB. Composes `system_instructions` from protocol helper functions. |
| `src/giljo_mcp/template_renderer.py` | `render_claude_agent()` -- produces `.md` file content from `AgentTemplate` model. |
| `src/giljo_mcp/models/templates.py` | `AgentTemplate` SQLAlchemy model with `system_instructions`, `user_instructions`, `behavioral_rules`, `success_criteria`. |
| `src/giljo_mcp/services/protocol_builder.py` | `_generate_agent_protocol()` -- 5-phase lifecycle protocol returned as `full_protocol`. `_generate_team_context_header()` -- team context for mission. |
| `src/giljo_mcp/services/orchestration_service.py` | `spawn_agent_job()` -- creates jobs + thin prompt. `get_agent_mission()` -- returns `mission` + `full_protocol`. `_resolve_spawn_template()` -- multi-terminal template injection. |
| `src/giljo_mcp/thin_prompt_generator.py` | Generates staging/implementation prompts. Orchestrator framing. |
| `api/endpoints/downloads.py` | ZIP download endpoint. |
| `api/endpoints/claude_export.py` | Filesystem export endpoint (has its own inline frontmatter generator). |
| `src/giljo_mcp/file_staging.py` | Token-based download staging. |

### Analysis Documents

| Document | Location |
|---|---|
| Multi-CLI maturity audit | `handovers/Subagent_CLLItool_maturity.md` |
| Integration analysis | `handovers/agent_analysis.md` |

---

## Implementation Plan

### Phase 1: Write Better Agent Role Definitions

Rewrite `user_instructions` for all 6 default templates in `_get_default_templates_v103()` (or create a v104). Each role should have rich, distinctive identity prose -- not just 4 bullet points. The role prose should convey the agent's expertise, judgment, priorities, and working style.

**Roles to write:**

1. **Orchestrator** -- Project coordinator who plans missions, decomposes work into agent jobs, monitors progress, handles blockers, and drives completion. Emphasis on planning discipline, delegation judgment, and quality gates.

2. **Implementer** -- Production code specialist. Emphasis on clean architecture, cross-platform compatibility, pathlib for file ops, error handling, and leaving codebase cleaner than found. Follows project coding standards. TDD where appropriate.

3. **Analyzer** -- Requirements and technical planning specialist. Breaks down vague requirements into actionable tasks. Identifies dependencies, edge cases, and cross-platform implications early. Plans for testability. Tasks should be < 1 day of work.

4. **Reviewer** -- Code review and quality assurance specialist. Constructive not critical. Focuses on significant issues (bugs, security, architecture) over style. Explains the "why" behind feedback. Approves when good enough rather than pursuing perfection.

5. **Tester** -- Test coverage and quality specialist. Tests behavior not implementation. Uses descriptive test names. Mocks external dependencies. Keeps tests deterministic with clear failure messages. Targets coverage >= 80%.

6. **Documenter** -- Documentation specialist. Writes for future developers. Uses clear, concise language. Includes code examples. Keeps docs in sync with feature work. No stale information.

**Each `user_instructions` should be 200-400 words of distinctive role prose, not generic bullet points.** The behavioral rules and success criteria can stay as separate JSON fields.

### Phase 2: Restructure `system_instructions` Content

**Current state:** `system_instructions` contains all protocol sections (~90 lines of MCP tool usage, check-in, messaging, context requesting, agent guidelines, blocker handling).

**Target state:** `system_instructions` becomes a lightweight MCP bootstrap (~5-10 lines):

```markdown
## GiljoAI MCP Agent

You are part of a GiljoAI MCP orchestration system. MCP tools are available as native
tool calls prefixed `mcp__giljo-mcp__*` in your tool list.

### STARTUP (MANDATORY)
1. Call `mcp__giljo-mcp__health_check()` to verify MCP connectivity
2. Call `mcp__giljo-mcp__get_agent_mission(job_id="<your_job_id>")` to receive:
   - Your full operating protocols (`full_protocol`)
   - Your work order and team context (`mission`)
3. Follow `full_protocol` for all lifecycle behavior

Do not begin work until you have received and read your mission and protocols.
```

**Files to modify:**

- `template_seeder.py`:
  - Update `seed_tenant_templates()` to use new slim `system_instructions`
  - Keep all protocol helper functions (`_get_mcp_coordination_section()`, etc.) -- they are still needed by `refresh_tenant_template_instructions()` and may be referenced elsewhere. BUT if they are only used for building `system_instructions`, they can be replaced with the new bootstrap content.
  - Update `refresh_tenant_template_instructions()` to regenerate the new slim format
  - Write new `user_instructions` for all 6 templates (Phase 1 content)

- **Do NOT delete protocol builder functions** in `protocol_builder.py` -- those power the `full_protocol` delivery via `get_agent_mission()` which is the correct home for protocols.

### Phase 3: Fix the Export Pipeline

**Goal:** Exported `.md` files should contain role identity + bootstrap, not protocol boilerplate.

**`template_renderer.py` -- `render_claude_agent()`:**

Currently composes: `frontmatter + system_instructions + behavioral_rules + success_criteria`

Change to: `frontmatter + system_instructions (now slim bootstrap) + user_instructions (role prose) + behavioral_rules + success_criteria`

```python
def render_claude_agent(template: AgentTemplate) -> str:
    # ... frontmatter generation (unchanged) ...

    parts: list[str] = []

    # Slim bootstrap (system_instructions -- now ~5-10 lines)
    bootstrap = (template.system_instructions or "").strip()
    if bootstrap:
        parts.append(bootstrap)

    # Role identity prose (user_instructions -- now included!)
    role_prose = (template.user_instructions or "").strip()
    if role_prose:
        parts.append(f"\n{role_prose}")

    # Behavioral Rules
    rules = template.behavioral_rules or []
    if isinstance(rules, list) and rules:
        parts.append("\n## Behavioral Rules")
        parts.extend(f"- {r}" for r in rules)

    # Success Criteria
    criteria = template.success_criteria or []
    if isinstance(criteria, list) and criteria:
        parts.append("\n## Success Criteria")
        parts.extend(f"- {c}" for c in criteria)

    body_text = "\n".join(parts).rstrip() + "\n"
    return f"---\n{yaml_header}\n---\n\n{body_text}"
```

**`claude_export.py` -- filesystem export endpoint:**

This has its own inline composition logic. Update to match the same pattern: bootstrap + user_instructions + behavioral_rules + success_criteria.

**`file_staging.py`:**

Uses `template_renderer.render_claude_agent()` -- no changes needed once renderer is fixed.

### Phase 4: Verify Multi-Terminal Template Injection

In `orchestration_service.py`, `_resolve_spawn_template()` (line 804) concatenates `system_instructions + "\n\n" + user_instructions` for multi-terminal mode injection. After this refactor:
- `system_instructions` = slim bootstrap (~10 lines)
- `user_instructions` = rich role prose (~200-400 words)

This concatenation still works, but verify the result reads well. The injected template content wraps the mission as "AGENT EXPERTISE & PROTOCOL / YOUR ASSIGNED WORK". After this refactor, the "EXPERTISE & PROTOCOL" section will be role-focused (correct) rather than protocol-heavy (current).

**Test both paths explicitly:**
1. **Multi-terminal path**: Call `spawn_agent_job()` with a project in `multi_terminal` mode. Verify `AgentJob.mission` contains the template bootstrap + role prose baked into the `AGENT EXPERTISE & PROTOCOL` section, NOT 90 lines of protocol.
2. **Claude Code CLI path**: Call `spawn_agent_job()` with a project in `claude_code_cli` mode. Verify `AgentJob.mission` is the raw work order with NO template injection (unchanged behavior).

### Phase 4b: Fix `get_agent_templates` Context Tool

In `src/giljo_mcp/tools/context_tools/get_agent_templates.py`, the "full" detail mode (line 129-143) returns `system_instructions` but not `user_instructions`. Add `user_instructions` to the "full" response dict:

```python
# In the "full" branch:
template_dict = {
    "name": template.name,
    "role": template.role or "Specialized agent",
    "description": template.description,
    "system_instructions": template.system_instructions,
    "user_instructions": template.user_instructions,  # ADD THIS
    "behavioral_rules": template.behavioral_rules,     # ADD THIS
    "success_criteria": template.success_criteria,     # ADD THIS
    # ... existing fields ...
}
```

### Phase 5: Verify `get_agent_mission()` Delivers Complete Protocols

Confirm that `_generate_agent_protocol()` in `protocol_builder.py` covers everything that was previously in `system_instructions`:

| Previously in system_instructions | Now covered by full_protocol? |
|---|---|
| MCP tool usage (native calls, not curl) | Verify -- may need to add if not present |
| Agent guidelines (follow mission, report progress) | Yes -- Phase 1 STARTUP |
| If Blocked or Unclear (report_error, send BLOCKER) | Yes -- Phase 5 ERROR HANDLING |
| Requesting broader context (send_message to orchestrator) | Verify -- may need to add |
| Check-in protocol (natural breaks, not timer-based) | Yes -- Phase 3 PROGRESS REPORTING |
| Messaging prefixes (BLOCKER, PROGRESS, COMPLETE, READY) | Verify -- may need to add |

**If any protocol content is NOT in `full_protocol`, add it to `_generate_agent_protocol()`.** This is the single source of truth for operating protocols.

### Phase 6: Test End-to-End

1. **Seed fresh templates:** Run the updated seeder against a test tenant. Verify `system_instructions` is slim bootstrap, `user_instructions` is rich role prose.

2. **Export templates:** Hit the ZIP download endpoint. Verify exported `.md` files are ~30-50 lines (bootstrap + role + rules + criteria), not ~108 lines of boilerplate.

3. **Compare exported template structure:**
   ```
   Expected .md structure:
   ---
   name: implementer
   description: Implementation specialist for writing production-grade code
   model: sonnet
   color: blue
   ---

   ## GiljoAI MCP Agent
   [5-10 line bootstrap]

   [200-400 words of role identity prose from user_instructions]

   ## Behavioral Rules
   - [4-6 role-specific bullets]

   ## Success Criteria
   - [4-6 role-specific bullets]
   ```

4. **Test agent lifecycle:** Spawn an agent job, call `get_agent_mission()`, verify `full_protocol` contains complete 5-phase lifecycle with all protocol sections. Verify `mission` contains team context + work order.

5. **Test multi-terminal mode:** Verify `_resolve_spawn_template()` produces clean "AGENT EXPERTISE & PROTOCOL" framing with role content (not protocol boilerplate).

6. **Run existing tests:** All tests in `tests/` must pass. Pay special attention to:
   - Template-related tests
   - Export/download tests
   - Agent mission/protocol tests
   - Orchestration service tests

---

## Testing Requirements

**Unit Tests (new or updated):**
- Test `render_claude_agent()` includes `user_instructions` in output
- Test `render_claude_agent()` output does NOT contain old protocol sections (MCP Tool Usage, CHECK-IN PROTOCOL, MESSAGING, etc.)
- Test `seed_tenant_templates()` produces slim `system_instructions`
- Test `refresh_tenant_template_instructions()` regenerates slim format
- Test `_resolve_spawn_template()` concatenation with new content structure

**Integration Tests:**
- Test full export pipeline: seed → export → verify `.md` content
- Test agent mission pipeline: spawn → `get_agent_mission()` → verify `full_protocol` completeness
- Test that agents receive protocols they need (nothing lost from the separation)

---

## Success Criteria

- [ ] Exported `.md` files are 30-50 lines of role-focused content (not 108 lines of boilerplate)
- [ ] `user_instructions` (role prose) appears in exported files
- [ ] Protocol sections (MCP tool usage, check-in, messaging, etc.) do NOT appear in exported files
- [ ] `full_protocol` from `get_agent_mission()` contains complete operating protocols (nothing lost)
- [ ] All 6 default templates have rich, distinctive role definitions (200-400 words each)
- [ ] **Multi-terminal mode**: `_resolve_spawn_template()` bakes slim bootstrap + rich role prose into mission (NOT 90 lines of protocol)
- [ ] **Claude Code CLI mode**: Template injection still skipped (unchanged behavior)
- [ ] **Both modes**: Agent receives `full_protocol` via `get_agent_mission()` with complete 5-phase lifecycle
- [ ] `get_agent_templates` context tool includes `user_instructions` in "full" detail mode
- [ ] All existing tests pass
- [ ] New tests cover the separation boundary for both execution modes

## Rollback Plan

The feature branch isolates all changes. If issues arise:
```bash
git checkout master
```

Template changes affect the seeder (new tenants) and `refresh_tenant_template_instructions()` (existing tenants). The refresh function is idempotent -- running it again with corrected content restores templates.

---

## Dependencies and Blockers

**No external dependencies.** All changes are within existing services and models. No schema migration needed (we're changing the _content_ of existing fields, not the fields themselves).

**Potential concern:** Existing tenants have the old `system_instructions` content. After deploying, `refresh_tenant_template_instructions()` must be called (it runs during startup/install) to update existing templates to the slim format.

---

## Recommended Sub-Agents

- **tdd-implementor** -- For writing tests first, then implementing Phase 2-3 changes
- **backend-tester** -- For end-to-end verification of the full pipeline (Phase 6)

---

## Additional Resources

- `handovers/agent_analysis.md` -- Full analysis with findings, architecture recommendation, and multi-CLI strategy context
- `handovers/Subagent_CLLItool_maturity.md` -- CLI tool comparison (Codex/Gemini/Claude Code) that motivates the portability goal
- `handovers/Reference_docs/QUICK_LAUNCH.txt` -- Pre-implementation reading
- `handovers/Reference_docs/AGENT_FLOW_SUMMARY.md` -- Pre-implementation reading
