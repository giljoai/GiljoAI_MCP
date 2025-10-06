"""
Integration tests for database setup detection feature.

Tests the /api/setup/status endpoint and SetupModeMiddleware behavior.
"""

import pytest
import tempfile
import yaml
from pathlib import Path
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


@pytest.fixture
def test_config_file():
    """Create a temporary config file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        config_data = {
            'installation': {
                'mode': 'localhost'
            },
            'database': {
                'type': 'postgresql',
                'host': 'localhost',
                'port': 5432,
                'database_name': 'test_db',
                'username': 'test_user',
                'password': 'test_pass'
            },
            'services': {
                'api': {
                    'host': '127.0.0.1',
                    'port': 7272
                }
            }
        }
        yaml.dump(config_data, f)
        temp_path = Path(f.name)

    yield temp_path

    # Cleanup
    temp_path.unlink(missing_ok=True)


@pytest.fixture
def test_config_no_db():
    """Create a config file without database configuration."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        config_data = {
            'installation': {
                'mode': 'localhost'
            },
            'services': {
                'api': {
                    'host': '127.0.0.1',
                    'port': 7272
                }
            }
        }
        yaml.dump(config_data, f)
        temp_path = Path(f.name)

    yield temp_path

    # Cleanup
    temp_path.unlink(missing_ok=True)


