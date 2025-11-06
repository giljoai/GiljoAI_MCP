import importlib
import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient


def _prepare_index_dir(index_dir: Path) -> None:
    index_dir.mkdir(parents=True, exist_ok=True)
    default_payload = {"success": True}
    filenames = [
        "api_catalog.json",
        "mcp_tool_catalog.json",
        "db_schema.json",
        "dependency_index.json",
        "flows_index.json",
        "search_index_seed.json",
        "tech_stack.json",
        "agent_template_catalog.json",
    ]
    for name in filenames:
        (index_dir / name).write_text(json.dumps(default_payload), encoding="utf-8")


def test_devpanel_routes_disabled_by_default(monkeypatch):
    monkeypatch.delenv("ENABLE_DEVPANEL", raising=False)
    from api.endpoints import developer_panel as dp

    app = FastAPI()
    app.include_router(dp.router)
    client = TestClient(app)

    response = client.get("/api/v1/developer/health")
    assert response.status_code == 404


def test_devpanel_routes_enabled_with_flag(monkeypatch, tmp_path):
    monkeypatch.setenv("ENABLE_DEVPANEL", "true")
    monkeypatch.setenv("DEVPANEL_INDEX_DIR", str(tmp_path))

    # Reload after env changes so INDEX_DIR picks up the tmp path
    from api.endpoints import developer_panel as dp

    importlib.reload(dp)

    _prepare_index_dir(tmp_path)

    app = FastAPI()
    app.include_router(dp.router)
    client = TestClient(app)

    response = client.get("/api/v1/developer/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "enabled"

    response = client.get("/api/v1/developer/api-catalog")
    assert response.status_code == 200
    assert response.json()["success"] is True
