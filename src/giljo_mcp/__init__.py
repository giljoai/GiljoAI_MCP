"""
GiljoAI MCP - Multi-Agent Coding Orchestrator
"""

try:
    from importlib.metadata import PackageNotFoundError
    from importlib.metadata import version as _get_version

    __version__ = _get_version("giljo-mcp")
except (PackageNotFoundError, ImportError):
    __version__ = "1.0.0"
