"""
Unit tests for database installer module
Tests PostgreSQL detection, database creation, and fallback script generation
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from installer.core.database import DatabaseInstaller, check_postgresql_connection, detect_postgresql_cli


class TestDatabaseInstaller(unittest.TestCase):
    """Test DatabaseInstaller class"""

    def setUp(self):
        """Set up test fixtures"""
        self.settings = {
            'pg_host': 'localhost',
            'pg_port': 5432,
            'pg_user': 'postgres',
            'pg_password': 'test_password',
            'batch': False
        }
        self.installer = DatabaseInstaller(self.settings)

    def test_initialization(self):
        """Test DatabaseInstaller initialization"""
        self.assertEqual(self.installer.pg_host, 'localhost')
        self.assertEqual(self.installer.pg_port, 5432)
        self.assertEqual(self.installer.pg_user, 'postgres')
        self.assertEqual(self.installer.db_name, 'giljo_mcp')
        self.assertIsNone(self.installer.owner_password)
        self.assertIsNone(self.installer.user_password)

    def test_version_constants(self):
        """Test version constants are defined correctly"""
        self.assertEqual(DatabaseInstaller.MIN_PG_VERSION, 14)
        self.assertEqual(DatabaseInstaller.MAX_PG_VERSION, 18)
        self.assertEqual(DatabaseInstaller.RECOMMENDED_VERSION, 18)

    def test_password_generation(self):
        """Test password generation"""
        password = self.installer.generate_password()
        self.assertEqual(len(password), 20)
        self.assertTrue(password.isalnum())

        # Test custom length
        password_30 = self.installer.generate_password(30)
        self.assertEqual(len(password_30), 30)

        # Test uniqueness
        password2 = self.installer.generate_password()
        self.assertNotEqual(password, password2)

    def test_postgresql_install_guide(self):
        """Test PostgreSQL installation guide generation"""
        with patch('platform.system', return_value='Windows'):
            guide = self.installer.get_postgresql_install_guide()
            self.assertIn('Windows', guide)
            self.assertIn('postgresql.org', guide)

        with patch('platform.system', return_value='Darwin'):
            guide = self.installer.get_postgresql_install_guide()
            self.assertIn('macOS', guide)
            self.assertIn('Homebrew', guide)

        with patch('platform.system', return_value='Linux'):
            guide = self.installer.get_postgresql_install_guide()
            self.assertIn('Linux', guide)
            self.assertIn('apt-get', guide)

    @patch('installer.core.database.psycopg2')
    def test_detect_postgresql_version_success(self, mock_psycopg2):
        """Test successful PostgreSQL version detection"""
        # Mock connection and cursor
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = Mock(return_value=False)

        # Mock version query results
        mock_cursor.fetchone.side_effect = [
            ("PostgreSQL 18.0 on x86_64-pc-linux-gnu",),
            ("180000",)
        ]

        mock_psycopg2.connect.return_value = mock_conn

        result = self.installer.detect_postgresql_version()

        self.assertTrue(result['success'])
        self.assertEqual(result['version'], 18)
        self.assertIn('PostgreSQL 18.0', result['version_string'])

    @patch('installer.core.database.psycopg2')
    def test_detect_postgresql_version_failure(self, mock_psycopg2):
        """Test PostgreSQL version detection with connection failure"""
        from psycopg2 import OperationalError

        mock_psycopg2.connect.side_effect = OperationalError("Connection refused")

        result = self.installer.detect_postgresql_version()

        self.assertFalse(result['success'])
        self.assertIn('error', result)

    def test_generate_windows_script(self):
        """Test Windows PowerShell script generation"""
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            scripts_dir = Path(tmpdir)
            self.installer.owner_password = 'test_owner_pass'
            self.installer.user_password = 'test_user_pass'

            script_path = self.installer.generate_windows_script(scripts_dir)

            self.assertTrue(script_path.exists())
            self.assertEqual(script_path.name, 'create_db.ps1')

            content = script_path.read_text()
            self.assertIn('GiljoAI MCP', content)
            self.assertIn('test_owner_pass', content)
            self.assertIn('test_user_pass', content)
            self.assertIn('giljo_mcp', content)
            self.assertIn('PowerShell', content)

    def test_generate_unix_script(self):
        """Test Unix/Linux bash script generation"""
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            scripts_dir = Path(tmpdir)
            self.installer.owner_password = 'test_owner_pass'
            self.installer.user_password = 'test_user_pass'

            script_path = self.installer.generate_unix_script(scripts_dir)

            self.assertTrue(script_path.exists())
            self.assertEqual(script_path.name, 'create_db.sh')

            content = script_path.read_text()
            self.assertIn('GiljoAI MCP', content)
            self.assertIn('test_owner_pass', content)
            self.assertIn('test_user_pass', content)
            self.assertIn('giljo_mcp', content)
            self.assertIn('#!/bin/bash', content)
            self.assertIn('set -euo pipefail', content)

    def test_save_credentials(self):
        """Test credential file creation"""
        import tempfile
        import os

        with tempfile.TemporaryDirectory() as tmpdir:
            # Change to temp directory
            original_cwd = os.getcwd()
            os.chdir(tmpdir)

            try:
                self.installer.owner_password = 'test_owner_pass'
                self.installer.user_password = 'test_user_pass'

                self.installer.save_credentials()

                self.assertIsNotNone(self.installer.credentials_file)
                self.assertTrue(self.installer.credentials_file.exists())

                content = self.installer.credentials_file.read_text()
                self.assertIn('giljo_mcp', content)
                self.assertIn('giljo_owner', content)
                self.assertIn('giljo_user', content)
                self.assertIn('test_owner_pass', content)
                self.assertIn('test_user_pass', content)
                self.assertIn('CONNECTION STRINGS', content.upper())

            finally:
                os.chdir(original_cwd)


class TestUtilityFunctions(unittest.TestCase):
    """Test utility functions"""

    @patch('socket.socket')
    def test_check_postgresql_connection_success(self, mock_socket):
        """Test successful PostgreSQL connection check"""
        mock_sock_instance = MagicMock()
        mock_sock_instance.connect_ex.return_value = 0
        mock_socket.return_value = mock_sock_instance

        result = check_postgresql_connection('localhost', 5432)

        self.assertTrue(result)
        mock_sock_instance.connect_ex.assert_called_once_with(('localhost', 5432))
        mock_sock_instance.close.assert_called_once()

    @patch('socket.socket')
    def test_check_postgresql_connection_failure(self, mock_socket):
        """Test failed PostgreSQL connection check"""
        mock_sock_instance = MagicMock()
        mock_sock_instance.connect_ex.return_value = 1
        mock_socket.return_value = mock_sock_instance

        result = check_postgresql_connection('localhost', 5432)

        self.assertFalse(result)

    @patch('socket.socket')
    def test_check_postgresql_connection_exception(self, mock_socket):
        """Test PostgreSQL connection check with exception"""
        mock_socket.side_effect = Exception("Network error")

        result = check_postgresql_connection('localhost', 5432)

        self.assertFalse(result)

    @patch('subprocess.run')
    def test_detect_postgresql_cli_success(self, mock_run):
        """Test successful psql detection"""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='psql (PostgreSQL) 18.0'
        )

        result = detect_postgresql_cli()

        self.assertIsNotNone(result)
        self.assertIn('18.0', result)

    @patch('subprocess.run')
    def test_detect_postgresql_cli_not_found(self, mock_run):
        """Test psql not found"""
        mock_run.side_effect = FileNotFoundError()

        result = detect_postgresql_cli()

        self.assertIsNone(result)


class TestDatabaseSetupFlow(unittest.TestCase):
    """Test complete database setup workflow"""

    def setUp(self):
        """Set up test fixtures"""
        self.settings = {
            'pg_host': 'localhost',
            'pg_port': 5432,
            'pg_user': 'postgres',
            'pg_password': 'test_password',
            'batch': False
        }

    @patch('installer.core.database.psycopg2', None)
    @patch('installer.core.database.check_postgresql_connection', return_value=True)
    def test_setup_without_psycopg2(self, mock_check):
        """Test setup flow when psycopg2 is not available"""
        installer = DatabaseInstaller(self.settings)

        with patch.object(installer, 'fallback_setup') as mock_fallback:
            mock_fallback.return_value = {'success': True}

            result = installer.setup()

            mock_fallback.assert_called_once()

    @patch('installer.core.database.check_postgresql_connection', return_value=False)
    def test_setup_postgresql_not_running(self, mock_check):
        """Test setup when PostgreSQL is not accessible"""
        installer = DatabaseInstaller(self.settings)

        result = installer.setup()

        self.assertFalse(result['success'])
        self.assertIn('Cannot connect to PostgreSQL', result['errors'][0])
        self.assertIn('postgresql_guide', result)


if __name__ == '__main__':
    unittest.main()
