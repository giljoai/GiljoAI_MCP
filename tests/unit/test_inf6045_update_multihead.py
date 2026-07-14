# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""INF-6045: update.py must not crash the CE update-check on a multi-head DB.

`update.py:_get_revisions` historically called alembic's singular
``MigrationContext.get_current_revision()``, which raises ``CommandError`` when
the ``alembic_version`` table holds more than one head (a forked/dual-chain DB).
It is the lone repo caller of that singular API. The fix switches to the plural
``get_current_heads()`` (matching scripts/alembic_cli.py) and tolerates >1 head
by taking the first, so the update check degrades gracefully instead of crashing.

Edition Scope: CE
"""

from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import update  # repo-root CE update-checker


@contextmanager
def _patched_alembic(heads: list[str], script_head: str = "ce_head"):
    """Patch alembic + sqlalchemy so _get_revisions runs without a real DB.

    The DB's ``get_current_heads()`` returns ``heads`` (0, 1, or many).
    """
    from alembic.util import CommandError

    ctx = MagicMock()
    ctx.get_current_heads.return_value = heads
    # Faithfully mimic real alembic: the singular API raises on >1 head. If code
    # ever regresses to get_current_revision(), the except-branch swallows this
    # and returns (None, None) -- the assertions below then fail loudly.
    if len(heads) > 1:
        ctx.get_current_revision.side_effect = CommandError("Version table has more than one head present")
    else:
        ctx.get_current_revision.return_value = heads[0] if heads else None

    conn = MagicMock()
    engine = MagicMock()
    engine.connect.return_value.__enter__.return_value = conn

    script = MagicMock()
    script.get_current_head.return_value = script_head

    with (
        patch.object(update, "ROOT") as root,
        patch("alembic.config.Config"),
        patch("alembic.script.ScriptDirectory.from_config", return_value=script),
        patch("alembic.runtime.migration.MigrationContext.configure", return_value=ctx),
        patch("sqlalchemy.create_engine", return_value=engine),
    ):
        # alembic.ini existence check must pass
        root.__truediv__.return_value.exists.return_value = True
        yield


def test_multihead_db_does_not_crash_and_returns_first_head():
    """Two stamped heads must NOT raise; _get_revisions returns the first head."""
    with _patched_alembic(heads=["saas_020_x", "ce_0042_y"], script_head="ce_0042_y"):
        current, head = update._get_revisions("postgresql://fake/db")

    assert current == "saas_020_x"  # first of the multi-head set, no CommandError
    assert head == "ce_0042_y"


def test_single_head_unchanged():
    """The normal CE single-head case returns that head verbatim."""
    with _patched_alembic(heads=["ce_0042_y"], script_head="ce_0042_y"):
        current, head = update._get_revisions("postgresql://fake/db")

    assert current == "ce_0042_y"
    assert head == "ce_0042_y"


def test_empty_head_returns_none():
    """An un-stamped DB (zero heads) yields a None current, not an IndexError."""
    with _patched_alembic(heads=[], script_head="ce_0042_y"):
        current, head = update._get_revisions("postgresql://fake/db")

    assert current is None
    assert head == "ce_0042_y"
