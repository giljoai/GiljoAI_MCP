# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Retire the agent bus: fold legacy bus rows onto project-bound threads + fix
the project-bound-thread lifecycle FK (BE-9012d, D8 + D10).

Revision ID: ce_0072_bus_retirement_fold_and_fk
Revises: ce_0071_agent_todo_item_kind
Create Date: 2026-07-03

Edition Scope: Both (comm_threads / messages are CE tables; the fold + FK are the
same on CE and SaaS). Final step (d) of the "Hub absorbs the bus" chain. Two
concerns, one migration, two clearly separated hunks.

D8 -- fold legacy bus rows onto project-bound Hub threads
---------------------------------------------------------
Legacy bus messages are ``messages`` rows with ``project_id`` set and
``thread_id`` NULL (Hub thread posts carry ``thread_id``). Retiring the bus means
every message must live on a thread, so this backfills each project's orphan bus
rows onto ONE resolved project-bound thread.

Resolution PRECEDENCE -- identical to the runtime resolver the D9 shims + the
D1(a) 360-pane use, so the migration, the shims and the pane all agree on "THE
project's bound thread". Among a project's LIVE (deleted_at IS NULL) project-bound
threads:
  1. exactly one exists -> use it (any subject);
  2. none               -> create one with the "(project comms)" marker subject;
  3. several            -> the marker-subject one if present, else the OLDEST.
An existing ORGANIC bound thread (e.g. a chain coordination hub) is the project's
comms home -- folding the bus history INTO it is the "history stays whole" goal,
not a reason to mint a duplicate (which would recreate the very multiplicity the
D1(a) pane exists to kill).

Idempotent: the fold is driven by ``thread_id IS NULL`` bus rows, so a re-run
(the CE installer reruns migrations on every boot) finds nothing to fold and
creates nothing new -- rerun-safety comes from the ``thread_id IS NULL`` guard,
NOT from the marker. Tenant-scoped: the fold groups by ``(tenant_key,
project_id)`` and every created thread carries its project's ``tenant_key``
(ADR-009: tenant_key is the isolation boundary; a future Team = one tenant, many
users -- this is org-correct after the flip). ``op.execute`` / raw DML backfill
is allowed (migrations bypass the service layer by design). Forward-only: the
fold is non-destructive (a message keeps every field, it only gains a
``thread_id``) and cannot be cleanly un-folded once merged into an organic
thread, so ``downgrade`` does not reverse it; re-upgrade is a clean no-op via the
``thread_id IS NULL`` guard.

D10 -- project-bound-thread lifecycle FK (SET NULL -> CASCADE)
-------------------------------------------------------------
``comm_threads.project_id`` shipped as ``ondelete=SET NULL`` (ce_0053). On a
genuine project purge (``nuclear_delete_project`` / the 10-day
``purge_expired_deleted_projects``) that ORPHANS the project's bound thread into
the town square. The delete chain is already CASCADE end to end EXCEPT this one
FK (``messages.thread_id`` CASCADE, the message junctions CASCADE,
``comm_participants`` CASCADE), so flipping it to CASCADE completes the chain:
purging a project takes its bound thread + posts + junctions + participants with
it, consistent with the purge already deleting the project's messages/tasks/jobs.
SET NULL is wrong under any policy; RESTRICT would block the existing purge paths
(the BE-6238 user_approvals RestrictViolation class). Soft-delete (the common,
reversible case) never fires the FK, so a recoverable project keeps its bound
thread for restore.

``comm_threads`` is NOT in ``baseline_v37_unified`` (it is created by the
post-baseline incremental ce_0053), so there is no baseline shape to mirror -- a
fresh install reaches CASCADE by running ce_0053 (SET NULL) then this migration,
exactly as an upgraded install does. No baseline edit for parity.

