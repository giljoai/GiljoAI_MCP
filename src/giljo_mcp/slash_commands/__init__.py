"""
Slash command registry for GiljoAI
Maps /gil_* commands to handler functions
"""

from typing import Callable


# Slash command registry
# NOTE: gil_activate, gil_launch removed (0388) - users perform these via web UI
# NOTE: gil_handover removed (0461/0700d) - user triggers via UI button (simple-handover REST endpoint)
SLASH_COMMANDS: dict[str, Callable] = {}


def get_slash_command(command_name: str) -> Callable | None:
    """Get handler for slash command"""
    return SLASH_COMMANDS.get(command_name)
