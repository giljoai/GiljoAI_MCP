# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""
BE-9060 (item 3) / BE-9073 (item 2): regression guard for the task_service
mixin splits.

task_service.py (1552-line god-class) was first split into the task_service/
package, extracting the agent-facing MCP surface into
``_mcp_adapter_mixin.McpAdapterMixin`` (mirroring the project_service package
precedent). BE-9073 item 2 then split the remaining ~1134-line composed class
further into ``_query_mixin._TaskQueryMixin`` (read path),
``_mutation_mixin._TaskMutationMixin`` (core CRUD write path), and
``_lifecycle_mixin._TaskLifecycleMixin`` (status-change / conversion /
completion-notes -- split out of the mutation mixin so every file in the
package stays under the 800-line cap with no ``size_budgets.txt`` entry),
mirroring project_service's QueryMixin/MutationMixin. These tests lock the
split at the layer it changed: the public import surface, the mixin
composition, and the verbatim behavior of the pure row-projection helpers
that moved into the mcp-adapter mixin.

The full behavioral surface (create/update/list_for_mcp against a DB) is covered
by the existing service/integration suites (test_task_taxonomy_mcp_tools,
test_be6049c_tsk_namespace, test_task_tools_mcp_transport, ...). This file guards
the STRUCTURE so a future re-split cannot silently drop a method off the composed
class or break an importer.
"""

from __future__ import annotations

from types import SimpleNamespace

from giljo_mcp.services.task_service import _ALLOWED_TASK_UPDATE_FIELDS, TaskService
from giljo_mcp.services.task_service._lifecycle_mixin import _TaskLifecycleMixin
from giljo_mcp.services.task_service._mcp_adapter_mixin import McpAdapterMixin
from giljo_mcp.services.task_service._mutation_mixin import (
    _ALLOWED_TASK_UPDATE_FIELDS as _MUTATION_MIXIN_ALLOWED_FIELDS,
)
from giljo_mcp.services.task_service._mutation_mixin import _TaskMutationMixin
from giljo_mcp.services.task_service._query_mixin import _TaskQueryMixin


def test_public_import_surface_preserved():
    """TaskService + _ALLOWED_TASK_UPDATE_FIELDS still import from the package path."""
    assert isinstance(_ALLOWED_TASK_UPDATE_FIELDS, frozenset)
    assert "title" in _ALLOWED_TASK_UPDATE_FIELDS
    # task_type_id stays excluded (TSK tag immutable — behavior unchanged by the split).
    assert "task_type_id" not in _ALLOWED_TASK_UPDATE_FIELDS


def test_taskservice_composes_the_mcp_adapter_mixin():
    assert issubclass(TaskService, McpAdapterMixin)


def test_taskservice_composes_the_query_and_mutation_mixins():
    """BE-9073 item 2: TaskService also composes the read/write/lifecycle mixins."""
    assert issubclass(TaskService, _TaskMutationMixin)
    assert issubclass(TaskService, _TaskLifecycleMixin)
    assert issubclass(TaskService, _TaskQueryMixin)


def test_allowed_update_fields_reexported_from_mutation_mixin():
    """_ALLOWED_TASK_UPDATE_FIELDS now lives in _mutation_mixin, re-exported
    at the package path for back-compat importers/tests."""
    assert _ALLOWED_TASK_UPDATE_FIELDS is _MUTATION_MIXIN_ALLOWED_FIELDS


def test_query_and_mutation_methods_resolve_on_composed_class():
    # Read-path methods that moved into _TaskQueryMixin.
    for name in (
        "list_tasks",
        "_list_tasks_impl",
        "get_task",
        "_get_task_impl",
        "list_deleted_tasks",
        "get_summary",
    ):
        assert callable(getattr(TaskService, name)), name
        assert hasattr(_TaskQueryMixin, name), name
    # Core CRUD write-path methods that moved into _TaskMutationMixin.
    for name in (
        "log_task",
        "_log_task_impl",
        "create_task",
        "create_task_for_rest",
        "update_task",
        "_update_task_impl",
        "delete_task",
        "_delete_task_impl",
        "restore_task",
        "_restore_task_impl",
        "purge_expired_deleted_tasks",
    ):
        assert callable(getattr(TaskService, name)), name
        assert hasattr(_TaskMutationMixin, name), name
    # Status-change / conversion / completion-notes methods that moved into
    # _TaskLifecycleMixin (split out of _TaskMutationMixin to stay under 800 lines).
    for name in (
        "convert_to_project",
        "change_status",
        "_change_status_impl",
        "_change_status_with_tenant",
        "append_completion_notes",
        "_append_completion_notes",
    ):
        assert callable(getattr(TaskService, name)), name
        assert hasattr(_TaskLifecycleMixin, name), name


def test_logger_name_unchanged_after_package_conversion():
    """The package __name__ matches the old module, so the logger name is stable."""
    svc = TaskService.__module__
    assert svc == "giljo_mcp.services.task_service"


def test_facade_and_core_methods_all_resolve_on_composed_class():
    # Facade methods that moved into the mixin.
    for name in (
        "create_task_for_mcp",
        "update_task_for_mcp",
        "list_tasks_for_mcp",
        "_list_tasks_for_mcp_impl",
        "_task_type_block",
        "_task_to_summary_row",
        "_task_to_full_row",
    ):
        assert callable(getattr(TaskService, name)), name
    # Core methods (now split across _TaskQueryMixin / _TaskMutationMixin,
    # BE-9073 item 2 -- still resolve unchanged on the composed class).
    for name in (
        "log_task",
        "create_task",
        "update_task",
        "get_task",
        "delete_task",
        "restore_task",
        "append_completion_notes",
        "_append_completion_notes",
        "_change_status_with_tenant",
    ):
        assert callable(getattr(TaskService, name)), name


def _stub_task(**overrides):
    """A minimal attribute bag matching what the row helpers read off a Task."""
    base = {
        "id": "task-123",
        "title": "Ship the thing",
        "status": "in_progress",
        "priority": "high",
        "task_type": SimpleNamespace(id="tt-1", abbreviation="TSK", label="Task", color="#abc"),
        "taxonomy_alias": "TSK-0042",
        "series_number": 42,
        "subseries": None,
        "hidden": False,
        "due_date": None,
        "created_at": None,
        "description": "a" * 50,
        "task_type_id": "tt-1",
        "product_id": "prod-1",
        "project_id": None,
        "parent_task_id": None,
        "estimated_effort": None,
        "actual_effort": None,
        "started_at": None,
        "completed_at": None,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_task_type_block_shape():
    block = TaskService._task_type_block(_stub_task())
    assert block == {"id": "tt-1", "abbreviation": "TSK", "label": "Task", "color": "#abc"}
    assert TaskService._task_type_block(_stub_task(task_type=None)) is None


def test_summary_row_shape():
    row = TaskService._task_to_summary_row(_stub_task())
    assert row["task_id"] == "task-123"
    assert row["taxonomy_alias"] == "TSK-0042"
    assert row["task_type"]["abbreviation"] == "TSK"
    assert row["hidden"] is False
    # summary is the lean projection — no description column.
    assert "description" not in row


def test_full_row_truncates_description_at_memory_limit():
    row = TaskService._task_to_full_row(_stub_task(), memory_limit=10)
    assert row["description"] == "a" * 10 + "..."
    # no limit -> full description preserved.
    full = TaskService._task_to_full_row(_stub_task(), memory_limit=None)
    assert full["description"] == "a" * 50
    assert full["product_id"] == "prod-1"
