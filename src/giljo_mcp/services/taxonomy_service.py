# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition -- source-available, single-user use only.

"""
TaxonomyService - unified taxonomy lookup for projects and tasks.

Phase A of the agent-parity + unified taxonomy project. The underlying
table (taxonomy_types, formerly project_types) is shared by Project
classification and -- as of Phase B -- Task classification. The legacy
module-level helpers in services/taxonomy_ops.py remain in place
for the existing project-side call sites; this class is the public
surface new code (TaskService.create_task_for_mcp, list_tasks tool)
calls when it needs to validate or list taxonomy types.

Tenant isolation is enforced by the underlying repository on every
read and write.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from giljo_mcp.database import DatabaseManager
from giljo_mcp.exceptions import ValidationError
from giljo_mcp.models.projects import TaxonomyType
from giljo_mcp.repositories.taxonomy_repository import TaxonomyRepository
from giljo_mcp.services import taxonomy_ops


logger = logging.getLogger(__name__)


class TaxonomyService:
    """Service surface for the taxonomy_types table."""

    def __init__(
        self,
        db_manager: DatabaseManager,
        session: AsyncSession | None = None,
    ) -> None:
        self._db_manager = db_manager
        self._session = session
        self._repo = TaxonomyRepository()
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    async def list_types(self, tenant_key: str) -> list[TaxonomyType]:
        """Return all taxonomy types for a tenant, ordered by sort_order.

        Each row carries a ``project_count`` attribute populated by the
        repository (legacy column name, kept for back-compat with the UI
        dropdown that already reads it).
        """
        if not tenant_key:
            raise ValidationError(
                "tenant_key is required",
                context={"operation": "taxonomy.list_types"},
            )
        if self._session is not None:
            return await taxonomy_ops.list_taxonomy_types(self._session, tenant_key)
        async with self._db_manager.get_session_async() as session:
            return await taxonomy_ops.list_taxonomy_types(session, tenant_key)

    async def validate(self, abbreviation: str, tenant_key: str) -> TaxonomyType:
        """Resolve an abbreviation to a TaxonomyType row, or raise.

        Lookup is case-sensitive on abbreviation (matching the storage
        convention BE / FE / INF). Callers pre-uppercase agent input.
        """
        if not abbreviation or not abbreviation.strip():
            raise ValidationError(
                "abbreviation is required",
                context={"operation": "taxonomy.validate"},
            )
        if not tenant_key:
            raise ValidationError(
                "tenant_key is required",
                context={"operation": "taxonomy.validate"},
            )
        normalized = abbreviation.strip()
        if self._session is not None:
            row = await self._repo.get_by_abbreviation(self._session, tenant_key, normalized)
        else:
            async with self._db_manager.get_session_async() as session:
                row = await self._repo.get_by_abbreviation(session, tenant_key, normalized)

        if row is None:
            valid_types = await self._valid_types_payload(tenant_key)
            valid_abbrevs = sorted(t["abbreviation"] for t in valid_types)
            raise ValidationError(
                f"Unknown taxonomy type '{normalized}'. Valid types: {', '.join(valid_abbrevs)}.",
                context={
                    "operation": "taxonomy.validate",
                    "abbreviation": normalized,
                    "valid_types": valid_types,
                },
            )
        return row

    async def create_type(
        self,
        tenant_key: str,
        *,
        abbreviation: str,
        label: str,
        color: str = "#607D8B",
        sort_order: int = 0,
    ) -> TaxonomyType:
        """Create a new taxonomy type. Tenant-scoped, abbreviation-unique."""
        if not tenant_key:
            raise ValidationError(
                "tenant_key is required",
                context={"operation": "taxonomy.create_type"},
            )
        if self._session is not None:
            return await taxonomy_ops.create_taxonomy_type(
                self._session,
                tenant_key,
                abbreviation=abbreviation,
                label=label,
                color=color,
                sort_order=sort_order,
            )
        async with self._db_manager.get_session_async() as session:
            return await taxonomy_ops.create_taxonomy_type(
                session,
                tenant_key,
                abbreviation=abbreviation,
                label=label,
                color=color,
                sort_order=sort_order,
            )

    async def _valid_types_payload(self, tenant_key: str) -> list[dict[str, Any]]:
        rows = await self.list_types(tenant_key)
        return [{"abbreviation": t.abbreviation, "label": t.label, "color": t.color} for t in rows]
