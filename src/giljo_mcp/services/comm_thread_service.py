# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""CommThreadService — the owning service for the Agent Message Hub (BE-6054b).

Sits on the BE-6054a CommThreadRepository data foundation and provides the
behaviour the 8 MCP tools delegate to: create/join threads, post to a thread
(SIDE-EFFECT-FREE — never routes through orchestration send_message), the baton
queries (get_my_turn / pass_baton), list/search, and read-only history.

Session handling mirrors TaxonomyService: a transactional test session
(``session=``) is used verbatim, otherwise a request-scoped
``get_session_async`` (which commits on clean exit) is opened. Every operation
runs inside ``tenant_session_context`` and filters ``tenant_key``.

Edition Scope: CE.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from giljo_mcp.database import DatabaseManager, tenant_session_context
from giljo_mcp.domain.soft_delete import RECOVER_WINDOW_DAYS, recover_window_expired
from giljo_mcp.exceptions import ResourceNotFoundError, ValidationError
from giljo_mcp.models.comm import (
    BOUND_THREAD_MARKER_SUBJECT,
    CHT_TAXONOMY_ABBR,
    LOOP_DIRECTIVE_MESSAGE_TYPE,
    TERMINAL_THREAD_STATUSES,
    VALID_PARTICIPANT_TYPES,
    CommThread,
)
from giljo_mcp.models.tasks import Message
from giljo_mcp.repositories.agent_operations_repository import AgentOperationsRepository
from giljo_mcp.repositories.comm_thread_repository import CommThreadRepository
from giljo_mcp.repositories.user_repository import UserRepository
from giljo_mcp.tenant import TenantManager
from giljo_mcp.utils.identity import validate_from_agent
from giljo_mcp.utils.taxonomy_alias import format_taxonomy_alias


logger = logging.getLogger(__name__)

# Loose status set the tool surface accepts on a status-setting post. The column
# itself tolerates freeform labels (BE-6054a), but the tool boundary constrains
# agent input to the known lifecycle to keep the board legible.
_SETTABLE_STATUSES = ("open", "active", "resolved", "closed")

# Length cap for an agent-supplied author identity (FE-6122). Mirrors MCP_ID_MAX
# at the tool boundary; enforced here too so the owning service validates the
# input itself ("no unvalidated agent input to DB"), not only the MCP wrapper.
_FROM_AGENT_MAX = 64

# FE-6140: bounds for the auto-check-in interval (minutes) carried on a
# loop_directive post. Validated here at the owning service so the column never
# receives unbounded agent/operator input ("no unvalidated agent input to DB").
# 1 min floor; 24h ceiling — a wider net than the FE slider (5..60) but a hard
# sanity bound for the MCP path.
_LOOP_INTERVAL_MIN_MINUTES = 1
_LOOP_INTERVAL_MAX_MINUTES = 1440

# BE-6226: bounds for the get_thread_history incremental-fetch ``tail`` (last N).
# Validated at the owning service so the repo never receives unbounded agent input.
_TAIL_MIN = 1
_TAIL_MAX = 500


