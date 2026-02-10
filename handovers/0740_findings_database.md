# 0740 Findings: Database Schema

## Executive Summary

This audit compares the SQLAlchemy model definitions in `src/giljo_mcp/models/` against the live PostgreSQL database (`giljo_mcp`). The codebase has 34 model tables defined across 10 model files. The database contains 35 tables (34 application tables + `alembic_version`). Three categories of issues were identified:

**Critical (P0)**: 2 findings -- orphaned legacy table `mcp_agent_jobs` with broken FK from `tasks.job_id`, and `product_memory` server_default still containing removed `sequential_history` key.

**High (P1)**: 5 findings -- 3 model-vs-DB column mismatches (extra DB columns not in models), 11 duplicate indexes wasting storage/write performance, and 3 index name mismatches between models and DB.

**Medium (P2)**: 4 findings -- DB column `projects.context_budget` has no model counterpart, `template_content` column exists in DB but not in models for `agent_templates` and `template_archives`, and `configurations.user_id` column exists in DB but not in model.

**Low (P3)**: 2 findings -- Several FK relationships use NO ACTION where CASCADE or SET NULL may be more appropriate, and minor naming inconsistencies.

**Totals**: 13 distinct findings across 4 priority levels.

---

## Methodology

1. Read all 15 model files in `src/giljo_mcp/models/` to catalog every SQLAlchemy model, column, index, constraint, and relationship.
2. Connected to the live PostgreSQL 17 database (`PGPASSWORD=$DB_PASSWORD psql -U postgres -d giljo_mcp`) and queried:
   - `\dt public.*` -- 35 tables
   - `information_schema.columns` -- 548 columns across 34 app tables
   - `pg_indexes` -- 233 indexes
   - `information_schema.table_constraints` + `referential_constraints` -- 40 FK constraints
3. Cross-referenced every model column against every DB column per table.
4. Searched codebase (`src/`, `api/`, `tests/`) for usage of suspect columns.
5. Verified FK cascade rules against model definitions.
6. Identified duplicate indexes by comparing index definitions with different names.

---

## Findings (by priority)

### P0 Critical

#### P0-1: Orphaned `mcp_agent_jobs` Table with Active FK Constraint

**Table**: `mcp_agent_jobs` (35 columns, 0 rows, 15 indexes)
**Impact**: Schema drift, broken FK constraint, wasted storage

The `mcp_agent_jobs` table exists in the database but has NO corresponding SQLAlchemy model. It was the original "god object" (pre-Handover 0366a) that was split into `agent_jobs` + `agent_executions`. However:

- The table was never dropped from the database.
- The `tasks` table still has an active FK constraint `fk_task_job` pointing to `mcp_agent_jobs.job_id` (NOT to `agent_jobs.job_id` as the Task model defines).
- The model in `src/giljo_mcp/models/tasks.py:73` declares: `job_id = Column(String(36), ForeignKey("agent_jobs.job_id"), nullable=True)` -- pointing to `agent_jobs`.
- The database constraint points to `mcp_agent_jobs`: `FOREIGN KEY (job_id) REFERENCES mcp_agent_jobs(job_id)`.
- `mcp_agent_jobs` has 0 data rows. `agent_jobs` has 58 rows.
- Currently no tasks have `job_id` set (0 rows with non-NULL job_id), so this is latent rather than actively breaking. But any attempt to insert a task with `job_id` pointing to an `agent_jobs` record would fail the DB-level FK check.

**Risk**: Any new task-to-job linking will fail at the database level because the FK targets the wrong (empty, orphaned) table.

**Files**:
- `src/giljo_mcp/models/tasks.py:73` -- Model FK definition
- DB constraint: `fk_task_job FOREIGN KEY (job_id) REFERENCES mcp_agent_jobs(job_id)`

**Recommendation**: Migration required to:
1. Drop FK constraint `fk_task_job` from `tasks`.
2. Create new FK: `tasks.job_id REFERENCES agent_jobs(job_id)`.
3. Drop table `mcp_agent_jobs` (0 rows, safe to remove).

---

