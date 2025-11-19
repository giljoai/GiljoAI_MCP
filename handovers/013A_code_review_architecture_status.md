# GiljoAI Codebase Architecture Status – November 16, 2025

This report summarizes the current state of the GiljoAI MCP codebase after the recent refactors (including the `0601_nuclear_reset_test_report.md`) and provides concrete next steps that are realistic for a **single developer**.

The focus areas are:

- User Settings (My Settings)
- Admin/System Settings
- Tasks
- Products
- Projects
- Jobs / Agents / Orchestration
- Context / Vision / Integrations
- Multi-tenancy

---

## 1. High-Level Health Snapshot

These scores are subjective but grounded in the current structure, tests, and presence of legacy code paths.

- **User Settings (My Settings)**: ~85/100  
- **Admin/System Settings**: ~80/100  
- **Tasks**: ~80/100  
- **Products**: ~90/100  
- **Projects**: ~85/100  
- **Jobs / Agents / Orchestration**: ~75/100  
- **Context / Vision / Chunking**: ~80/100  
- **Integrations (User-level & System-level)**: ~70/100  
- **Multi-tenancy (overall)**: ~85/100  
- **Overall architecture**: ~82–85/100  

In simple terms: this is a **mature V2 codebase** with explicit legacy seams. Most of the remaining work is **clean-up and simplification**, not rebuilding.

---

## 2. Area-by-Area Summary (Plain Language)

### 2.1 User Settings (My Settings)

- File: `frontend/src/views/UserSettings.vue`
- Tests: `frontend/tests/unit/views/UserSettings.spec.js`

**What’s good**

- Clear tab structure: General, Appearance, Notifications, Templates, API & Integrations.
- Integrations tab collects: MCP integration wizard, Slash Commands, Claude Code export, Serena, and now GitHub (placeholder).
- Serena integration has a proper toggle + advanced dialog, with backend wiring through `setupService`.
- Tests verify that My Settings renders, the tabs exist, and integrations content is present.

**What could be improved (future)**

- The file is large and contains both UI and logic (e.g., Serena advanced config, field priority configuration). Over time, you can move chunks into smaller components or composables.

**Risk level**: Low. This is well into “V2” territory.

---

### 2.2 Admin / System Settings

- File: `frontend/src/views/SystemSettings.vue`
- Tests: `frontend/tests/unit/views/SystemSettings*.spec.js`, API tests for config and settings.

**What’s good**

- Tabs for Database, Network, Integrations, Security, Users, etc. Each tab has a clear purpose.
- Database & Network tabs fetch configuration from `/api/v1/config` and `/api/v1/config/database` with proper handling.
- Security tab manages cookie domains with a clean API (`/api/settings/cookie-domains`).

**What could be improved**

- System Integrations currently mostly documents Serena. That’s fine, but it is not a full “integration manager” yet.
- The view is large. As with UserSettings, this is a “later” refactor task.

**Risk level**: Low–medium, purely because of size, not because of hacks.

---

### 2.3 Tasks

- Backend: `api/endpoints/tasks.py`, `src/giljo_mcp/services/task_service.py`
- Frontend: `frontend/src/views/TasksView.vue`
- Tests: `tests/api/test_tasks_api.py`

**What’s good**

- Backend uses a clear service (`TaskService`) and Pydantic models.
- Endpoints cover list/create/get/update/delete + conversion to project, with `can_modify_task` / `can_delete_task` helpers.
- Frontend TasksView uses Pinia stores and distinct dialogs for create/edit/convert/delete.

**What could be improved**

- TasksView is fairly large (table, filters, dialogs). Over time you can extract the table and dialogs into their own components.

**Risk level**: Low. There is no obvious mixed V0/V1 logic here.

---

### 2.4 Products

- Backend: `src/giljo_mcp/services/product_service.py`, `api/endpoints/products/*`
- Models: `src/giljo_mcp/models/products.py`, `src/giljo_mcp/models/context.py`
- Frontend: `frontend/src/views/ProductsView.vue`, `frontend/src/stores/products.js`
- Tests: `tests/api/test_products_api.py`, plus vision/context tests.

**What’s good**

