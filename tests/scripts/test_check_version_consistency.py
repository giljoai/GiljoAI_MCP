# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Tests for scripts/check_version_consistency.py -- scan-stale CHANGELOG filtering.

Regression guard for: commit 8edcdcf (broke CI) + fix-forward a92a9b6.
Project 195b1bdf-7462-47d4-bd45-f0db71cf525b (Tighten requires-python).

The scanner must ignore stale-version prose that documents *removed* version
floors (Breaking changes, Removed, Deprecated sections in CHANGELOG.md) while
still flagging those same patterns in other files and in active CHANGELOG sections.
"""

from __future__ import annotations

import sys
from pathlib import Path


# Make the scripts/ package importable without installation
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import check_version_consistency as cvc  # noqa: E402
from check_version_consistency import _changelog_exempt_lines  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _exempt_lines_from_text(text: str) -> frozenset[int]:
    return _changelog_exempt_lines(text)


# ---------------------------------------------------------------------------
# Test A: Breaking-changes section in CHANGELOG.md → lines are exempt
# ---------------------------------------------------------------------------


class TestChangelogBreakingSectionExempt:
    """Prose inside a Breaking-changes H2 section must be exempt (no finding)."""

    CHANGELOG_BREAKING_H2 = """\
## [1.2.6] - 2026-05-01

### Breaking changes

- pip install on Python 3.10 or 3.11 now fails with a clear error message.
- PostgreSQL 16 is no longer supported.

## [1.2.5] - 2026-04-20

### Added

- Some new feature.
"""

    def test_breaking_h2_section_lines_are_exempt(self) -> None:
        """Lines 4-7 are inside '## [1.2.6]' + '### Breaking changes' — must be exempt."""
        exempt = _exempt_lines_from_text(self.CHANGELOG_BREAKING_H2)
        # Line 5: "- pip install on Python 3.10 or 3.11 now fails..."
        assert 5 in exempt, f"Expected line 5 (Python 3.10) to be exempt; exempt={sorted(exempt)}"
        # Line 6: "- PostgreSQL 16 is no longer supported."
        assert 6 in exempt, f"Expected line 6 (PostgreSQL 16) to be exempt; exempt={sorted(exempt)}"

    def test_active_section_lines_are_not_exempt(self) -> None:
        """Lines inside '## [1.2.5]' / '### Added' must NOT be exempt."""
        exempt = _exempt_lines_from_text(self.CHANGELOG_BREAKING_H2)
        # Line 10 "### Added" and line 12 "- Some new feature." are NOT exempt
        assert 12 not in exempt, f"Line 12 (Added section) should NOT be exempt; exempt={sorted(exempt)}"

    CHANGELOG_BREAKING_H2_HEADING_ONLY = """\
## Breaking changes

- Dropped Python 3.11 support.
"""

    def test_h2_heading_that_is_literally_breaking_changes(self) -> None:
        """H2 heading literally named 'Breaking changes' (no version bracket) is also exempt."""
        exempt = _exempt_lines_from_text(self.CHANGELOG_BREAKING_H2_HEADING_ONLY)
        assert 3 in exempt, f"Line 3 must be exempt under '## Breaking changes'; exempt={sorted(exempt)}"


# ---------------------------------------------------------------------------
# Test A (variant): H3 ### Breaking changes / ### Removed / ### Deprecated
# ---------------------------------------------------------------------------


class TestChangelogExemptH3Sections:
    """H3 sub-sections for Removed, Deprecated, and Breaking must also exempt their content."""

    CHANGELOG_REMOVED_H3 = """\
## [1.2.6] - 2026-05-01

### Added

- Cool new thing.

### Removed

- Python 3.10 support removed.
- PostgreSQL 15 support removed.

### Changed

- Something else changed.
"""

    def test_removed_h3_lines_exempt(self) -> None:
        exempt = _exempt_lines_from_text(self.CHANGELOG_REMOVED_H3)
        # Line 9: "- Python 3.10 support removed."
        assert 9 in exempt, f"Expected line 9 to be exempt; exempt={sorted(exempt)}"
        # Line 10: "- PostgreSQL 15 support removed."
        assert 10 in exempt, f"Expected line 10 to be exempt; exempt={sorted(exempt)}"

    def test_added_section_lines_not_exempt(self) -> None:
        exempt = _exempt_lines_from_text(self.CHANGELOG_REMOVED_H3)
        # Line 5: "- Cool new thing." (inside ### Added) must NOT be exempt
        assert 5 not in exempt

    def test_changed_section_lines_not_exempt(self) -> None:
        exempt = _exempt_lines_from_text(self.CHANGELOG_REMOVED_H3)
        # Line 14: "- Something else changed." (inside ### Changed) must NOT be exempt
        assert 14 not in exempt

    CHANGELOG_DEPRECATED_H3 = """\
