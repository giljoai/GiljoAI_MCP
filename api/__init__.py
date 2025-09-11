"""
GiljoAI MCP API Package
FastAPI-based REST and WebSocket API for orchestration system
"""

from .app import create_app

__all__ = ['create_app']