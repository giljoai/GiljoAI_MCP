#!/usr/bin/env python3
"""Launch the standalone Developer Panel backend."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Dict

import uvicorn


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _log_config() -> Dict[str, Any]:
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "rich": {
                "format": "%(message)s",
                "datefmt": "[%X]",
            }
        },
        "handlers": {
            "rich": {
                "class": "rich.logging.RichHandler",
                "level": "INFO",
                "formatter": "rich",
                "markup": True,
                "rich_tracebacks": True,
            }
        },
        "loggers": {
            "uvicorn": {"handlers": ["rich"], "level": "INFO", "propagate": False},
            "uvicorn.error": {"handlers": ["rich"], "level": "INFO", "propagate": False},
            "uvicorn.access": {"handlers": ["rich"], "level": "INFO", "propagate": False},
        },
    }


def main() -> int:
    os.environ.setdefault("ENABLE_DEVPANEL", "true")
    uvicorn.run(
        "dev_tools.devpanel.backend.app:app",
        host="127.0.0.1",
        port=8283,
        reload=True,
        log_config=_log_config(),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
