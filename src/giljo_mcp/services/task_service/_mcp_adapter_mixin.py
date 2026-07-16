# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""
TaskService MCP-adapter mixin -- the agent-facing (@mcp.tool) task surface.

BE-9060 (item 3): the ~470-line MCP facade was mechanically split out of the
1552-line ``TaskService`` god-class into this mixin, mirroring the exact in-repo
precedent of the ``project_service`` package (``McpAdapterMixin``). The composed
``TaskService`` in the package ``__init__`` inherits from this mixin, so the public
import ``from giljo_mcp.services.task_service import TaskService`` and every
``task_service.create_task_for_mcp`` / ``update_task_for_mcp`` / ``list_tasks_for_mcp``
call site keep working unchanged. Behavior is unchanged -- these methods were
extracted verbatim.

Concerns owned here:
- ``create_task_for_mcp`` / ``update_task_for_mcp`` / ``list_tasks_for_mcp`` --
  the three agent-facing tool entry points (active-product resolution, TSK-tag
  forcing, summary/full projection modes).
- ``_list_tasks_for_mcp_impl`` + the ``_task_type_block`` / ``_task_to_summary_row``
  / ``_task_to_full_row`` projection helpers.

These methods reference base-class attributes/methods (``self.db_manager``,
``self.tenant_manager``, ``self._session``, ``self._logger``, ``self.log_task``,
``self.update_task``, ``self._get_session``, ``self._append_completion_notes``)
through ``self`` -- resolved across the MRO of the composed ``TaskService``.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from giljo_mcp.domain.task_status import VALID_TASK_STATUSES
from giljo_mcp.exceptions import ValidationError
from giljo_mcp.models import Task
from giljo_mcp.tenant import current_tenant
from giljo_mcp.utils.taxonomy_alias import format_taxonomy_alias


def _parse_due_date(value: Any, *, operation: str, field: str = "due_date", task_id: str = "") -> datetime:
    """TSK-9163/TSK-9177: the @mcp.tool wrappers deliver due_date (update_task)
    and due_before (list_tasks) as ISO 8601 STRINGS; unparsed they reach the
    DateTime(timezone=True) column as a str and asyncpg rejects the
    str-vs-timestamptz write/comparison as a generic internal error. Parse here —
    mirroring the REST path, where Pydantic's ``TaskUpdate.due_date: datetime``
    does the same conversion — and reject garbage as agent-actionable
    ValidationError, not a 500.
    """
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            pass
    context: dict[str, Any] = {"operation": operation}
    if task_id:
        context["task_id"] = task_id
    raise ValidationError(
        message=(
            f"Invalid {field} {value!r}. Pass an ISO 8601 date or datetime, "
            "e.g. '2026-07-15' or '2026-07-15T09:00:00+00:00'."
        ),
        context=context,
    )