#### P0-2: `products.product_memory` Server Default Contains Removed `sequential_history`

**Table**: `products`
**Column**: `product_memory`
**Impact**: New product rows created at DB level will contain `sequential_history: []` key that was explicitly removed in Handover 0700c.

**Model** (products.py:117):
```python
server_default=text('\'{"github": {}, "context": {}}\'::jsonb')
```

**Database**:
```sql
column_default = '{"github": {}, "context": {}, "sequential_history": []}'::jsonb
```

The model correctly omits `sequential_history`, but the DB still has the old default. This means:
- New products created via raw SQL or DB tools will get the old default with `sequential_history`.
- Products created via SQLAlchemy will get the model's default (correct).
- The `_build_product_memory_response` in `product_service.py` reads `sequential_history` from the normalized `product_memory_entries` table, so the JSONB key is vestigial. But its presence creates confusion and contradicts the 0700c cleanup.

**Files**:
- `src/giljo_mcp/models/products.py:114-119` -- Model definition
- `src/giljo_mcp/services/product_service.py:1507-1553` -- Still references `sequential_history` in API responses (built from table, not JSONB)

**Recommendation**: Migration to `ALTER TABLE products ALTER COLUMN product_memory SET DEFAULT '{"github": {}, "context": {}}'::jsonb;`

---

### P1 High

#### P1-1: 11 Duplicate Indexes (Same Column, Different Names)

**Impact**: Each duplicate index doubles write overhead and storage for that column. On a small dataset this is negligible, but it accumulates as data grows and wastes PostgreSQL maintenance resources (VACUUM, ANALYZE).

| Table | Duplicate 1 (model-defined) | Duplicate 2 (legacy `ix_` prefix) |
|-------|---------------------------|----------------------------------|
| `api_keys` | `idx_apikey_tenant` | `ix_api_keys_tenant_key` |
| `download_tokens` | `idx_download_token_tenant` | `ix_download_tokens_tenant_key` |
| `mcp_agent_jobs` | `idx_mcp_agent_jobs_project` | `ix_mcp_agent_jobs_project_id` |
| `mcp_sessions` | `idx_mcp_session_tenant` | `ix_mcp_sessions_tenant_key` |
| `optimization_metrics` | `idx_optimization_metric_tenant` | `ix_optimization_metrics_tenant_key` |
| `optimization_rules` | `idx_optimization_rule_tenant` | `ix_optimization_rules_tenant_key` |
| `products` | `idx_product_tenant` | `ix_products_tenant_key` |
| `settings` | `idx_settings_tenant` | `ix_settings_tenant_key` |
| `setup_state` | `idx_setup_database_initialized` | `ix_setup_state_database_initialized` |
| `users` | `idx_user_tenant` | `ix_users_tenant_key` |
| `vision_documents` | `idx_vision_doc_tenant` | `ix_vision_documents_tenant_key` |

**Root Cause**: The `ix_` prefixed indexes come from SQLAlchemy's automatic index creation (via `index=True` on Column definitions). The `idx_` prefixed indexes come from explicit `Index()` definitions in `__table_args__`. Both create the same btree index on the same column.

**Recommendation**: Migration to drop the 11 `ix_*` legacy indexes. Keep the explicitly named `idx_*` indexes for consistency with model definitions.

---

#### P1-2: `download_tokens` -- 2 Columns in DB Not in Model

**Table**: `download_tokens`
**Extra DB columns**: `is_used` (boolean, NOT NULL), `downloaded_at` (timestamp with time zone, nullable)

These columns exist in the database but are NOT defined in the model (`src/giljo_mcp/models/config.py:591-667`). The model defines `staging_status`, `download_count`, and `last_downloaded_at` instead.

Codebase search for `is_used`:
- `src/giljo_mcp/models/config.py` -- only in comments (describing DownloadToken)
- `src/giljo_mcp/download_tokens.py` -- does NOT reference `.is_used`

These appear to be legacy columns from an earlier version of the download token system that was replaced by `staging_status` + `download_count` + `last_downloaded_at`.

