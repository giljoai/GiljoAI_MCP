# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""Background task that checks the git remote for available updates.

Runs every 6 hours. Sets state.update_available when commits are detected
behind origin/master and broadcasts a WebSocket event on state transitions.
Silently no-ops if: git is not installed, no remote is configured, no
network is available, or the working directory is not a git repository.
"""

import asyncio
import logging
from pathlib import Path


logger = logging.getLogger(__name__)

_CHECK_INTERVAL_SECONDS = 21600  # 6 hours
_SUBPROCESS_TIMEOUT_SECONDS = 10


async def _run_git(*args: str) -> tuple[int, str, str]:
    """Run a git subcommand and return (returncode, stdout, stderr).

    Raises FileNotFoundError if the git binary is not on PATH.
    Raises asyncio.TimeoutError if the process does not complete in time.
    """
    proc = await asyncio.create_subprocess_exec(
        "git",
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=str(Path.cwd()),
    )
    stdout_bytes, stderr_bytes = await asyncio.wait_for(proc.communicate(), timeout=_SUBPROCESS_TIMEOUT_SECONDS)
    return (
        proc.returncode,
        stdout_bytes.decode("utf-8", errors="replace").strip(),
        stderr_bytes.decode("utf-8", errors="replace").strip(),
    )


async def _is_git_repo() -> bool:
    """Return True if the working directory is inside a git repository."""
    try:
        code, _, _ = await _run_git("rev-parse", "--is-inside-work-tree")
        return code == 0
    except (FileNotFoundError, asyncio.TimeoutError, OSError):
        return False


async def _has_remote(remote: str = "origin") -> bool:
    """Return True if the named remote exists."""
    try:
        code, _, _ = await _run_git("remote", "get-url", remote)
        return code == 0
    except (FileNotFoundError, asyncio.TimeoutError, OSError):
        return False


async def _fetch_remote(remote: str = "origin") -> bool:
    """Fetch the remote to populate FETCH_HEAD. Returns True on success."""
    try:
        code, _, stderr = await _run_git("fetch", remote)
        if code != 0:
            logger.debug("git fetch %s failed: %s", remote, stderr)
            return False
        return True
    except (FileNotFoundError, asyncio.TimeoutError, OSError) as exc:
        logger.debug("git fetch %s error: %s", remote, exc)
        return False


async def _commits_behind(branch: str = "origin/master") -> int | None:
    """Return the number of commits HEAD is behind the remote branch.

    Returns None if the count cannot be determined (network error, branch
    does not exist, etc.).
    """
    try:
        code, stdout, stderr = await _run_git("rev-list", f"HEAD..{branch}", "--count")
        if code != 0:
            logger.debug("git rev-list failed: %s", stderr)
            return None
        return int(stdout)
    except (FileNotFoundError, asyncio.TimeoutError, OSError, ValueError) as exc:
        logger.debug("git rev-list error: %s", exc)
        return None


async def _emit_update_event(state, update_info: dict | None) -> None:
    """Broadcast a system:update_available WebSocket event to all tenants.

    Does nothing if the WebSocket manager is not ready.
    """
    ws_manager = getattr(state, "websocket_manager", None)
    if ws_manager is None:
        return

    event_data = {
        "update_available": update_info is not None,
        "detail": update_info,
    }

    try:
        # broadcast_json sends to all connected clients across all tenants
        await ws_manager.broadcast_json(
            {
                "type": "system:update_available",
                "data": event_data,
            }
        )
        logger.debug("Broadcast system:update_available event")
    except Exception as exc:
        logger.debug("Could not broadcast update event: %s", exc)


async def _update_check_loop(state) -> None:
    """Periodic loop that checks for remote commits every 6 hours.

    Runs an initial fetch at startup so rev-list has accurate data, then
    polls on the configured interval. State transitions trigger WebSocket
    broadcasts.
    """
    remote = "origin"
    branch = f"{remote}/master"

    # Initial fetch to populate FETCH_HEAD before the first check
    fetched = await _fetch_remote(remote)
    if not fetched:
        logger.debug("Initial fetch failed — update checks will rely on stale FETCH_HEAD if present")

    while True:
        try:
            count = await _commits_behind(branch)

            if count is None:
                # Network or branch error — leave current state unchanged
                logger.debug("Could not determine commits behind %s — skipping this cycle", branch)
            elif count > 0:
                new_info: dict | None = {
                    "commits_behind": count,
                    "message": f"GiljoAI MCP: {count} update{'s' if count != 1 else ''} available. Run python update.py to install.",
                }
                previous = state.update_available
                state.update_available = new_info
                if previous is None:
                    logger.info(
                        "Update available: %d commit%s behind %s",
                        count,
                        "s" if count != 1 else "",
                        branch,
                    )
                    await _emit_update_event(state, new_info)
            else:
                previous = state.update_available
                state.update_available = None
                if previous is not None:
                    logger.info("System is up to date with %s", branch)
                    await _emit_update_event(state, None)

        except Exception as exc:
            logger.debug("Update check cycle error: %s", exc)

        await asyncio.sleep(_CHECK_INTERVAL_SECONDS)

        # Fetch before each subsequent check
        await _fetch_remote(remote)


async def start_update_checker(state) -> asyncio.Task | None:
    """Start the background git update checker task.

    Returns the asyncio.Task if started, or None if the environment does not
    support it (no git, no remote, not in a git repo).

    This function never raises — all failures are handled gracefully.
    """
    try:
        if not await _is_git_repo():
            logger.debug("Not in a git repository — update checker disabled")
            return None

        if not await _has_remote("origin"):
            logger.debug("No 'origin' remote configured — update checker disabled")
            return None

        task = asyncio.create_task(_update_check_loop(state))
        return task

    except FileNotFoundError:
        logger.debug("git binary not found — update checker disabled")
        return None
    except Exception as exc:
        logger.debug("Update checker could not start: %s", exc)
        return None
