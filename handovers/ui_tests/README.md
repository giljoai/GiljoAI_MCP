# UI Functional Test Suite

**Location:** `handovers/ui_tests/`
**Handover Reference:** 0769-UI (permanent, living documents)
**Created:** 2026-03-30
**Status:** PERMANENT — never closed out, never deleted, modified as the app evolves

---

## Purpose

Reusable browser-based functional test suite for GiljoAI MCP. Covers the complete user journey from product creation through multi-agent orchestration. Execute after major refactors, before releases, or as part of the quality audit process.

## Test Environment

- **URL:** `https://10.1.0.116:7274` (or current dev server)
- **Backend port:** 7272
- **Frontend port:** 7274
- **Protocol:** HTTPS (self-signed cert)
- **Test document:** `C:\Projects\TinyContacts\docs\product_proposal.txt`

## Execution

Can be executed by:
1. **Chrome automation agent** via Claude-in-Chrome MCP tools
2. **Manual tester** following the steps
3. **Orchestrator session** running phases sequentially

## Phases

| Phase | File | Test Area | Creates Data? |
|-------|------|-----------|---------------|
| A | `phase_a_product_creation.md` | Product creation, vision doc upload, chunking | Yes |
| B | `phase_b_project_creation.md` | Project creation from product | Yes |
| C | `phase_c_job_creation.md` | Agent job creation within project | Yes |
| D | `phase_d_task_lifecycle.md` | Task creation + graduation to project | Yes |
| E | `phase_e_user_settings.md` | User settings navigation and config | Read-only |
| F | `phase_f_admin_settings.md` | Admin settings and system config | Read-only |
| G | `phase_g_context_settings.md` | User context depth and tuning | Settings changes |
| H | `phase_h_project_launch.md` | Project launch with context verification | Light launch (1 agent) |
| I | `phase_i_agent_management.md` | Agent templates, on/off, constellation | Config changes |
| J | `phase_j_orchestration_modes.md` | Multi-terminal + subagent mode staging | Light launch (1 agent) |

## Error Protocol

- If a phase reveals a **regression** from a recent sprint: STOP, document, escalate to orchestrator
- If a phase reveals a **pre-existing issue**: document and continue
- If a page **fails to load or crashes**: check ports, ask user before force-stopping anything
- **Never enter passwords** — user logs in manually, then agent takes over
- **Keep projects light** — max 1 agent, in-and-out, don't accumulate test data

## Cleanup

After testing, delete any test products/projects created during the run (unless the user wants them kept for further testing).