- ProductService is fully service-layer based: create, get, list, update, activate/deactivate, delete/restore, cascade impact, and vision upload.
- Vision documents and context chunks use modern models (`VisionDocument`, `MCPContextIndex`) with multi-document, multi-tenant, chunked storage.
- Tests verify:
  - Product CRUD.
  - Multi-tenant isolation.
  - Vision upload and chunking.
  - config_data persistence (including tech_stack) on create and update.
- Frontend ProductsView is powerful:
  - Multi-tab wizard for Basic, Vision, Tech Stack, Architecture, Features & Testing.
  - Auto-save with localStorage.
  - Vision upload and chunk display.
  - Cascade impact and product activation.

**What could be improved**

- ProductsView.vue is very large. Over time, break into smaller components (e.g., `ProductForm.vue`, `ProductVisionPanel.vue`, `ProductDeleteDialog.vue`, etc.). This is structural, not urgent.

**Risk level**: Low. This is one of the cleanest areas in the codebase.

---

### 2.5 Projects

- Backend: `src/giljo_mcp/services/project_service.py`, `api/endpoints/projects/*`
- Frontend: `frontend/src/views/ProjectsView.vue`, `frontend/src/views/ProjectLaunchView.vue`
- Docs: `frontend/src/views/PROJECTS_VIEW_README.md`
- Tests: `tests/api/test_projects_api.py`, plus staged status tests.

**What’s good**

- ProjectService encapsulates complex flows (creation, staged status, launch, activation, metrics) rather than spreading logic across endpoints.
- ProjectsView is well-documented and aligned with the README.
- Tests cover a lot of project behavior, including staged status and cascade impact with tasks.

**What could be improved**

- As with Products, ProjectsView is large and would benefit from componentization over time.

**Risk level**: Low–medium mostly due to complexity of the domain, not code quality.

---

### 2.6 Jobs / Agents / Orchestration

- Backend: `src/giljo_mcp/orchestrator.py`, `src/giljo_mcp/services/orchestration_service.py`, `api/endpoints/agent_jobs/*`, `api/endpoints/agent_management.py`
- Tests: `tests/api/test_agent_jobs_api.py`, reliability/performance tests, handover docs.

**What’s good**

- There is a clear “new” orchestration flow using Mission templates and a structured job model.
- `orchestration_service.py` and `agent_job_manager.py` are strongly typed and aware of tenant isolation.

**Where the legacy paths live (this is the important part)**

- `src/giljo_mcp/orchestrator.py` explicitly contains legacy logic:
  - `_spawn_generic_agent(...)` and comments like “Spawn legacy agent (Codex/Gemini with job queue).”
  - Fallbacks: “logger.info('[spawn_agent] No template found for {role.value}, using legacy spawn logic')”
  - Defaulting to `mode="claude"` for legacy agents in some paths.

These legacy paths exist so that older “Codex/Gemini”-style flows or older prompt templates can still work. They are not hacks; they are intentional compatibility shims.

**What “Finish decommissioning legacy paths” actually means for you**

Because you’re a single dev, think of this in **phases**:

1. **Identify any real usage of legacy paths:**
   - Search for `_spawn_generic_agent(` in the codebase (`src/giljo_mcp/orchestrator.py`).
   - Look at where `_spawn_generic_agent` is called (e.g., when no template is found, or when a particular agent mode is requested).
   - Check your **templates** and **UI flows**:
     - Are you still referencing old “Codex/Gemini” agents anywhere (in `handovers`, templates, or UI)?
     - Are there any CLI tools or older scripts that call these endpoints expecting legacy behavior?

2. **Decide on a cutover date / version:**
   - Once you are confident nothing in your current workflows uses those legacy agent modes, you can:
     - Replace `_spawn_generic_agent` with a clearer “unsupported” error, **or**
     - Remove it entirely and simplify `spawn_agent` to use only the modern orchestration paths.

3. **Document the removal:**
   - Add a short note in `HANDOVER_INSTRUCTIONS.md` or a new handover that says:
     - “As of version X, legacy agent spawning via `_spawn_generic_agent` is removed. All agents must use the template-based orchestration flow.”

There is no external “installation” to scan; this is about your **own** code paths and any scripts/handovers that might assume the old behavior. The safest method is:

- Temporarily log or raise a warning if `_spawn_generic_agent` is ever called in your test and dev sessions. If you never see it triggered, it’s safe to remove later.

---

### 2.7 Context / Vision / Chunking

