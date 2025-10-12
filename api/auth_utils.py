"""
WebSocket Authentication Utilities (Phase 2 - Unified Auth)

Simplified authentication WITHOUT IP-based auto-login:
- During setup mode: Allow connections without auth (for progress updates)
- After setup: Require credentials for ALL connections (localhost and network treated identically)
"""

import logging
from typing import Any, Optional

from fastapi import WebSocket, WebSocketException
from sqlalchemy.ext.asyncio import AsyncSession


logger = logging.getLogger(__name__)


async def get_setup_state(db: AsyncSession = None) -> dict[str, Any]:
    """
    Get current setup state from database.

    Returns:
        dict with setup_completed flag
    """
    if not db:
        # If no database session, assume setup not completed
        return {'setup_completed': False}

    try:
        from sqlalchemy import select
        from src.giljo_mcp.models import SetupState

        stmt = select(SetupState).where(SetupState.tenant_key == 'default')
        result = await db.execute(stmt)
        setup_state = result.scalar_one_or_none()

        if setup_state:
            return {
                'setup_completed': setup_state.completed,
                'default_password_active': setup_state.default_password_active
            }

        # No setup state found - assume not completed
        return {'setup_completed': False}

    except Exception as e:
        logger.error(f"Failed to get setup state: {e}")
        return {'setup_completed': False}


