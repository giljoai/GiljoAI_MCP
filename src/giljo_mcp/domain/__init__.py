# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition -- source-available, single-user use only.

"""Shared domain enums and value objects.

This package holds cross-layer domain primitives that have no service or
repository dependencies. The first inhabitant is :mod:`project_status`,
which defines the canonical :class:`~giljo_mcp.domain.project_status.ProjectStatus`
enum used by the ORM, the lifecycle services, the REST endpoints, and the
status-metadata API.

Edition isolation: this package is CE-foundational. Nothing here imports
from ``saas/`` or ``demo/``. The Deletion Test (CE must run with all
``saas/`` directories removed) holds because none of these symbols depend
on SaaS code.
"""

from giljo_mcp.domain.project_status import (
    IMMUTABLE_PROJECT_STATUSES,
    LIFECYCLE_FINISHED_STATUSES,
    PROJECT_STATUS_META,
    VALID_PROJECT_STATUSES,
    VALID_UPDATE_STATUSES,
    ProjectStatus,
    ProjectStatusMeta,
)


__all__ = [
    "IMMUTABLE_PROJECT_STATUSES",
    "LIFECYCLE_FINISHED_STATUSES",
    "PROJECT_STATUS_META",
    "VALID_PROJECT_STATUSES",
    "VALID_UPDATE_STATUSES",
    "ProjectStatus",
    "ProjectStatusMeta",
]
