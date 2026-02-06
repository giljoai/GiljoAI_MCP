# Dependency Graph Filtering Results

**Date:** 2025-02-06
**Goal:** Focus dependency graph on operational code only

---

## Evolution: From 25K to 1.6K Files

### Phase 1: Initial Scan (Library Pollution)

```
Total Files: 25,019
  - Your code:        ~2,500 files (10%)
  - node_modules:    16,196 files (65%)
  - .d.ts files:      4,344 files (17%)
  - Other libraries:  1,979 files (8%)
```

**Problem:** Graph was 90% library code, making it useless for architecture analysis.

---

### Phase 2: Exclude Libraries

**Excluded:**
- `node_modules/` - All library code (Vuetify, TypeScript libs, etc.)
- `.d.ts` files - TypeScript type definitions
- `.css`, `.scss` - Stylesheets
- Images (`.png`, `.jpg`, `.svg`)
- Fonts (`.woff`, `.woff2`, `.ttf`)

```
Total Files: 2,912 (88% reduction)
  - Backend Python:     526 files
  - Frontend Vue/JS:    179 files
  - Tests:            1,066 files
  - Docs:             1,140 files
```

**Result:** Much cleaner, but still includes all handovers and documentation.

---

### Phase 3: Exclude Dev Tools & Docs (Final)

**Excluded:**
- `dev_tools/` - Development utilities
- `handovers/` - Handover documentation (not operational code)
- `docs/` - General documentation
- All `.md` files EXCEPT runtime data:
  - Product vision documents (`products/*/vision/*.md`)
  - Serena MCP memories (`.serena/memories/*.md`)
  - Claude agent templates (`.claude/agents/*.md`)

```
Total Files: 1,578 (94% reduction from original)
  - Backend Code:       505 files (32%)
    - API endpoints:    470 files
    - Models:            15 files
    - Services:          19 files
    - Config:             1 file
  - Frontend Code:      179 files (11%)
  - Test Code:          852 files (54%)
  - Runtime Data:        42 files (3%)
    - Product visions:   23 files
    - Claude agents:     10 files
    - Serena memories:    8 files
    - Other:              1 file
```

---

## Before vs After Comparison

| Metric | Initial | Final | Change |
|--------|---------|-------|--------|
| **Total Files** | 25,019 | 1,578 | **-94%** |
| **Your Backend** | 526 | 505 | **Clean** |
| **Your Frontend** | 179 | 179 | **Clean** |
| **Library Pollution** | 16,196 | 0 | **Eliminated** |
| **Vuetify .d.ts** | 1,068 | 0 | **Eliminated** |
| **Type Definitions** | 4,344 | 0 | **Eliminated** |
| **Docs/Handovers** | 1,140+ | 42 | **Runtime only** |

---

## Hub Files Analysis (Final)

### Top 8 Hub Files (50+ dependencies)

| # | File | Total | Prod | Test | % Prod |
|---|------|-------|------|------|--------|
| 1 | `models/__init__.py` | 364 | 87 | 277 | 24% |
| 2 | `agent_identity.py` | 171 | 26 | 145 | 15% |
| 3 | `database.py` | 166 | 53 | 113 | 32% |
| 4 | `tenant.py` | 120 | 23 | 97 | 19% |
| 5 | `api/app.py` | 84 | 30 | 54 | 36% |
| 6 | `products.py` | 69 | 10 | 59 | 14% |
| 7 | `auth/dependencies.py` | 62 | 44 | 18 | **71%** |
| 8 | `projects.py` | 55 | 6 | 49 | 11% |

**Key Insight:** `auth/dependencies.py` has highest production coupling (71%) - this is legitimate architectural coupling for authentication middleware.

---

## Architectural Findings

### 1. Frontend-Backend "Galaxies" ✅ GOOD

**Observation:** Dependency graph shows two separate clusters:
- Backend cluster: Python files (api/, src/giljo_mcp/)
- Frontend cluster: Vue/JS files (frontend/src/)

**Cross-layer imports:** 0 (zero!)

**Why this is GOOD:**
- Proper client-server separation
- Frontend and backend communicate via HTTP API (runtime)
- No compile-time coupling
- Can deploy independently
- Can swap frontend (e.g., mobile app) without backend changes

