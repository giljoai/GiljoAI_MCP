# Handover: 0346 - Depth Config Field Standardization

**Date:** 2025-12-13
**Status:** PARTIALLY COMPLETE - NEEDS INVESTIGATION
**Agent:** Claude Opus 4.5 (Claude Code CLI)

---

## Summary

Fixed several bugs related to vision document depth toggle in Settings → Context, but **depth truncation is still not working**.

### What's Fixed ✅
1. **Field name mismatch** - `vision_chunking` → `vision_documents` standardized
2. **MCP tool frozen config** - Now fetches fresh user config
3. **ToolAccessor frozen config** - Same fix applied
4. **Execution mode frozen** - Now reads from Project table
5. **v2.0 nested format** - Extracts priorities from `{"version": "2.0", "priorities": {...}}`

### What's Still Broken ❌
1. **Vision depth setting IGNORED** - Low/Medium/Full all produce ~10K tokens
2. **Agent Templates depth IGNORED** - "Type only" still shows full descriptions

---

## Critical Investigation Needed

### Test Results from User

| Test | Vision Setting | Vision Tokens | Total Tokens |
|------|----------------|---------------|--------------|
| 1 | Unknown (first) | ~21K (full) | 21,150 |
| 2 | After priority fix | 0 (excluded) | 408 |
| 3 | Low (5K) | ~10K | 11,337 |
| 4 | Medium (12.5K) | ~10K | 11,337 |
| 5 | Medium (12.5K) | ~10K | 10,791 |
| 6 | Full | ~10K | 10,791 |

**Conclusion:** Vision depth setting has NO effect - always returns ~10K tokens regardless of Low/Medium/Full setting.

### What IS Working

| Feature | Status | Evidence |
|---------|--------|----------|
| Priority labels | ✅ | Headers show CRITICAL/IMPORTANT/Reference |
| Priority ordering | ✅ | Fields reorder based on priority |
| Priority 3 truncation | ✅ | Architecture shows ... truncation |
| Settings persistence | ✅ | Priority changes reflected |
| Fresh config fetch | ✅ | Not using frozen job_metadata |

### What is NOT Working

| Feature | Status | Issue |
|---------|--------|-------|
| Vision token limits | ❌ | Low/Medium/Full all produce ~10K |
| Agent Templates "type only" | ❌ | Still shows name + role + description |

---

## Root Cause Hypothesis

The context assembly logic in `mission_planner.py` is:
- ✅ Reading priority settings correctly (headers change)
- ❌ NOT reading depth/token-limit settings (depth_config values ignored)

**Likely locations to investigate:**

1. `src/giljo_mcp/mission_planner.py` lines ~1375-1430
   - Where vision depth is read: `vision_depth = depth_config.get("vision_documents", "moderate")`
   - Where Sumy summaries should be selected based on depth

2. Check if Sumy summaries exist in database:
   ```sql
   SELECT id, filename,
          LENGTH(summary_light) as light_len,
          LENGTH(summary_moderate) as mod_len,
          LENGTH(summary_heavy) as heavy_len,
          original_token_count
   FROM vision_documents
   WHERE product_id = 'YOUR_PRODUCT_ID';
   ```

3. The depth selection logic at lines ~1413-1424:
   ```python
   if vision_depth == "light" and vision_doc.summary_light:
       vision_content = vision_doc.summary_light
   elif vision_depth == "moderate" and vision_doc.summary_moderate:
       vision_content = vision_doc.summary_moderate
   elif vision_depth == "heavy" and vision_doc.summary_heavy:
       vision_content = vision_doc.summary_heavy
   ```

**Possible bugs:**
- Sumy summaries not being generated during upload
- Depth value not reaching the selection logic
- Wrong default being used
- Fallback path always being taken

---

## Files Modified (Previous Session)

