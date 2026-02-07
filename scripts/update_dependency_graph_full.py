#!/usr/bin/env python3
"""
One-click dependency graph updater.
Regenerates complete dependency graph without requiring LLM assistance.

Usage:
    python scripts/update_dependency_graph_full.py

    OR via HTTP endpoint:
    POST /api/admin/update-dependency-graph
"""

import ast
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple


PROJECT_ROOT = Path(__file__).parent.parent
GRAPH_JSON = PROJECT_ROOT / "docs" / "cleanup" / "dependency_graph.json"
GRAPH_HTML = PROJECT_ROOT / "docs" / "cleanup" / "dependency_graph.html"

# Exclusion patterns (archive folders, libraries, etc)
EXCLUDED_PATTERNS = [
    "**/Archive/**",
    "**/archive/**",
    "**/__pycache__/**",
    "**/node_modules/**",
    "**/.git/**",
    "**/venv/**",
    "**/.pytest_cache/**",
    "**/.vscode/**",
    "**/.idea/**",
]

# Excluded file extensions (assets, type definitions)
EXCLUDED_EXTENSIONS = {
    ".d.ts",  # TypeScript definitions
    ".png",  # Images
    ".jpg",  # Images
    ".jpeg",  # Images
    ".svg",  # Images
    ".gif",  # Images
    ".ico",  # Icons
    ".css",  # Stylesheets
    ".scss",  # Stylesheets
    ".sass",  # Stylesheets
    ".less",  # Stylesheets
    ".woff",  # Fonts
    ".woff2",  # Fonts
    ".ttf",  # Fonts
    ".eot",  # Fonts
}


