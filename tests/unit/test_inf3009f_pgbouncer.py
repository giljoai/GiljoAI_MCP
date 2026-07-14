# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""INF-3009f — PgBouncer transaction-pooling prerequisites (config-gated, default OFF).

Regression tests at the failing layer:
- P1: ``_create_async_engine`` prepared-statement disable, proven on the LIVE engine's
  merged asyncpg connect params (the layer ``DuplicatePreparedStatementError`` would
  fire at). Default OFF must be byte-identical (no connect_args at all).
- P2: the broker-DSN seam in ``init_websocket_broker`` — the broker must be able to
  take a DIRECT (unpooled) DSN so its session-pinned LISTEN survives, with a fallback
  to the app URL that is byte-identical when the var is unset.
- P3: a source guard that ``scripts/alembic_cli.py`` still resolves ``DATABASE_URL``
  first, which the railway preDeploy ``DATABASE_URL=$DATABASE_UNPOOLED_URL`` override
  relies on.

These tests touch NO database — SQLAlchemy engines are lazy (no connection until first
checkout), so constructing a DatabaseManager with a fake URL is safe and parallel-safe.
Env state is isolated via monkeypatch (no module-level mutable state, no ordering deps).
"""

import inspect
from pathlib import Path
from types import SimpleNamespace

import pytest

from giljo_mcp.database import DatabaseManager, _pgbouncer_connect_args


FAKE_URL = "postgresql://u:p@localhost:5432/giljo_inf3009f_fake"

# The three asyncpg keys P1 injects to make prepared statements pooling-safe.
_PGBOUNCER_KEYS = {
    "statement_cache_size",
    "prepared_statement_cache_size",
    "prepared_statement_name_func",
}


def _connect_params(manager: DatabaseManager) -> dict:
    """Return the FINAL merged asyncpg connect params off the live engine.

    SQLAlchemy folds user ``connect_args`` into the pool creator's closure
    (``cparams``) together with the host/user/db parsed from the URL, and that dict is
    exactly what is handed to ``asyncpg.connect`` at checkout — so it is the real proof
    of what the driver will do, not a mock of our own call.
    """
    creator = manager.async_engine.sync_engine.pool._creator
    return dict(inspect.getclosurevars(creator).nonlocals["cparams"])


class TestP1HelperContract:
    """The env gate itself: only ``GILJO_PGBOUNCER=1`` turns it on."""

    def test_returns_none_when_unset(self, monkeypatch):
        monkeypatch.delenv("GILJO_PGBOUNCER", raising=False)
        assert _pgbouncer_connect_args() is None

    def test_returns_none_for_non_one_values(self, monkeypatch):
        # Matches the GILJO_FORCE_HTTP == "1" idiom: anything but "1" is OFF.
        for value in ("0", "true", "yes", "on", ""):
            monkeypatch.setenv("GILJO_PGBOUNCER", value)
            assert _pgbouncer_connect_args() is None, f"{value!r} must be treated as OFF"

    def test_returns_disable_args_when_on(self, monkeypatch):
        monkeypatch.setenv("GILJO_PGBOUNCER", "1")
        args = _pgbouncer_connect_args()
        assert args is not None
        assert args["statement_cache_size"] == 0
        assert args["prepared_statement_cache_size"] == 0
        assert callable(args["prepared_statement_name_func"])

    def test_name_func_is_unique_per_call(self, monkeypatch):
        monkeypatch.setenv("GILJO_PGBOUNCER", "1")
        name_func = _pgbouncer_connect_args()["prepared_statement_name_func"]
        names = {name_func() for _ in range(100)}
        assert len(names) == 100, "each prepared-statement name must be unique (uuid)"
        assert all(n.startswith("__asyncpg_") for n in names)


class TestP1EngineOffIsByteIdentical:
    """DoD: flag OFF adds NO connect_args — behavior byte-identical to pre-INF-3009f."""

    def test_pooled_engine_has_no_pgbouncer_keys(self, monkeypatch):
        monkeypatch.delenv("GILJO_PGBOUNCER", raising=False)
        params = _connect_params(DatabaseManager(FAKE_URL, is_async=True))
        assert _PGBOUNCER_KEYS.isdisjoint(params), f"unexpected pooling keys: {params}"

    def test_null_pool_engine_has_no_pgbouncer_keys(self, monkeypatch):
        monkeypatch.delenv("GILJO_PGBOUNCER", raising=False)
        params = _connect_params(DatabaseManager(FAKE_URL, is_async=True, use_null_pool=True))
        assert _PGBOUNCER_KEYS.isdisjoint(params)


class TestP1EngineOnDisablesPreparedStatements:
    """DoD (fix works): flag ON puts statement_cache_size==0 on the live engine params."""

    def test_pooled_engine_disables_prepared_statements(self, monkeypatch):
        monkeypatch.setenv("GILJO_PGBOUNCER", "1")
        params = _connect_params(DatabaseManager(FAKE_URL, is_async=True))
        assert params["statement_cache_size"] == 0
        assert params["prepared_statement_cache_size"] == 0
        assert callable(params["prepared_statement_name_func"])

    def test_null_pool_engine_disables_prepared_statements(self, monkeypatch):
        """The test-harness NullPool async branch must gate too (correct behind a pooler)."""
        monkeypatch.setenv("GILJO_PGBOUNCER", "1")
        params = _connect_params(DatabaseManager(FAKE_URL, is_async=True, use_null_pool=True))
        assert params["statement_cache_size"] == 0
        assert params["prepared_statement_cache_size"] == 0

    def test_engine_still_builds_and_is_usable_when_on(self, monkeypatch):
        """Two-sided: turning the flag on still yields a working async engine (no crash)."""
        monkeypatch.setenv("GILJO_PGBOUNCER", "1")
        mgr = DatabaseManager(FAKE_URL, is_async=True)
        assert mgr.async_engine is not None
        assert mgr.AsyncSessionLocal is not None


class TestP2BrokerDsnSeam:
    """DoD: the broker can take a DIRECT DSN; unset falls back byte-identically."""

    def _state(self, app_url: str = "postgresql://app:pw@pooler:6432/db") -> SimpleNamespace:
        return SimpleNamespace(db_manager=SimpleNamespace(database_url=app_url))

    def test_falls_back_to_app_url_when_unset(self, monkeypatch):
        from api.startup.core_services import _resolve_broker_dsn

        monkeypatch.delenv("GILJO_BROKER_DATABASE_URL", raising=False)
        assert _resolve_broker_dsn(self._state()) == "postgresql://app:pw@pooler:6432/db"

    def test_uses_direct_url_when_set(self, monkeypatch):
        from api.startup.core_services import _resolve_broker_dsn

        direct = "postgresql://app:pw@direct:5432/db"
        monkeypatch.setenv("GILJO_BROKER_DATABASE_URL", direct)
        # Even though the app URL points at the pooler, the broker gets the direct URL.
        assert _resolve_broker_dsn(self._state()) == direct

    def test_empty_var_falls_back(self, monkeypatch):
        from api.startup.core_services import _resolve_broker_dsn

        monkeypatch.setenv("GILJO_BROKER_DATABASE_URL", "")
        assert _resolve_broker_dsn(self._state()) == "postgresql://app:pw@pooler:6432/db"


class TestP3AlembicHonorsDatabaseUrl:
    """P3 guard: the railway preDeploy DATABASE_URL override depends on this precedence.

    A source scan (not an import) because ``scripts/alembic_cli.py`` runs os.chdir and
    patches alembic's CommandLine at module import — importing it in a pytest-xdist
    worker would not be parallel-safe. The guard still fails loudly if a refactor drops
    the DATABASE_URL-first resolution the override relies on.
    """

    def test_resolve_db_url_reads_database_url_first(self):
        path = Path(__file__).resolve().parents[2] / "scripts" / "alembic_cli.py"
        if not path.exists():
            # scripts/alembic_cli.py is SaaS/operator tooling; export_ce.sh strips it
            # from the public CE tree (only 4 scripts/ files ship). The P3 direct-URL
            # guard applies only where that deploy tooling exists, so it is N/A here.
            pytest.skip(reason="scripts/alembic_cli.py absent (stripped from the CE export); P3 guard N/A")
        source = path.read_text(encoding="utf-8")
        assert 'os.getenv("DATABASE_URL")' in source, (
            "alembic_cli must resolve DATABASE_URL; the railway preDeploy "
            "DATABASE_URL=$DATABASE_UNPOOLED_URL override (P3) relies on it"
        )
        # DATABASE_URL must be consulted before the POSTGRES_* fallback parts, so the
        # override wins over any ambient POSTGRES_HOST/PORT.
        assert source.index('os.getenv("DATABASE_URL")') < source.index('os.getenv("POSTGRES_HOST"')