### Backend (7 files)
| File | Change |
|------|--------|
| `api/endpoints/users.py` | `vision_chunking` → `vision_documents` |
| `src/giljo_mcp/models/auth.py` | Default dict key |
| `src/giljo_mcp/services/user_service.py` | 3 locations |
| `src/giljo_mcp/services/project_service.py` | Default dict key |
| `src/giljo_mcp/thin_prompt_generator.py` | Docstring + default |
| `src/giljo_mcp/tools/orchestration.py` | Fresh config + v2.0 nested format fix |
| `src/giljo_mcp/tools/tool_accessor.py` | Fresh config + execution_mode |

### Frontend (2 files)
| File | Change |
|------|--------|
| `frontend/src/components/settings/ContextPriorityConfig.vue` | Load/save mapping |
| `frontend/src/components/settings/ContextPriorityConfig.vision.spec.js` | Test assertions |

---

## Commits (Previous Session)

| Commit | Description |
|--------|-------------|
| `8a9482af` | test: TDD RED phase |
| `f2680bd8` | feat: Field standardization |
| `d11d8a2a` | fix: Existing test updates |
| `7e23a3fa` | fix: MCP tool fresh config |
| `21897e35` | fix: Both execution modes fresh config |
| `d28fac44` | fix: Extract priorities from v2.0 nested format |

---

## Next Agent Instructions

### Priority 1: Diagnose Vision Depth Issue

1. **Connect to MCP server** and call:
   ```
   get_orchestrator_instructions(orchestrator_id, tenant_key)
   ```

2. **Check database for Sumy summaries:**
   ```bash
   PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp -c \
     "SELECT id, filename, LENGTH(summary_light) as light, LENGTH(summary_moderate) as mod, LENGTH(summary_heavy) as heavy FROM vision_documents LIMIT 5;"
   ```

3. **Add logging to mission_planner.py** around line 1377:
   ```python
   logger.info(f"[VISION_DEPTH] depth_config received: {depth_config}")
   logger.info(f"[VISION_DEPTH] vision_depth value: {vision_depth}")
   ```

4. **Trace the data flow:**
   - `_get_user_config()` returns depth_config
   - `_build_context_with_priorities()` receives it
   - `vision_depth = depth_config.get("vision_documents", "moderate")` reads it
   - Selection logic chooses summary_light/moderate/heavy

### Priority 2: Check Sumy Integration

The Sumy LSA summarization should create:
- `summary_light` (~5K tokens)
- `summary_moderate` (~12.5K tokens)
- `summary_heavy` (~25K tokens)

These are created during vision document upload. If they don't exist, the fallback path returns chunks.

Check: `src/giljo_mcp/context_management/chunker.py` for Sumy integration.

---

## Test Credentials

```
Orchestrator ID: 1aaa0288-1c67-4906-8c01-2c70c4919b8a
Project ID: 2e55e66f-2745-4bac-bdac-a16ed54e51a8
Tenant Key: ***REMOVED***
User ID: b5f92da5-01b1-4322-a716-1b887876f9ab
Username: patrik
```

---

## Architecture Context

### Prompt Assembly Flow

```
get_orchestrator_instructions() MCP tool
       │
       ├── _get_user_config() → {field_priorities, depth_config}
       │   └── Extracts "priorities" from v2.0 nested format ✅
       │
       ├── _build_context_with_priorities()
       │   │
       │   ├── vision_depth = depth_config.get("vision_documents", "moderate")
       │   │   └── Should be "light", "moderate", "heavy", or "full"
       │   │
       │   └── Selection logic:
       │       if vision_depth == "light" → summary_light
       │       elif vision_depth == "moderate" → summary_moderate
       │       elif vision_depth == "heavy" → summary_heavy
       │       elif vision_depth == "full" → all chunks merged
       │       else → fallback (chunks with limit)  ← MIGHT BE HITTING THIS
       │
       └── Returns assembled mission with vision content
```

### Key Question

Is the depth_config value actually reaching the selection logic, or is something in between losing it?

---

## Session Notes

- User tested 6 times with different depth settings
- All tests returned ~10K tokens for vision content
- Priority system works (CRITICAL/IMPORTANT/Reference headers)
- Depth system does NOT work (Low/Medium/Full ignored)
- Backend restarts don't help (settings are persisted correctly)
- The bug is in the content assembly logic, not config storage/retrieval
