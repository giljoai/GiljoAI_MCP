# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.

"""
Tests for Alembic dual-chain migration configuration (SAAS-002).

Verifies that migrations/env.py correctly computes version_locations
based on GILJO_MODE and the existence of the saas_versions/ directory.
Also validates the SaaS baseline migration file structure.

These tests do NOT require a database connection -- all DB-dependent
code is mocked.
"""

from __future__ import annotations

import ast
import importlib
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).parent.parent.parent
MIGRATIONS_DIR = PROJECT_ROOT / "migrations"
SAAS_VERSIONS_DIR = MIGRATIONS_DIR / "saas_versions"
CE_VERSIONS_DIR = MIGRATIONS_DIR / "versions"
SAAS_BASELINE_FILE = SAAS_VERSIONS_DIR / "saas_baseline_v1.py"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _compute_version_locations(giljo_mode: str | None, saas_dir_exists: bool) -> list[str]:
    """Replicate env.py's version_locations logic for isolated testing.

    We cannot safely reload env.py because it triggers Alembic context
    operations and database connections at module level. Instead, we
    replicate the exact logic from lines 61-68 of env.py and verify
    its behavior against all mode/directory combinations.
    """
    mode = (giljo_mode or "ce").lower()
    migrations_dir = MIGRATIONS_DIR

    version_locations = [str(migrations_dir / "versions")]

    saas_versions_dir = migrations_dir / "saas_versions"
    if saas_dir_exists and mode != "ce":
        version_locations.append(str(saas_versions_dir))

    return version_locations


def _reload_env_module(monkeypatch, mode_value: str | None = None):
    """Reload migrations.env with controlled GILJO_MODE, fully mocked DB.

    This patches all database-dependent operations so env.py can be
    imported without a live PostgreSQL connection.
    """
    if mode_value is None:
        monkeypatch.delenv("GILJO_MODE", raising=False)
    else:
        monkeypatch.setenv("GILJO_MODE", mode_value)

    # Ensure POSTGRES_PASSWORD is set so env.py doesn't raise ValueError
    monkeypatch.setenv("POSTGRES_PASSWORD", "test_password")

    # Remove cached module so reimport picks up new env values
    sys.modules.pop("migrations.env", None)

    # Mock the Alembic context operations that require a DB
    mock_context = MagicMock()
    mock_context.config = MagicMock()
    mock_context.config.config_file_name = None
    mock_context.config.get_main_option.return_value = "postgresql://test:test@localhost/test"
    mock_context.config.get_section.return_value = {}
    mock_context.is_offline_mode.return_value = True

    with patch.dict("sys.modules", {"alembic.context": mock_context}):
        # We also need to patch 'alembic.context' usage within env.py
        # Since env.py does `from alembic import context`, we patch the
        # alembic module's context attribute
        mock_alembic = MagicMock()
        mock_alembic.context = mock_context

        with patch.dict("sys.modules", {"alembic": mock_alembic}):
            mod = importlib.import_module("migrations.env")
            return mod


# ---------------------------------------------------------------------------
# 1. env.py dual-chain logic -- version_locations computation
# ---------------------------------------------------------------------------


class TestDualChainVersionLocations:
    """Verify version_locations is computed correctly for each GILJO_MODE."""

    def test_ce_mode_includes_only_ce_versions(self):
        """When GILJO_MODE is 'ce', only migrations/versions/ is included."""
        locations = _compute_version_locations("ce", saas_dir_exists=True)
        assert len(locations) == 1
        assert str(CE_VERSIONS_DIR) in locations[0]
        assert "saas_versions" not in locations[0]

    def test_unset_mode_defaults_to_ce_only(self):
        """When GILJO_MODE is not set (None), defaults to CE-only."""
        locations = _compute_version_locations(None, saas_dir_exists=True)
        assert len(locations) == 1
        assert str(CE_VERSIONS_DIR) in locations[0]

    def test_saas_mode_includes_both_chains(self):
        """When GILJO_MODE is 'saas' and dir exists, both chains are included."""
        locations = _compute_version_locations("saas", saas_dir_exists=True)
        assert len(locations) == 2
        assert str(CE_VERSIONS_DIR) in locations[0]
        assert "saas_versions" in locations[1]

    def test_demo_mode_includes_both_chains(self):
        """When GILJO_MODE is 'demo' and dir exists, both chains are included."""
        locations = _compute_version_locations("demo", saas_dir_exists=True)
        assert len(locations) == 2
        assert str(CE_VERSIONS_DIR) in locations[0]
        assert "saas_versions" in locations[1]

    def test_saas_mode_without_dir_includes_only_ce(self):
        """When GILJO_MODE is 'saas' but saas_versions/ missing, CE-only."""
        locations = _compute_version_locations("saas", saas_dir_exists=False)
        assert len(locations) == 1
        assert "saas_versions" not in locations[0]

    def test_case_insensitive_saas_mode(self):
        """GILJO_MODE='SAAS' (uppercase) includes both chains."""
        locations = _compute_version_locations("SAAS", saas_dir_exists=True)
        assert len(locations) == 2

    def test_case_insensitive_ce_mode(self):
        """GILJO_MODE='CE' (uppercase) includes only CE chain."""
        locations = _compute_version_locations("CE", saas_dir_exists=True)
        assert len(locations) == 1

    def test_case_insensitive_demo_mode(self):
        """GILJO_MODE='Demo' (mixed case) includes both chains."""
        locations = _compute_version_locations("Demo", saas_dir_exists=True)
        assert len(locations) == 2

    def test_ce_versions_always_first(self):
        """CE versions directory is always the first entry."""
        for mode in ("ce", "saas", "demo"):
            locations = _compute_version_locations(mode, saas_dir_exists=True)
            assert "versions" in locations[0]
            assert "saas_versions" not in locations[0]


