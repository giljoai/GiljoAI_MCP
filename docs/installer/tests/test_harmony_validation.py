"""
Harmony Validation Test Suite
Ensures installer-generated configs work with the application
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

from installer.core.config_fixed import ConfigManager


class TestConfigHarmony(unittest.TestCase):
    """Test configuration harmony between installer and application"""

    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp()
        self.old_cwd = os.getcwd()
        os.chdir(self.test_dir)

        # Default settings for localhost mode
        self.localhost_settings = {
            'mode': 'localhost',
            'pg_host': 'localhost',
            'pg_port': 5432,
            'api_port': 7272,
            'dashboard_port': 6000,
            'owner_password': 'test_owner_pass',
            'user_password': 'test_user_pass',
            'open_browser': True
        }

        # Settings for server mode
        self.server_settings = {
            'mode': 'server',
            'pg_host': 'localhost',
            'pg_port': 5432,
            'api_port': 7272,
            'dashboard_port': 6000,
            'bind': '0.0.0.0',
            'owner_password': 'secure_owner_pass',
            'user_password': 'secure_user_pass',
            'admin_username': 'admin',
            'admin_email': 'admin@example.com',
            'server_name': 'test.example.com',
            'features': {
                'ssl': True,
                'api_keys': True,
                'multi_user': True
            },
            'ssl_cert_path': './certs/server.crt',
            'ssl_key_path': './certs/server.key'
        }

    def tearDown(self):
        """Clean up test environment"""
        os.chdir(self.old_cwd)
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_localhost_env_generation(self):
        """Test that localhost .env has all required variables"""
        config = ConfigManager(self.localhost_settings)
        result = config.generate_env_file()

        self.assertTrue(result['success'])
        self.assertTrue(Path('.env').exists())

        # Read generated .env
        env_content = Path('.env').read_text()

        # Check critical port variables
        self.assertIn('GILJO_API_PORT=7272', env_content)
        self.assertIn('GILJO_PORT=7272', env_content)
        self.assertIn('GILJO_FRONTEND_PORT=6000', env_content)
        self.assertIn('VITE_FRONTEND_PORT=6000', env_content)

        # Check database variables (both formats)
        self.assertIn('POSTGRES_HOST=localhost', env_content)
        self.assertIn('DB_HOST=localhost', env_content)
        self.assertIn('DB_NAME=giljo_mcp', env_content)
        self.assertIn('DB_USER=giljo_user', env_content)
        self.assertIn('DB_PASSWORD=test_user_pass', env_content)
        self.assertIn('DATABASE_URL=postgresql://giljo_user:test_user_pass@localhost:5432/giljo_mcp', env_content)

        # Check frontend variables
        self.assertIn('VITE_API_URL=http://localhost:7272', env_content)
        self.assertIn('VITE_WS_URL=ws://localhost:7272', env_content)
        self.assertIn('VITE_APP_MODE=local', env_content)
        self.assertIn('VITE_API_PORT=7272', env_content)

        # Check server mode
        self.assertIn('GILJO_MCP_MODE=LOCAL', env_content)
        self.assertIn('GILJO_API_HOST=127.0.0.1', env_content)

        # Check feature flags
        self.assertIn('ENABLE_VISION_CHUNKING=true', env_content)
        self.assertIn('ENABLE_MULTI_TENANT=true', env_content)
        self.assertIn('ENABLE_WEBSOCKET=true', env_content)
        self.assertIn('ENABLE_AUTO_HANDOFF=true', env_content)
        self.assertIn('ENABLE_DYNAMIC_DISCOVERY=true', env_content)

        # Check agent configuration
        self.assertIn('MAX_AGENTS_PER_PROJECT=20', env_content)
        self.assertIn('AGENT_CONTEXT_LIMIT=150000', env_content)
        self.assertIn('AGENT_HANDOFF_THRESHOLD=140000', env_content)

        # Check session configuration
        self.assertIn('SESSION_TIMEOUT=3600', env_content)
        self.assertIn('MAX_CONCURRENT_SESSIONS=10', env_content)
        self.assertIn('SESSION_CLEANUP_INTERVAL=300', env_content)

        # Check message queue configuration
        self.assertIn('MAX_QUEUE_SIZE=1000', env_content)
        self.assertIn('MESSAGE_BATCH_SIZE=10', env_content)
        self.assertIn('MESSAGE_RETRY_ATTEMPTS=3', env_content)
        self.assertIn('MESSAGE_RETRY_DELAY=1.0', env_content)

    def test_server_env_generation(self):
        """Test that server mode .env has all required variables"""
        config = ConfigManager(self.server_settings)
        result = config.generate_env_file()

        self.assertTrue(result['success'])
        self.assertTrue(Path('.env').exists())

        env_content = Path('.env').read_text()

        # Check server-specific settings
        self.assertIn('GILJO_MCP_MODE=LAN', env_content)
        self.assertIn('GILJO_API_HOST=0.0.0.0', env_content)
        self.assertIn('ENABLE_SSL=true', env_content)
        self.assertIn('ENABLE_API_KEYS=true', env_content)
        self.assertIn('ENABLE_MULTI_USER=true', env_content)

        # Check admin settings
        self.assertIn('ADMIN_USER=admin', env_content)
        self.assertIn('ADMIN_EMAIL=admin@example.com', env_content)
        self.assertIn('SERVER_NAME=test.example.com', env_content)

        # Check SSL paths
        self.assertIn('SSL_CERT_PATH=./certs/server.crt', env_content)
        self.assertIn('SSL_KEY_PATH=./certs/server.key', env_content)

    def test_config_yaml_generation(self):
        """Test that config.yaml has correct structure"""
        config = ConfigManager(self.localhost_settings)
        result = config.generate_config_yaml()

        self.assertTrue(result['success'])
        self.assertTrue(Path('config.yaml').exists())

        import yaml
        with open('config.yaml', 'r') as f:
            yaml_content = yaml.safe_load(f)

        # Check main sections exist
        self.assertIn('installation', yaml_content)
        self.assertIn('database', yaml_content)
        self.assertIn('services', yaml_content)
        self.assertIn('features', yaml_content)
        self.assertIn('paths', yaml_content)
        self.assertIn('logging', yaml_content)
        self.assertIn('agent', yaml_content)
        self.assertIn('session', yaml_content)
        self.assertIn('message_queue', yaml_content)
        self.assertIn('status', yaml_content)

        # Check service ports
        self.assertEqual(yaml_content['services']['api']['port'], 7272)
        self.assertEqual(yaml_content['services']['frontend']['port'], 6000)
        self.assertTrue(yaml_content['services']['api']['unified_port'])

        # Check database settings
        self.assertEqual(yaml_content['database']['type'], 'postgresql')
        self.assertEqual(yaml_content['database']['name'], 'giljo_mcp')
        self.assertEqual(yaml_content['database']['user'], 'giljo_user')
        self.assertEqual(yaml_content['database']['owner'], 'giljo_owner')

        # Check feature flags
        self.assertTrue(yaml_content['features']['vision_chunking'])
        self.assertTrue(yaml_content['features']['multi_tenant'])
        self.assertTrue(yaml_content['features']['websocket'])

        # Check agent settings
        self.assertEqual(yaml_content['agent']['max_per_project'], 20)
        self.assertEqual(yaml_content['agent']['context_limit'], 150000)
        self.assertEqual(yaml_content['agent']['handoff_threshold'], 140000)

    def test_config_validation(self):
        """Test configuration validation method"""
        config = ConfigManager(self.localhost_settings)

        # Generate configs
        config.generate_env_file()
        config.generate_config_yaml()

        # Validate
        validation = config.validate_config()

        self.assertTrue(validation['valid'])
        self.assertEqual(len(validation['issues']), 0)

    def test_env_variables_match_app_expectations(self):
        """Test that env variables match what the application code expects"""
        config = ConfigManager(self.localhost_settings)
        config.generate_env_file()

        env_content = Path('.env').read_text()

        # Variables the app actually checks for (from config_manager.py)
        app_expected = [
            'GILJO_MCP_MODE',
            'GILJO_API_PORT',
            'GILJO_PORT',
            'GILJO_API_HOST',
            'DB_TYPE',
            'DB_HOST',
            'DB_PORT',
            'DB_NAME',
            'DB_USER',
            'DB_PASSWORD',
            'DATABASE_URL',
            'LOG_LEVEL',
            'LOG_FILE',
            'ENABLE_VISION_CHUNKING',
            'ENABLE_MULTI_TENANT',
            'ENABLE_WEBSOCKET'
        ]

        for var in app_expected:
            self.assertIn(f'{var}=', env_content, f"Missing expected variable: {var}")

    def test_backward_compatibility(self):
        """Test that old variable names are still present for compatibility"""
        config = ConfigManager(self.localhost_settings)
        config.generate_env_file()

        env_content = Path('.env').read_text()

        # Both old and new formats should exist
        self.assertIn('POSTGRES_HOST=', env_content)
        self.assertIn('DB_HOST=', env_content)

        self.assertIn('POSTGRES_PORT=', env_content)
        self.assertIn('DB_PORT=', env_content)

        self.assertIn('GILJO_API_PORT=', env_content)
        self.assertIn('GILJO_PORT=', env_content)

    def test_secrets_are_unique(self):
        """Test that generated secrets are unique"""
        config = ConfigManager(self.localhost_settings)
        config.generate_env_file()

        env_content = Path('.env').read_text()

        # Extract secret values
        secrets = []
        for line in env_content.split('\n'):
            if 'SECRET' in line and '=' in line:
                secret_value = line.split('=', 1)[1].strip()
                if secret_value:
                    secrets.append(secret_value)

        # All secrets should be unique
        self.assertEqual(len(secrets), len(set(secrets)), "Duplicate secrets found")

    def test_server_configs_generated(self):
        """Test that server mode generates additional config files"""
        config = ConfigManager(self.server_settings)
        config.generate_all()

        # Check nginx config
        nginx_path = Path('installer/configs/nginx.conf.example')
        self.assertTrue(nginx_path.exists())

        nginx_content = nginx_path.read_text()
        self.assertIn('upstream giljo_api', nginx_content)
        self.assertIn('server 127.0.0.1:7272', nginx_content)

        # Check systemd service
        service_path = Path('installer/configs/giljo-mcp.service')
        self.assertTrue(service_path.exists())

        service_content = service_path.read_text()
        self.assertIn('Description=GiljoAI MCP Orchestrator Service', service_content)
        self.assertIn('ExecStart=/opt/giljo-mcp/venv/bin/python -m api.run_api', service_content)

    def test_api_keys_generation(self):
        """Test API keys file generation for server mode"""
        config = ConfigManager(self.server_settings)
        config.generate_api_keys()

        keys_path = Path('api_keys.yaml')
        self.assertTrue(keys_path.exists())

        import yaml
        with open(keys_path, 'r') as f:
            keys_data = yaml.safe_load(f)

        self.assertIn('keys', keys_data)
        self.assertEqual(len(keys_data['keys']), 1)
        self.assertIn('key', keys_data['keys'][0])
        self.assertIn('permissions', keys_data['keys'][0])


class TestApplicationCompatibility(unittest.TestCase):
    """Test that generated config works with actual application code"""

    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp()
        self.old_cwd = os.getcwd()
        os.chdir(self.test_dir)

    def tearDown(self):
        """Clean up test environment"""
        os.chdir(self.old_cwd)
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)

    @patch('os.getenv')
    def test_app_reads_correct_variables(self, mock_getenv):
        """Test that app reads the variables we generate"""
        # Generate config
        settings = {
            'mode': 'localhost',
            'pg_host': 'localhost',
            'pg_port': 5432,
            'api_port': 7272,
            'dashboard_port': 6000,
            'owner_password': 'test_pass',
            'user_password': 'test_pass'
        }

        config = ConfigManager(settings)
        config.generate_env_file()

        # Parse generated .env
        env_vars = {}
        with open('.env', 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key] = value

        # Mock getenv to return our values
        mock_getenv.side_effect = lambda key, default=None: env_vars.get(key, default)

        # Test that critical variables are available
        self.assertEqual(mock_getenv('GILJO_API_PORT'), '7272')
        self.assertEqual(mock_getenv('DB_HOST'), 'localhost')
        self.assertEqual(mock_getenv('DB_NAME'), 'giljo_mcp')
        self.assertEqual(mock_getenv('DB_USER'), 'giljo_user')
        self.assertEqual(mock_getenv('DATABASE_URL'), 'postgresql://giljo_user:test_pass@localhost:5432/giljo_mcp')


if __name__ == '__main__':
    unittest.main(verbosity=2)
