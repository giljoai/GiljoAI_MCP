"""Dependency visualization tool for codebase cleanup analysis.

Scans Python and Vue/JS files to build dependency graphs, analyze risk,
and generate interactive D3.js visualizations.
"""

import ast
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set


def extract_python_imports(file_path: Path) -> list[str]:
    """Extract imported modules from Python file using AST parsing."""
    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()
        tree = ast.parse(content, filename=str(file_path))
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)
        return imports
    except (OSError, SyntaxError, UnicodeDecodeError) as e:
        print(f"Warning: Failed to parse {file_path}: {e}")
        return []


def extract_vue_imports(file_path: Path) -> list[str]:
    """Extract imported modules from Vue/JS file using regex."""
    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()
        pattern = r"import\s+(?:(?:\{[^}]+\})|(?:\w+))\s+from\s+['\"]([^'\"]+)['\"]"
        matches = re.findall(pattern, content)
        return matches
    except (OSError, SyntaxError, UnicodeDecodeError) as e:
        print(f"Warning: Failed to parse {file_path}: {e}")
        return []


def classify_layer(file_path: Path, root_path: Path) -> str:
    """Classify file into architectural layer based on path."""
    # Normalize to forward slashes for consistent matching across platforms
    rel_path = str(file_path.relative_to(root_path)).lower().replace("\\", "/")
    if (
        "/models/" in rel_path
        or rel_path.startswith("models/")
        or rel_path.endswith("/models.py")
        or rel_path == "models.py"
    ):
        return "model"
    if "/services/" in rel_path or rel_path.startswith("services/"):
        return "service"
    if "/api/" in rel_path or rel_path.startswith("api/") or "/endpoints/" in rel_path:
        return "api"
    if "/frontend/" in rel_path or rel_path.startswith("frontend/"):
        return "frontend"
    if "/tests/" in rel_path or rel_path.startswith("tests/"):
        return "test"
    if "/config" in rel_path or rel_path.startswith("config"):
        return "config"
    if (
        "/tools/" in rel_path
        or rel_path.startswith("tools/")
        or "/src/giljo_mcp/" in rel_path
        or rel_path.startswith("src/giljo_mcp/")
    ):
        return "service"
    return "docs"


def resolve_import_to_file(import_name: str, source_file: Path, root_path: Path, all_files: set[Path]):
    """Attempt to resolve an import statement to an actual file path."""
    # Handle relative imports
    if import_name.startswith("."):
        source_dir = source_file.parent
        dots = len(import_name) - len(import_name.lstrip("."))
        target_dir = source_dir
        for _ in range(dots - 1):
            target_dir = target_dir.parent
        remainder = import_name.lstrip(".").lstrip("/")
        target = target_dir / remainder
        for ext in [".py", ".vue", ".js", ".ts", ""]:
            candidate = target.with_suffix(ext) if ext else target
            if candidate in all_files:
                return candidate
            init_candidate = candidate / "__init__.py"
            if init_candidate in all_files:
                return init_candidate
        return None

    # Handle absolute imports
    path_parts = import_name.split(".")
    for start_dir in [root_path / "src", root_path / "api", root_path / "frontend" / "src", root_path]:
        candidate_base = start_dir / Path(*path_parts)
        for ext in [".py", ".vue", ".js", ".ts", ""]:
            candidate = candidate_base.with_suffix(ext) if ext else candidate_base
            if candidate in all_files:
                return candidate
            init_candidate = candidate / "__init__.py"
            if init_candidate in all_files:
                return init_candidate
    return None


