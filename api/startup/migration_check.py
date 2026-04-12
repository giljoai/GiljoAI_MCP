# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""Migration status checker for startup validation.

Read-only check: compares the current database revision against the Alembic
head revision. Does NOT run any migrations. If they differ, the caller should
surface a warning and prompt the user to run update.py.
"""

import logging
from pathlib import Path


logger = logging.getLogger(__name__)


async def check_pending_migrations(state) -> bool:
    """Check whether the database has unapplied Alembic migrations.

    Uses a synchronous SQLAlchemy engine for the one-time MigrationContext
    check because Alembic's runtime migration API does not support async
    connections.

    Args:
        state: APIState instance. Must have db_manager initialised with a
               valid database_url before this function is called.

    Returns:
        True if the database revision differs from the current Alembic head,
        False if the database is up to date or if the check cannot be
        performed (e.g. alembic.ini is missing).

    Raises:
        Does not raise — all exceptions are caught and logged so that a
        check failure never blocks startup.
    """
    try:
        from alembic.config import Config
        from alembic.runtime.migration import MigrationContext
        from alembic.script import ScriptDirectory
        from sqlalchemy import create_engine
    except ImportError as exc:
        logger.warning("Alembic not available — skipping migration check: %s", exc)
        return False

    alembic_ini = Path.cwd() / "alembic.ini"
    if not alembic_ini.exists():
        logger.warning("alembic.ini not found at %s — skipping migration check", alembic_ini)
        return False

    if state.db_manager is None:
        logger.warning("db_manager not initialised — skipping migration check")
        return False

    try:
        alembic_cfg = Config(str(alembic_ini))
        script = ScriptDirectory.from_config(alembic_cfg)
        head = script.get_current_head()
    except Exception as exc:
        logger.warning("Could not read Alembic script directory: %s", exc)
        return False

    if head is None:
        logger.warning("Alembic head revision is None — skipping migration check")
        return False

    # The async engine uses the asyncpg driver. Alembic's MigrationContext
    # requires a synchronous connection, so we derive a sync URL from the
    # stored database_url (which already contains the psycopg2 sync driver).
    # db_manager.database_url is the synchronous URL; async_engine.url has
    # +asyncpg. We prefer database_url if available to stay driver-agnostic.
    try:
        raw_url = state.db_manager.database_url
        if not raw_url:
            # Fall back to deriving from the async engine URL
            async_url = str(state.db_manager.async_engine.url)
            raw_url = async_url.replace("+asyncpg", "")

        engine = create_engine(raw_url)
        try:
            with engine.connect() as conn:
                context = MigrationContext.configure(conn)
                current = context.get_current_revision()
        finally:
            engine.dispose()
    except Exception as exc:
        logger.warning("Could not connect to database for migration check: %s", exc)
        return False

    if current != head:
        logger.warning(
            "Pending migrations detected — current: %s, head: %s",
            current,
            head,
        )
        return True

    logger.debug("Database is up to date (revision: %s)", current)
    return False
