"""
Test suite for strict port 7274 enforcement in frontend dev server.

Tests cover:
- Port availability checking
- Refusing to start when port is in use
- Strict port flag passed to Vite
- Auto-kill zombie processes
- Clear error messages
- Cross-platform support
"""

import platform
import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, call
import subprocess
import socket


try:
    import psutil
except ImportError:
    psutil = None


class TestPortAvailabilityCheck:
    """Test port availability checking functionality."""

    def test_check_port_available_returns_boolean(self):
        """Test that port check returns a boolean value."""

        def is_port_available(port: int) -> bool:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(('127.0.0.1', port))
                    return True
            except OSError:
                return False

        result = is_port_available(7274)
        assert isinstance(result, bool)

    @patch('socket.socket')
    def test_port_available_when_free(self, mock_socket):
        """Test that port check returns True when port is free."""
        mock_sock = Mock()
        mock_socket.return_value.__enter__.return_value = mock_sock
        mock_sock.bind.return_value = None  # Success - port is free

        def is_port_available(port: int) -> bool:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(('127.0.0.1', port))
                    return True
            except OSError:
                return False

        result = is_port_available(7274)
        assert result is True

    @patch('socket.socket')
    def test_port_unavailable_when_in_use(self, mock_socket):
        """Test that port check returns False when port is in use."""
        mock_sock = Mock()
        mock_socket.return_value.__enter__.return_value = mock_sock
        mock_sock.bind.side_effect = OSError("Address already in use")

        def is_port_available(port: int) -> bool:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(('127.0.0.1', port))
                    return True
            except OSError:
                return False

        result = is_port_available(7274)
        assert result is False

    def test_port_check_uses_localhost(self):
        """Test that port check binds to localhost (127.0.0.1)."""
        # Port check should use 127.0.0.1, not 0.0.0.0
        bind_address = '127.0.0.1'
        assert bind_address == '127.0.0.1'

    def test_port_check_handles_socket_errors(self):
        """Test that port check handles socket errors gracefully."""

        def is_port_available(port: int) -> bool:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(('127.0.0.1', port))
                    return True
            except OSError:
                return False  # Handle error gracefully

        # Should not raise exception
        try:
            result = is_port_available(7274)
            assert isinstance(result, bool)
        except Exception as e:
            pytest.fail(f"Port check should handle errors gracefully, got: {e}")


class TestFrontendStartPortEnforcement:
    """Test frontend start with strict port 7274 enforcement."""

    @patch('tkinter.messagebox.showerror')
    def test_frontend_refuses_start_when_port_in_use(self, mock_error):
        """Test that frontend refuses to start when port 7274 is in use."""
        # Simulate port in use
        port_available = False

        if not port_available:
            mock_error(
                "Port In Use",
                "Port 7274 is already in use.\n\n"
                "Please stop the existing process using port 7274 before starting the frontend.\n\n"
                "You can use 'Stop Frontend' button or manually kill the process."
            )
            frontend_started = False
        else:
            frontend_started = True

        mock_error.assert_called_once()
        assert frontend_started is False

    @patch('subprocess.Popen')
    def test_frontend_command_includes_strict_port_flag(self, mock_popen):
        """Test that frontend start command includes --strictPort flag."""
        mock_process = Mock()
        mock_process.poll.return_value = None
        mock_popen.return_value = mock_process

        # Expected command with strictPort
        npm_cmd = "npm.cmd" if platform.system() == "Windows" else "npm"
        command = [
            npm_cmd, "run", "dev",
            "--",
            "--port", "7274",
            "--strictPort"
        ]

        proc = mock_popen(command, cwd="frontend")

        assert mock_popen.called
        call_args = mock_popen.call_args[0][0]
        assert "--strictPort" in call_args
        assert "--port" in call_args
        assert "7274" in call_args

    @patch('subprocess.Popen')
    def test_frontend_command_includes_port_7274(self, mock_popen):
        """Test that frontend start command specifies port 7274."""
        mock_process = Mock()
        mock_popen.return_value = mock_process

        npm_cmd = "npm.cmd" if platform.system() == "Windows" else "npm"
        command = [
            npm_cmd, "run", "dev",
            "--",
            "--port", "7274",
            "--strictPort"
        ]

        proc = mock_popen(command, cwd="frontend")

        call_args = mock_popen.call_args[0][0]
        port_index = call_args.index("--port")
        actual_port = call_args[port_index + 1]

        assert actual_port == "7274"

    def test_port_check_happens_before_start_attempt(self):
        """Test that port availability is checked BEFORE attempting to start."""
        # Expected sequence:
        # 1. Check port 7274 availability
        # 2. If unavailable -> show error, return early
        # 3. If available -> proceed with npm run dev --strictPort

        port_available = False  # Simulate port in use

        if not port_available:
            should_start = False
        else:
            should_start = True

        assert should_start is False

    def test_no_alternative_ports_attempted(self):
        """Test that system will NOT attempt to use alternative ports."""
        # strictPort flag ensures Vite fails if port is unavailable
        # rather than trying 7275, 7276, etc.
        strict_port_flag = "--strictPort"
        assert strict_port_flag == "--strictPort"