@pytest.fixture
def test_config_setup_mode():
    """Create a config file with setup_mode enabled."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        config_data = {
            'setup_mode': True,
            'installation': {
                'mode': 'localhost'
            },
            'database': {
                'type': 'postgresql',
                'host': 'localhost',
                'port': 5432,
                'database_name': 'test_db',
                'username': 'test_user',
                'password': 'test_pass'
            },
            'services': {
                'api': {
                    'host': '127.0.0.1',
                    'port': 7272
                }
            }
        }
        yaml.dump(config_data, f)
        temp_path = Path(f.name)

    yield temp_path

    # Cleanup
    temp_path.unlink(missing_ok=True)


class TestSetupStatusEndpoint:
    """Test the /api/setup/status endpoint."""

    def test_status_database_configured(self, test_config_file):
        """Test status when database is properly configured."""
        with patch('api.endpoints.setup.Path.cwd') as mock_cwd:
            mock_cwd.return_value = test_config_file.parent

            # Mock the database connection test
            with patch('api.endpoints.setup.DatabaseManager') as MockDBManager:
                mock_db = MagicMock()
                MockDBManager.return_value = mock_db

                # Import and create app after mocking
                from api.app import create_app
                app = create_app()
                client = TestClient(app)

                response = client.get("/api/setup/status")

                assert response.status_code == 200
                data = response.json()

                assert data["setup_mode"] == False
                assert data["database_configured"] == True
                assert data["requires_setup"] == False

    def test_status_no_database_config(self, test_config_no_db):
        """Test status when database configuration is missing."""
        with patch('api.endpoints.setup.Path.cwd') as mock_cwd:
            mock_cwd.return_value = test_config_no_db.parent

            from api.app import create_app
            app = create_app()
            client = TestClient(app)

            response = client.get("/api/setup/status")

            assert response.status_code == 200
            data = response.json()

            assert data["database_configured"] == False
            assert data["database_connected"] == False
            assert data["requires_setup"] == True

    def test_status_setup_mode_enabled(self, test_config_setup_mode):
        """Test status when setup_mode is enabled."""
        with patch('api.endpoints.setup.Path.cwd') as mock_cwd:
            mock_cwd.return_value = test_config_setup_mode.parent

            from api.app import create_app
            app = create_app()
            client = TestClient(app)

            response = client.get("/api/setup/status")

            assert response.status_code == 200
            data = response.json()

            assert data["setup_mode"] == True
            assert data["requires_setup"] == True

    def test_status_database_connection_error(self, test_config_file):
        """Test status when database connection fails."""
        with patch('api.endpoints.setup.Path.cwd') as mock_cwd:
            mock_cwd.return_value = test_config_file.parent

            # Mock the database connection to fail
            with patch('api.endpoints.setup.DatabaseManager') as MockDBManager:
                MockDBManager.side_effect = Exception("Connection failed")

                from api.app import create_app
                app = create_app()
                client = TestClient(app)

                response = client.get("/api/setup/status")

                assert response.status_code == 200
                data = response.json()

                assert data["database_configured"] == True
                assert data["database_connected"] == False
                assert data["database_error"] == "Connection failed"
                assert data["requires_setup"] == True


class TestSetupResetEndpoint:
    """Test the /api/setup/reset endpoint."""

    def test_reset_in_localhost_mode(self):
        """Test reset is allowed in localhost mode."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"
            config_data = {
                'mode': 'localhost',
                'database': {
                    'type': 'postgresql',
                    'host': 'localhost'
                }
            }

            with open(config_path, 'w') as f:
                yaml.dump(config_data, f)

            with patch('api.endpoints.setup.Path.cwd') as mock_cwd:
                mock_cwd.return_value = Path(tmpdir)

                from api.app import create_app
                app = create_app()
                client = TestClient(app)

                response = client.post("/api/setup/reset")

                assert response.status_code == 200
                data = response.json()

                assert data["success"] == True
                assert data["setup_mode"] == True

                # Verify config file was updated
                with open(config_path) as f:
                    updated_config = yaml.safe_load(f)
                assert updated_config["setup_mode"] == True

    def test_reset_denied_in_production_mode(self):
        """Test reset is denied in production mode."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"
            config_data = {
                'mode': 'production',
                'database': {
                    'type': 'postgresql',
                    'host': 'localhost'
                }
            }

            with open(config_path, 'w') as f:
                yaml.dump(config_data, f)

            with patch('api.endpoints.setup.Path.cwd') as mock_cwd:
                mock_cwd.return_value = Path(tmpdir)

                from api.app import create_app
                app = create_app()
                client = TestClient(app)

                response = client.post("/api/setup/reset")

                assert response.status_code == 403
                data = response.json()

                assert "development mode" in data["detail"]


class TestSetupModeMiddleware:
    """Test the SetupModeMiddleware behavior."""

    def test_middleware_blocks_api_in_setup_mode(self, test_config_setup_mode):
        """Test that API endpoints are blocked when in setup mode."""
        with patch('api.app.Path.cwd') as mock_cwd:
            mock_cwd.return_value = test_config_setup_mode.parent

            from api.app import create_app
            app = create_app()
            client = TestClient(app)

            # These endpoints should be blocked
            blocked_endpoints = [
                "/api/v1/projects",
                "/api/v1/agents",
                "/api/v1/messages",
                "/api/v1/tasks"
            ]

            for endpoint in blocked_endpoints:
                response = client.get(endpoint)
                assert response.status_code == 503
                data = response.json()
                assert data["error"] == "System setup required"
                assert data["requires_setup"] == True

    def test_middleware_allows_setup_endpoints(self, test_config_setup_mode):
        """Test that setup endpoints are accessible in setup mode."""
        with patch('api.app.Path.cwd') as mock_cwd:
            mock_cwd.return_value = test_config_setup_mode.parent

            from api.app import create_app
            app = create_app()
            client = TestClient(app)

            # These endpoints should be allowed
            allowed_endpoints = [
                "/",
                "/health",
                "/docs",
                "/api/setup/status",
                "/api/setup/detect-tools"
            ]

            for endpoint in allowed_endpoints:
                response = client.get(endpoint)
                # Should not return 503 (service unavailable)
                assert response.status_code != 503

    def test_middleware_allows_all_when_configured(self, test_config_file):
        """Test that all endpoints work when database is configured."""
        with patch('api.app.Path.cwd') as mock_cwd:
            mock_cwd.return_value = test_config_file.parent

            # Mock successful database connection
            with patch('giljo_mcp.database.DatabaseManager'):
                from api.app import create_app
                app = create_app()
                client = TestClient(app)

                # API endpoints should be accessible
                response = client.get("/api/v1/projects")
                # Should not return 503
                assert response.status_code != 503


class TestFrontendIntegration:
    """Test frontend integration with setup detection."""

    def test_dashboard_checks_setup_status(self):
        """Test that dashboard checks /api/setup/status on mount."""
        # This would be tested in frontend unit tests
        # Here we just verify the endpoint exists and returns expected format

        with patch('api.endpoints.setup.get_config') as mock_config:
            mock_config.return_value = MagicMock(
                mode='localhost',
                database=MagicMock(
                    host='localhost',
                    port=5432,
                    database_name='test',
                    username='user',
                    type='postgresql'
                )
            )

            from api.app import create_app
            app = create_app()
            client = TestClient(app)

            response = client.get("/api/setup/status")
            assert response.status_code == 200

            data = response.json()
            required_fields = [
                "setup_mode",
                "setup_complete",
                "database_configured",
                "database_connected",
                "requires_setup",
                "mode",
                "version"
            ]

            for field in required_fields:
                assert field in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])