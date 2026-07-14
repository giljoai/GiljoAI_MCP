# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Drift guard: the CSP inline-hash allowlist in api/middleware/security.py
MUST stay in sync with the actual inline <script>/<style> blocks shipped in
frontend/index.html.

Why this exists: the inline API-URL-config script in index.html was edited
(INF-5012c) without regenerating CSP_SCRIPT_HASH_1, so the CE Content-Security-
Policy shipped a stale hash and the browser blocked a legitimate first-party
inline script on every page load. This test fails the build if the constants
drift from index.html again, so the regression cannot silently reach users.

Self-contained on purpose: it reads frontend/index.html directly and computes
the hashes inline (the same algorithm as scripts/generate_csp_hashes.py). It
does NOT import that script, because scripts/ is stripped from the CE export
while tests/ and frontend/ ship — importing the generator would break the
exported CE test suite.

Parallel-safe (pytest-xdist): pure file read, no DB, no module-level mutable
state.
"""

import base64
import hashlib
import re
from pathlib import Path

import pytest

from api.middleware.security import (
    CSP_SCRIPT_HASH_1,
    CSP_SCRIPT_HASH_2,
    CSP_STYLE_HASH,
)


def _find_index_html() -> Path | None:
    """Locate frontend/index.html by walking up from this test file."""
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "frontend" / "index.html"
        if candidate.exists():
            return candidate
    return None


def _csp_hash(content: str) -> str:
    """SHA-256 of the exact inter-tag content, CSP-formatted. Mirrors
    scripts/generate_csp_hashes.py:calculate_csp_hash."""
    digest = hashlib.sha256(content.encode("utf-8")).digest()
    return f"'sha256-{base64.b64encode(digest).decode('utf-8')}'"


def _extract_inline_hashes(html: str) -> tuple[set[str], set[str]]:
    """Return (style_hashes, script_hashes) for inline blocks in the HTML.
    Inline = no src= attribute. Mirrors the generator's regex."""
    style_hashes = {_csp_hash(m.group(1)) for m in re.finditer(r"<style>(.*?)</style>", html, re.DOTALL)}
    script_hashes = {
        _csp_hash(m.group(1)) for m in re.finditer(r"<script(?![^>]*\bsrc=)(?:[^>]*)>(.*?)</script>", html, re.DOTALL)
    }
    return style_hashes, script_hashes


def _find_dist_index_html() -> Path | None:
    """Locate frontend/dist/index.html by walking up from this test file."""
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "frontend" / "dist" / "index.html"
        if candidate.exists():
            return candidate
    return None


def test_csp_inline_hashes_match_index_html() -> None:
    index_html = _find_index_html()
    if index_html is None:
        pytest.skip("frontend/index.html not present in this checkout")

    style_hashes, script_hashes = _extract_inline_hashes(index_html.read_text(encoding="utf-8"))

    shipped_scripts = {CSP_SCRIPT_HASH_1, CSP_SCRIPT_HASH_2}
    assert script_hashes == shipped_scripts, (
        "CSP script-src hashes in api/middleware/security.py are out of sync "
        "with the inline <script> blocks in frontend/index.html.\n"
        f"  index.html requires: {sorted(script_hashes)}\n"
        f"  security.py ships:   {sorted(shipped_scripts)}\n"
        "Run `python scripts/generate_csp_hashes.py` and update "
        "CSP_SCRIPT_HASH_1 / CSP_SCRIPT_HASH_2."
    )

    assert CSP_STYLE_HASH in style_hashes, (
        "CSP_STYLE_HASH in api/middleware/security.py does not match any inline "
        "<style> block in frontend/index.html.\n"
        f"  index.html style hashes: {sorted(style_hashes)}\n"
        f"  security.py ships:       {CSP_STYLE_HASH}\n"
        "Run `python scripts/generate_csp_hashes.py` and update CSP_STYLE_HASH."
    )


def test_csp_inline_hashes_match_dist_index_html() -> None:
    """Regression guard: the BUILT frontend/dist/index.html must produce the same
    inline-script and inline-style hashes as the source frontend/index.html, which
    the backend's security.py allowlists.

    Why this matters: Vite (or a future plugin/transformer) could theoretically
    normalise, minify, or otherwise transform inline <script>/<style> blocks during
    the build step, silently changing their byte content and therefore their CSP
    hashes. If that happened, every browser page load would receive a CSP violation
    for inline scripts while the header still advertised the pre-build hashes.
    This test catches that class of drift at CI time.

    Skipped when frontend/dist/ has not been built (e.g. backend-only CI runs).
    Parallel-safe: pure file read, no DB, no module-level mutable state.
    """
    dist_html = _find_dist_index_html()
    if dist_html is None:
        pytest.skip("frontend/dist/index.html not present — run `npm run build` first")

    dist_text = dist_html.read_text(encoding="utf-8")

    # Skip when dist/index.html is NOT a real Vite build of this app. Backend-only
    # CI jobs write a placeholder (`<!doctype html><title>ci</title>`) so app-surface
    # tests can mount StaticFiles; that placeholder has none of the inline blocks
    # this guard compares, so asserting against it would be a false failure. A real
    # built index.html always contains the Vue mount root `<div id="app"`. This
    # built-artifact guard therefore runs only where a genuine `npm run build` ran
    # (local dev, or a frontend-build CI) — it never fakes a build to satisfy CI.
    if '<div id="app"' not in dist_text:
        pytest.skip(  # skip: dist/index.html is a CI placeholder, not a real Vite build -- INF-3000d
            reason="frontend/dist/index.html is a CI placeholder, not a real Vite build "
            "— the built-artifact CSP guard only runs against a genuine `npm run build`"
        )

    # read_text() normalises CRLF→LF on Windows, matching the hash algorithm
    # used by scripts/generate_csp_hashes.py and the source-file guard above.
    style_hashes, script_hashes = _extract_inline_hashes(dist_text)

    shipped_scripts = {CSP_SCRIPT_HASH_1, CSP_SCRIPT_HASH_2}
    assert script_hashes == shipped_scripts, (
        "CSP script-src hashes in api/middleware/security.py are out of sync "
        "with the inline <script> blocks in frontend/dist/index.html (built artifact).\n"
        f"  dist/index.html requires: {sorted(script_hashes)}\n"
        f"  security.py ships:        {sorted(shipped_scripts)}\n"
        "The Vite build may have transformed the inline scripts. "
        "Run `python scripts/generate_csp_hashes.py` against the built dist/ and "
        "update CSP_SCRIPT_HASH_1 / CSP_SCRIPT_HASH_2 in api/middleware/security.py."
    )

    assert CSP_STYLE_HASH in style_hashes, (
        "CSP_STYLE_HASH in api/middleware/security.py does not match any inline "
        "<style> block in frontend/dist/index.html (built artifact).\n"
        f"  dist/index.html style hashes: {sorted(style_hashes)}\n"
        f"  security.py ships:            {CSP_STYLE_HASH}\n"
        "Run `python scripts/generate_csp_hashes.py` and update CSP_STYLE_HASH."
    )