- Models: `src/giljo_mcp/models/context.py`, `src/giljo_mcp/models/products.py` (VisionDocument and MCPContextIndex)
- Chunker: `src/giljo_mcp/context_management/chunker.py`, `src/giljo_mcp/tools/chunking.py`
- Discovery: `src/giljo_mcp/discovery.py`
- Repositories: `src/giljo_mcp/repositories/context_repository.py`, `src/giljo_mcp/repositories/vision_document_repository.py`

**What’s good**

- Clear separation between:
  - Vision document model (per product, per document).
  - Context chunks (MCPContextIndex) used by agents for RAG.
  - Chunking logic (EnhancedChunker) which is non-LLM and token-budget aware.
- Multi-tenant and multi-document support is built-in, not bolted on.

**Legacy / transitional bits**

- `src/giljo_mcp/context_management/context_service.py` still mentions deprecated context discovery and error-returning behavior.
  - This is again a compatibility layer: old API calls might expect the “old” discovery endpoints.

**What to do (practical for one dev)**

- Similar to orchestrator:
  - Identify if any **current UI or tools** still call deprecated context discovery endpoints.
  - If not, you can:
    - Mark them as “deprecated – do not use” in docstrings and eventually remove them.
  - If yes, plan a small migration to the newer context flows, then remove the old ones.

---

### 2.8 Integrations (User & System)

- User-level: `frontend/src/views/UserSettings.vue` (Integrations tab)
- System-level: `frontend/src/views/SystemSettings.vue` (Integrations section)
- Services: `frontend/src/services/setupService.js`, `frontend/src/services/api.js`

**What’s good**

- Serena is a fully wired integration (user-level toggle, advanced settings, backend support).
- Claude Code export and Slash Commands are integrated in a consistent way (cards + components).
- New GitHub placeholder now exists **only** where you wanted it: My Settings → Integrations tab.

**What could be improved – Integration Registry (expanded idea)**

Right now, each integration is hard-coded in the Vue templates. For a single dev, that’s fine, but as you add more integrations, it becomes harder to keep them consistent.

When I said “integration registry”, I **did not** mean a complicated dependency JSON. I meant a simple, centralized **data structure** that describes your integrations, which the UI loops over. For example:

```ts
// frontend/src/integrations/registry.ts
export const INTEGRATIONS = [
  {
    id: 'mcp',
    name: 'MCP Integration',
    kind: 'tooling',
    userConfigComponent: 'AiToolConfigWizard',
  },
  {
    id: 'slash_commands',
    name: 'Slash Commands',
    kind: 'tooling',
    userConfigComponent: 'SlashCommandSetup',
  },
  {
    id: 'claude_code',
    name: 'Claude Code Export',
    kind: 'export',
    userConfigComponent: 'ClaudeCodeExport',
  },
  {
    id: 'serena',
    name: 'Serena MCP',
    kind: 'ai_tool',
    userConfigComponent: 'SerenaIntegrationCard',
  },
  {
    id: 'github',
    name: 'GitHub Integration',
    kind: 'scm',
    userConfigComponent: 'GitHubIntegrationPlaceholder',
  },
]
```

Then in `UserSettings.vue`, instead of manually listing each card, you can write:

```vue
<template v-for="integration in integrations">
  <component
    :is="integration.userConfigComponent"
    :key="integration.id"
  />
</template>
```

This way:

- Adding a new integration becomes “add one entry to the registry + create a component” instead of editing multiple views.
- The registry lives in one place you can inspect to see all integrations.

This is an incremental improvement and **not urgent**. You can adopt it when you feel the integrations list is getting unwieldy.

---

### 2.9 Multi-Tenancy

- Tenant key: `tenant_key` appears consistently in models, repositories, services, and WebSocket code.
- `TenantManager` and `api/dependencies.py` manage current tenant context.
- Tests for multi-tenant isolation exist in most API suites (products, projects, tasks, users).

**State**: Strong. Multi-tenancy feels like a first-class design decision, not an afterthought.

---

## 3. Moving `models.py.original` to an Archive

You asked to move `src/giljo_mcp/models.py.original` out of the active package. This file is already an “archive” of earlier monolithic models, but it lives in a busy folder (`src/giljo_mcp`), which is visually noisy.

I moved it to:

- `handovers/archive/models.py.original`

This keeps it:

