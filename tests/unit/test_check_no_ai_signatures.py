# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Unit tests for scripts/check_no_ai_signatures.py --range (CI) mode.

Guards the de-layered AI-signature commit-message check (INF-6144 W/S3 A1):
the --range mode must flag a planted AI-signature commit and pass a clean one,
using the SAME COMPILED patterns as the commit-msg hook.

Note: the planted signature is assembled from fragments at runtime so this test
file's own source never contains a literal "Co-Authored-By: <model>" line --
otherwise ci.yml's "Check for AI signatures in code" file-scan (which scans
changed source files including tests/) would flag this file. We deliberately
use a "Bot" author (matched by COMPILED's \\bbot\\b alternative, NOT by the
narrower code-scan model list), so the temp commit message is caught while this
source stays clean on every layer.

Parallel-safe: each test builds its own temp git repo under tmp_path; the only
process-global mutation (cwd) is via monkeypatch.chdir, which pytest restores.
"""

import importlib.util
import subprocess
from pathlib import Path

import pytest


_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "check_no_ai_signatures.py"

# scripts/ is dev tooling the CE export strips; these tests target that script,
# so skip them when it is absent (the CE-export Deletion Test runs the suite
# against the stripped artifact). They run in full in private CI. (INF-6144 W/S3)
pytestmark = pytest.mark.skipif(
    not _SCRIPT.exists(),
    reason="scripts/check_no_ai_signatures.py is stripped from the CE export artifact",
)

# A trailer that matches COMPILED (via the \bbot\b alternative) but NOT the
# narrower ci.yml code-scan model list -- and never appears contiguously here.
_BAD_TRAILER = "Co-Authored" + "-By: Release Bot <bot@example.invalid>"


def _load_module():
    spec = importlib.util.spec_from_file_location("check_no_ai_signatures", _SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _git(repo: Path, *args: str, env: dict) -> None:
    subprocess.run(
        ["git", *args],
        cwd=str(repo),
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )


def _make_repo(tmp_path: Path) -> tuple[Path, dict]:
    """A throwaway git repo fully isolated from global/system config + hooks."""
    repo = tmp_path / "repo"
    repo.mkdir()

    import os

    empty_cfg = tmp_path / "empty.gitconfig"
    empty_cfg.write_text("", encoding="utf-8")
    env = dict(os.environ)
    # Isolate from the operator's global config (hooksPath, gpg signing, etc.).
    env["GIT_CONFIG_GLOBAL"] = str(empty_cfg)
    env["GIT_CONFIG_SYSTEM"] = str(empty_cfg)

    common = ["-c", "user.name=Tester", "-c", "user.email=tester@example.invalid", "-c", "commit.gpgsign=false"]
    _git(repo, "init", env=env)
    (repo / "f.txt").write_text("v1\n", encoding="utf-8")
    _git(repo, "add", "f.txt", env=env)
    _git(repo, *common, "commit", "--no-verify", "-m", "init", env=env)

    (repo / "f.txt").write_text("v2\n", encoding="utf-8")
    _git(repo, "add", "f.txt", env=env)
    _git(repo, *common, "commit", "--no-verify", "-m", "BE-0001: clean change\n\n**Edition Scope:** Both", env=env)

    (repo / "f.txt").write_text("v3\n", encoding="utf-8")
    _git(repo, "add", "f.txt", env=env)
    _git(repo, *common, "commit", "--no-verify", "-m", f"BE-0002: tainted change\n\n{_BAD_TRAILER}", env=env)

    return repo, env


def test_range_flags_planted_signature(tmp_path, monkeypatch, capsys):
    """--range over a range containing the tainted commit returns 1 + prints the SHA."""
    mod = _load_module()
    repo, env = _make_repo(tmp_path)
    monkeypatch.chdir(repo)

    # HEAD = tainted commit; HEAD~1..HEAD covers exactly it.
    bad_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=str(repo), env=env, text=True).strip()

    rc = mod._check_commit_range("HEAD~1..HEAD")

    assert rc == 1
    out = capsys.readouterr().out
    assert bad_sha in out


def test_range_passes_clean_commits(tmp_path, monkeypatch):
    """--range over a range of only clean commits returns 0."""
    mod = _load_module()
    repo, _env = _make_repo(tmp_path)
    monkeypatch.chdir(repo)

    # HEAD~2..HEAD~1 covers exactly the clean (second) commit.
    rc = mod._check_commit_range("HEAD~2..HEAD~1")

    assert rc == 0


def test_commit_msg_file_mode_still_works(tmp_path):
    """The original single-file commit-msg hook path is unchanged."""
    mod = _load_module()

    dirty = tmp_path / "MSG_DIRTY"
    dirty.write_text(f"subject line\n\n{_BAD_TRAILER}\n", encoding="utf-8")
    assert mod._check_commit_msg_file(str(dirty)) == 1

    clean = tmp_path / "MSG_CLEAN"
    clean.write_text("BE-0003: ordinary subject\n\n**Edition Scope:** CE\n", encoding="utf-8")
    assert mod._check_commit_msg_file(str(clean)) == 0


def test_range_requires_argument():
    """--range with no range argument is an error (exit 1)."""
    mod = _load_module()
    import sys

    saved = sys.argv
    try:
        sys.argv = ["check_no_ai_signatures.py", "--range"]
        assert mod.main() == 1
    finally:
        sys.argv = saved


def test_built_with_model_is_flagged():
    """CLAUDE.md bans 'Built with <model>' -- COMPILED must keep catching it.

    Guards the INF-6144 W3 (b) coverage restored to the canonical pattern set
    when the inline ci.yml regex was consolidated into COMPILED.
    """
    mod = _load_module()
    # Assembled from fragments for the same reason as _BAD_TRAILER.
    assert mod.find_signature("Add feature\n\n" + "Built " + "with Claude") is not None
    # A legitimate "built with <non-model>" subject must NOT be flagged.
    assert mod.find_signature("Refactor: built with care by the team") is None


def test_parity_full_model_list_caught():
    """INF-6144 W3 parity: trailer/generation groups match the full model list.

    The old inline ci.yml regex caught cursor / chatgpt / sonnet / opus / haiku
    trailers and 'Generated by <anthropic/openai/bard/sonnet/opus/haiku/llm>';
    consolidation into COMPILED must not lose them. Co-Authored-By fragments are
    assembled at runtime so this source does not trip ci.yml's code-scan.
    """
    mod = _load_module()
    coauth = "Co-Authored" + "-By: "
    assert mod.find_signature("subj\n\n" + coauth + "Sonnet <x@y.invalid>") is not None
    assert mod.find_signature("subj\n\n" + coauth + "Cursor <x@y.invalid>") is not None
    assert mod.find_signature("subj\n\n" + coauth + "Opus <x@y.invalid>") is not None
    assert mod.find_signature("subj\n\nGenerated by Opus") is not None
    assert mod.find_signature("subj\n\nGenerated by Anthropic tooling") is not None


def test_bare_model_word_not_flagged():
    """A bare model word in an ordinary subject/body is NOT a signature.

    The patterns are anchored to trailer / 'generated by|with|using' / 'built
    with' context, so a plain 'opus'/'haiku' word or an unrelated 'generated
    with airflow' must not false-positive.
    """
    mod = _load_module()
    assert mod.find_signature("Refactor opus module and tidy haiku formatting") is None
    assert mod.find_signature("Generated with airflow scheduler config") is None
