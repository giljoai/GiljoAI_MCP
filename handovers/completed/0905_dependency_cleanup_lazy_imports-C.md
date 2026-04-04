# Handover 0905: Dependency Cleanup & Lazy Import Optimization

**Date:** 2026-04-03
**Priority:** Medium
**Estimated Complexity:** 1 hour
**Status:** Not Started
**Edition Scope:** CE

---

## Task Summary

Remove unused Python dependencies from `requirements.txt` and `pyproject.toml`, clean up redundant explicit entries that are already installed as transitive deps, and make the heavy vision summarization imports lazy to reduce app startup memory footprint.

**Why:** Dependency audit revealed `aiohttp` (+ 7 sub-deps) is completely unused in production code — zero imports in `src/` or `api/`. Additionally, `numpy` (42.7 MB) and `scipy` (114.6 MB) load into memory on every app startup via a top-level import chain, even when vision summarization is never used.

**Expected outcome:** Cleaner dependency manifest, faster fresh installs (no aiohttp compilation), and ~167 MB less memory loaded at startup unless vision summarization is actively used.

---

## Audit Findings

### Package: aiohttp (REMOVE)
- **Status:** Zero imports in `src/` or `api/`
- **Size:** 2.0 MB installed (aiohttp + aiohappyeyeballs, aiosignal, attrs, frozenlist, multidict, propcache, yarl)
- **History:** Listed in requirements.txt with comment "required by websocket_client.py" but no such import exists
- **Action:** Remove from `requirements.txt` and `pyproject.toml`

### Package: websockets (REDUNDANT ENTRY)
- **Status:** Not imported in production code. Transitive dep of `uvicorn[standard]` (>=10.4)
- **Action:** Remove explicit entry from `requirements.txt` and `pyproject.toml`. Still installed via uvicorn.

### Package: numpy, scipy (REDUNDANT ENTRIES)
- **Status:** Not directly imported. Transitive deps of `sumy`
- **Size:** numpy 42.7 MB, scipy 114.6 MB on disk
- **Action:** Remove explicit entries. Pip installs them via sumy anyway. Add comment explaining this.

### Package: pydantic-settings (REDUNDANT IN PYPROJECT)
- **Status:** In `pyproject.toml` but NOT in `requirements.txt`. Transitive dep of `mcp>=1.23.0`
- **Action:** Remove from `pyproject.toml`

### Packages that STAY (no direct import but required)
- **email-validator:** Required at runtime by Pydantic `EmailStr` (used in auth.py, users.py)
- **python-multipart:** Required by FastAPI for form handling; also transitive dep of mcp
- **alembic:** Used by `alembic upgrade head` in migration commands

### Lazy Import: consolidation_service.py (STARTUP OPTIMIZATION)
- **File:** `src/giljo_mcp/services/consolidation_service.py` line 18
- **Current:** Top-level `from src.giljo_mcp.services.vision_summarizer import VisionDocumentSummarizer`
- **Problem:** This triggers loading sumy → numpy (42.7 MB) → scipy (114.6 MB) into memory on every startup
- **Fix:** Move import inside the methods that instantiate `VisionDocumentSummarizer`
- **Impact:** ~1-2 second delay on first vision summarization call per session, instead of every startup

---

## Files to Modify

| File | Change |
|------|--------|
| `requirements.txt` | Remove aiohttp, websockets, numpy, scipy entries. Add comments for transitive deps. |
| `pyproject.toml` | Remove aiohttp, websockets, numpy, scipy, pydantic-settings from dependencies list. |
| `src/giljo_mcp/services/consolidation_service.py` | Move VisionDocumentSummarizer import from top-level to inside methods. |

---

## Implementation Plan

### Phase 1: requirements.txt cleanup
1. Remove `aiohttp>=3.9.0` line and its comment
2. Remove `websockets>=12.0` line — add comment under uvicorn noting it provides websockets
3. Remove `numpy>=1.24.0` and `scipy>=1.10.0` lines — add comment under sumy noting they are transitive deps
4. Remove the "Vision Document Summarization" section header comment since sumy/nltk stay but numpy/scipy entries go

### Phase 2: pyproject.toml cleanup
1. Remove `"aiohttp>=3.9.0"` from dependencies
2. Remove `"websockets>=12.0"` from dependencies
3. Remove `"pydantic-settings>=2.0.0"` from dependencies
4. Remove `"numpy>=1.24.0"` and `"scipy>=1.10.0"` from dependencies

### Phase 3: Lazy import in consolidation_service.py
1. Remove top-level `from src.giljo_mcp.services.vision_summarizer import VisionDocumentSummarizer`
2. Find all methods that use `VisionDocumentSummarizer` and add local import inside each

---

## Testing Requirements

- `ruff check src/ api/` passes clean
- App starts successfully (`python startup.py`)
- Vision summarization still works (create/summarize a vision document)
- `pip install -r requirements.txt` in a fresh venv installs all needed packages (sumy still pulls numpy/scipy)

---

## Success Criteria

- Zero unused packages in requirements.txt
- pyproject.toml dependencies match requirements.txt (no phantom entries)
- App startup no longer loads numpy/scipy into memory
- All existing functionality preserved
