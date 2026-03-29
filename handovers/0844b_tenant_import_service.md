# Handover 0844b: Tenant Data Import Service + Schema Diff Engine

**Date:** 2026-03-29
**From Agent:** Planning Session
**To Agent:** Next Session
**Priority:** Medium
**Estimated Complexity:** 2-3 sessions (heaviest phase in the series)
**Status:** Not Started
**Edition Scope:** CE
**Series:** 0844b of 0844a/b/c — read `0844_tenant_data_export_import.md` first for shared context
**Depends On:** 0844a must be complete and manually verified (see Quality Gate below)

---

## 1. Task Summary

Build the import engine that takes a ZIP produced by 0844a's export, analyzes schema compatibility across versions, UPSERTs all data with fresh tenant identity, extracts vision files, and regenerates computed fields. This is the architecturally hardest phase — it holds the schema diff engine, FK-ordered UPSERT pipeline, topological sort for self-referential models, and vision file extraction tied to Product insert order.

---

## 2. Context and Background

See `0844_tenant_data_export_import.md` for full context, model registry, field stripping maps, manifest schema, and risk register.

**Pre-condition:** 0844a must be complete. The export endpoint must work and the user must have manually verified (Risk R1 gate) that no credentials leak in the ZIP. The import engine reads the exact ZIP format defined by 0844a.

**This phase has the most integration seams:**
- Checksum verification before any DB write
- Schema introspection and column diff classification
- UPSERT with correct FK ordering across 31 models
- Topological sort for Task self-referential parent_task_id
- Vision file extraction after Product + VisionDocument import
- TSVECTOR regeneration after MCPContextIndex import
- All wrapped in a single atomic transaction

---

## 3. Technical Details

### Files to Create

| File | Purpose |
|------|---------|
| `src/giljo_mcp/services/tenant_import_service.py` | Import engine — checksum verification, schema diff, UPSERT pipeline, file extraction, TSVECTOR regeneration |
| `tests/test_tenant_import_service.py` | Unit + integration tests |

### Files to Modify

| File | Change |
|------|--------|
| `api/endpoints/tenant_data.py` (created in 0844a) | Add analyze + execute endpoints |

### TenantImportService Design

```python
@dataclass
class SchemaCompatibilityReport:
    is_compatible: bool                           # True if core data can import
    same_version: bool                            # Exact alembic match
    export_revision: str
    current_revision: str
    exported_at: str                              # ISO 8601 — used for stale backup warning in frontend
    dropped_columns: dict[str, list[str]]         # model -> [col1, col2] (in export, not in schema)
    new_nullable_columns: dict[str, list[str]]    # model -> [col1, col2] (in schema, not in export)
    new_required_columns: dict[str, list[str]]    # model -> [col1, col2] (WARNING: no default)
    missing_models: list[str]                     # models in export not recognized by current app
    new_models: list[str]                         # models in current app not present in export
    warnings: list[str]                           # human-readable warning strings
    model_counts: dict[str, int]                  # model -> record count from export

@dataclass
class ImportResult:
    success: bool
    models_imported: dict[str, ModelImportResult]  # model -> {inserted, updated, skipped}
    files_extracted: int
    files_skipped: int                             # already existed at target path
    warnings: list[str]
    tsvector_regenerated: int                      # MCPContextIndex rows regenerated

@dataclass
class ModelImportResult:
    inserted: int
    updated: int
    skipped: int
    errors: list[str]

class TenantImportService:
    # Uses same EXPORT_MODELS registry from TenantExportService for FK ordering

    async def verify_checksums(self, zip_file, manifest) -> list[str]:
        """Verify all per-file SHA-256 checksums. Returns list of failed files. If any fail, reject import entirely."""

    async def analyze(self, zip_file, manifest) -> SchemaCompatibilityReport:
        """Schema diff: compare export JSON keys against current SQLAlchemy model columns."""

    async def execute(self, zip_file, manifest, report, tenant_key, progress_callback=None) -> ImportResult:
        """Full import pipeline inside a single transaction."""

    async def _import_model(self, model_class, records, tenant_key) -> ModelImportResult:
        """UPSERT records for one model. Injects tenant_key, applies IMPORT_OVERRIDES."""

    def _topological_sort_tasks(self, task_records) -> list[dict]:
        """Sort Task records so parent_task_id=null first, then children by depth."""

    async def _extract_vision_files(self, zip_file, manifest) -> tuple[int, int]:
        """Extract files/ from ZIP to working directory. Skip existing files. Returns (extracted, skipped)."""

    async def _regenerate_tsvectors(self, tenant_key) -> int:
        """UPDATE mcp_context_index SET searchable_vector = to_tsvector(...) WHERE tenant_key = :tk AND searchable_vector IS NULL"""
```

