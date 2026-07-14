# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""BE-9144 follow-up: lock the extracted closeout-readiness module's public surface.

The 800-line guardrail extraction (PR #453) moved AgentReadinessFinding,
CloseoutReadinessReport and the two batch lookup helpers out of
project_closeout_service.py into project_closeout_readiness.py, re-exporting the
dataclasses from the service so existing importers keep resolving. These tests pin
both halves of that contract; the helpers' behavior itself is covered by
tests/services/test_be9144_closeout_batch.py (result-equivalence + query counts).
"""

from giljo_mcp.services import project_closeout_readiness as readiness
from giljo_mcp.services import project_closeout_service as service


def test_dataclasses_re_exported_identically():
    """The service re-exports must be the SAME objects, not copies."""
    assert service.AgentReadinessFinding is readiness.AgentReadinessFinding
    assert service.CloseoutReadinessReport is readiness.CloseoutReadinessReport


def test_batch_helpers_live_in_readiness_module():
    """The batch lookup helpers moved with the extraction and stay async."""
    import inspect

    assert inspect.iscoroutinefunction(readiness.incomplete_todos_by_jobs)
    assert inspect.iscoroutinefunction(readiness.pending_approval_ids_by_execution)