Idempotent (the FK alter is constraint-name-agnostic and skipped when the FK is
already CASCADE) and reversible (downgrade restores SET NULL).
"""

import uuid

import sqlalchemy as sa
from alembic import op


revision = "ce_0072_bus_retirement_fold_and_fk"
down_revision = "ce_0071_agent_todo_item_kind"
branch_labels = None
depends_on = None


# Marker subject stamped on a bound thread CREATED by the fold when a project has
# no existing bound thread. Kept in sync with the runtime resolver's marker (D9
# shims add ``giljo_mcp.models.comm.BOUND_THREAD_MARKER_SUBJECT``); hardcoded here
# because a migration is a historical snapshot and must not follow a later change
# to the app constant.
_BOUND_THREAD_MARKER = "(project comms)"


def _project_bound_fk(conn) -> tuple[str | None, str | None]:
    """Return ``(constraint_name, confdeltype)`` for the comm_threads.project_id FK.

    ``confdeltype``: 'c' = CASCADE, 'n' = SET NULL, 'a'/' ' = NO ACTION, 'r' =
    RESTRICT. Constraint-name-agnostic so the alter works regardless of how
    Postgres auto-named the original FK.
    """
    row = conn.execute(
        sa.text(
            "SELECT con.conname, con.confdeltype "
            "FROM pg_constraint con "
            "JOIN pg_class rel ON rel.oid = con.conrelid "
            "JOIN pg_attribute att ON att.attrelid = con.conrelid "
            "  AND att.attnum = ANY(con.conkey) "
            "WHERE rel.relname = 'comm_threads' "
            "  AND con.contype = 'f' "
            "  AND att.attname = 'project_id'"
        )
    ).fetchone()
    if row is None:
        return None, None
    return row[0], row[1]


def _fold_bus_rows(conn) -> None:
    """D8: fold each project's orphan bus rows onto ONE resolved bound thread."""
    # Every (tenant_key, project_id) that still has orphan bus rows (thread_id
    # NULL, project_id set). On re-run this set is empty -> whole fold is a no-op.
    pairs = conn.execute(
        sa.text(
            "SELECT DISTINCT tenant_key, project_id FROM messages WHERE thread_id IS NULL AND project_id IS NOT NULL"
        )
    ).fetchall()

    for tenant_key, project_id in pairs:
        # Resolve THE bound thread by precedence: marker-subject first (CASE 0),
        # then oldest, among LIVE project-bound threads. The CASE (not a bare
        # ``subject = marker``) avoids the DESC-NULLS-FIRST trap for NULL subjects.
        resolved = conn.execute(
            sa.text(
                "SELECT id FROM comm_threads "
                "WHERE tenant_key = :tk AND project_id = :pid AND deleted_at IS NULL "
                "ORDER BY CASE WHEN subject = :marker THEN 0 ELSE 1 END ASC, created_at ASC "
                "LIMIT 1"
            ),
            {"tk": tenant_key, "pid": project_id, "marker": _BOUND_THREAD_MARKER},
        ).scalar()

        if resolved is None:
            # None exists -> create one with the marker subject. Mint the CHT
            # serial as max(serial)+1 for the tenant (counting soft-deleted rows,
            # per the model's never-reuse rule). The same-transaction insert makes
            # the next iteration's MAX see this row, so serials stay unique even
            # when several of a tenant's projects each need a fresh thread.
            serial = conn.execute(
                sa.text("SELECT COALESCE(MAX(serial), 0) + 1 FROM comm_threads WHERE tenant_key = :tk"),
                {"tk": tenant_key},
            ).scalar()
            product_id = conn.execute(
                sa.text("SELECT product_id FROM projects WHERE id = :pid"),
                {"pid": project_id},
            ).scalar()
            resolved = str(uuid.uuid4())
            conn.execute(
                sa.text(
                    "INSERT INTO comm_threads "
                    "(id, tenant_key, serial, subject, status, product_id, project_id, created_at, updated_at) "
                    "VALUES (:id, :tk, :serial, :subject, 'open', :product_id, :pid, now(), now())"
                ),
                {
                    "id": resolved,
                    "tk": tenant_key,
                    "serial": serial,
                    "subject": _BOUND_THREAD_MARKER,
                    "product_id": product_id,
                    "pid": project_id,
                },
            )

        # Fold this project's orphan bus rows onto the resolved thread. The
        # ``thread_id IS NULL`` guard makes this self-skipping on re-run.
        conn.execute(
            sa.text(
                "UPDATE messages SET thread_id = :tid "
                "WHERE tenant_key = :tk AND project_id = :pid AND thread_id IS NULL"
            ),
            {"tid": resolved, "tk": tenant_key, "pid": project_id},
        )


def upgrade() -> None:
    conn = op.get_bind()

    # --- D8: fold legacy bus rows onto project-bound threads --------------
    _fold_bus_rows(conn)

    # --- D10: comm_threads.project_id  SET NULL -> CASCADE ----------------
    conname, deltype = _project_bound_fk(conn)
    if conname is not None and deltype != "c":  # 'c' = CASCADE already -> skip
        op.execute(f'ALTER TABLE comm_threads DROP CONSTRAINT "{conname}"')
        op.execute(
            'ALTER TABLE comm_threads ADD CONSTRAINT "comm_threads_project_id_fkey" '
            "FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE"
        )


def downgrade() -> None:
    # Reverse D10 only. D8's data fold is forward-only (non-destructive and not
    # cleanly reversible once folded into an organic thread); re-upgrade is a
    # clean no-op via the ``thread_id IS NULL`` guard.
    conn = op.get_bind()
    conname, deltype = _project_bound_fk(conn)
    if conname is not None and deltype != "n":  # 'n' = SET NULL already -> skip
        op.execute(f'ALTER TABLE comm_threads DROP CONSTRAINT "{conname}"')
        op.execute(
            'ALTER TABLE comm_threads ADD CONSTRAINT "comm_threads_project_id_fkey" '
            "FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE SET NULL"
        )
