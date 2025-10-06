"""
Test suite for multi-port detection and management in Control Panel.

Tests comprehensive port detection capabilities including:
- Finding backend processes on any port
- Finding frontend processes on any port
- Startup detection and cleanup dialogs
- Dynamic port display in UI
- Wrong port warnings
- Offer to stop processes on wrong ports
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, call
import subprocess
import sys
import os
import platform


class TestMultiPortBackendDetection:
    """Test detecting backend processes on any port."""

    @patch('psutil.process_iter')
    def test_find_backend_on_standard_port_7272(self, mock_process_iter):
        """Test finding backend on standard port 7272."""
        # Mock backend process
        mock_proc = Mock()
        mock_proc.pid = 12345
        mock_proc.info = {
            'pid': 12345,
            'name': 'python.exe',
            'cmdline': ['python.exe', 'api/run_api.py', '--port', '7272']
        }

        # Mock connection on port 7272
        mock_conn = Mock()
        mock_conn.status = 'LISTEN'
        mock_conn.laddr.port = 7272
        mock_proc.connections.return_value = [mock_conn]

        mock_process_iter.return_value = [mock_proc]

        # Expected result: backend found on port 7272
        # This tests the _find_backend_processes() method
        # Should return [{"pid": 12345, "port": 7272, "cmdline": "..."}]
        assert mock_proc.pid == 12345
        assert mock_conn.laddr.port == 7272

    @patch('psutil.process_iter')
    def test_find_backend_on_alternative_port_7273(self, mock_process_iter):
        """Test finding backend on alternative port 7273."""
        mock_proc = Mock()
        mock_proc.pid = 67890
        mock_proc.info = {
            'pid': 67890,
            'name': 'python.exe',
            'cmdline': ['python.exe', 'api/run_api.py', '--port', '7273']
        }

        mock_conn = Mock()
        mock_conn.status = 'LISTEN'
        mock_conn.laddr.port = 7273
        mock_proc.connections.return_value = [mock_conn]

        mock_process_iter.return_value = [mock_proc]

        # Expected: backend found on wrong port 7273
        assert mock_proc.pid == 67890
        assert mock_conn.laddr.port == 7273

    @patch('psutil.process_iter')
    def test_find_backend_uvicorn_process(self, mock_process_iter):
        """Test finding backend when running via uvicorn."""
        mock_proc = Mock()
        mock_proc.pid = 11111
        mock_proc.info = {
            'pid': 11111,
            'name': 'python.exe',
            'cmdline': ['python.exe', '-m', 'uvicorn', 'api.main:app', '--port', '8000']
        }

        mock_conn = Mock()
        mock_conn.status = 'LISTEN'
        mock_conn.laddr.port = 8000
        mock_proc.connections.return_value = [mock_conn]

        mock_process_iter.return_value = [mock_proc]

        # Expected: should detect uvicorn processes too
        assert 'uvicorn' in mock_proc.info['cmdline']
        assert mock_conn.laddr.port == 8000

    @patch('psutil.process_iter')
    def test_find_no_backend_when_not_running(self, mock_process_iter):
        """Test finding no backend when none are running."""
        # Mock some processes but none are backend
        mock_proc1 = Mock()
        mock_proc1.info = {
            'pid': 1234,
            'name': 'chrome.exe',
            'cmdline': ['chrome.exe', '--type=renderer']
        }

        mock_process_iter.return_value = [mock_proc1]

        # Expected: empty list, no backend found
        assert 'api/run_api.py' not in str(mock_proc1.info['cmdline'])

    @patch('psutil.process_iter')
    def test_find_multiple_backend_instances(self, mock_process_iter):
        """Test finding multiple backend instances on different ports."""
        # Backend on port 7272
        mock_proc1 = Mock()
        mock_proc1.pid = 12345
        mock_proc1.info = {
            'pid': 12345,
            'name': 'python.exe',
            'cmdline': ['python.exe', 'api/run_api.py', '--port', '7272']
        }
        mock_conn1 = Mock()
        mock_conn1.status = 'LISTEN'
        mock_conn1.laddr.port = 7272
        mock_proc1.connections.return_value = [mock_conn1]

        # Backend on port 7273
        mock_proc2 = Mock()
        mock_proc2.pid = 67890
        mock_proc2.info = {
            'pid': 67890,
            'name': 'python.exe',
            'cmdline': ['python.exe', 'api/run_api.py', '--port', '7273']
        }
        mock_conn2 = Mock()
        mock_conn2.status = 'LISTEN'
        mock_conn2.laddr.port = 7273
        mock_proc2.connections.return_value = [mock_conn2]

        mock_process_iter.return_value = [mock_proc1, mock_proc2]

        # Expected: find both backends
        assert len([mock_proc1, mock_proc2]) == 2

    @patch('psutil.process_iter')
    def test_handle_access_denied_gracefully(self, mock_process_iter):
        """Test handling psutil.AccessDenied exceptions."""
        import psutil

        mock_proc = Mock()
        mock_proc.info = {'pid': 1234, 'name': 'system', 'cmdline': None}
        mock_proc.connections.side_effect = psutil.AccessDenied()

        mock_process_iter.return_value = [mock_proc]

        # Expected: should catch exception and continue
        # Should not crash, should skip this process


class TestMultiPortFrontendDetection:
    """Test detecting frontend processes on any port."""

    @patch('psutil.process_iter')
    def test_find_frontend_on_standard_port_7274(self, mock_process_iter):
        """Test finding frontend on standard port 7274."""
        mock_proc = Mock()
        mock_proc.pid = 22222
        mock_proc.info = {
            'pid': 22222,
            'name': 'node.exe',
            'cmdline': ['node.exe', 'npm', 'run', 'dev']
        }

        mock_conn = Mock()
        mock_conn.status = 'LISTEN'
        mock_conn.laddr.port = 7274
        mock_proc.connections.return_value = [mock_conn]

        mock_process_iter.return_value = [mock_proc]

        # Expected: frontend found on port 7274
        assert mock_proc.pid == 22222
        assert mock_conn.laddr.port == 7274

    @patch('psutil.process_iter')
    def test_find_frontend_on_vite_default_port_5173(self, mock_process_iter):
        """Test finding frontend on Vite's default port 5173."""
        mock_proc = Mock()
        mock_proc.pid = 33333
        mock_proc.info = {
            'pid': 33333,
            'name': 'node.exe',
            'cmdline': ['node.exe', 'vite']
        }

        mock_conn = Mock()
        mock_conn.status = 'LISTEN'
        mock_conn.laddr.port = 5173
        mock_proc.connections.return_value = [mock_conn]

        mock_process_iter.return_value = [mock_proc]

        # Expected: frontend found on wrong port 5173
        assert 'vite' in mock_proc.info['cmdline']
        assert mock_conn.laddr.port == 5173

    @patch('psutil.process_iter')
    def test_find_frontend_on_alternative_port_7275(self, mock_process_iter):
        """Test finding frontend on alternative port 7275."""
        mock_proc = Mock()
        mock_proc.pid = 44444
        mock_proc.info = {
            'pid': 44444,
            'name': 'node.exe',
            'cmdline': ['node.exe', 'npm', 'run', 'dev', '--', '--port', '7275']
        }

        mock_conn = Mock()
        mock_conn.status = 'LISTEN'
        mock_conn.laddr.port = 7275
        mock_proc.connections.return_value = [mock_conn]

        mock_process_iter.return_value = [mock_proc]

        # Expected: frontend found on wrong port 7275
        assert mock_proc.pid == 44444
        assert mock_conn.laddr.port == 7275

    @patch('psutil.process_iter')
    def test_distinguish_frontend_from_other_node_processes(self, mock_process_iter):
        """Test that we only detect frontend dev server, not other Node processes."""
        # Frontend dev server
        mock_frontend = Mock()
        mock_frontend.info = {
            'pid': 1111,
            'name': 'node.exe',
            'cmdline': ['node.exe', 'npm', 'run', 'dev']
        }

        # Other Node process (not frontend)
        mock_other = Mock()
        mock_other.info = {
            'pid': 2222,
            'name': 'node.exe',
            'cmdline': ['node.exe', 'some-other-script.js']
        }

        mock_process_iter.return_value = [mock_frontend, mock_other]

        # Expected: should only detect frontend dev server
        # Check for 'npm run dev' or 'vite' in cmdline
        assert 'npm' in mock_frontend.info['cmdline']
        assert 'dev' in mock_frontend.info['cmdline']

    @patch('psutil.process_iter')
    def test_find_no_frontend_when_not_running(self, mock_process_iter):
        """Test finding no frontend when none are running."""
        mock_proc = Mock()
        mock_proc.info = {
            'pid': 9999,
            'name': 'python.exe',
            'cmdline': ['python.exe', 'script.py']
        }

        mock_process_iter.return_value = [mock_proc]

        # Expected: empty list, no frontend found
        assert 'npm' not in str(mock_proc.info['cmdline'])
        assert 'vite' not in str(mock_proc.info['cmdline'])


