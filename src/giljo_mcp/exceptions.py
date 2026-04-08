# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Centralized Exception Hierarchy for GiljoAI MCP

This module provides a standardized exception hierarchy for consistent error handling
across the entire GiljoAI MCP system.
"""

from typing import Optional


class BaseGiljoError(Exception):
    """
    Base exception for all GiljoAI MCP errors.

    All custom exceptions in the system should inherit from this base class
    to enable consistent error handling and categorization.
    """

    default_status_code: int = 500

    def __init__(self, message: str, error_code: Optional[str] = None, context: Optional[dict] = None):
        """
        Initialize the base exception.

        Args:
            message: Human-readable error message
            error_code: Optional machine-readable error code
            context: Optional dictionary with additional error context
        """
        from datetime import datetime, timezone

        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__.upper()
        self.context = context or {}
        self.timestamp = datetime.now(timezone.utc)

    def __str__(self):
        if self.context:
            return f"{self.message} (Context: {self.context})"
        return self.message

    def to_dict(self) -> dict:
        """
        Convert exception to dictionary format for API responses.

        Returns:
            Dictionary containing error details
        """
        return {
            "error_code": self.error_code,
            "message": self.message,
            "context": self.context,
            "timestamp": self.timestamp.isoformat(),
            "status_code": self.default_status_code,
        }


# Configuration related exceptions
class ConfigurationError(BaseGiljoError):
    """Raised when there are configuration issues."""

    default_status_code: int = 500


class ConfigValidationError(ConfigurationError):
    """Raised when configuration validation fails."""


# Template related exceptions
class TemplateError(BaseGiljoError):
    """Base class for template-related errors."""


class TemplateNotFoundError(TemplateError):
    """Raised when a requested template cannot be found."""

    default_status_code: int = 404


# Orchestration related exceptions
class OrchestrationError(BaseGiljoError):
    """Base class for orchestration-related errors."""

    default_status_code: int = 500


class AgentCreationError(OrchestrationError):
    """Raised when agent creation fails."""


class AgentCommunicationError(OrchestrationError):
    """Raised when agent communication fails."""


class ProjectStateError(OrchestrationError):
    """Raised when project state is invalid for requested operation."""


class HandoffError(OrchestrationError):
    """Raised when agent handoff fails."""


# Database related exceptions
class DatabaseError(BaseGiljoError):
    """Base class for database-related errors."""

    default_status_code: int = 500


class DatabaseConnectionError(DatabaseError):
    """Raised when database connection fails."""


class DatabaseMigrationError(DatabaseError):
    """Raised when database migration fails."""


class DatabaseIntegrityError(DatabaseError):
    """Raised when database integrity constraints are violated."""


# Validation related exceptions
class ValidationError(BaseGiljoError):
    """Base class for validation errors."""

    default_status_code: int = 400


class SchemaValidationError(ValidationError):
    """Raised when schema validation fails."""


class DataValidationError(ValidationError):
    """Raised when data validation fails."""


# Queue related exceptions
class QueueError(BaseGiljoError):
    """Base class for queue-related errors."""


class ConsistencyError(QueueError):
    """Raised when queue consistency checks fail."""


class MessageDeliveryError(QueueError):
    """Raised when message delivery fails."""


# API related exceptions
class APIError(BaseGiljoError):
    """Base class for API-related errors."""


class AuthenticationError(APIError):
    """Raised when API authentication fails."""

    default_status_code: int = 401


class AuthorizationError(APIError):
    """Raised when API authorization fails."""

    default_status_code: int = 403


class RateLimitError(APIError):
    """Raised when API rate limits are exceeded."""

    default_status_code: int = 429


# Resource related exceptions
class ResourceError(BaseGiljoError):
    """Base class for resource-related errors."""


class ResourceNotFoundError(ResourceError):
    """Raised when a requested resource cannot be found."""

    default_status_code: int = 404


class AlreadyExistsError(ResourceError):
    """Raised when attempting to create a resource that already exists."""

    default_status_code: int = 409


class ResourceExhaustedError(ResourceError):
    """Raised when resources are exhausted."""


class RetryExhaustedError(ResourceError):
    """Raised when retry attempts are exhausted."""


# Context and session exceptions
class ContextError(BaseGiljoError):
    """Base class for context-related errors."""


class ContextLimitError(ContextError):
    """Raised when context limits are exceeded."""


class SessionError(BaseGiljoError):
    """Base class for session-related errors."""


class SessionExpiredError(SessionError):
    """Raised when a session has expired."""


# File and path exceptions
class FileSystemError(BaseGiljoError):
    """Base class for file system errors."""


class GiljoFileNotFoundError(FileSystemError):
    """Raised when a required file is not found."""


class GiljoPermissionError(FileSystemError):
    """Raised when file system permissions are insufficient."""


# Tool and MCP related exceptions
class MCPError(BaseGiljoError):
    """Base class for MCP protocol errors."""


class ToolError(MCPError):
    """Raised when MCP tool operations fail."""


class ProtocolError(MCPError):
    """Raised when MCP protocol violations occur."""


# Vision document exceptions
class VisionError(BaseGiljoError):
    """Base class for vision document errors."""


class VisionChunkingError(VisionError):
    """Raised when vision document chunking fails."""


class VisionParsingError(VisionError):
    """Raised when vision document parsing fails."""
