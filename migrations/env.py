# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool


# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from giljo_mcp.models import Base


# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Override database URL with environment variable if set
# CRITICAL: PostgreSQL is REQUIRED - SQLite is not supported
from dotenv import load_dotenv


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
            "Note: Only PostgreSQL 14-18 is supported."
        )

config.set_main_option("sqlalchemy.url", db_url)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


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
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
