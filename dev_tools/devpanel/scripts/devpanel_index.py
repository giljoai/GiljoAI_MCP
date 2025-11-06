#!/usr/bin/env python3
"""
DevPanel Indexer (Phase 1001)

Generates machine-readable inventories for the Developer Panel without modifying the main app:
- api_catalog.json: FastAPI routes, methods, tags, summaries
- mcp_tool_catalog.json: from api/endpoints/mcp_tools.list_mcp_tools()
- db_schema.json: SQLAlchemy models (tables, columns, FKs, indexes)
- agent_template_catalog.json: Template defaults + metadata
- tech_stack.json: Backend/frontend dependencies + deprecations
- dependency_index.json: Module import graph for api/ and src/
- flows_index.json: Parsed highlights from key docs/handovers
- search_index_seed.json: Aggregated entries for client-side search

Outputs live under temp/devpanel/index/ by default.
"""

from __future__ import annotations

import argparse
import asyncio
import importlib
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set


REPO_ROOT = Path(__file__).resolve().parents[3]
API_DIR = REPO_ROOT / "api"
SRC_DIR = REPO_ROOT / "src"
DOCS_DIR = REPO_ROOT / "docs"
HANDOVERS_DIR = REPO_ROOT / "handovers"
OUT_DIR_DEFAULT = REPO_ROOT / "temp" / "devpanel" / "index"


def ensure_paths(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)


def safe_json_dump(obj: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=2, ensure_ascii=False)


def add_repo_to_syspath() -> None:
    sys.path.insert(0, str(REPO_ROOT / "src"))
    sys.path.insert(0, str(REPO_ROOT))


def build_api_catalog() -> Dict[str, Any]:
    try:
        add_repo_to_syspath()
        app_mod = importlib.import_module("api.app")
        create_app = getattr(app_mod, "create_app", None)
        if not create_app:
            return {"success": False, "error": "create_app not found"}
        app = create_app()
        from fastapi.routing import APIRoute

        routes: List[Dict[str, Any]] = []
        for route in app.routes:
            if not isinstance(route, APIRoute):
                continue
            methods = sorted(m for m in route.methods if m not in {"HEAD", "OPTIONS"})
            summary = route.summary or (route.endpoint.__doc__.strip().splitlines()[0] if route.endpoint.__doc__ else "")
            routes.append(
                {
                    "path": route.path,
                    "name": route.name,
                    "methods": methods,
                    "tags": list(getattr(route, "tags", []) or []),
                    "summary": summary,
                    "endpoint": f"{route.endpoint.__module__}.{route.endpoint.__name__}",
                }
            )

        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for route in routes:
            key = route["tags"][0] if route["tags"] else "untagged"
            grouped.setdefault(key, []).append(route)

        return {"success": True, "total": len(routes), "routes": routes, "grouped": grouped}
    except ModuleNotFoundError as err:
        return {"success": False, "error": f"Missing dependency: {err}"}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


async def _call_mcp_list() -> Dict[str, Any]:
    add_repo_to_syspath()
    mod = importlib.import_module("api.endpoints.mcp_tools")
    func = getattr(mod, "list_mcp_tools")
    return await func()


def build_mcp_tool_catalog() -> Dict[str, Any]:
    try:
        data = asyncio.run(_call_mcp_list())
        return {"success": True, "data": data}
    except ModuleNotFoundError as err:
        return {"success": False, "error": f"Missing dependency: {err}"}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def build_db_schema() -> Dict[str, Any]:
    try:
        add_repo_to_syspath()
        models_mod = importlib.import_module("giljo_mcp.models")
        Base = getattr(models_mod, "Base")
        metadata = Base.metadata

        tables_out: Dict[str, Any] = {}
        for table_name, table in metadata.tables.items():
            cols = []
            for col in table.columns:
                cols.append(
                    {
                        "name": col.name,
                        "type": str(col.type),
                        "nullable": bool(col.nullable),
                        "primary_key": bool(col.primary_key),
                        "default": str(col.default.arg) if col.default is not None else None,
                        "server_default": str(col.server_default.arg.text) if col.server_default is not None else None,
                    }
                )

            fks = []
            for fk in table.foreign_keys:
                fks.append({"column": fk.parent.name, "ref": str(fk.column), "ondelete": fk.ondelete})

            idx = []
            for index in table.indexes:
                idx.append({"name": index.name, "columns": [col.name for col in index.expressions]})

            tables_out[table_name] = {"columns": cols, "foreign_keys": fks, "indexes": idx}

        return {"success": True, "tables": tables_out}
    except ModuleNotFoundError as err:
        return {"success": False, "error": f"Missing dependency: {err}"}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def iter_python_files(root: Path) -> Iterable[Path]:
    for path in root.rglob("*.py"):
        if any(part in {"__pycache__", ".venv", "venv"} for part in path.parts):
            continue
        yield path


