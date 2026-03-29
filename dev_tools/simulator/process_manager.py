import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class ProcInfo:
    name: str
    pid: int
    started_at: float
    port: int
    command: list[str]


class ProcessManager:
    """Manage launching/stopping the main API and static frontend server.

    - API: runs api/run_api.py
    - Frontend: runs serve_frontend.py (serves frontend/dist)
    """

    def __init__(self) -> None:
        self._api_proc: Optional[subprocess.Popen] = None
        self._frontend_proc: Optional[subprocess.Popen] = None
        self._api_info: Optional[ProcInfo] = None
        self._frontend_info: Optional[ProcInfo] = None

    # ---------------------- API ----------------------
    def _resolve_repo_python(self) -> str:
        """Prefer the repo root venv Python if present, else current interpreter."""
        here = Path(__file__).resolve()
        repo_root = here.parents[2]
        # Windows
        win_py = repo_root / ".venv" / "Scripts" / "python.exe"
        if win_py.exists():
            return str(win_py)
        # Unix
        nix_py = repo_root / ".venv" / "bin" / "python"
        if nix_py.exists():
            return str(nix_py)
        return sys.executable

    def start_api(self, host: str = "0.0.0.0", port: int = 7272, log_level: str = "info") -> ProcInfo:
        if self._api_proc and self._api_proc.poll() is None:
            return self._api_info  # type: ignore[return-value]

        python_bin = self._resolve_repo_python()
        cmd = [python_bin, "api/run_api.py", "--host", host, "--port", str(port), "--log-level", log_level]
        self._api_proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        self._api_info = ProcInfo(name="api", pid=self._api_proc.pid, started_at=time.time(), port=port, command=cmd)
        return self._api_info

    def stop_api(self) -> bool:
        if not self._api_proc:
            return False
        proc = self._api_proc
        if proc.poll() is None:
            try:
                if os.name == "nt":
                    proc.terminate()
                else:
                    proc.send_signal(signal.SIGTERM)
                proc.wait(timeout=10)
            except Exception:
                proc.kill()
        self._api_proc = None
        self._api_info = None
        return True

    # ------------------- Frontend -------------------
    def start_frontend(self, host: str = "0.0.0.0", port: int = 7274) -> ProcInfo:
        if self._frontend_proc and self._frontend_proc.poll() is None:
            return self._frontend_info  # type: ignore[return-value]

        # serve_frontend.py bind address derived from install-time network choice; we respect that default
        cmd = [sys.executable, "serve_frontend.py"]
        env = os.environ.copy()
        env["PORT"] = str(port)
        self._frontend_proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env)
        self._frontend_info = ProcInfo(
            name="frontend",
            pid=self._frontend_proc.pid,
            started_at=time.time(),
            port=port,
            command=cmd,
        )
        return self._frontend_info

    def stop_frontend(self) -> bool:
        if not self._frontend_proc:
            return False
        proc = self._frontend_proc
        if proc.poll() is None:
            try:
                if os.name == "nt":
                    proc.terminate()
                else:
                    proc.send_signal(signal.SIGTERM)
                proc.wait(timeout=10)
            except Exception:
                proc.kill()
        self._frontend_proc = None
        self._frontend_info = None
        return True

    # ------------------- Status ---------------------
    def status(self) -> dict:
        def proc_state(p: Optional[subprocess.Popen], info: Optional[ProcInfo]):
            if not p or not info:
                return {"running": False}
            return {
                "running": p.poll() is None,
                "pid": info.pid,
                "port": info.port,
                "started_at": info.started_at,
                "command": info.command,
            }

        return {
            "api": proc_state(self._api_proc, self._api_info),
            "frontend": proc_state(self._frontend_proc, self._frontend_info),
        }