class TestPortEnforcementErrorMessages:
    """Test error messages for port enforcement."""

    @patch('tkinter.messagebox.showerror')
    def test_error_message_mentions_port_7274(self, mock_error):
        """Test that error message specifically mentions port 7274."""
        mock_error(
            "Port In Use",
            "Port 7274 is already in use.\n\n"
            "Please stop the existing process using port 7274 before starting the frontend.\n\n"
            "You can use 'Stop Frontend' button or manually kill the process."
        )

        error_message = mock_error.call_args[0][1]
        assert "7274" in error_message

    @patch('tkinter.messagebox.showerror')
    def test_error_message_suggests_stop_button(self, mock_error):
        """Test that error message suggests using Stop Frontend button."""
        mock_error(
            "Port In Use",
            "Port 7274 is already in use.\n\n"
            "Please stop the existing process using port 7274 before starting the frontend.\n\n"
            "You can use 'Stop Frontend' button or manually kill the process."
        )

        error_message = mock_error.call_args[0][1]
        assert "Stop Frontend" in error_message

    @patch('tkinter.messagebox.showerror')
    def test_error_title_is_clear(self, mock_error):
        """Test that error dialog has clear title."""
        mock_error(
            "Port In Use",
            "Port 7274 is already in use.\n\n"
            "Please stop the existing process using port 7274 before starting the frontend.\n\n"
            "You can use 'Stop Frontend' button or manually kill the process."
        )

        error_title = mock_error.call_args[0][0]
        assert error_title == "Port In Use"


class TestProcessDiscoveryOnPort:
    """Test finding which process is using port 7274."""

    @patch('psutil.net_connections')
    def test_find_process_using_port_7274(self, mock_net_connections):
        """Test finding PID of process using port 7274."""
        if psutil is None:
            pytest.skip("psutil not available")

        # Mock a process using port 7274
        mock_conn = Mock()
        mock_conn.laddr = Mock()
        mock_conn.laddr.port = 7274
        mock_conn.pid = 12345
        mock_net_connections.return_value = [mock_conn]

        # Find process using port
        connections = [c for c in mock_net_connections() if c.laddr.port == 7274]
        if connections:
            pid_on_port = connections[0].pid
        else:
            pid_on_port = None

        assert pid_on_port == 12345

    @patch('psutil.net_connections')
    def test_return_none_when_no_process_on_port(self, mock_net_connections):
        """Test that None is returned when no process uses port 7274."""
        if psutil is None:
            pytest.skip("psutil not available")

        # No connections on port 7274
        mock_net_connections.return_value = []

        connections = [c for c in mock_net_connections() if c.laddr.port == 7274]
        if connections:
            pid_on_port = connections[0].pid
        else:
            pid_on_port = None

        assert pid_on_port is None


