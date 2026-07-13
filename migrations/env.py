# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import engine_from_config, pool


# Add src to path for imports
# TODO: Remove after editable install confirmed on all platforms
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from giljo_mcp.models import Base


# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Override database URL with environment variable if set
# CRITICAL: PostgreSQL is REQUIRED - SQLite is not supported


load_dotenv()  # Load .env file

db_url = os.getenv("DATABASE_URL")
if not db_url:
    # Try to construct from individual env vars
    db_host = os.getenv("POSTGRES_HOST", "localhost")
    db_port = os.getenv("POSTGRES_PORT", "5432")
    db_name = os.getenv("POSTGRES_DB", "giljo_mcp")
    db_user = os.getenv("POSTGRES_USER", "giljo_user")
    db_pass = os.getenv("POSTGRES_PASSWORD")

    if db_pass:
        db_url = f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
    else:
        raise ValueError(
            "PostgreSQL connection not configured!\n\n"
            "The installer should have created .env with POSTGRES_PASSWORD.\n"
            "If running migrations manually, ensure .env exists with:\n"
            "  POSTGRES_PASSWORD=<your_password>\n\n"
            "Note: PostgreSQL 18+ is required."
        )

config.set_main_option("sqlalchemy.url", db_url)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
# Programmatic callers may opt out of logging setup by setting
# config.attributes["configure_logger"] = False (standard alembic idiom);
# plain `alembic upgrade head` keeps alembic.ini's INFO logging unchanged.
if config.config_file_name is not None and config.attributes.get("configure_logger", True):
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

# --- Dual-chain migration support ---
# Always include CE migrations. Conditionally include SaaS migrations
# when the directory exists AND GILJO_MODE is "saas".
#
# CLI GOTCHA: alembic's `current`, `heads`, and other enumeration commands
# build ScriptDirectory from alembic.ini's static version_locations BEFORE
# env.py runs, so the dynamic SaaS-chain inclusion below ONLY takes effect
# for migration-execution commands invoked through env.py (i.e. when run via
# startup.py / startup_demo.py). Direct `alembic current` invocations against
# a SaaS-stamped DB will fail with "Can't locate revision" because the CLI
# only sees the CE chain. Use scripts/alembic_cli.py for a wrapper that loads
# both chains for CLI debugging, or trust that startup_demo.py / startup.py
# is the supported migration entry point.
giljo_mode = os.environ.get("GILJO_MODE", "ce").lower()
migrations_dir = Path(__file__).parent

version_locations = [str(migrations_dir / "versions")]

saas_versions_dir = migrations_dir / "saas_versions"
# BE-3002a: gate on the explicit SaaS value, never `!= "ce"` (banned CE-guard
# pattern). The only recognised modes are "" (CE) and "saas"; treat anything
# that is not "saas" as CE so the SaaS chain is opt-in.
if saas_versions_dir.is_dir() and giljo_mode == "saas":
    version_locations.append(str(saas_versions_dir))


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        version_locations=version_locations,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            version_locations=version_locations,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
