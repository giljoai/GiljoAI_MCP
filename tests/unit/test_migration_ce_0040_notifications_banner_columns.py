# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""IMP-5037b regression: ce_0040 migration idempotency tests.

Exercises upgrade() / downgrade() against a fake bind so the
information_schema existence guards and op.add_column /
op.create_check_constraint behavior can be verified without a live database.

Mandated regression #3 (failing layer: migration idempotency).
"""

from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Fake connection helpers
# ---------------------------------------------------------------------------


def _build_fake_conn(*, has_columns: tuple[str, ...] = (), has_constraint: bool = False):
    """Return a mock bind whose information_schema queries are pre-seeded.

    *has_columns* is a tuple of column names that already exist in the table.
    *has_constraint* controls whether the CHECK constraint is already present.
    """
    fake_conn = MagicMock()

    def execute(stmt, params=None):
        result = MagicMock()
        text = str(stmt).lower()
        if "information_schema.columns" in text:
            column_name = (params or {}).get("column", "")
            result.first.return_value = (1,) if column_name in has_columns else None
        elif "information_schema.table_constraints" in text:
            result.first.return_value = (1,) if has_constraint else None
        else:
            result.first.return_value = None
        return result

    fake_conn.execute.side_effect = execute
    return fake_conn


_ALL_COLUMNS = ("surface", "role_filter", "cta_label", "cta_route", "dismissible")


# ---------------------------------------------------------------------------
# Upgrade — fresh DB (none of the columns exist)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_upgrade_adds_all_five_columns_on_fresh_db():
    from migrations.versions import ce_0040_notifications_banner_columns as mig

    fake_conn = _build_fake_conn(has_columns=(), has_constraint=False)

    with (
        patch.object(mig.op, "get_bind", return_value=fake_conn),
        patch.object(mig.op, "add_column") as add_column,
        patch.object(mig.op, "create_check_constraint") as create_constraint,
        patch.object(mig.op, "execute"),
    ):
        mig.upgrade()

    added_col_names = [c.args[1].name for c in add_column.call_args_list]
    assert "surface" in added_col_names
    assert "role_filter" in added_col_names
    assert "cta_label" in added_col_names
    assert "cta_route" in added_col_names
    assert "dismissible" in added_col_names
    assert add_column.call_count == 5
    assert create_constraint.call_count == 1


@pytest.mark.unit
def test_upgrade_surface_column_has_correct_server_default():
    from migrations.versions import ce_0040_notifications_banner_columns as mig

    fake_conn = _build_fake_conn(has_columns=(), has_constraint=False)

    with (
        patch.object(mig.op, "get_bind", return_value=fake_conn),
        patch.object(mig.op, "add_column") as add_column,
        patch.object(mig.op, "create_check_constraint"),
        patch.object(mig.op, "execute"),
    ):
        mig.upgrade()

    surface_call = next(c for c in add_column.call_args_list if c.args[1].name == "surface")
    col = surface_call.args[1]
    assert "bell" in str(col.server_default.arg).lower()
    assert col.nullable is False


@pytest.mark.unit
def test_upgrade_dismissible_column_not_nullable():
    from migrations.versions import ce_0040_notifications_banner_columns as mig

    fake_conn = _build_fake_conn(has_columns=(), has_constraint=False)

    with (
        patch.object(mig.op, "get_bind", return_value=fake_conn),
        patch.object(mig.op, "add_column") as add_column,
        patch.object(mig.op, "create_check_constraint"),
        patch.object(mig.op, "execute"),
    ):
        mig.upgrade()

    dismissible_call = next(c for c in add_column.call_args_list if c.args[1].name == "dismissible")
    col = dismissible_call.args[1]
    assert col.nullable is False


# ---------------------------------------------------------------------------
# Upgrade — idempotent (all columns already present, constraint already exists)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_upgrade_is_noop_when_all_columns_and_constraint_present():
    """Regression: CE installer reruns alembic upgrade head on every boot."""
    from migrations.versions import ce_0040_notifications_banner_columns as mig

    fake_conn = _build_fake_conn(has_columns=_ALL_COLUMNS, has_constraint=True)

    with (
        patch.object(mig.op, "get_bind", return_value=fake_conn),
        patch.object(mig.op, "add_column") as add_column,
        patch.object(mig.op, "create_check_constraint") as create_constraint,
        patch.object(mig.op, "execute"),
    ):
        mig.upgrade()

    assert add_column.call_count == 0, "upgrade must not re-add columns that already exist"
    assert create_constraint.call_count == 0, "upgrade must not re-create constraint that already exists"


@pytest.mark.unit
def test_upgrade_partial_run_adds_missing_columns_skips_existing():
    """Partial prior run: only 'surface' was added; the other 4 are missing."""
    from migrations.versions import ce_0040_notifications_banner_columns as mig

    fake_conn = _build_fake_conn(has_columns=("surface",), has_constraint=False)

    with (
        patch.object(mig.op, "get_bind", return_value=fake_conn),
        patch.object(mig.op, "add_column") as add_column,
        patch.object(mig.op, "create_check_constraint") as create_constraint,
        patch.object(mig.op, "execute"),
    ):
        mig.upgrade()

    added_col_names = [c.args[1].name for c in add_column.call_args_list]
    assert "surface" not in added_col_names, "surface already existed — must not be re-added"
    assert "role_filter" in added_col_names
    assert "cta_label" in added_col_names
    assert "cta_route" in added_col_names
    assert "dismissible" in added_col_names
    assert add_column.call_count == 4
    assert create_constraint.call_count == 1


# ---------------------------------------------------------------------------
# CHECK constraint — surface IN ('bell','banner','both')
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_upgrade_check_constraint_covers_valid_surface_values():
    from migrations.versions import ce_0040_notifications_banner_columns as mig

    fake_conn = _build_fake_conn(has_columns=(), has_constraint=False)

    with (
        patch.object(mig.op, "get_bind", return_value=fake_conn),
        patch.object(mig.op, "add_column"),
        patch.object(mig.op, "create_check_constraint") as create_constraint,
        patch.object(mig.op, "execute"),
    ):
        mig.upgrade()

    assert create_constraint.call_count == 1
    constraint_expr = create_constraint.call_args.args[2]
    for surface_val in ("bell", "banner", "both"):
        assert surface_val in constraint_expr, f"'{surface_val}' must appear in CHECK expression"


@pytest.mark.unit
def test_upgrade_check_constraint_uses_correct_name():
    from migrations.versions import ce_0040_notifications_banner_columns as mig

    fake_conn = _build_fake_conn(has_columns=(), has_constraint=False)

    with (
        patch.object(mig.op, "get_bind", return_value=fake_conn),
        patch.object(mig.op, "add_column"),
        patch.object(mig.op, "create_check_constraint") as create_constraint,
        patch.object(mig.op, "execute"),
    ):
        mig.upgrade()

    constraint_name = create_constraint.call_args.args[0]
    assert constraint_name == "ck_notifications_surface"


# ---------------------------------------------------------------------------
# Downgrade
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_downgrade_drops_constraint_and_all_columns_when_present():
    from migrations.versions import ce_0040_notifications_banner_columns as mig

    fake_conn = _build_fake_conn(has_columns=_ALL_COLUMNS, has_constraint=True)

    with (
        patch.object(mig.op, "get_bind", return_value=fake_conn),
        patch.object(mig.op, "drop_constraint") as drop_constraint,
        patch.object(mig.op, "drop_column") as drop_column,
    ):
        mig.downgrade()

    assert drop_constraint.call_count == 1
    dropped_cols = [c.args[1] for c in drop_column.call_args_list]
    for col in _ALL_COLUMNS:
        assert col in dropped_cols, f"downgrade must drop column '{col}'"


@pytest.mark.unit
def test_downgrade_is_noop_when_already_downgraded():
    from migrations.versions import ce_0040_notifications_banner_columns as mig

    fake_conn = _build_fake_conn(has_columns=(), has_constraint=False)

    with (
        patch.object(mig.op, "get_bind", return_value=fake_conn),
        patch.object(mig.op, "drop_constraint") as drop_constraint,
        patch.object(mig.op, "drop_column") as drop_column,
    ):
        mig.downgrade()

    assert drop_constraint.call_count == 0
    assert drop_column.call_count == 0


# ---------------------------------------------------------------------------
# Revision chain
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_revision_id_and_chain():
    from migrations.versions import ce_0040_notifications_banner_columns as mig

    assert mig.revision == "ce_0040_notifications_banner_columns"
    assert mig.down_revision == "ce_0039_create_notifications"
