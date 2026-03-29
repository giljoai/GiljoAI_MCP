# Handover 0844a: Tenant Data Export Service

**Date:** 2026-03-29
**From Agent:** Planning Session
**To Agent:** Next Session
**Priority:** Medium
**Estimated Complexity:** 1-2 sessions
**Status:** Not Started
**Edition Scope:** CE
**Series:** 0844a of 0844a/b/c — read `0844_tenant_data_export_import.md` first for shared context

---

## 1. Task Summary

Build the backend export engine that serializes all tenant-scoped data into a portable ZIP file, strips credentials and tenant identity, includes vision document files from disk, and exposes a single API endpoint. This is the foundation — 0844b (import) and 0844c (frontend) depend on the export format and manifest schema defined here.

---

## 2. Context and Background

See `0844_tenant_data_export_import.md` for full context, model registry, field stripping maps, and manifest schema.

Key points for this phase:
- 31 models exported in FK dependency order (11 groups)
- `tenant_key` stripped from all records globally
- Credential fields stripped per model (`CREDENTIAL_FIELDS` map)
- TSVECTOR field skipped on MCPContextIndex (`SKIP_FIELDS` map)
- Vision files from `./products/{product_id}/vision/` included in ZIP
- Per-file SHA-256 checksums in manifest
- `REPEATABLE READ` transaction for snapshot consistency

---

## 3. Technical Details

### Files to Create

| File | Purpose |
|------|---------|
| `src/giljo_mcp/services/tenant_export_service.py` | Export engine — model registry, serialization, field stripping, vision file bundling, ZIP creation |
| `api/endpoints/tenant_data.py` | Export endpoint (import endpoints added in 0844b) |
| `tests/test_tenant_export_service.py` | Unit + integration tests |

### Files to Modify

| File | Change |
|------|--------|
| `api/app.py` | Register `tenant_data.router` with prefix `/api/v1/settings` |

### TenantExportService Design

```python
class TenantExportService:
    """Exports all tenant-scoped data to a portable ZIP."""

    # Ordered model registry — parents before children
    EXPORT_MODELS: list[tuple[type, ExportConfig]]

    GLOBAL_STRIP = {"tenant_key"}
    CREDENTIAL_FIELDS = {
        "User": {"password_hash", "recovery_pin_hash"},
        "GitConfig": {"password_encrypted", "ssh_key_encrypted", "webhook_secret"},
    }
    SKIP_FIELDS = {
        "MCPContextIndex": {"searchable_vector"},
    }

    async def export_all(self, progress_callback=None) -> Path:
        """Export all tenant data to a ZIP file on disk. Returns path to temp ZIP."""

    async def _export_model(self, model_class, config) -> list[dict]:
        """Query and serialize all rows for one model."""

    def _serialize_row(self, row, model_name) -> dict:
        """Convert ORM row to dict, stripping sensitive/skip fields."""

    async def _bundle_vision_files(self, vision_docs, zip_file) -> list[dict]:
        """Add vision files from disk to ZIP, return manifest file entries."""

    def _build_manifest(self, model_results, file_entries) -> dict:
        """Build manifest.json with checksums and metadata."""
```

### Serialization Rules

| Column Type | Serialization |
|-------------|---------------|
| DateTime | ISO 8601 with timezone (`dt.isoformat()`) |
| JSONB | Native Python dict (JSON-serializable already) |
| ARRAY (e.g. `product.target_platforms`) | Python list (JSON array) |
| TSVECTOR (`mcp_context_index.searchable_vector`) | **Skip** — regenerated on import |
| UUID (native, `ProductMemoryEntry.id`) | `str(uuid)` |
| String(36) UUID (all other PKs) | As-is (already a string) |
| Integer PK (`MCPContextIndex.id`) | As-is (integer) |

### Read Consistency

Wrap the entire export in `REPEATABLE READ`:
```python
async with session.begin():
    await session.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ"))
    # All 31 model queries see the same snapshot
```

### Vision File Bundling

After exporting VisionDocument DB rows:
1. Scan exported VisionDocument records for `vision_path` where `storage_type` in (`"file"`, `"hybrid"`)
2. If file exists at the referenced path on disk, add to ZIP under `files/{vision_path}`
3. Compute SHA-256 of each file, add to `manifest.files.entries`
4. If file doesn't exist on disk, log WARNING but don't fail (DB text content is still in the JSON export)

