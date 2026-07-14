# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Regression tests for TSK-9123: CSP mode mislabel.

installer/core/config.py's generated .env stamps ENVIRONMENT=development on
every CE install, regardless of whether the operator picked "Production"
(built frontend/dist/, single port) or "Contributor / Dev mode" (Vite dev
server, no dist/) at the installer's frontend-mode prompt. Before this fix,
is_development_mode() trusted that env var unconditionally, so a
Production-mode install's console banner said PRODUCTION while its CSP
still carried the DEVELOPMENT 'unsafe-eval' relaxation.

is_development_mode() now falls back to the same frontend/dist/index.html
signal startup.py's own console banner uses to resolve that ambiguity,
while an explicit GILJO_ENV override (never installer-set) still wins
unconditionally.

Edition Scope: CE. The middleware itself is CE-only logic.
"""

from api.middleware.security import is_development_mode


def _make_dist(tmp_path, monkeypatch):
    dist_dir = tmp_path / "frontend" / "dist"
    dist_dir.mkdir(parents=True)
    (dist_dir / "index.html").write_text("<html></html>")
    monkeypatch.chdir(tmp_path)


def test_environment_development_with_dist_built_is_production(tmp_path, monkeypatch):
    """Production-mode install (dist/ built) must NOT get the dev CSP relaxation,
    even though installer/core/config.py stamped ENVIRONMENT=development."""
    _make_dist(tmp_path, monkeypatch)
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.delenv("GILJO_ENV", raising=False)

    assert is_development_mode() is False


def test_environment_development_without_dist_is_development(tmp_path, monkeypatch):
    """Contributor/Dev-mode install (no dist/, Vite dev server) keeps the
    unsafe-eval relaxation Vite HMR needs."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.delenv("GILJO_ENV", raising=False)

    assert is_development_mode() is True


def test_giljo_env_explicit_override_wins_even_with_dist_built(tmp_path, monkeypatch):
    """GILJO_ENV is never installer-set -- an explicit override always wins,
    unconditionally, regardless of dist/ presence."""
    _make_dist(tmp_path, monkeypatch)
    monkeypatch.setenv("GILJO_ENV", "development")

    assert is_development_mode() is True


def test_no_env_vars_defaults_to_production(tmp_path, monkeypatch):
    """Fail-safe default: no dev signal at all means production."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("GILJO_ENV", raising=False)
    monkeypatch.delenv("ENVIRONMENT", raising=False)

    assert is_development_mode() is False


def test_environment_production_explicit_wins_even_without_dist(tmp_path, monkeypatch):
    """An explicit non-dev ENVIRONMENT value stays production unconditionally --
    unchanged pre-existing behavior, not gated on dist/ at all."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("GILJO_ENV", raising=False)

    assert is_development_mode() is False
