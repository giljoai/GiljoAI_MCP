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
import logging
import os
import platform
import shutil
import subprocess
import sys
import time
import webbrowser
from pathlib import Path
from tkinter import BooleanVar, Tk, messagebox, ttk
from typing import Any, List, Optional


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
        self.root.geometry("750x600")
        self.root.resizable(True, True)
        self.root.minsize(700, 500)

        # Project root detection (dynamic, no hardcoded paths)
        # If running from dev_tools/, go up one level
        if Path.cwd().name == "dev_tools":
            self.project_root = Path.cwd().parent
        else:
            self.project_root = Path.cwd()

        # Verify we found the project root
        if not (self.project_root / "api" / "run_api.py").exists():
            # Fallback: check if we're in project root
            if (Path.cwd() / "api" / "run_api.py").exists():
                self.project_root = Path.cwd()
            # Or if we need to go up
            elif (Path.cwd().parent / "api" / "run_api.py").exists():
                self.project_root = Path.cwd().parent

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

        # Setup logger for database operations
        self.logger = logging.getLogger("GiljoDevControlPanel")
        self.logger.setLevel(logging.INFO)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
            self.logger.addHandler(handler)

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
        """Build the complete UI with tabbed interface."""
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

        # Create tabbed notebook
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(0, 10))

        # Configure grid weights for resizing
        main_frame.grid_rowconfigure(1, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)

        # Build tabs
        self.build_services_tab()
        self.build_database_tab()
        self.build_resets_tab()
        self.build_reference_tab()

        # Status bar at bottom (5 rows high)
        self.status_label = ttk.Label(
            main_frame, text="Ready", relief="sunken", anchor="nw", justify="left", padding=(5, 5)
        )
        self.status_label.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(10, 0), ipady=40)

    def build_services_tab(self):
        """Build the Services tab with service management, cache, and frontend tools."""
        tab = ttk.Frame(self.notebook, padding="5")
        self.notebook.add(tab, text="Services")

        # Make tab scrollable if needed
        tab.grid_columnconfigure(0, weight=1)

        row = 0

        # Service Management section
        row = self.build_service_section(tab, row)

        # Cache Management section
        row = self.build_cache_section(tab, row)

        # Frontend Tools section
        row = self.build_frontend_section(tab, row)

    def build_database_tab(self):
        """Build the Database tab (connection check only)."""
        tab = ttk.Frame(self.notebook, padding="5")
        self.notebook.add(tab, text="Database")

        # Database Connection Check section
        section = ttk.LabelFrame(tab, text="Database Connection", padding="5")
        section.grid(row=0, column=0, columnspan=2, sticky="ew", pady=3)

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

        # Last backup status
        ttk.Label(section, text="Last Backup:").grid(row=2, column=0, sticky="w", pady=(10, 0))
        self.backup_indicator = ttk.Label(section, text="●", foreground="gray")
        self.backup_indicator.grid(row=2, column=1, pady=(10, 0))
        self.backup_label = ttk.Label(section, text="Not checked")
        self.backup_label.grid(row=2, column=2, sticky="w", padx=(5, 0), pady=(10, 0))

        # Action buttons
        ttk.Separator(section, orient="horizontal").grid(row=3, column=0, columnspan=4, sticky="ew", pady=10)
        ttk.Button(section, text="Check Connection", command=self.check_db_connection, width=20).grid(
            row=4, column=0, padx=5, pady=2
        )
        ttk.Button(section, text="Check Database", command=self.check_db_exists, width=20).grid(
            row=4, column=1, padx=5, pady=2
        )

        # Check for last backup on startup
        self.check_last_backup()

    def build_resets_tab(self):
        """Build the Resets tab (consolidated reset operations)."""
        tab = ttk.Frame(self.notebook, padding="5")
        self.notebook.add(tab, text="Resets")

        row = 0

        # Project Resets section
        row = self.build_project_reset_section(tab, row)

        # Database Operations section
        db_section = ttk.LabelFrame(tab, text="Database Operations", padding="5")
        db_section.grid(row=row, column=0, columnspan=2, sticky="ew", pady=3)

        ttk.Button(db_section, text="Backup Database", command=self.backup_database, width=20).grid(
            row=0, column=0, padx=5, pady=5
        )

        ttk.Button(db_section, text="Delete Database", command=self.delete_database, width=20).grid(
            row=0, column=1, padx=5, pady=5
        )

        row += 1

        # Environment Resets section
        row = self.build_reset_section(tab, row)

    def build_reference_tab(self):
        """Build the Reference tab with quick developer references."""
        tab = ttk.Frame(self.notebook, padding="5")
        self.notebook.add(tab, text="Reference")

        # Log Colors section
        colors_section = ttk.LabelFrame(tab, text="Log Color Legend", padding="10")
        colors_section.grid(row=0, column=0, sticky="ew", pady=3)

        # Color definitions with their meanings
        log_colors = [
            ("RED", "#DC3545", "Errors & Critical Issues", "Something broke - fix immediately"),
            ("YELLOW", "#FFC107", "Warnings", "Potential issue - investigate soon"),
            ("GREEN", "#28A745", "Success", "Operation completed successfully"),
            ("BLUE", "#007BFF", "Information", "General status updates"),
            ("WHITE", "#6C757D", "Debug", "Technical details for troubleshooting"),
            ("CYAN", "#17A2B8", "Highlights", "Important values & key data"),
        ]

        # Header
        ttk.Label(
            colors_section,
            text="Terminal logs use colors to help you quickly identify message severity:",
            wraplength=400,
        ).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 10))

        # Color table
        for idx, (color_name, hex_color, meaning, description) in enumerate(log_colors, start=1):
            # Colored indicator
            indicator = ttk.Label(colors_section, text="████", foreground=hex_color)
            indicator.grid(row=idx, column=0, sticky="w", padx=(0, 10))

            # Color name and meaning
            ttk.Label(colors_section, text=f"{color_name}: {meaning}", font=("Arial", 10, "bold")).grid(
                row=idx, column=1, sticky="w", padx=(0, 10)
            )

            # Description
            ttk.Label(colors_section, text=description, foreground="gray").grid(row=idx, column=2, sticky="w")

        # Tip at bottom
        tip_label = ttk.Label(
            colors_section,
            text="Tip: Red and yellow messages need your attention first!",
            font=("Arial", 9, "italic"),
            foreground="#6C757D",
        )
        tip_label.grid(row=len(log_colors) + 1, column=0, columnspan=3, sticky="w", pady=(15, 0))

    def build_service_section(self, parent: ttk.Frame, row: int) -> int:
        """Build service management section."""
        # Section frame
        section = ttk.LabelFrame(parent, text="Service Management", padding="5")
        section.grid(row=row, column=0, columnspan=2, sticky="ew", pady=3)

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
        section = ttk.LabelFrame(parent, text="Database Management", padding="5")
        section.grid(row=row, column=0, columnspan=2, sticky="ew", pady=3)

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

        # Last backup status
        ttk.Label(section, text="Last Backup:").grid(row=2, column=0, sticky="w", pady=(10, 0))
        self.backup_indicator = ttk.Label(section, text="●", foreground="gray")
        self.backup_indicator.grid(row=2, column=1, pady=(10, 0))
        self.backup_label = ttk.Label(section, text="Not checked")
        self.backup_label.grid(row=2, column=2, sticky="w", padx=(5, 0), pady=(10, 0))

        # Action buttons
        ttk.Separator(section, orient="horizontal").grid(row=3, column=0, columnspan=4, sticky="ew", pady=10)
        ttk.Button(section, text="Check Connection", command=self.check_db_connection, width=20).grid(
            row=4, column=0, padx=5, pady=2
        )
        ttk.Button(section, text="Check Database", command=self.check_db_exists, width=20).grid(
            row=4, column=1, padx=5, pady=2
        )
        ttk.Button(section, text="Backup Database", command=self.backup_database, width=20).grid(
            row=4, column=2, padx=5, pady=2
        )
        ttk.Button(section, text="Delete Database", command=self.delete_database, width=20).grid(
            row=4, column=3, padx=5, pady=2
        )

        # Check for last backup on startup
        self.check_last_backup()

        return row + 1

    def build_project_reset_section(self, parent: ttk.Frame, row: int) -> int:
        """Build project reset section - clear AI-generated staging data only."""
        section = ttk.LabelFrame(parent, text="Clear Project to Initial State", padding="5")
        section.grid(row=row, column=0, columnspan=2, sticky="ew", pady=3)

        ttk.Label(
            section,
            text="Remove AI-generated staging data (mission, agents, jobs) but keep project name/description",
            wraplength=600,
        ).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 10))

        # Project UUID input
        ttk.Label(section, text="Project UUID:").grid(row=1, column=0, sticky="w", padx=5)
        self.project_uuid_entry = ttk.Entry(section, width=40)
        self.project_uuid_entry.grid(row=1, column=1, sticky="ew", padx=5, pady=5)

        # Clear button
        ttk.Button(
            section,
            text="Clear Project",
            command=self.clear_project_staging,
            width=20,
        ).grid(row=1, column=2, padx=5, pady=5)

        # Description label
        ttk.Label(
            section,
            text="Clears: mission, spawned agents (waiting/preparing), agent jobs, messages",
            font=("Arial", 8),
            foreground="blue",
        ).grid(row=2, column=0, columnspan=3, sticky="w", padx=5)

        ttk.Label(
            section,
            text="Keeps: project name, description, status, metadata (human-entered data)",
            font=("Arial", 8),
            foreground="green",
        ).grid(row=3, column=0, columnspan=3, sticky="w", padx=5)

        return row + 1

    def build_reset_section(self, parent: ttk.Frame, row: int) -> int:
        """Build development reset section."""
        section = ttk.LabelFrame(parent, text="Development Reset", padding="5")
        section.grid(row=row, column=0, columnspan=2, sticky="ew", pady=3)

        ttk.Label(
            section,
            text="Reset options for development and testing",
            wraplength=600,
        ).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 10))

        # Row 1: Buttons
        ttk.Button(
            section,
            text="Reset to Fresh State",
            command=self.reset_to_fresh,
            width=25,
        ).grid(row=1, column=0, pady=5, padx=5)

        ttk.Button(
            section,
            text="Verify Fresh State",
            command=self.display_fresh_state_report,
            width=25,
        ).grid(row=1, column=1, pady=5, padx=5)

        ttk.Button(
            section,
            text="Reset to Pristine",
            command=self.reset_to_pristine,
            width=25,
        ).grid(row=1, column=2, pady=5, padx=5)

        # Row 2: Descriptions
        ttk.Label(
            section,
            text="Reset admin password to 'admin'",
            font=("Arial", 8),
        ).grid(row=2, column=0, sticky="w", padx=5)

        ttk.Label(
            section,
            text="Check if system is clean",
            font=("Arial", 8),
        ).grid(row=2, column=1, sticky="w", padx=5)

        ttk.Label(
            section,
            text="Complete reset (deletes everything)",
            font=("Arial", 8),
            foreground="red",
        ).grid(row=2, column=2, sticky="w", padx=5)

        return row + 1

    def build_cache_section(self, parent: ttk.Frame, row: int) -> int:
        """Build cache management section."""
        section = ttk.LabelFrame(parent, text="Cache Management", padding="5")
        section.grid(row=row, column=0, columnspan=2, sticky="ew", pady=3)

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
        section = ttk.LabelFrame(parent, text="Frontend Tools", padding="5")
        section.grid(row=row, column=0, columnspan=2, sticky="ew", pady=3)

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
        """Update all status indicators - detects ANY process on ports (not just tracked)."""
        # Check backend status - look for ANY process on port 7272
        backend_pid = self._find_process_on_port(7272)
        if backend_pid:
            self.backend_indicator.config(foreground="green")
            if self.backend_process and self.backend_process.poll() is None:
                self.backend_status_label.config(text=f"Running (Port 7272, PID {backend_pid})")
            else:
                # Process exists but NOT tracked by dev_tool
                self.backend_status_label.config(text=f"Running (Port 7272, PID {backend_pid}) [External]")
            self.backend_status.set(True)
        else:
            self.backend_indicator.config(foreground="red")
            self.backend_status_label.config(text="Stopped")
            self.backend_status.set(False)

        # Check frontend status - look for ANY process on port 7274
        frontend_pid = self._find_process_on_port(7274)
        if frontend_pid:
            self.frontend_indicator.config(foreground="green")
            if self.frontend_process and self.frontend_process.poll() is None:
                self.frontend_status_label.config(text=f"Running (Port 7274, PID {frontend_pid})")
            else:
                # Process exists but NOT tracked by dev_tool
                self.frontend_status_label.config(text=f"Running (Port 7274, PID {frontend_pid}) [External]")
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

        system = platform.system()
        work_dir = str(cwd if cwd else self.project_root)

        if system == "Windows":
            # Windows: Use cmd /k so the terminal stays open on error (user can read the message).
            # Without this, CREATE_NEW_CONSOLE closes the window instantly when the command fails.
            cmd_str = subprocess.list2cmdline(command)
            return subprocess.Popen(
                ["cmd", "/k", cmd_str],
                cwd=work_dir,
                creationflags=subprocess.CREATE_NEW_CONSOLE,
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
            raise FileNotFoundError("No suitable terminal emulator found. Install gnome-terminal, konsole, or xterm.")

        if system == "Darwin":
            # macOS: Use osascript with Terminal.app
            cmd_str = " ".join(command)
            script = f'tell application "Terminal" to do script "cd {work_dir} && {cmd_str}"'

            subprocess.Popen(["osascript", "-e", script])
            # Note: Cannot easily get PID on macOS with this approach
            return None

        raise OSError(f"Unsupported operating system: {system}")

    def _get_main_python_executable(self) -> Path:
        """
        Locate the Python executable inside the main project virtual environment.

        Returns:
            Path to Python interpreter inside venv.

        Raises:
            FileNotFoundError if the interpreter cannot be located.
        """
        # Check for .venv (preferred) or venv (legacy fallback)
        venv_dir = self.project_root / ".venv"
        if not venv_dir.exists():
            venv_dir = self.project_root / "venv"  # Legacy fallback

        if not venv_dir.exists():
            raise FileNotFoundError(
                f"Virtual environment not found at {self.project_root / '.venv'} or {self.project_root / 'venv'}. "
                "Run the installer to create the environment before using the control panel."
            )

        system = platform.system()
        candidates: List[Path] = []

        if system == "Windows":
            candidates.append(venv_dir / "Scripts" / "python.exe")
        else:
            candidates.extend(
                [
                    venv_dir / "bin" / "python",
                    venv_dir / "bin" / "python3",
                ]
            )

        for candidate in candidates:
            if candidate.exists():
                return candidate

        raise FileNotFoundError(
            "Could not locate the Python interpreter inside the project virtual environment.\n"
            "Expected one of:\n" + "\n".join(str(path) for path in candidates)
        )

    def _is_service_listening(self, port: int) -> bool:
        """
        Check if a service is actively listening on the given port.

        Uses socket.connect_ex() which works reliably across Windows, Linux,
        and macOS regardless of which interface (0.0.0.0 vs 127.0.0.1) the
        service binds to. This avoids the Windows-specific issue where
        socket.bind("127.0.0.1", port) succeeds even when another process
        is bound to 0.0.0.0:port.

        Args:
            port: Port number to check

        Returns:
            True if a service is listening, False otherwise
        """
        import socket

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                result = s.connect_ex(("127.0.0.1", port))
                return result == 0
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
            for conn in psutil.net_connections(kind="inet"):
                if conn.laddr.port == port:
                    return conn.pid
        except (psutil.AccessDenied, AttributeError):
            # May need admin privileges or psutil not fully functional
            return None

        return None

    def _find_all_giljo_ports(self) -> dict[int, int]:
        """
        Find ALL processes using ports in 72xxx range (GiljoAI ports).

        This detects processes started by ANY method (not just dev_tool).

        Returns:
            Dictionary mapping port number to PID
            Example: {7272: 12345, 7274: 67890}
        """
        giljo_ports = {}

        if psutil is None:
            return giljo_ports

        try:
            for conn in psutil.net_connections(kind="inet"):
                # Check if port is in 72xx range (7200-7299)
                if 7200 <= conn.laddr.port <= 7299:
                    giljo_ports[conn.laddr.port] = conn.pid
        except (psutil.AccessDenied, AttributeError):
            # Fallback to platform-specific CLI
            try:
                system = platform.system()
                if system == "Windows":
                    result = subprocess.run(
                        ["netstat", "-ano"], check=False, capture_output=True, text=True, timeout=5
                    )
                    for line in result.stdout.splitlines():
                        if ":72" in line and "LISTENING" in line:
                            parts = line.split()
                            if parts:
                                addr_parts = parts[1].split(":")
                                if len(addr_parts) == 2:
                                    try:
                                        port = int(addr_parts[1])
                                        pid = int(parts[-1])
                                        if 7200 <= port <= 7299 and pid != 0:
                                            giljo_ports[port] = pid
                                    except (ValueError, IndexError):
                                        pass
                else:
                    # Linux/macOS: use ss (preferred) or lsof
                    result = subprocess.run(
                        ["ss", "-tlnp"], check=False, capture_output=True, text=True, timeout=5
                    )
                    for line in result.stdout.splitlines():
                        if ":72" in line:
                            # ss output: LISTEN 0 128 0.0.0.0:7272 ... users:(("python3",pid=1234,...))
                            parts = line.split()
                            for part in parts:
                                if ":72" in part and "." in part:
                                    try:
                                        port = int(part.rsplit(":", 1)[1])
                                        if 7200 <= port <= 7299:
                                            # Extract PID from users:(...pid=NNNN...)
                                            import re
                                            pid_match = re.search(r"pid=(\d+)", line)
                                            pid = int(pid_match.group(1)) if pid_match else None
                                            if pid:
                                                giljo_ports[port] = pid
                                    except (ValueError, IndexError):
                                        pass
            except Exception:
                pass

        return giljo_ports

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
        TRIPLE-NUCLEAR option: Kill ALL processes using a specific port.

        Enhanced to handle auto-restart processes:
        1. Kill all processes on port (3 attempts)
        2. Wait and verify port is free
        3. If process respawns, kill again (up to 5 total rounds)

        Uses system commands for maximum aggression.

        Args:
            port: Port number to clear
        """
        system = platform.system()
        max_rounds = 5  # Maximum kill rounds (handles auto-restart)
        kills_per_round = 3  # Kill attempts per round

        for round_num in range(max_rounds):
            pids_killed_this_round = set()

            # Perform multiple kill attempts per round
            for attempt in range(kills_per_round):
                try:
                    if system == "Windows":
                        # Find PIDs using the port
                        result = subprocess.run(
                            ["netstat", "-ano"], check=False, capture_output=True, text=True, timeout=5
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
                                    ["taskkill", "/F", "/PID", pid], check=False, capture_output=True, timeout=5
                                )
                                pids_killed_this_round.add(pid)
                            except Exception:
                                pass

                    else:  # Linux/macOS
                        # Use lsof to find and kill processes
                        try:
                            result = subprocess.run(
                                ["lsof", "-ti", f":{port}"], check=False, capture_output=True, text=True, timeout=5
                            )

                            pids = result.stdout.strip().split()
                            for pid in pids:
                                if pid:
                                    try:
                                        subprocess.run(["kill", "-9", pid], check=False, capture_output=True, timeout=5)
                                        pids_killed_this_round.add(pid)
                                    except Exception:
                                        pass
                        except FileNotFoundError:
                            # lsof not available, try fuser
                            try:
                                subprocess.run(
                                    ["fuser", "-k", f"{port}/tcp"], check=False, capture_output=True, timeout=5
                                )
                            except FileNotFoundError:
                                pass

                    # Small delay between kill attempts
                    if attempt < kills_per_round - 1:
                        time.sleep(0.3)

                except Exception as e:
                    print(f"Warning: Kill attempt {attempt + 1} for port {port} failed: {e}")

            # Wait for processes to die
            time.sleep(1)

            # Verify port is now free (connect-based check)
            if not self._is_service_listening(port):
                # Success! Port is free
                if pids_killed_this_round:
                    print(f"Port {port} cleared after round {round_num + 1} (killed PIDs: {pids_killed_this_round})")
                return

            # Port still in use - process may have auto-restarted
            if round_num < max_rounds - 1:
                print(f"Port {port} still in use after round {round_num + 1}, trying again...")

        # If we get here, port is STILL in use after all rounds
        print(f"WARNING: Port {port} could not be cleared after {max_rounds} rounds!")

    # Service Management Methods

    def check_backend_port(self):
        """Check what's running on port 7272 and scan ALL 72xxx ports."""
        port = 7272

        # Check specific port (connect-based, reliable on all OSes)
        port_available = not self._is_service_listening(port)
        pid = self._find_process_on_port(port)

        # Scan ALL 72xxx ports
        all_giljo_ports = self._find_all_giljo_ports()

        # Build comprehensive report
        report = f"Backend Port {port}:\n"
        if port_available:
            report += "✓ Available (no process)\n"
        elif pid:
            report += f"✗ IN USE by PID {pid}\n"
        else:
            report += "✗ IN USE (PID unknown - need admin privileges)\n"

        # Add scan of all GiljoAI ports
        report += "\n--- All GiljoAI Ports (7200-7299) ---\n"
        if all_giljo_ports:
            report += f"Found {len(all_giljo_ports)} process(es):\n\n"
            for p, proc_pid in sorted(all_giljo_ports.items()):
                report += f"Port {p}: PID {proc_pid}\n"
            report += "\nUse 'Stop All Services' to kill these processes."
        else:
            report += "✓ No processes found on 7200-7299"

        if port_available:
            messagebox.showinfo("Port Scan Results", report)
        else:
            messagebox.showwarning("Port Scan Results", report)

    def check_frontend_port(self):
        """Check what's running on port 7274 and scan ALL 72xxx ports."""
        port = 7274

        # Check specific port (connect-based, reliable on all OSes)
        port_available = not self._is_service_listening(port)
        pid = self._find_process_on_port(port)

        # Scan ALL 72xxx ports
        all_giljo_ports = self._find_all_giljo_ports()

        # Build comprehensive report
        report = f"Frontend Port {port}:\n"
        if port_available:
            report += "✓ Available (no process)\n"
        elif pid:
            report += f"✗ IN USE by PID {pid}\n"
        else:
            report += "✗ IN USE (PID unknown - need admin privileges)\n"

        # Add scan of all GiljoAI ports
        report += "\n--- All GiljoAI Ports (7200-7299) ---\n"
        if all_giljo_ports:
            report += f"Found {len(all_giljo_ports)} process(es):\n\n"
            for p, proc_pid in sorted(all_giljo_ports.items()):
                report += f"Port {p}: PID {proc_pid}\n"
            report += "\nUse 'Stop All Services' to kill these processes."
        else:
            report += "✓ No processes found on 7200-7299"

        if port_available:
            messagebox.showinfo("Port Scan Results", report)
        else:
            messagebox.showwarning("Port Scan Results", report)

    def start_backend(self):
        """Start the backend API service in a new terminal window."""
        if self.backend_process and self.backend_process.poll() is None:
            messagebox.showinfo("Already Running", "Backend service is already running.")
            return

        # Also check port directly (covers macOS where process ref is None)
        api_port = 7272
        if self.config:
            api_port = self.config.get("services", {}).get("api", {}).get("port", 7272)
        if self._is_service_listening(api_port):
            messagebox.showinfo("Already Running", f"Backend is already listening on port {api_port}.")
            return

        self.update_status_message("Starting backend service in terminal window...")

        try:
            # Check if api/run_api.py exists
            api_script = self.project_root / "api" / "run_api.py"
            if not api_script.exists():
                raise FileNotFoundError(f"API script not found: {api_script}")

            # Build command - use main venv Python, not dev tools venv
            main_venv_python = self._get_main_python_executable()
            command = [str(main_venv_python), str(api_script), "--port", str(api_port)]

            # Launch in terminal window with verbose output
            self.backend_process = self._launch_in_terminal(
                command=command, title="GiljoAI Backend API", cwd=self.project_root
            )

            # Wait for API to start listening on port.
            # Uses connect() instead of bind() for detection - bind("127.0.0.1")
            # can falsely succeed on Windows when a service binds to 0.0.0.0.
            self.update_status_message(f"Waiting for backend on port {api_port}...")
            started = False
            for _ in range(30):  # Wait up to 15 seconds
                time.sleep(0.5)
                if self._is_service_listening(api_port):
                    started = True
                    break

            if started:
                self.update_status_message(f"Backend started in terminal on port {api_port}")
            else:
                self.update_status_message("Backend may still be starting...")
                messagebox.showwarning(
                    "Slow Start",
                    f"Backend has not responded on port {api_port} after 15s.\n\n"
                    "Check the terminal window for status or errors.",
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

            # Check if port 7274 is in use (connect-based, reliable on all OSes)
            if self._is_service_listening(frontend_port):
                # Port is in use - check if we can find the process
                existing_pid = self._find_process_on_port(frontend_port)

                if existing_pid:
                    # Found process using the port - offer to kill it
                    response = messagebox.askyesno(
                        "Port In Use",
                        f"Port {frontend_port} is in use by process {existing_pid}.\n\n"
                        "Kill the existing process and start frontend?",
                        icon="warning",
                    )

                    if response:
                        # User confirmed - kill process and wait for port release
                        self._kill_process(existing_pid)
                        time.sleep(1)  # Wait for port to be released

                        # Re-check if service is still listening
                        if self._is_service_listening(frontend_port):
                            messagebox.showerror(
                                "Port Still In Use",
                                f"Port {frontend_port} is still in use after killing process.\n\n"
                                "Please manually stop the process before starting frontend.",
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
                        "You can use 'Stop Frontend' button or manually kill the process.",
                    )
                    self.update_status_message(f"Port {frontend_port} is in use - cannot start frontend")
                    return

            # Port is available - proceed with start
            self.update_status_message("Starting frontend on port 7274 (strict mode)...")

            frontend_dir = self.project_root / "frontend"
            if not frontend_dir.exists():
                raise FileNotFoundError(f"Frontend directory not found: {frontend_dir}")

            # Check node_modules exists - offer to install if missing
            if not (frontend_dir / "node_modules").exists():
                response = messagebox.askyesno(
                    "Dependencies Missing",
                    "frontend/node_modules not found.\n\n"
                    "Run 'npm install' now?",
                    icon="warning",
                )
                if response:
                    self.update_status_message("Running npm install...")
                    npm_cmd = "npm.cmd" if platform.system() == "Windows" else "npm"
                    install_result = subprocess.run(
                        [npm_cmd, "install"],
                        cwd=str(frontend_dir),
                        capture_output=True,
                        text=True,
                        timeout=120,
                    )
                    if install_result.returncode != 0:
                        messagebox.showerror(
                            "npm install failed",
                            f"npm install exited with code {install_result.returncode}\n\n"
                            f"{install_result.stderr[:500]}",
                        )
                        self.update_status_message("npm install failed")
                        return
                    self.update_status_message("npm install complete, starting frontend...")
                else:
                    self.update_status_message("Frontend start cancelled - missing node_modules")
                    return

            # Build command with strict port enforcement
            npm_cmd = "npm.cmd" if platform.system() == "Windows" else "npm"
            command = [
                npm_cmd,
                "run",
                "dev",
                "--",
                "--port",
                str(frontend_port),
                "--strictPort",  # Fail if port unavailable (no fallback)
            ]

            # Launch in terminal window with verbose output
            self.frontend_process = self._launch_in_terminal(
                command=command, title=f"GiljoAI Frontend Dev Server (Port {frontend_port})", cwd=frontend_dir
            )

            # Wait for frontend to start listening on port.
            # Uses connect() instead of bind() for detection - bind("127.0.0.1")
            # can falsely succeed on Windows when a service binds to 0.0.0.0.
            self.update_status_message(f"Waiting for frontend on port {frontend_port}...")
            started = False
            for _ in range(30):  # Wait up to 15 seconds (Vite is slow on Windows)
                time.sleep(0.5)
                if self._is_service_listening(frontend_port):
                    started = True
                    break

            if started:
                self.update_status_message(f"Frontend started on port {frontend_port} (strict)")
            else:
                self.update_status_message("Frontend may still be starting...")
                messagebox.showwarning(
                    "Slow Start",
                    f"Frontend has not responded on port {frontend_port} after 15s.\n\n"
                    "Check the terminal window for status or errors.",
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
        """
        Stop all services - TRIPLE-NUCLEAR OPTION.

        Scans ALL ports 7200-7299 and kills EVERYTHING found.
        Handles auto-restart processes with multiple kill rounds.
        """
        self.update_status_message("Scanning ALL 72xxx ports for GiljoAI processes...")

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

            # Find ALL processes on 72xxx ports (comprehensive scan)
            giljo_ports = self._find_all_giljo_ports()

            if giljo_ports:
                ports_found = sorted(giljo_ports.keys())
                self.update_status_message(
                    f"Found {len(giljo_ports)} process(es) on ports: {', '.join(map(str, ports_found))}"
                )

                # TRIPLE-NUCLEAR: Kill everything found
                for port in ports_found:
                    self.update_status_message(f"Killing process on port {port} (triple-nuclear)...")
                    self._nuclear_kill_port(port)

                time.sleep(1)

                # Verify all ports cleared
                remaining = self._find_all_giljo_ports()
                if remaining:
                    self.update_status_message(f"WARNING: {len(remaining)} port(s) still in use!")
                    messagebox.showwarning(
                        "Incomplete Shutdown",
                        "Some processes could not be killed:\n\n"
                        + "\n".join(f"Port {p}: PID {pid}" for p, pid in remaining.items())
                        + "\n\nThese may be system-protected or auto-restarting.",
                    )
                else:
                    self.update_status_message("All services stopped (triple-nuclear)")
                    messagebox.showinfo(
                        "Success",
                        f"All services stopped!\n\nKilled {len(giljo_ports)} process(es) on ports:\n"
                        + ", ".join(map(str, ports_found)),
                    )
            else:
                self.update_status_message("No services running on 72xxx ports")
                messagebox.showinfo("No Services", "No processes found on ports 7200-7299")

        except Exception as e:
            self.update_status_message(f"Error stopping services: {e}")
            messagebox.showerror("Error", f"Failed to stop all services:\n{e}")

    # Database Management Methods

    def get_db_credentials(self) -> dict[str, Any]:
        """
        Get database credentials from .env or prompt.

        Cross-platform support:
        - Reads PG_SUPERUSER_PASSWORD from .env (set per dev station)
        - Falls back to prompting via dialog if not found
        - Caches the password for the session
        - Always connects to localhost:5432
        """
        password = getattr(self, "_cached_pg_password", None)

        if not password:
            # Try reading from .env
            env_file = self.project_root / ".env"
            if env_file.exists():
                try:
                    for line in env_file.read_text().splitlines():
                        line = line.strip()
                        if line.startswith("PG_SUPERUSER_PASSWORD="):
                            password = line.split("=", 1)[1].strip().strip("'\"")
                            break
                except Exception:
                    pass

            # Prompt if not found
            if not password:
                from tkinter import simpledialog
                password = simpledialog.askstring(
                    "PostgreSQL Password",
                    "Enter postgres superuser password:\n\n"
                    "(Add PG_SUPERUSER_PASSWORD=<pwd> to .env to skip this prompt)",
                    show="*",
                    parent=self.root,
                )

            if password:
                self._cached_pg_password = password

        credentials = {
            "host": "localhost",
            "port": 5432,
            "user": "postgres",
            "password": password,
            "database": "postgres",
        }

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
        """
        Delete giljo_mcp database after confirmation with proper ownership handling.

        Multi-PC Support:
        - Reads postgres password from .env (PG_SUPERUSER_PASSWORD) or prompts
        - Always connects to localhost PostgreSQL
        - Fallback to psql command-line if psycopg2 fails
        """
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

        # Try psycopg2 first, fallback to psql command-line
        if psycopg2 is not None:
            success = self._delete_database_with_psycopg2()
            if success:
                return
            # psycopg2 failed, try fallback
            self.update_status_message("psycopg2 failed, trying psql CLI fallback...")

        # Fallback to psql command-line
        self._delete_database_with_psql_cli()

    def _delete_database_with_psycopg2(self) -> bool:
        """
        Delete database using psycopg2 library with User/ApiKey auditing.

        Enhanced to:
        - Count User and ApiKey records before deletion
        - Verify foreign key constraints
        - Display detailed counts in success message
        - Handle counting errors gracefully

        Returns:
            True if successful, False if failed
        """
        try:
            credentials = self.get_db_credentials()

            # First, connect to giljo_mcp to count Users/ApiKeys before deletion
            user_count = 0
            apikey_count = 0
            fk_count = 0

            try:
                self.update_status_message("Auditing User/ApiKey data...")
                audit_conn = psycopg2.connect(
                    host=credentials["host"],
                    port=credentials["port"],
                    user=credentials["user"],
                    password=credentials["password"],
                    database="giljo_mcp",
                    connect_timeout=5,
                )

                with audit_conn.cursor() as audit_cur:
                    # Count users
                    try:
                        audit_cur.execute("SELECT COUNT(*) FROM users")
                        user_count = audit_cur.fetchone()[0]
                        self.logger.info(f"Found {user_count} users to delete")
                    except Exception as e:
                        user_count = 0
                        self.logger.warning(f"Could not count users: {e}")

                    # Count API keys
                    try:
                        audit_cur.execute("SELECT COUNT(*) FROM api_keys")
                        apikey_count = audit_cur.fetchone()[0]
                        self.logger.info(f"Found {apikey_count} API keys to delete")
                    except Exception as e:
                        apikey_count = 0
                        self.logger.warning(f"Could not count API keys: {e}")

                    # Verify foreign key constraints
                    self.update_status_message("Verifying User/ApiKey constraints...")
                    try:
                        audit_cur.execute("""
                            SELECT COUNT(*)
                            FROM information_schema.table_constraints
                            WHERE constraint_type = 'FOREIGN KEY'
                              AND table_name IN ('users', 'api_keys')
                        """)
                        fk_count = audit_cur.fetchone()[0]
                        self.logger.info(f"Found {fk_count} foreign key constraints on User/ApiKey tables")
                    except Exception as e:
                        self.logger.warning(f"Could not verify constraints: {e}")

                audit_conn.close()
            except Exception as e:
                # Database might not exist or tables don't exist - continue with deletion
                self.logger.warning(f"Could not audit database (may not exist): {e}")

            # Connect to postgres database (not giljo_mcp) for deletion
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
                # Step 1: Find ALL giljo-related databases (not just giljo_mcp)
                self.update_status_message("Finding all giljo databases...")
                cur.execute("""
                    SELECT datname FROM pg_database
                    WHERE datname LIKE 'giljo%'
                    AND datname != 'postgres'
                """)
                giljo_databases = [row[0] for row in cur.fetchall()]
                self.logger.info(f"Found giljo databases: {giljo_databases}")

                # Step 2: Terminate connections to ALL giljo databases
                self.update_status_message("Terminating active connections...")
                for db_name in giljo_databases:
                    try:
                        cur.execute(
                            """
                            SELECT pg_terminate_backend(pg_stat_activity.pid)
                            FROM pg_stat_activity
                            WHERE pg_stat_activity.datname = %s
                              AND pid <> pg_backend_pid()
                            """,
                            (db_name,),
                        )
                    except Exception as e:
                        self.logger.warning(f"Could not terminate connections to {db_name}: {e}")

                # Step 3: Drop ALL giljo databases first (before handling roles)
                self.update_status_message("Dropping all giljo databases...")
                dropped_dbs = []
                for db_name in giljo_databases:
                    try:
                        cur.execute(f"DROP DATABASE IF EXISTS {db_name}")
                        dropped_dbs.append(db_name)
                        self.logger.info(f"Dropped database: {db_name}")
                    except Exception as e:
                        self.logger.warning(f"Could not drop database {db_name}: {e}")

                # Step 4: Now handle roles - REASSIGN and DROP OWNED in postgres context
                self.update_status_message("Resolving ownership conflicts...")
                for role in ["giljo_user", "giljo_owner"]:
                    try:
                        cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (role,))
                        if cur.fetchone():
                            # REASSIGN OWNED moves ownership to postgres
                            cur.execute(f"REASSIGN OWNED BY {role} TO postgres")
                            self.logger.info(f"Reassigned owned objects from {role}")
                    except Exception as e:
                        self.logger.warning(f"Could not reassign from {role}: {e}")

                # Step 5: Drop owned objects (CASCADE to handle dependencies)
                self.update_status_message("Dropping owned objects...")
                for role in ["giljo_user", "giljo_owner"]:
                    try:
                        cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (role,))
                        if cur.fetchone():
                            cur.execute(f"DROP OWNED BY {role} CASCADE")
                            self.logger.info(f"Dropped owned objects for {role}")
                    except Exception as e:
                        self.logger.warning(f"Could not drop owned for {role}: {e}")

                # Step 6: Finally drop roles
                self.update_status_message("Dropping database roles...")
                dropped_roles = []
                for role in ["giljo_user", "giljo_owner"]:
                    try:
                        cur.execute(f"DROP ROLE IF EXISTS {role}")
                        # Verify it's actually gone
                        cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (role,))
                        if not cur.fetchone():
                            dropped_roles.append(role)
                            self.logger.info(f"Successfully dropped role: {role}")
                        else:
                            self.logger.warning(f"Role {role} still exists after DROP")
                    except Exception as e:
                        self.logger.warning(f"Could not drop role {role}: {e}")

            conn.close()

            self.db_exists_indicator.config(foreground="red")
            self.db_exists_label.config(text="Deleted")
            self.db_exists_status.set(False)
            self.update_status_message("Database cleanup completed successfully")

            # Build detailed success message
            db_list = "\n".join(f"- {db}" for db in dropped_dbs) if dropped_dbs else "- (none found)"
            role_list = (
                "\n".join(f"- {r}" for r in dropped_roles) if dropped_roles else "- (none found or could not drop)"
            )

            messagebox.showinfo(
                "Success",
                f"Database cleanup complete!\n\n"
                f"Databases removed ({len(dropped_dbs)}):\n{db_list}\n\n"
                f"Roles removed ({len(dropped_roles)}):\n{role_list}\n\n"
                f"Data removed:\n"
                f"- {user_count} users\n"
                f"- {apikey_count} API keys\n"
                f"- All projects, agents, tasks, and data",
            )
            return True

        except Exception as e:
            self.update_status_message(f"psycopg2 deletion failed: {e}")
            print(f"psycopg2 error: {e}")
            return False

    def _get_pg_install_hint(self) -> str:
        """Return platform-specific PostgreSQL installation hint."""
        system = platform.system()
        if system == "Windows":
            return (
                "Searched:\n"
                "- PATH environment variable\n"
                "- C:\\Program Files\\PostgreSQL\\*\\bin\\\n\n"
                "Please ensure PostgreSQL is installed."
            )
        elif system == "Darwin":
            return (
                "Searched:\n"
                "- PATH environment variable\n"
                "- Homebrew (/opt/homebrew/bin, /usr/local/bin)\n"
                "- /Library/PostgreSQL/*/bin/\n\n"
                "Install with: brew install postgresql"
            )
        else:
            return (
                "Searched:\n"
                "- PATH environment variable\n"
                "- /usr/bin/, /usr/local/bin/\n"
                "- /usr/lib/postgresql/*/bin/\n\n"
                "Install with: sudo apt install postgresql"
            )

    def _find_psql_path(self) -> Optional[str]:
        """
        Find psql path (cross-platform).

        Search order:
        1. PATH environment variable
        2. Common platform-specific PostgreSQL installation locations

        Returns:
            Path to psql if found, None otherwise
        """

        # Method 1: Check PATH
        psql_in_path = shutil.which("psql")
        if psql_in_path:
            self.logger.info(f"Found psql in PATH: {psql_in_path}")
            return psql_in_path

        # Method 2: Scan platform-specific locations
        system = platform.system()
        search_locations = []

        if system == "Windows":
            search_locations = [
                Path("C:/Program Files/PostgreSQL"),
                Path("C:/Program Files (x86)/PostgreSQL"),
            ]
        elif system == "Darwin":  # macOS
            search_locations = [
                Path("/Library/PostgreSQL"),
                Path("/opt/homebrew/opt/postgresql/bin").parent.parent,
                Path("/usr/local/opt/postgresql/bin").parent.parent,
            ]
            # Check Homebrew directly
            for brew_path in [
                Path("/opt/homebrew/bin/psql"),
                Path("/usr/local/bin/psql"),
            ]:
                if brew_path.exists():
                    self.logger.info(f"Found psql at: {brew_path}")
                    return str(brew_path)
        else:  # Linux
            for linux_path in [
                Path("/usr/bin/psql"),
                Path("/usr/local/bin/psql"),
                Path("/usr/lib/postgresql"),
            ]:
                if linux_path.name == "psql" and linux_path.exists():
                    self.logger.info(f"Found psql at: {linux_path}")
                    return str(linux_path)
                elif linux_path.is_dir():
                    # Scan /usr/lib/postgresql/*/bin/psql
                    for version_dir in sorted(linux_path.glob("*"), reverse=True):
                        psql_path = version_dir / "bin" / "psql"
                        if psql_path.exists():
                            self.logger.info(f"Found psql at: {psql_path}")
                            return str(psql_path)

        psql_name = "psql.exe" if system == "Windows" else "psql"
        for base in search_locations:
            if base.exists():
                # Sort versions in reverse order (newest first: 18, 17, 16, etc.)
                for version_dir in sorted(base.glob("*"), reverse=True):
                    if version_dir.is_dir():
                        psql_path = version_dir / "bin" / psql_name
                        if psql_path.exists():
                            self.logger.info(f"Found psql at: {psql_path}")
                            return str(psql_path)

        self.logger.warning("Could not find psql in PATH or common locations")
        return None

    def _find_pg_dump_path(self) -> Optional[str]:
        """
        Find pg_dump path (cross-platform).

        Search order:
        1. PATH environment variable
        2. Common platform-specific PostgreSQL installation locations

        Returns:
            Path to pg_dump if found, None otherwise
        """

        # Method 1: Check PATH
        pg_dump_in_path = shutil.which("pg_dump")
        if pg_dump_in_path:
            self.logger.info(f"Found pg_dump in PATH: {pg_dump_in_path}")
            return pg_dump_in_path

        # Method 2: Scan platform-specific locations
        system = platform.system()
        search_locations = []

        if system == "Windows":
            search_locations = [
                Path("C:/Program Files/PostgreSQL"),
                Path("C:/Program Files (x86)/PostgreSQL"),
            ]
        elif system == "Darwin":  # macOS
            search_locations = [
                Path("/Library/PostgreSQL"),
            ]
            for brew_path in [
                Path("/opt/homebrew/bin/pg_dump"),
                Path("/usr/local/bin/pg_dump"),
            ]:
                if brew_path.exists():
                    self.logger.info(f"Found pg_dump at: {brew_path}")
                    return str(brew_path)
        else:  # Linux
            for linux_path in [
                Path("/usr/bin/pg_dump"),
                Path("/usr/local/bin/pg_dump"),
                Path("/usr/lib/postgresql"),
            ]:
                if linux_path.name == "pg_dump" and linux_path.exists():
                    self.logger.info(f"Found pg_dump at: {linux_path}")
                    return str(linux_path)
                elif linux_path.is_dir():
                    for version_dir in sorted(linux_path.glob("*"), reverse=True):
                        pg_dump_path = version_dir / "bin" / "pg_dump"
                        if pg_dump_path.exists():
                            self.logger.info(f"Found pg_dump at: {pg_dump_path}")
                            return str(pg_dump_path)

        bin_name = "pg_dump.exe" if system == "Windows" else "pg_dump"
        for base in search_locations:
            if base.exists():
                for version_dir in sorted(base.glob("*"), reverse=True):
                    if version_dir.is_dir():
                        pg_dump_path = version_dir / "bin" / bin_name
                        if pg_dump_path.exists():
                            self.logger.info(f"Found pg_dump at: {pg_dump_path}")
                            return str(pg_dump_path)

        self.logger.warning("Could not find pg_dump in PATH or common locations")
        return None

    def _delete_database_with_psql_cli(self) -> bool:
        """
        Delete database using psql command-line (fallback method).

        This method:
        1. Finds psql (PATH or common platform-specific locations)
        2. Uses PGPASSWORD environment variable (from .env or prompt)
        3. Runs the same SQL sequence as psycopg2 method
        4. Includes User/ApiKey counting via DO block with RAISE NOTICE

        Returns:
            True if successful, False otherwise
        """
        self.update_status_message("Using psql command-line fallback...")

        # Find psql first
        psql_path = self._find_psql_path()
        if not psql_path:
            self.update_status_message("psql not found")
            messagebox.showerror(
                "Error",
                "psql not found!\n\n"
                "Could not find PostgreSQL command-line tools.\n\n"
                + self._get_pg_install_hint()
            )
            return False

        self.update_status_message(f"Found psql at: {psql_path}")

        # Get credentials (reads from .env or prompts)
        credentials = self.get_db_credentials()
        if not credentials.get("password"):
            messagebox.showerror("Error", "No PostgreSQL password provided.")
            return False

        try:
            # First, audit User/ApiKey counts via psql
            user_count = 0
            apikey_count = 0

            import tempfile

            audit_sql = """
-- Audit User/ApiKey counts
DO $$
DECLARE
    user_count INT;
    apikey_count INT;
BEGIN
    BEGIN
        SELECT COUNT(*) INTO user_count FROM users;
        SELECT COUNT(*) INTO apikey_count FROM api_keys;
        RAISE NOTICE 'Deleting % users and % API keys', user_count, apikey_count;
    EXCEPTION WHEN OTHERS THEN
        RAISE NOTICE 'Could not count users/API keys (tables may not exist)';
    END;
END $$;
"""

            with tempfile.NamedTemporaryFile(mode="w", suffix=".sql", delete=False) as f:
                f.write(audit_sql)
                audit_file = f.name

            try:
                env = os.environ.copy()
                env["PGPASSWORD"] = credentials["password"]

                # Run audit against giljo_mcp database
                audit_result = subprocess.run(
                    [psql_path, "-U", "postgres", "-h", "localhost", "-p", "5432", "-d", "giljo_mcp", "-f", audit_file],
                    check=False,
                    capture_output=True,
                    text=True,
                    env=env,
                    timeout=10,
                )

                # Parse NOTICE output for counts
                if audit_result.returncode == 0 and "Deleting" in audit_result.stderr:
                    import re

                    match = re.search(r"Deleting (\d+) users and (\d+) API keys", audit_result.stderr)
                    if match:
                        user_count = int(match.group(1))
                        apikey_count = int(match.group(2))
                        self.logger.info(f"Found {user_count} users and {apikey_count} API keys to delete")
            except Exception as e:
                self.logger.warning(f"Could not audit database via psql: {e}")
            finally:
                if os.path.exists(audit_file):
                    os.unlink(audit_file)

            # SQL commands to execute (deletion sequence)
            sql_commands = """
-- Terminate connections
SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'giljo_mcp' AND pid <> pg_backend_pid();

-- Reassign owned objects
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'giljo_user') THEN
        REASSIGN OWNED BY giljo_user TO postgres;
    END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'giljo_owner') THEN
        REASSIGN OWNED BY giljo_owner TO postgres;
    END IF;
END $$;

-- Drop owned objects
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'giljo_user') THEN
        DROP OWNED BY giljo_user CASCADE;
    END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'giljo_owner') THEN
        DROP OWNED BY giljo_owner CASCADE;
    END IF;
END $$;

-- Drop roles
DROP ROLE IF EXISTS giljo_user;
DROP ROLE IF EXISTS giljo_owner;

-- Drop database
DROP DATABASE IF EXISTS giljo_mcp;
"""

            # Write SQL to temp file
            with tempfile.NamedTemporaryFile(mode="w", suffix=".sql", delete=False) as f:
                f.write(sql_commands)
                sql_file = f.name

            try:
                # Execute psql with password in environment
                env = os.environ.copy()
                env["PGPASSWORD"] = credentials["password"]

                result = subprocess.run(
                    [psql_path, "-U", "postgres", "-h", "localhost", "-p", "5432", "-d", "postgres", "-f", sql_file],
                    check=False,
                    capture_output=True,
                    text=True,
                    env=env,
                    timeout=30,
                )

                # Clean up temp file
                os.unlink(sql_file)

                if result.returncode == 0:
                    self.db_exists_indicator.config(foreground="red")
                    self.db_exists_label.config(text="Deleted")
                    self.db_exists_status.set(False)
                    self.update_status_message("Database deleted via psql CLI")
                    messagebox.showinfo(
                        "Success",
                        "Database deletion complete (using psql CLI)!\n\n"
                        "Removed:\n"
                        "- giljo_mcp database\n"
                        f"- {user_count} users\n"
                        f"- {apikey_count} API keys\n"
                        "- giljo_user role\n"
                        "- giljo_owner role\n"
                        "- All projects, agents, tasks, and data",
                    )
                    return True
                raise Exception(f"psql failed: {result.stderr}")

            finally:
                # Ensure temp file is cleaned up
                if os.path.exists(sql_file):
                    os.unlink(sql_file)

        except Exception as e:
            self.update_status_message(f"psql CLI deletion failed: {e}")
            messagebox.showerror("Error", f"Database deletion failed:\n\n{e}")
            return False

        return False  # Should not reach here, but be safe

    def check_last_backup(self):
        """
        Check for the last database backup and update status indicator.

        Looks in docs/archive/database_backups/ for the most recent backup file.
        """
        try:
            backup_dir = self.project_root / "docs" / "archive" / "database_backups"

            if not backup_dir.exists():
                self.backup_label.config(text="No backups found")
                self.backup_indicator.config(foreground="gray")
                return

            # Find all .dump files (backup files)
            dump_files = list(backup_dir.glob("*.dump"))

            if not dump_files:
                self.backup_label.config(text="No backups found")
                self.backup_indicator.config(foreground="gray")
                return

            # Get the most recent file by modification time
            latest_backup = max(dump_files, key=lambda p: p.stat().st_mtime)

            # Format the timestamp
            mod_time = latest_backup.stat().st_mtime
            from datetime import datetime

            backup_time = datetime.fromtimestamp(mod_time).strftime("%Y-%m-%d %H:%M:%S")

            self.backup_label.config(text=backup_time)
            self.backup_indicator.config(foreground="green")

        except Exception as e:
            self.logger.warning(f"Could not check last backup: {e}")
            self.backup_label.config(text="Error checking backups")
            self.backup_indicator.config(foreground="red")

    def backup_database(self):
        """
        Backup the giljo_mcp database using pg_dump.

        Creates a timestamped backup file in docs/archive/database_backups/
        and generates a metadata .md file with backup information.
        """
        self.update_status_message("Backing up database...")

        try:
            # Create backup directory if it doesn't exist
            backup_dir = self.project_root / "docs" / "archive" / "database_backups"
            backup_dir.mkdir(parents=True, exist_ok=True)

            # Create timestamped backup filename
            from datetime import datetime

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = backup_dir / f"giljo_mcp_{timestamp}.dump"
            metadata_file = backup_dir / f"giljo_mcp_{timestamp}.md"

            # Get database credentials
            credentials = self.get_db_credentials()

            # Find pg_dump executable
            pg_dump_path = self._find_pg_dump_path()
            if not pg_dump_path:
                self.update_status_message("pg_dump not found")
                messagebox.showerror(
                    "Error",
                    "pg_dump not found!\n\n"
                    "Could not find PostgreSQL command-line tools.\n\n"
                    + self._get_pg_install_hint(),
                )
                return

            self.update_status_message(f"Found pg_dump at: {pg_dump_path}")

            # Build pg_dump command
            # Using -Fc format (custom format) for better compression and restore options
            env = os.environ.copy()
            env["PGPASSWORD"] = credentials["password"]

            command = [
                pg_dump_path,
                "-h",
                credentials["host"],
                "-p",
                str(credentials["port"]),
                "-U",
                credentials["user"],
                "-Fc",  # Custom format (compressed)
                "-v",  # Verbose
                "giljo_mcp",
            ]

            self.update_status_message("Running pg_dump (this may take a moment)...")

            # Run pg_dump
            result = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
                env=env,
                timeout=300,  # 5 minute timeout
            )

            if result.returncode != 0:
                raise Exception(f"pg_dump failed: {result.stderr}")

            # Write dump output to file
            with open(backup_file, "wb") as f:
                # Re-run pg_dump to get binary output
                result = subprocess.run(command, check=False, capture_output=True, env=env, timeout=300)
                if result.returncode != 0:
                    raise Exception(f"pg_dump failed: {result.stderr.decode()}")
                f.write(result.stdout)

            # Get backup file size
            backup_size = backup_file.stat().st_size
            size_mb = backup_size / (1024 * 1024)

            # Create metadata file
            metadata_content = f"""# Database Backup Metadata

**Backup Date**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Database**: giljo_mcp
**Format**: PostgreSQL Custom Format (pg_dump -Fc)
**File**: {backup_file.name}
**Size**: {size_mb:.2f} MB

## Backup Information

- **Host**: {credentials["host"]}
- **Port**: {credentials["port"]}
- **User**: {credentials["user"]}
- **Database**: giljo_mcp

## Restore Instructions

To restore this backup, use pg_restore:

```bash
pg_restore -h {credentials["host"]} -p {credentials["port"]} -U {credentials["user"]} -d giljo_mcp {backup_file.name}
```

Or with password prompt:
```bash
PGPASSWORD=<password> pg_restore -h {credentials["host"]} -p {credentials["port"]} -U {credentials["user"]} -d giljo_mcp {backup_file.name}
```

## Notes

- Backup created using pg_dump with custom format (-Fc)
- Custom format provides compression and parallel restore capability
- To restore, you must have an existing giljo_mcp database
- To restore to a fresh system, first create the database and roles

## Verification

To verify the backup integrity:

```bash
pg_restore -l {backup_file.name} | head -20
```
"""

            with open(metadata_file, "w") as f:
                f.write(metadata_content)

            # Update status
            self.check_last_backup()
            self.update_status_message(f"Database backup completed successfully ({size_mb:.2f} MB)")

            messagebox.showinfo(
                "Backup Successful",
                f"Database backup completed successfully!\n\n"
                f"Backup File: {backup_file.name}\n"
                f"Size: {size_mb:.2f} MB\n"
                f"Location: docs/archive/database_backups/\n\n"
                f"Metadata file created: {metadata_file.name}",
            )

        except FileNotFoundError as e:
            self.update_status_message("pg_dump not found in PATH")
            messagebox.showerror(
                "Error",
                "pg_dump not found!\n\n"
                "PostgreSQL command-line tools must be in PATH.\n"
                "Make sure PostgreSQL is properly installed.\n\n"
                f"Details: {e}",
            )

        except subprocess.TimeoutExpired:
            self.update_status_message("Backup timeout (exceeded 5 minutes)")
            messagebox.showerror(
                "Error",
                "Backup timeout!\n\n"
                "The database backup took too long (> 5 minutes).\n"
                "This may indicate a very large database or system issues.",
            )

        except Exception as e:
            self.update_status_message(f"Backup failed: {e}")
            messagebox.showerror(
                "Error",
                f"Database backup failed:\n\n{e}\n\n"
                "Make sure:\n"
                "1. PostgreSQL is running\n"
                "2. giljo_mcp database exists\n"
                "3. You have permission to read the database\n"
                "4. pg_dump is in your PATH",
            )

    def verify_fresh_state(self) -> dict[str, bool]:
        """
        Verify system is in true "fresh download" state.

        Checks all components that should be deleted after reset:
        - Virtual environment (venv/)
        - Configuration files (config.yaml, .env, install_config.yaml)
        - Database (giljo_mcp)
        - PostgreSQL roles (giljo_user, giljo_owner)

        Returns:
            Dict mapping component name to is_clean boolean
            - True: Component is clean (deleted/doesn't exist)
            - False: Component still exists (NOT CLEAN)
            - None: Cannot verify (missing dependencies)
        """
        checks = {}

        # Check venv deleted (check both .venv and venv)
        venv_exists = (self.project_root / ".venv").exists() or (self.project_root / "venv").exists()
        checks["venv"] = not venv_exists

        # Check config files deleted
        checks["config.yaml"] = not (self.project_root / "config.yaml").exists()
        checks[".env"] = not (self.project_root / ".env").exists()
        checks["install_config.yaml"] = not (self.project_root / "install_config.yaml").exists()

        # Check database deleted (try psycopg2 first, fallback to psql CLI)
        db_verified = False

        if psycopg2:
            try:
                credentials = self.get_db_credentials()
                conn = psycopg2.connect(
                    host=credentials["host"],
                    port=credentials["port"],
                    database="postgres",
                    user=credentials["user"],
                    password=credentials["password"],
                    connect_timeout=5,
                )

                with conn.cursor() as cur:
                    # Check if giljo_mcp database exists
                    cur.execute("SELECT 1 FROM pg_database WHERE datname = 'giljo_mcp'")
                    checks["database"] = cur.fetchone() is None

                    # Check if roles exist
                    cur.execute("""
                        SELECT 1 FROM pg_roles
                        WHERE rolname IN ('giljo_user', 'giljo_owner')
                    """)
                    checks["roles"] = cur.fetchone() is None

                conn.close()
                db_verified = True
            except Exception as e:
                print(f"Warning: psycopg2 verification failed: {e}")

        # Fallback to psql CLI if psycopg2 unavailable or failed
        if not db_verified:
            psql_path = self._find_psql_path()
            if psql_path:
                try:
                    credentials = self.get_db_credentials()
                    env = os.environ.copy()
                    env["PGPASSWORD"] = credentials.get("password", "")

                    # Check if database exists
                    db_result = subprocess.run(
                        [
                            psql_path,
                            "-U",
                            "postgres",
                            "-h",
                            "localhost",
                            "-p",
                            "5432",
                            "-d",
                            "postgres",
                            "-t",
                            "-c",
                            "SELECT 1 FROM pg_database WHERE datname = 'giljo_mcp'",
                        ],
                        capture_output=True,
                        text=True,
                        env=env,
                        timeout=10,
                        check=False,
                    )
                    # If output is empty (just whitespace), database doesn't exist
                    checks["database"] = db_result.stdout.strip() == ""

                    # Check if roles exist
                    roles_result = subprocess.run(
                        [
                            psql_path,
                            "-U",
                            "postgres",
                            "-h",
                            "localhost",
                            "-p",
                            "5432",
                            "-d",
                            "postgres",
                            "-t",
                            "-c",
                            "SELECT 1 FROM pg_roles WHERE rolname IN ('giljo_user', 'giljo_owner')",
                        ],
                        capture_output=True,
                        text=True,
                        env=env,
                        timeout=10,
                        check=False,
                    )
                    checks["roles"] = roles_result.stdout.strip() == ""
                    db_verified = True
                except Exception as e:
                    print(f"Warning: psql CLI verification failed: {e}")

        # If both methods failed, mark as unverifiable
        if not db_verified:
            checks["database"] = None
            checks["roles"] = None

        # Check Python cache deleted
        cache_clean = True
        cache_dirs = [".pytest_cache", ".ruff_cache", ".mypy_cache", "htmlcov", ".hypothesis", ".tox", ".nox"]
        for cache_dir in cache_dirs:
            if (self.project_root / cache_dir).exists():
                cache_clean = False
                break

        # Check for any __pycache__ directories
        pycache_exists = any(self.project_root.rglob("__pycache__"))

        checks["python_cache"] = cache_clean and not pycache_exists

        # Check frontend test cache deleted
        frontend_cache_clean = True
        frontend_caches = [
            self.project_root / "frontend" / ".vitest",
            self.project_root / "frontend" / "coverage",
            self.project_root / "frontend" / "playwright-report",
            self.project_root / "frontend" / "test-results",
        ]
        for cache_path in frontend_caches:
            if cache_path.exists():
                frontend_cache_clean = False
                break

        checks["frontend_cache"] = frontend_cache_clean

        return checks

    def display_fresh_state_report(self):
        """
        Display fresh state verification report in GUI dialog.

        Shows status of each component:
        - ✓ Clean: Component deleted/doesn't exist
        - ✗ NOT CLEAN: Component still exists
        - ⚠ Cannot verify: Missing dependencies or check failed
        """
        self.update_status_message("Verifying fresh state...")

        checks = self.verify_fresh_state()

        # Build report text
        report = "Fresh State Verification:\n\n"

        all_clean = True
        cannot_verify = []
        not_clean = []

        for component, is_clean in checks.items():
            if is_clean is None:
                status = "⚠ Cannot verify"
                cannot_verify.append(component)
            elif is_clean:
                status = "✓ Clean"
            else:
                status = "✗ NOT CLEAN"
                not_clean.append(component)
                all_clean = False

            report += f"{status} - {component}\n"

        # Add summary
        report += "\n"
        if all_clean and not cannot_verify:
            report += "✓ System is in fresh download state!"
        elif not_clean:
            report += f"✗ {len(not_clean)} component(s) need cleanup:\n"
            for comp in not_clean:
                report += f"  - {comp}\n"

        if cannot_verify:
            report += f"\n⚠ Could not verify {len(cannot_verify)} component(s):\n"
            for comp in cannot_verify:
                report += f"  - {comp}\n"

        self.update_status_message("Fresh state verification complete")
        messagebox.showinfo("Fresh State Report", report)

    # Development Reset Methods

    def reset_to_fresh(self):
        """
        Reset to fresh state for testing setup flow.

        Resets the dev admin user (patrik) to dev credentials (***REMOVED***)
        and sets must_change_password=True so you can test the password
        change flow without reinstalling.

        Does NOT delete venv or configs - only resets authentication state.
        """
        # Confirmation dialog
        confirm = messagebox.askyesno(
            "Confirm Reset to Fresh State",
            "This will reset the dev admin user for testing setup flow:\n\n"
            "- Reset 'patrik' password to '***REMOVED***'\n"
            "- Set must_change_password = True\n"
            "- Set must_set_pin = True\n"
            "- Clear recovery PIN\n\n"
            "This allows you to test:\n"
            "1. Password change flow (forced on login)\n"
            "2. Recovery PIN setup flow\n"
            "3. Complete onboarding experience\n\n"
            "WITHOUT reinstalling the application!\n\n"
            "Continue?",
            icon="question",
        )

        if not confirm:
            return

        self.update_status_message("Resetting dev admin user to test state...")

        # Reset admin user in database
        if psycopg2 is None:
            messagebox.showerror(
                "Missing Dependency", "psycopg2 is not installed.\n\nInstall with: pip install psycopg2"
            )
            return

        try:
            credentials = self.get_db_credentials()
            conn = psycopg2.connect(
                host=credentials["host"],
                port=credentials["port"],
                user=credentials["user"],
                password=credentials["password"],
                database="giljo_mcp",
                connect_timeout=5,
            )
            conn.autocommit = True

            with conn.cursor() as cur:
                # Step 1: Reset dev admin user password and set flags
                self.update_status_message("Resetting patrik password to dev credentials...")
                # This is the bcrypt hash for '***REMOVED***'
                dev_admin_hash = "$2b$12$ax7nbk8fPDnQjbgj3Cz9fe4h1bM7MDUiS9UQ0i3ZeJW8GvCVE3VGa"

                cur.execute(
                    """
                    UPDATE users
                    SET password_hash = %s,
                        must_change_password = TRUE,
                        must_set_pin = TRUE,
                        recovery_pin_hash = NULL,
                        failed_pin_attempts = 0,
                        pin_lockout_until = NULL
                    WHERE username = 'patrik'
                """,
                    (dev_admin_hash,),
                )

                # Check if update was successful
                if cur.rowcount == 0:
                    raise Exception("User 'patrik' not found in database")

            conn.close()

            self.update_status_message("Reset complete - ready for testing!")
            messagebox.showinfo(
                "Reset Complete",
                "Dev admin user reset successfully!\n\n"
                "You can now test the setup flow:\n\n"
                "1. Visit http://localhost:7274\n"
                "2. Login with patrik / ***REMOVED***\n"
                "3. Change password (forced)\n"
                "4. Set recovery PIN (forced)\n\n"
                "No reinstallation needed!",
            )

        except Exception as e:
            self.update_status_message(f"Reset failed: {e}")
            messagebox.showerror(
                "Reset Failed",
                f"Failed to reset dev admin user:\n\n{e}\n\n"
                "Make sure:\n"
                "1. PostgreSQL is running\n"
                "2. giljo_mcp database exists\n"
                "3. User 'patrik' exists in database",
            )

    def reset_to_pristine(self):
        """
        Comprehensive reset to pristine "fresh GitHub download" state.

        Deletes:
        - Configuration files (config.yaml, .env, install_config.yaml)
        - Virtual environment (.venv/ or venv/)
        - Database (giljo_mcp) with all tables and roles
        - Logs directory (logs/)
        - Data directory (data/)
        - Frontend build artifacts and dependencies (dist/, node_modules/)

        This provides the most complete reset, simulating a truly fresh
        installation experience.
        """
        # Confirmation dialog with comprehensive list
        confirm = messagebox.askyesno(
            "Confirm Pristine Reset",
            "This will DELETE everything to simulate a fresh GitHub download:\n\n"
            "Configuration & Environment:\n"
            "- Virtual environment (.venv/ or venv/)\n"
            "- Configuration files (config.yaml, .env)\n"
            "- Installer config (install_config.yaml)\n\n"
            "Python & Test Caches:\n"
            "- Python bytecode cache (__pycache__/)\n"
            "- Pytest, Ruff, MyPy, Coverage caches\n"
            "- All test cache directories\n\n"
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
            "- All npm dependencies (frontend/node_modules/)\n"
            "- Frontend test caches (Vitest, Playwright)\n\n"
            "⚠ This action CANNOT be undone!\n\n"
            "Continue?",
            icon="warning",
        )

        if not confirm:
            self.update_status_message("Pristine reset cancelled")
            return

        self.update_status_message("Starting pristine reset...")

        errors = []
        deleted = []

        # Step 1: Delete configuration files and venv
        try:
            self.update_status_message("Step 1/6: Deleting configuration files and venv...")

            targets = [
                (self.project_root / ".venv", "Virtual environment (.venv)"),
                (self.project_root / "venv", "Virtual environment (venv)"),  # Legacy fallback
                (self.project_root / "config.yaml", "Configuration file"),
                (self.project_root / ".env", "Environment file"),
                (self.project_root / "install_config.yaml", "Installer config"),
            ]

            for target, desc in targets:
                if target.exists():
                    try:
                        if target.is_dir():
                            if target.name in ("venv", ".venv"):
                                success = self._aggressive_delete_venv(target)
                                if success:
                                    deleted.append(desc)
                                else:
                                    errors.append(f"{desc}: Failed to delete")
                            else:
                                import shutil

                                shutil.rmtree(target)
                                deleted.append(desc)
                        else:
                            target.unlink()
                            deleted.append(desc)
                    except Exception as e:
                        errors.append(f"{desc}: {e}")

        except Exception as e:
            errors.append(f"Configuration cleanup: {e}")

        # Step 1.5: Delete Python cache files (CRITICAL for fresh install)
        try:
            import shutil  # Local import for this scope

            self.update_status_message("Step 1.5/7: Cleaning Python cache files...")

            cache_targets = [
                (self.project_root / ".pytest_cache", "Pytest cache"),
                (self.project_root / ".ruff_cache", "Ruff linter cache"),
                (self.project_root / ".mypy_cache", "MyPy cache"),
                (self.project_root / "htmlcov", "Coverage HTML reports"),
                (self.project_root / ".hypothesis", "Hypothesis cache"),
                (self.project_root / ".tox", "Tox cache"),
                (self.project_root / ".nox", "Nox cache"),
            ]

            for target, desc in cache_targets:
                if target.exists():
                    try:
                        if target.is_dir():
                            shutil.rmtree(target, ignore_errors=True)
                        else:
                            target.unlink()
                        deleted.append(desc)
                    except Exception as e:
                        errors.append(f"{desc}: {e}")

            # Recursively delete all __pycache__ directories
            pycache_count = 0
            for pycache in self.project_root.rglob("__pycache__"):
                try:
                    shutil.rmtree(pycache, ignore_errors=True)
                    pycache_count += 1
                except Exception:
                    pass

            if pycache_count > 0:
                deleted.append(f"Python bytecode cache ({pycache_count} directories)")

            # Delete .coverage and .coverage.* files
            coverage_file = self.project_root / ".coverage"
            if coverage_file.exists():
                try:
                    coverage_file.unlink()
                    deleted.append("Coverage data file")
                except Exception:
                    pass

            coverage_count = 0
            for cov_file in self.project_root.glob(".coverage.*"):
                try:
                    cov_file.unlink()
                    coverage_count += 1
                except Exception:
                    pass

            if coverage_count > 0:
                deleted.append(f"Coverage parallel files ({coverage_count} files)")

        except Exception as e:
            errors.append(f"Python cache cleanup: {e}")

        # Step 3: Delete database (with fallback)
        try:
            self.update_status_message("Step 3/7: Deleting database...")

            db_deleted = False

            # Try psycopg2 first if available
            if psycopg2:
                db_deleted = self._delete_database_with_psycopg2()
                if not db_deleted:
                    self.update_status_message("psycopg2 failed, trying psql CLI fallback...")

            # Fallback to psql CLI if psycopg2 unavailable or failed
            if not db_deleted:
                db_deleted = self._delete_database_with_psql_cli()

            if db_deleted:
                deleted.append("Database (giljo_mcp)")
                deleted.append("PostgreSQL roles")
            else:
                errors.append("Database deletion failed (both psycopg2 and psql CLI)")

        except Exception as e:
            errors.append(f"Database deletion: {e}")

        # Step 4: Delete logs directory
        try:
            self.update_status_message("Step 4/7: Cleaning logs directory...")

            logs_dir = self.project_root / "logs"
            if logs_dir.exists():
                import shutil

                shutil.rmtree(logs_dir, ignore_errors=True)
                deleted.append("Logs directory")

        except Exception as e:
            errors.append(f"Logs cleanup: {e}")

        # Step 5: Delete data directory
        try:
            self.update_status_message("Step 5/7: Cleaning data directory...")

            data_dir = self.project_root / "data"
            if data_dir.exists():
                import shutil

                shutil.rmtree(data_dir, ignore_errors=True)
                deleted.append("Data directory")

        except Exception as e:
            errors.append(f"Data cleanup: {e}")

        # Step 6: Delete session memories
        try:
            self.update_status_message("Step 6/7: Cleaning session memories...")

            sessions_dir = self.project_root / "docs" / "sessions"
            if sessions_dir.exists():
                import shutil

                shutil.rmtree(sessions_dir, ignore_errors=True)
                deleted.append("Session memories")

        except Exception as e:
            errors.append(f"Session cleanup: {e}")

        # Step 7: Delete frontend build artifacts and dependencies
        try:
            self.update_status_message("Step 7/7: Cleaning frontend artifacts and dependencies...")

            frontend_targets = [
                (self.project_root / "frontend" / "dist", "Frontend build output"),
                (self.project_root / "frontend" / "node_modules", "Node.js dependencies (complete)"),
                (self.project_root / "frontend" / ".vitest", "Vitest cache"),
                (self.project_root / "frontend" / "coverage", "Frontend coverage"),
                (self.project_root / "frontend" / "playwright-report", "Playwright reports"),
                (self.project_root / "frontend" / "test-results", "Playwright test results"),
            ]

            for target, desc in frontend_targets:
                if target.exists():
                    import shutil

                    shutil.rmtree(target, ignore_errors=True)
                    deleted.append(desc)

        except Exception as e:
            errors.append(f"Frontend cleanup: {e}")

        # Final verification
        self.update_status_message("Verifying pristine state...")
        time.sleep(1)

        # Build result message
        if errors:
            error_msg = "\n".join(errors)
            messagebox.showwarning(
                "Pristine Reset Partial Success",
                f"Pristine reset completed with errors:\n\n"
                f"Deleted ({len(deleted)} items):\n"
                + "\n".join(f"✓ {d}" for d in deleted[:5])
                + (f"\n  ... and {len(deleted) - 5} more" if len(deleted) > 5 else "")
                + f"\n\nErrors ({len(errors)}):\n{error_msg[:200]}"
                + ("..." if len(error_msg) > 200 else "")
                + "\n\nYou may need to manually delete remaining items.",
            )
        else:
            messagebox.showinfo(
                "Pristine Reset Complete",
                f"System reset to pristine state!\n\n"
                f"Deleted {len(deleted)} components:\n"
                + "\n".join(f"✓ {d}" for d in deleted[:8])
                + (f"\n  ... and {len(deleted) - 8} more" if len(deleted) > 8 else "")
                + "\n\nYou can now run 'python install.py' to set up from scratch.\n\n"
                "This simulates a fresh GitHub download.",
            )

        # Display fresh state verification
        self.display_fresh_state_report()

        self.update_status_message("Pristine reset complete")

    def _aggressive_delete_venv(self, venv_path: Path) -> bool:
        """
        Aggressively delete venv directory using Windows commands.

        Uses rmdir /s /q on Windows for better handling of locked files.
        Falls back to shutil.rmtree with retry logic.

        Args:
            venv_path: Path to venv directory

        Returns:
            True if successful, False otherwise
        """
        import time

        system = platform.system()

        if system == "Windows":
            # Method 1: Try Windows rmdir command (most aggressive)
            try:
                self.update_status_message("Deleting venv (using Windows rmdir)...")
                result = subprocess.run(
                    ["cmd", "/c", "rmdir", "/s", "/q", str(venv_path)], check=False, capture_output=True, timeout=30
                )
                if result.returncode == 0:
                    return True
            except Exception as e:
                print(f"rmdir failed: {e}")

            # Method 2: Try Python shutil with retry
            try:
                self.update_status_message("Deleting venv (using Python with retry)...")

                def retry_rmtree(path, max_retries=3):
                    """Retry deletion with delays for locked files."""
                    for attempt in range(max_retries):
                        try:
                            shutil.rmtree(path)
                            return True
                        except PermissionError:
                            if attempt < max_retries - 1:
                                time.sleep(1)  # Wait for files to unlock
                                continue
                            raise
                    return False

                if retry_rmtree(venv_path):
                    return True
            except Exception as e:
                print(f"shutil.rmtree failed: {e}")

            # Method 3: Rename then delete (Windows workaround for locked files)
            try:
                self.update_status_message("Deleting venv (rename-then-delete workaround)...")
                temp_name = venv_path.parent / f"_venv_delete_{int(time.time())}"
                venv_path.rename(temp_name)
                time.sleep(0.5)

                # Try Windows rmdir on renamed directory
                result = subprocess.run(
                    ["cmd", "/c", "rmdir", "/s", "/q", str(temp_name)], check=False, capture_output=True, timeout=30
                )
                if result.returncode == 0:
                    return True

                # If still exists, try shutil on renamed dir
                if temp_name.exists():
                    shutil.rmtree(temp_name, ignore_errors=True)

                return not temp_name.exists()
            except Exception as e:
                print(f"Rename-then-delete failed: {e}")
                return False

        else:
            # Linux/macOS: Standard shutil.rmtree should work
            try:
                shutil.rmtree(venv_path)
                return True
            except Exception as e:
                print(f"Failed to delete venv: {e}")
                return False

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

    def clear_project_staging(self):
        """
        Clear AI-generated staging data for a project.

        Removes:
        - AI-generated mission
        - ALL agent jobs (any status)
        - Tasks
        - Messages
        - Context indexes
        - Large document indexes
        - Sessions
        - Visions
        - Orchestrator summary
        - Context tracking
        - Staging status

        Keeps:
        - Project name
        - Project description
        - Metadata (human-entered data)

        Updated in Handover 0329 to include all cascade-deleted tables.
        """
        if psycopg2 is None:
            messagebox.showerror(
                "Missing Dependency", "psycopg2 is not installed.\n\nInstall with: pip install psycopg2"
            )
            return

        # Get project UUID from entry field
        project_uuid = self.project_uuid_entry.get().strip()

        if not project_uuid:
            messagebox.showwarning("Missing UUID", "Please enter a project UUID")
            return

        # Validate UUID format (basic check)
        if len(project_uuid) != 36 or project_uuid.count("-") != 4:
            messagebox.showwarning(
                "Invalid UUID", "Invalid UUID format. Expected format:\nce9015f5-d521-449c-9a89-66a9055436c8"
            )
            return

        # Confirmation dialog
        confirm = messagebox.askyesno(
            "Confirm Clear Project",
            f"Clear AI-generated staging data for project?\n\n"
            f"UUID: {project_uuid}\n\n"
            "This will remove:\n"
            "✗ AI-generated mission\n"
            "✗ ALL agent jobs (any status)\n"
            "✗ Tasks\n"
            "✗ Messages\n"
            "✗ Context indexes\n"
            "✗ Large document indexes\n"
            "✗ Sessions\n"
            "✗ Visions\n"
            "✗ Orchestrator summary\n"
            "✗ Context tracking\n"
            "✗ Staging status\n\n"
            "This will keep:\n"
            "✓ Project name\n"
            "✓ Project description\n"
            "✓ Metadata\n\n"
            "Continue?",
            icon="question",
        )

        if not confirm:
            return

        self.update_status_message(f"Clearing project {project_uuid[:8]}...")

        try:
            credentials = self.get_db_credentials()
            conn = psycopg2.connect(
                host=credentials["host"],
                port=credentials["port"],
                user=credentials["user"],
                password=credentials["password"],
                database="giljo_mcp",
                connect_timeout=5,
            )
            conn.autocommit = False  # Use transaction

            with conn.cursor() as cur:
                # Step 1: Verify project exists
                self.update_status_message("Verifying project exists...")
                cur.execute("SELECT id, name, description FROM projects WHERE id = %s", (project_uuid,))
                project_row = cur.fetchone()

                if not project_row:
                    conn.close()
                    messagebox.showerror("Project Not Found", f"No project found with UUID:\n{project_uuid}")
                    self.update_status_message("Project not found")
                    return

                project_name = project_row[1] if project_row[1] else "Unnamed Project"
                project_description = project_row[2] if project_row[2] else ""

                # Step 2: Count ALL agent jobs to delete
                self.update_status_message("Counting agent jobs to delete...")
                cur.execute(
                    """
                    SELECT COUNT(*) FROM agent_jobs
                    WHERE project_id = %s
                """,
                    (project_uuid,),
                )
                agent_count = cur.fetchone()[0]

                # Step 3: Count tasks to delete
                cur.execute("SELECT COUNT(*) FROM tasks WHERE project_id = %s", (project_uuid,))
                task_count = cur.fetchone()[0]

                # Step 4: Count messages to delete
                cur.execute("SELECT COUNT(*) FROM messages WHERE project_id = %s", (project_uuid,))
                message_count = cur.fetchone()[0]

                # Step 5: Count context indexes to delete
                cur.execute("SELECT COUNT(*) FROM context_index WHERE project_id = %s", (project_uuid,))
                context_index_count = cur.fetchone()[0]

                # Step 6: Count large document indexes to delete
                cur.execute("SELECT COUNT(*) FROM large_document_index WHERE project_id = %s", (project_uuid,))
                large_doc_count = cur.fetchone()[0]

                # Step 7: Count sessions to delete
                cur.execute("SELECT COUNT(*) FROM sessions WHERE project_id = %s", (project_uuid,))
                session_count = cur.fetchone()[0]

                # Step 8: Count visions to delete
                cur.execute("SELECT COUNT(*) FROM visions WHERE project_id = %s", (project_uuid,))
                vision_count = cur.fetchone()[0]

                # Step 9: Delete messages
                self.update_status_message(f"Deleting {message_count} messages...")
                cur.execute("DELETE FROM messages WHERE project_id = %s", (project_uuid,))

                # Step 10: Delete tasks
                self.update_status_message(f"Deleting {task_count} tasks...")
                cur.execute("DELETE FROM tasks WHERE project_id = %s", (project_uuid,))

                # Step 11: Delete ALL agent jobs and executions (any status)
                self.update_status_message(f"Deleting {agent_count} agent jobs and their executions...")
                # First delete agent_executions (referencing agent_jobs via agent_id)
                cur.execute(
                    """
                    DELETE FROM agent_executions
                    WHERE agent_id IN (
                        SELECT id FROM agent_jobs WHERE project_id = %s
                    )
                """,
                    (project_uuid,),
                )
                # Then delete agent_jobs (work orders)
                cur.execute(
                    """
                    DELETE FROM agent_jobs
                    WHERE project_id = %s
                """,
                    (project_uuid,),
                )

                # Step 12: Delete context indexes
                self.update_status_message(f"Deleting {context_index_count} context indexes...")
                cur.execute("DELETE FROM context_index WHERE project_id = %s", (project_uuid,))

                # Step 13: Delete large document indexes
                self.update_status_message(f"Deleting {large_doc_count} large document indexes...")
                cur.execute("DELETE FROM large_document_index WHERE project_id = %s", (project_uuid,))

                # Step 14: Delete sessions
                self.update_status_message(f"Deleting {session_count} sessions...")
                cur.execute("DELETE FROM sessions WHERE project_id = %s", (project_uuid,))

                # Step 15: Delete visions
                self.update_status_message(f"Deleting {vision_count} visions...")
                cur.execute("DELETE FROM visions WHERE project_id = %s", (project_uuid,))

                # Step 16: Clear project to pristine pre-staged state
                self.update_status_message("Resetting project to pre-staged state...")
                cur.execute(
                    """
                    UPDATE projects
                    SET mission = '',
                        staging_status = NULL,
                        orchestrator_summary = NULL,
                        context_used = 0,
                        context_budget = NULL,
                        activated_at = NULL,
                        paused_at = NULL,
                        completed_at = NULL,
                        closeout_prompt = NULL,
                        closeout_executed_at = NULL,
                        closeout_checklist = '[]'::jsonb,
                        meta_data = '{}',
                        updated_at = NOW()
                    WHERE id = %s
                """,
                    (project_uuid,),
                )

                # Commit transaction
                conn.commit()

            conn.close()

            self.update_status_message("Project cleared successfully")
            messagebox.showinfo(
                "Success",
                f"Project cleared to pre-staged state!\n\n"
                f"Project: {project_name}\n"
                f"UUID: {project_uuid}\n\n"
                f"Removed:\n"
                f"✗ {agent_count} agent job(s)\n"
                f"✗ {task_count} task(s)\n"
                f"✗ {message_count} message(s)\n"
                f"✗ {context_index_count} context index(es)\n"
                f"✗ {large_doc_count} large document index(es)\n"
                f"✗ {session_count} session(s)\n"
                f"✗ {vision_count} vision(s)\n"
                f"✗ AI-generated mission\n"
                f"✗ Orchestrator summary\n"
                f"✗ Context tracking\n"
                f"✗ Closeout data (prompt, checklist, execution time)\n"
                f"✗ All staging flags\n\n"
                f"Kept:\n"
                f"✓ Project name: {project_name}\n"
                f"✓ Description: {project_description[:50]}{'...' if len(project_description) > 50 else ''}\n\n"
                f"Project is now ready for fresh staging.",
            )

            # Clear the UUID entry field
            self.project_uuid_entry.delete(0, "end")

        except Exception as e:
            if conn:
                conn.rollback()
                conn.close()
            self.update_status_message(f"Clear project failed: {e}")
            messagebox.showerror(
                "Error",
                f"Failed to clear project:\n\n{e}\n\n"
                "Make sure:\n"
                "1. PostgreSQL is running\n"
                "2. giljo_mcp database exists\n"
                "3. UUID is correct",
            )

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
