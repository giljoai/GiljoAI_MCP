# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition -- source-available.

"""
Unit tests for scripts/ci_guardrails.sh -- Guardrail 6 (alembic revision ID length).

The guardrail caps revision IDs at 60 chars (ce_0003 widens the column to 64,
4-char headroom). These tests run the actual shell script against a synthetic
fixture directory that mirrors the repo layout: ``migrations/versions/`` and
``migrations/saas_versions/`` containing exactly one revision file per case.

We invoke the script with ``REPO_ROOT`` overridden via a wrapper so it scans
only the fixture, never the real repo.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from textwrap import dedent

import pytest


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
GUARDRAIL_SCRIPT = PROJECT_ROOT / "scripts" / "ci_guardrails.sh"


def _make_revision_file(path: Path, revision_id: str) -> None:
    path.write_text(
        dedent(
            f'''
            """Synthetic revision for guardrail test."""

            revision = "{revision_id}"
            down_revision = None
            branch_labels = None
            depends_on = None


            def upgrade() -> None:
                pass


            def downgrade() -> None:
                pass
            '''
        ).lstrip()
    )


def _build_fake_repo(root: Path, ce_revision: str | None, saas_revision: str | None) -> None:
    """Build a minimal fake repo just for guardrail #6.

    Layout:
        root/
            migrations/
                versions/<ce_revision>.py    (if ce_revision is not None)
                saas_versions/<saas_revision>.py  (if saas_revision is not None)
            scripts/
                ci_guardrails.sh   (copied from real repo)
            src/, api/             (empty -- other guardrails skip on empty)
            frontend/              (omitted -- guardrail 4 skips)
    """
    (root / "migrations" / "versions").mkdir(parents=True)
    (root / "migrations" / "saas_versions").mkdir(parents=True)
    (root / "scripts").mkdir(parents=True)
    (root / "src").mkdir()
    (root / "api").mkdir()
    (root / "api" / "endpoints").mkdir()

    if ce_revision is not None:
        _make_revision_file(root / "migrations" / "versions" / f"{ce_revision}.py", ce_revision)
    if saas_revision is not None:
        _make_revision_file(root / "migrations" / "saas_versions" / f"{saas_revision}.py", saas_revision)

    # Copy the script and replace its `main "$@"` invocation with a single
    # call to check_alembic_revision_length so the test runs only check #6
    # (and not the slow auth-AST scan or frontend bundle build).
    src = GUARDRAIL_SCRIPT.read_text(encoding="utf-8")
    patched = src.replace(
        'main "$@"',
        'check_alembic_revision_length\nexit "$FAIL_COUNT"',
    )
    if patched == src:
        raise RuntimeError("Could not patch ci_guardrails.sh -- 'main \"$@\"' invocation not found")
    target_script = root / "scripts" / "ci_guardrails.sh"
    target_script.write_text(patched, encoding="utf-8")
    target_script.chmod(0o755)


def _run_check_6(fake_root: Path) -> tuple[int, str]:
    """Run the patched guardrail script directly.

    The fake script's main invocation has been rewritten to call only
    check_alembic_revision_length (see _build_fake_repo). REPO_ROOT is
    computed inside the script as ``$(cd "$(dirname "$0")/.." && pwd)``,
    so it resolves to the fake repo root automatically.
    """
    completed = subprocess.run(
        ["bash", str(fake_root / "scripts" / "ci_guardrails.sh")],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    return completed.returncode, completed.stdout + completed.stderr


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRevisionIdGuardrailBoundary:
    """Verify check #6 enforces the 60-char boundary precisely."""

    def test_revision_at_exactly_60_chars_passes(self, tmp_path: Path) -> None:
        rev = "a" * 60
        assert len(rev) == 60
        _build_fake_repo(tmp_path, ce_revision=rev, saas_revision=None)
        rc, output = _run_check_6(tmp_path)
        assert rc == 0, f"60-char revision id was rejected (should pass).\nOutput:\n{output}"
        assert "FAIL" not in output, output

    def test_revision_at_61_chars_fails(self, tmp_path: Path) -> None:
        rev = "b" * 61
        assert len(rev) == 61
        _build_fake_repo(tmp_path, ce_revision=rev, saas_revision=None)
        rc, output = _run_check_6(tmp_path)
        assert rc != 0, f"61-char revision id was accepted (should fail).\nOutput:\n{output}"
        assert "61 chars" in output, output
        assert "FAIL" in output, output

    def test_saas_chain_is_also_scanned(self, tmp_path: Path) -> None:
        """A long revision in saas_versions/ must also fail."""
        rev = "s" * 65
        _build_fake_repo(tmp_path, ce_revision=None, saas_revision=rev)
        rc, output = _run_check_6(tmp_path)
        assert rc != 0, f"Long saas revision was accepted (should fail).\nOutput:\n{output}"
        assert "saas_versions" in output, output

    def test_short_revision_passes(self, tmp_path: Path) -> None:
        _build_fake_repo(tmp_path, ce_revision="ce_0001_short", saas_revision="saas_001_short")
        rc, output = _run_check_6(tmp_path)
        assert rc == 0, f"Short revisions were rejected.\nOutput:\n{output}"

    def test_real_repo_revision_ids_within_limit(self) -> None:
        """Sanity check: every actual revision ID in the real repo is <= 60.

        This is the live-fire equivalent of the synthetic boundary tests.
        If this fails, it means a contributor added a revision ID that the
        guardrail will block in CI -- catching it here is faster.
        """
        violations: list[tuple[str, int]] = []
        for sub in ("versions", "saas_versions"):
            mig_dir = PROJECT_ROOT / "migrations" / sub
            if not mig_dir.is_dir():
                continue
            for path in mig_dir.glob("*.py"):
                if path.name == "__init__.py":
                    continue
                source = path.read_text(encoding="utf-8")
                for line in source.splitlines():
                    stripped = line.strip()
                    if stripped.startswith("revision") and "=" in stripped:
                        # Strip an optional ": str" annotation, e.g.
                        # `revision: str = "baseline_v37"`.
                        rhs = stripped.split("=", 1)[1].strip()
                        if rhs.startswith(("'", '"')):
                            quote = rhs[0]
                            end = rhs.find(quote, 1)
                            if end > 1:
                                rev_id = rhs[1:end]
                                if len(rev_id) > 60:
                                    violations.append((str(path), len(rev_id)))
                        break
        assert not violations, f"Real revision IDs exceed 60-char guardrail: {violations}"
