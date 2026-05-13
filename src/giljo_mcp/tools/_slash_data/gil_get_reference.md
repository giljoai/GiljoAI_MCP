# /gil_get — agent reference cheat sheet

Read-only companion to `/gil_add`. Use this skill when the user wants to **look up**
existing projects or tasks. Never use it to create or modify state.

## When to call

- User says: "read project", "show project", "look up project", "fetch context for ...",
  "read task", "show tasks", "what tasks are open", "tasks due ...", or pastes bare UUIDs.
- User asks "what's <ALIAS> about?" / "what BE tasks are open?" / "show me everything FE".

## Tool shapes

### list_projects
Cheap discovery. Pick a mode by how much detail you need.
- `mcp__giljo_mcp__list_projects(summary_only=true)` — lightest payload (id, name,
  taxonomy_alias, status, timestamps). Match by alias to grab `project_id`.
- `mcp__giljo_mcp__list_projects(mode="triage")` — same shape as `summary_only`.
- `mcp__giljo_mcp__list_projects(mode="planning")` — adds description, mission,
  agent_summary. Use for bulk reads when user pastes multiple UUIDs.
- `mcp__giljo_mcp__list_projects(mode="audit")` — adds memory headlines.
- `mcp__giljo_mcp__list_projects(mode="forensic")` — full memory bodies + agent results.
  Heavy. Only when archaeology is genuinely needed.
- Optional filter: `project_type="BE"` (or any configured type prefix) for cross-cutting reads.

### list_tasks
- `mcp__giljo_mcp__list_tasks(mode="summary", task_type=None, filters={})` —
  one row per task: id, title, status, priority, task_type (embedded block),
  series_number, subseries, taxonomy_alias (e.g. `BE-0017`), hidden,
  due_date, created_at.
- `mode="full"` — adds description bodies. Avoid unless user wants the prose.
- `task_type` — taxonomy abbreviation (e.g. `"BE"`, `"FE"`, `"INF"`).
  Filters tasks with that type.
- `filters` (dict, all optional):
  - `status`: pending | in_progress | completed | blocked | cancelled | converted
  - `priority`: low | medium | high | critical
  - `hidden`: true | false — omit to get BOTH (default for agents; dashboard
    UI filters hidden=false). Tasks remain searchable here regardless of UI state.

### fetch_context
- `mcp__giljo_mcp__fetch_context(product_id=..., project_id=..., categories=["project"])`
  → ~300 tokens for ONE project: project_name, project_alias, project_description,
  orchestrator_mission, status, staging_status. Right tool for "what's X about?".
- `mcp__giljo_mcp__fetch_context(product_id=..., categories=["tasks"])`
  → full task bodies for the active product. Pair with `list_tasks` when the user
  wants both summary rows and descriptions.
- `categories` accepts both strings — e.g. `["project", "tasks"]` — for combined reads.

## Routing decision tree

1. User wants **one project's** description or mission → `fetch_context(["project"])`.
2. User wants to **find** a project by alias/name → `list_projects(summary_only=true)`,
   then optionally `fetch_context` for the match.
3. User wants **multiple projects** in detail → `list_projects(mode="planning")` and
   filter the saved tool-result with `jq` (the harness saves large results to disk).
4. User wants **task lists** → `list_tasks(mode="summary", filters=...)`.
5. User wants **everything BE/FE/...** → run `list_projects(project_type=X)` AND
   `list_tasks(task_type=X, filters={"status": "pending"})` in parallel.

## Hard rules

- This skill is **read-only**. Never call `create_project`, `create_task`,
  `update_project`, or `update_task`. Direct write intent to `/gil_add`.
- The project identifier field is `project_id`, **never** `id`. `.id` filters
  return nothing.
- Never pass `tenant_key`. The security layer injects it.
- Active product is required server-side. If you see "No active product", tell the
  user to activate one in the dashboard rather than retrying.
