"""
Claude Configuration Manager Service.

Manages the ~/.claude.json configuration file for MCP server registration.
Provides atomic operations with backup/restore capability.
"""

import json
import logging
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)


class ClaudeConfigManager:
    """
    Service for managing ~/.claude.json configuration file.

    This service handles:
    1. Injecting Serena MCP server configuration
    2. Removing Serena MCP server configuration
    3. Atomic writes with backup/restore
    4. UTF-8 encoding for unicode character support
    """

    def __init__(self):
        """Initialize the ClaudeConfigManager."""
        self.claude_config_path = Path.home() / ".claude.json"
        self.backup_dir = Path.home() / ".claude_backups"

    def inject_serena(self, project_root: Path) -> dict[str, Any]:
        """
        Inject Serena MCP configuration into ~/.claude.json.

        This operation:
        1. Creates a backup of the existing config
        2. Adds/updates Serena MCP server entry
        3. Preserves all other mcpServers entries
        4. Uses atomic write (temp file + replace)
        5. Rolls back on failure

        Args:
            project_root: Path to the project root directory

        Returns:
            Dictionary containing:
                - success (bool): True if injection succeeded
                - backup_path (str | None): Path to backup file
                - error (str | None): Error message if failed
        """
        result = {"success": False, "backup_path": None, "error": None}
        backup_path = None

        try:
            # Step 1: Load existing config or create new one
            config = self._load_config()

            # Step 2: Create backup before modifications
            if self.claude_config_path.exists():
                backup_path = self._backup_claude_config()
                result["backup_path"] = str(backup_path)

            # Step 3: Add/update Serena configuration
            config = self._add_serena_config(config, project_root)

            # Step 4: Validate the modified config
            if not self._validate_serena_config(config):
                result["error"] = "Invalid Serena configuration generated"
                if backup_path:
                    self._restore_backup(backup_path)
                return result

            # Step 5: Write atomically
            self._atomic_write(config)

            result["success"] = True
            logger.info(f"Successfully injected Serena MCP config into {self.claude_config_path}")

        except json.JSONDecodeError as e:
            result["error"] = f"Invalid JSON in config file: {e}"
            logger.error(f"JSON decode error: {e}")
            if backup_path:
                self._restore_backup(backup_path)
        except OSError as e:
            result["error"] = f"IO error: {e}"
            logger.error(f"IO error during injection: {e}")
            if backup_path:
                self._restore_backup(backup_path)
        except Exception as e:
            result["error"] = f"Unexpected error: {e}"
            logger.error(f"Unexpected error during injection: {e}")
            if backup_path:
                self._restore_backup(backup_path)

        return result

    def remove_serena(self) -> dict[str, Any]:
        """
        Remove Serena MCP configuration from ~/.claude.json.

        Preserves all other mcpServers entries.

        Returns:
            Dictionary containing:
                - success (bool): True if removal succeeded
                - message (str | None): Informational message
                - error (str | None): Error message if failed
        """
        result = {"success": False, "message": None, "error": None}
        backup_path = None

        try:
            # If config doesn't exist, nothing to remove
            if not self.claude_config_path.exists():
                result["success"] = True
                result["message"] = "Config file not found, nothing to remove"
                return result

            # Load existing config
            config = self._load_config()

            # Create backup
            backup_path = self._backup_claude_config()

            # Remove serena entry if it exists
            if "mcpServers" in config and "serena" in config["mcpServers"]:
                del config["mcpServers"]["serena"]
                logger.info("Removed Serena MCP from config")
            else:
                result["success"] = True
                result["message"] = "Serena not found in config"
                return result

            # Write atomically
            self._atomic_write(config)

            result["success"] = True
            result["message"] = "Serena MCP removed successfully"
            logger.info(f"Successfully removed Serena MCP from {self.claude_config_path}")

        except Exception as e:
            result["error"] = f"Error removing Serena: {e}"
            logger.error(f"Error during removal: {e}")
            if backup_path:
                self._restore_backup(backup_path)

        return result

    def _load_config(self) -> dict[str, Any]:
        """
        Load the Claude configuration file.

        Returns:
            Config dictionary, or empty config if file doesn't exist
        """
        if not self.claude_config_path.exists():
            return {"mcpServers": {}}

        try:
            config_text = self.claude_config_path.read_text(encoding="utf-8")
            config = json.loads(config_text)

            # Ensure mcpServers section exists
            if "mcpServers" not in config:
                config["mcpServers"] = {}

            return config
        except json.JSONDecodeError as e:
            raise json.JSONDecodeError(f"Invalid JSON in {self.claude_config_path}", e.doc, e.pos)

    def _backup_claude_config(self) -> Path:
        """
        Create a backup of the current config file.

        Returns:
            Path to the backup file
        """
        # Ensure backup directory exists
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        # Create timestamped backup filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"claude_config_backup_{timestamp}.json"

        # Copy the file
        shutil.copy2(self.claude_config_path, backup_path)
        logger.debug(f"Created backup at {backup_path}")

        return backup_path

    def _restore_backup(self, backup_path: Path) -> None:
        """
        Restore configuration from a backup file.

        Args:
            backup_path: Path to the backup file to restore
        """
        try:
            shutil.copy2(backup_path, self.claude_config_path)
            logger.info(f"Restored config from backup {backup_path}")
        except Exception as e:
            logger.error(f"Failed to restore backup: {e}")

    def _add_serena_config(self, config: dict[str, Any], project_root: Path) -> dict[str, Any]:
        """
        Add Serena MCP server configuration to config dict.

        Args:
            config: Existing config dictionary
            project_root: Path to the project root

        Returns:
            Modified config dictionary
        """
        # Ensure mcpServers section exists
        if "mcpServers" not in config:
            config["mcpServers"] = {}

        # Add Serena configuration
        config["mcpServers"]["serena"] = {
            "command": "uvx",
            "args": ["serena"],
            "env": {"SERENA_PROJECT_ROOT": str(project_root)},
        }

        return config

    def _validate_serena_config(self, config: dict[str, Any]) -> bool:
        """
        Validate that the Serena configuration is correct.

        Args:
            config: Config dictionary to validate

        Returns:
            True if valid, False otherwise
        """
        try:
            # Check structure
            if "mcpServers" not in config:
                return False

            if "serena" not in config["mcpServers"]:
                return False

            serena_config = config["mcpServers"]["serena"]

            # Validate required fields
            if serena_config.get("command") != "uvx":
                return False

            if serena_config.get("args") != ["serena"]:
                return False

            if "env" not in serena_config:
                return False

            if "SERENA_PROJECT_ROOT" not in serena_config["env"]:
                return False

            return True

        except Exception as e:
            logger.error(f"Validation error: {e}")
            return False

    def _atomic_write(self, config: dict[str, Any]) -> None:
        """
        Write configuration atomically using temp file + replace.

        This ensures that the config file is never in a partially-written state.

        Args:
            config: Configuration dictionary to write
        """
        # Ensure parent directory exists
        self.claude_config_path.parent.mkdir(parents=True, exist_ok=True)

        # Create temp file in the same directory (ensures same filesystem)
        temp_fd, temp_path = tempfile.mkstemp(
            dir=self.claude_config_path.parent, prefix=".claude_temp_", suffix=".json"
        )

        try:
            # Write to temp file
            with open(temp_fd, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
                f.flush()

            # Atomically replace the original file
            temp_path_obj = Path(temp_path)
            temp_path_obj.replace(self.claude_config_path)

            logger.debug(f"Atomically wrote config to {self.claude_config_path}")

        except Exception as e:
            # Clean up temp file on error
            try:
                Path(temp_path).unlink(missing_ok=True)
            except Exception:
                pass  # nosec B110 - temp file cleanup
            raise e
