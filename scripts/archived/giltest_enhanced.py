#!/usr/bin/env python3
"""
GiljoAI MCP - Complete Testing Workflow Orchestrator
=====================================================

PURPOSE:
    Provides a complete testing workflow that simulates the full user experience
    from git clone to installation to launch, with integrated cleanup options.

WORKFLOW:
    1. Copy project to test folder (simulating git clone)
    2. Run installer from test folder
    3. Launch application with start_giljo.py
    4. Provide cleanup options (devuninstall for dev, uninstall for production)

FEATURES:
    - Interactive workflow guidance
    - Automatic dependency checking
    - Error recovery suggestions
    - Both localhost and server mode support
    - Integrated with devuninstall.py and uninstall.py
"""

import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict


# Configuration
SOURCE_DIR = Path(__file__).parent
TEST_DIR = Path("C:/install_test/Giljo_MCP")
BACKUP_DIR = Path("C:/install_test/Giljo_MCP_backup")
LOG_DIR = Path("C:/install_test/logs")

# Default PostgreSQL settings for testing
DEFAULT_PG_PASSWORD = "4010"
DEFAULT_PG_HOST = "localhost"
DEFAULT_PG_PORT = "5432"


class TestWorkflowOrchestrator:
    """Orchestrates the complete testing workflow"""

    def __init__(self):
        self.source_dir = SOURCE_DIR
        self.test_dir = TEST_DIR
        self.backup_dir = BACKUP_DIR
        self.log_dir = LOG_DIR
        self.log_file = None
        self.workflow_state = {"copied": False, "installed": False, "launched": False, "cleanup_done": False}

    def setup_logging(self):
        """Initialize logging for the workflow"""
        self.log_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = self.log_dir / f"giltest_{timestamp}.log"

    def log(self, message: str, level: str = "INFO"):
        """Log message to both console and file"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}"

        print(log_entry)
        if self.log_file:
            with open(self.log_file, "a") as f:
                f.write(log_entry + "\n")

    def print_header(self):
        """Display the workflow header"""
        print("\n" + "=" * 70)
        print("   GiljoAI MCP - Complete Testing Workflow")
        print("   Simulates: Git Clone → Install → Launch → Cleanup")
        print("=" * 70)
        print()
        print(f"Source: {self.source_dir}")
        print(f"Target: {self.test_dir}")
        print(f"Log: {self.log_file if self.log_file else 'Not initialized'}")
        print()

    def check_prerequisites(self) -> Dict[str, bool]:
        """Check system prerequisites"""
        self.log("Checking prerequisites...")

        checks = {
            "python": self.check_python(),
            "postgresql": self.check_postgresql(),
            "ports": self.check_ports(),
            "disk_space": self.check_disk_space(),
        }

        return checks

    def check_python(self) -> bool:
        """Check Python version"""
        try:
            version = sys.version_info
            if version.major == 3 and version.minor >= 9:
                self.log(f"Python {version.major}.{version.minor}.{version.micro} OK")
                return True
            self.log(f"Python version {version.major}.{version.minor} (need 3.9+)", "WARNING")
            return False
        except Exception as e:
            self.log(f"Failed to check Python: {e}", "ERROR")
            return False

    def check_postgresql(self) -> bool:
        """Check PostgreSQL availability"""
        try:
            # Try to find psql
            psql_paths = [
                r"C:\Program Files\PostgreSQL\18\bin\psql.exe",
                r"C:\Program Files\PostgreSQL\17\bin\psql.exe",
                r"C:\Program Files\PostgreSQL\16\bin\psql.exe",
                "psql",
            ]

            for path in psql_paths:
                if Path(path).exists() or shutil.which(path):
                    self.log(f"PostgreSQL found: {path}")
                    return True

            self.log("PostgreSQL not found - will need to install", "WARNING")
            return False

        except Exception as e:
            self.log(f"Failed to check PostgreSQL: {e}", "ERROR")
            return False

    def check_ports(self) -> bool:
        """Check if required ports are available"""
        import socket

        ports_to_check = [(8000, "API"), (8001, "WebSocket"), (3000, "Dashboard"), (5432, "PostgreSQL")]

        all_clear = True
        for port, service in ports_to_check:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(("127.0.0.1", port))
            sock.close()

            if result == 0:
                self.log(f"Port {port} ({service}) is in use", "WARNING")
                all_clear = False
            else:
                self.log(f"Port {port} ({service}) is available")

        return all_clear

    def check_disk_space(self) -> bool:
        """Check available disk space"""
        try:
            import shutil

            stat = shutil.disk_usage(self.test_dir.parent if self.test_dir.exists() else "C:/")
            free_gb = stat.free / (1024**3)

            if free_gb >= 1:
                self.log(f"Disk space: {free_gb:.1f} GB available")
                return True
            self.log(f"Low disk space: {free_gb:.1f} GB", "WARNING")
            return False
        except Exception as e:
            self.log(f"Failed to check disk space: {e}", "ERROR")
            return True  # Assume OK if can't check

    def copy_project(self, clean: bool = True) -> bool:
        """Copy project to test directory (simulating git clone)"""
        self.log("\n" + "=" * 60)
        self.log("STEP 1: Copy Project (Simulate Git Clone)")
        self.log("=" * 60)

        try:
            # Handle existing installation
            if self.test_dir.exists():
                if clean:
                    self.log("Removing existing test directory...")
                    shutil.rmtree(self.test_dir)
                else:
                    self.log("Backing up existing data...")
                    self.backup_existing_data()

            # Create test directory
            self.test_dir.mkdir(parents=True, exist_ok=True)

            # Define exclusions (similar to .gitignore)
            exclude_patterns = [
                "__pycache__",
                "*.pyc",
                "*.pyo",
                ".git",
                ".venv",
                "venv",
                "*.log",
                "*.db",
                "data/",
                ".env",
                "config.yaml",
                "node_modules",
                "dist",
                "build",
            ]

            # Copy with exclusions
            self.log("Copying project files...")

            def ignore_patterns(dir, files):
                ignored = []
                for file in files:
                    full_path = Path(dir) / file

                    # Check patterns
                    for pattern in exclude_patterns:
                        if pattern.endswith("/"):
                            if full_path.is_dir() and file == pattern[:-1]:
                                ignored.append(file)
                        elif "*" in pattern:
                            import fnmatch

                            if fnmatch.fnmatch(file, pattern):
                                ignored.append(file)
                        elif file == pattern:
                            ignored.append(file)

                return ignored

            shutil.copytree(self.source_dir, self.test_dir, ignore=ignore_patterns, dirs_exist_ok=True)

            # Count copied files
            file_count = sum(1 for _ in self.test_dir.rglob("*") if _.is_file())
            self.log(f"Copied {file_count} files to test directory")

            # Restore backed up data if needed
            if not clean and self.backup_dir.exists():
                self.restore_backed_up_data()

            self.workflow_state["copied"] = True
            self.log("Project copy completed successfully!")
            return True

        except Exception as e:
            self.log(f"Failed to copy project: {e}", "ERROR")
            return False

    def backup_existing_data(self):
        """Backup existing user data before copy"""
        if not self.test_dir.exists():
            return

        self.backup_dir.mkdir(parents=True, exist_ok=True)

        # Items to backup
        backup_items = ["data", "logs", "projects", ".env", "config.yaml"]

        for item in backup_items:
            src = self.test_dir / item
            if src.exists():
                dst = self.backup_dir / item
                if src.is_dir():
                    shutil.copytree(src, dst, dirs_exist_ok=True)
                else:
                    shutil.copy2(src, dst)
                self.log(f"Backed up: {item}")

    def restore_backed_up_data(self):
        """Restore backed up data after copy"""
        if not self.backup_dir.exists():
            return

        for item in self.backup_dir.iterdir():
            src = item
            dst = self.test_dir / item.name

            if src.is_dir():
                shutil.copytree(src, dst, dirs_exist_ok=True)
            else:
                shutil.copy2(src, dst)
            self.log(f"Restored: {item.name}")

        # Clean up backup
        shutil.rmtree(self.backup_dir)

    def run_installer(self, mode: str = "localhost") -> bool:
        """Run the installer from the test directory"""
        self.log("\n" + "=" * 60)
        self.log("STEP 2: Run Installer")
        self.log("=" * 60)

        if not self.workflow_state["copied"]:
            self.log("Project not copied yet. Run copy step first.", "ERROR")
            return False

        try:
            # Change to test directory
            os.chdir(self.test_dir)

            # Check if installer exists
            installer_path = self.test_dir / "installer" / "cli" / "install.py"
            if not installer_path.exists():
                self.log(f"Installer not found at: {installer_path}", "ERROR")
                return False

            self.log(f"Running installer in {mode} mode...")

            # Prepare installer command
            cmd = [
                sys.executable,
                str(installer_path),
                "--mode",
                mode,
                "--pg-host",
                DEFAULT_PG_HOST,
                "--pg-port",
                DEFAULT_PG_PORT,
                "--pg-password",
                DEFAULT_PG_PASSWORD,
                "--batch",  # Run in batch mode for testing
            ]

            # Add server mode options if needed
            if mode == "server":
                cmd.extend(
                    [
                        "--bind",
                        "0.0.0.0",
                        "--admin-username",
                        "admin",
                        "--admin-password",
                        "admin123",
                        "--generate-api-key",
                    ]
                )

            self.log(f"Command: {' '.join(cmd)}")

            # Run installer
            result = subprocess.run(
                cmd,
                check=False,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
            )

            if result.returncode == 0:
                self.log("Installation completed successfully!")
                self.workflow_state["installed"] = True

                # Save installation info
                self.save_installation_info(mode)
                return True
            self.log(f"Installation failed with code {result.returncode}", "ERROR")
            self.log(f"STDOUT: {result.stdout}", "ERROR")
            self.log(f"STDERR: {result.stderr}", "ERROR")
            return False

        except subprocess.TimeoutExpired:
            self.log("Installation timed out after 5 minutes", "ERROR")
            return False
        except Exception as e:
            self.log(f"Failed to run installer: {e}", "ERROR")
            return False
        finally:
            # Return to original directory
            os.chdir(self.source_dir)

    def save_installation_info(self, mode: str):
        """Save installation information for later use"""
        info = {
            "mode": mode,
            "test_dir": str(self.test_dir),
            "timestamp": datetime.now().isoformat(),
            "pg_host": DEFAULT_PG_HOST,
            "pg_port": DEFAULT_PG_PORT,
            "api_port": 8000,
            "ws_port": 8001,
            "dashboard_port": 3000,
        }

        info_file = self.test_dir / ".giltest_info.json"
        with open(info_file, "w") as f:
            json.dump(info, f, indent=2)

        self.log(f"Installation info saved to: {info_file}")

    def launch_application(self) -> bool:
        """Launch the application using start_giljo.py"""
        self.log("\n" + "=" * 60)
        self.log("STEP 3: Launch Application")
        self.log("=" * 60)

        if not self.workflow_state["installed"]:
            self.log("Application not installed yet. Run installer first.", "ERROR")
            return False

        try:
            # Check for launcher
            launcher_path = self.test_dir / "start_giljo.py"
            if not launcher_path.exists():
                self.log("Launcher not found, creating one...", "WARNING")
                self.create_launcher()

            # Launch application
            self.log("Starting GiljoAI MCP services...")

            os.chdir(self.test_dir)

            # Start in background
            process = subprocess.Popen(
                [sys.executable, str(launcher_path)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )

            # Wait for services to start
            self.log("Waiting for services to start...")
            time.sleep(5)

            # Check if services are running
            if self.verify_services_running():
                self.log("Services started successfully!")
                self.workflow_state["launched"] = True

                self.log("\n" + "=" * 60)
                self.log("Application is now running!")
                self.log("=" * 60)
                self.log("API: http://localhost:7272")
                self.log("WebSocket: ws://localhost:7272")
                self.log("Dashboard: http://localhost:7274")

                return True
            self.log("Services failed to start", "ERROR")
            # Show process output
            stdout, stderr = process.communicate(timeout=5)
            if stdout:
                self.log(f"STDOUT: {stdout}", "ERROR")
            if stderr:
                self.log(f"STDERR: {stderr}", "ERROR")
            return False

        except Exception as e:
            self.log(f"Failed to launch application: {e}", "ERROR")
            return False
        finally:
            os.chdir(self.source_dir)

    def create_launcher(self):
        """Create a basic launcher if it doesn't exist"""
        launcher_content = '''#!/usr/bin/env python3
"""
GiljoAI MCP Launcher
Auto-generated by giltest.py
"""

import subprocess
import sys
import os
from pathlib import Path

def start_services():
    """Start all GiljoAI services"""

    print("Starting GiljoAI MCP services...")

    # Start backend
    backend_process = subprocess.Popen(
        [sys.executable, "-m", "giljo_mcp"],
        cwd=Path(__file__).parent
    )

    print(f"Backend started with PID: {backend_process.pid}")
    print()
    print("Services are running:")
    print("  API: http://localhost:7272")
    print("  WebSocket: ws://localhost:7272")
    print("  Dashboard: http://localhost:7274")
    print()
    print("Press Ctrl+C to stop")

    try:
        backend_process.wait()
    except KeyboardInterrupt:
        print("\\nStopping services...")
        backend_process.terminate()
        backend_process.wait()
        print("Services stopped.")

if __name__ == "__main__":
    start_services()
'''

        launcher_path = self.test_dir / "start_giljo.py"
        launcher_path.write_text(launcher_content)
        self.log(f"Created launcher: {launcher_path}")

    def verify_services_running(self) -> bool:
        """Verify that services are actually running"""
        import socket

        services = [("127.0.0.1", 8000, "API"), ("127.0.0.1", 8001, "WebSocket")]

        all_running = True
        for host, port, name in services:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex((host, port))
            sock.close()

            if result == 0:
                self.log(f"{name} service is running on port {port}")
            else:
                self.log(f"{name} service NOT running on port {port}", "WARNING")
                all_running = False

        return all_running

    def run_cleanup(self, cleanup_type: str = "dev") -> bool:
        """Run cleanup using devuninstall or uninstall"""
        self.log("\n" + "=" * 60)
        self.log("STEP 4: Cleanup")
        self.log("=" * 60)

        try:
            os.chdir(self.test_dir)

            if cleanup_type == "dev":
                # Use devuninstall.py for development cleanup
                uninstall_path = self.test_dir / "devuninstall.py"
                self.log("Running development uninstaller...")
            else:
                # Use uninstall.py for production cleanup
                uninstall_path = self.test_dir / "uninstall.py"
                self.log("Running production uninstaller...")

            if not uninstall_path.exists():
                self.log(f"Uninstaller not found: {uninstall_path}", "ERROR")
                return False

            # Run uninstaller
            result = subprocess.run(
                [sys.executable, str(uninstall_path)],
                check=False,
                input="1\nRESET\n",  # Auto-confirm for testing
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode == 0:
                self.log("Cleanup completed successfully!")
                self.workflow_state["cleanup_done"] = True
                return True
            self.log(f"Cleanup failed: {result.stderr}", "ERROR")
            return False

        except Exception as e:
            self.log(f"Failed to run cleanup: {e}", "ERROR")
            return False
        finally:
            os.chdir(self.source_dir)

    def show_workflow_summary(self):
        """Display workflow summary"""
        print("\n" + "=" * 70)
        print("   Workflow Summary")
        print("=" * 70)

        steps = [
            ("Project Copied", self.workflow_state["copied"]),
            ("Installer Run", self.workflow_state["installed"]),
            ("Application Launched", self.workflow_state["launched"]),
            ("Cleanup Done", self.workflow_state["cleanup_done"]),
        ]

        for step, completed in steps:
            status = "✓ Complete" if completed else "✗ Pending"
            print(f"  {step:.<30} {status}")

        print()

        if self.log_file and self.log_file.exists():
            print(f"Full log available at: {self.log_file}")

    def run_interactive(self):
        """Run the interactive workflow"""
        self.setup_logging()
        self.print_header()

        # Check prerequisites
        print("\n" + "=" * 60)
        print("Checking Prerequisites")
        print("=" * 60)

        checks = self.check_prerequisites()
        all_ok = all(checks.values())

        if not all_ok:
            print("\n⚠ Some prerequisites are missing or have issues.")
            if not self.confirm("Continue anyway?"):
                print("Workflow cancelled.")
                return

        # Main workflow menu
        while True:
            print("\n" + "=" * 60)
            print("Testing Workflow Menu")
            print("=" * 60)
            print()
            print("1. Full Workflow (Copy → Install → Launch → Cleanup)")
            print("2. Copy Project Only")
            print("3. Run Installer Only")
            print("4. Launch Application Only")
            print("5. Run Cleanup (Development)")
            print("6. Run Cleanup (Production)")
            print("7. Show Summary")
            print("8. Exit")
            print()

            choice = input("Select option [1-8]: ").strip()

            if choice == "1":
                # Full workflow
                self.run_full_workflow()
            elif choice == "2":
                # Copy only
                clean = self.confirm("Clean copy (remove existing)?")
                self.copy_project(clean)
            elif choice == "3":
                # Install only
                mode = self.select_mode()
                self.run_installer(mode)
            elif choice == "4":
                # Launch only
                self.launch_application()
            elif choice == "5":
                # Dev cleanup
                self.run_cleanup("dev")
            elif choice == "6":
                # Production cleanup
                if self.confirm("⚠ WARNING: Production cleanup removes EVERYTHING. Continue?"):
                    self.run_cleanup("prod")
            elif choice == "7":
                # Summary
                self.show_workflow_summary()
            elif choice == "8":
                # Exit
                print("Exiting workflow.")
                break
            else:
                print("Invalid option.")

        # Final summary
        self.show_workflow_summary()

    def run_full_workflow(self):
        """Run the complete workflow"""
        print("\n" + "=" * 70)
        print("Running Full Testing Workflow")
        print("=" * 70)

        # Step 1: Copy
        clean = self.confirm("Clean copy (remove existing data)?")
        if not self.copy_project(clean):
            self.log("Workflow stopped: Copy failed", "ERROR")
            return

        # Step 2: Install
        mode = self.select_mode()
        if not self.run_installer(mode):
            self.log("Workflow stopped: Installation failed", "ERROR")
            return

        # Step 3: Launch
        if not self.launch_application():
            self.log("Workflow stopped: Launch failed", "ERROR")
            return

        # Step 4: Interact
        print("\n" + "=" * 60)
        print("Application is running. Test it now!")
        print("=" * 60)
        input("Press Enter when ready to continue with cleanup...")

        # Step 5: Cleanup
        cleanup_type = "dev" if self.confirm("Use development cleanup?") else "prod"
        self.run_cleanup(cleanup_type)

        print("\n✅ Full workflow completed!")

    def confirm(self, prompt: str) -> bool:
        """Get yes/no confirmation"""
        while True:
            response = input(f"{prompt} (y/n): ").strip().lower()
            if response in ["y", "yes"]:
                return True
            if response in ["n", "no"]:
                return False
            print("Please enter 'y' or 'n'")

    def select_mode(self) -> str:
        """Select installation mode"""
        while True:
            print("\nSelect installation mode:")
            print("1. Localhost (development)")
            print("2. Server (team deployment)")

            choice = input("Choice [1-2]: ").strip()
            if choice == "1":
                return "localhost"
            if choice == "2":
                return "server"
            print("Invalid choice.")


def main():
    """Main entry point"""
    orchestrator = TestWorkflowOrchestrator()

    # Check for command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "--full":
            # Run full workflow automatically
            orchestrator.setup_logging()
            orchestrator.print_header()
            orchestrator.run_full_workflow()
        elif sys.argv[1] == "--help":
            print("GiljoAI MCP Testing Workflow")
            print()
            print("Usage:")
            print("  python giltest_enhanced.py          # Interactive mode")
            print("  python giltest_enhanced.py --full   # Run full workflow")
            print("  python giltest_enhanced.py --help   # Show this help")
        else:
            print(f"Unknown option: {sys.argv[1]}")
            print("Use --help for options")
    else:
        # Interactive mode
        orchestrator.run_interactive()


if __name__ == "__main__":
    main()
