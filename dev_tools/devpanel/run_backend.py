#!/usr/bin/env python3
"""Launch the standalone Developer Panel backend."""

from __future__ import annotations

import os

import uvicorn


def main() -> int:
    os.environ.setdefault("ENABLE_DEVPANEL", "true")
    uvicorn.run("dev_tools.devpanel.backend.app:app", host="127.0.0.1", port=8283, reload=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
