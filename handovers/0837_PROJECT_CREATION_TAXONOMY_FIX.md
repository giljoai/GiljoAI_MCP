# Handover 0837: Project Creation Taxonomy Fix — MCP & Multi-Tenant Safety

**Date:** 2026-03-23
**From Agent:** Session coordinator (0836 series)
**To Agent:** Next session
**Priority:** Critical
**Estimated Complexity:** 4-6 hours
**Status:** Not Started
**Edition Scope:** CE

---

## Task Summary

The `create_project` MCP tool is broken for any tenant that already has one project. The `uq_project_taxonomy` constraint with `NULLS NOT DISTINCT` blocks every INSERT after the first because all MCP-created projects have NULL taxonomy fields. This affects all platforms (Claude Code, Gemini CLI, Codex CLI). Additionally, audit all other unique constraints for similar multi-tenant lockout patterns.

---

## Context and Background

### The Bug

The project taxonomy system (Handover 0440a) added a unique constraint:
```sql
UniqueConstraint("tenant_key", "project_type_id", "series_number", "subseries",
                 name="uq_project_taxonomy", postgresql_nulls_not_distinct=True)
```

`NULLS NOT DISTINCT` means `(tenant_key, NULL, NULL, NULL)` can only exist ONCE. The MCP tool `create_project` in `tool_accessor.py` never passes taxonomy fields — it only sends `name`, `description`, `product_id`, `tenant_key`, `status`. So every project created via MCP gets `(tenant_key, NULL, NULL, NULL)`, and the second one fails.

The dashboard UI works because it provides `project_type_id` and `series_number`. Only MCP callers are broken.

**Confirmed in logs:** `Key (tenant_key, project_type_id, series_number, subseries)=(tk_..., null, null, null) already exists.`

### Design Decision (from user)

- NULL taxonomy is acceptable — users can edit taxonomy later via dashboard
- The MCP tool should auto-assign a `series_number` to avoid constraint violations
- Type should be resolvable by human-readable label (e.g. `"Frontend"`) not abbreviation or UUID
- The fix must be production-grade for SaaS multi-tenant — no race conditions, no lockouts

---

## Technical Details

### Files to Modify

| File | Change |
|------|--------|
| `src/giljo_mcp/services/project_service.py` | Auto-assign `series_number` when not provided |
| `src/giljo_mcp/tools/tool_accessor.py` | Accept optional `type` param, resolve label → `project_type_id` |
| `api/endpoints/mcp_http.py` | Add `type` to `create_project` MCP schema |
| `src/giljo_mcp/tools/slash_command_templates.py` | Update `/gil_add` templates to pass `type` when user specifies |

### Root Cause Fix: Auto-Assign Series Number

In `project_service.py` `create_project()`, when `series_number is None`:

```python
# Auto-assign next available series_number for this tenant + type combo
# Use SELECT ... FOR UPDATE to prevent race conditions
next_series_query = select(func.coalesce(func.max(Project.series_number), 0) + 1).where(
    Project.tenant_key == tenant_key,
    Project.deleted_at.is_(None),
)
if project_type_id:
    next_series_query = next_series_query.where(Project.project_type_id == project_type_id)
else:
    next_series_query = next_series_query.where(Project.project_type_id.is_(None))

# Lock rows to prevent concurrent race
next_series_query = next_series_query.with_for_update()
result = await session.execute(next_series_query)
series_number = result.scalar_one()
```

This ensures:
- Every project gets a unique `series_number` even without explicit taxonomy
- `FOR UPDATE` prevents two concurrent requests from getting the same number
- NULL `project_type_id` is fine — series numbers are unique within each type (including NULL type)

### Type Resolution by Label

In `tool_accessor.py` `create_project()`, add optional `type` parameter:

```python
async def create_project(self, name: str, description: str = "", type: str | None = None, ...):
    project_type_id = None
    if type:
        # Resolve label to project_type_id
        project_type = await self._project_service.get_project_type_by_label(type, tenant_key)
        if project_type:
            project_type_id = project_type.id
        # If not found, create without type (don't error — user can set later)
```

Add `get_project_type_by_label()` to `project_service.py`:
```python
async def get_project_type_by_label(self, label: str, tenant_key: str) -> ProjectType | None:
    """Resolve a project type by its human-readable label (case-insensitive)."""
    async with self._get_session() as session:
        result = await session.execute(
            select(ProjectType).where(
                ProjectType.tenant_key == tenant_key,
                func.lower(ProjectType.label) == label.lower(),
            )
        )
        return result.scalar_one_or_none()
```

### MCP Schema Update

