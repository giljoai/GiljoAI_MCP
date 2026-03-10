# Technical Debt - March 2026

**Purpose**: Actionable technical debt and implementation gaps for CE launch readiness.
**Replaces**: TECHNICAL_DEBT_v2.md (deleted - 2720 lines of mostly obsolete content)
**Last Audit**: 2026-03-09 (cross-referenced git history + codebase exploration)

---

## Partially Complete Items

These have some implementation but gaps remain.

---

### 1. Task-Agent Execution Integration

**Priority**: MEDIUM-HIGH
**Effort**: ~8 hours (reduced from original 16h estimate - schema work is done)
**Dependencies**: None

**What's done**:
- Task model has `job_id` FK to MCPAgentJob (added in Handover 0381)
- Indexed with `idx_task_job` and `idx_task_tenant_job`
- 10 MCP tools for task CRUD exist

**What's missing**:
- No `execute_task_with_agent()` MCP tool - can't assign a task and auto-spawn a job
- No `orchestrate_from_product_tasks()` - can't orchestrate from task list
- No background status sync between jobs and tasks (job completes, task stays `in_progress`)
- No REST endpoints for task execution (`POST /tasks/{id}/execute`)

**The gap**: Tasks and agent jobs are linked in the schema but disconnected in workflow. Users create tasks, manually spawn jobs, and manually update task status. The FK exists but nothing automates the lifecycle.

---

### 2. MCP Agent Coordination Tools

**Priority**: MEDIUM
**Effort**: 2-4 hours to verify completeness

**What's done**:
- `src/giljo_mcp/tools/agent_coordination.py` exists with `spawn_agent()` and `get_team_agents()`

**What needs verification**:
- Original plan called for 7 tools wrapping REST API endpoints. Only 2 confirmed.
- No handover (0060) was ever created, so there's no completion record.
- Need to verify: can external agents (Claude Code, Codex) fully coordinate through MCP tools? Or are there gaps in the tool surface?

**Action**: Quick audit of which coordination operations are exposed as MCP tools vs only available via REST API.

---

### 3. Agent Behavior Customization

**Priority**: LOW-MEDIUM
**Effort**: 6-8 hours

**What's done**:
- `AgentTemplate.behavioral_rules` (JSON column) exists in DB
- `template_manager.get_behavioral_rules()` method exists
- TemplateManager.vue has UI for editing behavioral_rules at template level

**What's missing**:
- No per-agent `behavior_philosophy` field (only template-level rules exist)
- No runtime injection of behavioral rules into agent missions
- No agent edit form for individual behavior customization

**The gap**: You can define rules at the template level but they don't flow through to mission prompts at runtime. And individual agents can't override template defaults.

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

---

**Next review**: When Items 1-3 are revisited for priority.
