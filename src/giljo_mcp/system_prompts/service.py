"""
System prompt service

Provides a canonical source for system-managed prompts (currently orchestrator),
with optional administrator overrides stored in the configurations table.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import DatabaseManager
from ..models import Configuration

DEFAULT_ORCHESTRATOR_CONFIG_KEY = "system.orchestrator_prompt"
MAX_PROMPT_BYTES = 150_000  # ~150 KB safety limit


@dataclass
class PromptRecord:
    """Structured prompt payload returned to callers."""

    content: str
    is_override: bool
    updated_at: Optional[datetime]
    updated_by: Optional[str]


class SystemPromptService:
    """Provide default + override-aware access to system prompts."""

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db_manager = db_manager
        self._default_orchestrator_prompt: Optional[str] = None

    async def get_orchestrator_prompt(self, session: Optional[AsyncSession] = None) -> PromptRecord:
        """
        Fetch orchestrator prompt with override metadata.

        Falls back to the hard-coded default when no override is present or
        when database access is unavailable.
        """
        if session:
            override = await self._fetch_override(session)
        elif self.db_manager:
            async with self.db_manager.get_session_async() as db_session:
                override = await self._fetch_override(db_session)
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
        self, *, content: str, updated_by: str, session: Optional[AsyncSession] = None
    ) -> PromptRecord:
        """Persist an administrator override for the orchestrator prompt."""
        self._ensure_db_manager()
        sanitized_content = content.strip()
        self._validate_content(sanitized_content)

        payload = {
            "content": sanitized_content,
            "updated_by": updated_by,
            "updated_at": datetime.now(timezone.utc),
        }

        if session:
            await self._upsert_override(session, payload)
            return await self.get_orchestrator_prompt(session=session)

        async with self.db_manager.get_session_async() as db_session:
            await self._upsert_override(db_session, payload)
            return await self.get_orchestrator_prompt(session=db_session)

    async def reset_orchestrator_prompt(self, session: Optional[AsyncSession] = None) -> PromptRecord:
        """Delete any existing override and return the default prompt."""
        self._ensure_db_manager()

        if session:
            await self._delete_override(session)
            return await self.get_orchestrator_prompt(session=session)

        async with self.db_manager.get_session_async() as db_session:
            await self._delete_override(db_session)
            return await self.get_orchestrator_prompt(session=db_session)

    def _ensure_db_manager(self) -> None:
        if not self.db_manager:
            raise RuntimeError("Database manager is required for this operation")

    @staticmethod
    def _validate_content(content: str) -> None:
        if not content or not content.strip():
            raise ValueError("Prompt content cannot be empty")
        if len(content.encode("utf-8")) > MAX_PROMPT_BYTES:
            raise ValueError(f"Prompt content exceeds {MAX_PROMPT_BYTES / 1024:.0f}KB limit")

    async def _fetch_override(self, session: AsyncSession) -> Optional[dict]:
        stmt = select(Configuration).where(
            Configuration.tenant_key.is_(None), Configuration.key == DEFAULT_ORCHESTRATOR_CONFIG_KEY
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

    async def _upsert_override(self, session: AsyncSession, payload: dict) -> None:
        stmt = select(Configuration).where(
            Configuration.tenant_key.is_(None), Configuration.key == DEFAULT_ORCHESTRATOR_CONFIG_KEY
        )
        result = await session.execute(stmt)
        record = result.scalar_one_or_none()

        stored_value = {
            "content": payload["content"],
            "updated_by": payload.get("updated_by"),
            "updated_at": payload.get("updated_at").isoformat() if payload.get("updated_at") else None,
        }

        if record:
            record.value = stored_value
            record.updated_at = datetime.now(timezone.utc)
        else:
            session.add(
                Configuration(
                    tenant_key=None,
                    project_id=None,
                    key=DEFAULT_ORCHESTRATOR_CONFIG_KEY,
                    value=stored_value,
                    category="system",
                    description="Administrator override for orchestrator prompt",
                )
            )

    async def _delete_override(self, session: AsyncSession) -> None:
        stmt = delete(Configuration).where(
            Configuration.tenant_key.is_(None), Configuration.key == DEFAULT_ORCHESTRATOR_CONFIG_KEY
        )
        await session.execute(stmt)

    def _build_default_orchestrator_prompt(self) -> str:
        if self._default_orchestrator_prompt:
            return self._default_orchestrator_prompt

        # Import lazily to avoid circular import issues during startup.
        from ..template_seeder import (
            _get_check_in_protocol_section,
            _get_default_templates_v103,
            _get_mcp_coordination_section,
            _get_orchestrator_context_response_section,
            _get_orchestrator_messaging_protocol_section,
        )

        base_template = ""
        for template_def in _get_default_templates_v103():
            if template_def.get("role") == "orchestrator":
                base_template = template_def["user_instructions"].strip()
                break

        if not base_template:
            raise RuntimeError("Default orchestrator template definition not found")

        orchestrator_response = _get_orchestrator_context_response_section().strip()
        mcp_section = _get_mcp_coordination_section().strip()
        check_in = _get_check_in_protocol_section().strip()
        orchestrator_messaging = _get_orchestrator_messaging_protocol_section().strip()

        user_instructions = f"{base_template}\n\n{orchestrator_response}".strip()
        # Orchestrator doesn't need context_request (it doesn't ask itself for context)
        system_instructions = f"{mcp_section}\n\n{check_in}\n\n{orchestrator_messaging}".strip()

        self._default_orchestrator_prompt = f"{user_instructions}\n\n{system_instructions}".strip()
        return self._default_orchestrator_prompt