**Files**:
- `src/giljo_mcp/models/config.py:591-667` -- DownloadToken model (no `is_used` or `downloaded_at`)
- DB: `download_tokens.is_used` (boolean NOT NULL), `download_tokens.downloaded_at` (timestamptz)

**Recommendation**: Migration to drop `is_used` and `downloaded_at` columns. Verify no direct SQL queries reference them first.

---

#### P1-3: `agent_templates` and `template_archives` -- `template_content` Column in DB Not in Model

**Table**: `agent_templates`, `template_archives`
**Extra DB column**: `template_content` (text, NOT NULL in agent_templates, NOT NULL in template_archives)

The model for `AgentTemplate` (`src/giljo_mcp/models/templates.py`) does NOT define a `template_content` column. The model uses `system_instructions` + `user_instructions` (dual-field system from Handover 0106).

Codebase search for `template_content`:
- Zero references in `src/giljo_mcp/` Python files.
- Only found in: migration files, `scripts/archived/`, `scripts/seed_orchestrator_template.py`, `scripts/init_templates.py`, `installer/core/config.py`.

This is a legacy column from before the dual-field split. It is NOT NULL in the DB, meaning it must have had data. But no active code reads or writes it.

**Files**:
- `src/giljo_mcp/models/templates.py:28-147` -- AgentTemplate model (no `template_content`)
- `src/giljo_mcp/models/templates.py:150-204` -- TemplateArchive model (no `template_content`)
- DB: `agent_templates.template_content` (text NOT NULL), `template_archives.template_content` (text NOT NULL)

**Recommendation**: Migration to drop `template_content` from both tables. Verify `scripts/` files are updated or archived.

---

#### P1-4: 3 Index Name Mismatches Between Model and DB

The following model-defined index names do not match the actual database index names:

| Table | Model Index Name | DB Index Name | Column |
|-------|-----------------|---------------|--------|
| `agent_templates` | `idx_agent_templates_org` | `idx_template_org_id` | `org_id` |
| `products` | `idx_products_org` | `idx_product_org_id` | `org_id` |
| `tasks` | `idx_tasks_org` | `idx_task_org_id` | `org_id` |

**Impact**: If a migration is generated from the model state, Alembic will attempt to create indexes that already exist (under different names), causing migration failures. This is a drift between model definitions and actual DB state.

**Files**:
- `src/giljo_mcp/models/templates.py:115` -- `Index("idx_agent_templates_org", "org_id")`
- `src/giljo_mcp/models/products.py:160` -- `Index("idx_products_org", "org_id")`
- `src/giljo_mcp/models/tasks.py:101` -- `Index("idx_tasks_org", "org_id")`

**Recommendation**: Either rename the model index names to match DB, or create a migration that renames DB indexes to match models. Prefer updating models to match DB since the DB is the source of truth.

---

#### P1-5: `configurations.user_id` Column Exists in DB But Not in Model

**Table**: `configurations`
**Extra DB column**: `user_id` (character varying(36), nullable)

The `Configuration` model in `src/giljo_mcp/models/config.py:32-58` does NOT define a `user_id` column. The DB has it.

This column is not referenced in any codebase search of `src/giljo_mcp/` for `configurations.*user_id`.

**Files**:
- `src/giljo_mcp/models/config.py:32-58` -- Configuration model
- DB: `configurations.user_id` (varchar(36), nullable)

**Recommendation**: Migration to drop `configurations.user_id` if unused, or add it to the model if it serves a purpose.

---

### P2 Medium

#### P2-1: `projects.context_budget` Column Exists in DB But Not in Model

**Table**: `projects`
**Extra DB column**: `context_budget` (integer, nullable)

The `Project` model in `src/giljo_mcp/models/projects.py` does NOT define a `context_budget` column. The model only defines `context_used` (line 67). The DB has both `context_budget` and `context_used`.

Context budget tracking has been moved to `AgentExecution` (per Handover 0366a), where both `context_used` and `context_budget` are defined. The project-level `context_budget` appears to be a legacy column.

