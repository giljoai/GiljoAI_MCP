"""Standalone FastAPI backend for the Developer Panel.

This service reads pre-generated inventories (see `devpanel_index.py`) and
exposes them via read-only endpoints. It runs outside of the production
application and should be started manually when needed.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict

from fastapi import Body, Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware


def _default_index_dir() -> Path:
    env_override = os.getenv("DEVPANEL_INDEX_DIR")
    if env_override:
        return Path(env_override).expanduser().resolve()
    return (Path.cwd() / "temp" / "devpanel" / "index").resolve()


INDEX_DIR = _default_index_dir()
DEVPANEL_ROOT = Path(__file__).resolve().parents[1]
FLOWS_DIR = (DEVPANEL_ROOT / "flows").resolve()


def require_local_request(request: Request) -> None:
    client = request.client
    host = client.host if client else None
    if host not in {"127.0.0.1", "::1", "testclient"}:
        raise HTTPException(status_code=403, detail="Developer Panel backend is localhost only")


@lru_cache(maxsize=64)
def _load_json(filename: str, mtime: float) -> Dict[str, Any]:
    path = INDEX_DIR / filename
    try:
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Inventory '{filename}' not found") from exc
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail=f"Inventory '{filename}' is invalid JSON") from exc


def load_inventory(filename: str) -> Dict[str, Any]:
    path = INDEX_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Inventory '{filename}' not generated yet")
    stat = path.stat()
    return _load_json(filename, stat.st_mtime)


def create_app() -> FastAPI:
    app = FastAPI(title="Developer Panel Backend", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],  # Dev panel: wildcard acceptable for local development tooling
        allow_headers=["*"],  # Dev panel: wildcard acceptable for local development tooling
    )

    def require_panel_enabled() -> None:
        if os.getenv("ENABLE_DEVPANEL", "false").lower() != "true":
            raise HTTPException(status_code=404, detail="Developer Panel disabled")

    dependency = [Depends(require_panel_enabled), Depends(require_local_request)]

    def require_flow_edit_enabled() -> None:
        if os.getenv("ALLOW_DEVPANEL_EDIT", "false").lower() != "true":
            raise HTTPException(status_code=403, detail="Flow editing disabled (set ALLOW_DEVPANEL_EDIT=true)")

    def _flow_path(flow_id: str) -> Path:
        safe_id = re.sub(r"[^a-zA-Z0-9_-]+", "_", flow_id).strip("_")
        if not safe_id:
            raise HTTPException(status_code=400, detail="Invalid flow id")
        FLOWS_DIR.mkdir(parents=True, exist_ok=True)
        return FLOWS_DIR / f"{safe_id}.json"

    @app.get("/health", dependencies=dependency)
    async def health() -> Dict[str, Any]:
        inventories = {
            "api_catalog": (INDEX_DIR / "api_catalog.json").exists(),
            "mcp_tool_catalog": (INDEX_DIR / "mcp_tool_catalog.json").exists(),
            "db_schema": (INDEX_DIR / "db_schema.json").exists(),
            "dependency_index": (INDEX_DIR / "dependency_index.json").exists(),
            "flows_index": (INDEX_DIR / "flows_index.json").exists(),
            "search_index_seed": (INDEX_DIR / "search_index_seed.json").exists(),
            "tech_stack": (INDEX_DIR / "tech_stack.json").exists(),
            "agent_template_catalog": (INDEX_DIR / "agent_template_catalog.json").exists(),
        }
        return {"status": "enabled", "index_dir": str(INDEX_DIR), "inventories": inventories}

    @app.get("/api-catalog", dependencies=dependency)
    async def api_catalog() -> Dict[str, Any]:
        return load_inventory("api_catalog.json")

    @app.get("/mcp-tools", dependencies=dependency)
    async def mcp_tools() -> Dict[str, Any]:
        return load_inventory("mcp_tool_catalog.json")

    @app.get("/agents-templates", dependencies=dependency)
    async def agents_templates() -> Dict[str, Any]:
        return load_inventory("agent_template_catalog.json")

    @app.get("/db-schema", dependencies=dependency)
    async def db_schema() -> Dict[str, Any]:
        return load_inventory("db_schema.json")

    @app.get("/dependency-index", dependencies=dependency)
    async def dependency_index() -> Dict[str, Any]:
        return load_inventory("dependency_index.json")

    @app.get("/flows", dependencies=dependency)
    async def flows() -> Dict[str, Any]:
        return load_inventory("flows_index.json")

    @app.get("/search-index", dependencies=dependency)
    async def search_index() -> Dict[str, Any]:
        return load_inventory("search_index_seed.json")

    @app.get("/tech-stack", dependencies=dependency)
    async def tech_stack() -> Dict[str, Any]:
        return load_inventory("tech_stack.json")

    @app.get("/flow-editor/flows", dependencies=dependency)
    async def flow_editor_list() -> Dict[str, Any]:
        FLOWS_DIR.mkdir(parents=True, exist_ok=True)
        flows = []
        for path in sorted(FLOWS_DIR.glob("*.json")):
            try:
                with path.open("r", encoding="utf-8") as fh:
                    data = json.load(fh)
            except json.JSONDecodeError:
                continue
            except FileNotFoundError:
                continue

            updated = data.get("updated_at") or data.get("generated_at")
            if not updated:
                updated = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()
            flows.append(
                {
                    "id": data.get("id") or path.stem,
                    "title": data.get("title") or data.get("id") or path.stem,
                    "filename": path.name,
                    "updated_at": updated,
                }
            )
        return {"flows": flows}

    @app.get("/flow-editor/flows/{flow_id}", dependencies=dependency)
    async def flow_editor_get(flow_id: str) -> Dict[str, Any]:
        path = _flow_path(flow_id)
        if not path.exists():
            raise HTTPException(status_code=404, detail=f"Flow '{flow_id}' not found")
        try:
            with path.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=500, detail=f"Flow '{flow_id}' contains invalid JSON") from exc
        data.setdefault("id", flow_id)
        return data

    @app.post("/flow-editor/flows/{flow_id}", dependencies=dependency)
    async def flow_editor_save(flow_id: str, payload: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
        require_flow_edit_enabled()
        path = _flow_path(flow_id)
        payload = payload or {}
        payload["id"] = flow_id
        payload["updated_at"] = datetime.now(timezone.utc).isoformat()
        with path.open("w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, ensure_ascii=False)
        return {"status": "saved", "flow": payload}

    return app


app = create_app()