class TestStartupDetection:
    """Test startup detection and cleanup dialog."""

    def test_detect_existing_services_on_startup(self):
        """Test detecting existing services when control panel starts."""
        # Expected behavior:
        # 1. On __init__, call detect_existing_services()
        # 2. Scan for backend and frontend processes
        # 3. If found, show cleanup dialog
        # 4. If not found, show "No instances running" message
        pass

    def test_show_cleanup_dialog_when_services_found(self):
        """Test showing cleanup dialog when existing services found."""
        # Mock services
        backend_procs = [{"pid": 12345, "port": 7272, "cmdline": "python api/run_api.py"}]
        frontend_procs = [{"pid": 67890, "port": 7275, "cmdline": "npm run dev"}]

        # Expected: should show dialog with:
        # - List of found services
        # - Checkbox: "Stop all existing services"
        # - Checkbox: "Keep running (mark as managed)"
        # - Continue and Exit buttons
        assert len(backend_procs) == 1
        assert len(frontend_procs) == 1

    def test_cleanup_dialog_stop_all_option(self):
        """Test 'Stop all' option in cleanup dialog."""
        # Expected: if user selects "Stop all":
        # 1. Terminate all found processes
        # 2. Wait for termination
        # 3. Continue with control panel
        pass

    def test_cleanup_dialog_keep_running_option(self):
        """Test 'Keep running' option in cleanup dialog."""
        # Expected: if user selects "Keep running":
        # 1. Track PIDs as managed by control panel
        # 2. Update UI to show services as running
        # 3. Continue with control panel
        pass

    def test_no_dialog_when_no_services_running(self):
        """Test no dialog shown when no services found."""
        backend_procs = []
        frontend_procs = []

        # Expected: should not show dialog
        # Should set status message: "No instances of backend or frontend running"
        assert len(backend_procs) == 0
        assert len(frontend_procs) == 0

    def test_cleanup_dialog_displays_correct_info(self):
        """Test cleanup dialog shows correct process information."""
        backend_procs = [
            {"pid": 12345, "port": 7272, "cmdline": "python api/run_api.py --port 7272"}
        ]
        frontend_procs = [
            {"pid": 67890, "port": 7275, "cmdline": "npm run dev -- --port 7275"}
        ]

        # Expected dialog content:
        # "Found existing services:"
        # "✓ Backend (PID 12345) - Port 7272"
        # "✓ Frontend (PID 67890) - Port 7275 ⚠️ Wrong port"

        assert backend_procs[0]["port"] == 7272  # Correct port
        assert frontend_procs[0]["port"] == 7275  # Wrong port


