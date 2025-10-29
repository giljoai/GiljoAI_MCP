"""
GiljoAI MCP Tools Package
Organized tool groups for MCP protocol operations
"""

from .agent import register_agent_tools
from .agent_communication import register_agent_communication_tools
from .agent_coordination import register_agent_coordination_tools
from .agent_coordination_external import register_external_agent_coordination_tools
from .agent_job_status import register_agent_job_status_tools
from .agent_messaging import register_agent_messaging_tools
from .agent_status import register_agent_status_tools
from .context import register_context_tools
from .message import register_message_tools
from .optimization import register_optimization_tools
from .orchestration import register_orchestration_tools
from .project import register_project_tools
from .task import register_task_tools


__all__ = [
    "register_agent_tools",
    "register_agent_communication_tools",
    "register_agent_coordination_tools",
    "register_agent_job_status_tools",
    "register_agent_messaging_tools",
    "register_agent_status_tools",
    "register_external_agent_coordination_tools",
    "register_context_tools",
    "register_git_tools",
    "register_message_tools",
    "register_optimization_tools",
    "register_orchestration_tools",
    "register_project_tools",
    "register_task_tools",
    "register_template_tools",
]