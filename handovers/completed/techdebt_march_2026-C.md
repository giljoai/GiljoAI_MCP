# Technical Debt - March 2026

**Purpose**: Actionable technical debt and implementation gaps for CE launch readiness.
**Replaces**: TECHNICAL_DEBT_v2.md (deleted - 2720 lines of mostly obsolete content)
**Last Audit**: 2026-03-12 (cross-referenced git history + codebase exploration)

---

## Post-CE / Future Roadmap (Not Blocking Launch)

These are recorded for future reference but should NOT delay CE launch.

| Item | Notes |
|------|-------|
| **Dashboard Scope Selector** | Per-product/project filtering of dashboard stats. |
| **Per-Agent Tool Selection UI** | Dropdown to select Claude/Codex/Gemini per agent. Only relevant when multi-tool ships. CE is Claude-only. |
| **Mission Launch Summary** | Preview mission plan before execution. Nice UX polish. |
| **Orchestrator Message Loop Automation** | Auto-polling toggle for message coordination during runs. Manual works. |
| **Local LLM Stack Recommendation** | LM Studio integration for privacy-preserving tech stack suggestions. 16-20h. Cool idea, not core. |
| **Developer Workflow Guide** | End-to-end documentation + quick start tutorial. Important but separate workstream. |
| **Codex MCP Integration** | OpenAI Codex as alternative agent tool. UI stubs exist (CodexConfigModal.vue). No backend. |
| **Gemini MCP Integration** | Google Gemini as agent tool. Enum values exist in models. No implementation. Cross-language (Node.js) complexity. |
| **360 Memory Frontend UI** | GitHubSettingsCard, ProductMemoryPanel, LearningTimeline components. Backend complete (Handovers 0135-0139). |
| **MCP HTTP Tool Catalog Refactoring** | Registry pattern to replace inline JSON schemas. Currently 1096 lines with builder functions. Planned for v4.0. |
| **Model Selection in Template Manager** | AgentTemplate.model field exists in DB but no UI for selecting/updating models per template. |
| **Developer Panel** | Localhost-based read-only panel showing architecture, MCP commands, APIs, dependencies. Aspirational. |

---

## Recently Resolved (Deleted from v2)

For git archaeology purposes, these items were in TECHNICAL_DEBT_v2.md and confirmed resolved:

| Item | Resolution |
|------|-----------|
| Dashboard Agent Monitoring UI | Per-project monitoring fully implemented (`JobsTab.vue`, `agentJobsStore.js`, WebSocket routing, full test coverage). Global dashboard view dropped by design -- not needed for CE. |
| Orchestrator Launch UI Workflow | Fully implemented as thin-client copy-paste architecture (Handover 0088). Stage/Implement/Agent prompts auto-copied to clipboard via `ProjectTabs.vue` and `JobsTab.vue`. Deliberate design -- no automated terminal launch needed. |
| Enhanced Agent Cards | Jobs tab (`JobsTab.vue`) already shows per-agent status, duration, steps, messages, execution order, and actions within project context. No separate Agents view exists or is needed -- the Jobs tab IS the agent monitoring view. |
| Project-Product Association UI | Active product pattern fully handles this. `ActiveProductDisplay.vue` shows current product in AppBar, "New Project" button disabled without active product, `product_id` auto-sent from `activeProduct.value.id` on creation, projects view filters by active product. No dropdown needed. |
| Implementation Phase Gate | `implementation_launched_at` field added. Handover 0487 complete. |
| Duplicate Orchestrator Creation | `_ensure_orchestrator_fixture()` uses exclusion-based filter. Handover 0485. |
| Frontend API Pattern Debt | OrchestratorCard.vue, TemplateArchive.vue migrated to namespaced API. Handover 0396. |
| v-window Theme Inheritance | Fixed globally with `global-tabs-window` CSS class in `global-tabs.scss`. |
| MCP Slash Commands | Resolved with different pattern (MCP tools returning instructions instead of `.claude/commands/` files). |
| Serena Advanced Settings | Intentionally removed per Handover 0277. Simple boolean toggle retained. |
| Orchestrator Self-Counting | Agent discovery returns templates not instances. Design change resolved the issue. |
| Task-Agent Execution Integration | Dead schema removed (Handover 0812). Column, FK, and indexes dropped. |
| Agent Behavior Customization | Resolved by design. The "Role & Expertise" field (`user_instructions`) in Template Manager is the behavioral customization mechanism -- it flows through to agent missions at runtime via `_resolve_spawn_template()`. The separate `behavioral_rules` JSON column was a planned structured alternative that was never wired up and is now dead weight (all defaults empty, no UI editor, no runtime injection). `get_behavioral_rules()` method referenced in old docs was removed during template adapter migration. |
| MCP Agent Coordination Tools | Resolved. Full audit (2026-03-12) found 21 MCP tools registered via `tool_map` in `mcp_http.py`, covering the complete agent coordination lifecycle: spawn, mission, progress, messaging, completion, error reporting, workflow status, context, and memory. The original Handover 0060 (7 REST-wrapping tools) was completed Oct 2025 then superseded -- its code was deleted in 0420b (Jan 2026), replaced by the `ToolAccessor` -> service class architecture. The `agent_coordination.py` file with `spawn_agent()` and `get_team_agents()` is vestigial dead code (not in tool_map, not imported by production code). No operational gaps exist. |

---

**Next review**: All actionable tech debt resolved. Only Post-CE roadmap items remain (non-blocking).
