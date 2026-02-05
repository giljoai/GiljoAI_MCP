# Kickoff Prompt: Handover 0701 - Dependency Visualization

**Handover ID**: 0701
**Series**: 0700 Code Cleanup Series (3/12 complete after 0700a and 0700)
**Type**: DISCOVERY
**Priority**: Medium
**Estimated Time**: 2-3 hours
**Status**: Ready to Start

---

## Mission Overview

Create a comprehensive dependency visualization infrastructure to map the GiljoAI MCP codebase. This is a **foundational discovery handover** that will inform ALL subsequent cleanup decisions in handovers 0700b-h and 0702-0711.

You are creating the visual blueprint that will guide the safe removal of ~1,000-2,500 lines of deprecated code and legacy infrastructure.

---

## Context: Where You Fit in the Series

### What Came Before

**0700a (Light Mode Removal)**: Completed. Removed 145 lines of light mode code. Established baseline for dead code removal.

**0700 (Index Creation)**: Completed. Created `cleanup_index.json` with 75 cataloged items:
- 46 deprecated markers
- 18 representative skipped tests
- 8 actionable TODOs
- 3 dead code items

**Your Mission**: Create visualization tools to understand **relationships** between these items before removal.

### Why Visualization Matters

The cleanup_index.json tells us WHAT to clean up. You will discover:
- **WHO depends on WHAT** - Which files will break if we delete X?
- **Orphan detection** - Which files are truly unused?
- **High-risk identification** - Which files have 20+ dependents?
- **Circular dependencies** - Import cycles that need untangling
- **Dead code candidates** - Functions with zero callers

**Without this visualization**: We risk cascading breaks, orphaned code, and missed cleanup opportunities.

---

## Required Reads (Phase 1: Context Acquisition)

### Core Documents (MANDATORY)

1. **`handovers/0701_cleanup_dependency_visualization.md`** - Your full specification
2. **`handovers/0700_series/cleanup_index.json`** - 75 items to analyze
3. **`handovers/0700_series/comms_log.json`** - Messages from 0700 and 0700a
4. **`handovers/0700_series/WORKER_PROTOCOL.md`** - Your execution workflow
5. **`handovers/0700_series/dead_code_audit.md`** - Strategic context and scope change

### Key Insights from These Documents

**From cleanup_index.json**:
- 3 CRITICAL production bugs (skip-bug-001, skip-bug-002, skip-bug-003)
- High-risk deprecations: `AgentExecution.messages`, `Product.product_memory.sequential_history`
- Entire succession.py module can be deleted
- 45 items marked for v4.0 removal

**From comms_log.json**:
- Entry 0700-001: Visualization targets component distribution, dependency graphs, urgency heatmaps
- Entry 0700-004: AgentExecution.messages migration must be verified before removal
- Entry 0700-006: ProjectService has UnboundLocalError bug at line 1545

**From dead_code_audit.md**:
- Strategic direction: Purge ALL deprecated code before v1.0 (not just dead code)
- Scope expanded: ~2,000-2,500 lines will be removed (vs original ~300)
- Codebase size: 92,218 total lines
- Vulture found 19 additional dead code candidates at 80%+ confidence

---

## Your Deliverables

### Primary Outputs

1. **Dependency Graph** (`docs/cleanup/dependency_graph.html`)
   - Interactive D3.js force-directed graph
   - Nodes: All Python/Vue files in codebase
   - Edges: Import relationships (who imports whom)
   - Color-coded by layer (model, service, api, frontend, test, config, docs)
   - Size-scaled by dependent count (critical = 50+, high = 20-49, medium = 5-19, low = <5)
   - Hover tooltips with file details
   - Click highlighting for connection exploration

2. **Data Export Script** (`src/giljo_mcp/cleanup/visualizer.py`)
   - `export_graph_data(session)` - Extract nodes and edges from codebase
   - `generate_html(data, output_path)` - Create standalone HTML with embedded D3.js
   - Support for filtering by layer and risk level

