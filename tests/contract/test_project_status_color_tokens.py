# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition -- source-available, single-user use only.

"""Contract test: PROJECT_STATUS_META color tokens must exist in main.scss.

Failure mode this test guards against
-------------------------------------
A future contributor changes the ``color_token`` for a status (e.g.
``"color-status-complete"`` -> ``"color-status-success"``) without
declaring the matching CSS custom property in
``frontend/src/styles/main.scss``. ``StatusBadge.vue`` would silently
fall back to the muted gray hex (the FALLBACK_HEX in the component),
producing a uniformly-gray status bar in the UI -- a regression that
runs green in every Vitest test that uses jsdom (where
getComputedStyle returns empty for unset tokens, exercising exactly
the fallback path).

This test reads the SCSS file at test time and verifies every distinct
``color_token`` in ``PROJECT_STATUS_META`` resolves to a
``--<token>: ...`` declaration. It does NOT assert hex values -- those
are owned by ``design-tokens.scss`` and visual-design review.
"""

from __future__ import annotations

import re
from pathlib import Path

from giljo_mcp.domain.project_status import PROJECT_STATUS_META


_REPO_ROOT = Path(__file__).resolve().parents[2]
_MAIN_SCSS = _REPO_ROOT / "frontend" / "src" / "styles" / "main.scss"


def test_main_scss_file_exists() -> None:
    """Sanity: the frontend stylesheet that the StatusBadge resolves
    against must exist.
    """

    assert _MAIN_SCSS.is_file(), (
        f"main.scss not found at {_MAIN_SCSS}. The frontend StatusBadge "
        "resolves color_token strings against CSS custom properties declared "
        "here. If you moved the file, update this test."
    )


def test_every_status_color_token_is_declared_in_main_scss() -> None:
    """Every ``color_token`` in ``PROJECT_STATUS_META`` has a matching
    ``--<token>:`` declaration in main.scss.

    Backend declares the token NAME (e.g. ``color-status-complete``);
    frontend declares the VALUE (e.g. ``#67bd6d``). This test verifies
    the join across the layer boundary.
    """

    text = _MAIN_SCSS.read_text(encoding="utf-8")

    # Distinct tokens to check (set, since multiple statuses can map to
    # the same token, e.g. TERMINATED and DELETED both use color-agent-analyzer).
    tokens = {meta.color_token for meta in PROJECT_STATUS_META.values()}
    assert tokens, "PROJECT_STATUS_META has no color tokens; check the enum."

    missing: list[str] = []
    for token in sorted(tokens):
        # Match ``--<token>:`` allowing whitespace around the colon and
        # the value to follow. Anchored at line start (after any leading
        # whitespace) to avoid matching the same string inside a comment
        # body.
        pattern = re.compile(rf"^\s*--{re.escape(token)}\s*:", re.MULTILINE)
        if not pattern.search(text):
            missing.append(token)

    assert not missing, (
        f"PROJECT_STATUS_META declares color tokens that are NOT defined as CSS "
        f"custom properties in {_MAIN_SCSS}: {missing}. "
        "StatusBadge.vue will silently fall back to muted gray. "
        "Either add `--<token>: <hex>;` declarations to main.scss or update "
        "PROJECT_STATUS_META to use existing tokens."
    )


def test_no_hex_literal_in_project_status_meta() -> None:
    """``color_token`` strings must be SCSS token NAMES, not hex literals.

    Defense-in-depth: a regression where someone short-circuits the SCSS
    indirection by hard-coding ``"#67bd6d"`` defeats the purpose of the
    color-token system and breaks theming.
    """

    hex_pattern = re.compile(r"^#[0-9a-fA-F]{3,8}$")
    for member, meta in PROJECT_STATUS_META.items():
        assert not hex_pattern.match(meta.color_token), (
            f"PROJECT_STATUS_META[{member.name}].color_token is a hex literal "
            f"({meta.color_token!r}). Use a SCSS custom-property name like "
            "'color-status-complete' instead."
        )