class McpAdapterMixin:
    """MCP-tool task surface (create/update/list + row projections).

    Mixed into ``TaskService``; never instantiated on its own. All state comes
    from the composed base (see module docstring).
    """

    async def create_task_for_mcp(
        self,
        title: str,
        description: str,
        priority: str = "medium",
        task_type: str | None = None,
        assigned_to: str | None = None,
        tenant_key: str | None = None,
        db_manager: Any | None = None,
        websocket_manager: Any | None = None,
    ) -> dict[str, Any]:
        """Create a task via MCP tool (active product resolution + TSK tag).

        BE-6049c: tasks are now **TSK-only**. The ``task_type`` parameter is
        accepted for backward compatibility but **ignored** — every new task is
        force-assigned the reserved ``TSK`` tag (decoupled from the project
        taxonomy) and renders ``TSK-nnnn`` on the global serial line. The TSK
        row is ensured lazily + race-safe for the calling tenant.
        """
        effective_tenant_key = tenant_key or self.tenant_manager.get_current_tenant()
        effective_db = db_manager or self.db_manager

        from giljo_mcp.services.product_service import ProductService
        from giljo_mcp.services.taxonomy_service import TaxonomyService

        product_service = ProductService(
            db_manager=effective_db,
            tenant_key=effective_tenant_key,
            websocket_manager=websocket_manager,
            test_session=self._session,
        )
        active_product = await product_service.get_active_product()

        if not active_product:
            raise ValidationError(
                "No active product set. Please activate a product first.",
                context={"tenant_key": effective_tenant_key, "operation": "create_task"},
            )

        product_id = active_product.id

        # BE-6049c: force the reserved TSK tag. ``ensure_reserved_task_type`` is
        # race-safe (INSERT ... ON CONFLICT DO NOTHING) so concurrent
        # first-task-creates for a tenant that predates TSK seeding cannot
        # collide. ``task_type`` is intentionally unused.
        taxonomy = TaxonomyService(db_manager=effective_db, session=self._session)
        reserved_type = await taxonomy.ensure_reserved_task_type(effective_tenant_key)
        task_type_id = reserved_type.id
        resolved_type_label = reserved_type.abbreviation

        # BE-5065/BE-6049b: shared global task+project series counter. Tasks are
        # always typed now (TSK), so every task draws a serial. ``log_task``
        # performs the lock + assign + insert inside one session so the FOR
        # UPDATE + advisory lock are held until the row is committed.
        assigned_series: list[int | None] = [None]
        task_id = await self.log_task(
            content=title,
            title=title,
            description=description,
            task_type_id=task_type_id,
            priority=priority,
            product_id=product_id,
            tenant_key=effective_tenant_key,
            assign_shared_series=True,
            _assigned_series_out=assigned_series,
        )

        self._logger.info(
            "Created task %s for tenant %s in product %s",
            task_id,
            effective_tenant_key,
            product_id,
        )

        if websocket_manager:
            try:
                await websocket_manager.broadcast_to_tenant(
                    tenant_key=effective_tenant_key,
                    event_type="task:created",
                    data={"task_id": task_id, "title": title, "product_id": product_id},
                )
            except (RuntimeError, ValueError, OSError) as e:
                self._logger.warning(f"Failed to broadcast task:created event: {e}")

        # BE-5065: surface taxonomy_alias (TSK-nnnn) to the MCP caller. Built
        # from the reserved abbreviation + the series_number assigned inside
        # log_task so we don't need a DB roundtrip (also keeps mock-friendly
        # tests happy when log_task is stubbed).
        taxonomy_alias = ""
        if assigned_series[0] is not None:
            taxonomy_alias = format_taxonomy_alias(resolved_type_label, assigned_series[0])

        return {
            "success": True,
            "task_id": task_id,
            "title": title,
            "priority": priority,
            "task_type": resolved_type_label,
            "taxonomy_alias": taxonomy_alias,
            "product_id": product_id,
            "message": f"Task '{title}' created successfully",
        }

    async def update_task_for_mcp(
        self,
        task_id: str,
        tenant_key: str | None = None,
        title: str | None = None,
        description: str | None = None,
        status: str | None = None,
        priority: str | None = None,
        task_type: str | None = None,
        due_date: Any = None,
        project_id: str | None = None,
        estimated_effort: float | None = None,
        actual_effort: float | None = None,
        hidden: bool | None = None,
        completion_notes: str | None = None,
    ) -> dict[str, Any]:
        """Update a task via the MCP surface. Phase C; mirrors update_project.

        Only fields actually supplied (non-None) are written; the underlying
        ``update_task`` enforces the field allowlist (post-0962 write
        discipline). BE-6049c: tasks are TSK-only and the tag is IMMUTABLE —
        ``task_type`` is accepted for signature compatibility but ignored (it is
        not in the update allowlist), so passing it is a harmless no-op.

        BE-6225a: ``completion_notes`` folds in the retired ``complete_task``
        tool. When the task is being completed (``status == "completed"``) the
        note is appended to the description as a timestamped audit-trail entry
        (shared ``_append_completion_notes`` format, identical to the REST PATCH
        and the old complete_task path). A note without ``status="completed"``
        is a no-op — the audit entry only makes sense on completion.
        """
        effective_tenant_key = tenant_key or self.tenant_manager.get_current_tenant()
        if not effective_tenant_key:
            raise ValidationError(
                message="tenant_key is required",
                context={"operation": "update_task_for_mcp", "task_id": task_id},
            )

        if status is not None and status not in VALID_TASK_STATUSES:
            valid_status_values = sorted(s.value for s in VALID_TASK_STATUSES)
            raise ValidationError(
                message=f"Unknown task status '{status}'. Valid statuses: {valid_status_values}",
                context={
                    "operation": "update_task_for_mcp",
                    "task_id": task_id,
                    "valid_statuses": valid_status_values,
                },
            )

        update_kwargs: dict[str, Any] = {}
        if title is not None:
            update_kwargs["title"] = title
        if description is not None:
            update_kwargs["description"] = description
        if status is not None:
            update_kwargs["status"] = status
        if priority is not None:
            update_kwargs["priority"] = priority
        if due_date is not None:
            update_kwargs["due_date"] = _parse_due_date(due_date, operation="update_task_for_mcp", task_id=task_id)
        if project_id is not None:
            update_kwargs["project_id"] = project_id
        if estimated_effort is not None:
            update_kwargs["estimated_effort"] = estimated_effort
        if actual_effort is not None:
            update_kwargs["actual_effort"] = actual_effort
        if hidden is not None:
            if not isinstance(hidden, bool):
                raise ValidationError(
                    message="hidden must be a boolean",
                    context={"operation": "update_task_for_mcp", "task_id": task_id},
                )
            update_kwargs["hidden"] = hidden

        # BE-6049c: task_type is intentionally NOT resolved/written — the TSK tag
        # is immutable (task_type_id is not in _ALLOWED_TASK_UPDATE_FIELDS), so a
        # supplied task_type is a no-op rather than a hard error.

        # BE-6225a: completion_notes only append on completion. A note alone (no
        # status="completed") is nothing to do, mirroring the no-fields case.
        will_append_notes = bool(completion_notes) and status == "completed"

        if not update_kwargs and not will_append_notes:
            return {
                "task_id": task_id,
                "updated_fields": [],
                "message": "No fields supplied; nothing to update.",
            }

        # Route through update_task; it owns the allowlist and timestamp logic.
        # update_task pulls tenant from tenant_manager — set it explicitly so
        # tenant_key parameter wins on the MCP-tool path.
        # Capture the token and reset() to the exact prior value (BE6004C-1):
        # the old set(previous) restore skipped restoring when previous was None,
        # leaving effective_tenant_key on the context — a cross-tenant leak.
        updated_fields: list[str] = []
        if update_kwargs:
            tenant_token = None
            if self.tenant_manager:
                tenant_token = self.tenant_manager.set_current_tenant(effective_tenant_key)
            try:
                result = await self.update_task(task_id, **update_kwargs)
            finally:
                if tenant_token is not None:
                    current_tenant.reset(tenant_token)
            updated_fields = list(result.updated_fields)

        # BE-6225a: append the audit-trail note AFTER the status write commits, so
        # the completed task carries the note exactly as the retired complete_task
        # tool did. Shares the single _append_completion_notes format with the
        # REST PATCH path (tenant-explicit; no new column).
        response: dict[str, Any] = {
            "task_id": task_id,
            "updated_fields": updated_fields,
            "message": f"Task {task_id} updated: {sorted(updated_fields)}",
        }
        if will_append_notes:
            await self._append_completion_notes(task_id, effective_tenant_key, completion_notes)
            response["completion_notes"] = completion_notes
        return response

    async def list_tasks_for_mcp(
        self,
        tenant_key: str | None = None,
        mode: str = "summary",
        status: str | None = None,
        priority: str | None = None,
        task_type: str | None = None,
        due_before: Any = None,
        summary_only: bool | None = None,
        memory_limit: int | None = None,
        hidden: bool | None = None,
    ) -> dict[str, Any]:
        """List tasks for the active product with summary/full projection modes.

        Phase D of agent-parity. Two modes only:

        - ``summary``: id, title, status, priority, task_type, due_date,
          created_at, taxonomy_alias, series_number, subseries, hidden,
          embedded task_type block — keeps the response under ~80 lines for a
          typical ~50-task corpus.
        - ``full``: the full projection of Task columns (see
          ``_task_to_full_row``) plus an embedded task_type block.
          ``memory_limit`` truncates description if set.

        Filters: status, priority, task_type (abbreviation), due_before, hidden.
        BE-6077: every query is scoped to BOTH tenant_key AND the active
        product (Task.product_id is NOT NULL), mirroring list_projects_for_mcp.
        Cross-tenant and cross-product tasks are never visible. Raises
        ValidationError when no active product is set.

        FE-5046: The 'hidden' field is per-row UI declutter and does NOT
        affect default visibility -- agents see hidden and non-hidden alike.
        Pass hidden=true|false to filter explicitly when needed (rare).
        """
        effective_tenant_key = tenant_key or self.tenant_manager.get_current_tenant()
        if not effective_tenant_key:
            raise ValidationError(
                message="tenant_key is required",
                context={"operation": "list_tasks_for_mcp"},
            )

        # BE-6077: scope to the active product, mirroring list_projects_for_mcp.
        # Tasks are NOT NULL product_id (models/tasks.py); without this an agent
        # "on the active product" saw the whole tenant's task corpus instead of
        # the active product's, diverging from both the UI and list_projects.
        from giljo_mcp.services.product_service import ProductService

        product_service = ProductService(
            db_manager=self.db_manager,
            tenant_key=effective_tenant_key,
            websocket_manager=self._websocket_manager,
            test_session=self._session,
        )
        active_product = await product_service.get_active_product(eager_load=False)
        if not active_product:
            raise ValidationError(
                message="No active product set. Please activate a product first.",
                context={"tenant_key": effective_tenant_key, "operation": "list_tasks_for_mcp"},
            )

        if summary_only is True:
            mode = "summary"
        elif summary_only is False:
            mode = "full"
        if mode not in {"summary", "full"}:
            raise ValidationError(
                message=f"Unknown mode '{mode}'. Valid modes: summary, full",
                context={"operation": "list_tasks_for_mcp", "mode": mode},
            )

        # TSK-9177: the @mcp.tool wrapper delivers due_before as an ISO string;
        # parse at the boundary (same class as TSK-9163) so the impl compares
        # datetime-vs-timestamptz instead of str-vs-timestamptz.
        if due_before is not None:
            due_before = _parse_due_date(due_before, operation="list_tasks_for_mcp", field="due_before")

        task_type_id: str | None = None
        if task_type:
            from giljo_mcp.services.taxonomy_service import TaxonomyService

            taxonomy = TaxonomyService(db_manager=self.db_manager, session=self._session)
            resolved = await taxonomy.validate(task_type.strip(), effective_tenant_key)
            task_type_id = resolved.id

        async with self._get_session(effective_tenant_key) as session:
            tasks = await self._list_tasks_for_mcp_impl(
                session,
                effective_tenant_key,
                product_id=active_product.id,
                status=status,
                priority=priority,
                task_type_id=task_type_id,
                due_before=due_before,
                hidden=hidden,
            )

        if mode == "summary":
            rows = [self._task_to_summary_row(t) for t in tasks]
        else:
            rows = [self._task_to_full_row(t, memory_limit=memory_limit) for t in tasks]

        return {
            "tasks": rows,
            "count": len(rows),
            "mode": mode,
            "tenant_key": effective_tenant_key,
            "product_id": active_product.id,
        }

    async def _list_tasks_for_mcp_impl(
        self,
        session: AsyncSession,
        tenant_key: str,
        *,
        product_id: str,
        status: str | None,
        priority: str | None,
        task_type_id: str | None,
        due_before: Any,
        hidden: bool | None = None,
    ) -> list[Task]:
        stmt = (
            select(Task)
            .options(selectinload(Task.task_type))
            .where(Task.tenant_key == tenant_key)
            .where(Task.product_id == product_id)
            .where(Task.deleted_at.is_(None))  # BE-6130b: exclude trashed tasks
            .order_by(Task.created_at.desc())
        )
        if status:
            stmt = stmt.where(Task.status == status)
        if priority:
            stmt = stmt.where(Task.priority == priority)
        if task_type_id:
            stmt = stmt.where(Task.task_type_id == task_type_id)
        if due_before is not None:
            stmt = stmt.where(Task.due_date < due_before)
        if hidden is not None:
            stmt = stmt.where(Task.hidden == hidden)

        result = await session.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    def _task_type_block(task: Task) -> dict[str, Any] | None:
        if not task.task_type:
            return None
        return {
            "id": task.task_type.id,
            "abbreviation": task.task_type.abbreviation,
            "label": task.task_type.label,
            "color": task.task_type.color,
        }

    @classmethod
    def _task_to_summary_row(cls, task: Task) -> dict[str, Any]:
        # FE-5046: summary now mirrors Project parity -- taxonomy_alias,
        # series_number, subseries, embedded task_type block, hidden.
        return {
            "task_id": str(task.id),
            "title": task.title,
            "status": task.status,
            "priority": task.priority,
            "task_type": cls._task_type_block(task),
            "taxonomy_alias": task.taxonomy_alias or "",
            "series_number": task.series_number,
            "subseries": task.subseries,
            "hidden": bool(task.hidden),
            "due_date": task.due_date.isoformat() if task.due_date else None,
            "created_at": task.created_at.isoformat() if task.created_at else None,
        }

    @classmethod
    def _task_to_full_row(cls, task: Task, *, memory_limit: int | None) -> dict[str, Any]:
        description = task.description or ""
        if memory_limit and len(description) > memory_limit:
            description = description[:memory_limit] + "..."
        return {
            "task_id": str(task.id),
            "title": task.title,
            "description": description,
            "status": task.status,
            "priority": task.priority,
            "task_type": cls._task_type_block(task),
            "taxonomy_alias": task.taxonomy_alias or "",
            "series_number": task.series_number,
            "subseries": task.subseries,
            "hidden": bool(task.hidden),
            "task_type_id": task.task_type_id,
            "product_id": task.product_id,
            "project_id": task.project_id,
            "parent_task_id": task.parent_task_id,
            "estimated_effort": task.estimated_effort,
            "actual_effort": task.actual_effort,
            "due_date": task.due_date.isoformat() if task.due_date else None,
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "created_at": task.created_at.isoformat() if task.created_at else None,
        }
