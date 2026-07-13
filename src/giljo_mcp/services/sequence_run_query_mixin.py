# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""SequenceRunQueryMixin — read/query methods for sequence_runs (BE-6225).

Extracted verbatim from SequenceRunService to keep that module under the
800-line file-size guardrail. Pure move, zero behavior change: these methods
call ``self._get_session``, ``self._logger``, and ``self.tenant_manager``,
which stay on SequenceRunService and resolve via inheritance.

Every read filters ``tenant_key``. Exceptions-on-error (post-0480 — never a
success-dict).

Edition Scope: CE.
"""

from typing import Any

from sqlalchemy import select

from giljo_mcp.exceptions import (
    BaseGiljoError,
    ResourceNotFoundError,
    ValidationError,
)
from giljo_mcp.models.sequence_runs import (
    VALID_RUN_STATUSES,
    SequenceRun,
)
from giljo_mcp.services.sequence_run_live_filter import filter_runs_with_live_members
from giljo_mcp.services.sequence_run_serialization import serialize_sequence_run


class SequenceRunQueryMixin:
    """Read-side of the sequence_runs owning service (mixed into SequenceRunService)."""

    async def find_active_run_for_project(
        self,
        *,
        project_id: str,
        tenant_key: str,
    ) -> dict[str, Any] | None:
        """Return the serialized active run whose project_ids JSONB contains project_id.

        Scoped to tenant_key. Status filter: pending, running, stalled (excludes
        completed, failed, terminated, cancelled). Returns the most recently updated
        run if multiple match (shouldn't happen with cap-5 + status filter). Returns
        None if no active run contains this project (the common solo path).
        """
        try:
            active_statuses = ("pending", "running", "stalled")
            async with self._get_session(tenant_key) as session:
                stmt = (
                    select(SequenceRun)
                    .where(
                        SequenceRun.tenant_key == tenant_key,
                        SequenceRun.status.in_(active_statuses),
                        SequenceRun.project_ids.contains([project_id]),
                    )
                    .order_by(SequenceRun.updated_at.desc())
                    .limit(1)
                )
                result = await session.execute(stmt)
                run = result.scalar_one_or_none()
                if run is None:
                    return None
                return _serialize(run)
        except (BaseGiljoError, ResourceNotFoundError, ValidationError):
            raise
        except Exception as exc:
            self._logger.exception("Failed to find active sequence_run for project")
            raise BaseGiljoError(
                message=str(exc), context={"operation": "find_active_run_for_project", "project_id": project_id}
            ) from exc

    async def find_active_run_for_conductor(
        self,
        *,
        conductor_agent_id: str,
        tenant_key: str,
    ) -> dict[str, Any] | None:
        """Return the serialized active run this agent is the registered CONDUCTOR of.

        BE-6177 (C1): the close-down guard uses this to refuse a conductor's
        complete_job while its chain is still in flight. Scoped to tenant_key, active
        statuses only (pending/running/stalled). Returns None when this agent is not
        the live conductor of any active run — the common path (solo, sub_orchestrator,
        or an already-finished/terminated run) — so complete_job stays byte-identical
        for every non-conductor.
        """
        try:
            active_statuses = ("pending", "running", "stalled")
            async with self._get_session(tenant_key) as session:
                stmt = (
                    select(SequenceRun)
                    .where(
                        SequenceRun.tenant_key == tenant_key,
                        SequenceRun.status.in_(active_statuses),
                        SequenceRun.conductor_agent_id == conductor_agent_id,
                    )
                    .order_by(SequenceRun.updated_at.desc())
                    .limit(1)
                )
                result = await session.execute(stmt)
                run = result.scalar_one_or_none()
                return _serialize(run) if run is not None else None
        except (BaseGiljoError, ResourceNotFoundError, ValidationError):
            raise
        except Exception as exc:
            self._logger.exception("Failed to find active sequence_run for conductor")
            raise BaseGiljoError(
                message=str(exc),
                context={"operation": "find_active_run_for_conductor", "conductor_agent_id": conductor_agent_id},
            ) from exc

    async def list_active(
        self,
        *,
        tenant_key: str | None = None,
        statuses: tuple[str, ...] = ("pending", "running", "stalled"),
    ) -> list[dict[str, Any]]:
        """Return all runs for this tenant whose status is in ``statuses``.

        The missing read-back (BE-6165e) that makes durable election renderable
        AND lets the cockpit detect an orphaned run for the reset hatch. Tenant-
        scoped, most-recently-updated first. Invalid status values raise
        ValidationError (-> 422) rather than silently returning nothing.
        """
        try:
            effective_tenant_key = tenant_key or (
                self.tenant_manager.get_current_tenant() if self.tenant_manager else None
            )
            if not effective_tenant_key:
                raise ValidationError(
                    message="tenant_key is required", context={"operation": "list_active_sequence_runs"}
                )
            invalid = [s for s in statuses if s not in VALID_RUN_STATUSES]
            if invalid:
                raise ValidationError(
                    message=f"Invalid status filter {invalid}. Valid: {sorted(VALID_RUN_STATUSES)}",
                    context={"field": "status", "valid": sorted(VALID_RUN_STATUSES)},
                )
            async with self._get_session(effective_tenant_key) as session:
                stmt = (
                    select(SequenceRun)
                    .where(
                        SequenceRun.tenant_key == effective_tenant_key,
                        SequenceRun.status.in_(tuple(statuses)),
                    )
                    .order_by(SequenceRun.updated_at.desc())
                )
                result = await session.execute(stmt)
                runs = list(result.scalars().all())
                # BE-6200 (Unit E): drop runs whose member PROJECT ROWS are all
                # terminal so a wedged (stuck-pending) run can't hijack the
                # project-less Jobs nav. Keyed on real Project rows, not the
                # drift-prone project_statuses JSON.
                live_runs = await filter_runs_with_live_members(
                    session=session,
                    runs=runs,
                    tenant_key=effective_tenant_key,
                )
                return [_serialize(r) for r in live_runs]
        except (BaseGiljoError, ResourceNotFoundError, ValidationError):
            raise
        except Exception as exc:
            self._logger.exception("Failed to list active sequence_runs")
            raise BaseGiljoError(message=str(exc), context={"operation": "list_active_sequence_runs"}) from exc

    async def list_review_pending(
        self,
        *,
        tenant_key: str | None = None,
        limit: int = 25,
    ) -> list[dict[str, Any]]:
        """Return recent TERMINAL runs that still have a completed-but-unreviewed member.

        FE-9104 reachability fix. After a chain run goes terminal the frontend's
        ``reviewPendingRun`` safety net cannot see it on a cold refresh (nothing
        populates ``activeRun`` without a ``?run=`` URL, and ``list_active`` filters
        terminal runs out). This gives the hydrate an additive, server-filtered
        source: terminal runs (status NOT in pending/running/stalled) with at least
        one member whose ``project_statuses`` == 'completed' that is NOT yet in
        ``reviewed_project_ids``.

        Tenant-scoped, most-recently-updated first, capped at ``limit`` so the scan
        stays bounded (the just-finished run is always the freshest). Does NOT apply
        the live-member filter that ``list_active`` uses — completed member rows are
        exactly what the review surface needs to reach. Fully reviewed runs drop out
        automatically (they no longer match), preserving the release semantics.
        """
        try:
            effective_tenant_key = tenant_key or (
                self.tenant_manager.get_current_tenant() if self.tenant_manager else None
            )
            if not effective_tenant_key:
                raise ValidationError(
                    message="tenant_key is required", context={"operation": "list_review_pending_sequence_runs"}
                )
            active_statuses = ("pending", "running", "stalled")
            async with self._get_session(effective_tenant_key) as session:
                stmt = (
                    select(SequenceRun)
                    .where(
                        SequenceRun.tenant_key == effective_tenant_key,
                        SequenceRun.status.notin_(active_statuses),
                    )
                    .order_by(SequenceRun.updated_at.desc())
                    .limit(limit)
                )
                result = await session.execute(stmt)
                runs = list(result.scalars().all())
                pending = [r for r in runs if _has_unreviewed_completed_member(r)]
                return [_serialize(r) for r in pending]
        except (BaseGiljoError, ResourceNotFoundError, ValidationError):
            raise
        except Exception as exc:
            self._logger.exception("Failed to list review-pending sequence_runs")
            raise BaseGiljoError(message=str(exc), context={"operation": "list_review_pending_sequence_runs"}) from exc

    async def get(self, *, run_id: str, tenant_key: str | None = None) -> dict[str, Any]:
        """Return a single sequence run by id, scoped to tenant.

        Raises ResourceNotFoundError (-> 404) if not found or wrong tenant.
        """
        try:
            effective_tenant_key = tenant_key or (
                self.tenant_manager.get_current_tenant() if self.tenant_manager else None
            )
            if not effective_tenant_key:
                raise ValidationError(message="tenant_key is required", context={"operation": "get_sequence_run"})

            async with self._get_session(effective_tenant_key) as session:
                result = await session.execute(
                    select(SequenceRun).where(
                        SequenceRun.id == run_id,
                        SequenceRun.tenant_key == effective_tenant_key,
                    )
                )
                run = result.scalar_one_or_none()
                if run is None:
                    raise ResourceNotFoundError(
                        message="sequence_run not found",
                        context={"run_id": run_id, "tenant_key": effective_tenant_key},
                    )
                return _serialize(run)
        except (BaseGiljoError, ResourceNotFoundError, ValidationError):
            raise
        except Exception as exc:
            self._logger.exception("Failed to get sequence_run")
            raise BaseGiljoError(message=str(exc), context={"operation": "get_sequence_run"}) from exc


def _has_unreviewed_completed_member(run: SequenceRun) -> bool:
    """True when a run has ≥1 member whose chain status is 'completed' and which is
    not yet in ``reviewed_project_ids`` (FE-9104). Mirrors the frontend
    ``reviewPendingRun`` predicate so BE-surfaced runs and in-session runs agree.
    """
    statuses = run.project_statuses if isinstance(run.project_statuses, dict) else {}
    reviewed = set(run.reviewed_project_ids or [])
    return any(status == "completed" and pid not in reviewed for pid, status in statuses.items())


# Serialization aliased to the prior private name so the moved method bodies are
# byte-identical to their SequenceRunService originals (BE-6184 extraction).
_serialize = serialize_sequence_run
