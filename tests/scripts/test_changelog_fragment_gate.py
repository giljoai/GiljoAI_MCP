# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.

"""INF-9190 — changelog fragment gate: classification, markers, CI wiring.

The gate script lives in ``internal/hooks/changelog_fragment_gate.py`` and is
therefore stripped from the CE export; on a stripped tree this module skips
green (same pattern as the other private-CI-definition tests). The workflow
wiring tests parse the PRIVATE ``.github/workflows/ci.yml``; they are guarded
by the same module-level skip because the public repo's ci.yml is a different
file with no changelog gate.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
GATE_REL = "internal/hooks/changelog_fragment_gate.py"
GATE_PATH = REPO_ROOT / "internal" / "hooks" / "changelog_fragment_gate.py"
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"

if not GATE_PATH.exists():
    pytest.skip(  # skip: internal/ checker stripped on CE export -- INF-9190
        reason=(
            "internal/ checker stripped from this artifact (CE export) -- the changelog gate runs on private CI only"
        ),
        allow_module_level=True,
    )

_spec = importlib.util.spec_from_file_location("changelog_fragment_gate", GATE_PATH)
gate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gate)


# ── Path classification (pure function; the WO list in the project is the spec) ──


@pytest.mark.parametrize(
    "path",
    [
        "src/giljo_mcp/services/product_service.py",
        "frontend/src/components/AgentCard.vue",
        "api/endpoints/projects.py",
        "migrations/versions/ce_0051_add_index.py",
        "install.py",
        "startup.py",
        "requirements.txt",
        "requirements.lock",
        "frontend/package.json",
    ],
)
def test_product_facing_members(path):
    assert gate.is_product_facing(path) is True


@pytest.mark.parametrize(
    "path",
    [
        "tests/unit/test_something.py",
        "internal/hooks/export_gate.py",
        "handovers/EDITION_ISOLATION_GUIDE.md",
        ".github/workflows/ci.yml",
        "scripts/export_ce.sh",
        "CHANGELOG.md",
        "changelog.d/inf-9190.md",
        "README.md",
        "frontend/package-lock.json",
        "installer/requirements.txt",  # requirements pattern is root-only
        "srcfoo/bar.py",  # prefix must match a directory, not a substring
    ],
)
def test_non_product_facing(path):
    assert gate.is_product_facing(path) is False


# ── Fragment detection ──


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("changelog.d/inf-9190.md", True),
        ("changelog.d/fix-login-flow.md", True),
        ("changelog.d/README.md", False),  # the format doc is not an entry
        ("changelog.d/sub/nested.md", False),  # flat directory only
        ("docs/changelog.d/other.md", False),  # must be repo-root changelog.d/
        ("changelog.d/notes.txt", False),  # .md only
    ],
)
def test_is_fragment(path, expected):
    assert gate.is_fragment(path) is expected


# ── Skip-marker parsing ──


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("changelog: skip", True),
        ("Changelog: SKIP", True),
        ("  changelog: skip  ", True),
        ("fix: quiet refactor\n\nchangelog: skip\n", True),  # commit trailer
        ("changelog skip", False),
        ("changelog: skipped", False),
        ("we should changelog: skip here", False),  # must be the whole line
        ("", False),
    ],
)
def test_has_skip_marker(text, expected):
    assert gate.has_skip_marker(text) is expected


# ── Verdict logic (pure; changed = list of (status, path)) ──


def test_evaluate_non_product_pr_passes():
    ok, _ = gate.evaluate([("M", "tests/unit/test_x.py"), ("M", "handovers/N.md")])
    assert ok is True


def test_evaluate_product_change_with_fragment_passes():
    ok, _ = gate.evaluate([("M", "src/giljo_mcp/app.py"), ("A", "changelog.d/my-change.md")])
    assert ok is True


def test_evaluate_deleted_fragment_does_not_count():
    ok, _ = gate.evaluate([("M", "src/giljo_mcp/app.py"), ("D", "changelog.d/old.md")])
    assert ok is False


def test_evaluate_skip_marker_in_commit_message_passes():
    ok, _ = gate.evaluate(
        [("M", "src/giljo_mcp/app.py")],
        commit_messages="chore: tidy imports\n\nchangelog: skip",
    )
    assert ok is True


def test_evaluate_skip_marker_in_pr_body_passes():
    ok, _ = gate.evaluate(
        [("M", "src/giljo_mcp/app.py")],
        pr_body="Internal refactor only.\nchangelog: skip",
    )
    assert ok is True


def test_evaluate_missing_fragment_fails_with_teaching_message():
    ok, message = gate.evaluate(
        [("M", "src/giljo_mcp/app.py")],
        head_ref="feat/inf9190-changelog-fragments-gate",
    )
    assert ok is False
    lines = message.splitlines()
    # The WO requires the failure to TEACH in two lines: the exact fragment
    # path to create, then the skip-marker alternative.
    assert len(lines) == 2
    assert "changelog.d/inf9190-changelog-fragments-gate.md" in lines[0]
    assert "changelog: skip" in lines[1]


# ── End-to-end through git (the layer the gate actually runs at) ──


def _git(cwd: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def _make_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "master")
    _git(repo, "config", "user.email", "ci-test@example.invalid")
    _git(repo, "config", "user.name", "ci-test")
    (repo / "README.md").write_text("seed\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-q", "-m", "seed")
    return repo


def _run_gate(repo: Path, base: str, head: str, env_extra: dict | None = None) -> subprocess.CompletedProcess:
    env = {**os.environ, **(env_extra or {})}
    return subprocess.run(  # noqa: PLW1510 -- rc asserted by callers
        [sys.executable, str(GATE_PATH), "--base", base, "--head", head],
        cwd=repo,
        capture_output=True,
        text=True,
        env=env,
    )


def test_cli_red_then_green_through_git(tmp_path):
    repo = _make_repo(tmp_path)
    base = _git(repo, "rev-parse", "HEAD").strip()

    src = repo / "src" / "giljo_mcp"
    src.mkdir(parents=True)
    (src / "feature.py").write_text("VALUE = 1\n", encoding="utf-8")
    _git(repo, "add", "src/giljo_mcp/feature.py")
    _git(repo, "commit", "-q", "-m", "feat: add feature")

    missing = _run_gate(repo, base, "HEAD")
    assert missing.returncode == 1, missing.stdout + missing.stderr
    assert "changelog.d/" in missing.stdout

    frag_dir = repo / "changelog.d"
    frag_dir.mkdir()
    (frag_dir / "add-feature.md").write_text("Added\n- **New feature.** Does the thing.\n", encoding="utf-8")
    _git(repo, "add", "changelog.d/add-feature.md")
    _git(repo, "commit", "-q", "-m", "docs: fragment")

    fixed = _run_gate(repo, base, "HEAD")
    assert fixed.returncode == 0, fixed.stdout + fixed.stderr


def test_cli_pr_body_skip_marker(tmp_path):
    repo = _make_repo(tmp_path)
    base = _git(repo, "rev-parse", "HEAD").strip()
    (repo / "startup.py").write_text("# tweaked\n", encoding="utf-8")
    _git(repo, "add", "startup.py")
    _git(repo, "commit", "-q", "-m", "chore: internal tweak")

    denied = _run_gate(repo, base, "HEAD")
    assert denied.returncode == 1

    allowed = _run_gate(repo, base, "HEAD", env_extra={"PR_BODY": "Internal only.\nchangelog: skip"})
    assert allowed.returncode == 0, allowed.stdout + allowed.stderr


# ── CI wiring: the gate job exists, is hashFiles-guarded, and skips green
#    where the checker is stripped (public-repo safety is a TESTED property) ──


def _load_jobs() -> dict:
    data = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    return data["jobs"]


def _gate_step() -> dict:
    jobs = _load_jobs()
    assert "changelog-fragment" in jobs, "ci.yml must define the changelog-fragment job"
    steps = jobs["changelog-fragment"]["steps"]
    guarded = [s for s in steps if "hashFiles" in str(s.get("if", ""))]
    assert len(guarded) == 1, "exactly one hashFiles-guarded gate step expected"
    return guarded[0]


def test_gate_step_guard_references_the_real_checker_path():
    step = _gate_step()
    condition = step["if"].strip()
    assert condition == f"hashFiles('{GATE_REL}') != ''", (
        "the step guard must be a pure presence check on the checker path -- "
        "hashFiles() returns '' when the file is absent (stripped public repo), "
        "which makes the step skip green there"
    )
    # The guarded path must be the checker that actually exists here, and it
    # must live under internal/ (stripped wholesale on CE export).
    assert (REPO_ROOT / GATE_REL).exists()
    assert GATE_REL.startswith("internal/")


def test_gate_step_env_is_expression_free_run_script():
    """The run script must consume only env vars (no inline ${{ }}), so the
    checker-absent simulation below executes the literal shipped script."""
    step = _gate_step()
    assert "${{" not in step["run"]
    for var in ("EVENT_NAME", "BASE_REF", "HEAD_SHA", "PR_BODY", "HEAD_REF"):
        assert var in step.get("env", {}), f"gate step must map {var} via env"


@pytest.mark.parametrize("event_name", ["pull_request", "push"])
def test_checker_absent_step_skips_green(tmp_path, event_name):
    """Simulate the stripped public tree: execute the gate step's literal run
    script in a repo WITHOUT internal/ — it must exit 0 (skip green), not fail."""
    step = _gate_step()
    repo = _make_repo(tmp_path)
    assert not (repo / "internal").exists()
    result = subprocess.run(  # noqa: PLW1510 -- rc asserted below
        ["bash", "-c", step["run"]],
        cwd=repo,
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "EVENT_NAME": event_name,
            "BASE_REF": "master",
            "HEAD_SHA": "HEAD",
            "PR_BODY": "",
            "HEAD_REF": "some-branch",
        },
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_gate_job_blocks_the_mirror():
    jobs = _load_jobs()
    assert "changelog-fragment" in jobs["mirror-to-github"]["needs"]