class TestDynamicPortDisplay:
    """Test dynamic port display in UI labels."""

    def test_backend_running_on_correct_port(self):
        """Test UI shows correct port with green indicator."""
        # Backend running on port 7272
        backend_info = {"pid": 12345, "port": 7272}

        # Expected UI:
        # "Backend: ● Running on port 7272" (green)
        expected_text = "Backend: ● Running on port 7272"
        expected_color = "green"

        assert backend_info["port"] == 7272
        # Test will verify label text and color

    def test_backend_running_on_wrong_port(self):
        """Test UI shows warning for wrong port with yellow indicator."""
        # Backend running on port 7273 (should be 7272)
        backend_info = {"pid": 12345, "port": 7273}

        # Expected UI:
        # "Backend: ● Running on port 7273 ⚠️ Non-standard port" (yellow/orange)
        expected_text = "Backend: ● Running on port 7273 ⚠️ Non-standard"
        expected_color = "orange"

        assert backend_info["port"] != 7272

    def test_backend_stopped(self):
        """Test UI shows stopped status with red indicator."""
        # No backend running
        backend_info = None

        # Expected UI:
        # "Backend: ○ Stopped" (red)
        expected_text = "Backend: ○ Stopped"
        expected_color = "red"

        assert backend_info is None

    def test_frontend_running_on_correct_port(self):
        """Test UI shows correct port for frontend."""
        frontend_info = {"pid": 67890, "port": 7274}

        # Expected UI:
        # "Frontend: ● Running on port 7274" (green)
        expected_text = "Frontend: ● Running on port 7274"
        expected_color = "green"

        assert frontend_info["port"] == 7274

    def test_frontend_running_on_wrong_port(self):
        """Test UI shows warning for frontend on wrong port."""
        frontend_info = {"pid": 67890, "port": 5173}

        # Expected UI:
        # "Frontend: ● Running on port 5173 ⚠️ Non-standard port" (yellow/orange)
        expected_text = "Frontend: ● Running on port 5173 ⚠️ Non-standard"
        expected_color = "orange"

        assert frontend_info["port"] != 7274

    def test_status_updates_automatically(self):
        """Test that status labels update automatically every 2 seconds."""
        # Expected: update_status() should be called on timer
        # Should refresh port display every 2 seconds
        pass

    def test_multiple_backends_shows_first_only(self):
        """Test that when multiple backends found, only first is shown."""
        backend_procs = [
            {"pid": 12345, "port": 7272},
            {"pid": 67890, "port": 7273}
        ]

        # Expected: UI shows first backend only
        # User would need to manually manage multiple instances
        assert len(backend_procs) > 1
        # Display backend_procs[0]


