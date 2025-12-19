# Handover 1014: Security Event Auditing

**Date**: 2025-12-18
**Status**: Pending (Future)
**Parent**: 1000 (Greptile Remediation)
**Risk**: LOW
**Tier**: 1 (Auto-Execute)
**Effort**: 8 hours
**Phase**: 5 (Monitoring - Future Work)

## Mission

Implement comprehensive security event auditing to log authentication, authorization, and sensitive operations for compliance and security monitoring.

## Overview

Add security event auditing capabilities to track all security-relevant events in the system, including authentication attempts, authorization decisions, and sensitive data operations.

**Key Goals**:
- Log all authentication and authorization events
- Track sensitive data access and modifications
- Create queryable audit trail for compliance
- Implement retention and cleanup policies
- Minimize performance impact

## Pre-Implementation Research

### 1. Identify Security-Relevant Events

**Authentication Events**:
- Login success/failure
- Logout
- Password change
- Password reset request
- Token refresh/revocation
- Session invalidation
- Multi-factor authentication

**Authorization Events**:
- Permission denied (403)
- Role changes
- Admin privilege escalation
- API key generation/revocation

**Data Access Events**:
- Sensitive data viewed (user data, credentials, API keys)
- Export operations (CSV, JSON exports)
- Bulk operations (mass updates, deletions)
- Configuration changes

**System Events**:
- User creation/deletion
- Product/project deletion
- Database schema changes
- Security settings modifications

### 2. Design Audit Log Schema

**Storage Requirements**:
- Fast writes (high-volume logging)
- Efficient queries by time range, actor, event type
- Support for multi-tenant isolation
- Compliance retention (90 days minimum)

**Performance Considerations**:
- Async logging to avoid blocking requests
- Batch inserts for high-volume events
- Indexed columns for common queries
- Partitioning for large datasets

### 3. Determine Retention Policy

**Retention Tiers**:
- Critical events (auth failures, privilege escalation): 1 year
- Standard events (logins, data access): 90 days
- Low-priority events (routine operations): 30 days

**Cleanup Strategy**:
- Automated cleanup job (daily)
- Archive before deletion (optional)
- Respect tenant-specific retention policies

## Database Schema

### AuditLog Table

```python
class AuditLog(Base):
    """Security event audit log."""
    __tablename__ = "audit_logs"

    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    timestamp = Column(DateTime(timezone=True), default=datetime.utcnow, index=True)

    # Event classification
    event_type = Column(String(50), nullable=False, index=True)
    # Event types: authentication, authorization, data_access, system, configuration

    # Actor information
    actor_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    actor_type = Column(String(20), nullable=False)  # user, system, agent, anonymous
    actor_name = Column(String(100))  # Cached for query performance

    # Request context
    ip_address = Column(String(45))  # IPv6 max length
    user_agent = Column(String(500))
    request_id = Column(String(36))  # Correlation ID

    # Resource information
    resource_type = Column(String(50))  # user, product, project, agent_job, etc.
    resource_id = Column(String(100))

    # Action and outcome
    action = Column(String(50), nullable=False)  # login, create, update, delete, view, etc.
    outcome = Column(String(20), nullable=False, index=True)  # success, failure, denied

    # Additional context
    details = Column(JSONB)  # Flexible field for event-specific data

    # Multi-tenant isolation
    tenant_key = Column(String(50), nullable=False, index=True)

    # Indexes for common queries
    __table_args__ = (
        Index('idx_audit_tenant_timestamp', 'tenant_key', 'timestamp'),
        Index('idx_audit_actor_timestamp', 'actor_id', 'timestamp'),
        Index('idx_audit_event_outcome', 'event_type', 'outcome'),
    )
```

### Example Audit Entries

```json
// Login success
{
  "event_type": "authentication",
  "actor_id": "uuid",
  "actor_type": "user",
  "action": "login",
  "outcome": "success",
  "ip_address": "192.168.1.100",
  "details": {
    "method": "password"
  }
}

// Permission denied
{
  "event_type": "authorization",
  "actor_id": "uuid",
  "actor_type": "user",
  "action": "delete_product",
  "outcome": "denied",
  "resource_type": "product",
  "resource_id": "product-uuid",
  "details": {
    "required_role": "admin",
    "actual_role": "user"
  }
}

// Data export
{
  "event_type": "data_access",
  "actor_id": "uuid",
  "actor_type": "user",
  "action": "export",
  "outcome": "success",
  "resource_type": "project",
  "details": {
    "format": "csv",
    "row_count": 150
  }
}
```

