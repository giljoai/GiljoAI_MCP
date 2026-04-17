# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# [CE] Community Edition -- source-available, single-user use only.

"""
Tests for --setup-only flag in install.py.

Verifies that when setup_only=True:
- Prereq checks (Python, PostgreSQL, Node.js) are skipped
- Dependency installation steps are skipped
- Frontend dependency installation is skipped
- Frontend mode prompt is skipped
- Shortcut creation is skipped
- Config generation and database setup still run
- HTTPS setup still runs
- Full flow still works when setup_only is False (regression)
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# install.py lives at repo root -- add to sys.path before importing
# TODO: Remove after editable install confirmed on all platforms
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from install import UnifiedInstaller, main  # noqa: E402


class TestSetupOnlyFlag:
    """Verify --setup-only click option is wired correctly."""

    def test_main_accepts_setup_only_flag(self):
        """The main() click command should accept --setup-only."""
        # click stores params on the command object
        param_names = [p.name for p in main.params]
        assert "setup_only" in param_names

    def test_setup_only_is_a_flag(self):
        """--setup-only should be a boolean flag, not a value option."""
        for p in main.params:
            if p.name == "setup_only":
                assert p.is_flag is True
                break
        else:
            pytest.fail("--setup-only param not found on main()")


class TestRunWithSetupOnly:
    """Verify run() skips the correct steps when setup_only=True."""

    @pytest.fixture
    def installer(self, tmp_path):
        """Create an installer with setup_only=True and all methods mocked."""
        settings = {
            "install_dir": str(tmp_path),
            "headless": True,
            "setup_only": True,
            "pg_password": "test",
        }
        with patch("install.get_platform_handler", return_value=MagicMock()):
            inst = UnifiedInstaller(settings=settings)

        # Mock every step method so nothing actually runs
        inst.welcome_screen = MagicMock()
        inst.ask_installation_questions = MagicMock()
        inst.check_python_version = MagicMock(return_value=True)
        inst.discover_postgresql = MagicMock(return_value={"found": True})
        inst.discover_nodejs = MagicMock(return_value={"found": True})
        inst.install_dependencies = MagicMock(return_value={"success": True})
        inst.generate_configs = MagicMock(return_value={"success": True})
        inst.setup_database = MagicMock(return_value={"success": True, "credentials": {}})
        inst.run_database_migrations = MagicMock(return_value={"success": True})
        inst.install_frontend_dependencies = MagicMock(return_value={"success": True})
        inst._prompt_frontend_mode = MagicMock()
        inst.setup_https = MagicMock(return_value={"enabled": False})
        inst.create_desktop_shortcuts = MagicMock()
        inst._print_success_summary = MagicMock()
        inst._print_header = MagicMock()

        return inst

    def test_skips_python_check(self, installer):
        installer.run()
        installer.check_python_version.assert_not_called()

    def test_skips_postgresql_discovery(self, installer):
        installer.run()
        installer.discover_postgresql.assert_not_called()

    def test_skips_nodejs_discovery(self, installer):
        installer.run()
        installer.discover_nodejs.assert_not_called()

    def test_skips_dependency_installation(self, installer):
        installer.run()
        installer.install_dependencies.assert_not_called()

    def test_skips_frontend_dependencies(self, installer):
        installer.run()
        installer.install_frontend_dependencies.assert_not_called()

    def test_skips_frontend_mode_prompt(self, installer):
        installer.run()
        installer._prompt_frontend_mode.assert_not_called()

    def test_skips_shortcuts(self, installer):
        # Even with create_shortcuts=True, setup_only should skip
        installer.settings["create_shortcuts"] = True
        installer.run()
        installer.create_desktop_shortcuts.assert_not_called()

    def test_still_shows_welcome(self, installer):
        installer.run()
        installer.welcome_screen.assert_called_once()

    def test_still_generates_configs(self, installer):
        installer.run()
        installer.generate_configs.assert_called_once()

    def test_still_sets_up_database(self, installer):
        installer.run()
        installer.setup_database.assert_called_once()

    def test_still_runs_migrations(self, installer):
        installer.run()
        installer.run_database_migrations.assert_called_once()

    def test_still_sets_up_https(self, installer):
        # setup_only is True but headless is False => HTTPS should run
        installer.settings["headless"] = False
        installer.run()
        installer.setup_https.assert_called_once()

    def test_returns_success(self, installer):
        result = installer.run()
        assert result["success"] is True

    def test_steps_contain_configs_generated(self, installer):
        result = installer.run()
        assert "configs_generated" in result["steps"]

    def test_steps_contain_database_created(self, installer):
        result = installer.run()
        assert "database_created" in result["steps"]

    def test_steps_do_not_contain_python_verified(self, installer):
        result = installer.run()
        assert "python_verified" not in result["steps"]

    def test_steps_do_not_contain_dependencies_installed(self, installer):
        result = installer.run()
        assert "dependencies_installed" not in result["steps"]

    def test_steps_do_not_contain_frontend_dependencies(self, installer):
        result = installer.run()
        assert "frontend_dependencies_installed" not in result["steps"]


class TestRunWithoutSetupOnly:
    """Regression: verify full flow still works when setup_only is False."""

    @pytest.fixture
    def installer(self, tmp_path):
        """Create an installer with setup_only=False (default) and all methods mocked."""
        settings = {
            "install_dir": str(tmp_path),
            "headless": True,
            "pg_password": "test",
        }
        with patch("install.get_platform_handler", return_value=MagicMock()):
            inst = UnifiedInstaller(settings=settings)

        inst.welcome_screen = MagicMock()
        inst.ask_installation_questions = MagicMock()
        inst.check_python_version = MagicMock(return_value=True)
        inst.discover_postgresql = MagicMock(return_value={"found": True})
        inst.discover_nodejs = MagicMock(return_value={"found": True})
        inst.install_dependencies = MagicMock(return_value={"success": True})
        inst.generate_configs = MagicMock(return_value={"success": True})
        inst.setup_database = MagicMock(return_value={"success": True, "credentials": {}})
        inst.run_database_migrations = MagicMock(return_value={"success": True})
        inst.install_frontend_dependencies = MagicMock(return_value={"success": True})
        inst._prompt_frontend_mode = MagicMock()
        inst.setup_https = MagicMock(return_value={"enabled": False})
        inst.create_desktop_shortcuts = MagicMock()
        inst._print_success_summary = MagicMock()
        inst._print_header = MagicMock()

        return inst

    def test_calls_python_check(self, installer):
        installer.run()
        installer.check_python_version.assert_called_once()

    def test_calls_postgresql_discovery(self, installer):
        installer.run()
        installer.discover_postgresql.assert_called_once()

    def test_calls_nodejs_discovery(self, installer):
        installer.run()
        installer.discover_nodejs.assert_called_once()

    def test_calls_dependency_installation(self, installer):
        installer.run()
        installer.install_dependencies.assert_called_once()

    def test_calls_frontend_dependencies(self, installer):
        installer.run()
        installer.install_frontend_dependencies.assert_called_once()

    def test_calls_configs_and_database(self, installer):
        installer.run()
        installer.generate_configs.assert_called_once()
        installer.setup_database.assert_called_once()

    def test_full_steps_present(self, installer):
        result = installer.run()
        assert "python_verified" in result["steps"]
        assert "dependencies_installed" in result["steps"]
        assert "configs_generated" in result["steps"]
        assert "database_created" in result["steps"]
        assert "frontend_dependencies_installed" in result["steps"]