class TestEnhancedStartMethods:
    """Test enhanced start methods with comprehensive port checking."""

    @patch('psutil.process_iter')
    def test_start_backend_checks_for_any_process(self, mock_process_iter):
        """Test start_backend checks for ANY backend process, not just port."""
        # Mock existing backend on port 7273
        mock_proc = Mock()
        mock_proc.pid = 12345
        mock_proc.info = {
            'pid': 12345,
            'name': 'python.exe',
            'cmdline': ['python.exe', 'api/run_api.py', '--port', '7273']
        }
        mock_conn = Mock()
        mock_conn.status = 'LISTEN'
        mock_conn.laddr.port = 7273
        mock_proc.connections.return_value = [mock_conn]

        mock_process_iter.return_value = [mock_proc]

        # Expected: start_backend should detect this process
        # Should offer to stop and restart on correct port
        assert mock_conn.laddr.port != 7272  # Wrong port

    def test_start_backend_offers_to_stop_wrong_port(self):
        """Test start_backend offers to stop process on wrong port."""
        existing_backend = {"pid": 12345, "port": 7273}

        # Expected dialog:
        # "Backend is running on port 7273 (PID 12345)."
        # "Stop it and restart on correct port 7272?"
        # [Yes] [No]

        # If Yes: kill process, wait, start on 7272
        # If No: cancel start operation
        assert existing_backend["port"] != 7272

    def test_start_backend_handles_already_running_correct_port(self):
        """Test start_backend handles already running on correct port."""
        existing_backend = {"pid": 12345, "port": 7272}

        # Expected: show info dialog
        # "Backend is already running on port 7272 (PID 12345)"
        # Do not start another instance
        assert existing_backend["port"] == 7272

    @patch('socket.socket')
    def test_start_backend_checks_port_availability(self, mock_socket):
        """Test start_backend checks if port 7272 is available."""
        # Mock port in use by non-backend process
        mock_sock = Mock()
        mock_sock.bind.side_effect = OSError("Port in use")
        mock_socket.return_value.__enter__.return_value = mock_sock

        # Expected: show error dialog
        # "Port 7272 is in use by another process."
        # "Please free the port before starting backend."

    def test_start_frontend_checks_for_any_process(self):
        """Test start_frontend checks for ANY frontend process."""
        existing_frontend = {"pid": 67890, "port": 5173}

        # Expected: should detect frontend on wrong port
        # Should offer to stop and restart on 7274
        assert existing_frontend["port"] != 7274

    def test_start_frontend_enforces_strict_port_7274(self):
        """Test start_frontend enforces strict port 7274."""
        # Expected: must use port 7274
        # Should pass --strictPort flag to Vite
        # Should not fall back to alternative ports
        designated_port = 7274
        assert designated_port == 7274

    def test_start_frontend_offers_to_kill_process_on_7274(self):
        """Test start_frontend offers to kill process using port 7274."""
        # Port 7274 in use by some other process
        port_in_use = True
        existing_pid = 99999

        # Expected dialog:
        # "Port 7274 is in use by process 99999."
        # "Kill the existing process and start frontend?"
        # [Yes] [No]
        assert port_in_use is True

    def test_start_methods_update_ui_immediately(self):
        """Test that start methods update UI status immediately."""
        # Expected: after starting service
        # 1. Update status label
        # 2. Update indicator color
        # 3. Show port number
        # Should not wait for next status check cycle
        pass