## Implementation

### 1. Audit Service

**File**: `src/giljo_mcp/services/audit_service.py`

```python
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from uuid import UUID

from ..models.audit import AuditLog

class AuditService:
    """Service for security event auditing."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def log_event(
        self,
        event_type: str,
        actor_id: Optional[UUID],
        actor_type: str,
        action: str,
        outcome: str,
        tenant_key: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> AuditLog:
        """
        Log a security event.

        Args:
            event_type: Type of event (authentication, authorization, data_access, system, configuration)
            actor_id: UUID of actor (user, agent, etc.)
            actor_type: Type of actor (user, system, agent, anonymous)
            action: Action performed (login, create, update, delete, view, etc.)
            outcome: Result (success, failure, denied)
            tenant_key: Tenant isolation key
            resource_type: Type of resource affected (optional)
            resource_id: ID of resource affected (optional)
            ip_address: Client IP address (optional)
            user_agent: Client user agent (optional)
            request_id: Correlation ID (optional)
            details: Additional event-specific data (optional)

        Returns:
            Created AuditLog entry
        """
        audit_entry = AuditLog(
            event_type=event_type,
            actor_id=actor_id,
            actor_type=actor_type,
            action=action,
            outcome=outcome,
            tenant_key=tenant_key,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
            details=details or {}
        )

        self.session.add(audit_entry)
        await self.session.commit()
        await self.session.refresh(audit_entry)

        return audit_entry

    async def query_events(
        self,
        tenant_key: str,
        event_type: Optional[str] = None,
        actor_id: Optional[UUID] = None,
        outcome: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> list[AuditLog]:
        """
        Query audit log events.

        Args:
            tenant_key: Tenant isolation key
            event_type: Filter by event type (optional)
            actor_id: Filter by actor (optional)
            outcome: Filter by outcome (optional)
            start_time: Filter by start timestamp (optional)
            end_time: Filter by end timestamp (optional)
            limit: Maximum results (default: 100)

        Returns:
            List of matching audit entries
        """
        query = select(AuditLog).where(AuditLog.tenant_key == tenant_key)

        if event_type:
            query = query.where(AuditLog.event_type == event_type)
        if actor_id:
            query = query.where(AuditLog.actor_id == actor_id)
        if outcome:
            query = query.where(AuditLog.outcome == outcome)
        if start_time:
            query = query.where(AuditLog.timestamp >= start_time)
        if end_time:
            query = query.where(AuditLog.timestamp <= end_time)

        query = query.order_by(AuditLog.timestamp.desc()).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def cleanup_old_entries(
        self,
        tenant_key: str,
        retention_days: int = 90
    ) -> int:
        """
        Delete audit entries older than retention period.

        Args:
            tenant_key: Tenant isolation key
            retention_days: Days to retain (default: 90)

        Returns:
            Number of entries deleted
        """
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)

        stmt = delete(AuditLog).where(
            AuditLog.tenant_key == tenant_key,
            AuditLog.timestamp < cutoff_date
        )

        result = await self.session.execute(stmt)
        await self.session.commit()

        return result.rowcount
```

### 2. Audit Middleware

**File**: `api/middleware/audit.py`

```python
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable
import uuid

class AuditMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add request context for auditing.
    Adds request_id and extracts IP/user-agent for audit logs.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate correlation ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        # Extract client information
        request.state.ip_address = request.client.host if request.client else None
        request.state.user_agent = request.headers.get("user-agent")

        # Add to response headers for debugging
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id

        return response
```

### 3. Usage in Authentication

**File**: `api/endpoints/auth.py` (modifications)

```python
from fastapi import Depends, Request, HTTPException
from ..dependencies import get_audit_service
from src.giljo_mcp.services.audit_service import AuditService

@router.post("/login")
async def login(
    credentials: LoginRequest,
    request: Request,
    audit: AuditService = Depends(get_audit_service)
):
    """Login endpoint with audit logging."""
    try:
        # Authenticate user
        user = await authenticate(credentials)

        # Log success
        await audit.log_event(
            event_type="authentication",
            actor_id=user.id,
            actor_type="user",
            action="login",
            outcome="success",
            tenant_key=user.tenant_key,
            ip_address=request.state.ip_address,
            user_agent=request.state.user_agent,
            request_id=request.state.request_id
        )

        return {"token": create_token(user)}

    except AuthenticationError as e:
        # Log failure
        await audit.log_event(
            event_type="authentication",
            actor_id=None,
            actor_type="anonymous",
            action="login",
            outcome="failure",
            tenant_key="system",  # No tenant context for failed logins
            ip_address=request.state.ip_address,
            user_agent=request.state.user_agent,
            request_id=request.state.request_id,
            details={"username": credentials.username, "reason": str(e)}
        )
        raise HTTPException(status_code=401, detail="Invalid credentials")

@router.post("/logout")
async def logout(
    request: Request,
    current_user: User = Depends(get_current_user),
    audit: AuditService = Depends(get_audit_service)
):
    """Logout endpoint with audit logging."""
    # Invalidate session/token
    await invalidate_session(current_user)

    # Log logout
    await audit.log_event(
        event_type="authentication",
        actor_id=current_user.id,
        actor_type="user",
        action="logout",
        outcome="success",
        tenant_key=current_user.tenant_key,
        ip_address=request.state.ip_address,
        request_id=request.state.request_id
    )

    return {"message": "Logged out successfully"}
```

