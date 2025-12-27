"""
Error Codes for Structured Logging

Provides standardized error codes for better observability and debugging.

Format: [COMPONENT][NUMBER]
- AUTH001-099: Authentication/authorization errors
- DB001-099: Database errors
- WS001-099: WebSocket errors
- MCP001-099: MCP tool/agent errors
- API001-099: API/request errors

Usage:
    from giljo_mcp.logging import logger, ErrorCode

    logger.error(
        "authentication_failed",
        error_code=ErrorCode.AUTH_INVALID_CREDENTIALS.value,
        user_id=user_id,
        ip_address=request.client.host
    )
"""

from enum import Enum


class ErrorCode(str, Enum):
    """Standardized error codes for structured logging"""

    # ============================================================================
    # AUTH (001-099): Authentication & Authorization Errors
    # ============================================================================

    AUTH_INVALID_CREDENTIALS = "AUTH001"  # Invalid username/password
    AUTH_TOKEN_EXPIRED = "AUTH002"  # JWT token expired
    AUTH_TOKEN_INVALID = "AUTH003"  # JWT token malformed/invalid
    AUTH_UNAUTHORIZED = "AUTH004"  # User not authorized for resource
    AUTH_SESSION_EXPIRED = "AUTH005"  # Session timeout
    AUTH_PIN_INVALID = "AUTH006"  # Password recovery PIN invalid
    AUTH_PIN_EXPIRED = "AUTH007"  # Password recovery PIN expired
    AUTH_RATE_LIMIT_EXCEEDED = "AUTH008"  # Too many auth attempts
    AUTH_USER_NOT_FOUND = "AUTH009"  # User account not found
    AUTH_TENANT_MISMATCH = "AUTH010"  # Tenant isolation violation
    AUTH_CSRF_VALIDATION_FAILED = "AUTH011"  # CSRF token validation failed

    # ============================================================================
    # DB (001-099): Database Errors
    # ============================================================================

    DB_CONNECTION_FAILED = "DB001"  # Database connection error
    DB_QUERY_TIMEOUT = "DB002"  # Query execution timeout
    DB_TRANSACTION_ROLLBACK = "DB003"  # Transaction rolled back
    DB_CONSTRAINT_VIOLATION = "DB004"  # Unique/foreign key violation
    DB_RECORD_NOT_FOUND = "DB005"  # Requested record doesn't exist
    DB_DUPLICATE_ENTRY = "DB006"  # Duplicate key error
    DB_MIGRATION_FAILED = "DB007"  # Database migration error
    DB_POOL_EXHAUSTED = "DB008"  # Connection pool exhausted
    DB_DEADLOCK_DETECTED = "DB009"  # Database deadlock
    DB_INTEGRITY_ERROR = "DB010"  # Data integrity violation

    # ============================================================================
    # WS (001-099): WebSocket Errors
    # ============================================================================

    WS_CONNECTION_FAILED = "WS001"  # WebSocket connection failed
    WS_MESSAGE_SEND_FAILED = "WS002"  # Failed to send message
    WS_MESSAGE_PARSE_FAILED = "WS003"  # Failed to parse incoming message
    WS_AUTHENTICATION_FAILED = "WS004"  # WebSocket auth failed
    WS_TENANT_ISOLATION_VIOLATED = "WS005"  # Cross-tenant message attempt
    WS_BROADCAST_FAILED = "WS006"  # Broadcast to tenant failed
    WS_DISCONNECTED_UNEXPECTEDLY = "WS007"  # Client disconnected unexpectedly
    WS_SUBSCRIPTION_FAILED = "WS008"  # Failed to subscribe to events
    WS_HEARTBEAT_TIMEOUT = "WS009"  # Client heartbeat timeout

    # ============================================================================
    # MCP (001-099): MCP Tool & Agent Errors
    # ============================================================================

    MCP_TOOL_EXECUTION_ERROR = "MCP001"  # MCP tool execution failed
    MCP_AGENT_SPAWN_FAILED = "MCP002"  # Failed to spawn agent job
    MCP_CONTEXT_FETCH_FAILED = "MCP003"  # Failed to fetch context
    MCP_MISSION_NOT_FOUND = "MCP004"  # Agent mission not found
    MCP_ORCHESTRATOR_ERROR = "MCP005"  # Orchestrator execution error
    MCP_SUCCESSION_FAILED = "MCP006"  # Orchestrator succession failed
    MCP_AGENT_NOT_FOUND = "MCP007"  # Agent job not found
    MCP_INVALID_TENANT = "MCP008"  # Invalid tenant_key for MCP operation
    MCP_TOOL_SCHEMA_INVALID = "MCP009"  # MCP tool schema validation failed
    MCP_SESSION_EXPIRED = "MCP010"  # MCP session expired
    MCP_HTTP_TRANSPORT_ERROR = "MCP011"  # MCP-over-HTTP transport error

    # ============================================================================
    # API (001-099): API & Request Errors
    # ============================================================================

    API_VALIDATION_ERROR = "API001"  # Request validation failed
    API_RATE_LIMIT_EXCEEDED = "API002"  # Rate limit exceeded
    API_RESOURCE_NOT_FOUND = "API003"  # Resource not found (404)
    API_METHOD_NOT_ALLOWED = "API004"  # HTTP method not allowed
    API_INTERNAL_ERROR = "API005"  # Internal server error (500)
    API_BAD_REQUEST = "API006"  # Malformed request (400)
    API_TIMEOUT = "API007"  # Request timeout
    API_PAYLOAD_TOO_LARGE = "API008"  # Request payload exceeds limit
    API_UNSUPPORTED_MEDIA_TYPE = "API009"  # Unsupported content type
    API_CONFLICT = "API010"  # Resource conflict (409)
    API_DEPENDENCY_FAILED = "API011"  # External service dependency failed

    def __str__(self) -> str:
        """Return the error code value"""
        return self.value


