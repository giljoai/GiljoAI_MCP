"""
Unit tests for DatabaseConfig legacy alias cleanup (Handover 0702).

Verifies that:
1. Legacy aliases (database_type, pg_host, pg_port, pg_database, pg_user, pg_password) are removed
2. New properties (type, host, port, database_name, username, password) work correctly
3. Config loading and validation still works
"""

import inspect

from src.giljo_mcp.config_manager import DatabaseConfig, get_config


class TestDatabaseConfigCleanup:
    """Test suite for DatabaseConfig legacy alias removal."""

    def test_new_fields_exist(self):
        """Verify all new fields are present."""
        db = DatabaseConfig()

        assert hasattr(db, "type"), "Missing 'type' field"
        assert hasattr(db, "host"), "Missing 'host' field"
        assert hasattr(db, "port"), "Missing 'port' field"
        assert hasattr(db, "database_name"), "Missing 'database_name' field"
        assert hasattr(db, "username"), "Missing 'username' field"
        assert hasattr(db, "password"), "Missing 'password' field"

    def test_legacy_aliases_removed(self):
        """Verify all legacy property aliases are removed."""
        db_class = DatabaseConfig
        props = {name for name, obj in inspect.getmembers(db_class) if isinstance(obj, property)}

        # These should NO LONGER be properties
        assert "database_type" not in props, "Legacy alias 'database_type' still exists"
        assert "pg_host" not in props, "Legacy alias 'pg_host' still exists"
        assert "pg_port" not in props, "Legacy alias 'pg_port' still exists"
        assert "pg_database" not in props, "Legacy alias 'pg_database' still exists"
        assert "pg_user" not in props, "Legacy alias 'pg_user' still exists"
        assert "pg_password" not in props, "Legacy alias 'pg_password' still exists"

    def test_new_fields_work(self):
        """Verify new fields can be set and retrieved."""
        db = DatabaseConfig()

        # Test setting values
        db.type = "postgresql"
        db.host = "testhost"
        db.port = 5433
        db.database_name = "testdb"
        db.username = "testuser"
        db.password = "testpass"

        # Test retrieving values
        assert db.type == "postgresql"
        assert db.host == "testhost"
        assert db.port == 5433
        assert db.database_name == "testdb"
        assert db.username == "testuser"
        assert db.password == "testpass"

    def test_defaults(self):
        """Verify default values are correct."""
        db = DatabaseConfig()

        assert db.type == "postgresql"
        assert db.host == "localhost"
        assert db.port == 5432
        assert db.username == "postgres"
        assert db.password == ""
        assert db.database_name == "giljo_mcp.db"

    def test_config_loads(self, monkeypatch):
        """Verify config still loads with new field names."""
        # Set password to bypass validation
        monkeypatch.setenv("DB_PASSWORD", "test")

        config = get_config()
        assert config is not None
        assert hasattr(config, "database")
        assert isinstance(config.database, DatabaseConfig)

    def test_env_var_override(self, monkeypatch):
        """Verify environment variables work with new field names."""
        monkeypatch.setenv("DB_HOST", "envhost")
        monkeypatch.setenv("DB_PORT", "5434")
        monkeypatch.setenv("DB_NAME", "envdb")
        monkeypatch.setenv("DB_USER", "envuser")
        monkeypatch.setenv("DB_PASSWORD", "envpass")

        from src.giljo_mcp.config_manager import ConfigManager

        config = ConfigManager()

        assert config.database.host == "envhost"
        assert config.database.port == 5434
        assert config.database.database_name == "envdb"
        assert config.database.username == "envuser"
        assert config.database.password == "envpass"
