"""
Unit tests for download helpers and the public slash-commands ZIP endpoint.

Scope:
- Pure helper functions in `api/endpoints/downloads.py`
- Public `/api/download/slash-commands.zip` contents (no auth required)
"""

import io
import zipfile
from unittest.mock import MagicMock, patch


class TestZipArchiveCreation:
    """Test ZIP archive creation utility."""

    def test_create_zip_archive_basic(self):
        from api.endpoints.downloads import create_zip_archive

        files = {
            "file1.md": "# Content 1",
            "file2.md": "# Content 2",
            "file3.md": "# Content 3",
        }

        zip_bytes = create_zip_archive(files)

        assert isinstance(zip_bytes, bytes)
        assert len(zip_bytes) > 0

        with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zipf:
            namelist = zipf.namelist()
            assert len(namelist) == 3
            assert set(namelist) == {"file1.md", "file2.md", "file3.md"}
            assert zipf.read("file1.md").decode("utf-8") == "# Content 1"

    def test_create_zip_archive_empty(self):
        from api.endpoints.downloads import create_zip_archive

        zip_bytes = create_zip_archive({})

        assert isinstance(zip_bytes, bytes)
        with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zipf:
            assert zipf.namelist() == []

    def test_create_zip_archive_unicode_content(self):
        from api.endpoints.downloads import create_zip_archive

        zip_bytes = create_zip_archive({"test.md": "# 测试 🚀 Test"})
        with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zipf:
            content = zipf.read("test.md").decode("utf-8")
            assert "测试" in content
            assert "🚀" in content


class TestDownloadSlashCommands:
    """Test `/api/download/slash-commands.zip` endpoint."""

    def test_download_slash_commands_public(self, api_client):
        response = api_client.get("/api/download/slash-commands.zip")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/zip"
        assert "attachment" in response.headers.get("content-disposition", "")

        with zipfile.ZipFile(io.BytesIO(response.content), "r") as zipf:
            namelist = set(zipf.namelist())

        # Current supported command set (Jan 2026+)
        assert {
            "gil_get_claude_agents.md",
            "gil_activate.md",
            "gil_launch.md",
            "gil_handover.md",
        }.issubset(namelist)

    def test_slash_commands_zip_does_not_ship_legacy_commands(self, api_client):
        response = api_client.get("/api/download/slash-commands.zip")
        assert response.status_code == 200

        with zipfile.ZipFile(io.BytesIO(response.content), "r") as zipf:
            namelist = set(zipf.namelist())

        assert "gil_import_productagents.md" not in namelist
        assert "gil_import_personalagents.md" not in namelist
        assert "gil_fetch.md" not in namelist
        assert "gil_update_agents.md" not in namelist

    def test_slash_commands_zip_content_verification(self, api_client):
        response = api_client.get("/api/download/slash-commands.zip")
        assert response.status_code == 200

        with zipfile.ZipFile(io.BytesIO(response.content), "r") as zipf:
            content = zipf.read("gil_get_claude_agents.md").decode("utf-8")
            assert "name: gil_get_claude_agents" in content
            assert "mcp__giljo-mcp__get_agent_download_url" in content


class TestRenderInstallScript:
    """Unit tests for install script rendering helper."""

    def test_render_install_script_substitutes_server_url(self):
        from api.endpoints.downloads import render_install_script

        template = "curl {{SERVER_URL}}/api/download/slash-commands.zip"
        rendered = render_install_script(template, "http://example.com:7272")
        assert rendered == "curl http://example.com:7272/api/download/slash-commands.zip"


class TestServerURLUtility:
    """Unit tests for get_server_url utility."""

    @patch("api.endpoints.downloads.get_config")
    def test_get_server_url_uses_config_yaml_external_host(self, mock_get_config, tmp_path, monkeypatch):
        from api.endpoints.downloads import get_server_url

        (tmp_path / "config.yaml").write_text("services:\n  external_host: example.com\n", encoding="utf-8")
        monkeypatch.chdir(tmp_path)

        mock_config = MagicMock()
        mock_config.server.api_port = 7272
        mock_get_config.return_value = mock_config

        url = get_server_url()
        assert url == "http://example.com:7272"

    @patch("api.endpoints.downloads.get_config")
    def test_get_server_url_uses_https_when_forwarded(self, mock_get_config, tmp_path, monkeypatch):
        from api.endpoints.downloads import get_server_url

        (tmp_path / "config.yaml").write_text("services:\n  external_host: example.com\n", encoding="utf-8")
        monkeypatch.chdir(tmp_path)

        mock_config = MagicMock()
        mock_config.server.api_port = 7272
        mock_get_config.return_value = mock_config

        mock_request = MagicMock()
        mock_request.headers = {"x-forwarded-proto": "https"}

        url = get_server_url(request=mock_request)
        assert url == "https://example.com:7272"

    @patch("api.endpoints.downloads.get_config", side_effect=Exception("boom"))
    def test_get_server_url_falls_back_on_error(self, _mock_get_config):
        from api.endpoints.downloads import get_server_url

        assert get_server_url() == "http://localhost:7272"
