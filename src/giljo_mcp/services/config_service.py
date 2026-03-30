"""Configuration service for centralized config.yaml management.

Updated Handover 0731: Reviewed for typed returns - dict[str, Any] retained because
config values are read from YAML files with dynamic, deployment-specific schemas.
Both get_serena_config() and _read_config() return raw YAML data whose structure
varies based on installation and feature flags. No fixed Pydantic model can represent
the full range of possible configurations.
"""

import logging
import threading
import time
from pathlib import Path
from typing import Any, Optional

from giljo_mcp._config_io import read_config


logger = logging.getLogger(__name__)


class ConfigService:
    """
    Centralized configuration management service.

    Provides thread-safe access to config.yaml with caching
    and automatic template cache invalidation.
    """

    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize ConfigService.

        Args:
            config_path: Path to config.yaml (defaults to cwd/config.yaml)
        """
        self.config_path = config_path or Path.cwd() / "config.yaml"
        self._cache: dict[str, Any] = {}
        self._cache_ttl = 60  # seconds
        self._last_read: Optional[float] = None
        self._lock = threading.RLock()

    def get_serena_config(self, use_cache: bool = True) -> dict[str, Any]:
        """
        Get Serena configuration.

        Args:
            use_cache: Whether to use cached config

        Returns:
            dict[str, Any] - Serena config with keys: enabled, installed, registered.
            Intentionally returns dict because YAML config structure varies by
            deployment and feature flags (not a fixed schema).
        """
        if use_cache and self._is_cache_valid():
            return self._cache.get("serena_mcp", {})

        config = self._read_config()
        serena_config = config.get("features", {}).get("serena_mcp", {})

        with self._lock:
            self._cache["serena_mcp"] = serena_config
            self._last_read = time.time()

        return serena_config

    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid."""
        if not self._last_read:
            return False
        return (time.time() - self._last_read) < self._cache_ttl

    def _read_config(self) -> dict[str, Any]:
        """Read config.yaml. Returns raw YAML data as dict (dynamic structure)."""
        return read_config(self.config_path)

    def invalidate_cache(self) -> None:
        """Force cache refresh on next read."""
        with self._lock:
            self._cache.clear()
            self._last_read = None