---

## 4. Schema Compatibility Engine (The Core Innovation)

This is the most architecturally novel piece. It must be precise — not over-engineered (no type change detection, no column rename guessing) and not under-engineered (must classify nullable vs. required).

### Algorithm

For each model in the export:
1. Get the model's current column names: `{c.name for c in Model.__table__.columns}`
2. Get the export's JSON keys from the first record (or from manifest if model is empty)
3. Subtract `GLOBAL_STRIP` and model-specific stripped fields from both sets
4. Classify the diff:

```python
export_keys = set(records[0].keys()) if records else set()
current_cols = {c.name for c in Model.__table__.columns} - GLOBAL_STRIP - CREDENTIAL_FIELDS.get(model_name, set()) - SKIP_FIELDS.get(model_name, set())

dropped = export_keys - current_cols      # In export, not in current schema
new_cols = current_cols - export_keys     # In current schema, not in export

for col_name in new_cols:
    col = Model.__table__.columns[col_name]
    if col.nullable or col.server_default is not None:
        new_nullable_columns[model_name].append(col_name)
    else:
        new_required_columns[model_name].append(col_name)  # WARNING
```

### Important: What NOT to do
- Do NOT try to detect column renames (too fragile, false positives)
- Do NOT try to detect type changes (UPSERT will either work or raise)
- Do NOT try to auto-migrate data between schemas — just report the diff
- DO classify new columns as nullable vs. required — this is the whole value

---

## 5. UPSERT Pipeline

### FK Dependency Order

Import models in the EXACT order defined in `EXPORT_MODELS` (same as export). Parents before children. This order is critical — getting it wrong produces FK violations.

### UPSERT Mechanics

```python
from sqlalchemy.dialects.postgresql import insert

stmt = insert(Model).values(records_with_tenant_key)
stmt = stmt.on_conflict_do_update(
    index_elements=[Model.id],  # or Model.job_id for AgentJob
    set_={col: stmt.excluded[col] for col in update_columns}
)
await session.execute(stmt)
```