def build_dependency_graph(root_path: Path) -> dict:
    print(f"Scanning codebase from: {root_path}")
    include_dirs = ["src", "api", "frontend/src"]
    extensions = {".py", ".vue", ".js", ".ts"}
    exclude_dirs = {
        "venv",
        "node_modules",
        "tests",
        ".pytest_cache",
        "__pycache__",
        "migrations",
        "backups",
        "handovers",
        "dist",
        "build",
        ".git",
    }
    all_files = set()
    for include_dir in include_dirs:
        search_path = root_path / include_dir
        if not search_path.exists():
            continue
        for file_path in search_path.rglob("*"):
            if file_path.is_file() and file_path.suffix in extensions:
                if any(excl in file_path.parts for excl in exclude_dirs):
                    continue
                all_files.add(file_path)
    print(f"Found {len(all_files)} files")
    nodes, edges, file_map = [], [], {}
    for idx, file_path in enumerate(sorted(all_files)):
        rel_path = str(file_path.relative_to(root_path))
        layer = classify_layer(file_path, root_path)
        node = {
            "id": idx,
            "path": rel_path,
            "name": file_path.name,
            "layer": layer,
            "dependents": [],
            "dependencies": [],
        }
        nodes.append(node)
        file_map[file_path] = idx
    for file_path in all_files:
        source_idx = file_map[file_path]
        if file_path.suffix == ".py":
            imports = extract_python_imports(file_path)
        elif file_path.suffix in {".vue", ".js", ".ts"}:
            imports = extract_vue_imports(file_path)
        else:
            continue
        for import_name in imports:
            target_file = resolve_import_to_file(import_name, file_path, root_path, all_files)
            if target_file and target_file in file_map:
                target_idx = file_map[target_file]
                if source_idx != target_idx:
                    edges.append({"source": source_idx, "target": target_idx})
                    nodes[source_idx]["dependencies"].append(target_idx)
                    nodes[target_idx]["dependents"].append(source_idx)
    print(f"Built graph: {len(nodes)} nodes, {len(edges)} edges")
    return {"nodes": nodes, "edges": edges, "file_map": file_map}


def detect_circular_dependencies(graph: dict) -> list[list[int]]:
    nodes = graph["nodes"]
    cycles, visited, rec_stack, path = [], set(), set(), []

    def dfs(node_idx: int) -> bool:
        visited.add(node_idx)
        rec_stack.add(node_idx)
        path.append(node_idx)
        for dep_idx in nodes[node_idx]["dependencies"]:
            if dep_idx not in visited:
                if dfs(dep_idx):
                    return True
            elif dep_idx in rec_stack:
                cycle_start = path.index(dep_idx)
                cycles.append(path[cycle_start:] + [dep_idx])
                return True
        path.pop()
        rec_stack.remove(node_idx)
        return False

    for idx in range(len(nodes)):
        if idx not in visited:
            dfs(idx)
    return cycles


def analyze_dependencies(graph: dict) -> dict:
    print("Analyzing dependencies...")
    nodes = graph["nodes"]
    entry_points = {"main.py", "app.py", "run_api.py", "startup.py", "install.py", "__init__.py"}
    orphans = [node["path"] for node in nodes if len(node["dependents"]) == 0 and node["name"] not in entry_points]
    high_risk = [
        {"path": node["path"], "dependents": len(node["dependents"])} for node in nodes if len(node["dependents"]) >= 20
    ]
    cycles = detect_circular_dependencies(graph)
    circular_deps = [[nodes[idx]["path"] for idx in cycle] for cycle in cycles]
    ordering = []
    in_degree = {idx: len(node["dependents"]) for idx, node in enumerate(nodes)}
    queue = [idx for idx, degree in in_degree.items() if degree == 0]
    while queue:
        node_idx = queue.pop(0)
        ordering.append(nodes[node_idx]["path"])
        for dep_idx in nodes[node_idx]["dependencies"]:
            in_degree[dep_idx] -= 1
            if in_degree[dep_idx] == 0:
                queue.append(dep_idx)
    layer_stats = defaultdict(int)
    for node in nodes:
        layer_stats[node["layer"]] += 1
    stats = {
        "total_files": len(nodes),
        "total_edges": len(graph["edges"]),
        "by_layer": dict(layer_stats),
        "orphans": len(orphans),
        "high_risk": len(high_risk),
        "circular_deps": len(circular_deps),
    }
    print(f"Found: {len(orphans)} orphans, {len(high_risk)} high-risk, {len(circular_deps)} circular deps")
    return {
        "orphan_modules": orphans,
        "high_risk_files": high_risk,
        "circular_dependencies": circular_deps,
        "cleanup_ordering": ordering,
        "stats": stats,
    }