**Files**:
- `src/giljo_mcp/models/projects.py:26-150` -- Project model (has `context_used`, no `context_budget`)
- `src/giljo_mcp/models/agent_identity.py:232-243` -- AgentExecution has both `context_used` and `context_budget`

**Recommendation**: Verify no code references `Project.context_budget` (initial search shows no references), then migrate to drop the column.

---

#### P2-2: FK Cascade Mismatch -- `agent_executions.job_id` NO ACTION vs Model Expectation

**Table**: `agent_executions`
**Column**: `job_id` (FK to `agent_jobs.job_id`)
**DB delete rule**: `NO ACTION`
**Model relationship** (agent_identity.py:103-108):
```python
executions = relationship(
    "AgentExecution",
    back_populates="job",
    cascade="all, delete-orphan",
)
```

The SQLAlchemy relationship specifies `cascade="all, delete-orphan"` on the parent side, which handles cascade at the ORM level. However, the DB-level FK has `NO ACTION`, meaning:
- Deleting an `AgentJob` via raw SQL will fail if `AgentExecution` rows reference it.
- Deleting via SQLAlchemy ORM will work (ORM handles cascade).

This is a defense-in-depth gap. The `AgentTodoItem.job_id` FK correctly uses `ondelete="CASCADE"` both in model and DB.

**Files**:
- `src/giljo_mcp/models/agent_identity.py:149-154` -- `job_id` FK (no `ondelete` specified)
- `src/giljo_mcp/models/agent_identity.py:103-108` -- Relationship with `cascade="all, delete-orphan"`

**Recommendation**: Add `ondelete="CASCADE"` to the `agent_executions.job_id` FK definition for consistency with the relationship cascade behavior.

---

#### P2-3: Several `project_id` FK Constraints Use NO ACTION

Multiple tables have FK relationships to `projects.id` with `NO ACTION` delete rule, but the `Project` model defines `cascade="all, delete-orphan"` relationships to several of them:

| Table | FK Column | Model Cascade | DB Delete Rule |
|-------|-----------|---------------|----------------|
| `agent_interactions` | `project_id` | via backref | NO ACTION |
| `context_index` | `project_id` | `cascade="all, delete-orphan"` | NO ACTION |
| `discovery_config` | `project_id` | via backref | NO ACTION |
| `large_document_index` | `project_id` | `cascade="all, delete-orphan"` | NO ACTION |
| `messages` | `project_id` | `cascade="all, delete-orphan"` | NO ACTION |

The ORM handles cascade correctly, but raw SQL deletes of projects would leave orphaned records.

**Files**:
- `src/giljo_mcp/models/projects.py:117-126` -- Relationship definitions

**Recommendation**: Add `ondelete="CASCADE"` to these FK definitions for defense-in-depth.

---

#### P2-4: `agent_jobs.project_id` FK Has NO ACTION but Project Relationship Has `cascade="all, delete-orphan"`

**Table**: `agent_jobs`
**Column**: `project_id` (FK to `projects.id`)
**DB**: NO ACTION
**Model** (projects.py:119): `agent_jobs_v2 = relationship("AgentJob", back_populates="project", cascade="all, delete-orphan")`

Same pattern as P2-3. ORM cascade works, but DB-level protection is missing.

---

### P3 Low

#### P3-1: `mcp_sessions.user_id` Index Uses Partial WHERE Clause

**DB index**: `idx_mcp_session_user` has `WHERE (user_id IS NOT NULL)`
**Model** (auth.py:266): `Index("idx_mcp_session_user", "user_id")` -- no `postgresql_where` clause

The DB index is a partial index (only indexes non-NULL values), but the model defines a full index. This is actually better behavior in the DB (partial index is more efficient), but it means the model does not accurately represent the database state.

---

#### P3-2: `api_keys.key_hash` Has Both Column-Level and Explicit Unique + Index

The `key_hash` column has `unique=True, index=True` on the Column definition AND explicit `Index("idx_apikey_hash", "key_hash")` in `__table_args__`. This creates 2 indexes in the DB:
- `ix_api_keys_key_hash` (unique, from Column `unique=True`)
- `idx_apikey_hash` (non-unique, from explicit Index)

