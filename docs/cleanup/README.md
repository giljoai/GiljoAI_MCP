# Dependency Visualization

## Quick Start

Open `dependency_graph.html` in your web browser to explore the interactive dependency graph.

## What You're Seeing

### Node Colors (Layer)
- **Blue** (#3b82f6) - Model layer (database models)
- **Green** (#22c55e) - Service layer (business logic)
- **Yellow** (#eab308) - API layer (endpoints)
- **Purple** (#a855f7) - Frontend layer (Vue components)
- **Gray** (#6b7280) - Test layer (test files)
- **Orange** (#f97316) - Config layer (configuration)
- **Cyan** (#06b6d4) - Docs layer (documentation)

### Node Sizes (Risk Level)
- **20px** - Critical (50+ dependents) - Extremely high impact
- **15px** - High (20-49 dependents) - Major refactor risk
- **10px** - Medium (5-19 dependents) - Moderate coupling
- **6px** - Low (<5 dependents) - Minimal impact

### Interactions

**Click a node** - Highlight all incoming and outgoing connections  
**Hover a node** - View tooltip with:
- File path
- Layer classification
- Risk level
- Number of dependents (files that import this)
- Number of dependencies (files this imports)
- Deprecations, TODOs, dead code counts

**Search box** - Type filename to filter and highlight matches

**Layer filter** - Toggle visibility of specific layers

**Risk filter** - Toggle visibility by risk level

**Zoom & Pan** - Mouse wheel to zoom, drag background to pan

**Drag nodes** - Click and drag to rearrange the graph

## Key Metrics

- **458 files** analyzed
- **763 connections** mapped
- **271 orphan modules** (no dependents) - safe removal candidates
- **8 high-risk files** (20+ dependents) - change with extreme caution
- **49 circular dependencies** - tight coupling issues

## Using This for Cleanup

### Phase 1: Remove Orphans (Handovers 0702-0705)
1. Filter by Risk: Low only
2. Search for files from orphan list
3. Verify they have zero dependents
4. Remove safely

### Phase 2: Break Circular Dependencies (Handovers 0706-0708)
1. Identify cycles in analysis JSON
2. Use visualization to understand coupling
3. Refactor to break cycles

### Phase 3: Purge Dead Code (Handovers 0709-0711)
1. Identify low-dependent files with dead code markers
2. Verify they're not critical (check node size)
3. Remove dead code sections

## Files

- `dependency_graph.html` - Interactive visualization (202KB)
- `../handovers/0700_series/dependency_graph_data.json` - Raw graph data (197KB)
- `../handovers/0700_series/dependency_analysis.json` - Analysis report (95KB)

## Regenerating

If the codebase changes, regenerate the visualization:

```bash
cd F:\GiljoAI_MCP
python -m src.giljo_mcp.cleanup.visualizer
```

This will update all three files based on the current codebase state.

## Technical Details

**Visualization**: D3.js v7.0 force-directed graph  
**Analysis**: Python AST parser for imports + regex for Vue/JS  
**Layout Algorithm**: Force simulation with charge, link, center, and collision forces  
**Data Format**: Nodes (id, path, name, layer, risk, dependents[], dependencies[]) + Links (source, target)

## Support

For questions or issues with the visualization, see:
- `../../handovers/0700_series/0701_execution_summary.md` - Full execution details
- `../../src/giljo_mcp/cleanup/visualizer.py` - Source code with documentation
