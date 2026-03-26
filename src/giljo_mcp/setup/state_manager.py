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
from pathlib import Path
from threading import Lock
from typing import Any, ClassVar

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session


logger = logging.getLogger(__name__)


class SetupStateManager:
    """
    Manages setup state with hybrid file/database storage.

    Uses file-based storage during bootstrap, migrates to database when available.
    Implements singleton pattern per tenant for consistency.
    """

    _instances: ClassVar[dict[str, "SetupStateManager"]] = {}
    _lock: ClassVar[Lock] = Lock()

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

            except json.JSONDecodeError:
                logger.exception("Failed to parse setup state file")
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
        }

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
                from pathlib import Path

                Path(self.state_file).chmod(0o600)

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
        if self.current_version and state.get("setup_version") and state["setup_version"] != self.current_version:
            errors.append(f"Setup version mismatch: stored={state['setup_version']}, current={self.current_version}")

        # Check database version
        if (
            self.required_db_version
            and state.get("database_version")
            and state["database_version"] != self.required_db_version
        ):
            errors.append(
                f"Database version mismatch: stored={state['database_version']}, required={self.required_db_version}"
            )

        # Check validation failures
        validation_failures = state.get("validation_failures", [])
        if validation_failures:
            errors.append(f"Setup has {len(validation_failures)} validation failures")

        is_valid = len(errors) == 0
        return is_valid, errors

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
