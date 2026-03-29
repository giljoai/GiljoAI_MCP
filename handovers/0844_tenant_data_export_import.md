# Handover 0844: Tenant Data Export/Import (Series Coordinator)

**Date:** 2026-03-29
**Priority:** Medium
**Status:** Not Started
**Edition Scope:** CE

---

## Series Overview

This is the **coordination document** for the 0844 series. Implementation is split into three sequential sub-handovers, each executable as an independent agent session.

| Sub-Handover | Scope | Effort | Dependency |
|--------------|-------|--------|------------|
| **0844a** | Backend Export Service | 1-2 sessions | None |
| **0844b** | Backend Import Service + Schema Diff | 2-3 sessions | 0844a (reads export format) |
| **0844c** | Frontend + Integration | 1 session | 0844a + 0844b (endpoints exist) |

**Total estimated effort:** 4-6 sessions, 12-20 agent-hours.

---

## What This Feature Does

Admin Settings > Database tab gets two new capabilities:
1. **Export** — Downloads all tenant data as a portable ZIP (credentials stripped, tenant identity removed)
2. **Import** — Uploads a ZIP, diffs schema versions, shows compatibility report, UPSERTs with fresh tenant identity

### Core Principle: Strip on Export, Apply on Import

The export ZIP is a **clean, portable, tenant-agnostic data package**. Zero credentials or tenant identity travel in the file. On import, the receiving instance injects its own tenant_key, forces credential resets, and extracts vision files to the correct paths.

---

## Risk Register (from PM Review)

These risks apply across the series. Each sub-handover references its relevant risks.

| # | Risk | Severity | Likelihood | Mitigation | Owner |
|---|------|----------|------------|------------|-------|
| R1 | Incomplete field stripping — credential leak in export | High | Medium | **MANDATORY manual gate after 0844a:** Open ZIP, grep for known test passwords and tenant_keys. Do not proceed to 0844b until verified. | User (manual) |
| R2 | FK dependency order wrong — import integrity errors | High | Medium | Round-trip integration test: export → import on clean DB. Catches immediately. | 0844b agent (automated) |
| R3 | Silent data corruption — JSONB deserialization, missing TSVECTOR | High | Low | After round-trip test, manually use the app: click through products, projects, agents. Verify search works. | User (manual) |
| R4 | Vision file path reconstruction fails | Medium | Medium | Test with at least one product that has vision documents with file uploads. | 0844b agent (automated) |
| R5 | Schema compatibility engine over/under-engineered | Medium | Medium | Test by temporarily adding a fake nullable column, export, remove column, import. Verify report classifies correctly. | 0844b agent (automated) |

### Mandatory Manual Verification Gates

**After 0844a completes — before starting 0844b:**
1. Run export on the live instance
2. Open the ZIP file manually
3. `grep -ri "password\|secret\|hash\|tenant_key" *.json` inside the extracted ZIP
4. Verify zero matches (except manifest.tenant_key provenance field)
5. Verify vision files are present under `files/`

**After 0844b completes — before starting 0844c:**
1. Run full round-trip: export → wipe test DB → import
2. Start the server, navigate the UI — products, projects, agents, vision docs
3. Verify search works (TSVECTOR regeneration)
4. Check vision file paths resolve correctly

**After 0844c completes — final sign-off:**
1. Full end-to-end test through the UI: export button → download → import button → analyze → confirm → complete
2. Verify stale backup warning shows correct date

---

## Shared Technical Context

All three sub-handovers reference this shared context. It is NOT repeated in each sub-handover — agents should read this document first.

### Models to Export (31 models, FK dependency order)

