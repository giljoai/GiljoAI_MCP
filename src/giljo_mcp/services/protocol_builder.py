"""
Protocol Builder - Compositor for orchestrator protocol chapters.

Handover 0750e2: Extracted from orchestration_service.py.
Handover 0950j: Section builders moved to protocol_sections/ subpackage.
This module retains the compositor function and re-exports for backward compatibility.
"""

from __future__ import annotations

import logging
from typing import Any

from src.giljo_mcp.services.protocol_sections.agent_lifecycle import (
    _generate_orchestrator_protocol,
)
from src.giljo_mcp.services.protocol_sections.agent_protocol import (
    _generate_agent_protocol,
)
from src.giljo_mcp.services.protocol_sections.chapters_reference import (
    _build_ch3_spawning_rules,
    _build_ch4_error_handling,
    _build_ch5_reference,
    _build_ch6_auto_checkin,
)
from src.giljo_mcp.services.protocol_sections.chapters_startup import (
    _build_ch1_mission,
    _build_ch2_startup,
)
from src.giljo_mcp.services.protocol_sections.team_context import (
    _generate_team_context_header,
)
from src.giljo_mcp.services.protocol_sections.user_config import (
    DEFAULT_DEPTH_CONFIG,
    DEFAULT_FIELD_PRIORITIES,
    _get_user_config,
    _normalize_field_toggles,
)


logger = logging.getLogger(__name__)

# Re-export all section functions for backward compatibility
__all__ = [
    "DEFAULT_DEPTH_CONFIG",
    "DEFAULT_FIELD_PRIORITIES",
    "_build_ch1_mission",
    "_build_ch2_startup",
    "_build_ch3_spawning_rules",
    "_build_ch4_error_handling",
    "_build_ch5_reference",
    "_build_ch6_auto_checkin",
    "_build_orchestrator_protocol",
    "_generate_agent_protocol",
    "_generate_orchestrator_protocol",
    "_generate_team_context_header",
    "_get_user_config",
    "_normalize_field_toggles",
]


def _build_orchestrator_protocol(
    cli_mode: bool,
    project_id: str,
    orchestrator_id: str,
    tenant_key: str,
    include_implementation_reference: bool = True,
    field_toggles: dict[str, bool] | None = None,
    depth_config: dict[str, Any] | None = None,
    product_id: str | None = None,
    tool: str = "claude-code",
    auto_checkin_enabled: bool = False,
    auto_checkin_interval: int = 60,
) -> dict:
    """
    Build chapter-based orchestrator protocol.

    Creates 5-6 navigable chapters with clear visual boundaries.
    Solves the "rotation problem" where content gets buried.

    Args:
        cli_mode: True if execution_mode is any CLI subagent mode
        project_id: Project UUID for parameter substitution
        orchestrator_id: Job ID for parameter substitution
        tenant_key: Tenant key for parameter substitution
        include_implementation_reference: Include CH5 (default True)
        field_toggles: Category toggles for inline fetch injection (Handover 0823)
        depth_config: Depth settings per category (Handover 0823)
        product_id: Product UUID for fetch calls (Handover 0823)
        tool: Platform identifier for platform-specific spawning rules (Handover 0838)
        auto_checkin_enabled: Enable CH6 auto check-in protocol (Handover 0904)
        auto_checkin_interval: Check-in interval in seconds (Handover 0904)

    Returns:
        Dict with chapter keys and navigation_hint
    """
    effective_tool = tool if cli_mode else "multi_terminal"
    ch1 = _build_ch1_mission(effective_tool)
    ch2 = _build_ch2_startup(
        orchestrator_id,
        project_id,
        field_toggles=field_toggles,
        depth_config=depth_config,
        product_id=product_id,
        tenant_key=tenant_key,
    )
    ch3 = _build_ch3_spawning_rules(effective_tool)
    ch4 = _build_ch4_error_handling()
    ch5 = _build_ch5_reference(project_id, orchestrator_id, effective_tool) if include_implementation_reference else ""

    ch6 = _build_ch6_auto_checkin(auto_checkin_interval) if (auto_checkin_enabled and not cli_mode) else ""

    return {
        "ch1_your_mission": ch1,
        "ch2_startup_sequence": ch2,
        "ch3_agent_spawning_rules": ch3,
        "ch4_error_handling": ch4,
        "ch5_reference": ch5,
        "ch6_auto_checkin": ch6,
        "navigation_hint": "Reference chapters by name (e.g., 'see CH4 for error handling')",
    }