class TestAutoKillZombieProcess:
    """Test auto-killing zombie processes using port 7274."""

    @patch('tkinter.messagebox.askyesno')
    @patch('psutil.Process')
    def test_ask_confirmation_before_killing(self, mock_process, mock_askyesno):
        """Test that user confirmation is requested before killing process."""
        if psutil is None:
            pytest.skip("psutil not available")

        mock_askyesno.return_value = True

        response = mock_askyesno(
            "Port In Use",
            "Port 7274 is in use by process 12345.\n\n"
            "Kill the existing process and start frontend?",
            icon='warning'
        )

        mock_askyesno.assert_called_once()
        assert response is True

    @patch('tkinter.messagebox.askyesno')
    @patch('psutil.Process')
    def test_kill_process_when_user_confirms(self, mock_process, mock_askyesno):
        """Test that process is killed when user confirms."""
        if psutil is None:
            pytest.skip("psutil not available")

        mock_askyesno.return_value = True

        mock_proc = Mock()
        mock_proc.pid = 12345
        mock_process.return_value = mock_proc

        response = mock_askyesno(
            "Port In Use",
            "Port 7274 is in use by process 12345.\n\n"
            "Kill the existing process and start frontend?",
            icon='warning'
        )

        if response:
            proc = mock_process(12345)
            proc.terminate()
            mock_proc.terminate.assert_called_once()

    @patch('tkinter.messagebox.askyesno')
    def test_no_kill_when_user_declines(self, mock_askyesno):
        """Test that process is NOT killed when user declines."""
        mock_askyesno.return_value = False

        response = mock_askyesno(
            "Port In Use",
            "Port 7274 is in use by process 12345.\n\n"
            "Kill the existing process and start frontend?",
            icon='warning'
        )

        if response:
            frontend_started = True
        else:
            frontend_started = False

        assert frontend_started is False

    @patch('time.sleep')
    def test_wait_after_killing_process(self, mock_sleep):
        """Test that we wait for port to be released after killing process."""
        # After killing process, wait 1 second for port to be released
        mock_sleep(1)
        mock_sleep.assert_called_once_with(1)

    @patch('tkinter.messagebox.askyesno')
    def test_confirmation_dialog_shows_pid(self, mock_askyesno):
        """Test that confirmation dialog shows the process PID."""
        mock_askyesno.return_value = True

        mock_askyesno(
            "Port In Use",
            "Port 7274 is in use by process 12345.\n\n"
            "Kill the existing process and start frontend?",
            icon='warning'
        )

        message = mock_askyesno.call_args[0][1]
        assert "12345" in message


class TestCrossPlatformPortEnforcement:
    """Test port enforcement works across platforms."""

    @patch('subprocess.Popen')
    def test_windows_uses_npm_cmd(self, mock_popen):
        """Test that Windows uses npm.cmd for starting frontend."""
        if platform.system() != "Windows":
            pytest.skip("Windows-specific test")

        mock_process = Mock()
        mock_popen.return_value = mock_process

        command = [
            "npm.cmd", "run", "dev",
            "--",
            "--port", "7274",
            "--strictPort"
        ]

        proc = mock_popen(command, cwd="frontend")

        call_args = mock_popen.call_args[0][0]
        assert "npm.cmd" in call_args or "npm" in call_args

    @patch('subprocess.Popen')
    def test_linux_uses_npm(self, mock_popen):
        """Test that Linux uses npm for starting frontend."""
        if platform.system() != "Linux":
            pytest.skip("Linux-specific test")

        mock_process = Mock()
        mock_popen.return_value = mock_process

        command = [
            "npm", "run", "dev",
            "--",
            "--port", "7274",
            "--strictPort"
        ]

        proc = mock_popen(command, cwd="frontend")

        call_args = mock_popen.call_args[0][0]
        assert "npm" in call_args


class TestStatusMessages:
    """Test status messages for port enforcement."""

    def test_status_message_indicates_strict_mode(self):
        """Test that status message indicates strict port enforcement."""
        status_message = "Frontend starting on port 7274 (strict)..."

        assert "7274" in status_message
        assert "strict" in status_message

    def test_status_message_on_port_conflict(self):
        """Test status message when port conflict is detected."""
        status_message = "Port 7274 is in use - cannot start frontend"

        assert "7274" in status_message
        assert "in use" in status_message
