# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
MCP Tool: submit_tuning_review (Tool #24, Handover 0831)

Allows agents to submit structured product context tuning proposals
after analyzing current product context against recent project history.

Called by the user's AI coding agent after reviewing the tuning comparison prompt.
Approved proposals are applied directly to product fields — no dashboard review step.
"""

import logging
from typing import Any

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.services.product_tuning_service import ProductTuningService

logger = logging.getLogger(__name__)

VALID_SECTIONS = {
    "description",
    "tech_stack",
    "architecture",
    "core_features",
    "brand_guidelines",
    "quality_standards",
    "target_platforms",
}

VALID_CONFIDENCE_LEVELS = {"high", "medium", "low"}


def _validate_proposals(proposals: list[dict[str, Any]]) -> list[str]:
    """Validate proposal structure. Returns list of error messages."""
    errors = []

    if not proposals:
        errors.append("proposals array must not be empty")
        return errors

    for i, proposal in enumerate(proposals):
        if not isinstance(proposal, dict):
            errors.append(f"proposals[{i}]: must be an object")
            continue

        section = proposal.get("section")
        if not section or section not in VALID_SECTIONS:
            errors.append(f"proposals[{i}]: invalid section '{section}', must be one of {sorted(VALID_SECTIONS)}")

        if "drift_detected" not in proposal:
            errors.append(f"proposals[{i}]: missing required field 'drift_detected'")

        confidence = proposal.get("confidence")
        if confidence and confidence not in VALID_CONFIDENCE_LEVELS:
            errors.append(f"proposals[{i}]: invalid confidence '{confidence}', must be high/medium/low")

        proposed_value = proposal.get("proposed_value")
        if proposed_value is not None:
            if not isinstance(proposed_value, (str, dict, list)):
                errors.append(
                    f"proposals[{i}]: proposed_value must be a string, object, or array, "
                    f"got {type(proposed_value).__name__}"
                )
            elif isinstance(proposed_value, str) and len(proposed_value) > 10000:
                errors.append(
                    f"proposals[{i}]: proposed_value string exceeds 10000 character limit ({len(proposed_value)} chars)"
                )
            elif isinstance(proposed_value, list) and section == "target_platforms":
                for j, item in enumerate(proposed_value):
                    if not isinstance(item, str):
                        errors.append(
                            f"proposals[{i}]: proposed_value[{j}] must be a string for "
                            f"target_platforms, got {type(item).__name__}"
                        )

    return errors


async def submit_tuning_review(
    product_id: str,
    tenant_key: str,
    proposals: list[dict[str, Any]],
    overall_summary: str | None = None,
    db_manager: DatabaseManager | None = None,
    websocket_manager: Any = None,
) -> dict[str, Any]:
    """
    Apply approved product context tuning proposals directly to product fields.

    Called by the user's AI coding agent after interactive review in the CLI.
    Proposals where drift_detected is True are written immediately. Proposals
    where drift_detected is False are skipped — no change is needed.

    Args:
        product_id: Target product UUID
        tenant_key: Tenant isolation key
        proposals: Per-section proposal dicts (user-reviewed)
        overall_summary: High-level drift assessment (informational)
        db_manager: Injected by ToolAccessor
        websocket_manager: Injected by ToolAccessor

    Returns:
        Dict with success, applied_count, sections_applied
    """
    if not db_manager:
        raise ValueError("db_manager is required")

    errors = _validate_proposals(proposals)
    if errors:
        raise ValueError(f"Invalid proposals: {'; '.join(errors)}")

    service = ProductTuningService(
        db_manager=db_manager,
        tenant_key=tenant_key,
        websocket_manager=websocket_manager,
    )

    return await service.apply_tuning_updates(
        product_id=product_id,
        proposals=proposals,
        overall_summary=overall_summary,
    )
