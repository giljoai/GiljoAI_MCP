# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""Background task that checks for available updates.

Two strategies:
  1. Git-based (cloned installs): git fetch + rev-list to count commits behind origin/master.
  2. GitHub releases API (zip installs): compare local __version__ against latest release tag.

Runs every 6 hours. Sets state.update_available when an update is detected
and broadcasts a WebSocket event on state transitions.
Silently no-ops if no network is available.
"""

import asyncio
import json
import logging
import urllib.error
import urllib.request
from pathlib import Path


try:
    from packaging.version import InvalidVersion, Version

    _HAS_PACKAGING = True
except ImportError:
    _HAS_PACKAGING = False


logger = logging.getLogger(__name__)

_CHECK_INTERVAL_SECONDS = 21600  # 6 hours
_SUBPROCESS_TIMEOUT_SECONDS = 10
_GITHUB_RELEASES_URL = "https://api.github.com/repos/giljoai/GiljoAI_MCP/releases/latest"
_HTTP_TIMEOUT_SECONDS = 10


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


def _get_local_version() -> str:
    """Return the local application version string."""
    try:
        from src.giljo_mcp import __version__

        return __version__
    except ImportError:
        return "0.0.0"


async def _check_github_release() -> dict | None:
    """Check the GitHub releases API for a newer version.

    Returns update info dict if a newer release exists, None if up to date.
    Runs the blocking HTTP request in a thread executor to avoid blocking the event loop.
    """
    loop = asyncio.get_running_loop()
    try:
        local_version = Version(_get_local_version())
    except InvalidVersion:
        logger.debug("Could not parse local version — release check skipped")
        return None

    def _fetch_latest():
        req = urllib.request.Request(  # noqa: S310 — URL is a hardcoded HTTPS constant
            _GITHUB_RELEASES_URL,
            headers={"Accept": "application/vnd.github+json", "User-Agent": "GiljoAI-MCP-UpdateChecker"},
        )
        with urllib.request.urlopen(req, timeout=_HTTP_TIMEOUT_SECONDS) as resp:  # noqa: S310  # nosec B310
            return json.loads(resp.read().decode("utf-8"))

    try:
        data = await loop.run_in_executor(None, _fetch_latest)
    except (urllib.error.URLError, OSError, json.JSONDecodeError) as exc:
        logger.debug("GitHub releases API error: %s", exc)
        return None

    tag = data.get("tag_name", "")
    # Strip leading 'v' from tag (e.g. "v1.1.0" -> "1.1.0")
    version_str = tag.lstrip("v")

    try:
        remote_version = Version(version_str)
    except InvalidVersion:
        logger.debug("Could not parse remote version tag: %s", tag)
        return None

    if remote_version > local_version:
        html_url = data.get("html_url", "https://github.com/giljoai/GiljoAI_MCP/releases")
        return {
            "current_version": str(local_version),
            "latest_version": str(remote_version),
            "release_url": html_url,
            "message": f"GiljoAI MCP v{remote_version} is available (you have v{local_version}). "
            f"Download the latest version from {html_url}",
        }

    return None


async def _release_check_loop(state) -> None:
    """Periodic loop for zip-based installs that checks GitHub releases."""
    while True:
        try:
            update_info = await _check_github_release()

            previous = state.update_available
            if update_info is not None:
                state.update_available = update_info
                if previous is None:
                    logger.info(
                        "Update available: v%s -> v%s",
                        update_info["current_version"],
                        update_info["latest_version"],
                    )
                    await _emit_update_event(state, update_info)
            else:
                state.update_available = None
                if previous is not None:
                    logger.info("System is up to date (v%s)", _get_local_version())
                    await _emit_update_event(state, None)

        except Exception as exc:
            logger.debug("Release check cycle error: %s", exc)

        await asyncio.sleep(_CHECK_INTERVAL_SECONDS)


async def start_update_checker(state) -> asyncio.Task | None:
    """Start the background update checker task.

    Uses git-based checking for cloned installs, falls back to GitHub
    releases API for zip-based installs.

    Returns the asyncio.Task if started, or None if the environment does not
    support it. This function never raises.
    """
    try:
        # Strategy 1: Git-based (cloned installs)
        if await _is_git_repo() and await _has_remote("origin"):
            logger.info("Update checker started (git mode)")
            return asyncio.create_task(_update_check_loop(state))

        # Strategy 2: GitHub releases API (zip installs)
        if not _HAS_PACKAGING:
            logger.debug("packaging library not available — release check disabled")
            return None
        logger.info("Update checker started (release mode — no git repo detected)")
        return asyncio.create_task(_release_check_loop(state))

    except FileNotFoundError:
        # No git binary — use release mode
        if not _HAS_PACKAGING:
            logger.debug("packaging library not available — release check disabled")
            return None
        logger.info("Update checker started (release mode — git not installed)")
        return asyncio.create_task(_release_check_loop(state))
    except Exception as exc:
        logger.debug("Update checker could not start: %s", exc)
        return None
