# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""
BE-6042h characterization test — locks the public surface of JobLifecycleService.

This suite is the behavior lock for the mechanical extraction of
``_build_predecessor_context`` out of ``job_lifecycle_service.py`` into the
module-level ``build_predecessor_context`` in ``_predecessor_context.py``. It
runs GREEN against the unmodified service FIRST, then unchanged after the
extraction. It asserts:

- The public import path
  ``from giljo_mcp.services.job_lifecycle_service import JobLifecycleService``
  resolves.
- ``spawn_job`` is the sole public async method, present and callable — catches
  the one real extraction failure mode: an accidentally public-exposed helper
  or a dropped ``spawn_job``.
- The private ``_build_predecessor_context`` method is NOT part of the public
  surface (it is being extracted to a module-level function).
"""

import inspect
from unittest.mock import MagicMock

from giljo_mcp.services.job_lifecycle_service import JobLifecycleService


# spawn_job is the only public method on JobLifecycleService. Everything else is
# a private `_`-prefixed helper. _build_predecessor_context (being extracted) is
# intentionally absent from this frozenset — it is not public surface.
PUBLIC_ASYNC_METHODS = frozenset({"spawn_job"})


def _service() -> JobLifecycleService:
    return JobLifecycleService(db_manager=MagicMock(), tenant_manager=MagicMock())


def test_public_import_resolves():
    from giljo_mcp.services.job_lifecycle_service import (
        JobLifecycleService as Imported,
    )

    assert Imported is JobLifecycleService


def test_public_async_surface_is_exactly_spawn_job():
    service = _service()
    public_async = {
        name
        for name in dir(service)
        if not name.startswith("_") and inspect.iscoroutinefunction(getattr(service, name))
    }
    assert public_async == PUBLIC_ASYNC_METHODS


def test_spawn_job_present_callable_async():
    service = _service()
    assert hasattr(service, "spawn_job")
    assert callable(service.spawn_job)
    assert inspect.iscoroutinefunction(service.spawn_job)