# Convenience mapping for quick lookups
ERROR_CODE_DESCRIPTIONS = {
    # AUTH
    ErrorCode.AUTH_INVALID_CREDENTIALS: "Invalid username or password",
    ErrorCode.AUTH_TOKEN_EXPIRED: "JWT token has expired",
    ErrorCode.AUTH_TOKEN_INVALID: "JWT token is malformed or invalid",
    ErrorCode.AUTH_UNAUTHORIZED: "User not authorized for this resource",
    ErrorCode.AUTH_SESSION_EXPIRED: "User session has expired",
    ErrorCode.AUTH_PIN_INVALID: "Password recovery PIN is invalid",
    ErrorCode.AUTH_PIN_EXPIRED: "Password recovery PIN has expired",
    ErrorCode.AUTH_RATE_LIMIT_EXCEEDED: "Too many authentication attempts",
    ErrorCode.AUTH_USER_NOT_FOUND: "User account not found",
    ErrorCode.AUTH_TENANT_MISMATCH: "Tenant isolation violation detected",
    ErrorCode.AUTH_CSRF_VALIDATION_FAILED: "CSRF token validation failed",

    # DB
    ErrorCode.DB_CONNECTION_FAILED: "Failed to connect to database",
    ErrorCode.DB_QUERY_TIMEOUT: "Database query execution timeout",
    ErrorCode.DB_TRANSACTION_ROLLBACK: "Database transaction rolled back",
    ErrorCode.DB_CONSTRAINT_VIOLATION: "Database constraint violation",
    ErrorCode.DB_RECORD_NOT_FOUND: "Requested database record not found",
    ErrorCode.DB_DUPLICATE_ENTRY: "Duplicate entry in database",
    ErrorCode.DB_MIGRATION_FAILED: "Database migration failed",
    ErrorCode.DB_POOL_EXHAUSTED: "Database connection pool exhausted",
    ErrorCode.DB_DEADLOCK_DETECTED: "Database deadlock detected",
    ErrorCode.DB_INTEGRITY_ERROR: "Data integrity violation",

    # WS
    ErrorCode.WS_CONNECTION_FAILED: "WebSocket connection failed",
    ErrorCode.WS_MESSAGE_SEND_FAILED: "Failed to send WebSocket message",
    ErrorCode.WS_MESSAGE_PARSE_FAILED: "Failed to parse WebSocket message",
    ErrorCode.WS_AUTHENTICATION_FAILED: "WebSocket authentication failed",
    ErrorCode.WS_TENANT_ISOLATION_VIOLATED: "Cross-tenant WebSocket message attempt",
    ErrorCode.WS_BROADCAST_FAILED: "Failed to broadcast to tenant",
    ErrorCode.WS_DISCONNECTED_UNEXPECTEDLY: "Client disconnected unexpectedly",
    ErrorCode.WS_SUBSCRIPTION_FAILED: "Failed to subscribe to events",
    ErrorCode.WS_HEARTBEAT_TIMEOUT: "Client heartbeat timeout",

    # MCP
    ErrorCode.MCP_TOOL_EXECUTION_ERROR: "MCP tool execution failed",
    ErrorCode.MCP_AGENT_SPAWN_FAILED: "Failed to spawn MCP agent job",
    ErrorCode.MCP_CONTEXT_FETCH_FAILED: "Failed to fetch context via MCP",
    ErrorCode.MCP_MISSION_NOT_FOUND: "Agent mission not found",
    ErrorCode.MCP_ORCHESTRATOR_ERROR: "Orchestrator execution error",
    ErrorCode.MCP_SUCCESSION_FAILED: "Orchestrator succession failed",
    ErrorCode.MCP_AGENT_NOT_FOUND: "Agent job not found",
    ErrorCode.MCP_INVALID_TENANT: "Invalid tenant_key for MCP operation",
    ErrorCode.MCP_TOOL_SCHEMA_INVALID: "MCP tool schema validation failed",
    ErrorCode.MCP_SESSION_EXPIRED: "MCP session expired",
    ErrorCode.MCP_HTTP_TRANSPORT_ERROR: "MCP-over-HTTP transport error",

    # API
    ErrorCode.API_VALIDATION_ERROR: "Request validation failed",
    ErrorCode.API_RATE_LIMIT_EXCEEDED: "API rate limit exceeded",
    ErrorCode.API_RESOURCE_NOT_FOUND: "Requested resource not found",
    ErrorCode.API_METHOD_NOT_ALLOWED: "HTTP method not allowed",
    ErrorCode.API_INTERNAL_ERROR: "Internal server error",
    ErrorCode.API_BAD_REQUEST: "Malformed request",
    ErrorCode.API_TIMEOUT: "Request timeout",
    ErrorCode.API_PAYLOAD_TOO_LARGE: "Request payload too large",
    ErrorCode.API_UNSUPPORTED_MEDIA_TYPE: "Unsupported media type",
    ErrorCode.API_CONFLICT: "Resource conflict",
    ErrorCode.API_DEPENDENCY_FAILED: "External service dependency failed",
}


def get_error_description(error_code: ErrorCode) -> str:
    """Get human-readable description for error code"""
    return ERROR_CODE_DESCRIPTIONS.get(error_code, "Unknown error")