### ZIP Structure

```
export.zip
├── manifest.json           # Metadata, checksums, model counts
├── data/
│   ├── organizations.json  # One file per model
│   ├── users.json
│   ├── products.json
│   ├── ...                 # 31 model files
│   └── optimization_rules.json
└── files/
    └── products/
        └── <product_id>/
            └── vision/
                └── readme.md   # Original vision files from disk
```

### Export Endpoint

```python
# POST /api/v1/settings/export
# Auth: require_admin
# Returns: {"download_url": "/api/download/temp/{token}/{filename}", "expires_at": "...", "model_counts": {...}}
```

- Use existing `DownloadToken` model for the temp download URL
- Build ZIP to `NamedTemporaryFile` on disk (not BytesIO)
- Stage ZIP at download path, create token with 15-min TTL
- Send WebSocket progress: `tenant:export_progress` with `{model, current, total, records, phase: "exporting"}`
- Log at INFO: timestamp, admin user, record counts, ZIP size in bytes

---

## 4. Implementation Plan

### Step 1: Model Registry
Define `EXPORT_MODELS` as an ordered list of `(ModelClass, ExportConfig)` tuples. The ordering must match the 11 groups from the coordinator doc. Use actual SQLAlchemy model classes imported from `src/giljo_mcp/models/`.

### Step 2: Serialization Engine
Implement `_serialize_row()` — iterate over model columns via `Model.__table__.columns`, apply `GLOBAL_STRIP`, `CREDENTIAL_FIELDS`, `SKIP_FIELDS`. Handle DateTime, UUID, and other types.

### Step 3: Export Pipeline
Implement `export_all()`:
1. Set `REPEATABLE READ` on the session
2. For each model in registry: query with `tenant_key` filter, serialize rows, write JSON to ZIP
3. After VisionDocument export: call `_bundle_vision_files()`
4. Build manifest with per-file SHA-256 checksums
5. Write manifest.json as the last entry in the ZIP
6. Return path to the temp ZIP file

### Step 4: API Endpoint + Router
Create `api/endpoints/tenant_data.py` with the export endpoint. Register in `app.py`. Use existing `require_admin` dependency from `api/dependencies/`. Use existing `DownloadToken` pattern from `api/endpoints/downloads.py`.