- Available if you ever need to reference old model definitions.
- Out of the main `src/giljo_mcp` package so newer contributors and tools don’t confuse it with active code.

If you later decide you never need it, you can delete that archived file entirely.

---

## 4. “Service Layer Only” Endpoints – What That Means for You

You asked: _“what does `service layer only` for remaining endpoints mean, tell me how I should instruct my agent coding tools to adhere to this and what it means.”_

### 4.1 Concept in plain language

- **Service layer only** means: your FastAPI endpoints should be very thin and should **not** contain business logic or direct SQL/ORM operations.

Instead:

1. The endpoint:
   - Parses the request (`request_model: Pydantic`).
   - Gets the current user/tenant via dependencies.
   - Calls a method on a service class, e.g., `ProjectService`, `ProductService`, `TaskService`.
   - Translates the returned dict into a response model.

2. The service class (`...Service`) is the **only place** where:
   - SQLAlchemy sessions and queries are used.
   - Business rules are enforced (status transitions, cascade impacts, validations).
   - Multi-tenant filters, soft-deletes, etc., are handled.

You are already doing this in many places (Products, Projects, Tasks). The recommendation is simply: **continue this pattern and avoid adding new endpoint-level logic**.

### 4.2 How to instruct your agent tools

When using AI/agent tools on this repo, include instructions like:

> “When adding or updating API endpoints under `api/endpoints`, do not write direct database queries or business logic in the endpoint function. Instead, add/extend methods on the appropriate `...Service` under `src/giljo_mcp/services/` and have the endpoint call those service methods. Keep endpoints as thin request/response translators.”

> “If you need a new operation (e.g., a new way to list tasks), create or extend a method on `TaskService` and call it from the endpoint. Do not import SQLAlchemy models directly into the endpoint.”

You can also enforce this mentally by scanning new diffs: if an endpoint uses `Session` or `select()` directly, that’s a smell—move it into the service.

---

## 5. Recommended Next Steps (Prioritized for a Single Developer)

### 5.1 Highest Value, Lowest Risk

1. **Continue “service layer” discipline**
   - Every time you touch an endpoint, check if logic should live in a service instead.
   - This costs almost nothing if you do it as you go.

2. **Keep Products/Projects/Tasks views functionally stable**
   - Don’t start big refactors in these views until you need new features.
   - When you do need a new feature, consider extracting a small, focused child component rather than adding more to the big view.

3. **Keep multi-tenancy front-of-mind**
   - Anytime you add a new model or endpoint, ask:
     - “Does this need a `tenant_key`?”
     - “Is there a service filtering by `tenant_key`?”

### 5.2 Medium Priority

4. **Legacy Orchestrator Paths**
   - Add temporary logging or asserts around `_spawn_generic_agent` and any deprecated context discovery functions.
   - Use your own workflows (TinyContacts, test projects) and see if these are ever hit.
   - If not, plan a version where you remove or hard-fail those paths and simplify the orchestrator.

5. **Integration Registry (small, incremental)**
   - Introduce a simple `INTEGRATIONS` array (as shown above) and gradually migrate My Settings → Integrations to use `<component :is="...">` based on that registry.
   - This can be done integration-by-integration, not all at once.

### 5.3 Longer-Term / “When You Have Time”

6. **Decompose large views**
   - For `ProductsView.vue` and `ProjectsView.vue`, identify natural “chunks”:
     - Product/Project list table.
     - Form panel / wizard.
     - Vision panel.
     - Delete/cascade confirm dialog.
   - Extract one small component at a time, keeping behavior exactly the same.

7. **Retire Remaining Legacy Documentation**
   - Once the legacy orchestrator/context paths are truly unused, update handover docs to reflect the simplified architecture.

---

## 6. Mental Model for You (First Product, Single Dev)

You’ve already:

- Survived a “nuclear reset”.
- Migrated to a clearer service-layer architecture.
- Built multi-tenant aware products/projects/tasks with strong tests.

Going forward, you can think of your responsibilities as:

1. **Guard rails**: Service layer only, multi-tenancy, and clear integration points.
2. **Pruning**: Gradually remove legacy paths once you have evidence they’re unused.
3. **Shaping**: Slowly reshape the largest frontend views into smaller, more digestible components when you touch them for new features.

You do **not** need massive rewrites. The codebase is in good enough shape that incremental, focused cleanups and features will keep improving it without destabilizing everything.

