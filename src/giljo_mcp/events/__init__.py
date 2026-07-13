# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""
WebSocket Events Module (package marker)

Event schemas live in giljo_mcp.events.schemas; event ORM models live in
giljo_mcp.events.models. BE-8000d dup-3: this file previously re-exported
every schemas.py symbol at the package level, but nothing imported through
that path (always giljo_mcp.events.schemas.X directly) -- removed as a
redundant re-export bridge (Sprint-003a relocation leftover).

Handover 0086A: Production-Grade Stage Project Architecture
Task 1.4: Create Standardized Event Schemas
Created: 2025-11-02
"""
