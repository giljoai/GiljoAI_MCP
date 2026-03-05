# 0765k External Code Quality Audit (Independent Second Auditor)

**Date:** 2026-03-03  
**Branch context:** `0760-perfect-score`  
**Scope:** Verify 0765j remediation claims, detect new regressions, and identify missed issues.

## 1) Fix Verification

**Fix verification: 10/10 confirmed**

Verified directly in source (not from handover claims):

1. ✅ `api/endpoints/context.py:246-248` adds `VisionDocument.tenant_key == tenant_key`
2. ✅ `api/endpoints/mcp_session.py:193-197` adds tenant filter capability in `get_session(...)`
3. ✅ `api/endpoints/vision_documents.py` old debug cross-tenant query/log block is removed
4. ✅ `api/endpoints/downloads.py:315` uses `AgentTemplate.tenant_key.is_(None)`
5. ✅ Dead fixture cleanup landed across 6 conftest files (`tests/*/conftest.py`) in commit `6ce77a92` (~2664 deletions)
6. ✅ `src/giljo_mcp/tools/agent.py` and `src/giljo_mcp/tools/claude_export.py` deleted
7. ✅ `frontend/src/components/projects/AgentJobModal.vue:91,176-179` uses centralized `@/config/agentColors`
8. ✅ `api/endpoints/statistics.py:420` now sets `peak_hour_messages=None` (fabricated value removed)
9. ✅ `frontend/src/stores/messages.js` reduced to active store API (dead exports removed)
10. ✅ `api/endpoints/orchestration.py` deleted; `tests/**/__pycache__` directories currently absent

Missing fixes: **none**

---

## 2) Per-Dimension Rubric Scores (1 point each)

1. **Lint cleanliness: 0.8/1.0**  
Evidence: `python -m ruff check src/ api/` reports 2 regressions:  
- `api/endpoints/statistics.py:1` unused `# ruff: noqa: A005`  
- `src/giljo_mcp/services/orchestration_service.py:650` RUF005

2. **Dead code: 0.7/1.0**  
Evidence (reference scans):
- `src/giljo_mcp/tools/context.py:259` `get_context_history()` has no references
- `src/giljo_mcp/tools/context.py:309` `get_succession_context()` has no references
- `src/giljo_mcp/colored_logger.py:197` `create_filtered_logger()` appears unreferenced

3. **Pattern compliance: 0.9/1.0**  
Evidence:
- No dict-return regressions found in `src/giljo_mcp/services` or `api/endpoints`
- Remaining no-op expression defects:
  - `src/giljo_mcp/services/message_service.py:375` (`messages[0]` bare expression)
  - `src/giljo_mcp/tools/chunking.py:100` (`content[search_start:search_end]` bare expression)

4. **Tenant isolation: 0.9/1.0**  
Evidence:
- Original 3 tenant gaps fixed (`context.py`, `mcp_session.py`, `vision_documents.py`)
- Residual defense-in-depth gap: `api/endpoints/mcp_session.py:213` updates via `get_session(session_id)` without tenant argument in update path

5. **Security posture: 0.8/1.0**  
Evidence:
- CSRF middleware enabled: `api/app.py:391-406`
- CORS restricted: `api/app.py:413-417`
- New security concern: committed API keys in `api_keys.json:4,15`

6. **Test health: 0.9/1.0**  
Evidence:
- `python -m pytest tests/ -q -c pytest_no_coverage.ini` => **1453 passed, 0 skipped, 0 failed**
- No oversized test files >500 lines (excluding fixtures/conftest/helpers)
- Residual dead fixture modules remain (see findings)

7. **Frontend hygiene: 0.6/1.0**  
Evidence:
- Hardcoded hex scan in `.vue` files only found allowed mask/regex/text hits
- `npx eslint src/` => **124 warnings** (many dead vars/unused declarations in production Vue files)

8. **Exception handling: 1.0/1.0**  
Evidence:
- Broad catches in `src/` + `api/` are annotated inline; no unannotated `except Exception` found

