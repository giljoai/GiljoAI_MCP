"""Protocol sections subpackage — focused submodules extracted from protocol_builder.py."""

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
    _build_ch2_fetch_calls,
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


__all__ = [
    "DEFAULT_DEPTH_CONFIG",
    "DEFAULT_FIELD_PRIORITIES",
    "_build_ch1_mission",
    "_build_ch2_fetch_calls",
    "_build_ch2_startup",
    "_build_ch3_spawning_rules",
    "_build_ch4_error_handling",
    "_build_ch5_reference",
    "_build_ch6_auto_checkin",
    "_generate_agent_protocol",
    "_generate_orchestrator_protocol",
    "_generate_team_context_header",
    "_get_user_config",
    "_normalize_field_toggles",
]
