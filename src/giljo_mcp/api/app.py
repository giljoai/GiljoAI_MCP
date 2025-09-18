"""
FastAPI application for GiljoAI MCP Orchestrator
Provides REST API endpoints for all MCP tools
"""

import logging
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .endpoints import agents, messages, projects, tasks, templates


logger = logging.getLogger(__name__)


def create_app(config: Optional[dict] = None) -> FastAPI:
    """
    Create and configure FastAPI application.
    
    Args:
        config: Optional configuration dictionary
        
    Returns:
        Configured FastAPI application
    """
    app = FastAPI(
        title="GiljoAI MCP Orchestrator API",
        version="5.4.4",
        description="Multi-agent coding orchestrator REST API",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Add CORS middleware for development
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Basic health check endpoint
    @app.get("/health")
    async def health_check():
        """Health check endpoint"""
        return {
            "status": "healthy",
            "message": "GiljoAI MCP Orchestrator API is running",
            "version": "5.4.4"
        }

    # Root endpoint
    @app.get("/")
    async def root():
        """Root endpoint"""
        return {
            "message": "GiljoAI MCP Orchestrator API",
            "version": "5.4.4",
            "docs": "/docs",
            "health": "/health"
        }

    # Include all endpoint routers
    app.include_router(projects.router)
    app.include_router(agents.router)
    app.include_router(messages.router)
    app.include_router(tasks.router)
    app.include_router(templates.router)

    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc):
        logger.exception(f"Unhandled exception: {exc}")
        return HTTPException(
            status_code=500,
            detail="Internal server error"
        )

    logger.info("FastAPI application created with all endpoint routers")
    return app


# Default app instance for testing
app = create_app()
