"""
Slash command registry for GiljoAI
Maps /gil_* commands to handler functions
"""

from typing import Callable

from .handover import handle_gil_handover


# Slash command registry
# NOTE: gil_activate, gil_launch removed (0388) - users perform these via web UI
SLASH_COMMANDS: dict[str, Callable] = {
    "gil_handover": handle_gil_handover,
}


def get_slash_command(command_name: str) -> Callable | None:
    """Get handler for slash command"""
    return SLASH_COMMANDS.get(command_name)
