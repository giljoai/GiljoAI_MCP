# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""Shutdown module

Handles graceful shutdown of all services and connections.
Each step has a timeout to prevent hanging on unresponsive services.
Visual progress is printed to the console for developer feedback.
"""

import asyncio
import contextlib
import logging
import time

from api.app import APIState

logger = logging.getLogger(__name__)

# Maximum seconds to wait for each shutdown step before force-skipping
STEP_TIMEOUT = 5


async def _run_with_timeout(coro, step_name: str, timeout: float = STEP_TIMEOUT) -> bool:
    """Run a coroutine with a timeout. Returns True if completed, False if timed out."""
    try:
        await asyncio.wait_for(coro, timeout=timeout)
        return True
    except asyncio.TimeoutError:
        logger.warning(f"Shutdown step '{step_name}' timed out after {timeout}s - forcing skip")
        return False
    except (RuntimeError, OSError, ConnectionError, ValueError):  # Shutdown resilience
        logger.exception("Error in shutdown step '%s'", step_name)
        return False


def _print_step(step: int, total: int, label: str, status: str = "...") -> None:
    """Print a shutdown progress line to the console."""
    bar_filled = step
    bar_empty = total - step
    bar = "=" * bar_filled + "-" * bar_empty
    print(f"\r  [{bar}] ({step}/{total}) {label}: {status}", end="", flush=True)


def _print_step_done(step: int, total: int, label: str, ok: bool, elapsed: float) -> None:
    """Print a completed shutdown step."""
    marker = "OK" if ok else "TIMEOUT"
    bar_filled = step
    bar_empty = total - step
    bar = "=" * bar_filled + "-" * bar_empty
    print(f"\r  [{bar}] ({step}/{total}) {label}: {marker} ({elapsed:.1f}s)")


async def shutdown(state: APIState) -> None:
    """Gracefully shutdown all services with timeouts and progress display.

    Each step has a 5-second timeout. If a step hangs, it is skipped
    and shutdown continues. Total worst-case shutdown time: ~30 seconds.

    Args:
        state: APIState instance with active services and connections
    """
    total_steps = 6
    print()  # Blank line before shutdown block
    logger.info("Shutting down GiljoAI MCP API...")
    print(f"  Shutting down ({total_steps} steps, {STEP_TIMEOUT}s timeout each):")

    # Step 1: Cancel background tasks
    step = 1
    label = "Background tasks"
    _print_step(step, total_steps, label)
    t0 = time.monotonic()
    try:
        tasks_to_cancel = []
        for task_attr in ("heartbeat_task", "cleanup_task", "metrics_sync_task"):
            task = getattr(state, task_attr, None)
            if task:
                task.cancel()
                tasks_to_cancel.append(task)
        if tasks_to_cancel:
            done = await _run_with_timeout(
                asyncio.gather(*tasks_to_cancel, return_exceptions=True),
                label,
            )
        else:
            done = True
    except (RuntimeError, OSError, ConnectionError, ValueError):  # Shutdown resilience
        done = False
    _print_step_done(step, total_steps, label, done, time.monotonic() - t0)

    # Step 2: Stop health monitor
    step = 2
    label = "Health monitor"
    _print_step(step, total_steps, label)
    t0 = time.monotonic()
    if state.health_monitor:
        done = await _run_with_timeout(state.health_monitor.stop(), label)
    else:
        done = True
    _print_step_done(step, total_steps, label, done, time.monotonic() - t0)

    # Step 3: Stop silence detector
    step = 3
    label = "Silence detector"
    _print_step(step, total_steps, label)
    t0 = time.monotonic()
    if getattr(state, "silence_detector", None):
        done = await _run_with_timeout(state.silence_detector.stop(), label)
    else:
        done = True
    _print_step_done(step, total_steps, label, done, time.monotonic() - t0)

    # Step 4: Close WebSocket connections
    step = 4
    label = "WebSocket connections"
    _print_step(step, total_steps, label)
    t0 = time.monotonic()
    ws_count = len(state.connections)

    async def close_all_ws():
        for ws in list(state.connections.values()):
            with contextlib.suppress(Exception):
                await ws.close()

    if ws_count > 0:
        done = await _run_with_timeout(close_all_ws(), label)
    else:
        done = True
    _print_step_done(step, total_steps, f"{label} ({ws_count})", done, time.monotonic() - t0)

    # Step 5: Stop WebSocket broker
    step = 5
    label = "WebSocket broker"
    _print_step(step, total_steps, label)
    t0 = time.monotonic()
    if getattr(state, "websocket_broker", None):
        done = await _run_with_timeout(state.websocket_broker.stop(), label)
    else:
        done = True
    _print_step_done(step, total_steps, label, done, time.monotonic() - t0)

    # Step 6: Close database
    step = 6
    label = "Database"
    _print_step(step, total_steps, label)
    t0 = time.monotonic()
    if state.db_manager:
        done = await _run_with_timeout(state.db_manager.close_async(), label)
    else:
        done = True
    _print_step_done(step, total_steps, label, done, time.monotonic() - t0)

    print(f"  [{'=' * total_steps}] Shutdown complete")
    logger.info("API shutdown complete")