class DependencyGraphBuilder:
    """Build dependency graph from codebase without LLM assistance."""

    def __init__(self, root: Path):
        self.root = root
        self.nodes = []
        self.node_map: Dict[str, int] = {}  # path -> node_id
        self.file_to_layer: Dict[str, str] = {}

    def should_exclude(self, path: Path) -> bool:
        """Check if file should be excluded."""
        # Check file extension
        if path.suffix in EXCLUDED_EXTENSIONS:
            return True

        # Get path string for checking
        path_str = str(path.relative_to(self.root)).replace("\\", "/")

        # Check for common exclusions directly (more reliable than glob)
        exclusion_keywords = [
            "node_modules",
            "Archive",
            "archive",
            "__pycache__",
            ".git",
            "venv",
            ".pytest_cache",
            ".vscode",
            ".idea",
            "htmlcov",  # Coverage HTML reports
            ".coverage",  # Coverage data files
            "dist",  # Build distributions
            "build",  # Build artifacts
            ".eggs",  # Egg build artifacts
            "*.egg-info",  # Package metadata
        ]

        for keyword in exclusion_keywords:
            if keyword in path_str:
                return True

        # Exclude entire folders (dev tools, handovers, docs)
        exclusion_folders = [
            "dev_tools/",
            "handovers/",
            "docs/",  # Documentation only, not runtime code
        ]

        for folder in exclusion_folders:
            if path_str.startswith(folder):
                return True

        # Exclude .md files EXCEPT runtime-loaded data
        if path.suffix == ".md":
            # Keep these .md files (runtime data):
            runtime_md_patterns = [
                "products/",  # Product vision documents
                ".serena/memories/",  # Serena MCP memories
                ".claude/agents/",  # Custom Claude agents
            ]

            # Check if this .md is runtime data
            is_runtime_md = any(pattern in path_str for pattern in runtime_md_patterns)

            if not is_runtime_md:
                return True  # Exclude all other .md files

        # Also check glob patterns as fallback
        for pattern in EXCLUDED_PATTERNS:
            if path.match(pattern):
                return True

        return False

    def classify_layer(self, rel_path: str) -> str:
        """Classify file into layer based on path."""
        parts = rel_path.replace("\\", "/").split("/")

        # Test layer
        if "test" in rel_path.lower() or rel_path.startswith("tests/"):
            return "test"

        # Docs layer
        if parts[0] in ["docs", "handovers"] or rel_path.endswith(".md"):
            return "docs"

        # Frontend layer
        if parts[0] == "frontend":
            return "frontend"

        # Backend layers
        if parts[0] == "api":
            return "api"

        if parts[0] == "src" and len(parts) > 2:
            if "models" in parts:
                return "model"
            if "services" in parts:
                return "service"
            if "config" in parts:
                return "config"

        return "api"  # default

    def parse_python_imports(self, file_path: Path) -> List[str]:
        """Extract imports from Python file using AST."""
        try:
            content = file_path.read_text(encoding="utf-8")
            tree = ast.parse(content)
            imports = []

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)

            return imports
        except:
            return []

    def parse_js_imports(self, file_path: Path) -> List[str]:
        """Extract imports from JS/Vue file using regex."""
        try:
            content = file_path.read_text(encoding="utf-8")
            imports = []

            # Match: import X from 'path'
            imports.extend(re.findall(r"import\s+.*?\s+from\s+['\"]([^'\"]+)['\"]", content))

            # Match: import('path')
            imports.extend(re.findall(r"import\(['\"]([^'\"]+)['\"]\)", content))

            # Match: require('path')
            imports.extend(re.findall(r"require\(['\"]([^'\"]+)['\"]\)", content))

            return imports
        except:
            return []

    def resolve_import_to_file(self, import_path: str, from_file: Path) -> str | None:
        """Resolve import path to actual file path in project."""
        # Handle Vue path alias (@/ -> frontend/src/)
        if import_path.startswith("@/"):
            resolved = import_path.replace("@/", "frontend/src/")
            # Try multiple extensions
            for ext in [".vue", ".js", ".ts", ".tsx", ""]:
                candidate = self.root / f"{resolved}{ext}"
                if candidate.exists() and candidate.is_file():
                    return str(candidate.relative_to(self.root))
            # Try as directory with index
            for index_file in ["index.vue", "index.js", "index.ts"]:
                candidate = self.root / resolved / index_file
                if candidate.exists():
                    return str(candidate.relative_to(self.root))

        # Handle relative imports (./ and ../)
        elif import_path.startswith(("./", "../")):
            from_dir = from_file.parent
            # Resolve relative path
            try:
                resolved = (from_dir / import_path).resolve()
                if resolved.is_relative_to(self.root):
                    # Try multiple extensions
                    for ext in [".vue", ".js", ".ts", ".tsx", ".py", ""]:
                        candidate = resolved.parent / f"{resolved.name}{ext}"
                        if candidate.exists() and candidate.is_file():
                            return str(candidate.relative_to(self.root))
                    # Try as directory with index or __init__
                    for index_file in ["index.vue", "index.js", "index.ts", "__init__.py"]:
                        candidate = resolved / index_file
                        if candidate.exists():
                            return str(candidate.relative_to(self.root))
            except (ValueError, OSError):
                pass

        # Handle Python absolute imports
        elif import_path.startswith(("api.", "src.giljo_mcp.", "giljo_mcp.")):
            module_path = import_path.replace(".", "/")
            # Try direct file
            py_file = self.root / f"{module_path}.py"
            if py_file.exists():
                return str(py_file.relative_to(self.root))
            # Try __init__.py
            init_file = self.root / module_path / "__init__.py"
            if init_file.exists():
                return str(init_file.relative_to(self.root))

        # Handle common Python test patterns (pytest, unittest)
        elif import_path.startswith(("tests.", "test.")):
            module_path = import_path.replace(".", "/")
            # Try direct file
            py_file = self.root / f"{module_path}.py"
            if py_file.exists():
                return str(py_file.relative_to(self.root))
            # Try in tests directory
            py_file = self.root / "tests" / f"{module_path.replace('tests/', '')}.py"
            if py_file.exists():
                return str(py_file.relative_to(self.root))

        return None

    def count_code_markers(self, file_path: Path) -> Tuple[int, int, int]:
        """Count TODOs, deprecations, dead code markers."""
        try:
            content = file_path.read_text(encoding="utf-8").lower()
            todos = content.count("todo") + content.count("fixme")
            deprecations = content.count("deprecated") + content.count("deprecation")
            dead_code = content.count("# unused") + content.count("// unused")
            return todos, deprecations, dead_code
        except:
            return 0, 0, 0

    def calculate_risk(self, dependents_count: int, todos: int, deprecations: int) -> str:
        """Calculate risk level."""
        if dependents_count >= 50 or deprecations >= 10:
            return "critical"
        if dependents_count >= 20 or deprecations >= 5:
            return "high"
        if dependents_count >= 5 or deprecations >= 2 or todos >= 5:
            return "medium"
        return "low"

    def build(self) -> Dict:
        """Build complete dependency graph."""
        print("[*] Scanning codebase...")

        # Phase 1: Find all files and create nodes
        file_extensions = {".py", ".js", ".vue", ".ts", ".tsx", ".md", ".html"}
        all_files = []

        for ext in file_extensions:
            for file_path in self.root.rglob(f"*{ext}"):
                if not self.should_exclude(file_path):
                    all_files.append(file_path)

        print(f"   Found {len(all_files)} files")

        # Phase 2: Create nodes
        print("[+] Creating nodes...")
        for idx, file_path in enumerate(all_files):
            rel_path = str(file_path.relative_to(self.root))
            layer = self.classify_layer(rel_path)
            todos, deprecations, dead_code = self.count_code_markers(file_path)

            node = {
                "id": idx,
                "path": rel_path,
                "name": file_path.name,
                "layer": layer,
                "dependents": [],
                "dependencies": [],
                "todos": todos,
                "deprecations": deprecations,
                "dead_code": dead_code,
                "risk": "low",  # Will calculate later
                "production_dependents": 0,
                "test_dependents": 0,
            }

            self.nodes.append(node)
            self.node_map[rel_path] = idx
            self.file_to_layer[rel_path] = layer

        # Phase 3: Parse imports and build edges
        print("[~] Building dependency edges...")
        links = []

        for node in self.nodes:
            file_path = self.root / node["path"]

            # Parse imports based on file type
            if file_path.suffix == ".py":
                imports = self.parse_python_imports(file_path)
            elif file_path.suffix in {".js", ".vue", ".ts", ".tsx"}:
                imports = self.parse_js_imports(file_path)
            else:
                imports = []

            # Resolve imports to files
            for import_path in imports:
                target_file = self.resolve_import_to_file(import_path, file_path)
                if target_file and target_file in self.node_map:
                    target_id = self.node_map[target_file]
                    source_id = node["id"]

                    # Add dependency
                    if target_id not in node["dependencies"]:
                        node["dependencies"].append(target_id)
                        links.append({"source": source_id, "target": target_id})

                    # Add dependent (reverse)
                    target_node = self.nodes[target_id]
                    if source_id not in target_node["dependents"]:
                        target_node["dependents"].append(source_id)

                        # Classify as production or test
                        if node["layer"] == "test":
                            target_node["test_dependents"] += 1
                        else:
                            target_node["production_dependents"] += 1

        # Phase 4: Calculate risk levels
        print("[!]  Calculating risk levels...")
        for node in self.nodes:
            total_deps = len(node["dependents"])
            node["risk"] = self.calculate_risk(total_deps, node["todos"], node["deprecations"])

        print(f"[OK] Graph complete: {len(self.nodes)} nodes, {len(links)} edges")

        return {
            "nodes": self.nodes,
            "links": links,
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "total_files": len(self.nodes),
                "total_dependencies": len(links),
            },
        }


