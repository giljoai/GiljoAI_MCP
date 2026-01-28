# Handover 0700: Cleanup Index Creation

**Date:** 2026-01-27
**From Agent:** orchestrator-coordinator
**To Agent:** database-expert / tdd-implementor
**Priority:** High
**Estimated Complexity:** 4-6 hours
**Status:** Not Started

---

## Task Summary

Create the foundational infrastructure for systematic codebase cleanup: a PostgreSQL-based index that tracks every source file with its dependencies, risk level, and cleanup status.

**Why it matters:** The codebase has ~560 source files and ~665 test files with 168 skip markers, 45 files with DEPRECATED markers, and 43 with TODO markers. A database-driven approach enables dependency-aware cleanup ordering and progress tracking.

---

## Technical Details

### Database Schema

**Table: cleanup_index**
```sql
CREATE TABLE cleanup_index (
    file_id SERIAL PRIMARY KEY,
    file_path TEXT NOT NULL UNIQUE,
    file_type TEXT,  -- 'python', 'vue', 'js', 'test', 'config', 'markdown'
    layer TEXT,      -- 'model', 'service', 'api', 'frontend', 'test', 'docs', 'config'
    status TEXT DEFAULT 'pending',  -- 'pending', 'in_progress', 'cleaned', 'verified'
    risk_level TEXT,  -- 'low', 'medium', 'high', 'critical'
    dependents_count INT DEFAULT 0,
    dependencies_count INT DEFAULT 0,
    deprecation_markers INT DEFAULT 0,
    todo_markers INT DEFAULT 0,
    line_count INT DEFAULT 0,
    last_cleaned_at TIMESTAMP,
    last_verified_at TIMESTAMP,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_cleanup_layer ON cleanup_index(layer);
CREATE INDEX idx_cleanup_status ON cleanup_index(status);
CREATE INDEX idx_cleanup_risk ON cleanup_index(risk_level);
```

**Table: file_dependencies**
```sql
CREATE TABLE file_dependencies (
    id SERIAL PRIMARY KEY,
    source_file_id INT REFERENCES cleanup_index(file_id) ON DELETE CASCADE,
    depends_on_file_id INT REFERENCES cleanup_index(file_id) ON DELETE CASCADE,
    dependency_type TEXT,  -- 'import', 'api_call', 'db_relation', 'component'
    UNIQUE(source_file_id, depends_on_file_id, dependency_type)
);

CREATE INDEX idx_deps_source ON file_dependencies(source_file_id);
CREATE INDEX idx_deps_target ON file_dependencies(depends_on_file_id);
```

### Files to Create

| File | Purpose |
|------|---------|
| `src/giljo_mcp/cleanup/models.py` | SQLAlchemy models for cleanup tables |
| `src/giljo_mcp/cleanup/scanner.py` | File scanner with AST import extraction |
| `src/giljo_mcp/cleanup/indexer.py` | Populates cleanup_index from scan results |
| `src/giljo_mcp/cleanup/__init__.py` | Module exports |
| `tests/cleanup/test_scanner.py` | Scanner unit tests |
| `tests/cleanup/test_indexer.py` | Indexer unit tests |

### Scanner Implementation

**Python AST Import Extraction:**
```python
import ast
from pathlib import Path

def extract_imports(file_path: Path) -> list[str]:
    """Extract all imports from a Python file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        tree = ast.parse(f.read())

    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)
    return imports
```

**Vue/JS Import Extraction:**
```python
import re

def extract_js_imports(file_path: Path) -> list[str]:
    """Extract imports from Vue/JS files using regex."""
    content = file_path.read_text(encoding='utf-8')
    patterns = [
        r'import\s+.*?\s+from\s+[\'"]([^\'"]+)[\'"]',
        r'require\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)',
    ]
    imports = []
    for pattern in patterns:
        imports.extend(re.findall(pattern, content))
    return imports
```

### Layer Classification Rules

| Pattern | Layer |
|---------|-------|
| `src/giljo_mcp/models/**` | model |
| `src/giljo_mcp/services/**` | service |
| `src/giljo_mcp/tools/**` | tool |
| `api/endpoints/**` | api |
| `frontend/src/**` | frontend |
| `tests/**` | test |
| `*.yaml`, `*.json`, `*.toml` | config |
| `docs/**`, `*.md` | docs |

### Risk Classification Algorithm

```python
def calculate_risk_level(dependents_count: int, layer: str) -> str:
    """Classify file risk based on dependents and layer."""
    # Critical: core infrastructure
    if layer == 'model' and dependents_count >= 20:
        return 'critical'
    if layer in ('service', 'api') and dependents_count >= 50:
        return 'critical'

    # High: heavily imported
    if dependents_count >= 20:
        return 'high'

    # Medium: moderate usage
    if dependents_count >= 5:
        return 'medium'

    return 'low'
```

