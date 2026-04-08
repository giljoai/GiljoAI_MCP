# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""Shared low-level config.yaml I/O.

This module is for raw file I/O only. Production code should use
get_config() from config_manager.py, which provides typed access
with environment variable overrides via get_nested() for arbitrary
YAML key paths.

Legitimate uses of read_config() / write_config():
  - Config CRUD endpoints that manage the YAML file directly
  - ConfigManager initialization itself
  - Bootstrapping code that runs before ConfigManager is available
  - Utilities that read from non-standard config paths

Design: read_config() returns a plain dict so the implementation can
later be extended (env-var overlays, per-tenant overrides, remote config)
without changing callers.
"""

import logging
from pathlib import Path
from typing import Any

import yaml


logger = logging.getLogger(__name__)


def get_config_path() -> Path:
    """Return the canonical path to config.yaml (project root / cwd)."""
    return Path.cwd() / "config.yaml"


def read_config(config_path: Path | None = None) -> dict[str, Any]:
    """Read and parse config.yaml.

    Args:
        config_path: Override path. Defaults to get_config_path().

    Returns:
        Parsed YAML as a dict. Empty dict if file is missing or unparseable.
    """
    path = config_path or get_config_path()
    if not path.exists():
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except (yaml.YAMLError, OSError):
        logger.exception("Failed to read %s", path)
        return {}


def write_config(config: dict[str, Any], config_path: Path | None = None) -> None:
    """Write config dict to config.yaml atomically.

    Uses temp-file-then-rename to prevent corruption on crash.

    Args:
        config: Configuration dictionary to persist.
        config_path: Override path. Defaults to get_config_path().

    Raises:
        OSError: If the file cannot be written.
    """
    path = config_path or get_config_path()
    temp_path = path.with_suffix(".yaml.tmp")
    with open(temp_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(config, f, default_flow_style=False, sort_keys=False)
    temp_path.replace(path)
