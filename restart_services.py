#!/usr/bin/env python3

# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
GiljoAI MCP Service Restart Script

Cross-platform script to gracefully restart GiljoAI services after setup completion.
Called by the /api/setup/restart-services endpoint.

Process:
1. Find running start_giljo.py processes
2. Gracefully terminate them (SIGTERM then SIGKILL if needed)
3. Restart services using start_giljo.py

Cross-Platform Support:
- Windows: Uses tasklist/taskkill or psutil
- Linux/macOS: Uses ps/kill or psutil
- Falls back to basic subprocess if psutil not available
"""

import os
import platform
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import List


# Try to import psutil for advanced process management
try:
    import psutil

    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    print("Warning: psutil not available. Using basic process management.")


class ServiceRestarter:
    """Cross-platform service restart manager."""

    def __init__(self):
        self.base_dir = Path(__file__).parent.absolute()
        self.launcher_script = self.base_dir / "start_giljo.py"
        self.system = platform.system()

    def find_launcher_processes(self) -> List[int]:
        """
        Find PIDs of running start_giljo.py processes.

        Returns:
            List of process IDs (PIDs)
        """
        pids = []

        if PSUTIL_AVAILABLE:
            # Use psutil for reliable process detection
            for proc in psutil.process_iter(["pid", "name", "cmdline"]):
                try:
                    cmdline = proc.info.get("cmdline")
                    if cmdline and "start_giljo.py" in " ".join(cmdline):
                        pids.append(proc.info["pid"])
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        # Fall back to platform-specific commands
        elif self.system == "Windows":
            pids = self._find_processes_windows()
        else:
            pids = self._find_processes_unix()

        return pids

    def _find_processes_windows(self) -> List[int]:
        """Find processes on Windows using tasklist."""
        pids = []
        try:
            # Run tasklist with verbose output
            result = subprocess.run(
                ["tasklist", "/V", "/FO", "CSV"],
                check=False,
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                # Parse CSV output to find python processes running start_giljo.py
                for line in result.stdout.split("\n"):
                    if "python" in line.lower() and "start_giljo.py" in line:
                        # Extract PID (second column in CSV)
                        parts = line.split('","')
                        if len(parts) > 1:
                            pid_str = parts[1].replace('"', "").strip()
                            try:
                                pids.append(int(pid_str))
                            except ValueError:
                                continue
        except Exception as e:
            print(f"Warning: Failed to find processes on Windows: {e}")

        return pids

    def _find_processes_unix(self) -> List[int]:
        """Find processes on Unix-like systems using ps."""
        pids = []
        try:
            # Use ps to find python processes
            result = subprocess.run(
                ["ps", "aux"],
                check=False,
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                for line in result.stdout.split("\n"):
                    if "python" in line and "start_giljo.py" in line:
                        # PID is second column
                        parts = line.split()
                        if len(parts) > 1:
                            try:
                                pids.append(int(parts[1]))
                            except ValueError:
                                continue
        except Exception as e:
            print(f"Warning: Failed to find processes on Unix: {e}")

        return pids

    def kill_process(self, pid: int, force: bool = False) -> bool:
        """
        Kill a process by PID.

        Args:
            pid: Process ID to kill
            force: If True, use SIGKILL (force kill), else SIGTERM (graceful)

        Returns:
            True if process was killed successfully
        """
        if PSUTIL_AVAILABLE:
            try:
                proc = psutil.Process(pid)
                if force:
                    proc.kill()  # SIGKILL
                else:
                    proc.terminate()  # SIGTERM
                proc.wait(timeout=5)
                return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired):
                return False
        # Fall back to platform-specific kill
        elif self.system == "Windows":
            return self._kill_process_windows(pid, force)
        else:
            return self._kill_process_unix(pid, force)

    def _kill_process_windows(self, pid: int, force: bool) -> bool:
        """Kill process on Windows using taskkill."""
        try:
            args = ["taskkill", "/PID", str(pid)]
            if force:
                args.append("/F")  # Force kill

            result = subprocess.run(args, check=False, capture_output=True, timeout=10)
            return result.returncode == 0
        except Exception:
            return False

    def _kill_process_unix(self, pid: int, force: bool) -> bool:
        """Kill process on Unix using kill command."""
        try:
            sig = signal.SIGKILL if force else signal.SIGTERM
            os.kill(pid, sig)
            return True
        except (OSError, ProcessLookupError):
            return False

    def stop_services(self) -> bool:
        """
        Stop all running GiljoAI services.

        Returns:
            True if all services stopped successfully
        """
        print("Finding running GiljoAI services...")
        pids = self.find_launcher_processes()

        if not pids:
            print("No running services found.")
            return True

        print(f"Found {len(pids)} running service(s): {pids}")

        # Try graceful termination first
        print("Attempting graceful shutdown (SIGTERM)...")
        for pid in pids:
            self.kill_process(pid, force=False)

        # Wait for processes to terminate
        time.sleep(3)

        # Check if any processes are still running
        remaining_pids = self.find_launcher_processes()

        if remaining_pids:
            print(f"Force killing remaining processes: {remaining_pids}")
            for pid in remaining_pids:
                self.kill_process(pid, force=True)

            # Final check
            time.sleep(1)
            final_check = self.find_launcher_processes()
            if final_check:
                print(f"Warning: Could not kill processes: {final_check}")
                return False

        print("All services stopped successfully.")
        return True

    def start_services(self) -> bool:
        """
        Start GiljoAI services using start_giljo.py.

        Returns:
            True if services started successfully
        """
        if not self.launcher_script.exists():
            print(f"Error: Launcher script not found: {self.launcher_script}")
            return False

        print(f"Starting services from {self.launcher_script}...")

        try:
            # Start in background (detached process)
            if self.system == "Windows":
                # Windows: Use CREATE_NEW_PROCESS_GROUP to detach
                subprocess.Popen(
                    [sys.executable, str(self.launcher_script)],
                    cwd=self.base_dir,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                )
            else:
                # Unix: Use nohup or similar
                subprocess.Popen(
                    [sys.executable, str(self.launcher_script)],
                    cwd=self.base_dir,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,  # Detach from parent
                )

            print("Services started successfully.")
            return True

        except Exception as e:
            print(f"Error starting services: {e}")
            return False

    def restart(self) -> bool:
        """
        Perform full restart: stop then start services.

        Returns:
            True if restart completed successfully
        """
        print("\n" + "=" * 60)
        print("  GiljoAI MCP Service Restart")
        print("=" * 60)
        print()

        # Stop existing services
        if not self.stop_services():
            print("\nError: Failed to stop services.")
            return False

        # Wait a moment for cleanup
        print("\nWaiting 2 seconds for cleanup...")
        time.sleep(2)

        # Start services
        if not self.start_services():
            print("\nError: Failed to start services.")
            return False

        print("\n" + "=" * 60)
        print("  Restart Complete!")
        print("  Services will be available in 10-15 seconds.")
        print("=" * 60)
        return True


def main():
    """Main entry point for restart script."""
    restarter = ServiceRestarter()

    try:
        success = restarter.restart()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nRestart cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\nFatal error during restart: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
