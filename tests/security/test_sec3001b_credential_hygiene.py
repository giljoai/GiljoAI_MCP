# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""SEC-3001b regression: no database-credential secret is tracked in git.

Class of bug this catches:
    The SEC-3001b incident (untracked in ``ada84d16c``) was a set of
    ``pg_dump`` SQL snapshots committed under ``backups/`` -- one carried a
    (now-rotated) founder DB password and several already-revoked API-key
    hashes. The repo-level mistake that let it happen: a ``.sql`` DB dump and
    the live ``.env`` slipping past ``.gitignore`` into the tracked set.

    This test is the structural backstop so the same class can never silently
    re-enter the tracked tree:
      1. The live secrets file ``.env`` must NEVER be tracked (only the
         placeholder ``.env.example`` is allowed).
      2. No database dump (``.sql`` / ``.dump`` / ``.backup`` / ``.pgdump``)
         and nothing under ``backups/`` may be tracked.
      3. No tracked operator script may carry an INLINE DB credential -- a
         ``scheme://user:password@host`` connection string with a real-looking
         password, or a literal ``PGPASSWORD=<secret>`` (variable references
         like ``PGPASSWORD="${VAR}"`` and placeholders are fine).

    The pre-commit gitleaks hook and the private ``export_gate.py`` already
    scan diffs at commit/push time; this test is the always-on, full-tree
    assertion that survives a force-add or a hook bypass.

Note on scope: rewriting the historical ``backups/*.sql`` blobs out of the git
object DB is a destructive force-push and is the owner's decision (SEC-3001b
project notes). This test asserts the CURRENT tracked set is clean; it does not
walk historical commits.

Edition Scope: CE (repo-hygiene concern affecting all editions/exports).

Parallel-safe: read-only ``git ls-files`` + file reads; no DB, no env mutation,
no module-level mutable state, no ordering dependency.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]

# pg_dump DATA-dump file shapes (NOT .sql -- migrations/verification queries are
# legitimately tracked .sql; the incident was binary/custom-format data dumps).
_DUMP_SUFFIXES = (".dump", ".backup", ".pgdump")

# Inline credential in a connection URL: scheme://user:password@host with a
# >=12-char password. Mirrors the export_gate.py credentials-in-URL rule; >=12
# and excluding { < > skips placeholders like ``:<your-password>@`` / ``${VAR}``.
_URL_CRED_RE = re.compile(r"(?i)\b(?:postgres|postgresql|mysql|mongodb|redis|amqp)://[^\s:@/]+:[^\s@/{<>]{12,}@[^\s/]+")

# Literal PGPASSWORD assignment. We EXCLUDE variable expansions ($VAR, ${VAR},
# %VAR%) and obvious placeholders -- only a hard-coded secret should flag.
_PGPASSWORD_RE = re.compile(r"""PGPASSWORD\s*=\s*["']?(?P<val>[^"'\s]+)""")
_PGPASSWORD_SAFE_PREFIXES = ("$", "{", "%", "<")
_PGPASSWORD_PLACEHOLDERS = ("your", "xxx", "changeme", "example", "placeholder", "redacted")

# Content scan is bounded to executable operator DB tooling (the surface that
# actually shells out to pg_dump/psql). Docs/handover narrative and scanner test
# fixtures legitimately contain credential-shaped EXAMPLES and are out of scope.
_SCRIPT_PREFIXES = ("scripts/", "internal/")
_SCRIPT_SUFFIXES = (".sh", ".ps1", ".bat")


def _tracked_files() -> list[str]:
    out = subprocess.run(["git", "ls-files"], cwd=REPO_ROOT, check=True, capture_output=True, text=True)
    return out.stdout.splitlines()


def test_dotenv_is_not_tracked() -> None:
    """The live secrets file must never be tracked -- only ``.env.example``."""
    tracked = set(_tracked_files())
    assert ".env" not in tracked, (
        ".env is tracked in git -- it holds live DB credentials. Untrack it "
        "(`git rm --cached .env`); only .env.example (placeholders) may be tracked."
    )


def test_backups_dir_has_no_tracked_files() -> None:
    """The ``backups/`` directory -- the exact SEC-3001b incident locus -- must
    have zero tracked files (it is gitignored + export-excluded)."""
    offenders = [p for p in _tracked_files() if p.startswith("backups/")]
    assert not offenders, (
        f"{len(offenders)} file(s) tracked under backups/ -- this is the exact "
        f"SEC-3001b incident (committed pg_dump snapshots carrying live creds). "
        f"Untrack them:\n  " + "\n  ".join(offenders[:20])
    )


def test_no_database_dump_tracked_anywhere() -> None:
    """No pg_dump DATA dump (``.dump`` / ``.backup`` / ``.pgdump``) may be tracked
    anywhere in the tree -- this is the exact SEC-3001b leak class."""
    offenders = [p for p in _tracked_files() if p.lower().endswith(_DUMP_SUFFIXES)]
    assert not offenders, (
        f"{len(offenders)} pg_dump data dump(s) tracked "
        f"(SEC-3001b leak class). Untrack them (git rm --cached):\n  " + "\n  ".join(offenders[:20])
    )


def test_no_inline_db_credential_in_tracked_scripts() -> None:
    """No tracked operator script carries an inline DB password.

    A pg_dump/psql invocation must take its password from the environment
    (``PGPASSWORD="${VAR}"`` / libpq) or ``.pgpass`` -- never a literal baked
    into a tracked connection string or assignment. Scoped to executable
    operator scripts (.sh/.ps1/.bat under scripts/ + internal/), excluding test
    fixtures that deliberately carry credential-shaped strings.
    """
    candidates = [
        p
        for p in _tracked_files()
        if p.startswith(_SCRIPT_PREFIXES) and p.endswith(_SCRIPT_SUFFIXES) and "/tests/" not in p and "/test_" not in p
    ]

    findings: list[str] = []
    for rel in candidates:
        path = REPO_ROOT / rel
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

        for lineno, line in enumerate(text.splitlines(), start=1):
            if _URL_CRED_RE.search(line):
                findings.append(f"{rel}:{lineno}: inline credential in connection URL")

            m = _PGPASSWORD_RE.search(line)
            if m:
                val = m.group("val")
                low = val.lower()
                is_var = val.startswith(_PGPASSWORD_SAFE_PREFIXES)
                is_placeholder = any(low.startswith(ph) for ph in _PGPASSWORD_PLACEHOLDERS)
                if not is_var and not is_placeholder:
                    findings.append(f"{rel}:{lineno}: literal PGPASSWORD assignment")

    assert not findings, (
        "Inline DB credential(s) found in tracked operator scripts (SEC-3001b). "
        "Pass the password via PGPASSWORD env var / .pgpass instead:\n  " + "\n  ".join(findings[:20])
    )