async def authenticate_websocket(
    websocket: WebSocket,
    db: AsyncSession = None
) -> dict[str, Any]:
    """
    Authenticate WebSocket connection with unified logic.

    Phase 2: NO IP-based auto-login
    - During setup mode: Allow connection without auth (for progress updates)
    - After setup: Require credentials for ALL connections

    Args:
        websocket: WebSocket connection
        db: Optional database session

    Returns:
        dict with authentication result:
            - authenticated: bool
            - context: str (e.g., 'setup')
            - user: dict (if authenticated with credentials)

    Raises:
        WebSocketException: If authentication fails
    """
    # Check setup state
    setup_state = await get_setup_state(db)
    setup_completed = setup_state.get('setup_completed', True)
    default_password_active = setup_state.get('default_password_active', False)

    # Allow connection without auth during:
    # 1. Initial setup (database not initialized)
    # 2. Password change phase (database ready but default password active)
    if not setup_completed:
        logger.info("WebSocket connection allowed: initial setup mode (database not initialized)")
        return {
            'authenticated': True,
            'context': 'setup'
        }

    if default_password_active:
        logger.info("WebSocket connection allowed: password change phase (default password active)")
        return {
            'authenticated': True,
            'context': 'password_change'
        }

    # Post-setup: Require credentials for ALL connections
    # Extract credentials from query params or headers
    token = websocket.query_params.get('token')
    api_key = websocket.query_params.get('api_key')

    # Check headers if not in query params
    if not token and not api_key:
        headers = dict(websocket.headers)
        auth_header = headers.get('authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]  # Remove 'Bearer ' prefix

        api_key = headers.get('x-api-key') or headers.get('x-api-key'.lower())

    # No credentials provided - reject
    if not token and not api_key:
        logger.warning("WebSocket connection rejected: no credentials provided (post-setup)")
        raise WebSocketException(
            code=1008,  # Policy violation
            reason="Authentication required"
        )

    # Validate token (JWT)
    if token:
        validated_user = await validate_jwt_token(token, db)
        if validated_user:
            logger.info(f"WebSocket authenticated via JWT: {validated_user.get('user_id')}")
            return {
                'authenticated': True,
                'user': validated_user
            }

    # Validate API key
    if api_key:
        validated_key = await validate_api_key(api_key, db)
        if validated_key:
            logger.info(f"WebSocket authenticated via API key: {validated_key.get('name')}")
            return {
                'authenticated': True,
                'user': {
                    'user_id': validated_key.get('name'),
                    'tenant_key': validated_key.get('tenant_key', 'default'),
                    'permissions': validated_key.get('permissions', ['*'])
                }
            }

    # Invalid credentials - reject
    logger.warning("WebSocket connection rejected: invalid credentials")
    raise WebSocketException(
        code=1008,  # Policy violation
        reason="Invalid credentials"
    )


async def validate_jwt_token(token: str, db: AsyncSession = None) -> Optional[dict[str, Any]]:
    """
    Validate JWT token.

    Args:
        token: JWT token string
        db: Optional database session

    Returns:
        User info dict if valid, None otherwise
    """
    try:
        from src.giljo_mcp.auth.jwt_manager import JWTManager

        # Decode and validate token
        payload = JWTManager.validate_access_token(token)
        if not payload:
            return None

        return {
            'user_id': payload.get('username'),
            'tenant_key': payload.get('tenant_key', 'default'),
            'role': payload.get('role'),
            'permissions': ['*']  # JWT users have full permissions
        }

    except Exception as e:
        logger.error(f"JWT validation failed: {e}")
        return None


async def validate_api_key(api_key: str, db: AsyncSession = None) -> Optional[dict[str, Any]]:
    """
    Validate API key.

    Args:
        api_key: API key string
        db: Optional database session

    Returns:
        Key info dict if valid, None otherwise
    """
    if not db:
        logger.warning("API key validation requires database session")
        return None

    try:
        from sqlalchemy import select
        from src.giljo_mcp.models import APIKey
        import bcrypt

        # Hash the provided API key to match stored hash
        stmt = select(APIKey).where(APIKey.is_active == True)
        result = await db.execute(stmt)
        api_keys = result.scalars().all()

        # Check each active key
        for key in api_keys:
            if bcrypt.checkpw(api_key.encode('utf-8'), key.key_hash.encode('utf-8')):
                # Key is valid
                return {
                    'name': key.name,
                    'tenant_key': key.tenant_key,
                    'permissions': key.permissions or ['*']
                }

        return None

    except Exception as e:
        logger.error(f"API key validation failed: {e}")
        return None


def check_subscription_permission(
    auth_context: dict[str, Any],
    entity_type: str,
    entity_id: str,
    tenant_key: Optional[str] = None
) -> bool:
    """
    Check if a WebSocket client has permission to subscribe to an entity.

    Multi-tenant isolation:
    - Clients can only subscribe to entities in their tenant
    - During setup mode (context='setup'), allow all subscriptions
    - Check user permissions for fine-grained access control

    Args:
        auth_context: Authentication context from WebSocket connection
        entity_type: Type of entity (e.g., 'project', 'agent', 'message')
        entity_id: ID of the entity
        tenant_key: Tenant key of the entity (for multi-tenant isolation)

    Returns:
        True if subscription is allowed, False otherwise
    """
    # Setup mode: Allow all subscriptions (no tenant isolation during setup)
    if auth_context.get('context') == 'setup':
        return True

    # No auth context: Deny (shouldn't happen if authenticate_websocket was called)
    if not auth_context:
        logger.warning(f"Subscription denied: no auth context for {entity_type}:{entity_id}")
        return False

    # Get user info from auth context
    user_info = auth_context.get('user', {})
    user_tenant_key = user_info.get('tenant_key', 'default')

    # Multi-tenant isolation: Check tenant_key match
    if tenant_key and user_tenant_key != tenant_key:
        logger.warning(
            f"Subscription denied: tenant mismatch "
            f"(user: {user_tenant_key}, entity: {tenant_key}) "
            f"for {entity_type}:{entity_id}"
        )
        return False

    # Check permissions (if implemented)
    user_permissions = user_info.get('permissions', [])

    # Wildcard permission grants all access
    if '*' in user_permissions:
        return True

    # Entity-specific permissions (future enhancement)
    # For now, all authenticated users in the same tenant can subscribe
    # Future: Check for specific permissions like 'read:projects', 'read:agents', etc.

    return True