### Marker Detection

```python
def count_markers(file_path: Path) -> tuple[int, int]:
    """Count DEPRECATED and TODO markers in file."""
    content = file_path.read_text(encoding='utf-8')
    deprecated = len(re.findall(r'DEPRECATED|@deprecated', content, re.IGNORECASE))
    todos = len(re.findall(r'TODO|FIXME|XXX|HACK', content))
    return deprecated, todos
```

---

## Implementation Plan

### Phase 1: Database Schema (30 min)
1. Create `src/giljo_mcp/cleanup/models.py` with SQLAlchemy models
2. Add migration logic in `install.py` (cleanup tables section)
3. Verify tables created with `psql`

### Phase 2: Scanner Implementation (1.5 hrs)
1. Create `scanner.py` with:
   - `scan_directory()` - recursive file discovery
   - `extract_imports()` - Python AST parsing
   - `extract_js_imports()` - Vue/JS regex parsing
   - `count_markers()` - DEPRECATED/TODO counting
   - `classify_layer()` - layer assignment
2. Write unit tests for each function

### Phase 3: Indexer Implementation (1.5 hrs)
1. Create `indexer.py` with:
   - `populate_index()` - scan all files, insert records
   - `build_dependency_graph()` - resolve imports to file_ids
   - `calculate_risk_levels()` - update risk after dependencies known
   - `update_dependent_counts()` - count how many files import each file
2. Write integration tests

### Phase 4: CLI Interface (1 hr)
1. Add `python -m giljo_mcp.cleanup scan` command
2. Add `python -m giljo_mcp.cleanup status` command
3. Add `python -m giljo_mcp.cleanup export` command (JSON/CSV)

### Phase 5: Verification (30 min)
1. Run full scan on codebase
2. Verify ~560 source files indexed
3. Verify dependency edges populated
4. Spot-check risk classifications

---

## Testing Requirements

### Unit Tests
- `test_extract_imports_simple` - basic import statement
- `test_extract_imports_from` - from X import Y
- `test_extract_imports_relative` - relative imports
- `test_extract_js_imports` - ES6 imports
- `test_count_markers` - DEPRECATED/TODO detection
- `test_classify_layer` - layer assignment

### Integration Tests
- `test_populate_index_full_scan` - end-to-end indexing
- `test_dependency_graph_accuracy` - verify edges
- `test_risk_calculation` - verify risk levels

### Verification Queries
```sql
-- Check file counts by layer
SELECT layer, COUNT(*) FROM cleanup_index GROUP BY layer;

-- Check risk distribution
SELECT risk_level, COUNT(*) FROM cleanup_index GROUP BY risk_level;

-- Find files with most dependents (likely critical)
SELECT file_path, dependents_count
FROM cleanup_index
ORDER BY dependents_count DESC
LIMIT 10;

-- Find files with most markers (need attention)
SELECT file_path, deprecation_markers, todo_markers
FROM cleanup_index
WHERE deprecation_markers > 0 OR todo_markers > 0
ORDER BY (deprecation_markers + todo_markers) DESC;
```

---

## Dependencies and Blockers

**Dependencies:**
- PostgreSQL running and accessible
- `psycopg2` and `sqlalchemy` installed
- Read access to entire codebase

**No blockers identified.**

---

## Success Criteria

- [ ] `cleanup_index` table created with all columns
- [ ] `file_dependencies` table created with foreign keys
- [ ] Scanner correctly extracts Python imports via AST
- [ ] Scanner correctly extracts Vue/JS imports via regex
- [ ] ~560 source files indexed (excluding `__pycache__`, `.git`, `node_modules`)
- [ ] Dependency edges populated with correct file_id references
- [ ] Risk levels calculated based on dependent counts
- [ ] DEPRECATED and TODO marker counts populated
- [ ] All unit tests passing
- [ ] CLI commands functional

---

## Rollback Plan

```sql
-- To remove cleanup infrastructure:
DROP TABLE IF EXISTS file_dependencies CASCADE;
DROP TABLE IF EXISTS cleanup_index CASCADE;
```

Delete created files:
- `src/giljo_mcp/cleanup/` directory
- `tests/cleanup/` directory

---

## Output Artifacts

After completion:
1. Database tables populated with ~560+ file records
2. Dependency graph with import relationships
3. Risk classifications (expect: ~10 critical, ~50 high, ~150 medium, ~350 low)
4. Marker counts identifying hotspot files

---

## Next Handover

**0701_cleanup_dependency_visualization.md** - Generate interactive HTML dependency graph from the populated index.
