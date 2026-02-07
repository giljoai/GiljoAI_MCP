"""
SetupStateManager - Manages setup state with hybrid file/database storage.

Implements hybrid storage strategy:
- Bootstrap phase: Uses ~/.giljo-mcp/setup_state.json file
- After database creation: Migrates to database
- File as fallback if database unavailable

Provides:
- Version tracking (setup_version, schema_version, app_version)
- State machine (NOT_STARTED → IN_PROGRESS → COMPLETED → VALIDATED)
- Multi-tenant isolation
- Configuration snapshots for rollback
- Feature and tool tracking
"""

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

class SetupStateManager:
    """
    Manages setup state with hybrid file/database storage.

    Uses file-based storage during bootstrap, migrates to database when available.
    Implements singleton pattern per tenant for consistency.
    """

    _instances: dict[str, "SetupStateManager"] = {}
    _lock = Lock()

    def __init__(
        self,
        tenant_key: str | None = None,
        db_session: Session | None = None,
        current_version: str | None = None,
        required_db_version: str | None = None,
    ):
        """
        Initialize SetupStateManager.

        Args:
            tenant_key: Tenant identifier (required)
            db_session: Optional database session for database operations
            current_version: Current application version for validation
            required_db_version: Required database version for validation

        Raises:
            ValueError: If tenant_key is None
        """
        if tenant_key is None:
            raise ValueError("tenant_key is required")

        self.tenant_key = tenant_key
        self.db_session = db_session
        self.current_version = current_version
        self.required_db_version = required_db_version

        # File storage location
        self.state_dir = Path.home() / ".giljo-mcp"
        self.state_file = self.state_dir / "setup_state.json"

        # File lock for concurrent access
        self._file_lock = Lock()

    @classmethod
    def get_instance(
        cls,
        tenant_key: str,
        db_session: Session | None = None,
        current_version: str | None = None,
        required_db_version: str | None = None,
    ) -> "SetupStateManager":
        """
        Get singleton instance for tenant.

        Args:
            tenant_key: Tenant identifier
            db_session: Optional database session
            current_version: Optional current version
            required_db_version: Optional required database version

        Returns:
            SetupStateManager instance for tenant
        """
        with cls._lock:
            if tenant_key not in cls._instances:
                cls._instances[tenant_key] = cls(
                    tenant_key=tenant_key,
                    db_session=db_session,
                    current_version=current_version,
                    required_db_version=required_db_version,
                )
            return cls._instances[tenant_key]

    def get_state(self) -> dict[str, Any]:
        """
        Get current setup state.

        Strategy:
        1. Try database first (if session available)
        2. Fall back to file if database fails
        3. Return default state if neither available

        Returns:
            Dict containing setup state
        """
        # Try database first
        if self.db_session is not None:
            try:
                state_dict = self._get_state_from_database()
                if state_dict is not None:
                    return state_dict
            except SQLAlchemyError as e:
                logger.warning(
                    f"Failed to get state from database for tenant {self.tenant_key}: {e}. "
                    "Falling back to file storage."
                )

        # Fall back to file
        try:
            state_dict = self._get_state_from_file()
            if state_dict is not None:
                return state_dict
        except (OSError, json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"Failed to get state from file for tenant {self.tenant_key}: {e}. Returning default state.")

        # Return default state
        return self._get_default_state()

    def _get_state_from_database(self) -> dict[str, Any | None]:
        """Get state from database."""
        from src.giljo_mcp.models import SetupState

        state = SetupState.get_by_tenant(self.db_session, self.tenant_key)
        if state:
            return state.to_dict()
        return None

    def _get_state_from_file(self) -> dict[str, Any | None]:
        """Get state from file."""
        if not self.state_file.exists():
            return None

        with self._file_lock:
            try:
                with open(self.state_file) as f:
                    data = json.load(f)

                # Filter to current tenant
                if data.get("tenant_key") == self.tenant_key:
                    return data

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse setup state file: {e}")
                return None

        return None

    def _get_default_state(self) -> dict[str, Any]:
        """Get default state structure."""
        return {
            "tenant_key": self.tenant_key,
            "database_initialized": False,
            "database_initialized_at": None,
            "setup_version": None,
            "database_version": None,
            "python_version": None,
            "node_version": None,
            "features_configured": {},
            "tools_enabled": [],
            "config_snapshot": None,
            "validation_passed": True,
            "validation_failures": [],
            "validation_warnings": [],
            "last_validation_at": None,
            "installer_version": None,
            "install_mode": None,
            "install_path": None,
            "meta_data": {},
        }

    def mark_database_initialized(
        self,
        setup_version: str | None = None,
        config_snapshot: dict[str, Any | None] = None,
    ) -> None:
        """
        Mark database as initialized (tables created and ready for use).

        Args:
            setup_version: Version to set (validates semantic versioning)
            config_snapshot: Optional config snapshot for rollback

        Raises:
            ValueError: If setup_version has invalid format
        """
        # Validate version format if provided
        if setup_version is not None:
            self._validate_version_format(setup_version)

        # Try database first
        if self.db_session is not None:
            try:
                self._mark_database_initialized_in_database(setup_version, config_snapshot)
                logger.info(f"Marked database initialized in database for tenant {self.tenant_key}")
                return
            except SQLAlchemyError as e:
                logger.warning(
                    f"Failed to mark database initialized in database for tenant {self.tenant_key}: {e}. "
                    "Falling back to file storage."
                )

        # Fall back to file
        self._mark_database_initialized_in_file(setup_version, config_snapshot)
        logger.info(f"Marked database initialized in file for tenant {self.tenant_key}")

    def _mark_database_initialized_in_database(
        self,
        setup_version: str | None,
        config_snapshot: dict[str, Any | None],
    ) -> None:
        """Mark database initialized in database."""
        from src.giljo_mcp.models import SetupState

        state = SetupState.create_or_update(
            self.db_session,
            tenant_key=self.tenant_key,
            database_initialized=True,
            database_initialized_at=datetime.now(timezone.utc),
            setup_version=setup_version,
            config_snapshot=config_snapshot,
        )

        self.db_session.commit()

    def _mark_database_initialized_in_file(
        self,
        setup_version: str | None,
        config_snapshot: dict[str, Any | None],
    ) -> None:
        """Mark database initialized in file."""
        # Ensure directory exists
        self.state_dir.mkdir(parents=True, exist_ok=True)

        # Get current state or default
        state = self._get_state_from_file()
        if state is None:
            state = self._get_default_state()

        # Update state
        state["database_initialized"] = True
        state["database_initialized_at"] = datetime.now(timezone.utc).isoformat()
        if setup_version:
            state["setup_version"] = setup_version
        if config_snapshot:
            state["config_snapshot"] = config_snapshot

        # Write to file
        with self._file_lock:
            with open(self.state_file, "w") as f:
                json.dump(state, f, indent=2)

            # Set secure permissions (Unix only)
            import platform

            if platform.system() != "Windows":
                import os

                os.chmod(self.state_file, 0o600)

    def update_state(self, **kwargs) -> None:
        """
        Update setup state with provided fields.

        Args:
            **kwargs: Fields to update in state
        """
        # Try database first
        if self.db_session is not None:
            try:
                self._update_state_in_database(**kwargs)
                return
            except SQLAlchemyError as e:
                logger.warning(
                    f"Failed to update state in database for tenant {self.tenant_key}: {e}. "
                    "Falling back to file storage."
                )

        # Fall back to file
        self._update_state_in_file(**kwargs)

    def _update_state_in_database(self, **kwargs) -> None:
        """Update state in database."""
        from src.giljo_mcp.models import SetupState

        SetupState.create_or_update(self.db_session, tenant_key=self.tenant_key, **kwargs)

        self.db_session.commit()

    def _update_state_in_file(self, **kwargs) -> None:
        """Update state in file."""
        # Ensure directory exists
        self.state_dir.mkdir(parents=True, exist_ok=True)

        # Get current state or default
        state = self._get_state_from_file()
        if state is None:
            state = self._get_default_state()

        # Update fields
        for key, value in kwargs.items():
            state[key] = value

        # Write to file
        with self._file_lock:
            with open(self.state_file, "w") as f:
                json.dump(state, f, indent=2)

            # Set secure permissions (Unix only)
            import platform

            if platform.system() != "Windows":
                import os

                os.chmod(self.state_file, 0o600)

    def migrate_file_to_database(self) -> bool:
        """
        Migrate file-based state to database.

        Returns:
            True if migration successful, False otherwise
        """
        if self.db_session is None:
            logger.error("Cannot migrate: no database session provided")
            return False

        # Get state from file
        file_state = self._get_state_from_file()
        if file_state is None:
            logger.info("No file state to migrate")
            return False

        try:
            from src.giljo_mcp.models import SetupState

            # Create or update database state
            SetupState.create_or_update(
                self.db_session,
                tenant_key=self.tenant_key,
                database_initialized=file_state.get("database_initialized", False),
                database_initialized_at=(
                    datetime.fromisoformat(file_state["database_initialized_at"])
                    if file_state.get("database_initialized_at")
                    else None
                ),
                setup_version=file_state.get("setup_version"),
                database_version=file_state.get("database_version"),
                python_version=file_state.get("python_version"),
                node_version=file_state.get("node_version"),
                features_configured=file_state.get("features_configured", {}),
                tools_enabled=file_state.get("tools_enabled", []),
                config_snapshot=file_state.get("config_snapshot"),
                validation_passed=file_state.get("validation_passed", True),
                validation_failures=file_state.get("validation_failures", []),
                validation_warnings=file_state.get("validation_warnings", []),
                installer_version=file_state.get("installer_version"),
                install_mode=file_state.get("install_mode"),
                install_path=file_state.get("install_path"),
                meta_data=file_state.get("meta_data", {}),
            )

            self.db_session.commit()
            logger.info(f"Successfully migrated file state to database for tenant {self.tenant_key}")
            return True

        except SQLAlchemyError as e:
            logger.error(f"Failed to migrate file state to database: {e}")
            self.db_session.rollback()
            return False

    def requires_migration(self) -> bool:
        """
        Check if state requires migration to new version.

        Returns:
            True if migration needed, False otherwise
        """
        if self.current_version is None:
            return False

        state = self.get_state()
        stored_version = state.get("setup_version")

        if stored_version is None:
            return False

        # Compare versions
        return stored_version != self.current_version

    def validate_state(self) -> tuple[bool, list[str]]:
        """
        Validate current state against requirements.

        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []
        state = self.get_state()

        # Check version compatibility
        if self.current_version and state.get("setup_version"):
            if state["setup_version"] != self.current_version:
                errors.append(
                    f"Setup version mismatch: stored={state['setup_version']}, current={self.current_version}"
                )

        # Check database version
        if self.required_db_version and state.get("database_version"):
            if state["database_version"] != self.required_db_version:
                errors.append(
                    f"Database version mismatch: stored={state['database_version']}, "
                    f"required={self.required_db_version}"
                )

        # Check validation failures
        validation_failures = state.get("validation_failures", [])
        if validation_failures:
            errors.append(f"Setup has {len(validation_failures)} validation failures")

        is_valid = len(errors) == 0
        return is_valid, errors

    def migrate_state(
        self,
        new_setup_version: str,
        new_database_version: str | None = None,
    ) -> None:
        """
        Migrate state to new version.

        Args:
            new_setup_version: New setup version
            new_database_version: Optional new database version
        """
        self._validate_version_format(new_setup_version)

        updates = {
            "setup_version": new_setup_version,
        }

        if new_database_version:
            updates["database_version"] = new_database_version

        self.update_state(**updates)
        logger.info(f"Migrated state for tenant {self.tenant_key} to version {new_setup_version}")

    def add_validation_failure(self, message: str) -> None:
        """
        Add validation failure message.

        Args:
            message: Error message
        """
        if self.db_session is not None:
            try:
                from src.giljo_mcp.models import SetupState

                state = SetupState.get_by_tenant(self.db_session, self.tenant_key)
                if state:
                    state.add_validation_failure(message)
                    self.db_session.commit()
                    return
            except SQLAlchemyError as e:
                logger.warning(f"Failed to add validation failure to database: {e}")

        # Fall back to file
        current_state = self.get_state()
        failures = list(current_state.get("validation_failures", []))
        failures.append({"message": message, "timestamp": datetime.now(timezone.utc).isoformat()})

        self.update_state(
            validation_failures=failures, validation_passed=False, last_validation_at=datetime.now(timezone.utc).isoformat()
        )

    def add_validation_warning(self, message: str) -> None:
        """
        Add validation warning message.

        Args:
            message: Warning message
        """
        if self.db_session is not None:
            try:
                from src.giljo_mcp.models import SetupState

                state = SetupState.get_by_tenant(self.db_session, self.tenant_key)
                if state:
                    state.add_validation_warning(message)
                    self.db_session.commit()
                    return
            except SQLAlchemyError as e:
                logger.warning(f"Failed to add validation warning to database: {e}")

        # Fall back to file
        current_state = self.get_state()
        warnings = list(current_state.get("validation_warnings", []))
        warnings.append({"message": message, "timestamp": datetime.now(timezone.utc).isoformat()})

        self.update_state(validation_warnings=warnings, last_validation_at=datetime.now(timezone.utc).isoformat())

    def reset_state(self) -> None:
        """
        Reset setup state (for testing and recovery).

        Deletes state from database and file.
        """
        # Remove from database
        if self.db_session is not None:
            try:
                from src.giljo_mcp.models import SetupState

                state = SetupState.get_by_tenant(self.db_session, self.tenant_key)
                if state:
                    self.db_session.delete(state)
                    self.db_session.commit()
                    logger.info(f"Deleted setup state from database for tenant {self.tenant_key}")
            except SQLAlchemyError as e:
                logger.error(f"Failed to delete state from database: {e}")
                self.db_session.rollback()

        # Remove file
        if self.state_file.exists():
            try:
                # Only remove if it's for this tenant
                state = self._get_state_from_file()
                if state and state.get("tenant_key") == self.tenant_key:
                    self.state_file.unlink()
                    logger.info(f"Deleted setup state file for tenant {self.tenant_key}")
            except (OSError, json.JSONDecodeError, KeyError, ValueError) as e:
                logger.error(f"Failed to delete state file: {e}")

    def add_configured_feature(self, feature_name: str, feature_config: Any = True) -> None:
        """
        Add a configured feature.

        Args:
            feature_name: Name of the feature
            feature_config: Configuration value (True/False or dict)
        """
        current_state = self.get_state()
        features = dict(current_state.get("features_configured", {}))
        features[feature_name] = feature_config

        self.update_state(features_configured=features)

    def add_enabled_tool(self, tool_name: str) -> None:
        """
        Add an enabled MCP tool.

        Args:
            tool_name: Name of the tool
        """
        current_state = self.get_state()
        tools = list(current_state.get("tools_enabled", []))

        if tool_name not in tools:
            tools.append(tool_name)
            self.update_state(tools_enabled=tools)

    def has_feature(self, feature_path: str) -> bool:
        """
        Check if a feature is configured.

        Supports nested paths using dot notation: "api.enabled"

        Args:
            feature_path: Dot-separated path to feature

        Returns:
            True if feature is configured and truthy, False otherwise
        """
        state = self.get_state()
        features = state.get("features_configured", {})

        if not features:
            return False

        keys = feature_path.split(".")
        value = features

        for key in keys:
            if not isinstance(value, dict) or key not in value:
                return False
            value = value[key]

        return bool(value)

    def get_config_snapshot(self) -> dict[str, Any | None]:
        """
        Get configuration snapshot.

        Returns:
            Config snapshot dict or None
        """
        state = self.get_state()
        return state.get("config_snapshot")

    def _validate_version_format(self, version: str) -> None:
        """
        Validate semantic versioning format.

        Args:
            version: Version string to validate

        Raises:
            ValueError: If version format is invalid
        """
        # Semantic versioning pattern: MAJOR.MINOR.PATCH[-prerelease]
        pattern = r"^[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9\.\-]+)?$"

        if not re.match(pattern, version):
            raise ValueError(
                f"Invalid version format: {version}. Expected semantic versioning (e.g., 1.0.0, 2.1.0-beta)"
            )
