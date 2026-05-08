# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""
Taxonomy Types Module

Provides CRUD endpoints for the unified taxonomy (projects + tasks) backed by
the ``taxonomy_types`` table. Renamed from ``project_types`` in Phase A of the
agent-parity + unified Type taxonomy project (2026-05).

All routers use ``/api/v1/taxonomy-types`` prefix and ``taxonomy-types`` tag.
"""

from fastapi import APIRouter

from . import routes


router = APIRouter(prefix="/api/v1/taxonomy-types", tags=["taxonomy-types"])
router.include_router(routes.router)

__all__ = ["router"]