The unique index already provides lookup performance, so the non-unique explicit index is redundant.

---

## Schema Overview

| Table | DB Cols | Model Cols | Indexes (DB) | FKs | Notes |
|-------|---------|-----------|-------------|-----|-------|
| `agent_executions` | 26 | 26 | 8 | 1 | OK - matches |
| `agent_interactions` | 14 | 14 | 4 | 1 | OK |
| `agent_jobs` | 10 | 10 | 4 | 2 | OK |
| `agent_templates` | 32 | 31 | 9 | 1 | +1 DB col: `template_content` |
| `agent_todo_items` | 8 | 8 | 3 | 1 | OK |
| `api_keys` | 11 | 11 | 7 | 1 | 1 dup index, 1 redundant index |
| `api_metrics` | 5 | 5 | 3 | 0 | OK |
| `configurations` | 11 | 10 | 3 | 1 | +1 DB col: `user_id` |
| `context_index` | 15 | 15 | 4 | 1 | OK |
| `discovery_config` | 10 | 10 | 3 | 1 | OK |
| `download_tokens` | 13 | 11 | 7 | 0 | +2 DB cols: `is_used`, `downloaded_at` |
| `git_commits` | 22 | 22 | 7 | 1 | OK |
| `git_configs` | 27 | 27 | 5 | 0 | OK |
| `jobs` | 10 | 10 | 2 | 0 | OK |
| `large_document_index` | 10 | 10 | 3 | 1 | OK |
| **`mcp_agent_jobs`** | **35** | **0** | **15** | **2** | **ORPHANED - no model** |
| `mcp_context_index` | 12 | 12 | 8 | 2 | OK |
| `mcp_context_summary` | 10 | 10 | 5 | 1 | OK |
| `mcp_sessions` | 10 | 10 | 11 | 3 | 1 dup index |
| `messages` | 21 | 21 | 5 | 1 | OK |
| `optimization_metrics` | 9 | 9 | 6 | 0 | 1 dup index |
| `optimization_rules` | 11 | 11 | 5 | 0 | 1 dup index |
| `org_memberships` | 8 | 8 | 4 | 3 | OK |
| `organizations` | 8 | 8 | 3 | 0 | OK |
| `product_memory_entries` | 26 | 26 | 7 | 2 | OK |
| `products` | 21 | 21 | 8 | 1 | server_default mismatch |
| `projects` | 24 | 23 | 6 | 1 | +1 DB col: `context_budget` |
| `settings` | 6 | 6 | 4 | 0 | 1 dup index |
| `setup_state` | 23 | 23 | 10 | 0 | 1 dup index |
| `tasks` | 21 | 21 | 12 | 6 | FK targets wrong table |
| `template_archives` | 24 | 23 | 5 | 1 | +1 DB col: `template_content` |
| `template_usage_stats` | 11 | 11 | 4 | 2 | OK |
| `users` | 19 | 19 | 8 | 1 | 1 dup index |
| `vision_documents` | 25 | 25 | 11 | 1 | 1 dup index |

**Totals**: 35 DB tables, 34 model tables, 233 DB indexes, 40 FK constraints.

---

## Deprecated Column Audit

| Column | Table | Model Status | DB Status | Notes |
|--------|-------|-------------|-----------|-------|
| `AgentExecution.messages` (JSONB) | `agent_executions` | REMOVED (0700c) | GONE | Correctly removed from both |
| `Product.product_memory.sequential_history` | `products` | REMOVED from server_default (0700c) | Still in server_default | P0-2: server_default not updated |
| `template_content` | `agent_templates` | REMOVED from model | EXISTS in DB | P1-3: Legacy column persists |
| `template_content` | `template_archives` | REMOVED from model | EXISTS in DB | P1-3: Legacy column persists |
| `is_used` | `download_tokens` | REMOVED from model | EXISTS in DB | P1-2: Legacy column persists |
| `downloaded_at` | `download_tokens` | REMOVED from model | EXISTS in DB | P1-2: Legacy column persists |
| `user_id` | `configurations` | Never in model | EXISTS in DB | P1-5: Ghost column |
| `context_budget` | `projects` | Never in current model | EXISTS in DB | P2-1: Moved to AgentExecution |

