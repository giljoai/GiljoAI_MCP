# Handover 0249a: Closeout Endpoint Implementation (Backend/UI Integration)

**Status:** Backend + UI call wired, unit tests passing. One integration test still failing due to test harness tenant mismatch (see Notes).

## What Changed
- Added GET `/api/v1/projects/{project_id}/closeout` endpoint (alias `/api/projects/{project_id}/closeout` for legacy callers).
- New response schema `ProjectCloseoutDataResponse` with checklist, MCP closeout prompt, project metadata, agent counts, failure/git flags.
- `ProjectService.get_closeout_data()` implemented with tenant isolation, job status aggregation, git integration detection, and rich prompt generation. Accepts optional shared session for reuse.
- Frontend `CloseoutModal.vue` now calls the versioned endpoint `/api/v1/projects/{id}/closeout`.
- Integration router registration includes both versioned and legacy prefixes to avoid prod 404s.

## Files Touched
- `api/endpoints/projects/completion.py` – added closeout GET.
- `api/endpoints/projects/__init__.py` – legacy + v1 routers.
- `api/app.py` – include legacy router.
- `api/schemas/prompt.py` – new `ProjectCloseoutDataResponse`.
- `src/giljo_mcp/services/project_service.py` – `get_closeout_data` + helper.
- `frontend/src/components/orchestration/CloseoutModal.vue` – path updated to `/api/v1/projects/.../closeout`.
- Tests: `tests/services/test_project_service_closeout_data.py`, `tests/integration/test_project_closeout_api.py`, `tests/integration/conftest_0073.py`.

## Behavior Notes
- Checklist rules: completed vs warning counts, failed agents flagged, meaningful work, git integration info. Git flag set when product `product_memory.git_integration.enabled` (or `github.enabled`) and repo_name exists.
- Prompt includes MCP command `close_project_and_update_memory(...)` with tenant_key + project_id prefilled and guidance text.
- Tenant isolation enforced in service query; returns 404 if project not found/tenant mismatch.

## Testing
- Unit: `pytest tests/services/test_project_service_closeout_data.py -q` (pass).
- Integration: `pytest tests/integration/test_project_closeout_api.py -k closeout_data` currently has **1 failing test**:
  - `test_get_closeout_data_endpoint_success` → 404 “Project not found or access denied”. Cause: test harness tenant context isn’t applied to the service despite the project using the same tenant key; likely need to set `TenantManager.set_current_tenant(test_user.tenant_key)` in the integration auth override before calling the endpoint, or inject tenant_key header in the request.
- Production path is unaffected; issue is confined to the test override.

## Recommended Next Steps (for 0249b)
1) Fix integration harness: in `tests/integration/conftest_0073.py` override, set `TenantManager.set_current_tenant(user.tenant_key)` or attach `X-Tenant-Key` header in requests so service sees the tenant. That should turn the remaining 404 into 200 in `test_get_closeout_data_endpoint_success`.
2) Proceed with 0249b: wire MCP closeout tool into `ProjectService.complete_project`, append rich entry to `product_memory.sequential_history`, emit WS events, add retry/error handling, and extend integration tests accordingly.

## Deployment / Compatibility
- Versioned endpoint added; legacy alias preserves existing frontend calls but frontend now uses `/api/v1`.
- No DB schema changes in 0249a.