def build_import_graph() -> Dict[str, Any]:
    import ast

    graph: Dict[str, Set[str]] = {}
    files = list(iter_python_files(SRC_DIR)) + list(iter_python_files(API_DIR))
    for path in files:
        try:
            source = path.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(source)
        except Exception:
            continue
        module_key = str(path.relative_to(REPO_ROOT)).replace(os.sep, "/")
        graph.setdefault(module_key, set())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    graph[module_key].add(alias.name)
            elif isinstance(node, ast.ImportFrom) and node.module:
                graph[module_key].add(node.module)

    return {"success": True, "modules": {k: sorted(v) for k, v in graph.items()}}


def extract_markdown_outline(md_path: Path) -> Dict[str, Any]:
    if not md_path.exists():
        return {"path": str(md_path), "sections": []}
    sections: List[Dict[str, Any]] = []
    for line in md_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if line.startswith("#"):
            level = len(line) - len(line.lstrip("#"))
            title = line.lstrip("#").strip()
            sections.append({"level": level, "title": title})
    return {"path": str(md_path), "sections": sections}


def build_flows_index() -> Dict[str, Any]:
    flows: Dict[str, Any] = {}
    candidates = [
        HANDOVERS_DIR / "start_to_finish_agent_FLOW.md",
        DOCS_DIR / "INSTALLATION_FLOW_PROCESS.md",
        HANDOVERS_DIR / "0106d_websocket_event_catalog.md",
    ]
    for path in candidates:
        flows[path.name] = extract_markdown_outline(path)
    return {"success": True, "flows": flows}


def build_agent_template_catalog() -> Dict[str, Any]:
    try:
        add_repo_to_syspath()
        seeder = importlib.import_module("giljo_mcp.template_seeder")
        get_defaults = getattr(seeder, "_get_default_templates_v103")
        get_metadata = getattr(seeder, "_get_template_metadata", lambda: {})
        templates = get_defaults()
        metadata = get_metadata()

        entries: List[Dict[str, Any]] = []
        for tpl in templates:
            role_key = (tpl.get("role") or "").lower()
            meta = metadata.get(role_key, {})
            entries.append(
                {
                    "name": tpl.get("name"),
                    "role": tpl.get("role"),
                    "description": tpl.get("description"),
                    "cli_tool": tpl.get("cli_tool"),
                    "model": tpl.get("model"),
                    "version": tpl.get("version"),
                    "is_active": tpl.get("is_active", True),
                    "is_default": tpl.get("is_default", False),
                    "behavioral_rules": meta.get("behavioral_rules", []),
                    "success_criteria": meta.get("success_criteria", []),
                    "variables": meta.get("variables", []),
                }
            )

        return {"success": True, "count": len(entries), "templates": entries}
    except ModuleNotFoundError as err:
        return {"success": False, "error": f"Missing dependency: {err}"}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def build_tech_stack() -> Dict[str, Any]:
    result: Dict[str, Any] = {"success": True}

    try:
        try:
            import tomllib
        except ModuleNotFoundError:  # pragma: no cover
            import tomli as tomllib  # type: ignore

        pyproject_path = REPO_ROOT / "pyproject.toml"
        if pyproject_path.exists():
            with pyproject_path.open("rb") as fh:
                data = tomllib.load(fh)
            project = data.get("project", {})
            result["python"] = {
                "name": project.get("name"),
                "version": project.get("version"),
                "dependencies": project.get("dependencies", []),
                "optional_dependencies": project.get("optional-dependencies", {}),
            }
        else:
            result["python"] = {"error": "pyproject.toml not found"}
    except ModuleNotFoundError as err:
        result["python"] = {"error": f"Missing dependency: {err}"}
    except Exception as exc:
        result["python"] = {"error": str(exc)}

    package_path = REPO_ROOT / "frontend" / "package.json"
    if package_path.exists():
        try:
            with package_path.open("r", encoding="utf-8") as fh:
                pkg = json.load(fh)
            result["frontend"] = {
                "name": pkg.get("name"),
                "version": pkg.get("version"),
                "dependencies": pkg.get("dependencies", {}),
                "devDependencies": pkg.get("devDependencies", {}),
            }
        except Exception as exc:
            result["frontend"] = {"error": str(exc)}
    else:
        result["frontend"] = {"error": "frontend/package.json not found"}

    deprecations: List[Dict[str, Any]] = []
    tech_doc = DOCS_DIR / "SERVER_ARCHITECTURE_TECH_STACK.md"
    if tech_doc.exists():
        for idx, line in enumerate(tech_doc.read_text(encoding="utf-8", errors="ignore").splitlines(), start=1):
            if "deprecat" in line.lower():
                deprecations.append({"line": idx, "text": line.strip(), "source": str(tech_doc.relative_to(REPO_ROOT))})
    debt_doc = HANDOVERS_DIR / "TECHNICAL_DEBT_v2.md"
    if debt_doc.exists():
        for idx, line in enumerate(debt_doc.read_text(encoding="utf-8", errors="ignore").splitlines(), start=1):
            if "deprecated" in line.lower():
                deprecations.append({"line": idx, "text": line.strip(), "source": str(debt_doc.relative_to(REPO_ROOT))})
    if deprecations:
        result["deprecations"] = deprecations

    return result


