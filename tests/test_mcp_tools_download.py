"""
Unit tests for MCP tool download functionality
Tests for gil_import_productagents and gil_import_personalagents using download approach.

Handover 0094: Token-Efficient MCP Downloads
"""

import io
import zipfile
from unittest.mock import MagicMock, patch

import pytest


class TestDownloadUtilities:
    """Test HTTP download utility functions"""

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient")
    async def test_download_file_success(self, mock_client):
        """Test successful file download via HTTP"""
        from src.giljo_mcp.tools.download_utils import download_file

        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"test content"
        mock_client.return_value.__aenter__.return_value.get.return_value = mock_response

        result = await download_file(url="http://localhost:7272/api/download/test.zip", api_key="test-api-key")

        assert result == b"test content"

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient")
    async def test_download_file_unauthorized(self, mock_client):
        """Test download with invalid API key"""
        from src.giljo_mcp.tools.download_utils import download_file

        # Mock 401 response
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.raise_for_status.side_effect = Exception("Unauthorized")
        mock_client.return_value.__aenter__.return_value.get.return_value = mock_response

        with pytest.raises(Exception, match="Unauthorized"):
            await download_file(url="http://localhost:7272/api/download/test.zip", api_key="invalid-key")

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient")
    async def test_download_file_network_error(self, mock_client):
        """Test download with network error"""
        from src.giljo_mcp.tools.download_utils import download_file

        # Mock network error
        mock_client.return_value.__aenter__.return_value.get.side_effect = Exception("Connection refused")

        with pytest.raises(Exception, match="Connection refused"):
            await download_file(url="http://localhost:7272/api/download/test.zip", api_key="test-key")


class TestZipExtraction:
    """Test ZIP extraction utility"""

    def test_extract_zip_to_directory(self, tmp_path):
        """Test ZIP extraction to target directory"""
        from src.giljo_mcp.tools.download_utils import extract_zip_to_directory

        # Create test ZIP
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
            zipf.writestr("test1.md", "# Test 1")
            zipf.writestr("test2.md", "# Test 2")
        zip_bytes = zip_buffer.getvalue()

        # Extract
        target_dir = tmp_path / "extracted"
        extract_zip_to_directory(zip_bytes, target_dir)

        # Verify
        assert target_dir.exists()
        assert (target_dir / "test1.md").exists()
        assert (target_dir / "test2.md").exists()
        assert (target_dir / "test1.md").read_text() == "# Test 1"

    def test_extract_zip_creates_directory(self, tmp_path):
        """Test ZIP extraction creates target directory if missing"""
        from src.giljo_mcp.tools.download_utils import extract_zip_to_directory

        # Create test ZIP
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zipf:
            zipf.writestr("file.md", "content")
        zip_bytes = zip_buffer.getvalue()

        # Extract to non-existent directory
        target_dir = tmp_path / "new" / "nested" / "directory"
        extract_zip_to_directory(zip_bytes, target_dir)

        assert target_dir.exists()
        assert (target_dir / "file.md").exists()


class TestGilImportProductAgents:
    """Test gil_import_productagents MCP tool with download approach"""

    @pytest.mark.asyncio
    @patch("src.giljo_mcp.tools.tool_accessor.download_file")
    @patch("src.giljo_mcp.tools.tool_accessor.extract_zip_to_directory")
    @patch("os.environ.get")
    async def test_import_product_agents_success(self, mock_env_get, mock_extract, mock_download):
        """Test successful product agent import via download"""
        from src.giljo_mcp.tools.tool_accessor import ToolAccessor

        # Setup mocks
        mock_env_get.return_value = "test-api-key"

        # Mock ZIP content
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zipf:
            zipf.writestr("orchestrator.md", "# Orchestrator")
            zipf.writestr("implementor.md", "# Implementor")
        mock_download.return_value = zip_buffer.getvalue()

        # Create tool accessor
        tool_accessor = ToolAccessor(db_manager=MagicMock(), tenant_manager=MagicMock())

        # Execute
        result = await tool_accessor.gil_import_productagents(project_id="test-project")

        # Verify
        assert result["success"] is True
        assert "Installed" in result["message"]
        assert len(result["files"]) == 2
        mock_download.assert_called_once()
        mock_extract.assert_called_once()

    @pytest.mark.asyncio
    @patch("os.environ.get")
    async def test_import_product_agents_no_api_key(self, mock_env_get):
        """Test product agent import fails without API key"""
        from src.giljo_mcp.tools.tool_accessor import ToolAccessor

        # No API key set
        mock_env_get.return_value = None

        tool_accessor = ToolAccessor(db_manager=MagicMock(), tenant_manager=MagicMock())

        result = await tool_accessor.gil_import_productagents()

        assert result["success"] is False
        assert "GILJO_API_KEY" in result["error"]
        assert "instructions" in result

    @pytest.mark.asyncio
    @patch("src.giljo_mcp.tools.tool_accessor.download_file")
    @patch("os.environ.get")
    async def test_import_product_agents_download_fails(self, mock_env_get, mock_download):
        """Test product agent import with download failure"""
        from src.giljo_mcp.tools.tool_accessor import ToolAccessor

        mock_env_get.return_value = "test-api-key"
        mock_download.side_effect = Exception("Network error")

        tool_accessor = ToolAccessor(db_manager=MagicMock(), tenant_manager=MagicMock())

        result = await tool_accessor.gil_import_productagents()

        assert result["success"] is False
        assert "error" in result
        assert "manual_fallback" in result
        assert "download_url" in result["manual_fallback"]
        assert "instructions" in result["manual_fallback"]