def enrich_with_cleanup_index(graph: dict, cleanup_index_path: Path) -> dict:
    if not cleanup_index_path.exists():
        return graph
    print("Enriching with cleanup_index.json...")
    with open(cleanup_index_path, encoding="utf-8") as f:
        cleanup_data = json.load(f)
    file_metadata = defaultdict(lambda: {"deprecations": 0, "todos": 0, "dead_code": 0})
    for entry in cleanup_data.get("entries", []):
        fp, et = entry.get("file_path", ""), entry.get("type", "")
        if et == "deprecated":
            file_metadata[fp]["deprecations"] += 1
        elif et == "todo":
            file_metadata[fp]["todos"] += 1
        elif et == "dead_code":
            file_metadata[fp]["dead_code"] += 1
    for node in graph["nodes"]:
        m = file_metadata[node["path"]]
        node["deprecations"], node["todos"], node["dead_code"] = m["deprecations"], m["todos"], m["dead_code"]
        dc = len(node["dependents"])
        node["risk"] = "critical" if dc >= 50 else "high" if dc >= 20 else "medium" if dc >= 5 else "low"
    print(f"Enriched {len(graph['nodes'])} nodes")
    return graph


def export_graph_data(graph: dict, cleanup_index_path: Path, output_path: Path):
    enriched = enrich_with_cleanup_index(graph, cleanup_index_path)
    d3_data = {"nodes": enriched["nodes"], "links": enriched["edges"]}
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(d3_data, f, indent=2)
    print(f"Exported: {output_path}")


