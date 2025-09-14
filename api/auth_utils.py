"""
WebSocket Authentication Utilities
Critical security fix for WebSocket authentication vulnerability
"""
from typing import Dict, Optional, Any
from dataclasses import dataclass
from fastapi import WebSocket, HTTPException
import logging

logger = logging.getLogger(__name__)


@dataclass
class AuthResult:
    """Authentication result with context"""
    is_valid: bool
    context: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


async def extract_credentials(
    websocket: WebSocket,
    api_key: Optional[str],
    token: Optional[str]
) -> Dict[str, Any]:
    """
    Extract authentication credentials from query params or headers
    
    Priority:
    1. Query parameters (most compatible)
    2. Headers (if client supports)
    """
    
    # Priority 1: Query parameters
    if api_key:
        logger.debug(f"Found API key in query params")
        return {"type": "api_key", "value": api_key}
    
    if token:
        logger.debug(f"Found JWT token in query params")
        return {"type": "jwt", "value": token}
    
    # Priority 2: Headers (if client supports)
    headers = dict(websocket.headers)
    
    # Check API Key header (case-insensitive)
    for header_name, header_value in headers.items():
        if header_name.lower() == "x-api-key":
            logger.debug(f"Found API key in headers")
            return {"type": "api_key", "value": header_value}
    
    # Check Bearer token
    auth_header = headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        logger.debug(f"Found JWT token in Authorization header")
        return {"type": "jwt", "value": auth_header[7:]}
    
    logger.warning("No authentication credentials found")
    return {"type": "none", "value": None}


async def validate_websocket_auth(
    credentials: Dict[str, Any],
    auth_manager: Any
) -> AuthResult:
    """
    Validate credentials using AuthManager
    
    Returns AuthResult with validation status and context
    """
    
    if not auth_manager:
        logger.error("AuthManager not available")
        return AuthResult(
            is_valid=False,
            error_message="Authentication service unavailable"
        )
    
    # No credentials provided
    if credentials["type"] == "none":
        # Check if auth is required
        if auth_manager.is_enabled():
            return AuthResult(
                is_valid=False,
                error_message="Authentication required"
            )
        else:
            # Auth disabled, allow connection (for development)
            logger.warning("WebSocket connection without auth (auth disabled)")
            return AuthResult(
                is_valid=True,
                context={
                    "tenant_key": "default",
                    "permissions": ["*"],
                    "auth_type": "none",
                    "warning": "Authentication disabled"
                }
            )
    
    # API Key authentication
    if credentials["type"] == "api_key":
        try:
            is_valid = await auth_manager.validate_api_key(credentials["value"])
            
            if is_valid:
                # Get key details from database
                # TODO: Enhance AuthManager to return key details
                return AuthResult(
                    is_valid=True,
                    context={
                        "tenant_key": "default",  # TODO: Get from key info
                        "permissions": ["read:*", "write:*"],  # TODO: Get from key info
                        "auth_type": "api_key",
                        "key_id": credentials["value"][:8] + "..."
                    }
                )
            else:
                return AuthResult(
                    is_valid=False,
                    error_message="Invalid API key"
                )
                
        except Exception as e:
            logger.error(f"Error validating API key: {e}")
            return AuthResult(
                is_valid=False,
                error_message="Authentication error"
            )
    
    # JWT Token authentication
    elif credentials["type"] == "jwt":
        try:
            token_data = auth_manager.validate_jwt_token(credentials["value"])
            
            if token_data:
                return AuthResult(
                    is_valid=True,
                    context={
                        "tenant_key": token_data.get("tenant_key", "default"),
                        "user_id": token_data.get("sub"),
                        "permissions": token_data.get("permissions", ["read:*"]),
                        "auth_type": "jwt",
                        "exp": token_data.get("exp")
                    }
                )
            else:
                return AuthResult(
                    is_valid=False,
                    error_message="Invalid or expired token"
                )
                
        except Exception as e:
            logger.error(f"Error validating JWT token: {e}")
            return AuthResult(
                is_valid=False,
                error_message="Token validation error"
            )
    
    return AuthResult(
        is_valid=False,
        error_message="Unknown authentication type"
    )


def check_subscription_permission(
    auth_context: Dict[str, Any],
    entity_type: str,
    entity_id: str,
    tenant_key: Optional[str] = None
) -> bool:
    """
    Check if authenticated user can subscribe to entity
    
    Enforces:
    1. Tenant isolation
    2. Permission checks
    """
    
    if not auth_context:
        return False
    
    # Check tenant isolation
    user_tenant = auth_context.get("tenant_key")
    if tenant_key and user_tenant != tenant_key:
        logger.warning(
            f"Tenant isolation violation: user tenant {user_tenant} "
            f"attempted to access tenant {tenant_key}"
        )
        return False
    
    # Check permissions
    permissions = auth_context.get("permissions", [])
    
    # Check for wildcard permission
    if "*" in permissions or "read:*" in permissions:
        return True
    
    # Check specific permission
    required_permission = f"read:{entity_type}"
    if required_permission in permissions:
        return True
    
    logger.debug(
        f"Permission denied: {required_permission} not in {permissions}"
    )
    return False


def get_websocket_close_code(error_type: str) -> int:
    """
    Get appropriate WebSocket close code for error type
    
    Reference: https://developer.mozilla.org/en-US/docs/Web/API/CloseEvent
    """
    close_codes = {
        "unauthorized": 1008,  # Policy Violation
        "invalid_format": 1003,  # Unsupported Data
        "server_error": 1011,  # Internal Error
        "normal": 1000,  # Normal Closure
    }
    return close_codes.get(error_type, 1008)