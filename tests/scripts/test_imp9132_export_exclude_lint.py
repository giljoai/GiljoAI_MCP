# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.

"""IMP-9132 test 5 — .export-exclude pattern lines carry no inline '#'.

``export_ce.sh:199`` strips comments from each ``.export-exclude`` line with
``sed 's/#.*//'``. A PATTERN (non-comment) line that contains a '#' is TRUNCATED at
the '#', so the intended exclusion pattern silently changes — and the failure
direction is a LEAK: a file that should have been stripped from the CE bundle ships
instead. Full-line comments (a line whose first non-space char is '#') are fine; this
bans '#' appearing inside a pattern line.

``.export-exclude`` excludes itself from CE export, so the file is absent inside a CE
checkout — the test skips there (private-repo-only lint).
"""

from __future__ import annotations

from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
EXPORT_EXCLUDE = REPO_ROOT / ".export-exclude"

pytestmark = pytest.mark.skipif(
    not EXPORT_EXCLUDE.exists(),
    reason=".export-exclude is absent (it excludes itself from CE export) — this is a private-repo-only lint",
)


def test_no_inline_hash_in_pattern_lines():
    offenders: list[str] = []
    for lineno, raw in enumerate(EXPORT_EXCLUDE.read_text(encoding="utf-8").splitlines(), 1):
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue  # blank line or full-line comment — safe
        if "#" in raw:
            offenders.append(f"{lineno}: {raw!r}")
    assert not offenders, (
        "export_ce.sh:199 strips '#...' from every .export-exclude line "
        "(`sed 's/#.*//'`), so an inline '#' TRUNCATES the pattern — the intended file "
        "is then NOT excluded and LEAKS into the CE bundle. Put the note on its own "
        "full-line comment above the pattern instead. Offending pattern lines:\n" + "\n".join(offenders)
    )
