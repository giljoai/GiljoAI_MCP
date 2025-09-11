"""
GiljoAI MCP Tools Package
Organized tool groups for MCP protocol operations
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .project import register_project_tools
    from .agent import register_agent_tools
    from .message import register_message_tools
    from .context import register_context_tools

__all__ = [
    "register_project_tools",
    "register_agent_tools", 
    "register_message_tools",
    "register_context_tools"
]