# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.

"""INF-9190 — release compile round-trip: fragments in → section out →
fragments deleted → idempotent rerun.

The compile script lives in ``internal/dev/compile_changelog.py`` and is
stripped from the CE export; on a stripped tree this module skips green.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
COMPILE_PATH = REPO_ROOT / "internal" / "dev" / "compile_changelog.py"

if not COMPILE_PATH.exists():
    pytest.skip(  # skip: internal/ compile script stripped on CE export -- INF-9190
        reason=(
            "internal/ compile script stripped from this artifact (CE export) -- "
            "release compile runs on the private repo only"
        ),
        allow_module_level=True,
    )

INTRO = "# Changelog\n\nAll notable changes are recorded here.\n\n"
OLD_SECTION = "## [2.0.0] — 2026-07-13\n\n### Added\n\n- **Old entry.** Already released.\n"


def _make_tree(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / "changelog.d").mkdir(parents=True)
    (root / "CHANGELOG.md").write_text(INTRO + OLD_SECTION, encoding="utf-8")
    (root / "changelog.d" / "README.md").write_text("format doc, never compiled\n", encoding="utf-8")
    return root


def _run(root: Path, *extra: str) -> subprocess.CompletedProcess:
    return subprocess.run(  # noqa: PLW1510 -- rc asserted by callers
        [
            sys.executable,
            str(COMPILE_PATH),
            "--version",
            "2.1.0",
            "--date",
            "2026-07-15",
            "--repo-root",
            str(root),
            *extra,
        ],
        capture_output=True,
        text=True,
    )


def test_round_trip_then_idempotent_rerun(tmp_path):
    root = _make_tree(tmp_path)
    frag = root / "changelog.d"
    (frag / "b-fix-login.md").write_text("Fixed\n- **Login works again.** No more spinner.\n", encoding="utf-8")
    (frag / "a-add-export.md").write_text(
        "Added\n- **One-click export.** Download everything as a zip.\n",
        encoding="utf-8",
    )
    (frag / "c-add-search.md").write_text(
        "Added\n- **Search everywhere.** Find any project instantly.\n",
        encoding="utf-8",
    )

    result = _run(root)
    assert result.returncode == 0, result.stdout + result.stderr

    text = (root / "CHANGELOG.md").read_text(encoding="utf-8")
    # New section sits below the intro, above the previous release.
    assert text.startswith(INTRO)
    new_pos = text.index("## [2.1.0] — 2026-07-15")
    old_pos = text.index("## [2.0.0] — 2026-07-13")
    assert new_pos < old_pos
    # Grouped by category, canonical order (Added before Fixed), entries kept.
    added_pos = text.index("### Added", new_pos)
    fixed_pos = text.index("### Fixed", new_pos)
    assert new_pos < added_pos < fixed_pos < old_pos
    assert "- **One-click export.** Download everything as a zip." in text
    assert "- **Search everywhere.** Find any project instantly." in text
    assert "- **Login works again.** No more spinner." in text
    # Pre-existing content survives byte-exact.
    assert text.endswith(OLD_SECTION)

    # The compiled section is printed for review.
    assert "## [2.1.0] — 2026-07-15" in result.stdout

    # Fragments are consumed; the format doc is not.
    assert sorted(p.name for p in frag.iterdir()) == ["README.md"]

    # Idempotent rerun: zero fragments = no-op, CHANGELOG untouched.
    rerun = _run(root)
    assert rerun.returncode == 0, rerun.stdout + rerun.stderr
    assert (root / "CHANGELOG.md").read_text(encoding="utf-8") == text
    assert text.count("## [2.1.0]") == 1


def test_no_fragments_directory_is_a_noop(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    (root / "CHANGELOG.md").write_text(INTRO + OLD_SECTION, encoding="utf-8")
    result = _run(root)
    assert result.returncode == 0, result.stdout + result.stderr
    assert (root / "CHANGELOG.md").read_text(encoding="utf-8") == INTRO + OLD_SECTION


def test_invalid_category_fails_loudly_and_changes_nothing(tmp_path):
    root = _make_tree(tmp_path)
    bad = root / "changelog.d" / "broken.md"
    bad.write_text("Improved\n- Not a valid category.\n", encoding="utf-8")

    result = _run(root)
    assert result.returncode != 0
    assert "broken.md" in (result.stdout + result.stderr)
    # Nothing consumed, nothing written.
    assert bad.exists()
    assert (root / "CHANGELOG.md").read_text(encoding="utf-8") == INTRO + OLD_SECTION
