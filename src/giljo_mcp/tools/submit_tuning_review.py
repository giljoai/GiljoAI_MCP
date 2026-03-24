"""
MCP Tool: submit_tuning_review (Tool #24, Handover 0831)

Allows agents to submit structured product context tuning proposals
after analyzing current product context against recent project history.

Called by the user's AI coding agent after reviewing the tuning comparison prompt.
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
    "codebase_structure",
    "database_type",
    "backend_framework",
    "frontend_framework",
    "quality_standards",
    "target_platforms",
    "vision_documents",
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
    Submit product context tuning proposals.

    Called by the user's AI coding agent after analyzing the comparison prompt.
    Stores proposals on the product for user review in the dashboard.

    Args:
        product_id: Target product UUID
        tenant_key: Tenant isolation key
        proposals: Per-section proposal dicts
        overall_summary: High-level drift assessment
        db_manager: Injected by ToolAccessor
        websocket_manager: Injected by ToolAccessor

    Returns:
        Dict with success, review_id, message
    """
    if not db_manager:
        raise ValueError("db_manager is required")

    # Validate proposals structure
    errors = _validate_proposals(proposals)
    if errors:
        raise ValueError(f"Invalid proposals: {'; '.join(errors)}")

    service = ProductTuningService(
        db_manager=db_manager,
        tenant_key=tenant_key,
        websocket_manager=websocket_manager,
    )

    return await service.store_proposals(
        product_id=product_id,
        proposals=proposals,
        overall_summary=overall_summary,
    )
