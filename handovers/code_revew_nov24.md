# GiljoAI Codebase Health Review — Nov 24, 2025

Overall stance: **Improving**. The biggest leaps are frontend decomposition and service-layer compliance. The remaining red flag is the lingering legacy agent spawn path; integration registry work is only half-wired.

## Scorecard (Nov 18 → Nov 24)
| Area | Prev | Now | Trend |
| --- | --- | --- | --- |
| User Settings | 82 | 88 | ▲ |
| Admin/System Settings | 78 | 86 | ▲ |
| Tasks | 80 | 80 | ▬ |
| Products | 88 | 92 | ▲ |
| Projects | 88 | 89 | ▲ |
| Jobs/Agents/Orchestration | 72 | 74 | ▲ (legacy still active) |
| Context/Vision/Chunking | 88 | 88 | ▬ |
| Integrations | 70 | 73 | ▲ (registry added but unused) |
| Multi-tenancy | 88 | 88 | ▬ |
| Overall Architecture | 80–83 | 84–86 | ▲ |

## What Improved
- **Frontend decomposition landed**:  
  - `ProductsView.vue` shrank from ~2,582 lines to 1,233 with extracted components (`frontend/src/components/products/*`), including `ProductForm.vue` (895 lines), `ProductVisionPanel.vue` (233), and dialog components.  
  - `UserSettings.vue` is 553 lines (was ~1,404) with integrations moved to dedicated cards under `frontend/src/components/settings/integrations`.  
  - `SystemSettings.vue` is 268 lines (was ~1,420) and delegates to tab components (`frontend/src/components/settings/tabs/*`).  
  - `ProjectsView.vue` trimmed to 893 lines (down from ~1,018).
- **Service-layer discipline**: `api/endpoints/users.py` now consistently injects `UserService` (see dependency uses around line 292 onward), removing prior direct SQL accesses.
- **Orchestration tool hardening**: `spawn_agent_job` in `src/giljo_mcp/tools/orchestration.py` now blocks duplicate orchestrators and broadcasts via HTTP bridge with strong test coverage (`tests/tools/test_orchestration_duplicate_prevention.py`, `tests/integration/test_agent_card_realtime.py`, etc.).
- **Integration registry created**: `frontend/src/integrations/registry.ts` centralizes integration metadata (ids, icons, components) for future dynamic rendering.

## Regressions / Risks
1) **Legacy agent spawn path still live (highest risk)**  
   - `_spawn_generic_agent` remains and is still called as the fallback (`src/giljo_mcp/orchestrator.py:470` and fallback at `:1144`). There is no telemetry or kill-switch; legacy Codex/Gemini path continues to operate by default if no template is found. Action: instrument usage and plan removal window.

2) **Integration registry not wired to UI**  
   - Despite `frontend/src/integrations/registry.ts`, `frontend/src/views/UserSettings.vue` still manually renders `McpIntegrationCard`, `SerenaIntegrationCard`, `GitIntegrationCard` (around lines 269–293) and maintains separate state handlers. System settings also hand-codes integration descriptions. Action: render integrations from the registry to avoid drift.

3) **Product form still monolithic and untested**  
   - `frontend/src/components/products/ProductForm.vue` is 895 lines; no unit tests mention `ProductForm` (`frontend/tests` search is empty). Action: add unit tests for validation/save flows and continue breaking the form into smaller subcomponents (tabs/dialogs).

4) **Potential tenant blind spot in spawn path**  
   - `ProjectOrchestrator.spawn_agent` loads `Project` by id only (no tenant filter) before spawning (`src/giljo_mcp/orchestrator.py:1078`). If exposed across tenants, this could allow cross-tenant access by id guessing. Confirm caller context and add tenant scoping or authorization guard.

5) **Nested Serena repo adds surface area**  
   - New `serena/` directory is a full git repo with Docker/flake configs. Verify it is intentionally vendored and excluded from packaging/build steps to avoid accidental deployment or lint noise.

## Recommendations (priority order)
1. Add telemetry/log assertions around `_spawn_generic_agent` calls and set a removal deadline; consider hard-failing when templates are missing once telemetry proves unused.  
2. Wire `frontend/src/views/UserSettings.vue` and `AdminIntegrationsTab.vue` to `INTEGRATIONS` registry for rendering and state, then delete duplicated card definitions.  
3. ProductForm split plan (caution: keep field priority mappings intact):  
   - Extract tab components: Basic, Vision, Tech Stack, Architecture, Features/Testing; keep the product data schema and field paths unchanged.  
   - Each tab imports `useFieldPriority` so priority chips still read `settingsStore.fieldPriorityConfig` (My Settings → Context tab).  
   - Add unit tests per tab to assert priority chips render when `fieldPriorityConfig` is mocked and that save payload/vision files emit unchanged.  
4. Tighten tenant scoping in `spawn_agent` (project lookup + authorization) or document why the current path is safe.  
5. Keep service-layer enforcement: new endpoints should follow the UserService/TaskService pattern; flag direct ORM usage in reviews.  
6. Confirm the vendored `serena/` repo is intentional; add `.gitignore`/packaging guards if it should stay dev-only (now ignored).

## Testing Notes
- Orchestration MCP toolchain is well-covered (spawn_agent_job duplicate prevention, HTTP bridge, thin prompts).  
- No new frontend unit tests observed for extracted product/settings components—add them alongside refactors.

## TL;DR
- **Good**: Frontend files are finally decomposed; service-layer consistency improved; orchestration tools have strong tests.  
- **Bad**: Legacy agent spawn path still runs; integration registry not actually used; product form mega-component lacks tests; spawn_agent may ignore tenant scoping.  
- **Next**: Instrument and retire legacy spawn, drive UI off the registry, test/split product form, and lock tenant scoping.