---

## Missing Index Analysis

| Table | Column | Query Pattern | Impact |
|-------|--------|---------------|--------|
| `agent_interactions` | `tenant_key` | Index exists | OK |
| `agent_jobs` | `template_id` | FK queries | Index missing in DB (not critical - low cardinality) |
| `messages` | `tenant_key, project_id` | Composite for tenant-scoped project message queries | Would benefit from composite index |
| `tasks` | `tenant_key, product_id` | Task listing by tenant+product | Would benefit from composite index |
| `products` | `tenant_key, is_active` | Active product lookup per tenant | Covered by partial unique index |

Overall index coverage is very thorough. The codebase has invested heavily in indexing. No critical missing indexes were identified.

---

## Foreign Key Integrity Summary

| Relationship | Model Cascade | DB ondelete | Status |
|-------------|---------------|-------------|--------|
| `products -> projects` | `all, delete-orphan` | CASCADE | MATCH |
| `products -> tasks` | `all, delete-orphan` | CASCADE | MATCH |
| `products -> vision_documents` | `all, delete-orphan` | CASCADE | MATCH |
| `products -> product_memory_entries` | `all, delete-orphan` | CASCADE | MATCH |
| `users -> api_keys` | `all, delete-orphan` | CASCADE | MATCH |
| `organizations -> org_memberships` | `all, delete-orphan` | CASCADE | MATCH |
| `agent_jobs -> agent_executions` | `all, delete-orphan` | NO ACTION | MISMATCH (P2-2) |
| `agent_jobs -> agent_todo_items` | `all, delete-orphan` | CASCADE | MATCH |
| `projects -> messages` | `all, delete-orphan` | NO ACTION | MISMATCH (P2-3) |
| `projects -> context_index` | `all, delete-orphan` | NO ACTION | MISMATCH (P2-3) |
| `projects -> large_document_index` | `all, delete-orphan` | NO ACTION | MISMATCH (P2-3) |
| `vision_documents -> mcp_context_index` | `all, delete-orphan` | CASCADE | MATCH |
| `product_memory_entries -> projects` | (back_populates) | SET NULL | MATCH |
| `users -> organizations` | (back_populates) | SET NULL | MATCH |
| `mcp_sessions -> projects` | (backref) | SET NULL | MATCH |
| `tasks.job_id -> agent_jobs` | (model FK) | N/A -- points to wrong table | **BROKEN (P0-1)** |

---

## False Positive Analysis

To ensure rigor, 20 columns were validated as NOT false positives:

1. `agent_executions.messages_sent_count` -- Used in `agent_job_manager.py` (confirmed active)
2. `agent_executions.messages_waiting_count` -- Used in WebSocket events (confirmed active)
3. `agent_executions.messages_read_count` -- Used in agent coordination (confirmed active)
4. `agent_executions.mission_acknowledged_at` -- Set by `get_agent_mission()` MCP tool (confirmed active)
5. `products.consolidated_vision_light` -- Used by `fetch_context` for vision summaries (confirmed active)
6. `products.consolidated_vision_hash` -- Used for change detection in summarization (confirmed active)
7. `products.target_platforms` -- Used by product service for platform filtering (confirmed active)
8. `products.quality_standards` -- Used by context tools for testing category (confirmed active)
9. `projects.staging_status` -- Used by staging workflow in project service (confirmed active)
10. `projects.execution_mode` -- Used by LaunchTab UI for execution mode toggle (confirmed active)
11. `projects.closeout_checklist` -- Used by orchestrator closeout workflow (confirmed active)
12. `agent_templates.last_exported_at` -- Used by `may_be_stale` property (confirmed active)
13. `agent_templates.cli_tool` -- Used for multi-CLI tool support (confirmed active)
14. `vision_documents.is_summarized` -- Used by summarization pipeline (confirmed active)
15. `vision_documents.summary_light` -- Used by consolidated vision builder (confirmed active)
16. `product_memory_entries.significance_score` -- Used by memory prioritization (confirmed active)
17. `product_memory_entries.deleted_by_user` -- Used by soft-delete tracking (confirmed active)
18. `setup_state.first_admin_created` -- Used by security check in auth endpoints (confirmed active)
19. `agent_todo_items.sequence` -- Used for display ordering (confirmed active)
20. `download_tokens.staging_status` -- Used by download lifecycle (confirmed active)