### 4. Usage in Authorization

**File**: `api/dependencies.py` (modifications)

```python
async def require_admin(
    request: Request,
    current_user: User = Depends(get_current_user),
    audit: AuditService = Depends(get_audit_service)
) -> User:
    """Dependency to require admin role with audit logging."""
    if not current_user.is_admin:
        # Log authorization failure
        await audit.log_event(
            event_type="authorization",
            actor_id=current_user.id,
            actor_type="user",
            action="admin_access",
            outcome="denied",
            tenant_key=current_user.tenant_key,
            ip_address=request.state.ip_address,
            request_id=request.state.request_id,
            details={
                "required_role": "admin",
                "actual_role": "user",
                "path": request.url.path
            }
        )
        raise HTTPException(status_code=403, detail="Admin access required")

    return current_user
```

### 5. Cleanup Job

**File**: `src/giljo_mcp/jobs/audit_cleanup.py`

```python
import asyncio
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_session
from ..services.audit_service import AuditService
from ..models import Tenant

async def cleanup_audit_logs():
    """
    Scheduled job to clean up old audit logs.
    Runs daily to enforce retention policies.
    """
    async with get_session() as session:
        # Get all tenants
        tenants = await session.execute(select(Tenant))

        for tenant in tenants.scalars().all():
            audit_service = AuditService(session)

            # Use tenant-specific retention or default to 90 days
            retention_days = tenant.settings.get("audit_retention_days", 90)

            deleted_count = await audit_service.cleanup_old_entries(
                tenant_key=tenant.tenant_key,
                retention_days=retention_days
            )

            print(f"[{datetime.utcnow()}] Cleaned up {deleted_count} audit entries for tenant {tenant.tenant_key}")

if __name__ == "__main__":
    asyncio.run(cleanup_audit_logs())
```

## Files to Modify

### New Files
1. `src/giljo_mcp/models/audit.py` - AuditLog model
2. `src/giljo_mcp/services/audit_service.py` - Audit service
3. `api/middleware/audit.py` - Audit middleware
4. `src/giljo_mcp/jobs/audit_cleanup.py` - Cleanup job
5. `tests/services/test_audit_service.py` - Service tests
6. `tests/integration/test_audit_logging.py` - Integration tests

### Modified Files
1. `api/endpoints/auth.py` - Add audit calls to auth endpoints
2. `api/dependencies.py` - Add audit calls to authorization checks
3. `api/app.py` - Register audit middleware
4. `src/giljo_mcp/models/__init__.py` - Import AuditLog

## Testing Strategy

### Unit Tests

**File**: `tests/services/test_audit_service.py`

```python
import pytest
from datetime import datetime, timedelta
from src.giljo_mcp.services.audit_service import AuditService

@pytest.mark.asyncio
async def test_log_event(db_session):
    """Test basic event logging."""
    audit = AuditService(db_session)

    entry = await audit.log_event(
        event_type="authentication",
        actor_id=uuid4(),
        actor_type="user",
        action="login",
        outcome="success",
        tenant_key="tenant_abc"
    )

    assert entry.id is not None
    assert entry.event_type == "authentication"
    assert entry.outcome == "success"

@pytest.mark.asyncio
async def test_query_events_by_type(db_session):
    """Test querying events by type."""
    audit = AuditService(db_session)

    # Log multiple events
    await audit.log_event("authentication", None, "user", "login", "success", "tenant_abc")
    await audit.log_event("authorization", None, "user", "access", "denied", "tenant_abc")

    # Query auth events
    events = await audit.query_events("tenant_abc", event_type="authentication")
    assert len(events) == 1
    assert events[0].event_type == "authentication"

@pytest.mark.asyncio
async def test_cleanup_old_entries(db_session):
    """Test cleanup of old audit entries."""
    audit = AuditService(db_session)

    # Create old entry (91 days ago)
    old_entry = AuditLog(
        event_type="test",
        actor_type="user",
        action="test",
        outcome="success",
        tenant_key="tenant_abc",
        timestamp=datetime.utcnow() - timedelta(days=91)
    )
    db_session.add(old_entry)
    await db_session.commit()

    # Cleanup (90 day retention)
    deleted = await audit.cleanup_old_entries("tenant_abc", retention_days=90)
    assert deleted == 1
```