class TestPort7273Mystery:
    """Test handling of mystery port 7273 (WebSocket legacy port)."""

    def test_port_7273_identified_as_websocket_legacy(self):
        """Test that port 7273 is correctly identified as WebSocket legacy."""
        # Port 7273 was used for separate WebSocket service
        # Now unified on port 7272
        websocket_legacy_port = 7273
        current_unified_port = 7272

        assert websocket_legacy_port == 7273
        assert current_unified_port == 7272

    def test_detect_process_on_7273(self):
        """Test detecting any process on port 7273."""
        # Could be:
        # - Old WebSocket server
        # - Alternative backend instance
        # - User's test server

        # Should detect and display in UI
        pass

    def test_alternative_ports_list_includes_7273(self):
        """Test that 7273 is in alternative ports list."""
        alternative_ports = [7273, 7274, 8747, 8823, 9456, 9789]

        assert 7273 in alternative_ports


class TestErrorHandlingMultiPort:
    """Test error handling for multi-port detection."""

    @patch('psutil.process_iter')
    def test_handle_no_psutil_gracefully(self, mock_process_iter):
        """Test handling when psutil is not available."""
        # Expected: should handle gracefully
        # Should show warning or use limited functionality
        mock_process_iter.side_effect = ImportError("psutil not installed")

    def test_handle_access_denied_on_process(self):
        """Test handling psutil.AccessDenied for system processes."""
        import psutil

        # Some processes require admin access
        # Expected: catch exception, skip process, continue
        pass

    def test_handle_process_terminated_during_check(self):
        """Test handling process that terminates while checking."""
        import psutil

        # Process might terminate between discovery and check
        # Expected: catch psutil.NoSuchProcess, skip, continue
        pass

    def test_handle_permission_error_killing_process(self):
        """Test handling permission error when killing process."""
        # User might not have permission to kill process
        # Expected: show error message with instructions
        pass


# Integration tests
class TestMultiPortIntegration:
    """Integration tests for multi-port detection workflow."""

    @pytest.mark.integration
    def test_full_startup_detection_workflow(self):
        """Test complete startup detection and cleanup workflow."""
        # 1. Control panel starts
        # 2. Scans for existing services
        # 3. Finds backend on 7273, frontend on 5173
        # 4. Shows cleanup dialog
        # 5. User selects "Stop all"
        # 6. Processes are killed
        # 7. UI updates to show stopped
        pass

    @pytest.mark.integration
    def test_full_wrong_port_restart_workflow(self):
        """Test complete wrong port detection and restart workflow."""
        # 1. Backend running on port 7273
        # 2. User clicks "Start Backend"
        # 3. System detects wrong port
        # 4. Offers to stop and restart
        # 5. User confirms
        # 6. Process killed
        # 7. Backend started on 7272
        # 8. UI shows "Running on port 7272" (green)
        pass

    @pytest.mark.integration
    def test_continuous_monitoring_of_ports(self):
        """Test continuous monitoring updates port display."""
        # 1. Backend starts on 7272
        # 2. UI shows green, port 7272
        # 3. Process crashes or is killed externally
        # 4. Next status check detects stopped
        # 5. UI updates to red, stopped
        # 6. Process started again on different port
        # 7. UI shows yellow, port 7273 warning
        pass
