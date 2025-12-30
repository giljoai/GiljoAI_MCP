"""Validation initialization module

Handles setup state validation and version checking on startup.
Extracted from api/app.py lifespan function (lines ~461-507).
"""

import logging
from pathlib import Path

import yaml

from api.app import APIState


logger = logging.getLogger(__name__)


async def init_validation(state: APIState) -> None:
    """Validate setup state and version on startup

    Args:
        state: APIState instance with db_manager initialized

    Note:
        Does not raise on failure - logs warnings and continues startup
    """
    # Check setup state on startup (version tracking and validation)
    if state.db_manager:
        try:
            logger.info("Checking setup state...")

            # Get current version from config
            from src.giljo_mcp.setup.state_manager import SetupStateManager

            config_path = Path.cwd() / "config.yaml"
            if config_path.exists():
                with open(config_path) as f:
                    config_data = yaml.safe_load(f) or {}
                current_version = config_data.get("installation", {}).get("version", "2.0.0")
                db_version = "18"  # PostgreSQL 18

                # Initialize state manager with versions
                state_manager = SetupStateManager.get_instance(
                    tenant_key="default",
                    current_version=current_version,
                    required_db_version=db_version,
                )

                # Check if migration needed
                if state_manager.requires_migration():
                    logger.warning("⚠️ Setup state version mismatch detected!")
                    logger.warning(f"Current version: {current_version}")
                    setup_state = state_manager.get_state()
                    logger.warning(f"Stored version: {setup_state.get('setup_version')}")
                    logger.warning("Run POST /api/setup/migrate to update state")
                else:
                    logger.info("Setup state version is current")

                # Validate current state
                valid, failures = state_manager.validate_state()
                if not valid:
                    logger.warning("⚠️ Setup validation failures detected:")
                    for failure in failures:
                        logger.warning(f"  - {failure}")
                    logger.warning("Review setup configuration or run migration")
                else:
                    logger.info("Setup state validation passed")

        except Exception as e:
            logger.error(f"Startup setup check failed: {e}", exc_info=True)
            # Don't crash the app on startup check failure
            logger.warning("Continuing startup despite setup check failure")
