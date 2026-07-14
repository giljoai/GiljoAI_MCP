# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Unit tests for scripts/check_saas_table_references.py.

Guards the de-layered SaaS-table reference check (INF-6144 W/S3 A2) against
regression: it must flag a CE file with a raw-SQL reference to a SaaS-only
table and must NOT flag ORM attribute access or a commented-out reference.

Note: the SaaS table name is assembled from fragments at runtime so this test
file's own source never contains a literal raw-SQL "<keyword> <table>" pair --
otherwise the very CI check under test (saas-table-references, which scans all
CE .py files including tests/) would flag this file. The temp fixture files we
write DO contain the literal reference; this source does not.

Parallel-safe: each test owns its tmp_path fixtures; no module-level mutable
state.
"""

import importlib.util
from pathlib import Path

import pytest


# The SaaS-only table name, never written as a contiguous literal in this file.
_SAAS_TABLE = "ten" + "ants"

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "check_saas_table_references.py"

# scripts/ is dev tooling the CE export strips; these tests target that script,
# so skip them when it is absent (the CE-export Deletion Test runs the suite
# against the stripped artifact). They run in full in private CI. (INF-6144 W/S3)
pytestmark = pytest.mark.skipif(
    not _SCRIPT.exists(),
    reason="scripts/check_saas_table_references.py is stripped from the CE export artifact",
)


def _load_module():
    """Import the script by path (it lives in scripts/, not an importable pkg)."""
    spec = importlib.util.spec_from_file_location("check_saas_table_references", _SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_flags_raw_sql_from_saas_table(tmp_path):
    """A CE file with `FROM <saas table>` in raw SQL is flagged."""
    mod = _load_module()
    bad = tmp_path / "ce_query.py"
    bad.write_text(
        f'def discover(conn):\n    return conn.execute("SELECT id FROM {_SAAS_TABLE} WHERE active = 1")\n',
        encoding="utf-8",
    )

    violations = mod.check_file(str(bad))

    assert violations, "expected the raw-SQL SaaS-table reference to be flagged"
    line_nums = [ln for ln, _ in violations]
    assert 2 in line_nums


def test_does_not_flag_orm_or_comment(tmp_path):
    """ORM attribute access and a commented-out reference are NOT flagged."""
    mod = _load_module()
    ok = tmp_path / "ce_orm.py"
    ok.write_text(
        "from giljo_mcp.models import Tenant\n"
        "def lookup(session):\n"
        "    return session.query(Tenant).filter(Tenant.is_active).all()\n"
        f"    # legacy raw sql once did FROM {_SAAS_TABLE} -- now via ORM\n",
        encoding="utf-8",
    )

    violations = mod.check_file(str(ok))

    assert violations == [], f"ORM/comment must not be flagged, got {violations}"


def test_join_and_into_keywords_match(tmp_path):
    """JOIN and INTO keyword positions are detected, not just FROM."""
    mod = _load_module()
    bad = tmp_path / "ce_join.py"
    bad.write_text(
        "def q(conn):\n"
        f'    conn.execute("INSERT INTO {_SAAS_TABLE} (id) VALUES (1)")\n'
        f'    conn.execute("SELECT 1 JOIN {_SAAS_TABLE} t ON t.id = x")\n',
        encoding="utf-8",
    )

    line_nums = [ln for ln, _ in mod.check_file(str(bad))]

    assert line_nums == [2, 3]


def test_main_exit_codes(tmp_path):
    """main() returns 1 when a file violates, 0 for a clean file."""
    mod = _load_module()
    bad = tmp_path / "bad.py"
    bad.write_text(f'x = "DELETE FROM {_SAAS_TABLE}"\n', encoding="utf-8")
    clean = tmp_path / "clean.py"
    clean.write_text("x = 1  # nothing sql here\n", encoding="utf-8")

    import sys

    saved = sys.argv
    try:
        sys.argv = ["check_saas_table_references.py", str(bad)]
        assert mod.main() == 1
        sys.argv = ["check_saas_table_references.py", str(clean)]
        assert mod.main() == 0
    finally:
        sys.argv = saved


def test_saas_dir_files_are_skipped(tmp_path):
    """A file under a saas/ directory is skipped even with a raw reference."""
    mod = _load_module()
    saas_dir = tmp_path / "saas"
    saas_dir.mkdir()
    saas_file = saas_dir / "billing.py"
    saas_file.write_text(f'x = "SELECT * FROM {_SAAS_TABLE}"\n', encoding="utf-8")

    import sys

    saved = sys.argv
    try:
        # main() applies the saas-dir skip; check_file alone would still flag it.
        sys.argv = ["check_saas_table_references.py", str(saas_file)]
        assert mod.main() == 0
    finally:
        sys.argv = saved