**This is textbook architecture.**

---

### 2. Library Code Was Drowning Real Code

**Before filtering:**
- 88% library code
- Couldn't identify hub files
- Vuetify internals dominated graph
- TypeScript definitions everywhere

**After filtering:**
- 100% your operational code
- Clear architectural patterns
- Meaningful hub file analysis
- Usable visualization

---

### 3. Runtime Data is Small but Important

**42 .md files are runtime-loaded data:**
- Product vision documents: Used by orchestrators
- Serena memories: Loaded by Serena MCP for context
- Claude agents: Custom agent definitions for Claude Code

**These are NOT documentation - they're data files.**

---

## Exclusion Rules Applied

### Complete Exclusion List

```python
# Folders excluded entirely
EXCLUDED_FOLDERS = [
    'node_modules/',      # All library code
    'dev_tools/',         # Development utilities
    'handovers/',         # Handover documentation
    'docs/',              # General documentation
    'Archive/',           # Archived code
    '__pycache__/',       # Python cache
    '.git/',              # Git metadata
    'venv/',              # Virtual environment
    '.pytest_cache/',     # Test cache
    '.vscode/',           # IDE config
    '.idea/',             # IDE config
]

# File extensions excluded
EXCLUDED_EXTENSIONS = {
    '.d.ts',      # TypeScript definitions
    '.png',       # Images
    '.jpg',       # Images
    '.jpeg',      # Images
    '.svg',       # Images
    '.gif',       # Images
    '.ico',       # Icons
    '.css',       # Stylesheets
    '.scss',      # Stylesheets
    '.sass',      # Stylesheets
    '.less',      # Stylesheets
    '.woff',      # Fonts
    '.woff2',     # Fonts
    '.ttf',       # Fonts
    '.eot',       # Fonts
}

# .md files excluded EXCEPT runtime data
RUNTIME_MD_PATTERNS = [
    'products/',          # Product vision documents
    '.serena/memories/',  # Serena MCP memories
    '.claude/agents/',    # Custom Claude agents
]
```

---

## Recommendations

### 1. Keep This Filtering ✅

**The current filtering is optimal for architecture analysis:**
- Shows only operational code
- Excludes library noise
- Includes runtime data
- Separates frontend/backend clusters clearly

### 2. Monitor Hub Files

**Watch for production dependency growth:**
- `models/__init__.py`: Currently 87 prod deps (acceptable)
- `database.py`: Currently 53 prod deps (infrastructure - expected)
- `auth/dependencies.py`: Currently 44 prod deps (security layer - expected)

**Alert if production deps exceed:**
- Barrel files (like `__init__.py`): 150+ prod deps
- Domain models: 50+ prod deps
- Infrastructure: 100+ prod deps

### 3. Investigate Low Production Usage

**These files have <15% production usage:**
- `products.py`: 10 prod / 59 test (14%)
- `projects.py`: 6 prod / 49 test (11%)

**Questions:**
- Are these models under-utilized in production code?
- Are tests importing directly instead of through services?
- Should service layer be importing these more?

---

## Update Process

### Manual Update (CLI)

```bash
python scripts/update_dependency_graph_full.py
```

**Output:**
```
[*] Scanning codebase...
   Found 1578 files
[+] Creating nodes...
[~] Building dependency edges...
[OK] Graph complete: 1578 nodes, 2075 edges
[OK] Dependency graph updated successfully!
```

**Time:** ~10 seconds

### Web Button (Coming Soon)

**Once API endpoint is registered:**
1. Open dependency graph HTML
2. Click "Update Graph" button
3. Wait ~10 seconds
4. Page reloads with fresh data

**No LLM required - pure static analysis.**

---

## Conclusion

**From 25,019 files → 1,578 files (94% reduction)**

The dependency graph now shows:
- ✅ Your operational code only
- ✅ Clear frontend-backend separation
- ✅ Meaningful hub file analysis
- ✅ Runtime data included
- ✅ Library noise eliminated

**The "galaxies" you saw weren't a problem - they were 88% library code pollution.**

Now you can actually see your architecture.
