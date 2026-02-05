"""Database initialization module

Handles database connection, table creation, and configuration loading.
Extracted from api/app.py lifespan function (lines ~160-214).
"""

import os

from api.app import APIState
from src.giljo_mcp.config_manager import get_config
from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.logging import get_logger, ErrorCode
from src.giljo_mcp.system_prompts import SystemPromptService


logger = get_logger(__name__)


async def init_database(state: APIState) -> None:
    """Initialize database connection and configuration

    Args:
        state: APIState instance to populate with db_manager, config, and system_prompt_service

    Raises:
        ValueError: If database URL is not configured
        Exception: If database initialization fails
    """
    try:
        # Initialize configuration
        logger.info("Initializing configuration...")
        state.config = get_config()  # Use the singleton getter
        logger.info("Configuration loaded successfully")
        # v3.0: DeploymentMode removed - server always binds 0.0.0.0, firewall controls access
    except Exception as e:
        logger.error(
            "config_load_failed",
            error_code=ErrorCode.API_INTERNAL_ERROR.value,
            error_message=str(e),
            exc_info=True,
        )
        raise

    # v3.0: Setup mode removed - all access requires authentication

    # Initialize database (ALWAYS - install.py creates DB before API starts)
    # v3.0: No "setup mode without database" - database exists from installation
    # Check for DATABASE_URL in environment first
    logger.info("Initializing database connection...")
    db_url = os.getenv("DATABASE_URL")

    if db_url:
        logger.info("Using DATABASE_URL from environment")
    elif state.config.database:
        # Construct database URL using configuration manager (handles env + migrations)
        try:
            logger.info("Constructing database URL from configuration manager")
            db_url = state.config.database.get_connection_string()
            logger.debug(
                f"Database config: host={state.config.database.host}, port={state.config.database.port}, database={state.config.database.database_name}"
            )
        except Exception as e:
            logger.error(
                "database_url_build_failed",
                error_code=ErrorCode.DB_CONNECTION_FAILED.value,
                error_message=str(e),
            )
            raise

    if not db_url:
        logger.error(
            "database_config_missing",
            error_code=ErrorCode.DB_CONNECTION_FAILED.value,
        )
        raise ValueError("Database URL not configured. PostgreSQL is required.")

    logger.info(
        f"Connecting to database: {db_url.split('@')[-1] if '@' in db_url else db_url}"
    )

    try:
        state.db_manager = DatabaseManager(db_url, is_async=True)
        logger.info("Database manager created successfully")

        logger.info("Creating database tables...")
        await state.db_manager.create_tables_async()
        logger.info("Database tables created/verified successfully")

        state.system_prompt_service = SystemPromptService(state.db_manager)
        logger.info("System prompt service initialized")
    except Exception as e:
        logger.error(
            "database_init_failed",
            error_code=ErrorCode.DB_CONNECTION_FAILED.value,
            error_message=str(e),
            exc_info=True,
        )
        raise
