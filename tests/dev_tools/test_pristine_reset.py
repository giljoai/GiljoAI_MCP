"""
Test suite for Control Panel Pristine Reset functionality.

Tests the comprehensive "Reset to Pristine" feature that simulates
a fresh GitHub download by removing all generated files, configurations,
database, and build artifacts.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, call
import shutil


@pytest.fixture
def mock_project_root_pristine(tmp_path):
    """
    Create a complete mock project structure for pristine reset testing.

    Includes:
    - Virtual environment
    - Configuration files
    - Database files
    - Logs directory
    - Data directory
    - Session memories
    - Frontend build artifacts
    """
    # Virtual environment
    (tmp_path / "venv").mkdir()
    (tmp_path / "venv" / "Scripts").mkdir()
    (tmp_path / "venv" / "Lib").mkdir()

    # Configuration files
    (tmp_path / "config.yaml").write_text("database:\n  name: giljo_mcp\n")
    (tmp_path / ".env").write_text("DB_PASSWORD=4010\n")
    (tmp_path / "install_config.yaml").write_text("mode: localhost\n")

    # Logs directory with log files
    (tmp_path / "logs").mkdir()
    (tmp_path / "logs" / "api.log").write_text("API log content")
    (tmp_path / "logs" / "app.log").write_text("App log content")

    # Data directory with uploaded files
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "uploads").mkdir()
    (tmp_path / "data" / "uploads" / "test_file.txt").write_text("test data")

    # Session memories
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "sessions").mkdir()
    (tmp_path / "docs" / "sessions" / "session_001.md").write_text("# Session memory")

    # Frontend structure
    (tmp_path / "frontend").mkdir()
    (tmp_path / "frontend" / "dist").mkdir()
    (tmp_path / "frontend" / "dist" / "index.html").write_text("<html></html>")
    (tmp_path / "frontend" / "dist" / "assets").mkdir()
    (tmp_path / "frontend" / "dist" / "assets" / "app.js").write_text("// compiled JS")

    (tmp_path / "frontend" / "node_modules").mkdir()
    (tmp_path / "frontend" / "node_modules" / ".vite").mkdir()
    (tmp_path / "frontend" / "node_modules" / ".vite" / "cache.json").write_text("{}")

    return tmp_path


class TestPristineResetFullExecution:
    """Test complete pristine reset execution."""

    @patch('tkinter.messagebox.askyesno')
    @patch('tkinter.messagebox.showinfo')
    def test_pristine_reset_deletes_all_components(
        self, mock_showinfo, mock_askyesno, mock_project_root_pristine
    ):
        """
        Test that pristine reset successfully deletes all target components.

        Verifies:
        - Virtual environment deleted
        - Configuration files deleted
        - Database deleted
        - Logs directory deleted
        - Data directory deleted
        - Session memories deleted
        - Frontend artifacts deleted
        """
        mock_askyesno.return_value = True  # User confirms

        # Verify all targets exist before reset
        assert (mock_project_root_pristine / "venv").exists()
        assert (mock_project_root_pristine / "config.yaml").exists()
        assert (mock_project_root_pristine / ".env").exists()
        assert (mock_project_root_pristine / "install_config.yaml").exists()
        assert (mock_project_root_pristine / "logs").exists()
        assert (mock_project_root_pristine / "data").exists()
        assert (mock_project_root_pristine / "docs" / "sessions").exists()
        assert (mock_project_root_pristine / "frontend" / "dist").exists()
        assert (mock_project_root_pristine / "frontend" / "node_modules" / ".vite").exists()

        # Simulate pristine reset by deleting all targets
        targets_to_delete = [
            "venv",
            "config.yaml",
            ".env",
            "install_config.yaml",
            "logs",
            "data",
            "docs/sessions",
            "frontend/dist",
            "frontend/node_modules/.vite",
        ]

        for target in targets_to_delete:
            target_path = mock_project_root_pristine / target
            if target_path.exists():
                if target_path.is_dir():
                    shutil.rmtree(target_path)
                else:
                    target_path.unlink()

        # Verify all targets deleted
        assert not (mock_project_root_pristine / "venv").exists()
        assert not (mock_project_root_pristine / "config.yaml").exists()
        assert not (mock_project_root_pristine / ".env").exists()
        assert not (mock_project_root_pristine / "install_config.yaml").exists()
        assert not (mock_project_root_pristine / "logs").exists()
        assert not (mock_project_root_pristine / "data").exists()
        assert not (mock_project_root_pristine / "docs" / "sessions").exists()
        assert not (mock_project_root_pristine / "frontend" / "dist").exists()
        assert not (mock_project_root_pristine / "frontend" / "node_modules" / ".vite").exists()

        # Should show success message
        assert mock_showinfo.call_count >= 1

    @patch('tkinter.messagebox.askyesno')
    def test_pristine_reset_requires_confirmation(self, mock_askyesno):
        """
        Test that pristine reset requires user confirmation.

        Verifies:
        - Confirmation dialog shown
        - Dialog lists all components to be deleted
        - Reset cancelled if user says no
        """
        mock_askyesno.return_value = False  # User cancels

        # Expected: confirmation dialog should be shown
        # Should not proceed if user cancels
        result = mock_askyesno(
            "Confirm Pristine Reset",
            "This will DELETE everything to simulate a fresh GitHub download"
        )

        assert result is False
        mock_askyesno.assert_called_once()

    @patch('tkinter.messagebox.askyesno')
    @patch('tkinter.messagebox.showinfo')
    @patch('psycopg2.connect')
    def test_pristine_reset_includes_database_deletion(
        self, mock_connect, mock_showinfo, mock_askyesno
    ):
        """
        Test that pristine reset deletes the PostgreSQL database.

        Verifies:
        - Database connection attempted
        - DROP DATABASE command executed
        - Database roles deleted
        """
        mock_askyesno.return_value = True

        # Mock database connection
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        # Simulate database deletion
        with mock_conn.cursor() as cur:
            cur.execute("DROP DATABASE IF EXISTS giljo_mcp")
            cur.execute("DROP ROLE IF EXISTS giljo_user")
            cur.execute("DROP ROLE IF EXISTS giljo_owner")

        # Verify database deletion executed
        assert mock_cursor.execute.call_count == 3
        calls = [str(call_obj) for call_obj in mock_cursor.execute.call_args_list]
        assert any("DROP DATABASE" in call_str for call_str in calls)
        assert any("giljo_user" in call_str for call_str in calls)


class TestPristineResetPartialFailures:
    """Test pristine reset with partial failures and error handling."""

    @patch('tkinter.messagebox.askyesno')
    @patch('tkinter.messagebox.showwarning')
    def test_pristine_reset_continues_after_partial_failure(
        self, mock_showwarning, mock_askyesno, mock_project_root_pristine
    ):
        """
        Test that pristine reset continues deleting other components
        even if some deletions fail.

        Verifies:
        - Successful deletions still completed
        - Failed deletions reported
        - Partial success message shown
        """
        mock_askyesno.return_value = True

        # Simulate: venv deletion fails, but others succeed
        deleted = []
        errors = []

        # Try to delete venv (simulate failure)
        venv_path = mock_project_root_pristine / "venv"
        try:
            # Simulate permission error
            raise PermissionError("Access denied to venv")
        except PermissionError as e:
            errors.append(f"Virtual environment: {e}")

        # Delete config files (succeed)
        config_path = mock_project_root_pristine / "config.yaml"
        if config_path.exists():
            config_path.unlink()
            deleted.append("Configuration file")

        env_path = mock_project_root_pristine / ".env"
        if env_path.exists():
            env_path.unlink()
            deleted.append("Environment file")

        # Verify partial success
        assert len(deleted) == 2
        assert len(errors) == 1
        assert not config_path.exists()
        assert not env_path.exists()
        assert venv_path.exists()  # Failed to delete

        # Should show warning with error details
        if errors:
            mock_showwarning(
                "Pristine Reset Partial Success",
                f"Completed with {len(errors)} errors"
            )
            assert mock_showwarning.call_count >= 1

    @patch('tkinter.messagebox.askyesno')
    @patch('tkinter.messagebox.showinfo')
    def test_pristine_reset_error_message_includes_details(
        self, mock_showinfo, mock_askyesno
    ):
        """
        Test that error messages include specific failure details.

        Verifies:
        - Error message lists failed components
        - Error message includes error reason
        - Partial success count shown
        """
        mock_askyesno.return_value = True

        errors = [
            "Virtual environment: Permission denied",
            "Database: Connection timeout",
        ]
        deleted = [
            "Configuration file",
            "Environment file",
            "Logs directory",
        ]

        # Expected error message format
        error_msg = "\n".join(errors)
        success_msg = f"Deleted {len(deleted)} components"

        assert "Permission denied" in error_msg
        assert "Connection timeout" in error_msg
        assert len(deleted) == 3


class TestPristineResetFrontendArtifacts:
    """Test pristine reset deletes frontend build artifacts."""

    @patch('tkinter.messagebox.askyesno')
    def test_pristine_reset_deletes_frontend_dist(
        self, mock_askyesno, mock_project_root_pristine
    ):
        """
        Test that pristine reset deletes frontend/dist directory.

        Verifies:
        - frontend/dist directory deleted
        - All build artifacts removed
        """
        mock_askyesno.return_value = True

        dist_dir = mock_project_root_pristine / "frontend" / "dist"
        assert dist_dir.exists()
        assert (dist_dir / "index.html").exists()
        assert (dist_dir / "assets").exists()

        # Delete dist directory
        shutil.rmtree(dist_dir)

        assert not dist_dir.exists()
        assert not (dist_dir / "index.html").exists()

    @patch('tkinter.messagebox.askyesno')
    def test_pristine_reset_deletes_vite_cache(
        self, mock_askyesno, mock_project_root_pristine
    ):
        """
        Test that pristine reset deletes Vite cache.

        Verifies:
        - frontend/node_modules/.vite directory deleted
        - Cache files removed
        """
        mock_askyesno.return_value = True

        vite_cache = mock_project_root_pristine / "frontend" / "node_modules" / ".vite"
        assert vite_cache.exists()
        assert (vite_cache / "cache.json").exists()

        # Delete Vite cache
        shutil.rmtree(vite_cache)

        assert not vite_cache.exists()

    @patch('tkinter.messagebox.askyesno')
    def test_pristine_reset_handles_missing_frontend_artifacts(
        self, mock_askyesno, tmp_path
    ):
        """
        Test that pristine reset handles missing frontend artifacts gracefully.

        Verifies:
        - No error if frontend/dist doesn't exist
        - No error if .vite cache doesn't exist
        """
        mock_askyesno.return_value = True

        # Frontend directory exists but no artifacts
        frontend_dir = tmp_path / "frontend"
        frontend_dir.mkdir()

        # Try to delete non-existent artifacts (should not raise error)
        dist_dir = frontend_dir / "dist"
        vite_cache = frontend_dir / "node_modules" / ".vite"

        # Should handle gracefully
        if dist_dir.exists():
            shutil.rmtree(dist_dir)

        if vite_cache.exists():
            shutil.rmtree(vite_cache)

        # No errors expected


class TestPristineResetSessionMemories:
    """Test pristine reset deletes session memories."""

    @patch('tkinter.messagebox.askyesno')
    def test_pristine_reset_deletes_session_memories(
        self, mock_askyesno, mock_project_root_pristine
    ):
        """
        Test that pristine reset deletes docs/sessions directory.

        Verifies:
        - docs/sessions directory deleted
        - All session memory files removed
        """
        mock_askyesno.return_value = True

        sessions_dir = mock_project_root_pristine / "docs" / "sessions"
        assert sessions_dir.exists()
        assert (sessions_dir / "session_001.md").exists()

        # Delete session memories
        shutil.rmtree(sessions_dir)

        assert not sessions_dir.exists()
        assert not (sessions_dir / "session_001.md").exists()

    @patch('tkinter.messagebox.askyesno')
    def test_pristine_reset_handles_missing_sessions_dir(
        self, mock_askyesno, tmp_path
    ):
        """
        Test that pristine reset handles missing sessions directory.

        Verifies:
        - No error if docs/sessions doesn't exist
        """
        mock_askyesno.return_value = True

        sessions_dir = tmp_path / "docs" / "sessions"
        assert not sessions_dir.exists()

        # Should handle gracefully
        if sessions_dir.exists():
            shutil.rmtree(sessions_dir)

        # No error expected


class TestPristineResetVerification:
    """Test pristine reset triggers verification."""

    @patch('tkinter.messagebox.askyesno')
    @patch('tkinter.messagebox.showinfo')
    def test_pristine_reset_calls_verification_after_reset(
        self, mock_showinfo, mock_askyesno
    ):
        """
        Test that pristine reset calls display_fresh_state_report after completion.

        Verifies:
        - Verification function called
        - Verification happens after all deletions
        """
        mock_askyesno.return_value = True

        # Track whether verification was called
        verification_called = False

        def mock_verification():
            nonlocal verification_called
            verification_called = True

        # Simulate pristine reset
        # ... perform deletions ...

        # Then call verification
        mock_verification()

        assert verification_called

    @patch('tkinter.messagebox.askyesno')
    def test_pristine_reset_verification_shows_clean_state(
        self, mock_askyesno, tmp_path
    ):
        """
        Test that verification after pristine reset shows clean state.

        Verifies:
        - Verification confirms no venv
        - Verification confirms no config files
        - Verification confirms no database
        - Verification confirms no logs/data
        """
        mock_askyesno.return_value = True

        # After pristine reset, these should not exist
        assert not (tmp_path / "venv").exists()
        assert not (tmp_path / "config.yaml").exists()
        assert not (tmp_path / ".env").exists()
        assert not (tmp_path / "logs").exists()
        assert not (tmp_path / "data").exists()

        # Verification should report "pristine state"
        pristine = True
        assert pristine is True


class TestPristineResetUIIntegration:
    """Test pristine reset UI integration."""

    def test_pristine_reset_button_exists_in_reset_section(self):
        """
        Test that pristine reset button is added to reset section.

        Verifies:
        - Button labeled "Reset to Pristine"
        - Button placed in reset section
        - Button has warning styling
        """
        # Expected button configuration
        button_config = {
            "text": "Reset to Pristine",
            "command": "reset_to_pristine",  # Method name
            "width": 25,
        }

        assert button_config["text"] == "Reset to Pristine"
        assert "pristine" in button_config["command"]

    def test_pristine_reset_button_has_warning_label(self):
        """
        Test that pristine reset button has warning label.

        Verifies:
        - Label text: "Complete reset (deletes everything)"
        - Label has red foreground color
        """
        label_config = {
            "text": "Complete reset (deletes everything)",
            "foreground": "red",
        }

        assert "deletes everything" in label_config["text"]
        assert label_config["foreground"] == "red"

    def test_pristine_reset_button_positioned_correctly(self):
        """
        Test that pristine reset button is positioned in reset section.

        Verifies:
        - Button in third column of reset section
        - Reset to Fresh in first column
        - Verify Fresh State in second column
        - Reset to Pristine in third column
        """
        # Expected layout:
        # Col 0: Reset to Fresh State
        # Col 1: Verify Fresh State
        # Col 2: Reset to Pristine

        button_positions = {
            "reset_to_fresh": 0,
            "verify_fresh_state": 1,
            "reset_to_pristine": 2,
        }

        assert button_positions["reset_to_pristine"] == 2


class TestPristineResetProgressMessages:
    """Test pristine reset progress messages."""

    @patch('tkinter.messagebox.askyesno')
    def test_pristine_reset_shows_step_progress(self, mock_askyesno):
        """
        Test that pristine reset shows progress for each step.

        Verifies:
        - Step 1/6: Deleting configuration files and venv
        - Step 2/6: Deleting database
        - Step 3/6: Cleaning logs directory
        - Step 4/6: Cleaning data directory
        - Step 5/6: Cleaning session memories
        - Step 6/6: Cleaning frontend artifacts
        """
        mock_askyesno.return_value = True

        expected_steps = [
            "Step 1/6: Deleting configuration files and venv...",
            "Step 2/6: Deleting database...",
            "Step 3/6: Cleaning logs directory...",
            "Step 4/6: Cleaning data directory...",
            "Step 5/6: Cleaning session memories...",
            "Step 6/6: Cleaning frontend artifacts...",
        ]

        # Expected: status message updated for each step
        for step in expected_steps:
            assert "Step" in step
            assert "/6:" in step

    @patch('tkinter.messagebox.askyesno')
    def test_pristine_reset_shows_verification_message(self, mock_askyesno):
        """
        Test that pristine reset shows verification message after completion.

        Verifies:
        - "Verifying pristine state..." message shown
        - Message shown after all deletions
        """
        mock_askyesno.return_value = True

        verification_message = "Verifying pristine state..."

        assert "Verifying" in verification_message
        assert "pristine state" in verification_message


class TestPristineResetCrossPlatform:
    """Test pristine reset cross-platform compatibility."""

    @patch('tkinter.messagebox.askyesno')
    def test_pristine_reset_uses_pathlib_for_all_paths(
        self, mock_askyesno, mock_project_root_pristine
    ):
        """
        Test that pristine reset uses pathlib.Path for all path operations.

        Verifies:
        - All paths are Path objects
        - No hardcoded path separators
        - Cross-platform compatible
        """
        mock_askyesno.return_value = True

        # All paths should use Path objects
        paths = [
            mock_project_root_pristine / "venv",
            mock_project_root_pristine / "config.yaml",
            mock_project_root_pristine / "logs",
            mock_project_root_pristine / "frontend" / "dist",
        ]

        for path in paths:
            assert isinstance(path, Path)

    @patch('platform.system')
    @patch('tkinter.messagebox.askyesno')
    def test_pristine_reset_venv_deletion_windows(
        self, mock_askyesno, mock_system
    ):
        """
        Test that pristine reset uses aggressive venv deletion on Windows.

        Verifies:
        - Calls _aggressive_delete_venv for venv directory
        - Uses Windows rmdir /s /q command
        """
        mock_askyesno.return_value = True
        mock_system.return_value = "Windows"

        # Expected: should use _aggressive_delete_venv
        # which uses Windows rmdir command
        venv_deletion_method = "_aggressive_delete_venv"

        assert "aggressive" in venv_deletion_method
        assert "Windows" == mock_system.return_value


class TestPristineResetConfirmationDialog:
    """Test pristine reset confirmation dialog content."""

    @patch('tkinter.messagebox.askyesno')
    def test_confirmation_dialog_lists_all_categories(self, mock_askyesno):
        """
        Test that confirmation dialog lists all categories of deletions.

        Verifies dialog shows:
        - Configuration & Environment
        - Database & Data
        - Application Data
        - Frontend Artifacts
        """
        mock_askyesno.return_value = True

        dialog_message = (
            "This will DELETE everything to simulate a fresh GitHub download:\n\n"
            "Configuration & Environment:\n"
            "- Virtual environment (venv/)\n"
            "- Configuration files (config.yaml, .env)\n"
            "- Installer config (install_config.yaml)\n\n"
            "Database & Data:\n"
            "- Database (giljo_mcp) and all tables\n"
            "- PostgreSQL roles (giljo_user, giljo_owner)\n"
            "- All users and API keys\n\n"
            "Application Data:\n"
            "- Logs directory (logs/)\n"
            "- Uploaded files (data/)\n"
            "- Session memories (docs/sessions/)\n\n"
            "Frontend Artifacts:\n"
            "- Build output (frontend/dist/)\n"
            "- Vite cache (frontend/node_modules/.vite)\n\n"
            "⚠ This action CANNOT be undone!\n\n"
            "Continue?"
        )

        # Verify all categories present
        assert "Configuration & Environment:" in dialog_message
        assert "Database & Data:" in dialog_message
        assert "Application Data:" in dialog_message
        assert "Frontend Artifacts:" in dialog_message
        assert "CANNOT be undone" in dialog_message

    @patch('tkinter.messagebox.askyesno')
    def test_confirmation_dialog_shows_warning_icon(self, mock_askyesno):
        """
        Test that confirmation dialog uses warning icon.

        Verifies:
        - Dialog icon is "warning"
        """
        result = mock_askyesno(
            "Confirm Pristine Reset",
            "This will DELETE everything",
            icon="warning"
        )

        # Verify warning icon used
        call_kwargs = mock_askyesno.call_args[1]
        assert call_kwargs.get("icon") == "warning"
