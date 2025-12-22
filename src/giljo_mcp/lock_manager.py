"""
Lock Manager for GiljoAI MCP
Provides instance locking to prevent multiple servers from running
Uses a custom lock file to prevent conflicts with other MCP servers
"""

import atexit
import os
import sys
from pathlib import Path
from typing import Optional


class LockManager:
    """Manages a lock file to ensure single instance of GiljoAI MCP"""

    def __init__(self, lock_dir: Optional[Path] = None):
        """Initialize lock manager with custom directory"""
        if lock_dir is None:
            # Use user's home directory for lock file
            # This is unique to GiljoAI MCP
            lock_dir = Path.home() / ".giljo_mcp" / "locks"

        lock_dir.mkdir(parents=True, exist_ok=True)
        self.lock_file = lock_dir / "giljo_mcp.lock"
        self.pid = os.getpid()
        self.locked = False

    def acquire_lock(self) -> bool:
        """Try to acquire the lock"""
        try:
            # Check if lock file exists
            if self.lock_file.exists():
                # Read the PID from the lock file
                try:
                    with open(self.lock_file) as f:
                        old_pid = int(f.read().strip())

                    # Check if the process is still running
                    if self._is_process_running(old_pid):
                        return False
                    # Old process is dead, remove stale lock
                    self.lock_file.unlink()
                except (ValueError, OSError):
                    # Invalid lock file, remove it
                    self.lock_file.unlink()

            # Create new lock file with our PID
            with open(self.lock_file, "w") as f:
                f.write(str(self.pid))

            self.locked = True
            # Register cleanup on exit
            atexit.register(self.release_lock)
            return True

        except Exception:
            return False

    def release_lock(self):
        """Release the lock"""
        if self.locked and self.lock_file.exists():
            try:
                # Only remove if it's our lock
                with open(self.lock_file) as f:
                    if int(f.read().strip()) == self.pid:
                        self.lock_file.unlink()
                        self.locked = False
            except Exception:
                pass  # nosec B110 - best effort lock cleanup

    def _is_process_running(self, pid: int) -> bool:
        """Check if a process with given PID is running"""
        if sys.platform == "win32":
            import subprocess  # nosec B404

            try:
                result = subprocess.run(  # nosec B603 B607
                    ["tasklist", "/FI", f"PID eq {pid}"], capture_output=True, text=True, check=False
                )
                return str(pid) in result.stdout
            except Exception:
                return False
        else:
            # Unix-based systems
            try:
                os.kill(pid, 0)
                return True
            except (OSError, ProcessLookupError):
                return False

    def __enter__(self):
        """Context manager support"""
        if not self.acquire_lock():
            raise RuntimeError("Could not acquire GiljoAI MCP lock")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager cleanup"""
        self.release_lock()


# Global instance for convenience
_lock_manager = None


def get_lock_manager() -> LockManager:
    """Get the global lock manager instance"""
    global _lock_manager
    if _lock_manager is None:
        _lock_manager = LockManager()
    return _lock_manager
