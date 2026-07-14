# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""BE-6211f Split 3 — mission_assembly extraction: free functions + back-compat shims.

Split 3 moved ``_assemble_mission_context`` + ``_compute_protocol_etag`` out of
mission_service.py into a new ``mission_assembly.py`` as free functions that take
already-fetched ORM objects and open NO database sessions. ``MissionService`` keeps
thin shims delegating to them (other suites — test_be6208g, test_be6177_chain_header_mode,
test_be6205_conductor_banner, test_mission_service_serena_guidance — call those shims).

These tests lock the new module surface + the etag shim's pass-through delegation.
Pure (no DB, no module-level mutable state) — parallel-safe under xdist.
Edition Scope: CE.
"""

from __future__ import annotations


def test_free_functions_importable_from_mission_assembly() -> None:
    """The extracted logic is importable from the new module as free functions."""
    from giljo_mcp.services.mission_assembly import (
        assemble_mission_context,
        compute_protocol_etag,
    )

    assert callable(assemble_mission_context)
    assert callable(compute_protocol_etag)


def test_back_compat_shims_still_present_on_mission_service() -> None:
    """The shims other suites depend on are still attributes of MissionService."""
    from giljo_mcp.services.mission_service import MissionService

    assert hasattr(MissionService, "_assemble_mission_context")
    assert hasattr(MissionService, "_compute_protocol_etag")


def test_compute_etag_shim_delegates_to_free_function() -> None:
    """MissionService._compute_protocol_etag is a pure pass-through to the free function."""
    from giljo_mcp.services.mission_assembly import compute_protocol_etag
    from giljo_mcp.services.mission_service import MissionService

    assert MissionService._compute_protocol_etag("ID", "PROTO") == compute_protocol_etag("ID", "PROTO")
    assert MissionService._compute_protocol_etag(None, None) == compute_protocol_etag(None, None)


def test_compute_etag_is_stable_and_collision_resistant() -> None:
    """Deterministic over (identity, protocol); the NUL separator prevents concat collisions."""
    from giljo_mcp.services.mission_assembly import compute_protocol_etag

    assert compute_protocol_etag("ID", "PROTO") == compute_protocol_etag("ID", "PROTO")
    assert compute_protocol_etag("AB", "C") != compute_protocol_etag("A", "BC")
