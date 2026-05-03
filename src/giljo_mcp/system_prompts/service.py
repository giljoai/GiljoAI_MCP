# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
System prompt service

Provides a canonical source for system-managed prompts (currently orchestrator),
with optional administrator overrides stored in the configurations table.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from giljo_mcp.database import DatabaseManager
from giljo_mcp.models import Configuration


DEFAULT_ORCHESTRATOR_CONFIG_KEY = "system.orchestrator_prompt"
MAX_PROMPT_BYTES = 150_000  # ~150 KB safety limit


@dataclass
class PromptRecord:
    """Structured prompt payload returned to callers."""

    content: str
    is_override: bool
    updated_at: datetime | None
    updated_by: str | None


class SystemPromptService:
    """Provide default + override-aware access to system prompts."""

    def __init__(self, db_manager: DatabaseManager | None = None):
        self.db_manager = db_manager
        self._default_orchestrator_prompt: str | None = None

    async def get_orchestrator_prompt(self, *, tenant_key: str, session: AsyncSession | None = None) -> PromptRecord:
        """
        Fetch orchestrator prompt with override metadata for the given tenant.

        Falls back to the hard-coded default when no override is present or
        when database access is unavailable.
        """
        self._require_tenant_key(tenant_key)

        if session:
            override = await self._fetch_override(session, tenant_key)
        elif self.db_manager:
            async with self.db_manager.get_session_async() as db_session:
                override = await self._fetch_override(db_session, tenant_key)
        else:
            override = None

        if override:
            return PromptRecord(
                content=override["content"],
                is_override=True,
                updated_at=override.get("updated_at"),
                updated_by=override.get("updated_by"),
            )

        return PromptRecord(
            content=self._build_default_orchestrator_prompt(),
            is_override=False,
            updated_at=None,
            updated_by=None,
        )

    async def update_orchestrator_prompt(
        self,
        *,
        tenant_key: str,
        content: str,
        updated_by: str,
        session: AsyncSession | None = None,
    ) -> PromptRecord:
        """Persist an administrator override for the orchestrator prompt (per tenant)."""
        self._require_tenant_key(tenant_key)
        self._ensure_db_manager()
        sanitized_content = content.strip()
        self._validate_content(sanitized_content)

        payload = {
            "content": sanitized_content,
            "updated_by": updated_by,
            "updated_at": datetime.now(UTC),
        }

        if session:
            await self._upsert_override(session, tenant_key, payload)
            return await self.get_orchestrator_prompt(tenant_key=tenant_key, session=session)

        async with self.db_manager.get_session_async() as db_session:
            await self._upsert_override(db_session, tenant_key, payload)
            return await self.get_orchestrator_prompt(tenant_key=tenant_key, session=db_session)

    async def reset_orchestrator_prompt(self, *, tenant_key: str, session: AsyncSession | None = None) -> PromptRecord:
        """Delete any existing override for the tenant and return the default prompt."""
        self._require_tenant_key(tenant_key)
        self._ensure_db_manager()

        if session:
            await self._delete_override(session, tenant_key)
            return await self.get_orchestrator_prompt(tenant_key=tenant_key, session=session)

        async with self.db_manager.get_session_async() as db_session:
            await self._delete_override(db_session, tenant_key)
            return await self.get_orchestrator_prompt(tenant_key=tenant_key, session=db_session)

    def _ensure_db_manager(self) -> None:
        if not self.db_manager:
            raise RuntimeError("Database manager is required for this operation")

    @staticmethod
    def _require_tenant_key(tenant_key: str) -> None:
        if not tenant_key or not tenant_key.strip():
            raise ValueError("tenant_key is required")

    @staticmethod
    def _validate_content(content: str) -> None:
        if not content or not content.strip():
            raise ValueError("Prompt content cannot be empty")
        if len(content.encode("utf-8")) > MAX_PROMPT_BYTES:
            raise ValueError(f"Prompt content exceeds {MAX_PROMPT_BYTES / 1024:.0f}KB limit")

    async def _fetch_override(self, session: AsyncSession, tenant_key: str) -> dict | None:
        stmt = select(Configuration).where(
            Configuration.tenant_key == tenant_key,
            Configuration.key == DEFAULT_ORCHESTRATOR_CONFIG_KEY,
        )
        result = await session.execute(stmt)
        record = result.scalar_one_or_none()
        if not record:
            return None

        value = record.value or {}
        content = value.get("content")
        if not content:
            return None

        updated_at = value.get("updated_at")
        if isinstance(updated_at, str):
            try:
                updated_at = datetime.fromisoformat(updated_at)
            except ValueError:
                updated_at = None

        return {
            "content": content,
            "updated_by": value.get("updated_by"),
            "updated_at": updated_at,
        }

    async def _upsert_override(self, session: AsyncSession, tenant_key: str, payload: dict) -> None:
        """
        Persist the per-tenant orchestrator override.

        HO1027: Converted from select-then-insert-or-update to PostgreSQL
        ``INSERT ... ON CONFLICT (tenant_key, key) DO UPDATE`` so two
        concurrent admin saves cannot create duplicate rows or race past the
        existence check. Requires the ``uq_config_tenant_key`` unique
        constraint added in migration ``ce_0006``.
        """
        stored_value = {
            "content": payload["content"],
            "updated_by": payload.get("updated_by"),
            "updated_at": payload.get("updated_at").isoformat() if payload.get("updated_at") else None,
        }
        now = datetime.now(UTC)

        stmt = pg_insert(Configuration).values(
            tenant_key=tenant_key,
            project_id=None,
            key=DEFAULT_ORCHESTRATOR_CONFIG_KEY,
            value=stored_value,
            category="system",
            description="Administrator override for orchestrator prompt",
            updated_at=now,
        )
        stmt = stmt.on_conflict_do_update(
            constraint="uq_config_tenant_key",
            set_={
                "value": stmt.excluded.value,
                "updated_at": now,
            },
        )
        await session.execute(stmt)

    async def _delete_override(self, session: AsyncSession, tenant_key: str) -> None:
        stmt = delete(Configuration).where(
            Configuration.tenant_key == tenant_key,
            Configuration.key == DEFAULT_ORCHESTRATOR_CONFIG_KEY,
        )
        await session.execute(stmt)

    def _build_default_orchestrator_prompt(self) -> str:
        """
        Return the Layer B "user seed" content for the admin textarea.

        HO1027 (three-layer identity refactor): The default prompt the admin
        sees and edits is ONLY the user-facing seed — no harness mechanics
        (MCP Tool Usage, CHECK-IN PROTOCOL, HARNESS REMINDER OVERRIDE). The
        harness is appended at runtime by ``compose_orchestrator_identity``
        regardless of whether the tenant has saved an override. This keeps
        the textarea readable and prevents admins from accidentally deleting
        harness wiring when they save a custom prompt.
        """
        if self._default_orchestrator_prompt:
            return self._default_orchestrator_prompt

        # Import lazily to avoid circular import issues during startup.
        from giljo_mcp.template_seeder import _get_user_facing_orchestrator_seed

        self._default_orchestrator_prompt = _get_user_facing_orchestrator_seed().strip()
        return self._default_orchestrator_prompt