All 20 columns are actively used in codebase. None are false positives for removal.

---

## Recommendations

### Immediate (Migration Required)

1. **Drop `mcp_agent_jobs` table** (P0-1):
   - Drop FK `fk_task_job` from `tasks`
   - Create replacement FK: `tasks.job_id -> agent_jobs.job_id`
   - Drop table `mcp_agent_jobs` (0 rows)
   - Estimated risk: LOW (table is empty, no active code references it)

2. **Fix `products.product_memory` server_default** (P0-2):
   ```sql
   ALTER TABLE products
   ALTER COLUMN product_memory
   SET DEFAULT '{"github": {}, "context": {}}'::jsonb;
   ```

3. **Drop 11 duplicate indexes** (P1-1):
   ```sql
   DROP INDEX ix_api_keys_tenant_key;
   DROP INDEX ix_download_tokens_tenant_key;
   DROP INDEX ix_mcp_agent_jobs_project_id;
   DROP INDEX ix_mcp_sessions_tenant_key;
   DROP INDEX ix_optimization_metrics_tenant_key;
   DROP INDEX ix_optimization_rules_tenant_key;
   DROP INDEX ix_products_tenant_key;
   DROP INDEX ix_settings_tenant_key;
   DROP INDEX ix_setup_state_database_initialized;
   DROP INDEX ix_users_tenant_key;
   DROP INDEX ix_vision_documents_tenant_key;
   ```

4. **Drop legacy columns** (P1-2, P1-3, P1-5, P2-1):
   ```sql
   ALTER TABLE download_tokens DROP COLUMN is_used;
   ALTER TABLE download_tokens DROP COLUMN downloaded_at;
   ALTER TABLE agent_templates DROP COLUMN template_content;
   ALTER TABLE template_archives DROP COLUMN template_content;
   ALTER TABLE configurations DROP COLUMN user_id;
   ALTER TABLE projects DROP COLUMN context_budget;
   ```

### Short-Term (Model Updates)

5. **Fix index name mismatches** (P1-4) -- Update model files to match DB:
   - `templates.py:115`: `idx_agent_templates_org` -> `idx_template_org_id`
   - `products.py:160`: `idx_products_org` -> `idx_product_org_id`
   - `tasks.py:101`: `idx_tasks_org` -> `idx_task_org_id`

### Medium-Term (FK Hardening)

6. **Add `ondelete="CASCADE"` to FK definitions** (P2-2, P2-3, P2-4):
   - `agent_executions.job_id` FK
   - `context_index.project_id` FK
   - `large_document_index.project_id` FK
   - `messages.project_id` FK
   - `agent_jobs.project_id` FK
   - `agent_interactions.project_id` FK
   - `discovery_config.project_id` FK

---

## Migration Strategy

All changes should be consolidated into a single migration file following the project's baseline migration approach. Recommended order:

1. Drop the `fk_task_job` constraint from `tasks`
2. Create new FK `tasks.job_id -> agent_jobs.job_id`
3. Drop `mcp_agent_jobs` table
4. Drop legacy columns from 4 tables
5. Drop 11 duplicate indexes
6. Update `products.product_memory` default
7. Update FK constraints to add CASCADE where needed

**Risk Assessment**: LOW for all changes. The `mcp_agent_jobs` table has 0 rows. All dropped columns are unused in active code. Duplicate indexes are purely redundant. FK cascade changes only affect raw SQL operations (ORM already handles cascade).

**Rollback**: Standard Alembic downgrade with `op.create_table` / `op.add_column` / `op.create_index` for all dropped items.