### Integration Tests

**File**: `tests/integration/test_audit_logging.py`

```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_login_audit_success(client: AsyncClient, db_session):
    """Test successful login creates audit entry."""
    response = await client.post("/api/auth/login", json={
        "username": "testuser",
        "password": "password123"
    })

    assert response.status_code == 200

    # Verify audit entry
    audit = AuditService(db_session)
    events = await audit.query_events("tenant_abc", event_type="authentication")
    assert len(events) == 1
    assert events[0].action == "login"
    assert events[0].outcome == "success"

@pytest.mark.asyncio
async def test_login_audit_failure(client: AsyncClient, db_session):
    """Test failed login creates audit entry."""
    response = await client.post("/api/auth/login", json={
        "username": "testuser",
        "password": "wrongpassword"
    })

    assert response.status_code == 401

    # Verify audit entry
    audit = AuditService(db_session)
    events = await audit.query_events("system", event_type="authentication", outcome="failure")
    assert len(events) == 1
    assert events[0].action == "login"
    assert events[0].outcome == "failure"

@pytest.mark.asyncio
async def test_admin_access_denied_audit(client: AsyncClient, db_session):
    """Test admin access denial creates audit entry."""
    # Login as regular user
    login_response = await client.post("/api/auth/login", json={
        "username": "regularuser",
        "password": "password123"
    })
    token = login_response.json()["token"]

    # Try to access admin endpoint
    response = await client.get(
        "/api/admin/settings",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 403

    # Verify audit entry
    audit = AuditService(db_session)
    events = await audit.query_events("tenant_abc", event_type="authorization", outcome="denied")
    assert len(events) == 1
    assert events[0].action == "admin_access"
```

## Verification Checklist

### Functionality
- [ ] All authentication events logged (login, logout, password change)
- [ ] All authorization failures logged (permission denied, role checks)
- [ ] Sensitive data access logged (user data, exports, bulk ops)
- [ ] System events logged (config changes, user management)
- [ ] Query API works (filter by type, actor, time range)
- [ ] Cleanup job removes old entries

### Security
- [ ] No sensitive data in logs (passwords, tokens, etc.)
- [ ] Multi-tenant isolation enforced
- [ ] IP addresses captured for forensics
- [ ] Request correlation IDs present
- [ ] Tamper-resistant (append-only pattern)

### Performance
- [ ] Logging doesn't block requests (async)
- [ ] Query performance acceptable (<100ms for common queries)
- [ ] Indexes cover common query patterns
- [ ] Cleanup job completes in reasonable time

### Compliance
- [ ] Retention policy configurable per tenant
- [ ] Audit trail covers all security-relevant events
- [ ] Logs queryable for compliance reporting
- [ ] Timestamps use UTC

## Cascade Risk

**Risk Level**: LOW

**Potential Impacts**:
- Database schema change (new table, indexes)
- Middleware addition affects all requests (minimal overhead)
- Service layer dependency injection (non-breaking)

**Mitigation**:
- Audit logging is additive (doesn't change existing logic)
- Async logging prevents blocking
- Migration tested before deployment
- Feature can be disabled via config if issues arise

## Success Criteria

1. **Complete Coverage**: All security events captured (authentication, authorization, data access, system)
2. **Queryability**: Audit logs searchable by event type, actor, time range, outcome
3. **Compliance Ready**: Audit trail meets compliance requirements (retention, completeness, integrity)
4. **Performance**: Minimal impact on request latency (<5ms overhead)
5. **Maintainability**: Clear event types, standardized details format, automated cleanup

## Next Steps

1. Review schema with DBA
2. Implement AuditLog model and service
3. Add middleware and update endpoints
4. Write comprehensive tests
5. Deploy migration
6. Monitor performance
7. Document query patterns for compliance reporting

---

**Dependencies**: 1001 (Input Validation), 1002 (API Key Security)
**Blocks**: None
**Related**: 1015 (Rate Limiting - also uses request middleware)
