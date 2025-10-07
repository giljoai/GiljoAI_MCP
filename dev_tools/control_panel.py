#!/usr/bin/env python3
"""
GiljoAI MCP Developer Control Panel

A comprehensive GUI tool for managing GiljoAI MCP development environment.

Features:
- Service management (start/stop/restart backend and frontend)
- Database operations (connection check, database check, deletion)
- Development reset (simulate fresh download)
- Cache management (Python, Frontend, All)
- Frontend hard reload
- Cross-platform support (Windows, Linux, macOS)
- Admin privilege detection and handling

Usage:
    python dev_tools/control_panel.py
"""

import ctypes
import os
import platform
import subprocess
import sys
import time
import webbrowser
from pathlib import Path
from tkinter import BooleanVar, Tk, messagebox, ttk
from typing import Any, Optional


try:
    import psutil
except ImportError:
    psutil = None
    print("Warning: psutil not installed. Service status checking will be limited.")

try:
    import psycopg2
except ImportError:
    psycopg2 = None
    print("Warning: psycopg2 not installed. Database features will be disabled.")

try:
    import yaml
except ImportError:
    yaml = None
    print("Warning: pyyaml not installed. Config loading will be limited.")


class GiljoDevControlPanel:
    """
    Developer control panel for GiljoAI MCP.

    Provides GUI controls for common development tasks including service
    management, database operations, cache clearing, and environment reset.
    """

    def __init__(self):
        """Initialize the control panel."""
        self.root = Tk()
        self.root.title("GiljoAI MCP - Developer Control Panel")
        self.root.geometry("700x800")
        self.root.resizable(False, False)

        # Project root detection (dynamic, no hardcoded paths)
        self.project_root = Path.cwd()
        if not (self.project_root / "config.yaml").exists():
            # Try parent directory
            self.project_root = Path.cwd().parent
            if not (self.project_root / "config.yaml").exists():
                self.project_root = Path.cwd()

        # Process tracking
        self.backend_process: Optional[subprocess.Popen] = None
        self.frontend_process: Optional[subprocess.Popen] = None

        # Status variables
        self.backend_status = BooleanVar(value=False)
        self.frontend_status = BooleanVar(value=False)
        self.db_connection_status = BooleanVar(value=False)
        self.db_exists_status = BooleanVar(value=False)

        # Configuration
        self.config: Optional[dict[str, Any]] = None
        self.load_config()

        # Check admin privileges
        self.is_admin = self.check_admin()
        if not self.is_admin:
            messagebox.showwarning(
                "Admin Privileges Required",
                "Some features may not work without administrator privileges.\n\n"
                "Windows: Run as Administrator\n"
                "Linux/macOS: Run with sudo",
            )

        # Build UI
        self.build_ui()

        # Initial status check
        self.update_status()

    def check_admin(self) -> bool:
        """
        Check if running with administrator/root privileges.

        Returns:
            True if running as admin/root, False otherwise
        """
        try:
            if platform.system() == "Windows":
                # Windows: Check if admin using ctypes
                return ctypes.windll.shell32.IsUserAnAdmin() != 0
            # Linux/macOS: Check if root (UID 0)
            return os.geteuid() == 0
        except (AttributeError, OSError):
            # If check fails, assume not admin
            return False

    def load_config(self):
        """Load configuration from config.yaml."""
        if yaml is None:
            return

        config_path = self.project_root / "config.yaml"
        if config_path.exists():
            try:
                with open(config_path) as f:
                    self.config = yaml.safe_load(f)
            except Exception as e:
                print(f"Warning: Could not load config.yaml: {e}")
                self.config = None

    def build_ui(self):
        """Build the complete UI."""
        # Main container with padding
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky="nsew")

        # Title
        title_label = ttk.Label(
            main_frame,
            text="GiljoAI MCP Developer Control Panel",
            font=("Arial", 16, "bold"),
        )
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))

        # Build sections
        row = 1
        row = self.build_service_section(main_frame, row)
        row = self.build_database_section(main_frame, row)
        row = self.build_reset_section(main_frame, row)
        row = self.build_cache_section(main_frame, row)
        row = self.build_frontend_section(main_frame, row)

        # Status bar at bottom
        self.status_label = ttk.Label(main_frame, text="Ready", relief="sunken", anchor="w")
        self.status_label.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(20, 0))

    def build_service_section(self, parent: ttk.Frame, row: int) -> int:
        """Build service management section."""
        # Section frame
        section = ttk.LabelFrame(parent, text="Service Management", padding="10")
        section.grid(row=row, column=0, columnspan=2, sticky="ew", pady=5)

        # Backend service
        ttk.Label(section, text="Backend API:").grid(row=0, column=0, sticky="w")
        self.backend_indicator = ttk.Label(section, text="●", foreground="red")
        self.backend_indicator.grid(row=0, column=1)
        self.backend_status_label = ttk.Label(section, text="Stopped")
        self.backend_status_label.grid(row=0, column=2, sticky="w", padx=(5, 20))
        ttk.Button(section, text="Start", command=self.start_backend, width=10).grid(row=0, column=3, padx=2)
        ttk.Button(section, text="Stop", command=self.stop_backend, width=10).grid(row=0, column=4, padx=2)
        ttk.Button(section, text="Restart", command=self.restart_backend, width=10).grid(row=0, column=5, padx=2)
        ttk.Button(section, text="Check Port", command=self.check_backend_port, width=10).grid(row=0, column=6, padx=2)

        # Frontend service
        ttk.Label(section, text="Frontend Dev:").grid(row=1, column=0, sticky="w", pady=(10, 0))
        self.frontend_indicator = ttk.Label(section, text="●", foreground="red")
        self.frontend_indicator.grid(row=1, column=1, pady=(10, 0))
        self.frontend_status_label = ttk.Label(section, text="Stopped")
        self.frontend_status_label.grid(row=1, column=2, sticky="w", padx=(5, 20), pady=(10, 0))
        ttk.Button(section, text="Start", command=self.start_frontend, width=10).grid(
            row=1, column=3, padx=2, pady=(10, 0)
        )
        ttk.Button(section, text="Stop", command=self.stop_frontend, width=10).grid(
            row=1, column=4, padx=2, pady=(10, 0)
        )
        ttk.Button(section, text="Restart", command=self.restart_frontend, width=10).grid(
            row=1, column=5, padx=2, pady=(10, 0)
        )
        ttk.Button(section, text="Check Port", command=self.check_frontend_port, width=10).grid(
            row=1, column=6, padx=2, pady=(10, 0)
        )

        # Control all services
        ttk.Separator(section, orient="horizontal").grid(row=2, column=0, columnspan=7, sticky="ew", pady=10)
        ttk.Button(section, text="Start All Services", command=self.start_all_services, width=20).grid(
            row=3, column=0, columnspan=3, pady=5
        )
        ttk.Button(section, text="Stop All Services", command=self.stop_all_services, width=20).grid(
            row=3, column=3, columnspan=3, pady=5
        )

        return row + 1

    def build_database_section(self, parent: ttk.Frame, row: int) -> int:
        """Build database management section."""
        section = ttk.LabelFrame(parent, text="Database Management", padding="10")
        section.grid(row=row, column=0, columnspan=2, sticky="ew", pady=5)

        # Connection status
        ttk.Label(section, text="Connection:").grid(row=0, column=0, sticky="w")
        self.db_conn_indicator = ttk.Label(section, text="●", foreground="red")
        self.db_conn_indicator.grid(row=0, column=1)
        self.db_conn_label = ttk.Label(section, text="Not checked")
        self.db_conn_label.grid(row=0, column=2, sticky="w", padx=(5, 0))

        # Database exists status
        ttk.Label(section, text="giljo_mcp DB:").grid(row=1, column=0, sticky="w", pady=(10, 0))
        self.db_exists_indicator = ttk.Label(section, text="●", foreground="red")
        self.db_exists_indicator.grid(row=1, column=1, pady=(10, 0))
        self.db_exists_label = ttk.Label(section, text="Not checked")
        self.db_exists_label.grid(row=1, column=2, sticky="w", padx=(5, 0), pady=(10, 0))

        # Action buttons
        ttk.Separator(section, orient="horizontal").grid(row=2, column=0, columnspan=3, sticky="ew", pady=10)
        ttk.Button(section, text="Check Connection", command=self.check_db_connection, width=20).grid(
            row=3, column=0, padx=5, pady=2
        )
        ttk.Button(section, text="Check Database", command=self.check_db_exists, width=20).grid(
            row=3, column=1, padx=5, pady=2
        )
        ttk.Button(section, text="Delete Database", command=self.delete_database, width=20).grid(
            row=3, column=2, padx=5, pady=2
        )

        return row + 1

    def build_reset_section(self, parent: ttk.Frame, row: int) -> int:
        """Build development reset section."""
        section = ttk.LabelFrame(parent, text="Development Reset", padding="10")
        section.grid(row=row, column=0, columnspan=2, sticky="ew", pady=5)

        ttk.Label(
            section,
            text="Reset to fresh state (removes venv, configs, etc.)",
            wraplength=600,
        ).grid(row=0, column=0, sticky="w", pady=(0, 10))

        ttk.Button(
            section,
            text="Reset to Fresh State",
            command=self.reset_to_fresh,
            width=30,
        ).grid(row=1, column=0, pady=5)

        return row + 1

    def build_cache_section(self, parent: ttk.Frame, row: int) -> int:
        """Build cache management section."""
        section = ttk.LabelFrame(parent, text="Cache Management", padding="10")
        section.grid(row=row, column=0, columnspan=2, sticky="ew", pady=5)

        ttk.Button(section, text="Clear Python Cache", command=self.clear_python_cache, width=20).grid(
            row=0, column=0, padx=5, pady=5
        )
        ttk.Button(section, text="Clear Frontend Cache", command=self.clear_frontend_cache, width=20).grid(
            row=0, column=1, padx=5, pady=5
        )
        ttk.Button(section, text="Clear All Caches", command=self.clear_all_caches, width=20).grid(
            row=0, column=2, padx=5, pady=5
        )

        return row + 1

    def build_frontend_section(self, parent: ttk.Frame, row: int) -> int:
        """Build frontend tools section."""
        section = ttk.LabelFrame(parent, text="Frontend Tools", padding="10")
        section.grid(row=row, column=0, columnspan=2, sticky="ew", pady=5)

        ttk.Label(
            section,
            text="Hard reload: Stop dev server, clear cache, restart, open browser",
            wraplength=600,
        ).grid(row=0, column=0, sticky="w", pady=(0, 10))

        ttk.Button(
            section,
            text="Hard Reload Frontend",
            command=self.hard_reload_frontend,
            width=30,
        ).grid(row=1, column=0, pady=5)

        return row + 1

    def update_status_message(self, message: str):
        """Update status bar message."""
        self.status_label.config(text=message)
        self.root.update_idletasks()

    def update_status(self):
        """Update all status indicators with port information."""
        # Check backend status
        if self.backend_process and self.backend_process.poll() is None:
            self.backend_indicator.config(foreground="green")
            self.backend_status_label.config(text="Running (Port 7272)")
            self.backend_status.set(True)
        else:
            self.backend_indicator.config(foreground="red")
            self.backend_status_label.config(text="Stopped")
            self.backend_status.set(False)

        # Check frontend status
        if self.frontend_process and self.frontend_process.poll() is None:
            self.frontend_indicator.config(foreground="green")
            self.frontend_status_label.config(text="Running (Port 7274)")
            self.frontend_status.set(True)
        else:
            self.frontend_indicator.config(foreground="red")
            self.frontend_status_label.config(text="Stopped")
            self.frontend_status.set(False)

        # Schedule next update
        self.root.after(2000, self.update_status)

    def _launch_in_terminal(
        self, command: list[str], title: str = "", cwd: Optional[Path] = None
    ) -> Optional[subprocess.Popen]:
        """
        Launch command in a new terminal window.

        Detects operating system and uses the appropriate method to launch
        a new terminal window with the given command. Terminal windows display
        verbose output for debugging.

        Args:
            command: Command and arguments to execute
            title: Terminal window title for identification
            cwd: Working directory for command (defaults to project root)

        Returns:
            Process object for tracking (None on macOS - PID tracking limited)

        Raises:
            FileNotFoundError: If no suitable terminal emulator is found (Linux)
            OSError: If terminal launch fails
        """
        import shutil

        system = platform.system()
        work_dir = str(cwd if cwd else self.project_root)

        if system == "Windows":
            # Windows: Use CREATE_NEW_CONSOLE flag
            return subprocess.Popen(
                command, cwd=work_dir, creationflags=subprocess.CREATE_NEW_CONSOLE
            )

        if system == "Linux":
            # Linux: Try terminal emulators in order of preference
            terminal_emulators = [
                {
                    "name": "gnome-terminal",
                    "cmd": ["gnome-terminal", "--title", title, "--", *command],
                },
                {"name": "konsole", "cmd": ["konsole", "--title", title, "-e", *command]},
                {"name": "xterm", "cmd": ["xterm", "-title", title, "-e", *command]},
            ]

            for emulator in terminal_emulators:
                # Check if emulator is available
                if shutil.which(emulator["name"]):
                    try:
                        return subprocess.Popen(emulator["cmd"], cwd=work_dir)
                    except FileNotFoundError:
                        continue

            # No terminal emulator found
            raise FileNotFoundError(
                "No suitable terminal emulator found. Install gnome-terminal, konsole, or xterm."
            )

        if system == "Darwin":
            # macOS: Use osascript with Terminal.app
            cmd_str = " ".join(command)
            script = f'tell application "Terminal" to do script "cd {work_dir} && {cmd_str}"'

            subprocess.Popen(["osascript", "-e", script])
            # Note: Cannot easily get PID on macOS with this approach
            return None

        raise OSError(f"Unsupported operating system: {system}")

    def _is_port_available(self, port: int) -> bool:
        """
        Check if a port is available for binding.

        Args:
            port: Port number to check

        Returns:
            True if port is available, False if already in use
        """
        import socket

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('127.0.0.1', port))
                return True
        except OSError:
            return False

    def _find_process_on_port(self, port: int) -> Optional[int]:
        """
        Find the PID of the process using the given port.

        Args:
            port: Port number to check

        Returns:
            PID of process using the port, or None if port is free or psutil unavailable
        """
        if psutil is None:
            return None

        try:
            for conn in psutil.net_connections(kind='inet'):
                if conn.laddr.port == port:
                    return conn.pid
        except (psutil.AccessDenied, AttributeError):
            # May need admin privileges or psutil not fully functional
            return None

        return None

    def _kill_process(self, pid: int):
        """
        Terminate a process by PID.

        Args:
            pid: Process ID to terminate
        """
        if psutil is None:
            return

        try:
            proc = psutil.Process(pid)
            proc.terminate()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    def _nuclear_kill_port(self, port: int):
        """
        Nuclear option: Kill ALL processes using a specific port.
        Uses system commands for maximum aggression.

        Args:
            port: Port number to clear
        """
        system = platform.system()

        try:
            if system == "Windows":
                # Find PIDs using the port
                result = subprocess.run(
                    ["netstat", "-ano"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )

                pids_to_kill = set()
                for line in result.stdout.splitlines():
                    if f":{port}" in line and "LISTENING" in line:
                        parts = line.split()
                        if parts:
                            pid = parts[-1]
                            if pid.isdigit() and pid != "0":
                                pids_to_kill.add(pid)

                # Force kill each PID
                for pid in pids_to_kill:
                    try:
                        subprocess.run(
                            ["taskkill", "/F", "/PID", pid],
                            capture_output=True,
                            timeout=5
                        )
                    except Exception:
                        pass

            else:  # Linux/macOS
                # Use lsof to find and kill processes
                try:
                    result = subprocess.run(
                        ["lsof", "-ti", f":{port}"],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )

                    pids = result.stdout.strip().split()
                    for pid in pids:
                        if pid:
                            try:
                                subprocess.run(
                                    ["kill", "-9", pid],
                                    capture_output=True,
                                    timeout=5
                                )
                            except Exception:
                                pass
                except FileNotFoundError:
                    # lsof not available, try fuser
                    try:
                        subprocess.run(
                            ["fuser", "-k", f"{port}/tcp"],
                            capture_output=True,
                            timeout=5
                        )
                    except FileNotFoundError:
                        pass

        except Exception as e:
            print(f"Warning: Nuclear kill port {port} failed: {e}")

    # Service Management Methods

    def check_backend_port(self):
        """Check what's running on port 7272."""
        port = 7272

        if self._is_port_available(port):
            messagebox.showinfo(
                "Port Available",
                f"Port {port} is available\n\nNo process is using this port."
            )
        else:
            pid = self._find_process_on_port(port)
            if pid:
                messagebox.showwarning(
                    "Port In Use",
                    f"Port {port} is IN USE\n\nProcess ID: {pid}\n\n"
                    "This process must be stopped before starting the backend."
                )
            else:
                messagebox.showwarning(
                    "Port In Use",
                    f"Port {port} is IN USE\n\n"
                    "Could not determine which process is using it.\n"
                    "You may need administrator privileges."
                )

    def check_frontend_port(self):
        """Check what's running on port 7274."""
        port = 7274

        if self._is_port_available(port):
            messagebox.showinfo(
                "Port Available",
                f"Port {port} is available\n\nNo process is using this port."
            )
        else:
            pid = self._find_process_on_port(port)
            if pid:
                messagebox.showwarning(
                    "Port In Use",
                    f"Port {port} is IN USE\n\nProcess ID: {pid}\n\n"
                    "This process must be stopped before starting the frontend."
                )
            else:
                messagebox.showwarning(
                    "Port In Use",
                    f"Port {port} is IN USE\n\n"
                    "Could not determine which process is using it.\n"
                    "You may need administrator privileges."
                )

    def start_backend(self):
        """Start the backend API service in a new terminal window."""
        if self.backend_process and self.backend_process.poll() is None:
            messagebox.showinfo("Already Running", "Backend service is already running.")
            return

        self.update_status_message("Starting backend service in terminal window...")

        try:
            # Get API port from config
            api_port = 7272
            if self.config:
                api_port = self.config.get("services", {}).get("api", {}).get("port", 7272)

            # Check if api/run_api.py exists
            api_script = self.project_root / "api" / "run_api.py"
            if not api_script.exists():
                raise FileNotFoundError(f"API script not found: {api_script}")

            # Build command
            command = [sys.executable, str(api_script), "--port", str(api_port)]

            # Launch in terminal window with verbose output
            self.backend_process = self._launch_in_terminal(
                command=command, title="GiljoAI Backend API", cwd=self.project_root
            )

            time.sleep(2)  # Wait for startup

            # Check if process started (None on macOS is acceptable)
            if self.backend_process is None or self.backend_process.poll() is None:
                self.update_status_message(f"Backend started in terminal on port {api_port}")
                messagebox.showinfo(
                    "Success",
                    f"Backend service started in terminal window on port {api_port}\n\n"
                    "Check the terminal window for verbose output.",
                )
            else:
                self.update_status_message("Backend failed to start")
                messagebox.showerror(
                    "Error",
                    "Backend service failed to start\n\nCheck the terminal window for error details.",
                )

        except Exception as e:
            self.update_status_message(f"Error starting backend: {e}")
            messagebox.showerror("Error", f"Failed to start backend:\n{e}")

    def stop_backend(self):
        """Stop the backend API service - NUCLEAR OPTION (kills all processes on port 7272)."""
        self.update_status_message("Stopping backend service (nuclear mode)...")

        try:
            # First try to stop tracked process if exists
            if self.backend_process and self.backend_process.poll() is None:
                try:
                    self.backend_process.terminate()
                    time.sleep(1)
                    if self.backend_process.poll() is None:
                        self.backend_process.kill()
                except Exception:
                    pass
                finally:
                    self.backend_process = None

            # NUCLEAR: Kill everything on port 7272
            self._nuclear_kill_port(7272)

            # Also try port 7273 (sometimes used)
            self._nuclear_kill_port(7273)

            time.sleep(1)
            self.update_status_message("Backend stopped (nuclear)")
            messagebox.showinfo("Success", "Backend service stopped (nuclear mode - killed all processes on ports 7272-7273)")

        except Exception as e:
            self.update_status_message(f"Error stopping backend: {e}")
            messagebox.showerror("Error", f"Failed to stop backend:\n{e}")

    def restart_backend(self):
        """Restart the backend service."""
        self.stop_backend()
        time.sleep(1)
        self.start_backend()

    def start_frontend(self):
        """Start the frontend dev server in a new terminal window on port 7274 (strict)."""
        if self.frontend_process and self.frontend_process.poll() is None:
            messagebox.showinfo("Already Running", "Frontend service is already running.")
            return

        self.update_status_message("Checking port 7274 availability...")

        try:
            # Strict port enforcement - MUST use port 7274
            frontend_port = 7274

            # Check if port 7274 is available
            if not self._is_port_available(frontend_port):
                # Port is in use - check if we can find the process
                existing_pid = self._find_process_on_port(frontend_port)

                if existing_pid:
                    # Found process using the port - offer to kill it
                    response = messagebox.askyesno(
                        "Port In Use",
                        f"Port {frontend_port} is in use by process {existing_pid}.\n\n"
                        "Kill the existing process and start frontend?",
                        icon='warning'
                    )

                    if response:
                        # User confirmed - kill process and wait for port release
                        self._kill_process(existing_pid)
                        time.sleep(1)  # Wait for port to be released

                        # Re-check port availability
                        if not self._is_port_available(frontend_port):
                            messagebox.showerror(
                                "Port Still In Use",
                                f"Port {frontend_port} is still in use after killing process.\n\n"
                                "Please manually stop the process before starting frontend."
                            )
                            self.update_status_message("Port 7274 still in use - cannot start frontend")
                            return
                    else:
                        # User declined to kill process
                        self.update_status_message("Frontend start cancelled by user")
                        return
                else:
                    # Port in use but couldn't find process
                    messagebox.showerror(
                        "Port In Use",
                        f"Port {frontend_port} is already in use.\n\n"
                        "Please stop the existing process using port 7274 before starting the frontend.\n\n"
                        "You can use 'Stop Frontend' button or manually kill the process."
                    )
                    self.update_status_message(f"Port {frontend_port} is in use - cannot start frontend")
                    return

            # Port is available - proceed with start
            self.update_status_message("Starting frontend on port 7274 (strict mode)...")

            frontend_dir = self.project_root / "frontend"
            if not frontend_dir.exists():
                raise FileNotFoundError(f"Frontend directory not found: {frontend_dir}")

            # Build command with strict port enforcement
            npm_cmd = "npm.cmd" if platform.system() == "Windows" else "npm"
            command = [
                npm_cmd, "run", "dev",
                "--",
                "--port", str(frontend_port),
                "--strictPort"  # Fail if port unavailable (no fallback)
            ]

            # Launch in terminal window with verbose output
            self.frontend_process = self._launch_in_terminal(
                command=command,
                title=f"GiljoAI Frontend Dev Server (Port {frontend_port})",
                cwd=frontend_dir
            )

            time.sleep(2)  # Wait for startup

            # Check if process started (None on macOS is acceptable)
            if self.frontend_process is None or self.frontend_process.poll() is None:
                self.update_status_message(f"Frontend started on port {frontend_port} (strict)")
                messagebox.showinfo(
                    "Frontend Starting",
                    f"Frontend dev server starting in terminal window.\n"
                    f"Port: {frontend_port} (strict - will not use alternative ports)\n\n"
                    "Check the terminal window for verbose output."
                )
            else:
                self.update_status_message("Frontend failed to start")
                messagebox.showerror(
                    "Error",
                    "Frontend service failed to start\n\nCheck the terminal window for error details.",
                )

        except Exception as e:
            self.update_status_message(f"Error starting frontend: {e}")
            messagebox.showerror("Error", f"Failed to start frontend:\n{e}")

    def stop_frontend(self):
        """Stop the frontend dev server - NUCLEAR OPTION (kills all processes on port 7274)."""
        self.update_status_message("Stopping frontend service (nuclear mode)...")

        try:
            # First try to stop tracked process if exists
            if self.frontend_process and self.frontend_process.poll() is None:
                try:
                    self.frontend_process.terminate()
                    time.sleep(1)
                    if self.frontend_process.poll() is None:
                        self.frontend_process.kill()
                except Exception:
                    pass
                finally:
                    self.frontend_process = None

            # NUCLEAR: Kill everything on port 7274
            self._nuclear_kill_port(7274)

            time.sleep(1)
            self.update_status_message("Frontend stopped (nuclear)")
            messagebox.showinfo("Success", "Frontend service stopped (nuclear mode - killed all processes on port 7274)")

        except Exception as e:
            self.update_status_message(f"Error stopping frontend: {e}")
            messagebox.showerror("Error", f"Failed to stop frontend:\n{e}")

    def restart_frontend(self):
        """Restart the frontend service."""
        self.stop_frontend()
        time.sleep(1)
        self.start_frontend()

    def start_all_services(self):
        """Start all services."""
        self.start_backend()
        time.sleep(2)
        self.start_frontend()

    def stop_all_services(self):
        """Stop all services - NUCLEAR OPTION (kills all processes on ports 7272, 7273, 7274)."""
        self.update_status_message("Stopping all services (nuclear mode)...")

        try:
            # Stop tracked processes first
            if self.backend_process and self.backend_process.poll() is None:
                try:
                    self.backend_process.terminate()
                    time.sleep(0.5)
                    if self.backend_process.poll() is None:
                        self.backend_process.kill()
                except Exception:
                    pass
                finally:
                    self.backend_process = None

            if self.frontend_process and self.frontend_process.poll() is None:
                try:
                    self.frontend_process.terminate()
                    time.sleep(0.5)
                    if self.frontend_process.poll() is None:
                        self.frontend_process.kill()
                except Exception:
                    pass
                finally:
                    self.frontend_process = None

            # NUCLEAR: Kill everything on all GiljoAI ports
            self._nuclear_kill_port(7272)  # Backend API
            self._nuclear_kill_port(7273)  # Alternative backend
            self._nuclear_kill_port(7274)  # Frontend

            time.sleep(1)
            self.update_status_message("All services stopped (nuclear)")
            messagebox.showinfo(
                "Success",
                "All services stopped (nuclear mode)\n\n"
                "Killed all processes on ports:\n"
                "- 7272 (Backend API)\n"
                "- 7273 (Alternative Backend)\n"
                "- 7274 (Frontend)"
            )

        except Exception as e:
            self.update_status_message(f"Error stopping services: {e}")
            messagebox.showerror("Error", f"Failed to stop all services:\n{e}")

    # Database Management Methods

    def get_db_credentials(self) -> dict[str, Any]:
        """Get database credentials from config and environment."""
        credentials = {
            "host": "localhost",
            "port": 5432,
            "user": "postgres",
            "password": "4010",  # Development default
            "database": "postgres",  # Connect to postgres DB to check/create giljo_mcp
        }

        # Load from config if available
        if self.config:
            db_config = self.config.get("database", {})
            credentials["host"] = db_config.get("host", "localhost")
            credentials["port"] = db_config.get("port", 5432)
            credentials["user"] = db_config.get("user", "postgres")

        # Try to load password from .env
        env_file = self.project_root / ".env"
        if env_file.exists():
            try:
                with open(env_file) as f:
                    for line in f:
                        if line.startswith("DB_PASSWORD="):
                            credentials["password"] = line.split("=", 1)[1].strip()
                            break
            except Exception:
                pass  # Use default

        return credentials

    def check_db_connection(self):
        """Check if PostgreSQL is accessible."""
        if psycopg2 is None:
            messagebox.showerror(
                "Missing Dependency", "psycopg2 is not installed.\n\nInstall with: pip install psycopg2"
            )
            return

        self.update_status_message("Checking database connection...")

        try:
            credentials = self.get_db_credentials()
            conn = psycopg2.connect(
                host=credentials["host"],
                port=credentials["port"],
                user=credentials["user"],
                password=credentials["password"],
                database=credentials["database"],
                connect_timeout=5,
            )
            conn.close()

            self.db_conn_indicator.config(foreground="green")
            self.db_conn_label.config(text=f"Connected ({credentials['host']}:{credentials['port']})")
            self.db_connection_status.set(True)
            self.update_status_message("Database connection successful")
            messagebox.showinfo("Success", "PostgreSQL connection successful!")

        except Exception as e:
            self.db_conn_indicator.config(foreground="red")
            self.db_conn_label.config(text="Connection failed")
            self.db_connection_status.set(False)
            self.update_status_message(f"Database connection failed: {e}")
            messagebox.showerror("Connection Failed", f"Could not connect to PostgreSQL:\n\n{e}")

    def check_db_exists(self):
        """Check if giljo_mcp database exists."""
        if psycopg2 is None:
            messagebox.showerror(
                "Missing Dependency", "psycopg2 is not installed.\n\nInstall with: pip install psycopg2"
            )
            return

        self.update_status_message("Checking if giljo_mcp database exists...")

        try:
            credentials = self.get_db_credentials()
            conn = psycopg2.connect(
                host=credentials["host"],
                port=credentials["port"],
                user=credentials["user"],
                password=credentials["password"],
                database=credentials["database"],
                connect_timeout=5,
            )

            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM pg_database WHERE datname = 'giljo_mcp'")
                exists = cur.fetchone() is not None

            conn.close()

            if exists:
                self.db_exists_indicator.config(foreground="green")
                self.db_exists_label.config(text="Exists")
                self.db_exists_status.set(True)
                self.update_status_message("giljo_mcp database exists")
                messagebox.showinfo("Database Found", "giljo_mcp database exists!")
            else:
                self.db_exists_indicator.config(foreground="red")
                self.db_exists_label.config(text="Not found")
                self.db_exists_status.set(False)
                self.update_status_message("giljo_mcp database not found")
                messagebox.showwarning("Database Not Found", "giljo_mcp database does not exist")

        except Exception as e:
            self.db_exists_indicator.config(foreground="red")
            self.db_exists_label.config(text="Check failed")
            self.db_exists_status.set(False)
            self.update_status_message(f"Database check failed: {e}")
            messagebox.showerror("Error", f"Failed to check database:\n\n{e}")

    def delete_database(self):
        """Delete giljo_mcp database after confirmation with proper ownership handling."""
        if psycopg2 is None:
            messagebox.showerror(
                "Missing Dependency", "psycopg2 is not installed.\n\nInstall with: pip install psycopg2"
            )
            return

        # Confirmation dialog
        confirm = messagebox.askyesno(
            "Confirm Database Deletion",
            "Are you sure you want to DELETE the giljo_mcp database?\n\n"
            "This will remove:\n"
            "- All projects\n"
            "- All agents\n"
            "- All tasks\n"
            "- All messages\n"
            "- All templates\n"
            "- All data in the database\n\n"
            "This action CANNOT be undone!",
            icon="warning",
        )

        if not confirm:
            return

        self.update_status_message("Deleting giljo_mcp database...")

        try:
            credentials = self.get_db_credentials()

            # Connect to postgres database (not giljo_mcp)
            conn = psycopg2.connect(
                host=credentials["host"],
                port=credentials["port"],
                user=credentials["user"],
                password=credentials["password"],
                database="postgres",
                connect_timeout=5,
            )
            conn.autocommit = True

            with conn.cursor() as cur:
                # Step 1: Terminate all connections to giljo_mcp
                self.update_status_message("Terminating active connections...")
                cur.execute(
                    """
                    SELECT pg_terminate_backend(pg_stat_activity.pid)
                    FROM pg_stat_activity
                    WHERE pg_stat_activity.datname = 'giljo_mcp'
                      AND pid <> pg_backend_pid()
                """
                )

                # Step 2: Reassign owned objects to postgres superuser (fixes ownership issues)
                self.update_status_message("Resolving ownership conflicts...")
                for role in ['giljo_user', 'giljo_owner']:
                    try:
                        # Check if role exists first
                        cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (role,))
                        if cur.fetchone():
                            cur.execute(f"REASSIGN OWNED BY {role} TO postgres")
                    except Exception:
                        pass  # Role doesn't exist or already handled

                # Step 3: Drop owned objects (CASCADE to handle dependencies)
                self.update_status_message("Dropping owned objects...")
                for role in ['giljo_user', 'giljo_owner']:
                    try:
                        cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (role,))
                        if cur.fetchone():
                            cur.execute(f"DROP OWNED BY {role} CASCADE")
                    except Exception:
                        pass  # Role doesn't exist or already handled

                # Step 4: Drop roles if they exist
                self.update_status_message("Dropping database roles...")
                for role in ['giljo_user', 'giljo_owner']:
                    try:
                        cur.execute(f"DROP ROLE IF EXISTS {role}")
                    except Exception:
                        pass  # Role in use or other issue

                # Step 5: Finally drop the database
                self.update_status_message("Dropping database...")
                cur.execute("DROP DATABASE IF EXISTS giljo_mcp")

            conn.close()

            self.db_exists_indicator.config(foreground="red")
            self.db_exists_label.config(text="Deleted")
            self.db_exists_status.set(False)
            self.update_status_message("giljo_mcp database deleted successfully")
            messagebox.showinfo(
                "Success",
                "Database deletion complete!\n\n"
                "Removed:\n"
                "- giljo_mcp database\n"
                "- giljo_user role\n"
                "- giljo_owner role\n"
                "- All owned objects"
            )

        except Exception as e:
            self.update_status_message(f"Database deletion failed: {e}")
            messagebox.showerror("Error", f"Failed to delete database:\n\n{e}")

    # Development Reset Methods

    def reset_to_fresh(self):
        """Reset to fresh state by removing venv, configs, etc."""
        # Build list of targets
        targets = []
        venv_path = self.project_root / "venv"
        if venv_path.exists():
            targets.append(("venv/", "Virtual environment directory"))

        config_path = self.project_root / "config.yaml"
        if config_path.exists():
            targets.append(("config.yaml", "Configuration file"))

        env_path = self.project_root / ".env"
        if env_path.exists():
            targets.append((".env", "Environment variables file"))

        install_config_path = self.project_root / "install_config.yaml"
        if install_config_path.exists():
            targets.append(("install_config.yaml", "Installer configuration"))

        if not targets:
            messagebox.showinfo("Nothing to Reset", "No files/directories found to reset.")
            return

        # Show confirmation with list
        target_list = "\n".join([f"- {name}: {desc}" for name, desc in targets])
        confirm = messagebox.askyesno(
            "Confirm Reset to Fresh State",
            f"This will DELETE the following:\n\n{target_list}\n\n"
            "This simulates a fresh download.\n"
            "You will need to run the installer again.\n\n"
            "Continue?",
            icon="warning",
        )

        if not confirm:
            return

        self.update_status_message("Resetting to fresh state...")

        # Remove targets
        errors = []
        for name, desc in targets:
            try:
                target = self.project_root / name
                if target.is_dir():
                    import shutil

                    shutil.rmtree(target)
                else:
                    target.unlink()
            except Exception as e:
                errors.append(f"{name}: {e}")

        if errors:
            error_msg = "\n".join(errors)
            messagebox.showerror(
                "Partial Success",
                f"Some items could not be removed:\n\n{error_msg}\n\n"
                "You may need to remove them manually or run with admin privileges.",
            )
        else:
            self.update_status_message("Reset complete")
            messagebox.showinfo(
                "Reset Complete",
                "Reset to fresh state complete!\n\n" "You can now run the installer to set up again.",
            )

    # Cache Management Methods

    def clear_python_cache(self):
        """Clear all Python cache files and directories."""
        self.update_status_message("Clearing Python cache...")

        try:
            import shutil

            removed_count = 0

            # Remove __pycache__ directories
            for cache_dir in self.project_root.rglob("__pycache__"):
                try:
                    shutil.rmtree(cache_dir)
                    removed_count += 1
                except Exception:
                    pass

            # Remove .pyc files
            for pyc_file in self.project_root.rglob("*.pyc"):
                try:
                    pyc_file.unlink()
                    removed_count += 1
                except Exception:
                    pass

            # Remove .pyo files
            for pyo_file in self.project_root.rglob("*.pyo"):
                try:
                    pyo_file.unlink()
                    removed_count += 1
                except Exception:
                    pass

            self.update_status_message(f"Python cache cleared ({removed_count} items)")
            messagebox.showinfo("Success", f"Python cache cleared!\n\nRemoved {removed_count} cache items.")

        except Exception as e:
            self.update_status_message(f"Error clearing Python cache: {e}")
            messagebox.showerror("Error", f"Failed to clear Python cache:\n\n{e}")

    def clear_frontend_cache(self):
        """Clear frontend cache (Vite, dist)."""
        self.update_status_message("Clearing frontend cache...")

        try:
            import shutil

            removed = []

            # Clear Vite cache
            vite_cache = self.project_root / "frontend" / "node_modules" / ".vite"
            if vite_cache.exists():
                shutil.rmtree(vite_cache)
                removed.append("Vite cache")

            # Clear dist directory
            dist_dir = self.project_root / "frontend" / "dist"
            if dist_dir.exists():
                shutil.rmtree(dist_dir)
                removed.append("dist directory")

            if removed:
                self.update_status_message("Frontend cache cleared")
                messagebox.showinfo(
                    "Success", "Frontend cache cleared!\n\nRemoved:\n" + "\n".join(f"- {r}" for r in removed)
                )
            else:
                self.update_status_message("No frontend cache found")
                messagebox.showinfo("Nothing to Clear", "No frontend cache found.")

        except Exception as e:
            self.update_status_message(f"Error clearing frontend cache: {e}")
            messagebox.showerror("Error", f"Failed to clear frontend cache:\n\n{e}")

    def clear_all_caches(self):
        """Clear both Python and frontend caches."""
        self.clear_python_cache()
        time.sleep(0.5)
        self.clear_frontend_cache()

    # Frontend Tools Methods

    def hard_reload_frontend(self):
        """Hard reload frontend: stop, clear cache, restart, open browser."""
        self.update_status_message("Performing hard reload...")

        try:
            # Stop frontend if running
            if self.frontend_process and self.frontend_process.poll() is None:
                self.stop_frontend()
                time.sleep(1)

            # Clear Vite cache
            import shutil

            vite_cache = self.project_root / "frontend" / "node_modules" / ".vite"
            if vite_cache.exists():
                shutil.rmtree(vite_cache)

            # Start frontend
            self.start_frontend()
            time.sleep(3)

            # Open browser with cache-busting parameter
            frontend_port = 7274
            if self.config:
                frontend_port = self.config.get("services", {}).get("frontend", {}).get("port", 7274)

            cache_bust = int(time.time())
            url = f"http://localhost:{frontend_port}?_={cache_bust}"
            webbrowser.open(url)

            self.update_status_message("Hard reload complete")
            messagebox.showinfo(
                "Success",
                "Frontend hard reload complete!\n\n"
                "- Stopped dev server\n"
                "- Cleared Vite cache\n"
                "- Restarted dev server\n"
                "- Opened browser",
            )

        except Exception as e:
            self.update_status_message(f"Error during hard reload: {e}")
            messagebox.showerror("Error", f"Failed to perform hard reload:\n\n{e}")

    def run(self):
        """Run the control panel application."""
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            self.stop_all_services()
            sys.exit(0)


def main():
    """Main entry point."""
    print("=" * 60)
    print("   GiljoAI MCP Developer Control Panel")
    print("=" * 60)
    print()

    # Check for required dependencies
    missing = []
    if psutil is None:
        missing.append("psutil")
    if psycopg2 is None:
        missing.append("psycopg2")
    if yaml is None:
        missing.append("pyyaml")

    if missing:
        print("Warning: Missing optional dependencies:")
        for dep in missing:
            print(f"  - {dep}")
        print()
        print("Some features may not work. Install with:")
        print(f"  pip install {' '.join(missing)}")
        print()

    # Create and run control panel
    app = GiljoDevControlPanel()
    app.run()


if __name__ == "__main__":
    main()
