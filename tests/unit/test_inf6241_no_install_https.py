# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""INF-6241 regression: install-time HTTPS/cert factory is fully removed.

Failing layer = install.py / startup.py. INF-6241 deletes the entire mkcert
install-time cert factory:

  - install.py: setup_https(), regenerate_cert(), _install_mkcert(),
    _find_windows_shim() are removed; ssl_opt_out / GILJO_ENABLE_HTTPS are
    removed concepts.
  - startup.py: _heal_cert_for_ip_drift() is removed (its only consumer,
    the install-time DHCP IP-drift self-heal, is no longer needed).

These tests assert that none of those symbols or source tokens survive. They
serve as a re-introduction guard: if any of the removed items come back (by
accident or revert), these tests fail loudly at the layer the removal landed.

Parallel-safe (xdist): no DB, no module-level mutable state. Imports of
install/startup are read-only introspection (hasattr / source scan).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


# ---------------------------------------------------------------------------
# install.py -- removed symbols
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def install_module():
    """Import install.py once for the module; read-only introspection only."""
    import install  # noqa: PLC0415

    return install


@pytest.fixture(scope="module")
def unified_installer_class(install_module):
    return install_module.UnifiedInstaller


def test_no_setup_https(unified_installer_class):
    """install.UnifiedInstaller must NOT define setup_https() after INF-6241."""
    assert not hasattr(unified_installer_class, "setup_https"), (
        "setup_https() was removed in INF-6241 (install-time cert factory gone); re-introduction detected"
    )


def test_no_regenerate_cert(install_module):
    """install module must NOT define regenerate_cert() after INF-6241."""
    assert not hasattr(install_module, "regenerate_cert"), (
        "regenerate_cert() was removed in INF-6241; re-introduction detected"
    )


def test_no_install_mkcert(unified_installer_class):
    """UnifiedInstaller must NOT define _install_mkcert() after INF-6241."""
    assert not hasattr(unified_installer_class, "_install_mkcert"), (
        "_install_mkcert() was removed in INF-6241; re-introduction detected"
    )


def test_no_find_windows_shim(unified_installer_class):
    """UnifiedInstaller must NOT define _find_windows_shim() after INF-6241."""
    assert not hasattr(unified_installer_class, "_find_windows_shim"), (
        "_find_windows_shim() was removed in INF-6241; re-introduction detected"
    )


# ---------------------------------------------------------------------------
# startup.py -- removed symbol
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def startup_module():
    """Import startup.py once for the module; read-only introspection only."""
    import startup  # noqa: PLC0415

    return startup


def test_no_heal_cert_for_ip_drift(startup_module):
    """startup module must NOT define _heal_cert_for_ip_drift() after INF-6241."""
    assert not hasattr(startup_module, "_heal_cert_for_ip_drift"), (
        "_heal_cert_for_ip_drift() was removed in INF-6241 (startup DHCP cert self-heal "
        "gone alongside install-time cert factory); re-introduction detected"
    )


# ---------------------------------------------------------------------------
# Source token scan: install.py must not contain removed token strings
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def install_source(install_module) -> str:
    """Return the full lowercased source text of install.py."""
    return Path(install_module.__file__).read_text(encoding="utf-8").lower()


def test_install_source_free_of_mkcert(install_source):
    """install.py source must not reference 'mkcert' after INF-6241.

    The install-time cert factory used mkcert for CA-trust + leaf-cert generation.
    All mkcert references in install.py are gone; the remaining mkcert mentions in
    the codebase are in bring-your-own documentation and dev_tools teardown scripts.
    """
    assert "mkcert" not in install_source, (
        "Found 'mkcert' token in install.py source — re-introduction of the removed cert factory detected (INF-6241)"
    )


def test_install_source_free_of_giljo_enable_https(install_source):
    """install.py source must not reference GILJO_ENABLE_HTTPS after INF-6241.

    This env var drove the install-time HTTPS branch (Step 7.5). It is removed.
    """
    assert "giljo_enable_https" not in install_source, (
        "Found 'giljo_enable_https' in install.py source — re-introduction detected (INF-6241)"
    )


def test_install_source_free_of_ssl_opt_out(install_source):
    """install.py source must not reference ssl_opt_out after INF-6241.

    ssl_opt_out was the install-time flag that short-circuited setup_https().
    The concept is removed; the installer always produces ssl_enabled=False.
    """
    assert "ssl_opt_out" not in install_source, (
        "Found 'ssl_opt_out' in install.py source — re-introduction detected (INF-6241)"
    )
