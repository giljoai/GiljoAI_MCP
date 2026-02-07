# Handover 0701: Cleanup Dependency Visualization

**Date:** 2026-01-27
**From Agent:** orchestrator-coordinator
**To Agent:** frontend-tester / ux-designer
**Priority:** Medium
**Estimated Complexity:** 2-3 hours
**Status:** Not Started
**Depends On:** 0700 (Index Creation)

---

## Task Summary

Generate an interactive HTML dependency graph from the `cleanup_index` and `file_dependencies` tables. This visualization helps identify critical files, circular dependencies, and optimal cleanup ordering.

---

## Technical Details

### Output File
`docs/cleanup/dependency_graph.html` - Standalone HTML with embedded D3.js

### Visualization Requirements

**Node Colors by Layer:**
| Layer | Color | Hex |
|-------|-------|-----|
| model | Blue | #3b82f6 |
| service | Green | #22c55e |
| api | Yellow | #eab308 |
| frontend | Purple | #a855f7 |
| test | Gray | #6b7280 |
| config | Orange | #f97316 |
| docs | Cyan | #06b6d4 |

**Node Size by Dependents:**
- Critical (50+ dependents): 20px radius
- High (20-49): 15px radius
- Medium (5-19): 10px radius
- Low (<5): 6px radius

