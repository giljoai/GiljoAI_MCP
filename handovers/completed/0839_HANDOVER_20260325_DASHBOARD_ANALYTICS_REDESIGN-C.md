# Handover 0839: Dashboard Analytics Redesign

**Date:** 2026-03-25
**From Agent:** Implementation session (0838 + UI polish)
**To Agent:** Implementation agent
**Priority:** High
**Estimated Complexity:** 6-8 hours
**Status:** Not Started
**Edition Scope:** CE

---

## Task Summary

Redesign the Dashboard (`/Dashboard`) into a product-aware analytics hub with a product selector, categorized stat rows, three animated donut charts, and recent activity lists. Install `chart.js` + `vue-chartjs` for charting.

---

## Context and Background

### Current State

The Dashboard (`frontend/src/views/DashboardView.vue`) shows:
- Static stat badge cards in two groups (Projects, Server)
- No product filtering — all stats are global
- No charts or visualizations
- No recent activity lists
- Stats come from `/api/stats/system` (backend) and `/api/stats/call-counts`

### What Needs to Change

Transform the dashboard into a layered analytics view:

```
┌─────────────────────────────────────────────────┐
│  [All Products]  [TinyContacts]  [Product X]    │  product selector
├─────────────────────────────────────────────────┤
│  Projects ▸ # | Active # | Staged # | ...      │  filtered by product
│  Tasks    ▸ # | Open # | Completed # | ...     │  filtered by product
│  Server   ▸ API # | MCP # | Agents #           │  always global
├─────────────────────────────────────────────────┤
│  [◉ Status]    [◉ Taxonomy]    [◉ Agent Roles]  │  donut charts
├─────────────────────────────────────────────────┤
│  Recent Projects          │  Recent 360 Memories │  activity lists
└─────────────────────────────────────────────────┘
```

---

## Technical Details

### Files to Modify

| File | Change |
|------|--------|
| `frontend/src/views/DashboardView.vue` | Complete redesign — product selector, categorized stat rows, chart containers, recent activity lists |
| `api/endpoints/statistics.py` | New endpoints: product-filtered stats, agent role distribution, taxonomy distribution, recent memories |
| `src/giljo_mcp/repositories/statistics_repository.py` | New query methods for dashboard analytics |
| `frontend/package.json` | Add `chart.js` + `vue-chartjs` dependencies |

### Files to Create

| File | Purpose |
|------|---------|
| `frontend/src/components/dashboard/ProductSelector.vue` | Horizontal product selector with "All Products" default |
| `frontend/src/components/dashboard/DonutChart.vue` | Reusable donut chart wrapper with spin-up animation |
| `frontend/src/components/dashboard/RecentProjectsList.vue` | Last 10 projects with status badges and duration |
| `frontend/src/components/dashboard/RecentMemoriesList.vue` | Last 10 360 memory entries with summaries |

### Files to Read (no changes expected)

| File | Why |
|------|-----|
| `src/giljo_mcp/models/projects.py` | Project model fields: `status`, `completed_at`, `created_at`, `project_type_id`, `product_id` |
| `src/giljo_mcp/models/agent_identity.py` | AgentExecution: `agent_display_name` (role distribution), `tool_type`, `started_at`, `completed_at` |
| `src/giljo_mcp/models/product_memory_entry.py` | ProductMemoryEntry: `timestamp`, `summary`, `project_name`, `entry_type` |
| `src/giljo_mcp/models/products.py` | Product model: `name`, `is_active`, `id` |
| `src/giljo_mcp/models/tasks.py` | Task model: status fields for task row stats |
| `frontend/src/stores/products.js` | Existing product store — reuse for product list |

---

## Implementation Plan

### Phase 1: Backend — Dashboard Analytics Endpoints

#### 1a. New Repository Methods (`statistics_repository.py`)

Add these methods to `StatisticsRepository`:

```python
async def get_project_status_distribution(session, tenant_key, product_id=None) -> dict[str, int]
    # GROUP BY status, COUNT. Optional product_id filter.

async def get_project_taxonomy_distribution(session, tenant_key, product_id=None) -> list[dict]
    # JOIN project_types, GROUP BY type label, COUNT. Include custom types.

async def get_agent_role_distribution(session, tenant_key, product_id=None) -> dict[str, int]
    # GROUP BY agent_display_name, COUNT. Optional product_id via AgentJob.project_id -> Project.product_id.

async def get_recent_projects(session, tenant_key, product_id=None, limit=10) -> list[dict]
    # ORDER BY created_at DESC, LIMIT 10. Return name, status, created_at, completed_at, taxonomy_alias.

async def get_recent_memory_entries(session, tenant_key, product_id=None, limit=10) -> list[dict]
    # ORDER BY timestamp DESC, LIMIT 10. Return project_name, summary[:200], timestamp, entry_type.

async def get_task_status_distribution(session, tenant_key, product_id=None) -> dict[str, int]
    # GROUP BY status, COUNT for tasks.

async def get_product_project_counts(session, tenant_key) -> list[dict]
    # Per-product: {product_id, product_name, project_count}. For product selector badges.
```

#### 1b. New API Endpoint (`statistics.py`)

Add a single consolidated endpoint:

```python
@router.get("/dashboard")
async def get_dashboard_stats(
    product_id: Optional[str] = Query(None),  # None = all products
    current_user = Depends(get_current_active_user),
    db = Depends(get_db_session),
) -> dict:
    # Returns: project_status_dist, taxonomy_dist, agent_role_dist,
    #          recent_projects, recent_memories, task_status_dist, products
```

Single endpoint reduces frontend round-trips. Server stats (API/MCP calls, agents spawned) remain on existing `/stats/system` and `/stats/call-counts` endpoints.

