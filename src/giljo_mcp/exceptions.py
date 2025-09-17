"""
Centralized Exception Hierarchy for GiljoAI MCP

This module provides a standardized exception hierarchy for consistent error handling
across the entire GiljoAI MCP system.
"""


class BaseGiljoException(Exception):
    """
    Base exception for all GiljoAI MCP errors.

    All custom exceptions in the system should inherit from this base class
    to enable consistent error handling and categorization.
    """

    def __init__(self, message: str, error_code: str = None, context: dict = None):
        """
        Initialize the base exception.

        Args:
            message: Human-readable error message
            error_code: Optional machine-readable error code
            context: Optional dictionary with additional error context
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__.upper()
        self.context = context or {}

    def __str__(self):
        if self.context:
            return f"{self.message} (Context: {self.context})"
        return self.message


# Configuration related exceptions
class ConfigurationError(BaseGiljoException):
    """Raised when there are configuration issues."""

    pass


class ConfigValidationError(ConfigurationError):
    """Raised when configuration validation fails."""

    pass


# Template related exceptions
class TemplateError(BaseGiljoException):
    """Base class for template-related errors."""

    pass


class TemplateNotFoundError(TemplateError):
    """Raised when a requested template cannot be found."""

    pass


class TemplateValidationError(TemplateError):
    """Raised when template validation fails."""

    pass


class TemplateRenderError(TemplateError):
    """Raised when template rendering fails."""

    pass


# Orchestration related exceptions
class OrchestrationError(BaseGiljoException):
    """Base class for orchestration-related errors."""

    pass


class AgentCreationError(OrchestrationError):
    """Raised when agent creation fails."""

    pass


class AgentCommunicationError(OrchestrationError):
    """Raised when agent communication fails."""

    pass


class ProjectStateError(OrchestrationError):
    """Raised when project state is invalid for requested operation."""

    pass


class HandoffError(OrchestrationError):
    """Raised when agent handoff fails."""

    pass


# Database related exceptions
class DatabaseError(BaseGiljoException):
    """Base class for database-related errors."""

    pass


class DatabaseConnectionError(DatabaseError):
    """Raised when database connection fails."""

    pass


class DatabaseMigrationError(DatabaseError):
    """Raised when database migration fails."""

    pass


class DatabaseIntegrityError(DatabaseError):
    """Raised when database integrity constraints are violated."""

    pass


# Validation related exceptions
class ValidationError(BaseGiljoException):
    """Base class for validation errors."""

    pass


class SchemaValidationError(ValidationError):
    """Raised when schema validation fails."""

    pass


class DataValidationError(ValidationError):
    """Raised when data validation fails."""

    pass


# Git operations exceptions
class GitOperationError(BaseGiljoException):
    """Base class for Git operation errors."""

    pass


class GitAuthenticationError(GitOperationError):
    """Raised when Git authentication fails."""

    pass


class GitRepositoryError(GitOperationError):
    """Raised when Git repository operations fail."""

    pass


# Queue related exceptions
class QueueException(BaseGiljoException):
    """Base class for queue-related errors."""

    pass


class ConsistencyError(QueueException):
    """Raised when queue consistency checks fail."""

    pass


class MessageDeliveryError(QueueException):
    """Raised when message delivery fails."""

    pass


# API related exceptions
class APIError(BaseGiljoException):
    """Base class for API-related errors."""

    pass


class AuthenticationError(APIError):
    """Raised when API authentication fails."""

    pass


class AuthorizationError(APIError):
    """Raised when API authorization fails."""

    pass


class RateLimitError(APIError):
    """Raised when API rate limits are exceeded."""

    pass


# Resource related exceptions
class ResourceError(BaseGiljoException):
    """Base class for resource-related errors."""

    pass


class ResourceNotFoundError(ResourceError):
    """Raised when a requested resource cannot be found."""

    pass


class ResourceExhaustedError(ResourceError):
    """Raised when resources are exhausted."""

    pass


class RetryExhaustedError(ResourceError):
    """Raised when retry attempts are exhausted."""

    pass


# Context and session exceptions
class ContextError(BaseGiljoException):
    """Base class for context-related errors."""

    pass


class ContextLimitError(ContextError):
    """Raised when context limits are exceeded."""

    pass


class SessionError(BaseGiljoException):
    """Base class for session-related errors."""

    pass


class SessionExpiredError(SessionError):
    """Raised when a session has expired."""

    pass


# File and path exceptions
class FileSystemError(BaseGiljoException):
    """Base class for file system errors."""

    pass


class FileNotFoundError(FileSystemError):
    """Raised when a required file is not found."""

    pass


class PermissionError(FileSystemError):
    """Raised when file system permissions are insufficient."""

    pass


# Tool and MCP related exceptions
class MCPError(BaseGiljoException):
    """Base class for MCP protocol errors."""

    pass


class ToolError(MCPError):
    """Raised when MCP tool operations fail."""

    pass


class ProtocolError(MCPError):
    """Raised when MCP protocol violations occur."""

    pass


# Vision document exceptions
class VisionError(BaseGiljoException):
    """Base class for vision document errors."""

    pass


class VisionChunkingError(VisionError):
    """Raised when vision document chunking fails."""

    pass


class VisionParsingError(VisionError):
    """Raised when vision document parsing fails."""

    pass


def create_error_from_exception(
    exc: Exception, context: dict = None
) -> BaseGiljoException:
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
    return exception_class(
        message=str(exc), context=context or {"original_type": type(exc).__name__}
    )
