# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Single source of truth for taxonomy-alias rendering (BE-6049a).

A taxonomy alias is the human-facing serial label for a project or task,
e.g. ``BE-0017`` or ``TSK-0042a``. Historically the same string was built in
two independent places — a SQL ``column_property`` (models/projects.py,
models/tasks.py) and several Python f-strings — which could silently drift.

Worse, every builder hard-padded the serial to exactly 4 digits via
``lpad(cast(series, text), 4, '0')`` / ``f"{n:04d}"``. ``lpad`` *truncates*
when the value is longer than the width, so a grandfathered 5-digit serial
(``10000``) rendered as ``"1000"`` — a live display bug.

This module is the canonical Python builder. It pads to a **minimum** of 4
digits and **never truncates** (full width up to 6 digits). The SQL builders
mirror it with ``lpad(..., greatest(4, length(...)), '0')``; a parity test
(tests/unit/models/test_taxonomy_alias.py) asserts SQL output == this helper
for boundary serials so the two can never drift again.
"""

from __future__ import annotations


def format_taxonomy_alias(
    abbreviation: str | None,
    series_number: int | None,
    subseries: str | None = None,
    *,
    fallback: str = "",
) -> str:
    """Render a taxonomy alias from its parts.

    Args:
        abbreviation: Taxonomy type abbreviation (e.g. ``"BE"``); ``None``/``""``
            when the row carries no type.
        series_number: Serial integer (1..9999 for new rows; grandfathered rows
            may exceed 9999 — never truncated). ``None`` when unnumbered.
        subseries: Single-letter suffix (e.g. ``"a"`` in ``BE-0001a``);
            ``None``/``""`` when absent.
        fallback: Returned only when BOTH ``abbreviation`` and ``series_number``
            are absent. Project passes its random ``alias``; Task passes ``""``
            (its default), matching the respective SQL ``column_property``.

    Returns:
        The formatted alias. Examples (default ``fallback=""``)::

            format_taxonomy_alias("BE", 17)        -> "BE-0017"
            format_taxonomy_alias("BE", 17, "a")   -> "BE-0017a"
            format_taxonomy_alias("BE", 10000)     -> "BE-10000"   (no truncation)
            format_taxonomy_alias("BE", None)      -> "BE"
            format_taxonomy_alias(None, 17)        -> "0017"
            format_taxonomy_alias(None, None)      -> ""           (== fallback)
    """
    abbr = abbreviation or ""
    if series_number is None:
        # Type-only (or wholly empty -> caller's fallback). Mirrors the SQL
        # ``series_number IS NULL`` branch which returns coalesce(abbr, "").
        return abbr or fallback
    # ``zfill`` pads to a minimum width of 4 and never truncates, mirroring the
    # SQL ``lpad(..., greatest(4, length(...)), '0')``.
    padded = str(series_number).zfill(4)
    sep = "-" if abbr else ""
    return f"{abbr}{sep}{padded}{subseries or ''}"
