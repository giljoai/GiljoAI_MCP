# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""
WebSocket Events Module (package marker)

Canonical location for event schemas: giljo_mcp.events.schemas. BE-8000d
dup-3: this file and its sibling api/events/schemas.py previously re-exported
schemas.py symbols for api/ consumers, but nothing imported through either
path (always giljo_mcp.events.schemas.X directly) -- both removed as
redundant re-export bridges (Sprint-003a relocation leftovers).
"""