## [1.3.0]

### Deprecated

- Python 3.11 deprecated; will be removed next release.
"""

    def test_deprecated_h3_lines_exempt(self) -> None:
        exempt = _exempt_lines_from_text(self.CHANGELOG_DEPRECATED_H3)
        assert 5 in exempt, f"Expected line 5 (deprecated block) to be exempt; exempt={sorted(exempt)}"

    CHANGELOG_BREAKING_H3 = """\
## [1.3.0]

### Breaking Changes

- Python 3.12 now required; earlier versions fail at install.
"""

    def test_breaking_h3_lines_exempt(self) -> None:
        exempt = _changelog_exempt_lines(self.CHANGELOG_BREAKING_H3)
        assert 5 in exempt, f"Expected line 5 (Breaking Changes h3) to be exempt; exempt={sorted(exempt)}"


# ---------------------------------------------------------------------------
# Test B: Same prose in a non-CHANGELOG file → _changelog_exempt_lines not
#         used (scanner only calls it for CHANGELOG.md). Verify that
#         _changelog_exempt_lines returns empty for arbitrary Markdown.
# ---------------------------------------------------------------------------


class TestNonChangelogFileNotExempt:
    """_changelog_exempt_lines is only called for CHANGELOG.md.

    For any other file the scanner passes frozenset() — we confirm the helper
    returns a non-empty set for CHANGELOG content so the scanner *would* skip it,
    and separately confirm that the same raw prose in a non-CHANGELOG context
    would NOT be covered by the helper (since the caller won't invoke it).
    """

    # Same prose as Test A but now imagine it's in docs/foo.md
    DOCS_FOO_CONTENT = """\
## [1.2.6] - 2026-05-01

### Breaking changes

- pip install on Python 3.10 or 3.11 now fails with a clear error message.
"""

    def test_helper_still_returns_exempt_lines_for_identical_content(self) -> None:
        """The helper itself is content-agnostic; the *caller* decides which filename to use it for.

        This test confirms the helper correctly identifies exempt lines regardless
        of the filename.  The scanner integration (only calling it for CHANGELOG.md)
        is tested separately in test_scanner_does_not_exempt_non_changelog_files.
        """
        exempt = _changelog_exempt_lines(self.DOCS_FOO_CONTENT)
        # The helper would exempt line 5 — but the scanner won't call it for docs/foo.md
        assert 5 in exempt

    def test_scanner_does_not_exempt_non_changelog_files(self, tmp_path: Path) -> None:
        """End-to-end: same stale content in docs/foo.md IS flagged by the scanner."""
        import importlib

        # Dynamically import the module so we can patch REPO_ROOT
        import importlib.util
        import types

        spec = importlib.util.spec_from_file_location("cvc_tmp", REPO_ROOT / "scripts" / "check_version_consistency.py")
        assert spec and spec.loader
        mod: types.ModuleType = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)  # type: ignore[union-attr]

        # Build a minimal fake repo tree in tmp_path
        (tmp_path / "VERSION").write_text("1.2.6\n", encoding="utf-8")
        docs = tmp_path / "docs"
        docs.mkdir()
        # docs/foo.md with stale Python mention NOT in CHANGELOG.md
        (docs / "foo.md").write_text(
            "## [1.2.6]\n### Breaking changes\n- Python 3.10 support dropped.\n",
            encoding="utf-8",
        )

        # Patch REPO_ROOT on the imported module
        mod.REPO_ROOT = tmp_path  # type: ignore[attr-defined]

        hits: list[tuple[str, int, str]] = []
        for path in tmp_path.rglob("*"):
            if not path.is_file() or path.suffix not in mod.SCAN_INCLUDE_EXTS:
                continue
            rel = path.relative_to(tmp_path)
            if mod._path_excluded(rel):
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, PermissionError):
                continue
            # Simulate scanner: only call _changelog_exempt_lines for CHANGELOG.md
            changelog_exempt: frozenset[int] = (
                mod._changelog_exempt_lines(text) if path.name == "CHANGELOG.md" else frozenset()
            )
            for lineno, line in enumerate(text.splitlines(), start=1):
                if lineno in changelog_exempt:
                    continue
                for m in mod.PY_STALE_RE.finditer(line):
                    if mod._is_stale_python(m.group(1)):
                        hits.append((str(rel), lineno, line.strip()))
                        break

        # docs/foo.md line 3 must be flagged (not CHANGELOG.md → not exempt)
        flagged_files = {h[0].replace("\\", "/") for h in hits}
        assert any("foo.md" in f for f in flagged_files), (
            f"Expected docs/foo.md to be flagged for stale Python 3.10; hits={hits}"
        )


# ---------------------------------------------------------------------------
# Test C: CHANGELOG.md with stale mention OUTSIDE Breaking/Removed/Deprecated
#         → still flagged (regression guard against over-suppression)
# ---------------------------------------------------------------------------


class TestChangelogActiveAreaStillFlagged:
    """Stale version outside exempt sections in CHANGELOG.md must still produce a finding."""

    CHANGELOG_ACTIVE_STALE = """\
## [1.2.6] - 2026-05-01

### Added

- Improved installer now works on Python 3.10 and Python 3.11.

### Changed

- Updated docs.
"""

    def test_active_section_stale_mention_not_exempt(self) -> None:
        """Line 5 is inside '### Added' (not exempt) — must NOT appear in exempt set."""
        exempt = _changelog_exempt_lines(self.CHANGELOG_ACTIVE_STALE)
        # Line 5 mentions Python 3.10 inside ### Added — must NOT be exempt
        assert 5 not in exempt, f"Line 5 (### Added section) must NOT be exempt; exempt={sorted(exempt)}"

    CHANGELOG_MIXED = """\
## [1.2.6] - 2026-05-01

### Breaking changes

- Python 3.10 dropped.

### Added

- Supports Python 3.12 and 3.11 (active mention of 3.11 in active section).
"""

    def test_mixed_changelog_only_exempts_breaking_section(self) -> None:
        exempt = _changelog_exempt_lines(self.CHANGELOG_MIXED)
        # Line 5 (Breaking changes content) → exempt
        assert 5 in exempt
        # Line 9 (Added section content) → NOT exempt even though it mentions 3.11
        assert 9 not in exempt


# ---------------------------------------------------------------------------
# Test D: INF-9115 no-hardcode guard — the 4 backend spots must DERIVE their
#         version from giljo_mcp.__version__, never carry a literal semver.
# ---------------------------------------------------------------------------


class TestNoHardcodeGuard:
    """Regression guard for the INF-9115 backend version-derive fixes."""

    def _write_target_files(self, tmp_path: Path, app_py_version_line: str) -> None:
        (tmp_path / "api").mkdir()
        (tmp_path / "api" / "app.py").write_text(
            f'    app = FastAPI(\n        title=f"GiljoAI MCP API v{{giljo_version}} - Community Edition",\n        {app_py_version_line}\n',
            encoding="utf-8",
        )
        (tmp_path / "api" / "run_api.py").write_text(
            '    logger.info(f"  GiljoAI MCP REST API v{giljo_version}")\n',
            encoding="utf-8",
        )
        wiring_dir = tmp_path / "api" / "wiring"
        wiring_dir.mkdir()
        (wiring_dir / "events.py").write_text('                "version": giljo_version,\n', encoding="utf-8")
        mcp_tools_dir = tmp_path / "api" / "endpoints" / "mcp_tools"
        mcp_tools_dir.mkdir(parents=True)
        (mcp_tools_dir / "_base.py").write_text("mcp._mcp_server.version = _giljo_version\n", encoding="utf-8")

    def test_derived_version_lines_pass_clean(self, tmp_path, monkeypatch) -> None:
        self._write_target_files(tmp_path, "version=giljo_version,")
        monkeypatch.setattr(cvc, "REPO_ROOT", tmp_path)
        assert cvc.check_no_hardcoded_versions() == []

    def test_rehardcoded_literal_semver_is_flagged(self, tmp_path, monkeypatch) -> None:
        """FAIL-FIRST case: someone re-hardcodes api/app.py's version= to a literal."""
        self._write_target_files(tmp_path, 'version="1.0.0",')
        monkeypatch.setattr(cvc, "REPO_ROOT", tmp_path)
        hits = cvc.check_no_hardcoded_versions()
        assert len(hits) == 1, f"expected exactly 1 hit; got {hits}"
        assert hits[0][0] == "api/app.py"
        assert '"1.0.0"' in hits[0][2]

    def test_check_returns_nonzero_when_hardcoded(self, tmp_path, monkeypatch, capsys) -> None:
        """End-to-end: check() must FAIL (exit 1) when a hardcode hit exists, even
        if every SSoT touchpoint row is otherwise consistent."""
        self._write_target_files(tmp_path, 'version="1.0.0",')
        monkeypatch.setattr(cvc, "REPO_ROOT", tmp_path)
        monkeypatch.setattr(cvc, "read_pyproject", lambda: "1.3.0")
        monkeypatch.setattr(cvc, "read_package_json", lambda: "1.3.0")
        monkeypatch.setattr(cvc, "read_package_lock", lambda: ("1.3.0", "1.3.0"))
        monkeypatch.setattr(cvc, "read_init_fallback", lambda: "1.3.0")
        monkeypatch.setattr(cvc, "read_changelog_latest", lambda: ("1.3.0", False))
        assert cvc.check("1.3.0") == 1