# ---------------------------------------------------------------------------
# 2. Deletion Test -- saas_versions/ directory missing
# ---------------------------------------------------------------------------


class TestDeletionTestMigrations:
    """Verify env.py works when saas_versions/ does not exist (CE-only).

    This is the migration-specific Deletion Test -- critical for edition
    isolation. If all SaaS directories are deleted, CE must still work.
    """

    def test_missing_saas_dir_produces_single_location(self):
        """When saas_versions/ doesn't exist, only CE path is returned."""
        locations = _compute_version_locations("saas", saas_dir_exists=False)
        assert len(locations) == 1
        assert "saas_versions" not in locations[0]

    def test_missing_saas_dir_in_ce_mode_still_works(self):
        """CE mode with missing saas_versions/ is the normal CE state."""
        locations = _compute_version_locations("ce", saas_dir_exists=False)
        assert len(locations) == 1

    def test_missing_saas_dir_in_demo_mode_degrades_gracefully(self):
        """Demo mode with missing saas_versions/ falls back to CE-only."""
        locations = _compute_version_locations("demo", saas_dir_exists=False)
        assert len(locations) == 1
        assert "saas_versions" not in locations[0]

    def test_env_py_logic_matches_is_dir_check(self):
        """Verify the actual env.py uses Path.is_dir() for the check.

        This ensures the Deletion Test works by filesystem check,
        not by catching ImportError or other less robust methods.
        """
        source = MIGRATIONS_DIR / "env.py"
        content = source.read_text()
        # The implementation should check is_dir() on saas_versions
        assert "saas_versions_dir.is_dir()" in content
        # And the condition should also check giljo_mode != "ce"
        assert 'giljo_mode != "ce"' in content


# ---------------------------------------------------------------------------
# 3. SaaS baseline migration file validation
# ---------------------------------------------------------------------------


class TestSaasBaselineMigration:
    """Validate the SaaS baseline migration file structure."""

    def test_baseline_file_exists(self):
        """The SaaS baseline migration file must exist."""
        assert SAAS_BASELINE_FILE.exists(), f"SaaS baseline migration not found at {SAAS_BASELINE_FILE}"

    def test_baseline_is_valid_python(self):
        """The baseline migration must be syntactically valid Python."""
        source = SAAS_BASELINE_FILE.read_text()
        # ast.parse will raise SyntaxError if invalid
        ast.parse(source)

    def test_baseline_has_revision_id(self):
        """The baseline must define a revision identifier."""
        source = SAAS_BASELINE_FILE.read_text()
        tree = ast.parse(source)
        assignments = {
            node.targets[0].id: node.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)
        }
        assert "revision" in assignments
        # Verify it's a string constant
        rev_node = assignments["revision"]
        assert isinstance(rev_node, ast.Constant)
        assert isinstance(rev_node.value, str)
        assert len(rev_node.value) > 0

    def test_baseline_has_saas_branch_label(self):
        """The baseline must have branch_labels containing 'saas'."""
        source = SAAS_BASELINE_FILE.read_text()
        tree = ast.parse(source)
        assignments = {
            node.targets[0].id: node.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)
        }
        assert "branch_labels" in assignments
        bl_node = assignments["branch_labels"]
        # branch_labels should be a tuple containing "saas"
        assert isinstance(bl_node, ast.Tuple)
        label_values = [elt.value for elt in bl_node.elts if isinstance(elt, ast.Constant)]
        assert "saas" in label_values

    def test_baseline_has_no_down_revision(self):
        """The baseline is a root migration -- down_revision must be None."""
        source = SAAS_BASELINE_FILE.read_text()
        tree = ast.parse(source)
        assignments = {
            node.targets[0].id: node.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)
        }
        assert "down_revision" in assignments
        dr_node = assignments["down_revision"]
        assert isinstance(dr_node, ast.Constant)
        assert dr_node.value is None

    def test_baseline_has_upgrade_function(self):
        """The baseline must define an upgrade() function."""
        source = SAAS_BASELINE_FILE.read_text()
        tree = ast.parse(source)
        func_names = [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
        assert "upgrade" in func_names

    def test_baseline_has_downgrade_function(self):
        """The baseline must define a downgrade() function."""
        source = SAAS_BASELINE_FILE.read_text()
        tree = ast.parse(source)
        func_names = [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
        assert "downgrade" in func_names

    def test_baseline_lives_in_saas_versions_directory(self):
        """The baseline must be inside migrations/saas_versions/, not versions/."""
        assert SAAS_BASELINE_FILE.parent.name == "saas_versions"
        assert SAAS_BASELINE_FILE.parent.parent.name == "migrations"


# ---------------------------------------------------------------------------
# 4. alembic.ini configuration validation
# ---------------------------------------------------------------------------


class TestAlembicIniConfiguration:
    """Verify alembic.ini has correct version_locations setting."""

    def test_version_locations_points_to_ce_versions(self):
        """alembic.ini version_locations must include migrations/versions."""
        ini_path = PROJECT_ROOT / "alembic.ini"
        content = ini_path.read_text()
        # Find the version_locations line (not commented out)
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("version_locations") and "=" in stripped:
                value = stripped.split("=", 1)[1].strip()
                assert "migrations/versions" in value
                return
        pytest.fail("version_locations not found in alembic.ini")

    def test_version_path_separator_is_os(self):
        """alembic.ini must use 'os' as the version_path_separator."""
        ini_path = PROJECT_ROOT / "alembic.ini"
        content = ini_path.read_text()
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("version_path_separator") and "=" in stripped and not stripped.startswith("#"):
                value = stripped.split("=", 1)[1].split("#")[0].strip()
                assert value == "os"
                return
        pytest.fail("version_path_separator not found in alembic.ini")
