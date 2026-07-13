# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Migration status checker for startup validation.

Read-only check: compares the current database revision against the Alembic
head revision. Does NOT run any migrations. If they differ, the caller should
surface a warning and prompt the user to run update.py.
"""

import logging
import os
from pathlib import Path


logger = logging.getLogger(__name__)


async def check_pending_migrations(state) -> bool:
    """Check whether the database has unapplied Alembic migrations.

    Uses a synchronous SQLAlchemy engine for the one-time MigrationContext
    check because Alembic's runtime migration API does not support async
    connections.

    Handles both single-chain (CE) and multi-chain (SaaS) Alembic setups by
    using the plural ``get_heads()`` / ``get_current_heads()`` APIs and
    comparing as sets. The SaaS chain is included dynamically when
    ``GILJO_MODE == "saas"`` and ``migrations/saas_versions/`` exists, matching
    the logic in ``migrations/env.py``.

    Args:
        state: APIState instance. Must have db_manager initialised with a
               valid database_url before this function is called.

    Returns:
        True if the database is missing any head revisions, False if all
        heads are present in ``alembic_version`` or if the check cannot be
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
        # Mirror migrations/env.py: when running in SaaS/Demo mode, also include
        # the SaaS migration chain so multi-head deployments are recognised here
        # (the bare alembic CLI only sees alembic.ini's static version_locations,
        # which is the CE chain only).
        giljo_mode = os.environ.get("GILJO_MODE", "ce").lower()
        migrations_dir = Path.cwd() / "migrations"
        version_locations = [str(migrations_dir / "versions")]
        saas_versions_dir = migrations_dir / "saas_versions"
        # BE-3002a: gate on the explicit SaaS value, never `!= "ce"` (banned
        # CE-guard pattern); mirrors migrations/env.py.
        if saas_versions_dir.is_dir() and giljo_mode == "saas":
            version_locations.append(str(saas_versions_dir))
        alembic_cfg.set_main_option("version_locations", os.pathsep.join(version_locations))

        script = ScriptDirectory.from_config(alembic_cfg)
        heads = set(script.get_heads())
    except Exception as exc:
        logger.warning("Could not read Alembic script directory: %s", exc)
        return False

    if not heads:
        logger.warning("Alembic script directory has no heads — skipping migration check")
        return False

    # The async engine uses the asyncpg driver. Alembic's MigrationContext
    # requires a synchronous connection, so we derive a sync URL from the
    # stored database_url (which already contains the psycopg2 sync driver).
    try:
        raw_url = state.db_manager.database_url
        if not raw_url:
            async_url = str(state.db_manager.async_engine.url)
            raw_url = async_url.replace("+asyncpg", "")

        engine = create_engine(raw_url)
        try:
            with engine.connect() as conn:
                context = MigrationContext.configure(conn)
                current_heads = set(context.get_current_heads())
        finally:
            engine.dispose()
    except Exception as exc:
        logger.warning("Could not connect to database for migration check: %s", exc)
        return False

    missing = heads - current_heads
    if missing:
        logger.warning(
            "Pending migrations detected — missing heads: %s (current: %s, expected: %s)",
            sorted(missing),
            sorted(current_heads),
            sorted(heads),
        )
        return True

    logger.debug("Database is up to date (heads: %s)", sorted(current_heads))
    return False


def get_pending_migration_info(state) -> dict | None:
    """Return ``{"pending": int, "head": str}`` when migrations are pending, else None.

    Synchronous (mirrors ``check_pending_migrations``' use of a sync engine for
    the MigrationContext check). Used by the system-banner emitter to populate
    the ``system.pending_migrations`` notification payload. Never raises — a
    check failure returns None so banner emission degrades to "no banner".
    """
    try:
        from alembic.config import Config
        from alembic.runtime.migration import MigrationContext
        from alembic.script import ScriptDirectory
        from sqlalchemy import create_engine
    except ImportError:
        return None

    alembic_ini = Path.cwd() / "alembic.ini"
    if not alembic_ini.exists() or state.db_manager is None:
        return None

    try:
        alembic_cfg = Config(str(alembic_ini))
        giljo_mode = os.environ.get("GILJO_MODE", "ce").lower()
        migrations_dir = Path.cwd() / "migrations"
        version_locations = [str(migrations_dir / "versions")]
        saas_versions_dir = migrations_dir / "saas_versions"
        # BE-3002a: gate on the explicit SaaS value, never `!= "ce"` (banned
        # CE-guard pattern); mirrors migrations/env.py.
        if saas_versions_dir.is_dir() and giljo_mode == "saas":
            version_locations.append(str(saas_versions_dir))
        alembic_cfg.set_main_option("version_locations", os.pathsep.join(version_locations))

        script = ScriptDirectory.from_config(alembic_cfg)
        heads = set(script.get_heads())
        if not heads:
            return None

        raw_url = state.db_manager.database_url
        if not raw_url:
            raw_url = str(state.db_manager.async_engine.url).replace("+asyncpg", "")

        engine = create_engine(raw_url)
        try:
            with engine.connect() as conn:
                context = MigrationContext.configure(conn)
                current_heads = set(context.get_current_heads())
        finally:
            engine.dispose()
    except Exception as exc:
        logger.warning("Could not compute pending migration info: %s", exc)
        return None

    missing = heads - current_heads
    if not missing:
        return None
    return {"pending": len(missing), "head": sorted(heads)[-1]}