3. **Analysis Report** (`handovers/0700_series/dependency_analysis.json`)
   - Orphan modules (files not imported by anything)
   - High-risk files (20+ dependents)
   - Circular dependencies detected
   - Dead code candidates (functions with zero callers)
   - Recommendations for cleanup ordering

### Secondary Outputs

4. **Findings to comms_log.json**
   - Entry for downstream handovers (0700b-h, 0702-0711)
   - Critical high-risk files identified
   - Recommended cleanup order based on dependency tree
   - Any blockers discovered during analysis

---

## Technical Approach

### Phase 2: Scope Investigation

#### Python Import Extraction (AST-Based)
```python
import ast
from pathlib import Path

def extract_python_imports(file_path: Path) -> list[str]:
    """Extract all import statements from Python file using AST."""
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

#### Vue/JS Import Extraction (Regex-Based)
```python
import re

def extract_vue_imports(file_path: Path) -> list[str]:
    """Extract import statements from Vue/JS files using regex."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Match: import X from 'Y' or import { X } from 'Y'
    pattern = r"import\s+(?:(?:\{[^}]+\})|(?:\w+))\s+from\s+['\"]([^'\"]+)['\"]"
    matches = re.findall(pattern, content)
    return matches
```

#### Graph Data Structure
```python
{
    "nodes": [
        {
            "id": 0,
            "file_id": "src/giljo_mcp/models.py",
            "name": "models.py",
            "path": "src/giljo_mcp/models.py",
            "layer": "model",  # model, service, api, frontend, test, config, docs
            "risk": "high",    # critical (50+), high (20-49), medium (5-19), low (<5)
            "dependents": 35,
            "deprecations": 13,  # From cleanup_index.json
            "todos": 2
        }
    ],
    "links": [
        {
            "source": 0,  # Node index
            "target": 5,  # Node index
            "type": "import"  # import, call (future enhancement)
        }
    ]
}
```

### Phase 3: Execution Plan

**Step 1: File Discovery** (10 min)
- Use `mcp__serena__find_file` to locate all `.py`, `.vue`, `.js` files
- Exclude: `venv/`, `node_modules/`, `tests/`, `.pytest_cache/`, `migrations/`
- Store file list with metadata (path, layer, size)

**Step 2: Import Extraction** (20 min)
- For each Python file: Use AST parser
- For each Vue/JS file: Use regex parser
- Build import graph: file → [dependencies]

**Step 3: Dependency Analysis** (15 min)
- Calculate dependents: reverse graph (who depends on me?)
- Classify risk levels: count dependents per file
- Detect orphans: files with zero dependents (excluding entry points)
- Detect circular dependencies: cycle detection algorithm

**Step 4: Data Export** (10 min)
- Convert graph to D3.js-compatible JSON
- Assign colors by layer
- Assign sizes by dependent count
- Include metadata from cleanup_index.json

**Step 5: HTML Generation** (30 min)
- Embed D3.js force-directed layout
- Add interactive features (hover, click, search, filters)
- Add legend and stats panel
- Test with 560+ nodes from cleanup_index baseline

**Step 6: Analysis Report** (20 min)
- Write findings to `dependency_analysis.json`
- Document orphan modules
- Document high-risk files
- Recommend cleanup ordering

---

## Integration with cleanup_index.json

### Enriching Nodes with Cleanup Data

For each file in your dependency graph:
1. Check if it appears in `cleanup_index.json`
2. If yes, add metadata:
   - `deprecations`: Count of deprecated markers in that file
   - `todos`: Count of TODO markers
   - `skipped_tests`: Count of skipped tests
   - `dead_code`: Boolean if dead code detected
3. Use this data to size/color nodes differently

### Example Node Enrichment
```python
def enrich_node_from_index(node, cleanup_index):
    """Add cleanup metadata to graph node."""
    file_path = node['path']

    # Count deprecations in this file
    deprecations = [e for e in cleanup_index['entries']
                    if e['file_path'] == file_path and e['type'] == 'deprecated']
    node['deprecations'] = len(deprecations)

    # Count TODOs
    todos = [e for e in cleanup_index['entries']
             if e['file_path'] == file_path and e['type'] == 'todo']
    node['todos'] = len(todos)

    # Check for dead code
    dead_code = [e for e in cleanup_index['entries']
                 if e['file_path'] == file_path and e['type'] == 'dead_code']
    node['has_dead_code'] = len(dead_code) > 0

    return node
```

---

## Visualization Requirements

### D3.js Force-Directed Graph

**Layout Parameters**:
```javascript
const simulation = d3.forceSimulation(nodes)
    .force("link", d3.forceLink(links).id(d => d.id).distance(100))
    .force("charge", d3.forceManyBody().strength(-300))
    .force("center", d3.forceCenter(width / 2, height / 2))
    .force("collision", d3.forceCollide().radius(15));
```

**Color Scheme** (by layer):
| Layer | Color | Hex |
|-------|-------|-----|
| model | Blue | #3b82f6 |
| service | Green | #22c55e |
| api | Yellow | #eab308 |
| frontend | Purple | #a855f7 |
| test | Gray | #6b7280 |
| config | Orange | #f97316 |
| docs | Cyan | #06b6d4 |

**Node Sizing** (by dependent count):
| Risk Level | Dependents | Radius |
|------------|-----------|--------|
| Critical | 50+ | 20px |
| High | 20-49 | 15px |
| Medium | 5-19 | 10px |
| Low | <5 | 6px |

**Interactive Features**:
1. **Hover**: Show tooltip with file path, layer, risk level, dependent count, deprecations
2. **Click**: Highlight node + all incoming/outgoing connections
3. **Search**: Filter/highlight nodes by filename substring
4. **Layer filters**: Checkboxes to show/hide layers
5. **Risk filters**: Checkboxes to show/hide risk levels

---

## Recommended Subagent

**Primary**: `deep-researcher`
- Best for comprehensive codebase analysis
- Excels at pattern recognition and relationship mapping
- Can handle large-scale import extraction

**Secondary**: `system-architect`
- Graph design and visualization architecture
- D3.js implementation guidance
- Structural analysis of dependency patterns

---

## Communication Requirements

### Write to comms_log.json

**For 0700b-h** (Schema Cleanup):
```json
{
  "from_handover": "0701",
  "to_handovers": ["0700b", "0700c", "0700d", "0700e", "0700f", "0700g", "0700h"],
  "type": "dependency",
  "subject": "High-risk files identified for careful removal",
  "message": "Dependency analysis complete. HIGH-RISK files with 20+ dependents: [list]. Recommend removing in REVERSE order of dependent count (leaf nodes first). See dependency_analysis.json for full ordering.",
  "files_affected": ["docs/cleanup/dependency_graph.html", "handovers/0700_series/dependency_analysis.json"],
  "action_required": true
}
```

**For 0702-0711** (Component Cleanup):
```json
{
  "from_handover": "0701",
  "to_handovers": ["0702", "0703", "0704", "0705", "0706", "0707", "0708", "0711"],
  "type": "info",
  "subject": "Orphan modules and circular dependencies detected",
  "message": "Found X orphan modules (no dependents). Found Y circular dependencies. See dependency_graph.html and dependency_analysis.json for interactive exploration. Orphans are safe to delete first.",
  "files_affected": ["docs/cleanup/dependency_graph.html"],
  "action_required": false
}
```

---

## Verification Checklist

### Phase 4: Documentation

- [ ] `docs/cleanup/dependency_graph.html` created and loads without errors
- [ ] Graph renders all 560+ files (or actual file count)
- [ ] All layers color-coded correctly
- [ ] Node sizes reflect dependent counts
- [ ] Hover tooltips show file details
- [ ] Click highlighting works for connections
- [ ] Search box filters nodes
- [ ] Layer/risk checkboxes show/hide nodes
- [ ] Loads in <3 seconds with full dataset

### Analysis Verification

- [ ] `dependency_analysis.json` created with structured findings
- [ ] Orphan modules listed with file paths
- [ ] High-risk files (20+ dependents) identified
- [ ] Circular dependencies documented
- [ ] Dead code candidates listed (functions with zero callers)
- [ ] Cleanup ordering recommendations provided

### Communication Verification

- [ ] comms_log.json updated with entry for downstream handovers
- [ ] Findings clearly documented for 0700b-h and 0702-0711
- [ ] Action items specified where needed

---

## Output File Locations

```
handovers/0700_series/dependency_analysis.json  ← Analysis findings
docs/cleanup/dependency_graph.html              ← Interactive visualization
src/giljo_mcp/cleanup/visualizer.py             ← Data export script
```

---

## Success Criteria

**Minimum Viable Product**:
- [ ] Dependency graph HTML renders all Python/Vue/JS files
- [ ] Nodes color-coded by layer (7 layers)
- [ ] Nodes sized by dependent count (4 sizes)
- [ ] Basic interactivity (hover, click, search)

**Full Success**:
- [ ] All visualization requirements met (filters, highlighting, stats)
- [ ] Analysis report identifies orphans, high-risk files, circular deps
- [ ] Enriched with cleanup_index.json metadata
- [ ] Clear recommendations for cleanup ordering
- [ ] comms_log updated for downstream handovers

**Stretch Goals** (if time permits):
- [ ] Call graph analysis (which functions call which)
- [ ] Export/import for other visualization tools (Graphviz, Gephi)
- [ ] Automatic detection of "cluster" modules (highly interconnected groups)

---

## Risk Assessment

**LOW RISK**: This is pure discovery - no code changes, no deletions.

**Potential Issues**:
1. **Large graph performance** - 560+ nodes may lag in browser
   - Mitigation: Add pagination or lazy loading
   - Mitigation: Default to hiding test layer (reduces nodes by ~15%)

2. **Import parsing edge cases** - Dynamic imports, relative paths
   - Mitigation: Handle errors gracefully, log skipped files
   - Mitigation: Focus on static imports first

3. **Circular dependency complexity** - Many cycles detected
   - Mitigation: Visualize top 10 most critical cycles only
   - Mitigation: Defer detailed cycle analysis to 0711

---

## Next Handover Dependencies

**0700b (Database Schema Purge)**: Needs your orphan detection and high-risk file list
**0700c (JSONB Field Cleanup)**: Needs your dependency graph to verify safe removal
**0702-0711 (Component Cleanup)**: Needs your analysis to prioritize cleanup order
**0373 (Template Adapter)**: Needs your findings on TemplateManager usage

**Your work unblocks the entire cleanup series.**

---

## Commit Format

```bash
git commit -m "discovery(0701): Create dependency visualization infrastructure

Implemented comprehensive dependency analysis tools:
- Interactive D3.js force-directed graph (docs/cleanup/dependency_graph.html)
- AST-based Python import extraction
- Regex-based Vue/JS import extraction
- Dependency analysis with orphan detection, high-risk files, circular deps

Findings written to dependency_analysis.json.
Enriched graph with cleanup_index.json metadata (deprecations, TODOs).

Changes:
- ADD docs/cleanup/dependency_graph.html (interactive visualization)
- ADD src/giljo_mcp/cleanup/visualizer.py (data export script)
- ADD handovers/0700_series/dependency_analysis.json (findings report)
- UPDATE handovers/0700_series/comms_log.json (downstream notifications)

Docs Updated:
- None (pure discovery handover)

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Final Notes

This is a **DISCOVERY** handover - your job is to understand, not to change. You are building the map that guides the cleanup.

**Be thorough**: The quality of your visualization directly impacts the safety of all subsequent deletions.

**Be visual**: Make the graph beautiful and intuitive - it will be referenced constantly during the cleanup series.

**Be analytical**: Your findings in `dependency_analysis.json` will inform prioritization and ordering decisions.

---

**Ready to begin? Read the required context files above, then proceed with Phase 1: Context Acquisition.**