9. **Code organization: 0.6/1.0**  
Evidence (AST length scan >250 lines):
- `api/endpoints/mcp_http.py:298` `handle_tools_list` (485 lines)
- `api/app.py:209` `create_app` (441)
- `src/giljo_mcp/services/message_service.py:124` `send_message` (439)
- `src/giljo_mcp/template_manager.py:162` `_load_legacy_templates` (417)
- `src/giljo_mcp/tools/context_tools/get_vision_document.py:232` `get_vision_document` (322)
- `src/giljo_mcp/template_seeder.py:259` `_get_default_templates_v103` (315)
- `src/giljo_mcp/thin_prompt_generator.py:1276` `_build_claude_code_execution_prompt` (272)

10. **Documentation sync: 0.8/1.0**  
Evidence:
- `api/endpoints/ai_tools.py:212-214` explicitly documents placeholder behavior and still ships placeholder API key
- `src/giljo_mcp/tools/__init__.py:28-30` states context tools are implemented via `ContextService`, while active path is via `context_tools.fetch_context`

---

## 3) New Findings (Post-Remediation + Missed by Prior Audit)

| Severity | File:line | Description | Suggested fix |
|---|---|---|---|
| HIGH | `api_keys.json:4` | API key-like credential committed to repo | Remove tracked credentials, rotate keys, move runtime keys to untracked secret storage |
| HIGH | `api_keys.json:15` | Second committed API key-like credential | Same as above; add CI secret scanning gate |
| HIGH | `api/endpoints/ai_tools.py:214` | Endpoint returns generated configs using hardcoded placeholder API key | Generate scoped key/token server-side or remove endpoint until secure flow exists |
| MEDIUM | `api/endpoints/mcp_session.py:213` | `update_session_data()` resolves session without tenant scoping | Thread `tenant_key` into update/delete paths and enforce tenant filter consistently |
| MEDIUM | `src/giljo_mcp/services/message_service.py:375` | Bare expression no-op (`messages[0]`) indicates leftover/debug artifact | Remove or use value explicitly |
| MEDIUM | `src/giljo_mcp/tools/chunking.py:100` | Bare expression no-op (`content[search_start:search_end]`) | Remove dead expression |
| MEDIUM | `src/giljo_mcp/tools/context.py:259` | `get_context_history()` has zero references in codebase | Remove or wire into public flow and add coverage |
| MEDIUM | `src/giljo_mcp/tools/context.py:309` | `get_succession_context()` has zero references in codebase | Remove or wire into public flow and add coverage |
| MEDIUM | `frontend/src/views/ProductsView.vue:327` | Representative of widespread frontend dead-variable drift (`npx eslint src/` => 124 warnings) | Enforce eslint warnings cleanup + pre-merge warning budget |
| LOW | `tests/fixtures/vision_document_fixtures.py:158` | Fixture module appears unregistered/unreferenced (multiple fixtures only defined here) | Register via `conftest.py`/`pytest_plugins` or delete dead fixtures |
| LOW | `tests/helpers/mock_servers.py:186` | `mock_api_server`/`mock_websocket_server` fixtures appear unused | Delete or move to active test plugin path |
| LOW | `api/endpoints/statistics.py:1` | Unused ruff suppression remains | Remove stale `noqa` |

---

## 4) Overall Score

**Overall score: 8.0/10**

## 5) Verdict

**FAIL** (threshold is >= 9.5)

### Prioritized Fix List

1. Remove committed API-key material (`api_keys.json`) and rotate affected credentials.
2. Replace `ai_tools` placeholder key flow with real secure key/token issuance.
3. Close tenant defense-in-depth gap in MCP session update/delete paths.
4. Eliminate no-op bare expressions (`message_service.py:375`, `chunking.py:100`).
5. Clear frontend lint debt (124 warnings), starting with production Vue files.
6. Remove or integrate unreferenced production functions (`tools/context.py`, `colored_logger.py`).
7. Address the two ruff regressions and reduce oversized function hotspots.
