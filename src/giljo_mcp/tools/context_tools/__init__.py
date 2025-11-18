"""Context fetching tools for thin client orchestration.

This module provides MCP tools for on-demand context fetching with user-configured depth levels.
These tools support the thin client architecture (Handover 0315) by allowing orchestrators to
fetch only the context they need, reducing token usage from ~3500 to ~600 tokens.

Available Tools:
- get_vision_document: Fetch vision document chunks with configurable chunking depth
- get_360_memory: Fetch sequential project history from product memory
- get_git_history: Fetch git commit history (when GitHub integration enabled)
- get_agent_templates: Fetch agent template metadata
- get_tech_stack: Fetch tech stack information
- get_architecture: Fetch architecture documentation
"""

from .get_vision_document import get_vision_document
from .get_360_memory import get_360_memory
from .get_git_history import get_git_history
from .get_agent_templates import get_agent_templates
from .get_tech_stack import get_tech_stack
from .get_architecture import get_architecture

__all__ = [
    "get_vision_document",
    "get_360_memory",
    "get_git_history",
    "get_agent_templates",
    "get_tech_stack",
    "get_architecture",
]
