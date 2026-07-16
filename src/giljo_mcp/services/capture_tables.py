# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Single source of truth for the tenant-data CAPTURE set (BE-9188).

Every capture surface — the per-tenant fidelity export/backup engine, the
Danger Zone checkpoints, and the GDPR portability export (all three route
through ``TenantExportService.export``) — derives its table set from THIS
module: every tenant-keyed ORM model discovered from ``Base.metadata`` MINUS
the explicit, rationale-per-entry :data:`EXPORT_EXCLUDE` list. Adding a new
product table therefore never requires touching backup code again; a new
tenant-keyed model is captured by construction.

This mirrors the proven schema-driven design of the DELETION side
(``saas/deletion/tenant_tables.py``, BE-3005a): audit BE-6113 found 9 tables
that had silently drifted out of a hand-maintained delete list, and audit
IMP-9186 found the exact same disease on the capture side (the Message Hub
tables — a CONFIRMED restore data-loss defect, fixed surgically in BE-9187).
The hand-maintained ``EXPORT_MODELS`` allowlist this module replaces is gone;
``tests/saas/backup/test_export_membership_drift.py`` enforces the discovery
invariant (every tenant-keyed table is discovered-included XOR excluded).

Edition isolation: this module is [CE] and imports no ``saas/`` code. Discovery
is LAZY (computed per call from the live registry), so each edition captures
exactly the models registered in its own runtime: CE discovers CE tables; the
SaaS app (which imports ``saas/`` models at startup) additionally discovers the
SaaS-only tenant tables — most of which are then deliberately excluded below.

Ordering: ``Base.metadata.sorted_tables`` is SQLAlchemy's topological sort of
the FK graph (parents first) — the INSERT order a restore needs. The purge
direction is its exact reverse (children first); both directions are asserted
by ``test_restore_order_symmetry_covers_every_fk_both_directions``. A genuine
FK cycle makes ``sorted_tables`` raise ``CircularDependencyError`` — loudly, at
export time and in CI, never silently. (Self-referential FKs — e.g.
``tasks.parent_task_id`` — are not cycles; both existing ones are nullable and
their row-level insert order is unchanged from the allowlist era.)
"""

from __future__ import annotations

from sqlalchemy import MetaData


# Stamped into every export manifest. "2.0" = discovery-era artifact (this
# module chose the table set); "1.0" = allowlist-era (EXPORT_MODELS chose it).
# The restore engine is artifact-SHAPE-driven (it keys on the tables the
# manifest actually lists), so old artifacts restore losslessly without
# version branching; the stamp records provenance for diagnostics.
ARTIFACT_SCHEMA_VERSION = "2.0"


# --------------------------------------------------------------------------- #
# The ONLY hand-maintained piece: deliberate non-capture, one rationale per
# entry. Gray areas default to INCLUDE (owner direction, 2026-07-15: capture
# all user data). An entry here is NOT captured by any surface and relies on
# the restore engine's collateral preservation (or deliberate lapse) instead.
# --------------------------------------------------------------------------- #

EXPORT_EXCLUDE: frozenset[str] = frozenset(
    {
        # -- Ephemeral tokens / sessions / codes: worthless minutes-to-hours
        #    after minting; a restore must never resurrect them (the user
        #    re-authenticates; a resurrected reset/change token is a hazard).
        "download_tokens",
        "email_change_tokens",
        "mcp_sessions",
        "oauth_authorization_codes",
        "password_reset_tokens",
        # -- Live credentials / auth infrastructure: never serialized into an
        #    artifact. Durable ones (api_keys — BE-6152) are preserved LIVE by
        #    the restore engine's collateral step instead of being captured.
        "api_keys",
        "oauth_clients",
        "oauth_refresh_tokens",
        "oauth_revoked_tokens",  # revocation ledger — restoring old state could un-revoke a token
        "org_api_keys",
        # -- Platform/operator records: billing, trials, legal evidence, and
        #    the workflow rows that drive deletion/restore themselves.
        #    Collateral-preserved on restore where applicable; they are the
        #    platform's records about the account, not the user's data.
        "account_deletion_requests",
        "organization_plans",
        "organization_terms_acceptances",  # proof-of-acceptance, retained under its own legal basis (BE-9045a)
        "restore_requests",  # the row DRIVING a restore; capturing it is self-referential
        "tenant_trials",
        # -- Derived operational telemetry (flagged gray in BE-9188 review):
        #    rolling request counters, high-volume, no user-created content,
        #    meaningless to resurrect onto a restored account. Recommendation
        #    EXCLUDE; flip to include is a one-line deletion here if overruled.
        "api_metrics",
    }
)


def _tenant_mappers() -> dict[str, type]:
    """Every tenant-keyed ORM model in the live registry, by table name."""
    import giljo_mcp.models  # noqa: F401 — registers all CE models on Base (side effect)
    from giljo_mcp.models.base import Base

    out: dict[str, type] = {}
    for mapper in Base.registry.mappers:
        table = mapper.local_table
        if table is not None and "tenant_key" in table.columns:
            out.setdefault(table.name, mapper.class_)
    return out


def capture_models() -> tuple[type, ...]:
    """The discovered capture set, in FK-correct INSERT order (parents first).

    Lazy by design — computed from whatever models the running edition has
    registered. Do not cache at module level: the SaaS app registers its
    models after CE ones, and tests register throwaway schemas.
    """
    from giljo_mcp.models.base import Base  # CE models registered by _tenant_mappers below

    mappers = _tenant_mappers()
    return tuple(
        mappers[table.name]
        for table in Base.metadata.sorted_tables  # topological; raises on a genuine FK cycle
        if table.name in mappers and table.name not in EXPORT_EXCLUDE
    )


def capture_table_names() -> list[str]:
    """Capture-set table names in FK-correct INSERT order (parents first).

    This is the fidelity manifest's ``restore_order``; the restore engine
    purges its exact reverse (children first).
    """
    return [model.__tablename__ for model in capture_models()]


def models_by_table() -> dict[str, type]:
    """Capture-set models keyed by table name (restore reload mapping)."""
    return {model.__tablename__: model for model in capture_models()}


def unaccounted_tenant_tables(metadata: MetaData | None = None) -> set[str]:
    """Reconciliation: tenant-keyed tables neither discovered nor excluded.

    Non-empty means drift — in practice a tenant-keyed table that exists in
    ``metadata`` without a registered ORM mapper (e.g. created by a migration
    only), which model-based discovery cannot see. The CI drift test asserts
    this is empty for the real ``Base.metadata``; pass a synthetic ``metadata``
    to exercise the red path without touching the global registry.
    """
    # capture_models() first: it force-registers the CE models, so a default
    # Base.metadata read below sees the full schema even if nothing imported
    # giljo_mcp.models yet in this process.
    captured = {model.__tablename__ for model in capture_models()}
    if metadata is None:
        from giljo_mcp.models.base import Base

        metadata = Base.metadata
    tenant_tables = {t.name for t in metadata.tables.values() if "tenant_key" in t.columns}
    return tenant_tables - captured - EXPORT_EXCLUDE