class CommThreadService:
    """Service surface for comm_threads / comm_participants + thread messaging."""

    def __init__(
        self,
        db_manager: DatabaseManager,
        tenant_manager: TenantManager,
        session: AsyncSession | None = None,
    ) -> None:
        self._db_manager = db_manager
        self._tenant_manager = tenant_manager
        self._session = session
        self._repo = CommThreadRepository()
        self._user_repo = UserRepository()
        self._agent_ops = AgentOperationsRepository()

    # ------------------------------------------------------------------
    # Session + tenant plumbing
    # ------------------------------------------------------------------

    def _resolve_tenant(self, tenant_key: str | None) -> str:
        tk = tenant_key or self._tenant_manager.get_current_tenant()
        if not tk:
            raise ValidationError("tenant_key is required", context={"operation": "comm_thread"})
        return tk

    @asynccontextmanager
    async def _scoped_session(self, tenant_key: str):
        if self._session is not None:
            with tenant_session_context(self._session, tenant_key):
                yield self._session
        else:
            async with self._db_manager.get_session_async(tenant_key=tenant_key) as session:
                with tenant_session_context(session, tenant_key):
                    yield session

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    @staticmethod
    def _thread_dict(thread: CommThread) -> dict[str, Any]:
        return {
            "thread_id": thread.id,
            "chat_id": thread.taxonomy_alias,
            "subject": thread.subject,
            "status": thread.status,
            "next_action_owner": thread.next_action_owner,
            "severity": thread.severity,
            "product_id": thread.product_id,
            "project_id": thread.project_id,
            "created_at": thread.created_at.isoformat() if thread.created_at else None,
        }

    @staticmethod
    def _message_dict(msg: Message, recipient_state: dict[str, list[str]] | None = None) -> dict[str, Any]:
        out = {
            "message_id": msg.id,
            "thread_id": msg.thread_id,
            "from_agent_id": msg.from_agent_id,
            "from_display_name": msg.from_display_name,
            "content": msg.content,
            "message_type": msg.message_type,
            "priority": msg.priority,
            "status": msg.status,
            "requires_action": msg.requires_action,
            "loop_interval_minutes": msg.loop_interval_minutes,
            "created_at": msg.created_at.isoformat() if msg.created_at else None,
        }
        # FE-9012c (D3): additive MESSAGE-relative junction state, only when the caller
        # (the Hub REST path) asks for it. Absent on the default read (byte-identical).
        if recipient_state is not None:
            recipients = recipient_state.get("recipients", [])
            acted = set(recipient_state.get("acked_by", [])) | set(recipient_state.get("completed_by", []))
            out["recipients"] = recipients
            out["acked_by"] = recipient_state.get("acked_by", [])
            out["completed_by"] = recipient_state.get("completed_by", [])
            out["pending_for"] = [r for r in recipients if r not in acted]
        return out

    async def _require_thread(self, session: AsyncSession, tenant_key: str, thread_id: str) -> CommThread:
        thread = await self._repo.get_by_id(session, tenant_key, thread_id)
        if thread is None:
            raise ResourceNotFoundError(
                message="Thread not found or access denied",
                context={"operation": "comm_thread", "thread_id": thread_id},
            )
        return thread

    # ------------------------------------------------------------------
    # Tool operations
    # ------------------------------------------------------------------

    async def create_thread(
        self,
        *,
        subject: str | None = None,
        severity: str | None = None,
        product_id: str | None = None,
        project_id: str | None = None,
        creator_id: str | None = None,
        creator_type: str = "agent",
        creator_display_name: str | None = None,
        tenant_key: str | None = None,
    ) -> dict[str, Any]:
        """Create a thread (mints the CHT-#### serial). Optionally registers the
        creator as the first participant + hands them the baton."""
        tk = self._resolve_tenant(tenant_key)
        async with self._scoped_session(tk) as session:
            thread = await self._repo.create_thread(
                session,
                tk,
                subject=subject,
                severity=severity,
                product_id=product_id,
                project_id=project_id,
                next_action_owner=creator_id,
            )
            if creator_id:
                ctype = creator_type if creator_type in VALID_PARTICIPANT_TYPES else "agent"
                await self._repo.add_participant(
                    session,
                    tk,
                    thread.id,
                    participant_id=creator_id,
                    participant_type=ctype,
                    display_name=creator_display_name,
                    role="creator",
                )
            return self._thread_dict(thread)

    async def resolve_or_create_bound_thread(self, *, project_id: str, tenant_key: str | None = None) -> dict[str, Any]:
        """Resolve (or create) THE project's bound thread — the single source of
        truth shared by the D9 deprecation shims and the D1(a) 360-pane, using the
        same precedence the ce_0072 fold does (see the repo method). Tenant-scoped."""
        tk = self._resolve_tenant(tenant_key)
        async with self._scoped_session(tk) as session:
            thread = await self._repo.resolve_or_create_bound_thread(
                session, tk, project_id, marker=BOUND_THREAD_MARKER_SUBJECT
            )
            return self._thread_dict(thread)

    async def join_thread(
        self,
        *,
        thread_id: str,
        participant_id: str,
        participant_type: str = "agent",
        display_name: str | None = None,
        role: str | None = None,
        tenant_key: str | None = None,
    ) -> dict[str, Any]:
        """Declare/claim an identity on a thread (collision-safe)."""
        tk = self._resolve_tenant(tenant_key)
        if not participant_id:
            raise ValidationError("participant_id is required", context={"operation": "comm_thread.join"})
        async with self._scoped_session(tk) as session:
            await self._require_thread(session, tk, thread_id)
            participant = await self._repo.add_participant(
                session,
                tk,
                thread_id,
                participant_id=participant_id,
                participant_type=participant_type,
                display_name=display_name,
                role=role,
            )
            return {
                "participant_id": participant.participant_id,
                "thread_id": thread_id,
                "participant_type": participant.participant_type,
            }

    async def post_to_thread(
        self,
        *,
        thread_id: str,
        content: str,
        from_agent: str | None = None,
        to_participant: str | None = None,
        message_type: str = "direct",
        priority: str = "normal",
        requires_action: bool = False,
        set_status: str | None = None,
        loop_directive: bool = False,
        loop_interval_minutes: int | None = None,
        user_id: str | None = None,
        tenant_key: str | None = None,
    ) -> dict[str, Any]:
        """Post a message to a thread (broadcast to all participants, or direct to
        one). SIDE-EFFECT-FREE: persists Message + message_recipients only — never
        the orchestration send_message side-effects. Accepts a NULL project_id.

        BE-6054c: ``loop_directive=True`` marks the message so addressed agents get
        the "loop/sleep until this thread is resolved/closed" directive in their
        next mission. The loop terminates when the thread reaches a terminal status.

        FE-6140: ``loop_interval_minutes`` is the operator-chosen auto-check-in
        cadence. It is persisted on the loop_directive message and surfaced on the
        get_my_turn / get_thread_history poll responses (the harness-neutral inject)
        so a running agent re-reads it and self-schedules its wake. Ignored unless
        ``loop_directive`` is True (a non-directive message never carries a cadence)."""
        tk = self._resolve_tenant(tenant_key)
        if not content or not content.strip():
            raise ValidationError("content is required", context={"operation": "comm_thread.post"})
        if set_status is not None and set_status not in _SETTABLE_STATUSES:
            raise ValidationError(
                f"set_status must be one of {_SETTABLE_STATUSES}, got '{set_status}'.",
                context={"operation": "comm_thread.post", "set_status": set_status},
            )

        # FE-6140: validate the cadence before it reaches the DB. Only a
        # loop_directive post carries one — drop a stray interval on a normal post
        # rather than persisting a meaningless cadence.
        interval_to_persist: int | None = None
        if loop_directive and loop_interval_minutes is not None:
            if not isinstance(loop_interval_minutes, int) or isinstance(loop_interval_minutes, bool):
                raise ValidationError(
                    "loop_interval_minutes must be an integer number of minutes.",
                    context={"operation": "comm_thread.post"},
                )
            if not (_LOOP_INTERVAL_MIN_MINUTES <= loop_interval_minutes <= _LOOP_INTERVAL_MAX_MINUTES):
                raise ValidationError(
                    f"loop_interval_minutes must be between {_LOOP_INTERVAL_MIN_MINUTES} and "
                    f"{_LOOP_INTERVAL_MAX_MINUTES}.",
                    context={"operation": "comm_thread.post", "loop_interval_minutes": loop_interval_minutes},
                )
            interval_to_persist = loop_interval_minutes

        # (A) Author attribution (FE-6122 / BE-9037). An agent self-declares its
        # identity (its role/lane id) via ``from_agent`` (WINS when present); a USER
        # post falls back to the authenticated principal. The value feeds the
        # FUNCTIONAL identity field (from_agent_id: recipient self-exclusion, baton/
        # get_my_turn matching, read cursors), so it is hardened at the write boundary
        # (validate_from_agent: type-check + length-cap + control/zero-width strip +
        # reject-empty -> clean 422). The Hub keys on the SLUG — from_agent_id is never
        # rewritten to a UUID (breaks self-exclusion/baton); unknown-but-sane slugs OK.
        # RESIDUAL LIMITATION (NOT fixed here — see PR): identity is self-declared; a
        # caller can still claim any slug because the session carries only tenant_key +
        # user_id. Impersonation-proofing needs auth-bound agent identity, a separate
        # effort. This guard stops garbage/corruption, not role impersonation.
        from_agent = validate_from_agent(from_agent, max_len=_FROM_AGENT_MAX)

        async with self._scoped_session(tk) as session:
            thread = await self._require_thread(session, tk, thread_id)

            # attribution_warning (TSK-0008): surface, never silently stamp. An
            # omitted from_agent falls back to the principal; the backend cannot tell
            # an agent that forgot it from a genuine user post, so it attributes AND
            # advises. None on the agent path.
            attribution_warning: str | None = None
            if from_agent:
                from_agent_id = from_agent
                # Resolve the STORED display name from the poster's own participant
                # row (set at join_thread) so every reader sees the friendly role; a
                # poster with no row (or no display_name) falls back to the slug —
                # never a crash, never worse than pre-fix.
                participant = await self._repo.get_participant(session, tk, thread_id, from_agent)
                from_display_name = (participant.display_name if participant else None) or from_agent
            elif user_id:
                user = await self._user_repo.get_user_by_id(session, user_id, tk)
                from_agent_id = user_id
                from_display_name = user.display_name if user else "user"
                attribution_warning = (
                    "from_agent omitted; attributed to the authenticated principal. An AGENT post "
                    "must pass from_agent (its role/lane id) or it is mis-attributed (TSK-0008)."
                )
            else:
                from_agent_id = "orchestrator"
                from_display_name = "orchestrator"
                attribution_warning = "from_agent omitted and no principal resolved; attributed to 'orchestrator'."

            # Recipients: a direct target, else broadcast to all OTHER participants.
            if to_participant:
                recipient_ids = [to_participant]
            else:
                # BE-6141: a broadcast on a PROJECT-ANCHORED thread auto-enrolls the
                # project's active agents as participants first, so the broadcast
                # reaches agents that never manually join_thread'd. Standalone
                # threads (NULL project_id) are unaffected — they still broadcast to
                # exactly the participants who joined.
                if thread.project_id:
                    await self._auto_enroll_project_roster(session, tk, thread_id, thread.project_id)
                participants = await self._repo.get_participants(session, tk, thread_id)
                recipient_ids = [p.participant_id for p in participants if p.participant_id != from_agent_id]

            # A loop-directive post is marked with the reserved message_type so the
            # mission composer can detect it; otherwise broadcast vs direct as usual.
            if loop_directive:
                resolved_message_type = LOOP_DIRECTIVE_MESSAGE_TYPE
            elif to_participant:
                resolved_message_type = message_type
            else:
                resolved_message_type = "broadcast"

            message = await self._repo.persist_thread_message(
                session,
                tenant_key=tk,
                thread_id=thread_id,
                project_id=thread.project_id,  # may be NULL (standalone thread)
                content=content,
                from_agent_id=from_agent_id,
                from_display_name=from_display_name,
                message_type=resolved_message_type,
                priority=priority,
                requires_action=requires_action,
                recipient_ids=recipient_ids,
                loop_interval_minutes=interval_to_persist,
            )
            if set_status is not None:
                await self._repo.set_status(session, tk, thread_id, set_status)
            return {
                "message_id": message.id,
                "thread_id": thread_id,
                "recipients": recipient_ids,
                "from_agent_id": from_agent_id,
                "from_display_name": from_display_name,
                "attribution_warning": attribution_warning,
                "loop_directive_armed": loop_directive,
                "loop_interval_minutes": interval_to_persist,
            }

    async def _auto_enroll_project_roster(
        self, session: AsyncSession, tenant_key: str, thread_id: str, project_id: str
    ) -> None:
        """Enroll a project's ACTIVE agents as thread participants (BE-6141).

        Reuses the AgentExecution roster (the owning AgentOperationsRepository)
        and the collision-safe ``add_participant`` join, so a broadcast reaches
        agents that never manually joined. Idempotent: re-enrolling an existing
        participant is a no-op (``ON CONFLICT DO NOTHING``), so no duplicate rows
        accrue across repeated posts. Scoped to the project's active agents —
        does not over-enroll terminal (complete/closed/decommissioned) agents.
        """
        roster = await self._agent_ops.get_active_agent_ids_for_project(session, tenant_key, project_id)
        for agent_id, display_name in roster:
            await self._repo.add_participant(
                session,
                tenant_key,
                thread_id,
                participant_id=agent_id,
                participant_type="agent",
                display_name=display_name,
                role="auto-enrolled",
            )

    async def has_active_loop_directive(self, *, agent_id: str, tenant_key: str | None = None) -> bool:
        """Whether an agent currently has a live loop directive (BE-6054c).

        Used by the mission composer to decide whether to inject the loop/sleep
        directive. True iff a loop_directive message targets this agent on a
        non-terminal thread."""
        tk = self._resolve_tenant(tenant_key)
        async with self._scoped_session(tk) as session:
            return await self._repo.has_active_loop_directive(session, tk, agent_id)

    async def get_my_turn(self, *, agent_id: str, tenant_key: str | None = None) -> dict[str, Any]:
        """The baton query: threads where next_action_owner == agent_id (or 'all').

        FE-6140: also surfaces ``loop_directives`` — the active auto-check-in
        requests for EVERY thread this agent participates in (not only the threads
        where it holds the baton). This is the harness-neutral inject: a running
        agent polling get_my_turn reads its cadence(s) and self-schedules a wake.
        Each entry is ``{thread_id, chat_id, interval_minutes}`` (interval may be
        None when a directive was armed without an explicit cadence)."""
        tk = self._resolve_tenant(tenant_key)
        if not agent_id:
            raise ValidationError("agent_id is required", context={"operation": "comm_thread.get_my_turn"})
        async with self._scoped_session(tk) as session:
            mine = await self._repo.list_threads(session, tk, next_action_owner=agent_id)
            broadcast = await self._repo.list_threads(session, tk, next_action_owner="all")
            threads = {t.id: t for t in [*mine, *broadcast]}
            directives = await self._repo.get_active_loop_directives_for_agent(session, tk, agent_id)
            return {
                "agent_id": agent_id,
                "count": len(threads),
                "threads": [self._thread_dict(t) for t in threads.values()],
                "loop_directives": [
                    {
                        "thread_id": d["thread_id"],
                        "chat_id": format_taxonomy_alias(CHT_TAXONOMY_ABBR, d["serial"]),
                        "interval_minutes": d["interval_minutes"],
                    }
                    for d in directives
                ],
            }

    async def pass_baton(self, *, thread_id: str, to: str, tenant_key: str | None = None) -> dict[str, Any]:
        """Hand the baton: set next_action_owner to an agent_id / user_id / 'all' / 'none'."""
        tk = self._resolve_tenant(tenant_key)
        if not to:
            raise ValidationError("to is required", context={"operation": "comm_thread.pass_baton"})
        owner = None if to == "none" else to
        async with self._scoped_session(tk) as session:
            thread = await self._repo.set_next_action_owner(session, tk, thread_id, owner)
            if thread is None:
                raise ResourceNotFoundError(
                    message="Thread not found or access denied",
                    context={"operation": "comm_thread.pass_baton", "thread_id": thread_id},
                )
            return {"thread_id": thread_id, "next_action_owner": thread.next_action_owner}

    async def delete_thread(self, *, thread_id: str, tenant_key: str | None = None) -> dict[str, Any]:
        """Soft-delete a thread (Message Hub trash action).

        Stamps ``deleted_at`` so the thread drops out of every read; message
        history + participants stay intact. Raises ResourceNotFoundError when the
        thread does not exist (or is already deleted) for the tenant."""
        tk = self._resolve_tenant(tenant_key)
        async with self._scoped_session(tk) as session:
            thread = await self._require_thread(session, tk, thread_id)
            chat_id = thread.taxonomy_alias
            deleted = await self._repo.soft_delete(session, tk, thread_id)
            if not deleted:  # pragma: no cover - _require_thread already guarantees presence
                raise ResourceNotFoundError(
                    message="Thread not found or access denied",
                    context={"operation": "comm_thread.delete", "thread_id": thread_id},
                )
            return {"thread_id": thread_id, "chat_id": chat_id, "deleted": True}

    async def restore_thread(self, *, thread_id: str, tenant_key: str | None = None) -> dict[str, Any]:
        """Restore a soft-deleted thread (Message Hub recover action).

        Clears ``deleted_at`` so the thread (and its intact message history +
        participants) surfaces again in every read. Raises ResourceNotFoundError
        when no soft-deleted thread matches the id for the tenant."""
        tk = self._resolve_tenant(tenant_key)
        async with self._scoped_session(tk) as session:
            trashed = await self._repo.get_deleted_by_id(session, tk, thread_id)
            if trashed is None:
                raise ResourceNotFoundError(
                    message="Deleted thread not found or access denied",
                    context={"operation": "comm_thread.restore", "thread_id": thread_id},
                )
            if recover_window_expired(trashed.deleted_at):
                raise ValidationError(
                    f"This thread was deleted more than {RECOVER_WINDOW_DAYS} days ago and can no longer be recovered.",
                    context={"operation": "comm_thread.restore", "thread_id": thread_id},
                )
            thread = await self._repo.restore(session, tk, thread_id)
            return self._thread_dict(thread)

    async def list_deleted_threads(
        self,
        *,
        product_id: str | None = None,
        project_id: str | None = None,
        tenant_key: str | None = None,
    ) -> dict[str, Any]:
        """List soft-deleted threads (the recover dialog's source). Includes
        ``deleted_at`` so the UI can show how long ago each was trashed."""
        tk = self._resolve_tenant(tenant_key)
        async with self._scoped_session(tk) as session:
            threads = await self._repo.list_deleted(session, tk, product_id=product_id, project_id=project_id)
            return {
                "count": len(threads),
                "threads": [
                    {
                        **self._thread_dict(t),
                        "deleted_at": t.deleted_at.isoformat() if t.deleted_at else None,
                    }
                    for t in threads
                ],
            }

    async def purge_expired_deleted_threads(self, *, tenant_key: str | None = None) -> int:
        """Hard-delete trashed threads past the recovery window (TSK-6132 reaper).

        Walks this tenant's soft-deleted threads and permanently removes those
        whose ``deleted_at`` is past ``RECOVER_WINDOW_DAYS`` (the same boundary
        ``restore_thread`` refuses to recover past). Cascade is DB-level. Returns
        the count purged; tenant-isolated and idempotent (re-running finds none).
        """
        tk = self._resolve_tenant(tenant_key)
        purged = 0
        async with self._scoped_session(tk) as session:
            for thread in await self._repo.list_deleted(session, tk):
                if not recover_window_expired(thread.deleted_at):
                    continue
                try:
                    if await self._repo.hard_delete(session, tk, thread.id):
                        purged += 1
                except Exception:
                    logger.exception("Reaper failed to purge thread %s", thread.id)
        return purged

    async def list_threads(
        self,
        *,
        status: str | None = None,
        owner: str | None = None,
        product_id: str | None = None,
        project_id: str | None = None,
        limit: int | None = None,
        before_id: str | None = None,
        tenant_key: str | None = None,
    ) -> dict[str, Any]:
        """List threads with optional filters.

        BE-6131b: ``limit`` + ``before_id`` keyset pagination added to bound the
        Hub thread list (mirrors the BE-6071 bound on the ``/messages`` endpoint).
        """
        tk = self._resolve_tenant(tenant_key)
        async with self._scoped_session(tk) as session:
            threads = await self._repo.list_threads(
                session,
                tk,
                status=status,
                next_action_owner=owner,
                product_id=product_id,
                project_id=project_id,
                limit=limit,
                before_id=before_id,
            )
            return {"count": len(threads), "threads": [self._thread_dict(t) for t in threads]}

    async def get_thread_history(
        self,
        *,
        thread_id: str,
        after_message_id: str | None = None,
        since: str | None = None,
        tail: int | None = None,
        as_participant: str | None = None,
        unread_only: bool = False,
        mark_read: bool = False,
        directed_only: bool = False,
        action_required_only: bool = False,
        include_recipient_state: bool = False,
        tenant_key: str | None = None,
    ) -> dict[str, Any]:
        """Read a thread's message timeline (READ-ONLY unless ``mark_read=True``).

        FE-6140: also surfaces ``loop_directive`` — ``{active, interval_minutes}``
        for the thread. ``active`` is True iff the latest loop_directive message
        exists AND the thread is non-terminal (a resolved/closed thread silences the
        directive, the same gate that makes the loop provably terminate). This is the
        harness-neutral inject a running agent re-reads on each poll.

        BE-6226 — incremental fetch (backward-compatible). With NONE of the optional
        params the response is byte-identical to the pre-BE-6226 full-timeline read.
        A chain conductor passes a marker to pull only NEW messages each poll instead
        of re-fetching the whole thread:
          - ``after_message_id`` — only messages after that message id (the poll cursor).
          - ``since`` — ISO-8601 timestamp; only messages created strictly after it.
          - ``tail`` — only the last N messages (1..500), applied after any marker.
        ``after_message_id`` and ``since`` are mutually exclusive (both name a start
        marker); ``count`` reflects the rows actually returned.

        BE-9012a (D6/D4) — server-persistent per-(thread, participant) cursor, so a
        unified-Hub read is O(N) drain-equivalent, not an O(N^2) re-read (INF-6201 §1).
        ``as_participant`` (the reader's participant_id) is REQUIRED for the four below:
          - ``unread_only`` — only posts after the reader's stored ``last_read_at``.
            No cursor / never joined => the whole timeline (honest "nothing read yet").
          - ``mark_read`` — ack the returned posts in ``message_acknowledgments``
            (idempotent) and, on a clean forward drain (no narrowing/truncation),
            advance the cursor to the newest returned post. Refuses with a structured
            ``NOT_A_PARTICIPANT`` rejection if the reader never joined. ONLY write path.
          - ``directed_only`` / ``action_required_only`` — posts delivered to the reader
            (DM or received broadcast) / ``requires_action=True`` posts.
        Every query is ``tenant_key``-scoped; the cursor is per-(thread, participant) —
        ADR-009 Teams-ready (never per-user account-level state).

        FE-9012c (D3/D4) — ``include_recipient_state`` (default False, so the MCP agent
        poll path stays byte-identical + does zero extra queries) surfaces per-post
        MESSAGE-relative junction state for the Hub's in-thread waiting/read/sent filter:
        each message dict gains ``recipients`` / ``acked_by`` / ``completed_by`` /
        ``pending_for`` (recipients minus those who acked-or-completed). One batched
        tenant-scoped fetch across the returned message ids — not per-message."""
        if after_message_id and since:
            raise ValidationError(
                "Pass at most one of 'after_message_id' or 'since' (both name a start marker).",
                context={"operation": "comm_thread.history", "thread_id": thread_id},
            )

        # BE-9012a: cursor params need the reader's identity (never inferred) -> clean 422.
        if (unread_only or mark_read or directed_only or action_required_only) and not as_participant:
            raise ValidationError(
                "as_participant is required when using unread_only / mark_read / "
                "directed_only / action_required_only (the per-participant cursor "
                "must know who is reading).",
                context={"operation": "comm_thread.history", "thread_id": thread_id},
            )

        since_dt: datetime | None = None
        if since:
            try:
                since_dt = datetime.fromisoformat(since)
            except (TypeError, ValueError) as exc:
                raise ValidationError(
                    "'since' must be an ISO-8601 timestamp (e.g. a message's created_at).",
                    context={"operation": "comm_thread.history", "since": since},
                ) from exc

        if tail is not None:
            if not isinstance(tail, int) or isinstance(tail, bool):
                raise ValidationError(
                    "'tail' must be an integer number of messages.",
                    context={"operation": "comm_thread.history"},
                )
            if not (_TAIL_MIN <= tail <= _TAIL_MAX):
                raise ValidationError(
                    f"'tail' must be between {_TAIL_MIN} and {_TAIL_MAX}.",
                    context={"operation": "comm_thread.history", "tail": tail},
                )

        tk = self._resolve_tenant(tenant_key)
        async with self._scoped_session(tk) as session:
            thread = await self._require_thread(session, tk, thread_id)

            participant = None  # BE-9012a: the reader's per-(thread, participant) cursor row.
            if as_participant:
                participant = await self._repo.get_participant(session, tk, thread_id, as_participant)

            if mark_read and participant is None:
                # BE-6081 carve-out: a deliberate domain rejection (not an error). A
                # silent no-op would let the caller believe it acked when it did not —
                # the closeout-dance failure this chain exists to kill.
                return {
                    "success": False,
                    "error": "NOT_A_PARTICIPANT",
                    "thread_id": thread_id,
                    "as_participant": as_participant,
                    "hint": "join_thread this thread first (re-joining is a safe no-op), then retry mark_read.",
                }

            # unread keys on the stored timestamp (reaper-safe); no cursor => whole timeline.
            unread_after = participant.last_read_at if (unread_only and participant is not None) else None
            directed_to = as_participant if directed_only else None

            messages = await self._repo.get_thread_messages(
                session,
                tk,
                thread_id,
                after_message_id=after_message_id or None,
                since=since_dt,
                tail=tail,
                unread_after=unread_after,
                directed_to=directed_to,
                action_required_only=action_required_only,
            )

            marked_read = 0
            if mark_read and participant is not None and messages:
                # D4: per-recipient acted-on state for every post seen (idempotent).
                await self._repo.ack_messages_for_participant(
                    session, tk, agent_id=as_participant, message_ids=[m.id for m in messages]
                )
                marked_read = len(messages)
                # Advance the watermark ONLY on a clean forward drain: narrowing
                # (directed/action) or truncation (tail/marker) means the returned set
                # is not the contiguous run up to newest, so advancing would skip unread
                # posts it excluded. The acks above still record what was seen.
                is_full_drain = not (directed_only or action_required_only or tail or after_message_id or since)
                newest = messages[-1]  # oldest-first => last is the newest returned
                if (
                    is_full_drain
                    and newest.created_at is not None
                    and (participant.last_read_at is None or newest.created_at > participant.last_read_at)
                ):
                    participant.last_read_message_id = newest.id
                    participant.last_read_at = newest.created_at
                    await session.flush()

            # FE-9012c (D3): one batched junction fetch, merged per message. Gated so
            # the default read (MCP agent poll) is byte-identical and query-identical.
            recipient_state: dict[str, dict[str, list[str]]] = {}
            if include_recipient_state and messages:
                recipient_state = await self._repo.get_recipient_state_for_messages(
                    session, tk, message_ids=[m.id for m in messages]
                )

            directive = await self._repo.get_latest_loop_directive(session, tk, thread_id)
            active = directive is not None and not self.is_terminal_status(thread.status)
            response = {
                "thread": self._thread_dict(thread),
                "count": len(messages),
                "messages": [
                    self._message_dict(m, recipient_state.get(m.id) if include_recipient_state else None)
                    for m in messages
                ],
                "loop_directive": {
                    "active": active,
                    "interval_minutes": directive.loop_interval_minutes if (directive and active) else None,
                },
            }
            # Additive only when mark_read requested (legacy read stays byte-identical).
            if mark_read:
                response["marked_read"] = marked_read
            return response

    async def search_threads(self, *, query: str, limit: int = 50, tenant_key: str | None = None) -> dict[str, Any]:
        """Find threads by subject, CHT serial, message content, or participant."""
        tk = self._resolve_tenant(tenant_key)
        if not query or not query.strip():
            raise ValidationError("query is required", context={"operation": "comm_thread.search"})
        async with self._scoped_session(tk) as session:
            threads = await self._repo.search_threads(session, tk, query, limit=limit)
            return {"query": query, "count": len(threads), "threads": [self._thread_dict(t) for t in threads]}

    async def list_participants(self, *, thread_id: str, tenant_key: str | None = None) -> dict[str, Any]:
        """Return the participant directory for a thread (BE-6054ef REST adapter)."""
        tk = self._resolve_tenant(tenant_key)
        async with self._scoped_session(tk) as session:
            await self._require_thread(session, tk, thread_id)
            parts = await self._repo.get_participants(session, tk, thread_id)
            return {
                "thread_id": thread_id,
                "count": len(parts),
                "participants": [
                    {
                        "participant_id": p.participant_id,
                        "participant_type": p.participant_type,
                        "display_name": p.display_name,
                        "role": p.role,
                        "joined_at": p.joined_at.isoformat() if p.joined_at else None,
                    }
                    for p in parts
                ],
            }

    @staticmethod
    def is_terminal_status(status: str | None) -> bool:
        """Whether a thread status ends the loop/sleep coordination (BE-6054c uses this)."""
        return status in TERMINAL_THREAD_STATUSES