**Per-record processing before UPSERT:**
1. Inject `tenant_key` (from importing user's session)
2. Apply `IMPORT_OVERRIDES` for the model (e.g., `must_change_password=True` for User)
3. Drop any keys not in current model columns (the "dropped columns" from schema diff)
4. Set `None` for any new nullable columns not present in the record

### Special Cases

**AgentJob PK:** Uses `job_id` as column name, not `id`. The UPSERT conflict target must be `AgentJob.job_id`.

**MCPContextIndex:** Has Integer PK (autoincrement) but also has `chunk_id` String(36) UUID. The UPSERT conflict target should be `chunk_id` (the semantic unique key), NOT the integer `id`. On conflict, update the row. The integer `id` gets auto-assigned on insert.

**ProductMemoryEntry:** Uses native PostgreSQL UUID type (`UUID(as_uuid=True)`) with `default=uuid4`. Serialize as string in export, deserialize back to UUID on import using `uuid.UUID(str_value)`.

### Task Topological Sort

`Task.parent_task_id` is self-referential. Import order matters.

```python
def _topological_sort_tasks(self, records: list[dict]) -> list[dict]:
    """Sort so parent_task_id=None first, then children by depth."""
    by_id = {r["id"]: r for r in records}
    result = []
    visited = set()

    def visit(record):
        if record["id"] in visited:
            return
        parent_id = record.get("parent_task_id")
        if parent_id and parent_id in by_id and parent_id not in visited:
            visit(by_id[parent_id])
        visited.add(record["id"])
        result.append(record)

    for r in records:
        visit(r)
    return result
```

Alternative (simpler, slightly less efficient): two-pass approach — insert all tasks with `parent_task_id` set to `None`, then UPDATE to restore parent references. This avoids the sort entirely but requires an extra UPDATE pass.

---

## 6. Vision File Extraction

This is a **pipeline step, not an afterthought.** It runs AFTER Product and VisionDocument UPSERT succeeds.

```python
async def _extract_vision_files(self, zip_file, manifest) -> tuple[int, int]:
    extracted, skipped = 0, 0
    for entry in manifest.get("files", {}).get("entries", []):
        zip_path = entry["zip_path"]       # e.g., "files/products/<uuid>/vision/readme.md"
        target_path = zip_path[6:]         # Strip "files/" prefix → "products/<uuid>/vision/readme.md"

        target = Path(target_path)
        if target.exists():
            skipped += 1                   # Don't overwrite newer local files
            continue

        target.parent.mkdir(parents=True, exist_ok=True)
        with zip_file.open(zip_path) as src, open(target, "wb") as dst:
            dst.write(src.read())
        extracted += 1
    return extracted, skipped
```

**Why it depends on Product import:** The `vision_path` values like `./products/{product_id}/vision/file.md` use the Product UUID. Since we preserve UUIDs on UPSERT (not remapping), the paths remain valid. But the Product record must exist in the DB before we create directories for its vision files — otherwise a failed import could leave orphaned directories.

---

## 7. API Endpoints (Added to tenant_data.py)

### POST /api/v1/settings/import/analyze

```python
# Accepts: multipart/form-data with ZIP file
# Returns: SchemaCompatibilityReport as JSON
# Side effect: stages ZIP in temp dir, creates DownloadToken with download_type='import_staging' and 15-min TTL
# The analysis_token is returned so the execute endpoint can retrieve the staged ZIP
```

### POST /api/v1/settings/import/execute

```python
# Accepts: {"analysis_token": "<uuid>"}
# Returns: ImportResult as JSON
# Pipeline:
#   1. Retrieve staged ZIP via analysis_token
#   2. Acquire pg_advisory_lock(844) — reject if another import is running
#   3. Verify all per-file checksums
#   4. Begin transaction
#   5. UPSERT models in FK order, applying tenant_key + overrides
#   6. Extract vision files
#   7. Regenerate TSVECTOR for MCPContextIndex
#   8. Commit transaction
#   9. Release advisory lock
#   10. Send WebSocket: tenant:import_progress
#   11. Log at INFO: timestamp, admin, manifest details, per-model counts
```

---

## 8. Implementation Plan

### Step 1: SchemaCompatibilityReport + analyze()
Build the schema diff engine first — it's testable in isolation. Introspect SQLAlchemy models, compare against mock export data with missing/extra columns.

### Step 2: Checksum Verification
Implement `verify_checksums()`. Test with a tampered JSON file — verify rejection.

### Step 3: UPSERT Pipeline
Implement `_import_model()` with tenant_key injection, IMPORT_OVERRIDES, and column filtering. Start with a simple model (Organization) and verify round-trip works.

### Step 4: Special Cases
Handle AgentJob.job_id PK, MCPContextIndex chunk_id conflict target, ProductMemoryEntry UUID type, Task topological sort.

### Step 5: Vision File Extraction
Implement `_extract_vision_files()` as a method called after VisionDocument UPSERT. Test with a product that has vision files.

### Step 6: TSVECTOR Regeneration
Single SQL UPDATE after all MCPContextIndex records imported.

### Step 7: Transaction Wrapping + Advisory Lock
Wrap the full pipeline in `async with session.begin()` + `pg_advisory_lock(844)`.

### Step 8: API Endpoints
Add analyze + execute endpoints to `tenant_data.py`. Wire the analysis token staging via DownloadToken.

### Step 9: Integration Test — Full Round-Trip
**This test is the single most important quality gate.** Export all data, import into a clean DB (or with different tenant_key), verify data integrity.

---

## 9. Testing Requirements

### Unit Tests (`tests/test_tenant_import_service.py`)

**Schema diff engine:**
- `test_same_version_no_diffs`
- `test_dropped_column_classified_correctly`
- `test_new_nullable_column_classified_correctly`
- `test_new_required_column_classified_as_warning`
- `test_missing_model_in_current_app`
- `test_new_model_not_in_export`
- `test_empty_export_is_compatible`

**Checksum verification:**
- `test_valid_checksums_pass`
- `test_tampered_file_rejected`
- `test_missing_file_rejected`

**UPSERT pipeline:**
- `test_tenant_key_injected_into_all_records`
- `test_import_overrides_applied_to_user`
- `test_import_overrides_applied_to_gitconfig`
- `test_upsert_inserts_new_records`
- `test_upsert_updates_existing_records`
- `test_dropped_columns_ignored_on_import`
- `test_transaction_rollback_on_error`

**Special cases:**
- `test_agentjob_uses_job_id_as_conflict_target`
- `test_mcp_context_index_uses_chunk_id_as_conflict_target`
- `test_product_memory_entry_uuid_type_handled`
- `test_task_topological_sort_parents_before_children`
- `test_task_topological_sort_handles_orphaned_parents`

**Vision files:**
- `test_vision_files_extracted_to_correct_paths`
- `test_existing_files_not_overwritten`
- `test_directories_created_as_needed`

**TSVECTOR:**
- `test_tsvector_regenerated_after_import`

### Integration Tests
- `test_analyze_endpoint_requires_admin`
- `test_execute_endpoint_requires_admin`
- `test_full_roundtrip_export_then_import`
- `test_cross_version_import_with_schema_diff`
- `test_corrupt_zip_rejected`
- `test_advisory_lock_prevents_concurrent_imports`

---

## 10. Quality Gate: MANDATORY Manual Verification

**Before 0844c can start, the user MUST:**
1. Run full round-trip: export from live instance → import into clean test DB
2. Start the server against the imported DB
3. Navigate: products, projects, agents, vision docs — verify data is correct
4. Test search (verifies TSVECTOR regeneration)
5. Check `./products/*/vision/` — verify vision files extracted correctly
6. Try importing a second time — verify UPSERT updates, doesn't duplicate

**Risks R2 (FK order), R3 (silent corruption), R4 (vision paths), R5 (schema engine) are all verified by this gate.**

---

## 11. Dependencies and Blockers

**Dependencies:**
- **0844a must be complete and manually verified** (Risk R1 gate passed)
- `TenantExportService` and `EXPORT_MODELS` registry (created in 0844a)
- `tenant_data.py` endpoint file (created in 0844a, extended here)
- All existing models, services, and dependencies already in place

**Known Blockers:** None.

---

## 12. Success Criteria

- `POST /api/v1/settings/import/analyze` returns accurate SchemaCompatibilityReport
- Schema diff correctly classifies dropped, new-nullable, and new-required columns
- Checksum verification rejects tampered/corrupt files before any DB write
- `POST /api/v1/settings/import/execute` UPSERTs all data with correct FK ordering
- Task self-referential records import in parent-before-child order
- Vision files extracted to correct `./products/{id}/vision/` paths, existing files skipped
- TSVECTOR regenerated for MCPContextIndex rows
- Entire import is atomic — rollback on any error, no partial state
- Advisory lock prevents concurrent imports
- Import injects fresh tenant_key, sets must_change_password on Users, nulls GitConfig credentials
- Full round-trip (export → import) produces identical data (minus excluded/stripped fields)
- All tests pass, ruff clean

---

## 13. Rollback Plan

Delete `tenant_import_service.py`, `test_tenant_import_service.py`. Remove analyze + execute endpoints from `tenant_data.py`. Zero impact — export still works standalone.

---

## Chain Execution Instructions (Orchestrator-Gated v3)

You are **session 2 of 3** in the 0844 chain. You are on branch `feature/0844-tenant-data-export-import`.

### Step 1: Read Chain Log
Read `prompts/0844_chain/chain_log.json`
- Check `orchestrator_directives` — if contains "STOP", halt immediately
- **Read 0844a's `notes_for_next` carefully** — it contains the exact class names, method signatures, model registry order, and serialization details you need. The export format you're importing against is defined by what 0844a actually built, not just what the handover planned.

### Step 2: Read Shared Context
Read `handovers/0844_tenant_data_export_import.md` — the series coordinator. It contains the model registry, field stripping maps, manifest schema, and risk register.

### Step 3: Verify Prerequisite
Confirm 0844a's session status is `"complete"` in the chain log. If not, STOP and report to orchestrator.

### Step 4: Mark Session Started
Update your session in `prompts/0844_chain/chain_log.json`:
```json
"status": "in_progress", "started_at": "<current ISO timestamp>"
```

### Step 5: Execute Handover Tasks
Implement everything in this document. Use `tdd-implementor` and `backend-tester` subagents.

**CRITICAL:** Read the actual `TenantExportService` code (created by 0844a) before building the import engine. Your import must read the exact ZIP format that was built, which may deviate from the plan.

### Step 6: Update Chain Log
Update your session in `prompts/0844_chain/chain_log.json` with:
- `tasks_completed`: list of what you actually did
- `deviations`: any differences from the plan
- `blockers_encountered`: any issues
- `notes_for_next`: **Be specific for the frontend agent.** Include exact endpoint response schemas (SchemaCompatibilityReport JSON shape, ImportResult JSON shape), WebSocket event payloads, and the analysis_token flow. The 0844c agent builds the UI against your API.
- `cascading_impacts`: changes that affect 0844c
- `summary`: 2-3 sentences including commit hash
- `status`: "complete"
- `completed_at`: ISO timestamp

### Step 7: Commit and STOP
```bash
git add -A && git commit -m "feat(0844b): tenant import service — schema diff engine, UPSERT pipeline, vision file extraction, TSVECTOR regeneration"
```
Update the chain log:
```bash
git add prompts/0844_chain/chain_log.json && git commit -m "docs: 0844b chain log — session complete"
```

**Do NOT spawn the next terminal.** The orchestrator will:
1. Review your chain log entries
2. Perform the MANDATORY manual verification gate (round-trip test + app walkthrough)
3. Update 0844c handover if any deviations require it (especially API response schemas)
4. Spawn the 0844c terminal when ready
