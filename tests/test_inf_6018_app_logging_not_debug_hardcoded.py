# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""INF-6018 regression: api/app.py must not hardcode DEBUG logging.

api/app.py configures logging at module import time (before .env loads), so a
hardcoded ``level=logging.DEBUG`` forces the ENTIRE app to DEBUG on every
deploy -- overriding the uvicorn ``--log-level info`` start command and the
canonical LOG_LEVEL-aware setup in ``giljo_mcp.logging``. On prod this floods
logs (~500 lines/sec) and adds per-request I/O overhead.

The failing layer is the module-level logging config, so the guard asserts on
the source of api/app.py directly: the level must be derived from the
LOG_LEVEL env var, never pinned to DEBUG.
"""

from __future__ import annotations

from pathlib import Path


_APP_PY = Path(__file__).resolve().parent.parent / "api" / "app.py"


def _source() -> str:
    return _APP_PY.read_text(encoding="utf-8")


def test_app_does_not_hardcode_debug_level() -> None:
    """The early basicConfig must not pin the root logger to DEBUG."""
    src = _source()
    assert "level=logging.DEBUG" not in src, (
        "api/app.py hardcodes logging.DEBUG at import time. This overrides "
        "LOG_LEVEL and uvicorn --log-level, forcing DEBUG on prod. Derive the "
        "level from os.getenv('LOG_LEVEL', 'INFO') instead (INF-6018)."
    )


def test_app_logging_honors_log_level_env() -> None:
    """The logging level must be derived from the LOG_LEVEL env var."""
    src = _source()
    assert 'os.getenv("LOG_LEVEL"' in src or "os.getenv('LOG_LEVEL'" in src, (
        "api/app.py must resolve its log level from the LOG_LEVEL env var "
        "(default INFO), mirroring giljo_mcp.logging (INF-6018)."
    )
