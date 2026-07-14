# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""INF-9057 — CE installs are constrained to the shipped pinned tree.

Before INF-9057, CE self-hosters installed from unpinned ``>=`` floors with no
major-version caps — the exact failure mode requirements.lock was created to
prevent for prod/CI (evidence: redis floated 5.0 → 8.0.1 on fresh installs).
One breaking upstream release broke every fresh CE install with zero CI signal.

The fix ships requirements.lock with the CE export and passes it as a pip
CONSTRAINTS file (``-c``) at every dependency-install site. These are
structural checks in the house installer-test idiom (test_install_script.py):
installers cannot be executed end-to-end in unit CI, so we lock the wiring —
the cross-platform end-to-end run is operator-gated per the Public Deploy DoD.

Whether the lock's pins actually SATISFY the requirements.txt floors is already
locked by tests/unit/test_requirements_lock_drift.py (kept separate — INF-6054).
"""

from __future__ import annotations

from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent.parent

EXPORT_EXCLUDE = REPO_ROOT / ".export-exclude"
INSTALL_PY = REPO_ROOT / "install.py"
UPDATE_PY = REPO_ROOT / "update.py"
STARTUP_PY = REPO_ROOT / "startup.py"
INSTALL_PS1 = REPO_ROOT / "scripts" / "install.ps1"
INSTALL_SH = REPO_ROOT / "scripts" / "install.sh"
SECURITY_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "security.yml"
LOCK = REPO_ROOT / "requirements.lock"


def test_requirements_lock_ships_with_ce_export():
    """requirements.lock must NOT be stripped by the CE export — the whole fix
    is void if the constraints file never reaches the self-hoster's disk."""
    # The lock's presence is the load-bearing check and holds in BOTH contexts:
    # the private repo AND the stripped CE export artifact (where the lock must
    # still be there — that's the whole point of INF-9057).
    assert LOCK.exists(), "requirements.lock missing from the repo root"
    # .export-exclude is itself stripped from the CE export artifact, so its
    # absence means we are running against the export (or the public repo) —
    # LOCK.exists() above already proved the lock shipped, nothing more to check.
    if not EXPORT_EXCLUDE.exists():
        pytest.skip(".export-exclude not present (CE export artifact / public repo)")
    active_patterns = [
        line.strip()
        for line in EXPORT_EXCLUDE.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    assert "requirements.lock" not in active_patterns, (
        ".export-exclude strips requirements.lock from the CE artifact — the "
        "installer constraints layer (INF-9057) needs it shipped."
    )


class TestInstallPyConstraints:
    @pytest.fixture(autouse=True)
    def _load(self):
        # install_dependencies() lives in install.py before the BE-9060 split
        # and in installer/core/python_env.py after it — accept either home.
        candidates = [INSTALL_PY, REPO_ROOT / "installer" / "core" / "python_env.py"]
        self.content = "".join(p.read_text(encoding="utf-8") for p in candidates if p.exists())

    def test_declares_constraints_file(self):
        assert 'self.constraints_file = self.install_dir / "requirements.lock"' in self.content

    def test_requirements_install_applies_constraints(self):
        assert "*constraints_args," in self.content, (
            "install.py's main `pip install -r requirements.txt` no longer "
            "splices in the -c requirements.lock constraint args"
        )
        assert '["-c", str(self.constraints_file)]' in self.content

    def test_editable_install_applies_constraints(self):
        assert '"-e", ".", "--quiet", *constraints_args' in self.content

    def test_missing_lock_is_tolerated_not_fatal(self):
        """An older extracted release without the lock must still install."""
        assert "requirements.lock not found" in self.content


def test_update_py_applies_constraints():
    content = UPDATE_PY.read_text(encoding="utf-8")
    assert 'ROOT / "requirements.lock"' in content
    assert 'cmd += ["-c", str(lock_file)]' in content


def test_startup_py_self_heal_applies_constraints():
    # install_requirements() lives in startup.py before the BE-9060 split and
    # in startup_support/checks.py after it — accept either home.
    candidates = [STARTUP_PY, REPO_ROOT / "startup_support" / "checks.py"]
    content = "".join(p.read_text(encoding="utf-8") for p in candidates if p.exists())
    assert 'Path.cwd() / "requirements.lock"' in content
    assert 'cmd += ["-c", str(constraints_path)]' in content


def test_install_ps1_applies_constraints():
    content = INSTALL_PS1.read_text(encoding="utf-8")
    assert '$constraintsPath = Join-Path $TargetDir "requirements.lock"' in content
    assert '@("-c", $constraintsPath)' in content
    assert content.count("@constraintsArgs") >= 2, (
        "install.ps1 must splice @constraintsArgs into BOTH the -r requirements install and the editable install"
    )


def test_install_sh_applies_constraints():
    content = INSTALL_SH.read_text(encoding="utf-8")
    assert 'constraints="${target_dir}/requirements.lock"' in content
    assert 'constraint_args=(-c "$constraints")' in content
    assert content.count('${constraint_args[@]+"${constraint_args[@]}"}') >= 2, (
        "install.sh must splice the constraint args (set -u-safe expansion) into "
        "BOTH the -r requirements install and the editable install"
    )


@pytest.mark.skipif(not SECURITY_WORKFLOW.exists(), reason="private CI workflow not present in this artifact")
def test_pip_audit_scans_the_lock_not_the_floors():
    """The CVE gate must audit the pins we actually ship/run, not whatever
    latest versions the >= floors happen to resolve to on scan day."""
    content = SECURITY_WORKFLOW.read_text(encoding="utf-8")
    assert "-r requirements.lock" in content
    assert "-r requirements.txt" not in content
