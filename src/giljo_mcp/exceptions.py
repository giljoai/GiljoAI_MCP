"""
Centralized Exception Hierarchy for GiljoAI MCP

This module provides a standardized exception hierarchy for consistent error handling
across the entire GiljoAI MCP system.
"""

from typing import Optional


class BaseGiljoException(Exception):
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
            "status_code": self.default_status_code
        }


# Configuration related exceptions
class ConfigurationError(BaseGiljoException):
    """Raised when there are configuration issues."""
    default_status_code: int = 500


class ConfigValidationError(ConfigurationError):
    """Raised when configuration validation fails."""


# Template related exceptions
class TemplateError(BaseGiljoException):
    """Base class for template-related errors."""


class TemplateNotFoundError(TemplateError):
    """Raised when a requested template cannot be found."""
    default_status_code: int = 404


# Orchestration related exceptions
class OrchestrationError(BaseGiljoException):
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
class DatabaseError(BaseGiljoException):
    """Base class for database-related errors."""
    default_status_code: int = 500


class DatabaseConnectionError(DatabaseError):
    """Raised when database connection fails."""


class DatabaseMigrationError(DatabaseError):
    """Raised when database migration fails."""


class DatabaseIntegrityError(DatabaseError):
    """Raised when database integrity constraints are violated."""


# Validation related exceptions
class ValidationError(BaseGiljoException):
    """Base class for validation errors."""
    default_status_code: int = 400


class SchemaValidationError(ValidationError):
    """Raised when schema validation fails."""


class DataValidationError(ValidationError):
    """Raised when data validation fails."""


# Queue related exceptions
class QueueException(BaseGiljoException):
    """Base class for queue-related errors."""


class ConsistencyError(QueueException):
    """Raised when queue consistency checks fail."""


class MessageDeliveryError(QueueException):
    """Raised when message delivery fails."""


# API related exceptions
class APIError(BaseGiljoException):
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
class ResourceError(BaseGiljoException):
    """Base class for resource-related errors."""


class ResourceNotFoundError(ResourceError):
    """Raised when a requested resource cannot be found."""
    default_status_code: int = 404


class ResourceExhaustedError(ResourceError):
    """Raised when resources are exhausted."""


class RetryExhaustedError(ResourceError):
    """Raised when retry attempts are exhausted."""


# Context and session exceptions
class ContextError(BaseGiljoException):
    """Base class for context-related errors."""


class ContextLimitError(ContextError):
    """Raised when context limits are exceeded."""


class SessionError(BaseGiljoException):
    """Base class for session-related errors."""


class SessionExpiredError(SessionError):
    """Raised when a session has expired."""


# File and path exceptions
class FileSystemError(BaseGiljoException):
    """Base class for file system errors."""


class FileNotFoundError(FileSystemError):
    """Raised when a required file is not found."""


class PermissionError(FileSystemError):
    """Raised when file system permissions are insufficient."""


# Tool and MCP related exceptions
class MCPError(BaseGiljoException):
    """Base class for MCP protocol errors."""


class ToolError(MCPError):
    """Raised when MCP tool operations fail."""


class ProtocolError(MCPError):
    """Raised when MCP protocol violations occur."""


# Vision document exceptions
class VisionError(BaseGiljoException):
    """Base class for vision document errors."""


class VisionChunkingError(VisionError):
    """Raised when vision document chunking fails."""


class VisionParsingError(VisionError):
    """Raised when vision document parsing fails."""


def create_error_from_exception(exc: Exception, context: Optional[dict] = None) -> BaseGiljoException:
    """
    Convert a standard Python exception to a GiljoAI exception.

    Args:
        exc: The original exception
        context: Optional context to add to the error

    Returns:
        A BaseGiljoException or appropriate subclass
    """
    if isinstance(exc, BaseGiljoException):
        # Already a GiljoAI exception, just update context if needed
        if context:
            exc.context.update(context)
        return exc

    # Map common Python exceptions to appropriate GiljoAI exceptions
    mapping = {
        FileNotFoundError: FileNotFoundError,
        PermissionError: PermissionError,
        ConnectionError: DatabaseConnectionError,
        TimeoutError: ResourceExhaustedError,
        ValueError: ValidationError,
        KeyError: DataValidationError,
    }

    exception_class = mapping.get(type(exc), BaseGiljoException)
    return exception_class(message=str(exc), context=context or {"original_type": type(exc).__name__})