class TestGilImportPersonalAgents:
    """Test gil_import_personalagents MCP tool with download approach"""

    @pytest.mark.asyncio
    @patch("src.giljo_mcp.tools.tool_accessor.download_file")
    @patch("src.giljo_mcp.tools.tool_accessor.extract_zip_to_directory")
    @patch("os.environ.get")
    async def test_import_personal_agents_success(self, mock_env_get, mock_extract, mock_download):
        """Test successful personal agent import via download"""
        from src.giljo_mcp.tools.tool_accessor import ToolAccessor

        # Setup mocks
        mock_env_get.return_value = "test-api-key"

        # Mock ZIP content
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zipf:
            zipf.writestr("orchestrator.md", "# Orchestrator")
        mock_download.return_value = zip_buffer.getvalue()

        tool_accessor = ToolAccessor(db_manager=MagicMock(), tenant_manager=MagicMock())

        result = await tool_accessor.gil_import_personalagents()

        assert result["success"] is True
        assert "~/.claude/agents" in result["location"] or ".claude/agents" in result["location"]
        mock_download.assert_called_once()
        mock_extract.assert_called_once()

    @pytest.mark.asyncio
    @patch("os.environ.get")
    async def test_import_personal_agents_no_api_key(self, mock_env_get):
        """Test personal agent import fails without API key"""
        from src.giljo_mcp.tools.tool_accessor import ToolAccessor

        mock_env_get.return_value = None

        tool_accessor = ToolAccessor(db_manager=MagicMock(), tenant_manager=MagicMock())

        result = await tool_accessor.gil_import_personalagents()

        assert result["success"] is False
        assert "GILJO_API_KEY" in result["error"]

    @pytest.mark.asyncio
    @patch("src.giljo_mcp.tools.tool_accessor.download_file")
    @patch("os.environ.get")
    async def test_import_personal_agents_with_fallback(self, mock_env_get, mock_download):
        """Test personal agent import provides fallback instructions on error"""
        from src.giljo_mcp.tools.tool_accessor import ToolAccessor

        mock_env_get.return_value = "test-api-key"
        mock_download.side_effect = Exception("Download failed")

        tool_accessor = ToolAccessor(db_manager=MagicMock(), tenant_manager=MagicMock())

        result = await tool_accessor.gil_import_personalagents()

        assert result["success"] is False
        assert "manual_fallback" in result
        fallback = result["manual_fallback"]
        assert "download_url" in fallback
        assert "install_script_url" in fallback
        assert "instructions" in fallback
        assert len(fallback["instructions"]) > 0


class TestServerURLExtraction:
    """Test server URL extraction from MCP config"""

    def test_get_server_url_from_env(self):
        """Test server URL extraction from environment variable"""
        from src.giljo_mcp.tools.download_utils import get_server_url_from_config

        with patch.dict("os.environ", {"GILJO_SERVER_URL": "http://10.0.0.5:7272"}):
            url = get_server_url_from_config()
            assert url == "http://10.0.0.5:7272"

    def test_get_server_url_default(self):
        """Test server URL defaults to localhost"""
        from src.giljo_mcp.tools.download_utils import get_server_url_from_config

        with patch.dict("os.environ", {}, clear=True):
            url = get_server_url_from_config()
            assert "localhost" in url or "127.0.0.1" in url


# Integration test placeholder
class TestDownloadWorkflowIntegration:
    """Integration tests for full download workflow"""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_full_agent_download_workflow(self):
        """
        Integration test: Full agent template download workflow
        This test requires:
        - Running GiljoAI MCP server
        - Valid API key in environment
        - Active agent templates in database
        """
        # Mark as integration test - skip in unit test runs
        pytest.skip("Integration test - requires running server")
