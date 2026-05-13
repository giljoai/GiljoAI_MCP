---
description: "Look up projects and tasks in the GiljoAI dashboard. Read-only — use /gil_add to create or update."
---

# /gil_get — Look up projects and tasks in GiljoAI dashboard

## Routing

Route by what the user wants to read:

- **Project reads** — user says "read project", "show project", "look up project", "fetch context for ...", or pastes one or more project UUIDs → Project read mode below
- **Task reads** — user says "read task", "show tasks", "what tasks are open", "tasks due before X", or pastes bare task UUIDs → Task read mode below
- **Cross-cutting** — user says "show me everything BE" or similar (type prefix across both tables) → parallel project + task read

---

## Project read mode

**Triggers** — route here when the user says any of these, or pastes one or more UUIDs with little surrounding text:
- "read project", "read projects"
- "show project", "show projects"
- "look up project", "look up projects"
- "fetch context for ..."
- A bare list of project UUIDs

**GOTCHA:** the project identifier field is **`project_id`**, NOT `id`. Filtering on `.id` returns nothing. Always use `.project_id` in jq filters.

**IDs you already have:** `tenant_key` is auto-injected from auth. `product_id` is in your session context the moment any tool response surfaces it (most tool responses include it). You only need `project_id` — get it from step 1 below or from the user's paste.

**Tool sequence (cheap-first — pick the smallest path that answers the question):**
1. **Find the project_id by name/alias** → `mcp__giljo_mcp__list_projects(summary_only=true)`. Returns ~150 lines of metadata (project_id, name, taxonomy_alias, status, timestamps). Lightweight. Match by `name` or `taxonomy_alias` to grab the project_id.
2. **Read one project deeply** → `mcp__giljo_mcp__fetch_context(product_id=..., project_id=..., categories=["project"])`. Returns ~300 tokens for one project: project_name, project_alias, project_description, orchestrator_mission, status, staging_status. This is the right tool when the user wants description/mission for ONE project.
3. **Bulk read many projects (only if the user pastes multiple UUIDs and needs full fields for all)** → `mcp__giljo_mcp__list_projects(mode="planning")` for description+mission, or `mode="audit"` if memory headlines are also needed. The harness auto-saves the tool result to a file when large. Filter with jq:
   ```bash
   jq '.projects[] | select(.project_id == "UUID-HERE") | {project_id, name, taxonomy_alias, status, description, mission}' /path/to/saved-tool-result.json
   ```

**Modes (preferred over numeric depth):** `triage` (id+name+status+dates), `planning` (+ description, mission, agent counts), `audit` (+ memory headlines + agent summaries), `forensic` (+ full memory bodies, agent results). `mode="forensic"` is the heavy archaeology call — only use it when you actually need full memory bodies.

**Response shapes:**
- `fetch_context(["project"])`: `project_name`, `project_alias`, `project_description`, `orchestrator_mission`, `status`, `staging_status`
- `list_projects` row (`mode="planning"`): `project_id`, `name`, `taxonomy_alias`, `status`, `project_type`, `series_number`, `description`, `mission`, `agent_summary`, `created_at`, `completed_at`

**Worked example:**
> User asks "what's IMP-0019 about?" → call `list_projects(mode="triage")` → match `taxonomy_alias=="IMP-0019"` → grab `project_id` → call `fetch_context(product_id, project_id, ["project"])` → return description + mission. No multi-MB pull.

---

## Task read mode

**Triggers** — route here when the user says any of these, or pastes one or more task UUIDs:
- "read task", "read tasks"
- "show tasks", "show me tasks"
- "what tasks are open", "what's pending"
- "tasks due before X", "tasks with priority high"
- A bare list of task UUIDs

**Tool sequence (cheap-first):**
1. **List tasks with filters** → `mcp__giljo_mcp__list_tasks(mode="summary", task_type=..., filters=...)`. Returns one row per task with: `id`, `title`, `status`, `priority`, `task_type` (embedded block id+abbreviation+label+color), `series_number`, `subseries`, `taxonomy_alias` (e.g. `BE-0017`), `hidden`, `due_date`, `created_at`. Use `mode="summary"` unless the user specifically needs description bodies.
2. **Read a task deeply** → `mcp__giljo_mcp__fetch_context(product_id=..., categories=["tasks"])`. Returns full task bodies with the same taxonomy fields as `list_tasks`. Use when the user wants task descriptions for a project or a filtered set.
3. **Filter parameters** (pass as `filters={}` dict):
   - `status`: `pending` | `in_progress` | `completed` | `blocked` | `cancelled`
   - `priority`: `low` | `medium` | `high` | `critical`
   - `task_type`: taxonomy abbreviation (e.g. `"BE"`, `"FE"`, `"INF"`) — filters to tasks with that type
   - `hidden`: omit by default (returns BOTH hidden and visible — agents see all). Pass `true` to only get hidden tasks; `false` to only get visible ones. The dashboard filters `hidden=false` by default but `/gil_get` does NOT (so agents can still reorder/sort across the full backlog).

**`task_type` vs `mode`:**
- `task_type` filters which tasks are returned (by project-type association)
- `mode="summary"` returns lightweight rows; `mode="full"` returns full description bodies

**Worked example:**
> User asks "what BE tasks are still open?" → call `list_tasks(mode="summary", task_type="BE", filters={"status": "pending"})` → return table of matching tasks. No full-body pull unless user asks for detail.

---

## Cross-cutting mode

**Triggers** — user wants both projects and tasks filtered by type or status in one request:
- "show me everything BE"
- "what's open across FE?"
- "status of all INF work"

**Tool sequence:** run in parallel:
1. `mcp__giljo_mcp__list_projects(project_type="BE", mode="triage")`
2. `mcp__giljo_mcp__list_tasks(mode="summary", task_type="BE", filters={"status": "pending"})`

Present results as two sections: **Projects** and **Tasks**.

---

## Rules

- Never pass `tenant_key` (auto-injected by security layer)
- Active product required (server-side enforced) — if error mentions "No active product", tell user to activate one in dashboard
- This skill is read-only — never call `create_project`, `create_task`, `update_project`, or `update_task` from here; direct writes to `/gil_add`
- On error: show what went wrong and how to fix
