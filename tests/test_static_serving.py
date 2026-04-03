"""Tests for production single-port frontend serving (Handover 0902d).

Validates that:
- GET / serves index.html when frontend/dist/ exists
- API routes take priority over SPA fallback
- Static assets are served without authentication
- Non-API 404s fall through to SPA, API 404s return JSON
"""

import textwrap
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


def _build_dist(tmp_path: Path) -> Path:
    """Create a minimal fake frontend/dist/ directory."""
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text(
        textwrap.dedent("""\
            <!DOCTYPE html>
            <html><head><title>GiljoAI</title></head>
            <body><div id="app"></div></body></html>
        """)
    )
    assets = dist / "assets"
    assets.mkdir()
    (assets / "test.js").write_text("console.log('hello');")
    (assets / "test.css").write_text("body { margin: 0; }")
    return dist


def _make_client(dist_path: Path | None) -> TestClient:
    """Create a TestClient with a fresh app, optionally pointing at *dist_path*.

    We patch ``state.config`` so ``create_app()`` resolves the dist directory
    to our temp path (or a non-existent path when *dist_path* is None).
    """
    mock_config = MagicMock()

    if dist_path is not None:
        mock_config.get_nested.return_value = str(dist_path)
    else:
        mock_config.get_nested.return_value = str(Path("/nonexistent/dist"))

    with patch("api.app.state") as mock_state:
        mock_state.config = mock_config
        mock_state.db_manager = None
        mock_state.auth = None
        mock_state.tenant_manager = None
        mock_state.tool_accessor = None
        mock_state.websocket_manager = MagicMock()
        mock_state.websocket_broker = None
        mock_state.event_bus = None
        mock_state.connections = {}
        mock_state.heartbeat_task = None
        mock_state.cleanup_task = None
        mock_state.metrics_sync_task = None
        mock_state.health_monitor = None
        mock_state.health_monitor_task = None
        mock_state.silence_detector = None
        mock_state.api_call_count = {}
        mock_state.mcp_call_count = {}
        mock_state.system_prompt_service = None
        mock_state.startup_complete = False
        mock_state.degraded_services = []

        from importlib import reload

        import api.app as app_module

        reload(app_module)
        fresh_app = app_module.create_app()

    return TestClient(fresh_app, raise_server_exceptions=False)


@pytest.fixture()
def dist_dir(tmp_path):
    """Provide a populated dist/ directory."""
    return _build_dist(tmp_path)


@pytest.fixture()
def client_with_dist(dist_dir):
    """TestClient whose app has a valid frontend/dist/."""
    return _make_client(dist_dir)


@pytest.fixture()
def client_without_dist():
    """TestClient whose app has NO frontend/dist/."""
    return _make_client(None)


class TestStaticServing:
    """Test static file serving when frontend/dist/ exists."""

    def test_root_serves_index_html_when_dist_exists(self, client_with_dist):
        """GET / returns index.html content, not JSON."""
        response = client_with_dist.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "<div id=\"app\"></div>" in response.text

    def test_api_health_returns_json(self, client_with_dist):
        """GET /health returns JSON, not index.html -- API routes take priority."""
        response = client_with_dist.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["checks"]["api"] == "healthy"

    def test_spa_fallback_for_vue_routes(self, client_with_dist):
        """GET /projects/123 returns index.html (SPA fallback for Vue Router)."""
        response = client_with_dist.get("/projects/123")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "<div id=\"app\"></div>" in response.text

    def test_static_js_asset_served(self, client_with_dist):
        """GET /assets/test.js returns the JS file."""
        response = client_with_dist.get("/assets/test.js")
        assert response.status_code == 200
        assert "console.log" in response.text

    def test_static_css_asset_served_without_auth(self, client_with_dist):
        """Static CSS files served without authentication (no 401)."""
        response = client_with_dist.get("/assets/test.css")
        assert response.status_code == 200
        assert response.status_code != 401

    def test_api_404_returns_json_not_html(self, client_with_dist):
        """GET /api/nonexistent returns JSON 404, not index.html."""
        response = client_with_dist.get("/api/nonexistent")
        assert response.status_code == 404
        assert "application/json" in response.headers["content-type"]


class TestWithoutDist:
    """Test behavior when frontend/dist/ does NOT exist."""

    def test_root_returns_json_without_dist(self, client_without_dist):
        """GET / returns API info JSON when no dist/ directory."""
        response = client_without_dist.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "GiljoAI" in data.get("name", "")
