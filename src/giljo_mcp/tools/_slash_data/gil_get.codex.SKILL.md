---
name: gil-get
description: "Look up projects and tasks in the GiljoAI dashboard. Read-only — use $gil-add to create or update."
---

# $gil-get — Look up projects and tasks in GiljoAI dashboard

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

**GOTCHA:** the project identifier field is `project_id`, NOT `id`. Filtering on `.id` returns nothing. Always use `.project_id` in jq filters.

**IDs you already have:** `tenant_key` is auto-injected from auth. `product_id` is in your session context the moment any tool response surfaces it. You only need `project_id` — get it from step 1 or the user's paste.

**Tool sequence (cheap-first):**
1. **Find the project_id by name/alias** → call `list_projects` with `mode="triage"`. Returns ~150 lines of metadata only.
2. **Read one project deeply** → call `fetch_context` with `product_id`, `project_id`, and `categories=["project"]`. Returns ~300 tokens for one project.
3. **Bulk read many projects** → call `list_projects` with `mode="planning"` for description+mission, or `mode="audit"` for memory headlines. Codex auto-saves large results to a tool-result file. Filter with jq:
   ```
   jq '.projects[] | select(.project_id == "UUID-HERE") | {project_id, name, taxonomy_alias, status, description, mission}' /path/to/saved-tool-result.json
   ```

**Modes:** `triage` (id+name+status+dates), `planning` (+ description, mission, agent counts), `audit` (+ memory headlines), `forensic` (+ full memory bodies). Use `forensic` only when full bodies are genuinely needed.

---

## Task read mode

**Triggers** — route here when the user says any of these, or pastes one or more task UUIDs:
- "read task", "read tasks"
- "show tasks", "show me tasks"
- "what tasks are open", "what's pending"
- "tasks due before X", "tasks with priority high"
- A bare list of task UUIDs

**Tool sequence:**
1. List tasks with filters: `list_tasks` with `mode="summary"`, `task_type=...`, `filters=...`. Returns one row per task with: `id`, `title`, `status`, `priority`, `task_type` (embedded block), `series_number`, `subseries`, `taxonomy_alias` (e.g. `BE-0017`), `hidden`, `due_date`, `created_at`.
2. Read a task deeply: `fetch_context` with `product_id` and `categories=["tasks"]`. Returns full task bodies with the same taxonomy fields.
3. Filter parameters (pass as `filters={}` dict):
   - `status`: pending | in_progress | completed | blocked | cancelled | converted
   - `priority`: low | medium | high | critical
   - `task_type`: taxonomy abbreviation (e.g. `"BE"`, `"FE"`, `"INF"`)
   - `hidden`: true | false — omit by default (returns BOTH; agents see all). Dashboard filters `hidden=false`; `/gil_get` does NOT so agents reorder/sort across the full backlog.

**Menu prompts:** When asking which projects to expand or summary vs full, use `request_user_input` (1-3 questions per call) with structured options. Never plain text.

---

## Cross-cutting mode

**Triggers** — user wants both projects and tasks filtered by type or status in one request:
- "show me everything BE"
- "what's open across FE?"
- "status of all INF work"

**Tool sequence:** run in parallel:
1. `list_projects` with `project_type="BE"` and `mode="triage"`
2. `list_tasks` with `mode="summary"`, `task_type="BE"`, `filters={"status": "pending"}`

Present results as two sections: **Projects** and **Tasks**.

---

## Rules
- Never pass `tenant_key` (auto-injected by security layer)
- Active product required (server-side enforced) — if error mentions "No active product", tell user to activate one in dashboard
- This skill is read-only — never call `create_project`, `create_task`, `update_project`, or `update_task`; direct writes to `$gil-add`
- On error: show what went wrong and how to fix
