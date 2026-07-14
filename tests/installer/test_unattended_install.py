# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Regression tests for install.py unattended (env-driven) mode.

Exercised at the installer CLI boundary — the layer where the interactive
prompts that block headless/automated installs actually live (INF-6037).

The unattended path is activated by GILJO_UNATTENDED=1 and reads:
    GILJO_NETWORK_MODE   localhost (default) | lan | wan | auto
    GILJO_PG_PASSWORD    required, no default (fail-fast)
    GILJO_DB_NAME        default "giljo_mcp"

These tests are DB-free: the fail-fast case raises before any database work,
and the settings-shape cases call _apply_unattended_settings() directly with
the postgres peer-auth side effect stubbed out.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
INSTALL_PY = REPO_ROOT / "install.py"

_UNATTENDED_ENV_KEYS = (
    "GILJO_UNATTENDED",
    "GILJO_PG_PASSWORD",
    "GILJO_NETWORK_MODE",
    "GILJO_DB_NAME",
    "GILJO_INSTALL_DIR",
)


def _run_install(env_extra: dict, args=("--setup-only",), cwd=None) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    for key in _UNATTENDED_ENV_KEYS:
        env.pop(key, None)
    env.update(env_extra)
    return subprocess.run(
        [sys.executable, str(INSTALL_PY), *args],
        cwd=str(cwd or REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )


def test_unattended_requires_pg_password(tmp_path):
    """GILJO_UNATTENDED with no password must fail fast (exit 1) before any DB work."""
    result = _run_install(
        {
            "GILJO_UNATTENDED": "1",
            "GILJO_NETWORK_MODE": "localhost",
            "GILJO_INSTALL_DIR": str(tmp_path),
        },
        cwd=tmp_path,
    )
    assert result.returncode == 1, (
        f"expected exit 1, got {result.returncode}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
    combined = result.stdout + result.stderr
    assert "PostgreSQL password" in combined, combined


def _import_installer(monkeypatch, tmp_path):
    """Import install.py with side effects contained to tmp_path."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.syspath_prepend(str(REPO_ROOT))
    import install  # noqa: PLC0415  # reason: deferred import keeps module side effects inside the test

    # Stub the postgres peer-auth password set (would shell out to sudo on Linux).
    monkeypatch.setattr(
        install.UnifiedInstaller,
        "_set_postgres_password_via_peer",
        lambda self, password: True,
    )
    for key in _UNATTENDED_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)
    return install


def test_unattended_localhost_binds_loopback(tmp_path, monkeypatch):
    install = _import_installer(monkeypatch, tmp_path)
    monkeypatch.setenv("GILJO_UNATTENDED", "1")
    monkeypatch.setenv("GILJO_PG_PASSWORD", "testpw")
    monkeypatch.setenv("GILJO_NETWORK_MODE", "localhost")

    inst = install.UnifiedInstaller(
        settings={"unattended": True, "pg_password": "testpw", "install_dir": str(tmp_path)}
    )
    inst._apply_unattended_settings()

    assert inst.settings["bind"] == "127.0.0.1"
    assert inst.settings["network_mode"] == "localhost"
    assert inst.settings["db_name"] == "giljo_mcp"


def test_unattended_lan_binds_all_interfaces(tmp_path, monkeypatch):
    install = _import_installer(monkeypatch, tmp_path)
    monkeypatch.setenv("GILJO_UNATTENDED", "1")
    monkeypatch.setenv("GILJO_PG_PASSWORD", "testpw")
    monkeypatch.setenv("GILJO_NETWORK_MODE", "lan")
    monkeypatch.setenv("GILJO_DB_NAME", "giljo_lan_test")

    inst = install.UnifiedInstaller(
        settings={"unattended": True, "pg_password": "testpw", "install_dir": str(tmp_path)}
    )
    inst._apply_unattended_settings()

    assert inst.settings["bind"] == "0.0.0.0"
    # LAN must NOT be localhost (confirming the non-loopback bind).
    assert inst.settings["network_mode"] != "localhost"
    assert inst.settings["db_name"] == "giljo_lan_test"


def test_unattended_lan_http_skips_ssl(tmp_path, monkeypatch):
    """INF-6241: GILJO_NETWORK_MODE=lan yields plain HTTP-LAN (ssl_enabled=False).

    Failing layer = the unattended settings population in install.py. LAN mode must
    bind 0.0.0.0 and configure plain HTTP. ssl_opt_out is a removed concept;
    the installer always produces ssl_enabled=False.
    """
    install = _import_installer(monkeypatch, tmp_path)
    monkeypatch.setenv("GILJO_UNATTENDED", "1")
    monkeypatch.setenv("GILJO_PG_PASSWORD", "testpw")
    monkeypatch.setenv("GILJO_NETWORK_MODE", "lan")

    inst = install.UnifiedInstaller(
        settings={"unattended": True, "pg_password": "testpw", "install_dir": str(tmp_path)}
    )
    inst._apply_unattended_settings()

    assert inst.settings["bind"] == "0.0.0.0"
    assert inst.settings["network_mode"] != "localhost"
    assert inst.settings.get("ssl_enabled") is False
    assert "ssl_opt_out" not in inst.settings  # concept removed


def test_unattended_force_http_opts_out_on_lan(tmp_path, monkeypatch):
    """INF-6241: GILJO_NETWORK_MODE=lan always configures plain HTTP (ssl_enabled=False).

    GILJO_FORCE_HTTP is a retained runtime flag (controls run_api TLS binding) but
    its install-time ssl_opt_out role is removed. ssl_opt_out is no longer a concept.
    """
    install = _import_installer(monkeypatch, tmp_path)
    monkeypatch.setenv("GILJO_UNATTENDED", "1")
    monkeypatch.setenv("GILJO_PG_PASSWORD", "testpw")
    monkeypatch.setenv("GILJO_NETWORK_MODE", "lan")

    inst = install.UnifiedInstaller(
        settings={"unattended": True, "pg_password": "testpw", "install_dir": str(tmp_path)}
    )
    inst._apply_unattended_settings()

    assert inst.settings["bind"] == "0.0.0.0"
    assert inst.settings.get("ssl_enabled") is False
    assert "ssl_opt_out" not in inst.settings  # concept removed


def test_unattended_bare_lan_configures_http(tmp_path, monkeypatch):
    """INF-6241: bare LAN mode (GILJO_NETWORK_MODE=lan) configures ssl_enabled=False.

    The installer no longer has an mkcert/HTTPS path; every LAN install produces
    plain HTTP. ssl_opt_out is a removed concept.
    """
    install = _import_installer(monkeypatch, tmp_path)
    monkeypatch.setenv("GILJO_UNATTENDED", "1")
    monkeypatch.setenv("GILJO_PG_PASSWORD", "testpw")
    monkeypatch.setenv("GILJO_NETWORK_MODE", "lan")
    monkeypatch.delenv("GILJO_FORCE_HTTP", raising=False)

    inst = install.UnifiedInstaller(
        settings={"unattended": True, "pg_password": "testpw", "install_dir": str(tmp_path)}
    )
    inst._apply_unattended_settings()

    assert inst.settings["bind"] == "0.0.0.0"
    assert inst.settings.get("ssl_enabled") is False
    assert "ssl_opt_out" not in inst.settings  # concept removed


def test_is_private_lan_host_classifier():
    """INF-6241: is_private_lan_host classifies addresses to drive WAN cleartext warnings.

    Private/loopback/link-local IPs are LAN addresses; domains and public IPs are a
    WAN/public posture where the installer emits a cleartext warning (no hard-fail).
    """
    from installer.shared.network import is_private_lan_host

    # Private (non-globally-routable) / loopback / link-local -> HTTP-on-LAN acceptable.
    # NOTE: real adapter IPs are RFC-1918 (10/8, 172.16/12, 192.168/16); we use RFC 5737
    # documentation IPs here (leak-check forbids literal RFC-1918 in shipped files). Python
    # classifies BOTH as is_private, so these exercise the identical helper branch.
    assert is_private_lan_host("192.0.2.10") is True  # RFC 5737 doc range == is_private
    assert is_private_lan_host("198.51.100.7") is True
    assert is_private_lan_host("203.0.113.9") is True
    assert is_private_lan_host("127.0.0.1") is True  # loopback
    assert is_private_lan_host("169.254.1.1") is True  # link-local (RFC 3927)
    # WAN/public posture -> HTTPS stays mandatory.
    assert is_private_lan_host("8.8.8.8") is False
    assert is_private_lan_host("example.com") is False
    assert is_private_lan_host("mybox.local") is False


def test_unattended_missing_password_raises_in_process(tmp_path, monkeypatch):
    install = _import_installer(monkeypatch, tmp_path)
    monkeypatch.setenv("GILJO_UNATTENDED", "1")
    monkeypatch.setenv("GILJO_NETWORK_MODE", "localhost")

    inst = install.UnifiedInstaller(settings={"unattended": True, "install_dir": str(tmp_path)})
    inst.settings["pg_password"] = None
    with pytest.raises(ValueError, match="PostgreSQL password"):
        inst._apply_unattended_settings()


# ---------------------------------------------------------------------------
# INF-6241 regression: every install mode produces plain HTTP / ssl_enabled=False.
# WAN/public binds emit a cleartext warning but do NOT raise / SystemExit.
# ---------------------------------------------------------------------------

_PUBLIC_ADAPTER = [{"ip": "8.8.8.8", "name": "eth0", "is_virtual": False}]


def _abort_getpass(prompt: str = "") -> str:
    """Raise KeyboardInterrupt to short-circuit the PG-password section."""
    raise KeyboardInterrupt("abort PG section in test")


@pytest.mark.parametrize(
    "mode,expected_bind",
    [
        ("localhost", "127.0.0.1"),
        ("lan", "0.0.0.0"),
        ("wan", "0.0.0.0"),
    ],
)
def test_unattended_always_configures_http(tmp_path, monkeypatch, mode, expected_bind):
    """INF-6241 (a): every unattended network mode sets ssl_enabled=False, no ssl_opt_out.

    Failing layer: _apply_unattended_settings() in install.py. After INF-6241 removes
    the install-time cert factory, all modes must produce plain HTTP with the correct
    bind address. ssl_opt_out is a removed concept.
    """
    install = _import_installer(monkeypatch, tmp_path)
    monkeypatch.setenv("GILJO_UNATTENDED", "1")
    monkeypatch.setenv("GILJO_PG_PASSWORD", "testpw")
    monkeypatch.setenv("GILJO_NETWORK_MODE", mode)

    inst = install.UnifiedInstaller(
        settings={"unattended": True, "pg_password": "testpw", "install_dir": str(tmp_path)}
    )
    inst._apply_unattended_settings()

    assert inst.settings["bind"] == expected_bind
    assert inst.settings.get("ssl_enabled") is False
    assert "ssl_opt_out" not in inst.settings  # concept removed


def test_unattended_wan_warns_but_does_not_fail(tmp_path, monkeypatch, capsys):
    """INF-6241 (b): WAN/public unattended install emits a cleartext warning, does NOT raise.

    Failing layer: _apply_unattended_settings() in install.py. Before INF-6241, a
    WAN install hard-failed (result["success"]=False; SystemExit). After the removal,
    it must warn and proceed with ssl_enabled=False.
    """
    install = _import_installer(monkeypatch, tmp_path)
    monkeypatch.setenv("GILJO_UNATTENDED", "1")
    monkeypatch.setenv("GILJO_PG_PASSWORD", "testpw")
    monkeypatch.setenv("GILJO_NETWORK_MODE", "wan")

    inst = install.UnifiedInstaller(
        settings={"unattended": True, "pg_password": "testpw", "install_dir": str(tmp_path)}
    )
    inst._apply_unattended_settings()  # must NOT raise / SystemExit

    assert inst.settings.get("ssl_enabled") is False
    combined = " ".join(capsys.readouterr()).lower()
    assert "cleartext" in combined or "reverse proxy" in combined or "tunnel" in combined, (
        f"expected a cleartext/WAN warning in output; got: {combined!r}"
    )


def test_interactive_autodetect_public_ip_warns_no_fail(tmp_path, monkeypatch, capsys):
    """INF-6241 (b) interactive: auto-detect (choice 2) with a public-IP NIC must
    emit a WAN cleartext warning and proceed with ssl_enabled=False (no hard-fail).

    Failing layer: ask_installation_questions() in install.py. Before INF-6241,
    a public IP triggered a mandatory-HTTPS hard-fail (ssl_opt_out absent + SystemExit).
    """
    import installer.shared.network as net_mod

    install = _import_installer(monkeypatch, tmp_path)
    monkeypatch.setattr(net_mod, "get_network_adapters", lambda: _PUBLIC_ADAPTER)

    # "2" selects auto-detect; getpass raises to abort before the PG section
    # so the test runs without any real password/DB work.
    tty_calls = iter(["2"])
    monkeypatch.setattr(install, "tty_input", lambda prompt="": next(tty_calls))
    monkeypatch.setattr(install, "getpass_with_asterisks", _abort_getpass)

    inst = install.UnifiedInstaller(settings={"install_dir": str(tmp_path)})
    with pytest.raises(KeyboardInterrupt):
        inst.ask_installation_questions()

    # Must NOT set ssl_opt_out (removed) and must NOT hard-fail before the KBI.
    assert "ssl_opt_out" not in inst.settings, (
        "public IP auto-detect (choice 2) must not set ssl_opt_out (removed concept)"
    )
    assert inst.settings.get("ssl_enabled") is False
    combined = " ".join(capsys.readouterr()).lower()
    assert "cleartext" in combined or "reverse proxy" in combined or "tunnel" in combined, (
        f"expected a WAN cleartext warning in output; got: {combined!r}"
    )


def test_interactive_specific_adapter_public_ip_warns_no_fail(tmp_path, monkeypatch, capsys):
    """INF-6241 (b) interactive: selecting a specific adapter (choice 3) with a public IP
    must emit a WAN cleartext warning and proceed with ssl_enabled=False (no hard-fail).

    Failing layer: ask_installation_questions() in install.py. Before INF-6241,
    choice 3 also triggered the mandatory-HTTPS hard-fail gate for WAN addresses.
    """
    import installer.shared.network as net_mod

    install = _import_installer(monkeypatch, tmp_path)
    monkeypatch.setattr(net_mod, "get_network_adapters", lambda: _PUBLIC_ADAPTER)

    # "3" selects the first specific adapter (index 0); getpass aborts PG section.
    tty_calls = iter(["3"])
    monkeypatch.setattr(install, "tty_input", lambda prompt="": next(tty_calls))
    monkeypatch.setattr(install, "getpass_with_asterisks", _abort_getpass)

    inst = install.UnifiedInstaller(settings={"install_dir": str(tmp_path)})
    with pytest.raises(KeyboardInterrupt):
        inst.ask_installation_questions()

    assert "ssl_opt_out" not in inst.settings, (
        "public IP specific-adapter (choice 3) must not set ssl_opt_out (removed concept)"
    )
    assert inst.settings.get("ssl_enabled") is False
    combined = " ".join(capsys.readouterr()).lower()
    assert "cleartext" in combined or "reverse proxy" in combined or "tunnel" in combined, (
        f"expected a WAN cleartext warning in output; got: {combined!r}"
    )
