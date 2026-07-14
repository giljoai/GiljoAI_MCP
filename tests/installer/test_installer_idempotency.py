# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Regression tests for INF-5089: install.py re-entrancy & idempotency.

Exercised at the installer layer (install.py + installer/core/*) — the layer where
the re-run / partial-failure bugs actually occur. All DB and psycopg2 I/O is stubbed,
so these run headlessly in CI with no PostgreSQL. Parallel-safe: no module-level
mutable state; monkeypatch / tmp_path fixtures own every side effect.

Covers:
  * generate_env_file() preserves security secrets across a regenerate (no session /
    JWT / API-key rotation on a --repair re-run); mints fresh secrets on first write.
  * DatabaseInstaller.reset_role_passwords() (the --repair credential-recovery seam)
    issues ALTER ROLE PASSWORD for BOTH roles and returns fresh credentials.
  * _seed_setup_state() is idempotent (reuses an existing tenant_key, no duplicate
    insert) and no longer NameErrors on `UTC` — the BE-9060 mechanical-split regression.
  * The --repair CLI flag exists and implies --setup-only (prereqs/deps skipped).
"""

import contextlib
import sys
from pathlib import Path
from unittest.mock import MagicMock


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))


# ---------------------------------------------------------------------------
# generate_env_file() secret preservation (env-write idempotency)
# ---------------------------------------------------------------------------


def _make_config(tmp_path, **extra):
    from installer.core.config import ConfigManager

    return ConfigManager(
        settings={
            "install_dir": str(tmp_path),
            "owner_password": extra.pop("owner_password", "new_owner_pw"),
            "user_password": extra.pop("user_password", "new_user_pw"),
            "db_name": "giljo_mcp",
            **extra,
        }
    )


def _parse_env(text: str) -> dict:
    out = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip()
    return out


def test_generate_env_preserves_existing_secrets(tmp_path):
    """A .env regenerate (--repair) must keep the existing security secrets, only
    rotating the DB passwords it was handed.

    Failing layer: installer/core/config.py generate_env_file().
    """
    env_file = tmp_path / ".env"
    env_file.write_text(
        "GILJO_MCP_SECRET_KEY=keep_mcp\n"
        "SECRET_KEY=keep_secret\n"
        "JWT_SECRET=keep_jwt\n"
        "SESSION_SECRET=keep_session\n"
        "GILJO_MCP_API_KEY=keep_api\n"
        "DEFAULT_TENANT_KEY=tk_keep\n"
        "POSTGRES_PASSWORD=old_user_pw\n"
        "POSTGRES_OWNER_PASSWORD=old_owner_pw\n",
        encoding="utf-8",
    )

    cm = _make_config(tmp_path, owner_password="new_owner_pw", user_password="new_user_pw")
    result = cm.generate_env_file()
    assert result["success"], result

    env = _parse_env(env_file.read_text(encoding="utf-8"))
    # Secrets preserved verbatim.
    assert env["GILJO_MCP_SECRET_KEY"] == "keep_mcp"
    assert env["SECRET_KEY"] == "keep_secret"
    assert env["JWT_SECRET"] == "keep_jwt"
    assert env["SESSION_SECRET"] == "keep_session"
    assert env["GILJO_MCP_API_KEY"] == "keep_api"
    assert env["DEFAULT_TENANT_KEY"] == "tk_keep"
    # DB passwords rotated to the new values the installer supplied.
    assert env["POSTGRES_PASSWORD"] == "new_user_pw"
    assert env["POSTGRES_OWNER_PASSWORD"] == "new_owner_pw"


def test_generate_env_mints_secrets_when_absent(tmp_path):
    """First write (no prior .env) must mint non-empty, distinct secrets.

    Failing layer: installer/core/config.py generate_env_file().
    """
    cm = _make_config(tmp_path)
    result = cm.generate_env_file()
    assert result["success"], result

    env = _parse_env((tmp_path / ".env").read_text(encoding="utf-8"))
    for key in ("GILJO_MCP_SECRET_KEY", "SECRET_KEY", "JWT_SECRET", "SESSION_SECRET"):
        assert env.get(key), f"{key} must be minted non-empty on a fresh write"
    # Independently generated -> not all identical.
    assert len({env["SECRET_KEY"], env["JWT_SECRET"], env["SESSION_SECRET"]}) > 1


# ---------------------------------------------------------------------------
# ENVIRONMENT stamp follows the frontend-mode choice (INF-9155)
# ---------------------------------------------------------------------------


def test_generate_env_stamps_production_for_production_mode(tmp_path):
    """A Production frontend-mode install must stamp ENVIRONMENT=production, not the
    old hardcoded ENVIRONMENT=development (INF-9155).

    Failing layer: installer/core/config.py generate_env_file().
    """
    cm = _make_config(tmp_path, frontend_mode="production")
    result = cm.generate_env_file()
    assert result["success"], result

    env = _parse_env((tmp_path / ".env").read_text(encoding="utf-8"))
    assert env["ENVIRONMENT"] == "production"


def test_generate_env_stamps_development_for_contributor_mode(tmp_path):
    """A Contributor/Dev frontend-mode install keeps ENVIRONMENT=development so the
    is_development_mode() dist-signal fallback keeps Vite HMR relaxations (INF-9155).

    Failing layer: installer/core/config.py generate_env_file().
    """
    cm = _make_config(tmp_path, frontend_mode="development")
    result = cm.generate_env_file()
    assert result["success"], result

    env = _parse_env((tmp_path / ".env").read_text(encoding="utf-8"))
    assert env["ENVIRONMENT"] == "development"


def test_generate_env_defaults_development_when_mode_absent(tmp_path):
    """The first .env write happens at database setup, before the frontend-mode prompt,
    so an absent frontend_mode must default to development (preserves prior behaviour
    until the choice re-stamps it) (INF-9155).

    Failing layer: installer/core/config.py generate_env_file().
    """
    cm = _make_config(tmp_path)  # no frontend_mode
    result = cm.generate_env_file()
    assert result["success"], result

    env = _parse_env((tmp_path / ".env").read_text(encoding="utf-8"))
    assert env["ENVIRONMENT"] == "development"


def test_generate_env_production_stamp_is_idempotent(tmp_path):
    """Re-running the .env write (installer re-run) with the same Production choice must
    keep ENVIRONMENT=production and preserve the existing secrets (INF-9155).

    Failing layer: installer/core/config.py generate_env_file().
    """
    cm = _make_config(tmp_path, frontend_mode="production")
    assert cm.generate_env_file()["success"]
    first = _parse_env((tmp_path / ".env").read_text(encoding="utf-8"))

    assert cm.generate_env_file()["success"]
    second = _parse_env((tmp_path / ".env").read_text(encoding="utf-8"))

    assert first["ENVIRONMENT"] == second["ENVIRONMENT"] == "production"
    # Secrets are preserved verbatim across the re-run (no rotation).
    for key in ("SECRET_KEY", "JWT_SECRET", "SESSION_SECRET", "GILJO_MCP_SECRET_KEY"):
        assert first[key] == second[key], f"{key} must not rotate on re-run"


def test_update_env_plumbs_frontend_mode_from_settings(tmp_path):
    """The install.py .env-writer call site must forward the recorded frontend_mode into
    the ConfigManager settings so the ENVIRONMENT stamp reflects the user's choice end to
    end (INF-9155).

    Failing layer: install.py update_env_with_real_credentials().
    """
    import install

    inst = install.UnifiedInstaller(settings={"install_dir": str(tmp_path), "frontend_mode": "production"})
    inst.database_credentials = {"owner_password": "owner_pw", "user_password": "user_pw"}

    result = inst.update_env_with_real_credentials()
    assert result["success"], result

    env = _parse_env((tmp_path / ".env").read_text(encoding="utf-8"))
    assert env["ENVIRONMENT"] == "production"


# ---------------------------------------------------------------------------
# reset_role_passwords() — the --repair credential-recovery seam
# ---------------------------------------------------------------------------


def test_reset_role_passwords_alters_both_roles(monkeypatch):
    """reset_role_passwords() must ALTER ROLE PASSWORD for giljo_owner AND giljo_user
    and return fresh credentials.

    Failing layer: installer/core/database.py reset_role_passwords().
    """
    import types

    import psycopg2.sql as real_sql

    import installer.core.database as db_mod

    captured_templates: list[str] = []

    def spy_sql(template: str):
        captured_templates.append(template)
        return real_sql.SQL(template)

    monkeypatch.setattr(
        db_mod,
        "sql",
        types.SimpleNamespace(SQL=spy_sql, Identifier=real_sql.Identifier),
    )

    cur = MagicMock()
    cur_ctx = MagicMock()
    cur_ctx.__enter__ = MagicMock(return_value=cur)
    cur_ctx.__exit__ = MagicMock(return_value=False)
    conn = MagicMock()
    conn.cursor.return_value = cur_ctx

    mock_pg = MagicMock()
    mock_pg.connect.return_value = conn
    mock_pg.Error = Exception
    monkeypatch.setattr(db_mod, "psycopg2", mock_pg)

    inst = db_mod.DatabaseInstaller(
        settings={"host": "localhost", "port": 5432, "password": "pw", "username": "postgres", "db_name": "giljo_mcp"}
    )
    monkeypatch.setattr(inst, "save_credentials", lambda: None)

    result = inst.reset_role_passwords()

    assert result["success"] is True, f"Expected success; got: {result}"
    creds = result["credentials"]
    assert creds["owner_password"] and creds["user_password"]
    assert creds["owner_password"] != creds["user_password"]

    alters = [t for t in captured_templates if "ALTER" in t.upper() and "ROLE" in t.upper() and "PASSWORD" in t.upper()]
    assert len(alters) == 2, f"Expected 2 ALTER ROLE PASSWORD templates (owner + user); got: {captured_templates}"


# ---------------------------------------------------------------------------
# _seed_setup_state() — idempotency + UTC regression (BE-9060 split)
# ---------------------------------------------------------------------------


class _FakeResult:
    def __init__(self, scalar=None, scalar_one=None):
        self._scalar = scalar
        self._scalar_one = scalar_one

    def scalar(self):
        return self._scalar

    def scalar_one_or_none(self):
        return self._scalar_one


class _FakeSession:
    """Returns the pre-check result first, then the ORM existence result."""

    def __init__(self, existing_tk, existing_state):
        self._results = [
            _FakeResult(scalar=existing_tk),  # raw "SELECT tenant_key FROM setup_state"
            _FakeResult(scalar_one=existing_state),  # ORM SetupState existence check
        ]
        self._i = 0
        self.added = []
        self.committed = False

    async def execute(self, *args, **kwargs):
        result = self._results[min(self._i, len(self._results) - 1)]
        self._i += 1
        return result

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        self.committed = True


class _FakeSessionCtx:
    def __init__(self, session):
        self.session = session

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, *exc):
        return False


class _FakeDBManager:
    def __init__(self, session):
        self.session = session

    def get_session_async(self):
        return _FakeSessionCtx(self.session)

    async def close_async(self):
        return None


def _patch_db(monkeypatch, session):
    import giljo_mcp.database as gdb

    monkeypatch.setattr(gdb, "DatabaseManager", lambda *a, **k: _FakeDBManager(session))
    monkeypatch.setattr(gdb, "tenant_session_context", lambda s, k: contextlib.nullcontext())


def _installer(tmp_path):
    import install

    return install.UnifiedInstaller(settings={"install_dir": str(tmp_path)})


def test_seed_setup_state_fresh_inserts_no_utc_nameerror(tmp_path, monkeypatch):
    """Fresh DB (no prior setup_state): a row is inserted and committed, and building
    the SetupState row must NOT raise NameError on `UTC` (BE-9060 split regression).

    Failing layer: installer/core/database_setup.py _seed_setup_state().
    """
    session = _FakeSession(existing_tk=None, existing_state=None)
    _patch_db(monkeypatch, session)

    inst = _installer(tmp_path)
    tenant_key = inst._seed_setup_state("postgresql://fake/db")

    assert tenant_key and tenant_key.startswith("tk_"), f"expected a generated tenant_key; got {tenant_key!r}"
    assert len(session.added) == 1, "fresh install must insert exactly one SetupState row"
    assert session.committed is True


def test_seed_setup_state_reuses_existing_tenant(tmp_path, monkeypatch):
    """Re-run against a DB that already has a setup_state row: reuse its tenant_key and
    insert nothing (idempotent — no duplicate SetupState / demo re-seed).

    Failing layer: installer/core/database_setup.py _seed_setup_state().
    """
    session = _FakeSession(existing_tk="tk_existing", existing_state=object())
    _patch_db(monkeypatch, session)

    inst = _installer(tmp_path)
    tenant_key = inst._seed_setup_state("postgresql://fake/db")

    assert tenant_key == "tk_existing", "must reuse the tenant_key already present in setup_state"
    assert session.added == [], "no duplicate SetupState row may be inserted on re-run"


# ---------------------------------------------------------------------------
# --repair CLI flag: exists and implies --setup-only
# ---------------------------------------------------------------------------


def test_repair_flag_registered():
    """The --repair option must be exposed on the installer CLI.

    Failing layer: install.py main() click command.
    """
    from click.testing import CliRunner

    import install

    result = CliRunner().invoke(install.main, ["--help"])
    assert result.exit_code == 0, result.output
    assert "--repair" in result.output


def test_repair_implies_setup_only_skips_prereqs(tmp_path, monkeypatch):
    """--repair must skip prerequisite/dependency steps (Python check, PostgreSQL
    discovery, dependency install) just like --setup-only.

    Failing layer: install.py UnifiedInstaller.run().
    """
    import install

    inst = install.UnifiedInstaller(settings={"install_dir": str(tmp_path), "repair": True, "headless": True})

    called = {"discover_pg": False, "check_py": False, "install_deps": False}
    monkeypatch.setattr(inst, "welcome_screen", lambda: None)
    monkeypatch.setattr(inst, "check_python_version", lambda: called.__setitem__("check_py", True) or True)
    monkeypatch.setattr(inst, "discover_postgresql", lambda: called.__setitem__("discover_pg", True) or {"found": True})
    monkeypatch.setattr(inst, "discover_nodejs", lambda: {"found": False})
    monkeypatch.setattr(
        inst, "install_dependencies", lambda: called.__setitem__("install_deps", True) or {"success": True}
    )
    monkeypatch.setattr(inst, "generate_configs", lambda: {"success": True})
    monkeypatch.setattr(inst, "setup_database", lambda: {"success": True, "credentials": {}})
    monkeypatch.setattr(inst, "run_database_migrations", lambda: {"success": True, "migrations_applied": []})
    monkeypatch.setattr(inst, "_print_success_summary", lambda: None)

    result = inst.run()

    assert result["success"] is True, f"repair run should succeed with stubs; got {result}"
    assert called["check_py"] is False, "--repair must skip the Python-version prereq"
    assert called["discover_pg"] is False, "--repair must skip PostgreSQL discovery"
    assert called["install_deps"] is False, "--repair must skip dependency installation"


# ---------------------------------------------------------------------------
# .env encoding invariants (INF-9159 — v2.0.0 tag-install failure on cp1252)
# ---------------------------------------------------------------------------


def test_generated_env_is_pure_ascii(tmp_path):
    """The generated .env must be pure ASCII so it parses identically under ANY
    locale. v2.0.0's template carried em-dashes; on a vanilla cp1252 Windows box
    the (then locale-default) write emitted byte 0x97 and load_dotenv's strict
    UTF-8 read crashed the installer (INF-9159).

    Failing layer: installer/core/config.py generate_env_file() template.
    """
    cm = _make_config(tmp_path, frontend_mode="production")
    assert cm.generate_env_file()["success"]
    raw = (tmp_path / ".env").read_bytes()
    non_ascii = [b for b in raw if b > 127]
    assert not non_ascii, f"non-ASCII bytes in generated .env: {non_ascii[:5]}"


def test_generated_env_survives_strict_utf8_and_dotenv_roundtrip(tmp_path):
    """The exact crash path from the v2.0.0 tag install: generate .env, then
    parse it back with python-dotenv (strict UTF-8). Locks write-encoding and
    template purity together (INF-9159).
    """
    from dotenv import dotenv_values

    cm = _make_config(tmp_path, frontend_mode="production")
    assert cm.generate_env_file()["success"]
    (tmp_path / ".env").read_bytes().decode("utf-8")  # strict decode must not raise
    values = dotenv_values(str(tmp_path / ".env"))
    assert values.get("ENVIRONMENT") == "production"
