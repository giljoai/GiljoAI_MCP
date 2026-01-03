"""
Slash command registry for GiljoAI
Maps /gil_* commands to handler functions
"""

from typing import Callable

from .handover import handle_gil_handover
from .project import handle_gil_activate, handle_gil_launch


# Slash command registry
SLASH_COMMANDS: dict[str, Callable] = {
    "gil_handover": handle_gil_handover,
    "gil_activate": handle_gil_activate,
    "gil_launch": handle_gil_launch,
    # Future commands:
    # "gil_activate": handle_gil_activate,
    # "gil_launch": handle_gil_launch,
    # "gil_status": handle_gil_status,
}


def get_slash_command(command_name: str) -> Callable | None:
    """Get handler for slash command"""
    return SLASH_COMMANDS.get(command_name)