### Step 5: Tests
Write tests covering:
- Serialization of each column type (DateTime, JSONB, ARRAY, UUID)
- Credential stripping (verify password_hash absent from User export)
- TSVECTOR skip (verify searchable_vector absent from MCPContextIndex export)
- Vision file inclusion (create a test product with a vision file, verify it's in the ZIP)
- Manifest accuracy (record counts, checksums match)
- Empty tenant export (no data, still produces valid ZIP with empty model files)
- Admin-only auth (403 for non-admin)

---

## 5. Testing Requirements

### Unit Tests (`tests/test_tenant_export_service.py`)
- `test_serialize_datetime_to_iso8601`
- `test_serialize_jsonb_as_dict`
- `test_serialize_array_as_list`
- `test_strip_tenant_key_from_all_models`
- `test_strip_user_credentials`
- `test_strip_gitconfig_credentials`
- `test_skip_tsvector_field`
- `test_manifest_checksums_match_file_contents`
- `test_vision_files_included_in_zip`
- `test_missing_vision_file_logs_warning_not_error`
- `test_empty_tenant_produces_valid_zip`
- `test_model_dependency_order`

### Integration Tests
- `test_export_endpoint_requires_admin`
- `test_export_endpoint_returns_download_url`
- `test_full_export_roundtrip_produces_valid_zip`

---

## 6. Quality Gate: MANDATORY Manual Verification

**Before 0844b can start, the user MUST:**
1. Run the export on the live instance with real data
2. Extract the ZIP
3. Run: `grep -ri "password\|secret\|hash\|tenant_key" data/*.json`
4. Verify ZERO matches (except `manifest.json` tenant_key provenance field)
5. Verify `files/` directory contains expected vision files
6. Open `manifest.json` — verify record counts are plausible

**Risk R1 (credential leak) is the highest-severity risk in the series. This manual gate is non-negotiable.**

---

## 7. Dependencies and Blockers

**Dependencies (all already in place):**
- SQLAlchemy models: `src/giljo_mcp/models/` (all 31+ models)
- DownloadToken model: `src/giljo_mcp/models/config.py`
- Download infrastructure: `api/endpoints/downloads.py` (reference pattern)
- WebSocket manager: `api/websocket_manager.py`
- `require_admin` dependency: `api/dependencies/`
- `get_db`, `get_tenant_key` dependencies

**Known Blockers:** None.

---

## 8. Success Criteria

- `POST /api/v1/settings/export` returns a download URL for a valid ZIP
- ZIP contains `manifest.json` + `data/*.json` (31 model files) + `files/` (vision files)
- No `tenant_key` values in any data JSON file
- No credential values (`password_hash`, `recovery_pin_hash`, etc.) in any data JSON file
- Per-file SHA-256 checksums in manifest match actual file contents
- Vision files from `./products/*/vision/` included when they exist on disk
- Export uses `REPEATABLE READ` transaction
- ZIP is written to temp file on disk, not held in memory
- WebSocket progress events fire during export
- 403 for non-admin users
- All tests pass, ruff clean

---

## 9. Rollback Plan

Delete `tenant_export_service.py`, `tenant_data.py`, `test_tenant_export_service.py`. Remove router registration from `app.py`. Zero impact on existing functionality.

---

## 10. Additional Resources

- Existing download pattern to reference: `api/endpoints/downloads.py` (ZIP creation, DownloadToken)
- Model files: `src/giljo_mcp/models/` — auth.py, products.py, projects.py, tasks.py, agent_identity.py, templates.py, config.py, settings.py, organizations.py, context.py, product_memory_entry.py, oauth.py
- Base model with `generate_uuid()`: `src/giljo_mcp/models/base.py`
- Vision upload handler (reference for file paths): `api/endpoints/vision_documents.py:207-254`
- Settings endpoint pattern: `api/endpoints/settings.py`

---

## Chain Execution Instructions (Orchestrator-Gated v3)

You are **session 1 of 3** in the 0844 chain. You are on branch `feature/0844-tenant-data-export-import`.

### Step 1: Read Chain Log
Read `prompts/0844_chain/chain_log.json`
- Check `orchestrator_directives` — if contains "STOP", halt immediately
- This is the first session, so no previous `notes_for_next` to review

### Step 2: Read Shared Context
Read `handovers/0844_tenant_data_export_import.md` — the series coordinator. It contains the model registry, field stripping maps, manifest schema, and risk register that you must implement.

### Step 3: Mark Session Started
Update your session in `prompts/0844_chain/chain_log.json`:
```json
"status": "in_progress", "started_at": "<current ISO timestamp>"
```

### Step 4: Execute Handover Tasks
Implement everything in this document. Use `tdd-implementor` and `backend-tester` subagents.

### Step 5: Update Chain Log
Update your session in `prompts/0844_chain/chain_log.json` with:
- `tasks_completed`: list of what you actually did
- `deviations`: any differences from the plan (different method names, skipped steps, alternative approaches)
- `blockers_encountered`: any issues
- `notes_for_next`: **CRITICAL — be specific.** Include exact class names, method signatures, file paths, the actual model registry order you used, any serialization details the import engine needs to know. The 0844b agent will build the import engine that reads your export format.
- `cascading_impacts`: changes that affect 0844b or 0844c
- `summary`: 2-3 sentences including commit hash
- `status`: "complete"
- `completed_at`: ISO timestamp

### Step 6: Commit and STOP
```bash
git add -A && git commit -m "feat(0844a): tenant export service — model registry, field stripping, vision file bundling, ZIP creation"
```
Update the chain log:
```bash
git add prompts/0844_chain/chain_log.json && git commit -m "docs: 0844a chain log — session complete"
```

**Do NOT spawn the next terminal.** The orchestrator will:
1. Review your chain log entries
2. Perform the MANDATORY manual verification gate (grep for credential leaks)
3. Update 0844b handover if any deviations require it
4. Spawn the 0844b terminal when ready