| Group | Models | Notes |
|-------|--------|-------|
| 1. Identity | Organization, User, Settings, SetupState | User credentials stripped |
| 2. Membership | OrgMembership, UserFieldPriority | APIKey EXCLUDED entirely |
| 3. Products | Product, ProjectType | JSONB fields serialize as native dicts |
| 4. Projects | Project, DiscoveryConfig, GitConfig | GitConfig credential fields stripped |
| 5. Vision | VisionDocument, VisionDocumentSummary, ProductTechStack, ProductArchitecture, ProductTestConfig | |
| 6. Memory | ProductMemoryEntry, MCPContextIndex | MCPContextIndex.searchable_vector skipped (TSVECTOR) |
| 7. Tasks | Task, Message | Task: topological sort on import |
| 8. Msg Junction | MessageRecipient, MessageAcknowledgment, MessageCompletion | |
| 9. Agents | AgentTemplate, TemplateArchive, TemplateUsageStats | |
| 10. Jobs | AgentJob, AgentExecution, AgentTodoItem | |
| 11. Config | Configuration, GitCommit, OptimizationRule | |

**Excluded models (security/ephemeral):** APIKey, ApiKeyIpLog, DownloadToken, ApiMetrics, OAuthAuthorizationCode, MCPSession, OptimizationMetric

### Field Stripping Maps

```python
GLOBAL_STRIP = {"tenant_key"}

CREDENTIAL_FIELDS = {
    "User": {"password_hash", "recovery_pin_hash"},
    "GitConfig": {"password_encrypted", "ssh_key_encrypted", "webhook_secret"},
}

SKIP_FIELDS = {
    "MCPContextIndex": {"searchable_vector"},
}

IMPORT_OVERRIDES = {
    "User": {"must_change_password": True, "must_set_pin": True},
    "GitConfig": {"password_encrypted": None, "ssh_key_encrypted": None, "webhook_secret": None},
}
```

### Key Codebase Facts

- **Primary keys:** String(36) UUIDs via `generate_uuid()` (`models/base.py`). UPSERT conflict target is the UUID `id` column directly. No ID remapping needed. Two exceptions: MCPContextIndex (integer PK, has `chunk_id` UUID), ProductMemoryEntry (native PostgreSQL UUID). DownloadToken (integer PK) is excluded.
- **Vision files:** Uploaded as `.md`/`.txt`/`.markdown` only (frontend enforces `accept=".txt,.md,.markdown"`). Saved to `./products/{product_id}/vision/{filename}` AND decoded text stored in `vision_document` TEXT column. Export must include both DB rows and disk files for portability.
- **No database migration needed.** Feature reads/writes existing tables only.

### Manifest Schema (manifest.json)

```json
{
  "export_version": "1.0",
  "alembic_revision": "<current head>",
  "exported_at": "2026-03-29T12:00:00Z",
  "tenant_key": "<provenance only>",
  "giljo_mcp_version": "3.3.0",
  "models": {
    "Organization": {"count": 1, "table": "organizations", "sha256": "<per-file hash>"},
    "User": {"count": 3, "table": "users", "sha256": "<hash>", "sensitive_fields_stripped": ["password_hash", "recovery_pin_hash"]}
  },
  "files": {
    "count": 7,
    "total_bytes": 145200,
    "entries": [
      {"zip_path": "files/products/<id>/vision/readme.md", "sha256": "<hash>", "bytes": 4200}
    ]
  }
}
```

**Integrity:** Per-file SHA-256 for every JSON data file and every vision file. Verified before any DB write on import. Do NOT checksum the ZIP itself.

### API Endpoints (created across 0844a + 0844b)

| Method | Path | Auth | Created In |
|--------|------|------|------------|
| `POST` | `/api/v1/settings/export` | `require_admin` | 0844a |
| `POST` | `/api/v1/settings/import/analyze` | `require_admin` | 0844b |
| `POST` | `/api/v1/settings/import/execute` | `require_admin` | 0844b |

### Deferred to v1.1

| Enhancement | Priority |
|-------------|----------|
| Data-level preview (create/update/skip counts per model) | High |
| Optional AES-256 encryption | Low |
| Structured audit trail (ImportHistory table) | Low |

---

## Rollback Plan

All changes are additive (new files + minor mods to 3 existing files):
- Delete: `tenant_export_service.py`, `tenant_import_service.py`, `tenant_data.py`, `TenantDataManager.vue`, test files
- Revert: router registration in `app.py`, `<TenantDataManager>` in `SystemSettings.vue`, 3 methods in `api.js`
- No database migration to roll back