def generate_html(data_path: Path, output_path: Path):
    print("Generating HTML...")
    with open(data_path, encoding="utf-8") as f:
        gd = f.read()

    # CSS styles including autocomplete and filter enhancements
    css = """*{margin:0;padding:0}body{background:#0f172a;color:#e2e8f0}
#controls{position:absolute;top:20px;left:20px;background:#1e293b;padding:20px;border-radius:8px;max-width:300px;z-index:1000}
#controls h2{color:#60a5fa}
#search-container{position:relative}
#search{width:100%;padding:8px;background:#0f172a;border:1px solid #334155;color:#e2e8f0;box-sizing:border-box}
#autocomplete{position:absolute;top:100%;left:0;right:0;background:#1e293b;border:1px solid #334155;border-top:none;max-height:200px;overflow-y:auto;display:none;z-index:1001}
#autocomplete div{padding:8px;cursor:pointer;color:#e2e8f0;border-bottom:1px solid #334155}
#autocomplete div:hover{background:#334155;color:#60a5fa}
#reset-view{width:100%;padding:8px;margin:10px 0;background:#0f172a;border:1px solid #334155;color:#e2e8f0;cursor:pointer;transition:all 0.2s}
#reset-view:hover{background:#334155;border-color:#60a5fa;color:#60a5fa}
.filter-group{margin-bottom:10px}
.filter-group label{display:flex;padding:4px 0;cursor:pointer}
.filter-group label:hover{color:#60a5fa}
.layer-indicator{width:12px;height:12px;margin-right:6px;display:inline-block}
#stats{font-size:12px;color:#94a3b8;margin-top:10px}
#graph{width:100vw;height:100vh}
.node{stroke:#1e293b;stroke-width:2px;cursor:pointer}
.node:hover{stroke:#f59e0b;stroke-width:3px}
.node.highlighted{stroke:#f59e0b;stroke-width:3px}
.node.dimmed{opacity:0.2}
.link{stroke:#475569;stroke-opacity:0.3}
.link.highlighted{stroke:#f59e0b;stroke-opacity:0.8;stroke-width:2px}
.link.dimmed{opacity:0.1}
.tooltip{position:absolute;background:#1e293b;padding:12px;border:1px solid #334155;pointer-events:none;z-index:2000;max-width:300px}
.tooltip-title{font-weight:600;color:#60a5fa}"""

    # HTML structure with search container, autocomplete, and reset button
    html_body = """<div id="controls">
<h2>Dependency Graph</h2>
<div id="search-container"><input type="text" id="search" placeholder="Search..."><div id="autocomplete"></div></div>
<button id="reset-view">Reset View</button>
<h3>Layers</h3><div class="filter-group" id="layer-filters"></div>
<h3>Risk</h3><div class="filter-group" id="risk-filters"></div>
<div id="stats"><div id="stats-content"></div></div>
</div>
<svg id="graph"></svg>
<div class="tooltip" id="tooltip" style="display:none"></div>"""

    # JavaScript with all enhancements
    js = (
        """const graphData="""
        + gd
        + """;
const lc={model:"#3b82f6",service:"#22c55e",api:"#eab308",frontend:"#a855f7",test:"#6b7280",config:"#f97316",docs:"#06b6d4"};
const rs={critical:20,high:15,medium:10,low:6};
const svg=d3.select("#graph"),w=window.innerWidth,h=window.innerHeight;
svg.attr("width",w).attr("height",h);
const g=svg.append("g");
svg.call(d3.zoom().scaleExtent([0.1,10]).on("zoom",e=>{g.attr("transform",e.transform);}));
const sim=d3.forceSimulation(graphData.nodes).force("link",d3.forceLink(graphData.links).id(d=>d.id).distance(100)).force("charge",d3.forceManyBody().strength(-300)).force("center",d3.forceCenter(w/2,h/2));
const link=g.append("g").selectAll("line").data(graphData.links).join("line").attr("class","link");
let selectedNode=null;
const node=g.append("g").selectAll("circle").data(graphData.nodes).join("circle").attr("class","node").attr("r",d=>rs[d.risk]||8).attr("fill",d=>lc[d.layer]||"#64748b")
.call(d3.drag().on("start",(e,d)=>{if(!e.active)sim.alphaTarget(0.3).restart();d.fx=d.x;d.fy=d.y;}).on("drag",(e,d)=>{d.fx=e.x;d.fy=e.y;}).on("end",(e,d)=>{if(!e.active)sim.alphaTarget(0);d.fx=null;d.fy=null;}))
.on("click",(e,d)=>{e.stopPropagation();if(selectedNode===d){resetView();}else{selectedNode=d;node.classed("highlighted",n=>n===d).classed("dimmed",n=>n!==d);link.classed("highlighted",l=>l.source===d||l.target===d).classed("dimmed",l=>l.source!==d&&l.target!==d);}})
.on("mouseover",(e,d)=>{const tt=d3.select("#tooltip");tt.html("<div class=tooltip-title>"+d.name+"</div><div>Path: "+d.path+"</div><div>Layer: "+d.layer+"</div><div>Risk: "+d.risk+"</div><div>Dependents: "+d.dependents.length+"</div><div>Dependencies: "+d.dependencies.length+"</div>").style("display","block").style("left",(e.pageX+15)+"px").style("top",(e.pageY+15)+"px");})
.on("mouseout",()=>{d3.select("#tooltip").style("display","none");});
sim.on("tick",()=>{link.attr("x1",d=>d.source.x).attr("y1",d=>d.source.y).attr("x2",d=>d.target.x).attr("y2",d=>d.target.y);node.attr("cx",d=>d.x).attr("cy",d=>d.y);});

const layers=Object.keys(lc),lf=d3.select("#layer-filters");
layers.forEach(l=>{const lab=lf.append("label");lab.append("input").attr("type","checkbox").attr("checked",true).attr("data-layer",l).on("change",applyFilters);lab.append("span").attr("class","layer-indicator").style("background",lc[l]);lab.append("span").text(l);});
const risks=["low","medium","high","critical"],rf=d3.select("#risk-filters");
risks.forEach(r=>{const lab=rf.append("label");lab.append("input").attr("type","checkbox").attr("checked",true).attr("data-risk",r).on("change",applyFilters);lab.append("span").text(r);});

function applyFilters(){
const selectedLayers=[];lf.selectAll("input").each(function(){if(this.checked)selectedLayers.push(this.getAttribute("data-layer"));});
const selectedRisks=[];rf.selectAll("input").each(function(){if(this.checked)selectedRisks.push(this.getAttribute("data-risk"));});
node.classed("dimmed",d=>!selectedLayers.includes(d.layer)||!selectedRisks.includes(d.risk));
link.classed("dimmed",l=>{const srcVisible=selectedLayers.includes(l.source.layer)&&selectedRisks.includes(l.source.risk);const tgtVisible=selectedLayers.includes(l.target.layer)&&selectedRisks.includes(l.target.risk);return!srcVisible||!tgtVisible;});
}

function resetView(){selectedNode=null;node.classed("highlighted",false).classed("dimmed",false);link.classed("highlighted",false).classed("dimmed",false);d3.select("#search").property("value","");d3.select("#autocomplete").style("display","none");applyFilters();}
d3.select("#reset-view").on("click",resetView);

const searchInput=d3.select("#search"),autocomplete=d3.select("#autocomplete");
searchInput.on("input",function(){const q=this.value.toLowerCase();autocomplete.html("");if(q.length>0){const matches=graphData.nodes.filter(d=>d.path.toLowerCase().includes(q)||d.name.toLowerCase().includes(q)).slice(0,10);if(matches.length>0){matches.forEach(d=>{autocomplete.append("div").text(d.path).on("click",()=>{selectedNode=d;node.classed("highlighted",n=>n===d).classed("dimmed",n=>n!==d);link.classed("highlighted",l=>l.source===d||l.target===d).classed("dimmed",l=>l.source!==d&&l.target!==d);searchInput.property("value",d.path);autocomplete.style("display","none");});});autocomplete.style("display","block");}else{autocomplete.style("display","none");}}else{autocomplete.style("display","none");applyFilters();}});
document.addEventListener("click",e=>{if(!document.getElementById("search-container").contains(e.target)){autocomplete.style("display","none");}});

function updateStats(){const s={total:graphData.nodes.length,edges:graphData.links.length,layers:{},risks:{}};graphData.nodes.forEach(n=>{s.layers[n.layer]=(s.layers[n.layer]||0)+1;s.risks[n.risk]=(s.risks[n.risk]||0)+1;});let ht="<div>Files: "+s.total+"</div><div>Connections: "+s.edges+"</div><div>Layers:</div>";Object.entries(s.layers).forEach(([l,c])=>{ht+="<div>  "+l+": "+c+"</div>";});ht+="<div>Risk:</div>";Object.entries(s.risks).forEach(([r,c])=>{ht+="<div>  "+r+": "+c+"</div>";});d3.select("#stats-content").html(ht);}
updateStats();"""
    )

    h = '<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Dependency Graph</title>'
    h += '<script src="https://d3js.org/d3.v7.min.js"></script>'
    h += "<style>" + css.replace("\n", "") + "</style></head><body>"
    h += html_body
    h += "<script>" + js + "</script></body></html>"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(h)
    print(f"Generated: {output_path}")


def main():
    root_path = Path(__file__).parent.parent.parent.parent
    print("GiljoAI MCP Dependency Visualizer")
    print(f"Root: {root_path}")
    graph = build_dependency_graph(root_path)
    analysis = analyze_dependencies(graph)
    cleanup_index_path = root_path / "handovers" / "0700_series" / "cleanup_index.json"
    graph_data_path = root_path / "handovers" / "0700_series" / "dependency_graph_data.json"
    export_graph_data(graph, cleanup_index_path, graph_data_path)
    html_output_path = root_path / "docs" / "cleanup" / "dependency_graph.html"
    generate_html(graph_data_path, html_output_path)
    analysis_output_path = root_path / "handovers" / "0700_series" / "dependency_analysis.json"
    with open(analysis_output_path, "w", encoding="utf-8") as f:
        json.dump(analysis, f, indent=2)
    print(f"Analysis: {analysis_output_path}")
    print("\nSUCCESS: Visualization complete!")
    print(f"Open: {html_output_path}")


if __name__ == "__main__":
    main()