In `mcp_http.py`, add `type` to the `create_project` tool definition:
```json
{
    "type": {
        "type": "string",
        "description": "Optional project type label (e.g. 'Frontend', 'Backend'). Resolved to type ID internally."
    }
}
```

---

## Sub-Handover Breakdown

### 0837a — Auto-Assign Series Number (Root cause fix)

**Scope:** `project_service.py` only
**What:** When `series_number` is not provided, auto-assign `MAX(series_number) + 1` with `FOR UPDATE` lock.
**Tests:**
- Create 2+ projects without taxonomy → both succeed with unique series numbers
- Create projects concurrently (async) → no duplicates
- Create projects with explicit taxonomy → still works (no regression)
- Create project after soft-deleted project with same taxonomy → works

**Success criteria:** Any MCP caller can create unlimited projects without taxonomy errors.

### 0837b — Type Resolution by Label + MCP Schema

**Scope:** `tool_accessor.py`, `project_service.py` (new method), `mcp_http.py`
**What:** Add optional `type` parameter to `create_project` MCP tool. Resolve human-readable label (e.g. "Frontend") to `project_type_id` via case-insensitive lookup. If type not found, create without type (no error).
**Tests:**
- `create_project(name="foo", type="Frontend")` → resolves to correct type ID
- `create_project(name="foo", type="frontend")` → case-insensitive match
- `create_project(name="foo", type="NonExistent")` → creates without type (no error)
- `create_project(name="foo")` → still works (no type, auto-series)

**Success criteria:** MCP callers can optionally classify projects by type using plain English names.

### 0837c — Slash Command Template Updates

**Scope:** `slash_command_templates.py`
**What:** Update `/gil_add` templates (Claude, Gemini, Codex) to pass `type` when user specifies a category for projects. Currently `/gil_add` only sends `name` and `description`.
**Tests:** Existing slash command template tests + new assertions for type param.

**Success criteria:** `/gil_add --project "Vanilla" --type Frontend` works across all platforms.

### 0837d — Multi-Tenant Constraint Audit

**Scope:** All models in `src/giljo_mcp/models/`
**What:** Audit every `UniqueConstraint` and `unique=True` column for lockout patterns where:
1. NULL values in constrained columns could cause `NULLS NOT DISTINCT` collisions
2. Constraints could block legitimate writes from different users in the same tenant
3. Missing tenant_key scoping could cause cross-tenant collisions

**Known constraints to audit (from model scan):**

| Constraint | Table | Columns | Risk |
|-----------|-------|---------|------|
| `uq_project_taxonomy` | projects | tenant_key, project_type_id, series_number, subseries | **CONFIRMED BUG** — fixed in 0837a |
| `uq_project_type_abbr` | project_types | tenant_key, abbreviation | Low — abbreviation is always provided |
| `uq_template_product_name_version` | agent_templates | product_id, name, version | Check — could block if version is NULL |
| `uq_vision_doc_product_name` | vision_documents | product_id, document_name | Low — name always provided |
| `uq_config_tenant_key` | config | tenant_key, key | Low — key always provided |
| `uq_settings_tenant_category` | settings | tenant_key, category | Low — category always provided |
| `uq_product_sequence` | product_memory | product_id, sequence | Check — sequence auto-assigned? |
| `idx_product_single_active_per_tenant` | products | tenant_key (WHERE is_active=true) | Check — can only one product be active? (by design) |
| `uq_org_user` | org_memberships | org_id, user_id | Low — always provided |
| `uq_api_key_ip` | api_key_ips | api_key_id, ip_address | Low — always provided |
| `uq_discovery_path` | discovery_paths | project_id, path_key | Low — always provided |

**Deliverable:** Audit report confirming each constraint is safe or flagging additional fixes needed.

---

## Cascading Analysis

**Downstream:** Projects created via MCP will now have `series_number` populated. The taxonomy alias display (`FE-0001`) will work for typed projects. Untyped projects show just the series number or name — no UI regression.

**Upstream:** No product or organization changes. The `product_id` resolution path is unchanged.

**Sibling:** Tasks are unaffected (no taxonomy system on tasks). Other projects in the same product continue to work — the `FOR UPDATE` lock is scoped to the specific type+tenant combo.

**Installation:** No migration needed — the DB constraint stays the same. The fix is application-level (auto-assign values that satisfy the constraint).

---

## Success Criteria

- [ ] MCP `create_project` works for 2+ projects per tenant without taxonomy fields
- [ ] Optional `type` parameter resolves by label (case-insensitive)
- [ ] Concurrent project creation doesn't produce duplicate series numbers
- [ ] All existing dashboard project creation still works (no regression)
- [ ] Constraint audit complete with no other lockout risks identified
- [ ] All tests pass
