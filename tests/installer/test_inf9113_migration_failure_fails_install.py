# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""INF-9113 regression (d): a failed migration must FAIL the install.

The shipped installer swallowed migration failures on the "upgrade" branch
("Continuing installation - manual migration may be required") and went on
to print "Installation Complete!" over a wedged database. The fresh-install
"critical" guard could never fire: by step 6.5 setup_database() had already
written .env, so ``is_fresh_install`` was always False.

Failing layer: install.py UnifiedInstaller.run() (the swallow lived in its
step 6.5 branch). All heavy steps are stubbed; no DB, no subprocess.
main() maps run()'s success flag to the process exit code
(``sys.exit(0 if result["success"] else 1)``), so asserting on the run()
result asserts the non-zero exit.
"""

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))


def _make_installer(tmp_path, monkeypatch, migration_result: dict):
    """UnifiedInstaller with everything before/after step 6.5 stubbed."""
    import install

    inst = install.UnifiedInstaller(
        settings={
            "install_dir": str(tmp_path),
            "setup_only": True,
            "unattended": True,
            "headless": True,
        }
    )
    monkeypatch.setattr(inst, "welcome_screen", lambda: None)
    monkeypatch.setattr(inst, "_apply_unattended_settings", lambda: None)
    monkeypatch.setattr(inst, "generate_configs", lambda: {"success": True})
    monkeypatch.setattr(inst, "setup_database", lambda: {"success": True, "credentials": {}})
    monkeypatch.setattr(inst, "run_database_migrations", lambda: migration_result)
    # Record whether the success banner ("Installation Complete!") fires.
    summary_calls: list[bool] = []
    monkeypatch.setattr(inst, "_print_success_summary", lambda: summary_calls.append(True))
    # SaaS Redis step must not run in this CE-scoped test.
    monkeypatch.delenv("GILJO_MODE", raising=False)
    return inst, summary_calls


def test_migration_failure_fails_the_install(tmp_path, monkeypatch):
    """Migration failure => run() returns success=False with the error, and
    the "Installation Complete!" summary is never printed (exit code 1)."""
    inst, summary_calls = _make_installer(
        tmp_path,
        monkeypatch,
        {"success": False, "error": "simulated migration failure", "migrations_applied": []},
    )

    result = inst.run()

    assert result["success"] is False
    assert result["error"] == "simulated migration failure"
    assert "migrations_applied" not in result["steps"]
    assert summary_calls == [], "success summary must not print after a failed migration"


def test_migration_success_still_completes(tmp_path, monkeypatch):
    """Happy path unchanged: successful migrations complete the install."""
    inst, summary_calls = _make_installer(
        tmp_path,
        monkeypatch,
        {"success": True, "error": None, "migrations_applied": []},
    )

    result = inst.run()

    assert result["success"] is True
    assert "migrations_applied" in result["steps"]
    assert summary_calls == [True]