### Phase 2: Frontend — Install Chart.js

```bash
cd frontend && npm install chart.js vue-chartjs
```

### Phase 3: Frontend — Product Selector Component

`ProductSelector.vue`:
- Horizontal row of chips/buttons, centered
- "All Products" chip (default selected, primary color)
- One chip per product from product store
- Emits `@select="productId"` (null for All)
- Each chip shows product name + project count badge

### Phase 4: Frontend — Categorized Stat Rows

Refactor `DashboardView.vue` stat cards into three rows:

**Projects row** (filtered by selected product):
- Projects, Active, Inactive, Staged, Finished, Cancelled, Terminated

**Tasks row** (filtered by selected product):
- Tasks, Open, Completed, (other task statuses)

**Server row** (always global, never filtered):
- API Calls (mdi-swap-horizontal), MCP Calls (logo-mcp.svg), Agents Spawned (giljo_YW_Face.svg)

Use existing compact stat card style (`.stat-card`, `.stat-icon-box`, etc.)

### Phase 5: Frontend — Donut Charts

`DonutChart.vue` — reusable wrapper:
- Props: `data` (labels + values + colors), `title`
- Uses `vue-chartjs` Doughnut component
- **Spin-up animation**: Chart.js natively supports animation on render. Configure `animation.animateRotate = true` with 1-second duration
- Re-animates when data changes (product selection change)

Three instances in DashboardView:
1. **Projects by Status** — segments: Active (green), Inactive (grey), Completed (blue), Cancelled (orange), Terminated (red)
2. **Projects by Taxonomy** — segments: one per ProjectType (use type's `color` field). Include "Untyped" segment for projects without type
3. **Agent Role Distribution** — segments: one per `agent_display_name` value (orchestrator, implementer, tester, analyzer, documenter, reviewer)

All three filtered by selected product (or global when "All Products").

### Phase 6: Frontend — Recent Activity Lists

Two side-by-side lists below the charts:

**Recent Projects** (`RecentProjectsList.vue`):
- Last 10 projects (filtered by product)
- Each row: taxonomy chip, project name, StatusBadge, duration (if completed)
- Duration = `completed_at - created_at` formatted as "2d 4h" or "< 1h"
- Clickable rows (same behavior as ProjectsView: edit modal or review modal)

**Recent 360 Memories** (`RecentMemoriesList.vue`):
- Last 10 memory entries (filtered by product)
- Each row: project name, entry_type chip, summary snippet (first 120 chars), relative timestamp ("2h ago")
- Compact list style, no heavy cards

### Phase 7: Wiring — Product Selection State

In `DashboardView.vue`:
- `selectedProductId = ref(null)` (null = All Products)
- `watch(selectedProductId)` → fetch `/api/stats/dashboard?product_id=X`
- Server row always uses existing global endpoints (no product filter)
- Charts and stat rows re-render with new data on product change
- Donut charts re-animate on data change (spin-up effect)

---

## Data Availability Reference

All data columns needed already exist in the database:

| Widget | Source Table | Key Fields |
|--------|------------|------------|
| Project status dist | `projects` | `status`, `product_id` |
| Taxonomy dist | `projects` JOIN `project_types` | `project_type_id`, `label`, `color` |
| Agent role dist | `agent_executions` JOIN `agent_jobs` JOIN `projects` | `agent_display_name`, `product_id` |
| Recent projects | `projects` | `name`, `status`, `created_at`, `completed_at`, `taxonomy_alias` |
| Recent 360 memories | `product_memory_entries` | `project_name`, `summary`, `timestamp`, `entry_type` |
| Task status dist | `tasks` | `status`, `product_id` |
| Product list | `products` | `name`, `id`, `is_active` |

No new database columns or migrations required.

---

## Testing Requirements

**Unit Tests:**
- Each new repository method returns correct counts with product_id filter
- Each new repository method returns correct counts without filter (all products)
- Tenant isolation on all new queries

**Integration Tests:**
- `/api/stats/dashboard` returns complete response shape
- `/api/stats/dashboard?product_id=X` filters correctly
- Product with no projects returns zero counts (not errors)

**Manual Tests:**
- Product selector highlights selected product
- Switching products re-animates donut charts and updates stat rows
- Server row stays constant when product changes
- Recent projects list shows correct projects for selected product
- Donut charts show correct segment counts matching stat row numbers

---

## Success Criteria

- [ ] Product selector row with "All Products" + per-product chips
- [ ] Three categorized stat rows (Projects, Tasks, Server)
- [ ] Projects and Tasks rows filter by selected product
- [ ] Server row always shows global stats
- [ ] Three donut charts with spin-up animation on render
- [ ] Charts filter by selected product
- [ ] Recent 10 projects list with status badges
- [ ] Recent 10 360 memories list with summaries
- [ ] Single `/api/stats/dashboard` endpoint with optional product_id
- [ ] All new queries enforce tenant_key isolation
- [ ] chart.js + vue-chartjs installed and working

---

## Key File Reference

| Component | File | Lines |
|-----------|------|-------|
| Dashboard view | `frontend/src/views/DashboardView.vue` | Full file |
| Statistics endpoint | `api/endpoints/statistics.py` | 139-190 |
| Statistics repository | `src/giljo_mcp/repositories/statistics_repository.py` | Full file |
| Product store | `frontend/src/stores/products.js` | Full file |
| Project model | `src/giljo_mcp/models/projects.py` | 60-175 |
| AgentExecution model | `src/giljo_mcp/models/agent_identity.py` | Full file |
| ProductMemoryEntry model | `src/giljo_mcp/models/product_memory_entry.py` | Full file |
| Task model | `src/giljo_mcp/models/tasks.py` | Task class |