**Edge Styling:**
- Color: Gray (#94a3b8)
- Opacity: 0.3 (to reduce visual clutter)
- Arrow heads for direction

**Interactions:**
- Hover: Show file path, layer, risk level, dependent count
- Click: Highlight all connections (both incoming and outgoing)
- Search box: Filter/highlight by file name
- Layer filter: Checkboxes to show/hide layers
- Risk filter: Checkboxes to show/hide risk levels

### Data Export Script

Create `src/giljo_mcp/cleanup/visualizer.py`:

```python
import json
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.orm import Session

def export_graph_data(session: Session) -> dict:
    """Export cleanup index as D3-compatible JSON."""
    # Query all files
    files = session.execute(
        select(CleanupIndex)
    ).scalars().all()

    # Query all dependencies
    deps = session.execute(
        select(FileDependency)
    ).scalars().all()

    # Build nodes
    nodes = []
    file_id_map = {}
    for i, f in enumerate(files):
        file_id_map[f.file_id] = i
        nodes.append({
            'id': i,
            'file_id': f.file_id,
            'name': Path(f.file_path).name,
            'path': f.file_path,
            'layer': f.layer,
            'risk': f.risk_level,
            'dependents': f.dependents_count,
            'deprecations': f.deprecation_markers,
            'todos': f.todo_markers,
        })

    # Build edges
    links = []
    for d in deps:
        if d.source_file_id in file_id_map and d.depends_on_file_id in file_id_map:
            links.append({
                'source': file_id_map[d.source_file_id],
                'target': file_id_map[d.depends_on_file_id],
                'type': d.dependency_type,
            })

    return {'nodes': nodes, 'links': links}

def generate_html(data: dict, output_path: Path):
    """Generate standalone HTML with embedded D3.js visualization."""
    # Template with D3.js force-directed graph
    html_template = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GiljoAI MCP - Dependency Graph</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        body { margin: 0; font-family: system-ui, sans-serif; background: #0f172a; color: #e2e8f0; }
        #controls { position: fixed; top: 10px; left: 10px; background: #1e293b; padding: 15px; border-radius: 8px; z-index: 100; }
        #controls h3 { margin: 0 0 10px 0; font-size: 14px; }
        #search { width: 200px; padding: 8px; border: 1px solid #334155; border-radius: 4px; background: #0f172a; color: #e2e8f0; }
        .filter-group { margin: 10px 0; }
        .filter-group label { display: block; margin: 3px 0; font-size: 12px; cursor: pointer; }
        #tooltip { position: absolute; background: #1e293b; padding: 10px; border-radius: 6px; font-size: 12px; pointer-events: none; opacity: 0; border: 1px solid #334155; max-width: 300px; }
        #stats { position: fixed; bottom: 10px; left: 10px; background: #1e293b; padding: 10px; border-radius: 8px; font-size: 12px; }
        svg { display: block; }
        .node { cursor: pointer; }
        .link { stroke: #475569; stroke-opacity: 0.3; }
        .link.highlighted { stroke: #f59e0b; stroke-opacity: 0.8; stroke-width: 2px; }
        .node.highlighted circle { stroke: #f59e0b; stroke-width: 3px; }
        .node.dimmed { opacity: 0.2; }
        .link.dimmed { opacity: 0.05; }
    </style>
</head>
<body>
    <div id="controls">
        <h3>Dependency Graph</h3>
        <input type="text" id="search" placeholder="Search files...">
        <div class="filter-group">
            <strong>Layers:</strong>
            <label><input type="checkbox" class="layer-filter" value="model" checked> Models</label>
            <label><input type="checkbox" class="layer-filter" value="service" checked> Services</label>
            <label><input type="checkbox" class="layer-filter" value="api" checked> API</label>
            <label><input type="checkbox" class="layer-filter" value="frontend" checked> Frontend</label>
            <label><input type="checkbox" class="layer-filter" value="test"> Tests</label>
            <label><input type="checkbox" class="layer-filter" value="config"> Config</label>
        </div>
        <div class="filter-group">
            <strong>Risk:</strong>
            <label><input type="checkbox" class="risk-filter" value="critical" checked> Critical</label>
            <label><input type="checkbox" class="risk-filter" value="high" checked> High</label>
            <label><input type="checkbox" class="risk-filter" value="medium" checked> Medium</label>
            <label><input type="checkbox" class="risk-filter" value="low" checked> Low</label>
        </div>
    </div>
    <div id="tooltip"></div>
    <div id="stats"></div>
    <script>
        const data = GRAPH_DATA_PLACEHOLDER;
        // D3.js force-directed graph implementation
        // (Full implementation in actual file)
    </script>
</body>
</html>'''

    # Inject data
    html = html_template.replace('GRAPH_DATA_PLACEHOLDER', json.dumps(data))
    output_path.write_text(html, encoding='utf-8')
```

---

## Implementation Plan

### Phase 1: Data Export (30 min)
1. Create `visualizer.py` with `export_graph_data()`
2. Add `generate_html()` with D3.js template
3. Test JSON export structure

### Phase 2: D3.js Visualization (1.5 hrs)
1. Implement force-directed layout
2. Add color coding by layer
3. Add size scaling by dependents
4. Add arrow heads for edges
5. Implement hover tooltips
6. Implement click highlighting

### Phase 3: Filtering & Search (45 min)
1. Add search box with highlighting
2. Add layer filter checkboxes
3. Add risk filter checkboxes
4. Add node count stats display

### Phase 4: Polish (30 min)
1. Test with actual data from cleanup_index
2. Optimize layout parameters
3. Add legend
4. Verify responsive behavior

---

## Testing Requirements

### Manual Testing
1. Open `dependency_graph.html` in browser
2. Verify all nodes render with correct colors
3. Verify node sizes reflect dependent counts
4. Test hover shows correct file info
5. Test click highlights connections
6. Test search filters correctly
7. Test layer/risk checkboxes work

### Verification Checklist
- [ ] Graph loads without JavaScript errors
- [ ] All 560+ nodes visible (zoomed out)
- [ ] Colors match layer assignments
- [ ] Critical files (large nodes) identifiable
- [ ] Search finds files by name
- [ ] Filters hide/show appropriate nodes

---

## Success Criteria

- [ ] `docs/cleanup/dependency_graph.html` created
- [ ] Visualization renders all indexed files
- [ ] Node colors indicate layer
- [ ] Node sizes indicate risk/dependents
- [ ] Hover shows file details
- [ ] Click highlights connections
- [ ] Search box functional
- [ ] Layer/risk filters functional
- [ ] Loads in <3 seconds with 560+ nodes

---

## Output Artifacts

1. `docs/cleanup/dependency_graph.html` - Standalone visualization
2. `src/giljo_mcp/cleanup/visualizer.py` - Data export and HTML generation

---

## Next Handover

**0702_cleanup_utils_config.md** - Begin actual cleanup with low-risk utility files.