def build_search_index_seed(
    api_catalog: Dict[str, Any],
    mcp_catalog: Dict[str, Any],
    db_schema: Dict[str, Any],
    agent_templates: Dict[str, Any],
) -> Dict[str, Any]:
    entries: List[Dict[str, Any]] = []

    for route in api_catalog.get("routes", []):
        entries.append(
            {
                "type": "api_route",
                "title": f"{','.join(route.get('methods', []))} {route.get('path')}",
                "tags": route.get("tags", []),
                "desc": route.get("summary") or "",
                "source": route.get("endpoint"),
            }
        )

    data = (mcp_catalog.get("data") or {}).get("tools", {}) if mcp_catalog.get("success") else {}
    for category, tools in data.items():
        for tool in tools:
            entries.append(
                {
                    "type": "mcp_tool",
                    "title": tool.get("name"),
                    "tags": ["mcp", category],
                    "desc": tool.get("description", ""),
                    "source": f"api.endpoints.mcp_tools:{category}:{tool.get('name')}",
                }
            )

    for table_name, table in (db_schema.get("tables") or {}).items():
        entries.append(
            {
                "type": "db_table",
                "title": table_name,
                "tags": ["db"],
                "desc": f"columns: {len(table.get('columns', []))}",
                "source": f"giljo_mcp.models:{table_name}",
            }
        )

    if agent_templates.get("success"):
        for tpl in agent_templates.get("templates", []):
            entries.append(
                {
                    "type": "agent_template",
                    "title": tpl.get("name"),
                    "tags": ["agent", tpl.get("role")],
                    "desc": tpl.get("description", ""),
                    "source": "giljo_mcp.template_seeder",
                }
            )

    return {"success": True, "count": len(entries), "entries": entries}


def run(output_dir: Path) -> int:
    ensure_paths(output_dir)

    api_catalog = build_api_catalog()
    safe_json_dump(api_catalog, output_dir / "api_catalog.json")

    mcp_catalog = build_mcp_tool_catalog()
    safe_json_dump(mcp_catalog, output_dir / "mcp_tool_catalog.json")

    db_schema = build_db_schema()
    safe_json_dump(db_schema, output_dir / "db_schema.json")

    agent_templates = build_agent_template_catalog()
    safe_json_dump(agent_templates, output_dir / "agent_template_catalog.json")

    tech_stack = build_tech_stack()
    safe_json_dump(tech_stack, output_dir / "tech_stack.json")

    dependency_index = build_import_graph()
    safe_json_dump(dependency_index, output_dir / "dependency_index.json")

    flows_index = build_flows_index()
    safe_json_dump(flows_index, output_dir / "flows_index.json")

    search_index = build_search_index_seed(api_catalog, mcp_catalog, db_schema, agent_templates)
    safe_json_dump(search_index, output_dir / "search_index_seed.json")

    print(f"Wrote inventories to {output_dir}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Developer Panel inventories (Phase 1001)")
    parser.add_argument("--out", default=str(OUT_DIR_DEFAULT), help="Output directory for JSON inventories")
    args = parser.parse_args()
    output_dir = Path(args.out).resolve()
    return run(output_dir)


if __name__ == "__main__":
    raise SystemExit(main())

