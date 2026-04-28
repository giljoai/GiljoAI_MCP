# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""HO 1028 coverage gap fill: migration ce_0007 idempotency.

The migration's docstring claims each ADD COLUMN is wrapped in an
``information_schema.columns`` check so it is safe to re-apply. The
existing test suite never exercises that guard. This test imports the
migration module and verifies that ``upgrade()`` is a no-op when both
target columns are already reported as present by the conn.

We use a fake ``op.get_bind()`` connection that:
  - returns a row from the ``information_schema.columns`` SELECT (so
    ``_has_column`` reports True for both columns)
  - records all calls to ``op.add_column`` so we can assert it is NOT
    invoked on the re-run path.

This is a unit test — it does not touch a real database. Schema-level
re-apply behavior on a real DB is an integration concern and out of
scope here; we are verifying the IDEMPOTENCY GUARD LOGIC, which is what
the docstring promises.
"""

from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
def test_upgrade_is_noop_when_columns_already_present():
    """Re-running ce_0007.upgrade() must not call add_column when columns exist."""
    from migrations.versions import ce_0007_users_skills_version_tracking as mig

    fake_conn = MagicMock()
    # Any SELECT against information_schema.columns reports the column exists:
    # _has_column(...) calls conn.execute(...).first() and returns truthy.
    fake_result = MagicMock()
    fake_result.first.return_value = (1,)
    fake_conn.execute.return_value = fake_result

    with (
        patch.object(mig.op, "get_bind", return_value=fake_conn),
        patch.object(mig.op, "add_column") as add_column,
    ):
        mig.upgrade()

    # Both columns reported present -> no add_column calls.
    assert add_column.call_count == 0


@pytest.mark.unit
def test_upgrade_adds_columns_when_absent():
    """Fresh-install path must still add both columns."""
    from migrations.versions import ce_0007_users_skills_version_tracking as mig

    fake_conn = MagicMock()
    # information_schema reports no rows -> _has_column returns False.
    fake_result = MagicMock()
    fake_result.first.return_value = None
    fake_conn.execute.return_value = fake_result

    with (
        patch.object(mig.op, "get_bind", return_value=fake_conn),
        patch.object(mig.op, "add_column") as add_column,
    ):
        mig.upgrade()

    # Both columns added.
    assert add_column.call_count == 2
    added_names = [call.args[1].name for call in add_column.call_args_list]
    assert "last_installed_skills_version" in added_names
    assert "last_update_reminder_at" in added_names


@pytest.mark.unit
def test_downgrade_is_noop_when_columns_already_absent():
    """Re-running downgrade after columns were dropped must not call drop_column."""
    from migrations.versions import ce_0007_users_skills_version_tracking as mig

    fake_conn = MagicMock()
    fake_result = MagicMock()
    fake_result.first.return_value = None  # absent
    fake_conn.execute.return_value = fake_result

    with (
        patch.object(mig.op, "get_bind", return_value=fake_conn),
        patch.object(mig.op, "drop_column") as drop_column,
    ):
        mig.downgrade()

    assert drop_column.call_count == 0
