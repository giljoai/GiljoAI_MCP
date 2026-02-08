#!/usr/bin/env python3
"""
One-click dependency graph updater.
Regenerates complete dependency graph without requiring LLM assistance.

Standalone development tool - isolated from GiljoAI MCP product.

Usage:
    python scripts/update_dependency_graph_full.py
"""

import ast
import json
import re
import yaml
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple


PROJECT_ROOT = Path(__file__).parent.parent
GRAPH_JSON = PROJECT_ROOT / "docs" / "cleanup" / "dependency_graph.json"
GRAPH_HTML = PROJECT_ROOT / "docs" / "cleanup" / "dependency_graph.html"

# Edge types for dependency relationships
EDGE_TYPES = {
    "import": "Python/JS import statement",
    "pre_commit": "Pre-commit hook invocation",
    "ci_cd": "CI/CD workflow reference",
    "doc_ref": "Documentation reference",
    "subprocess": "subprocess.run/Popen call",
    "test_import": "Test file importing script",
}

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
    "**/.serena/**",
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

        # Exclude entire folders (dev tools, handovers, docs, user data)
        exclusion_folders = [
            "dev_tools/",
            "handovers/",
            "docs/",  # Documentation only, not runtime code
            "products/",  # User data folders (vision documents per product)
            "data/",  # Runtime data folder
            "logs/",  # Log files
            "temp/",  # Temporary files
        ]

        for folder in exclusion_folders:
            if path_str.startswith(folder):
                return True

        # Exclude .md files EXCEPT runtime-loaded data
        if path.suffix == ".md":
            # Keep these .md files (runtime data):
            runtime_md_patterns = [
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

        # Config layer for YAML/config files
        if rel_path.endswith((".yaml", ".yml")) or ".pre-commit" in rel_path:
            return "config"

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
        """Count TODOs, deprecations, dead code markers.

        Deprecation detection is strict - only counts:
        - @deprecated decorators
        - warnings.warn with deprecation
        - DeprecationWarning references
        - Actual deprecated class/function definitions (not comments)
        """
        try:
            content = file_path.read_text(encoding="utf-8")
            content_lower = content.lower()

            # Count TODOs/FIXMEs (case-insensitive, simple count)
            todos = content_lower.count("todo") + content_lower.count("fixme")

            # Count REAL deprecations only (not comments or docs)
            deprecations = 0
            for line in content.split('\n'):
                line_stripped = line.strip()
                line_lower = line_stripped.lower()

                # Skip comments and docstrings mentioning deprecation
                if line_stripped.startswith('#') or line_stripped.startswith('//'):
                    continue
                if line_stripped.startswith('"""') or line_stripped.startswith("'''"):
                    continue
                if line_stripped.startswith('*') or line_stripped.startswith('/*'):
                    continue

                # Count actual deprecation patterns
                if any([
                    '@deprecated' in line_lower,  # Python/JS decorators
                    'warnings.warn' in line_lower and 'deprecat' in line_lower,  # Python warnings
                    'deprecationwarning' in line_lower,  # Python warning type
                    'console.warn' in line_lower and 'deprecat' in line_lower,  # JS console warnings
                ]):
                    deprecations += 1

            # Dead code markers
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

    def parse_precommit_invocations(self) -> List[Tuple[str, str]]:
        """Parse .pre-commit-config.yaml for script invocations.

        Returns list of (source_file, target_script) tuples.
        """
        precommit_file = self.root / ".pre-commit-config.yaml"
        if not precommit_file.exists():
            return []

        invocations = []

        try:
            with open(precommit_file, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)

            if not config or "repos" not in config:
                return []

            source_path = str(precommit_file.relative_to(self.root))

            # Scan all hook entries
            for repo in config.get("repos", []):
                for hook in repo.get("hooks", []):
                    entry = hook.get("entry", "")

                    # Match patterns like "python scripts/check_deprecated_models.py"
                    # or direct script paths
                    script_patterns = [
                        r"python\s+(scripts/[\w_/]+\.py)",  # python scripts/foo.py
                        r"^(scripts/[\w_/]+\.py)",  # scripts/foo.py (at start)
                    ]

                    for pattern in script_patterns:
                        matches = re.findall(pattern, entry)
                        for match in matches:
                            # Normalize path separators
                            script_path = match.replace("/", "\\") if "\\" in str(self.root) else match
                            full_path = self.root / script_path
                            if full_path.exists():
                                target_path = str(full_path.relative_to(self.root))
                                invocations.append((source_path, target_path))

        except Exception:
            pass  # Skip on parse errors

        return invocations

    def parse_doc_references(self) -> List[Tuple[str, str]]:
        """Parse markdown files for script references.

        Scans ALL .md files in the codebase (not just nodes, since most .md
        files are excluded from the graph).

        Returns list of (source_file, target_script) tuples.
        """
        invocations = []

        # Directories to exclude from doc scanning
        excluded_dirs = {"node_modules", "venv", ".venv", "__pycache__", ".git"}

        # Find ALL .md files directly (not just nodes)
        for file_path in self.root.rglob("*.md"):
            # Skip excluded directories
            if any(excluded in file_path.parts for excluded in excluded_dirs):
                continue

            try:
                content = file_path.read_text(encoding="utf-8")

                # Match patterns like "python scripts/foo.py" or "`scripts/foo.py`"
                script_patterns = [
                    r"python\s+(scripts/[\w_/]+\.py)",  # python scripts/foo.py
                    r"`(scripts/[\w_/]+\.py)`",  # `scripts/foo.py`
                    r"(?:^|\s)(scripts/[\w_/]+\.py)(?:\s|$|[)\]])",  # scripts/foo.py (standalone)
                ]

                source_rel = str(file_path.relative_to(self.root))

                for pattern in script_patterns:
                    matches = re.findall(pattern, content, re.MULTILINE)
                    for match in matches:
                        # Normalize path separators for Windows
                        script_path = match.replace("/", "\\") if "\\" in str(self.root) else match
                        full_path = self.root / script_path
                        if full_path.exists():
                            target_path = str(full_path.relative_to(self.root))
                            # Only add if target script is in our node map
                            if target_path in self.node_map:
                                invocations.append((source_rel, target_path))

            except Exception:
                pass  # Skip on read errors

        # Deduplicate (same script referenced multiple times in same doc)
        return list(set(invocations))

    def parse_subprocess_calls(self) -> List[Tuple[str, str]]:
        """Parse Python files for subprocess calls invoking scripts.

        Returns list of (source_file, target_script) tuples.
        """
        invocations = []

        for node in self.nodes:
            if not node["path"].endswith(".py"):
                continue

            file_path = self.root / node["path"]

            try:
                content = file_path.read_text(encoding="utf-8")
                tree = ast.parse(content)

                for astnode in ast.walk(tree):
                    # Check for subprocess.run/Popen/call
                    if isinstance(astnode, ast.Call):
                        func_name = None

                        # Get function name
                        if isinstance(astnode.func, ast.Attribute):
                            if isinstance(astnode.func.value, ast.Name):
                                module = astnode.func.value.id
                                func = astnode.func.attr
                                if module == "subprocess" and func in ("run", "Popen", "call"):
                                    func_name = f"{module}.{func}"

                        # Also check os.system
                        if isinstance(astnode.func, ast.Attribute):
                            if isinstance(astnode.func.value, ast.Name):
                                if astnode.func.value.id == "os" and astnode.func.attr == "system":
                                    func_name = "os.system"

                        if func_name:
                            # Extract script paths from arguments
                            for arg in astnode.args:
                                # Handle list arguments (subprocess.run(['python', 'script.py']))
                                if isinstance(arg, ast.List):
                                    script_path = self._extract_script_from_list(arg)
                                    if script_path:
                                        invocations.append((node["path"], script_path))

                                # Handle string arguments (os.system('python script.py'))
                                elif isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                                    script_path = self._extract_script_from_string(arg.value)
                                    if script_path:
                                        invocations.append((node["path"], script_path))

            except Exception:
                pass  # Skip on parse errors

        return invocations

    def _extract_script_from_list(self, list_node: ast.List) -> str | None:
        """Extract script path from subprocess argument list."""
        # Look for patterns like ['python', 'scripts/foo.py'] or ['scripts/foo.py']
        elements = []
        for elt in list_node.elts:
            if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                elements.append(elt.value)

        # Find script paths
        for elem in elements:
            if elem.startswith("scripts/") and elem.endswith(".py"):
                script_path = elem.replace("/", "\\") if "\\" in str(self.root) else elem
                full_path = self.root / script_path
                if full_path.exists():
                    return str(full_path.relative_to(self.root))

        return None

    def _extract_script_from_string(self, cmd: str) -> str | None:
        """Extract script path from os.system command string."""
        # Match patterns like "python scripts/foo.py"
        matches = re.findall(r"scripts/[\w_/]+\.py", cmd)
        for match in matches:
            script_path = match.replace("/", "\\") if "\\" in str(self.root) else match
            full_path = self.root / script_path
            if full_path.exists():
                return str(full_path.relative_to(self.root))

        return None

    def build(self) -> Dict:
        """Build complete dependency graph."""
        print("[*] Scanning codebase...")

        # Phase 1: Find all files and create nodes
        file_extensions = {".py", ".js", ".vue", ".ts", ".tsx", ".md", ".html", ".yaml", ".yml"}
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
                # New invocation statistics
                "import_deps": 0,  # Count of import edges
                "invocation_deps": 0,  # Count of pre_commit + ci_cd + subprocess edges
                "doc_refs": 0,  # Count of doc_ref edges
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

                    # Determine edge type (default: import for Python/JS imports)
                    edge_type = "import"

                    # Add dependency
                    if target_id not in node["dependencies"]:
                        node["dependencies"].append(target_id)
                        links.append({
                            "source": source_id,
                            "target": target_id,
                            "type": edge_type
                        })

                    # Add dependent (reverse)
                    target_node = self.nodes[target_id]
                    if source_id not in target_node["dependents"]:
                        target_node["dependents"].append(source_id)

                        # Classify as production or test
                        if node["layer"] == "test":
                            target_node["test_dependents"] += 1
                        else:
                            target_node["production_dependents"] += 1

                        # Track import edges
                        target_node["import_deps"] += 1

        # Phase 3.5: Detect invocation edges (pre-commit, docs, subprocess)
        print("[~] Detecting invocation edges...")

        # Pre-commit hook invocations
        precommit_invocations = self.parse_precommit_invocations()
        for source_path, target_path in precommit_invocations:
            if source_path in self.node_map and target_path in self.node_map:
                source_id = self.node_map[source_path]
                target_id = self.node_map[target_path]

                # Add edge
                source_node = self.nodes[source_id]
                target_node = self.nodes[target_id]

                if target_id not in source_node["dependencies"]:
                    source_node["dependencies"].append(target_id)
                    links.append({
                        "source": source_id,
                        "target": target_id,
                        "type": "pre_commit"
                    })

                if source_id not in target_node["dependents"]:
                    target_node["dependents"].append(source_id)
                    target_node["invocation_deps"] += 1

        # Documentation references
        # Note: Doc files are NOT nodes (excluded from graph), so we only
        # increment doc_refs on the TARGET script - no edges created since
        # we can't link to non-existent source nodes
        doc_invocations = self.parse_doc_references()
        doc_ref_count = 0
        for source_path, target_path in doc_invocations:
            # Only target needs to be in node_map (source is a doc file, not a node)
            if target_path in self.node_map:
                target_id = self.node_map[target_path]
                target_node = self.nodes[target_id]
                target_node["doc_refs"] += 1
                doc_ref_count += 1

        # Subprocess invocations
        subprocess_invocations = self.parse_subprocess_calls()
        for source_path, target_path in subprocess_invocations:
            if source_path in self.node_map and target_path in self.node_map:
                source_id = self.node_map[source_path]
                target_id = self.node_map[target_path]

                # Add edge
                source_node = self.nodes[source_id]
                target_node = self.nodes[target_id]

                if target_id not in source_node["dependencies"]:
                    source_node["dependencies"].append(target_id)
                    links.append({
                        "source": source_id,
                        "target": target_id,
                        "type": "subprocess"
                    })

                if source_id not in target_node["dependents"]:
                    target_node["dependents"].append(source_id)
                    target_node["invocation_deps"] += 1

        print(f"   Found {len(precommit_invocations)} pre-commit, {doc_ref_count} doc refs, {len(subprocess_invocations)} subprocess calls")

        # Phase 4: Calculate risk levels
        print("[!]  Calculating risk levels...")
        for node in self.nodes:
            total_deps = len(node["dependents"])
            node["risk"] = self.calculate_risk(total_deps, node["todos"], node["deprecations"])

        # Phase 4.5: Classify connectivity status
        print("[~] Classifying node connectivity...")
        status_counts = {"connected": 0, "standalone": 0, "orphan": 0}
        for node in self.nodes:
            has_imports = node["import_deps"] > 0  # Something imports this
            has_invocations = node["invocation_deps"] > 0  # Pre-commit/subprocess calls this
            has_doc_refs = node["doc_refs"] > 0  # Documentation references this
            has_dependents = len(node["dependents"]) > 0  # Anything depends on this

            if has_imports or has_dependents:
                node["status"] = "connected"  # Normal code with import edges
            elif has_invocations or has_doc_refs:
                node["status"] = "standalone"  # Utility: invoked/documented but not imported
            else:
                node["status"] = "orphan"  # True orphan: nothing references this

            status_counts[node["status"]] += 1

        print(f"   Status: {status_counts['connected']} connected, {status_counts['standalone']} standalone, {status_counts['orphan']} orphan")

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
    """Update HTML file with new graph data and timestamp.

    Preserves the existing HTML structure (filters, table, visualization)
    and only updates the embedded graphData JSON.
    """
    print("[EDIT] Updating HTML file...")

    html_content = html_path.read_text(encoding="utf-8")

    # Find and replace graphData
    start_marker = "const graphData="
    end_marker = "const lc="

    start_idx = html_content.find(start_marker)
    end_idx = html_content.find(end_marker)

    if start_idx == -1 or end_idx == -1:
        raise ValueError("Could not find graphData section in HTML")

    # Build new data section (minified JSON)
    graph_json = json.dumps(graph_data, separators=(",", ":"))

    new_section = f"const graphData={graph_json};\n"

    # Replace the graphData section
    new_html = html_content[:start_idx] + new_section + html_content[end_idx:]

    html_path.write_text(new_html, encoding="utf-8")
    print("[OK] HTML updated with new data")


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