def update_html_with_data(html_path: Path, graph_data: Dict):
    """Update HTML file with new graph data and timestamp."""
    print("[EDIT] Updating HTML file...")

    html_content = html_path.read_text(encoding="utf-8")

    # Find and replace graphData
    start_marker = "const graphData="
    end_marker = "const lc="

    start_idx = html_content.find(start_marker)
    end_idx = html_content.find(end_marker)

    if start_idx == -1 or end_idx == -1:
        raise ValueError("Could not find graphData section in HTML")

    # Build new data section (minified JSON) - include metadata with timestamp
    graph_json = json.dumps(graph_data, separators=(",", ":"))

    new_section = f"const graphData={graph_json};\n"

    # Replace
    new_html = html_content[:start_idx] + new_section + html_content[end_idx:]

    html_path.write_text(new_html, encoding="utf-8")
    print("[OK] HTML updated with timestamp")


def main():
    """Main entry point for one-click update."""
    print("=" * 60)
    print("Dependency Graph Updater (No LLM Required)")
    print("=" * 60)

    # Build graph
    builder = DependencyGraphBuilder(PROJECT_ROOT)
    graph_data = builder.build()

    # Save JSON
    print(f"[SAVE] Saving to {GRAPH_JSON}...")
    with open(GRAPH_JSON, "w", encoding="utf-8") as f:
        json.dump(graph_data, f, indent=2)

    # Update HTML
    update_html_with_data(GRAPH_HTML, graph_data)

    # Print summary
    print("\n" + "=" * 60)
    print("[STATS] SUMMARY")
    print("=" * 60)

    layers = {}
    risks = {}
    for node in graph_data["nodes"]:
        layers[node["layer"]] = layers.get(node["layer"], 0) + 1
        risks[node["risk"]] = risks.get(node["risk"], 0) + 1

    print(f"Total Files: {len(graph_data['nodes'])}")
    print(f"Total Dependencies: {len(graph_data['links'])}")
    print(f"\nLayers: {dict(sorted(layers.items()))}")
    print(f"Risks: {dict(sorted(risks.items()))}")

    # Hub files
    hub_files = [n for n in graph_data["nodes"] if len(n["dependents"]) >= 50]
    if hub_files:
        print(f"\nHub Files (50+ dependents): {len(hub_files)}")
        for node in sorted(hub_files, key=lambda n: len(n["dependents"]), reverse=True)[:5]:
            print(f"  - {node['path']}: {len(node['dependents'])} deps")

    print("\n[OK] Dependency graph updated successfully!")
    print(f"   View at: file://{GRAPH_HTML.absolute()}")


if __name__ == "__main__":
    main()
