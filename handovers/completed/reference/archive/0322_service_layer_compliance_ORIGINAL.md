# Handover 0322: Service Layer Compliance

## Problem Statement

Only 35-40% of endpoints follow the service-layer-only pattern. Major violations exist in core authentication and user management endpoints, undermining the architectural consistency established by ProductService and ProjectService.

Per Handover 013A Section 4: "Service layer only means your FastAPI endpoints should be very thin and should NOT contain business logic or direct SQL/ORM operations." Current violations create inconsistent patterns, make testing harder, and scatter business logic across the codebase.

## Current State

### Violations Found

#### 1. users.py - No UserService Exists (17 direct DB queries)

The entire users.py endpoint file contains direct database access with no service layer abstraction.

| Line | Description | Impact |
|------|-------------|--------|
| 313-315 | `select(User).where(User.tenant_key...)` for list_users | Multi-tenant logic in endpoint |
| 347-349 | `select(User).where(User.username...)` for duplicate check | Validation logic in endpoint |
| 357-360 | `select(User).where(User.email...)` for duplicate email | Validation logic in endpoint |
| 365-384 | Direct `User()` creation with `db.add()` and `db.commit()` | Business logic in endpoint |
| 416-418 | `select(User).where(User.id...)` for get_user | Query logic in endpoint |
| 461-463 | `select(User).where(User.id...)` for update_user | Query logic in endpoint |
| 476-478 | `select(User).where(User.email...)` for email duplicate | Validation logic in endpoint |
| 486-494 | Direct field updates with `db.commit()` | State mutation in endpoint |
| 526-528 | `select(User).where(User.id...)` for delete_user | Query logic in endpoint |
| 571-573 | `select(User).where(User.id...)` for change_role | Query logic in endpoint |
| 631-633 | `select(User).where(User.id...)` for change_password | Query logic in endpoint |
| 653-654 | Direct `bcrypt.verify()` and `bcrypt.hash()` | Auth logic in endpoint |
| 696-698 | `select(User).where(User.id...)` for reset_password | Query logic in endpoint |
| 705-715 | Direct password hash update with `db.commit()` | State mutation in endpoint |
| 823-824 | Direct `db.commit()` and `db.refresh()` | Transaction control in endpoint |

**Total: 17 direct database operations, 0 service calls**

#### 2. tasks.py - Bypasses Existing TaskService (13 direct DB queries)

TaskService exists at `src/giljo_mcp/services/task_service.py` with methods like `create_task()`, `list_tasks()`, `update_task()`, `complete_task()`, but the endpoint completely ignores it.

| Line | Description | Impact |
|------|-------------|--------|
| 152 | `select(Task).where(Task.tenant_key...)` for list_tasks | Service has `list_tasks()` method |
| 161-165 | `select(Product).where(Product.is_active...)` for active product | Should use ProductService |
| 216-234 | Direct `Task()` creation with `db.add()` | Service has `create_task()` method |
| 249-251 | `select(Task).where(Task.id...)` for get_task | Service method needed |
| 292-294 | `select(Task).where(Task.id...)` for update_task | Service has `update_task()` method |
| 306-314 | Direct status timestamp logic | Business logic in endpoint |
| 345-347 | `select(Task).where(Task.id...)` for delete_task | Service method needed |
| 358 | Direct `await db.delete(task)` | Deletion in endpoint |
| 395-397 | `select(Task).where(Task.id...)` for convert | Conversion logic in endpoint |
| 417-419 | `select(Product).where(Product.is_active...)` | Should use ProductService |
| 431-436 | `select(Project).where(Project.status...)` | Should use ProjectService |
| 501-503 | `select(Task).where(Task.id...)` for status change | Service has `update_task()` |
| 533-537 | `select(Task).where(Task.tenant_key...)` for summary | Service method needed |

**Total: 13 direct database operations despite existing TaskService**

#### 3. auth.py - No AuthenticationService Exists (18 direct DB queries)

Authentication logic is entirely embedded in endpoints with no service abstraction for login, registration, API key management, or password reset flows.

| Line | Description | Impact |
|------|-------------|--------|
| 309-311 | `select(User).where(User.username...)` for login | Auth logic in endpoint |
| 318-320 | Direct `bcrypt.verify()` for password check | Auth logic in endpoint |
| 325-327 | `select(SetupState).where(...)` for setup check | State logic in endpoint |
| 415-417 | Direct `user.last_login` update | State mutation in endpoint |
| 533-539 | `select(APIKey).where(APIKey.user_id...)` for list | Query logic in endpoint |
| 584-597 | Direct `APIKey()` creation with `db.add()` | Business logic in endpoint |
| 632-634 | `select(APIKey).where(APIKey.id...)` for revoke | Query logic in endpoint |
| 640-642 | Direct `api_key.is_active = False` update | State mutation in endpoint |
| 672-674 | `select(User).where(User.tenant_key...)` for list | Query logic in endpoint |
| 715-717 | `select(User).where(User.username...)` for register | Validation in endpoint |
| 725-728 | `select(User).where(User.email...)` for email check | Validation in endpoint |
| 739-752 | Direct `User()` creation with `db.add()` | Business logic in endpoint |
| 819-839 | `select(SetupState).where(...)` for first admin | Security logic in endpoint |
| 844-856 | `func.count(User.id)` for user count | Query logic in endpoint |
| 886 | Direct `bcrypt.hash()` for password | Auth logic in endpoint |
| 892-902 | Direct `User()` creation for first admin | Critical security in endpoint |
| 1013-1030 | Direct `SetupState` creation/update | State mutation in endpoint |

**Total: 18 direct database operations, 0 service calls**

#### 4. messages.py - Direct DB Queries, Uses Legacy tool_accessor

| Line | Description | Impact |
|------|-------------|--------|
| 114-119 | `select(MCPAgentJob).where(...)` for list_messages | Query logic in endpoint |
| 282-287 | `select(MCPAgentJob).where(...)` for broadcast | Query logic in endpoint |
| 45, 173, 207, etc. | Uses `state.tool_accessor.*` methods | Bypasses service layer |

**Note**: MessageService exists at `src/giljo_mcp/services/message_service.py` but is not used by the endpoint.

### Compliant Examples (Reference)

**ProductService pattern** (from `docs/SERVICES.md`):
```python
# api/endpoints/products.py - COMPLIANT
@router.post("/api/products")
async def create_product(
    product_data: ProductCreate,
    session: AsyncSession = Depends(get_db),
    user = Depends(get_current_user)
):
    service = ProductService(session, tenant_key=user.tenant_key)
    product = await service.create_product(product_data)
    return product
```

**TaskService exists but is not used** (`src/giljo_mcp/services/task_service.py`):
```python
class TaskService:
    async def create_task(...) -> dict[str, Any]
    async def list_tasks(...) -> dict[str, Any]
    async def update_task(...) -> dict[str, Any]
    async def complete_task(...) -> dict[str, Any]
```

## Scope

### In Scope

1. **Create UserService** in `src/giljo_mcp/services/user_service.py`
   - All user CRUD operations
   - Password management (change, reset, verify)
   - Role management
   - Field priority and depth config management
   - Multi-tenant isolation

2. **Create AuthenticationService** in `src/giljo_mcp/services/auth_service.py`
   - Login/logout with JWT management
   - API key creation, listing, revocation
   - User registration
   - First admin creation flow
   - Password verification

3. **Migrate users.py** to use UserService
   - All 10+ endpoints to call service methods
   - Remove all direct `select()` and `db.commit()` calls

4. **Migrate tasks.py** to use existing TaskService
   - Extend TaskService with missing methods (get_task, delete_task, convert_to_project, get_summary)
   - All 8 endpoints to call service methods

5. **Migrate auth.py** to use AuthenticationService
   - All 8 endpoints to call service methods

6. **Migrate messages.py** to use MessageService
   - Replace tool_accessor calls with MessageService
   - All 6 endpoints to call service methods

7. **Update tests** to maintain coverage
   - Unit tests for new services
   - Integration tests for migrated endpoints

### Out of Scope

- Frontend changes (no API contract changes)
- Database schema changes
- Performance optimizations
- New features or capabilities
- Other endpoint files not listed above

## Success Criteria

- [ ] UserService created with full user operations (12+ methods)
- [ ] AuthenticationService created with full auth operations (8+ methods)
- [ ] TaskService extended with missing methods (4+ methods)
- [ ] 0 direct `select()` queries in users.py
- [ ] 0 direct `select()` queries in tasks.py
- [ ] 0 direct `select()` queries in auth.py
- [ ] 0 `tool_accessor` calls in messages.py
- [ ] Service layer compliance >80% across all endpoints
- [ ] All existing tests pass
- [ ] New service unit tests added (>80% coverage per service)
- [ ] No API contract changes (frontend compatibility maintained)

## Technical Approach

### Phase 1: UserService (Highest Impact)

**File**: `src/giljo_mcp/services/user_service.py`

**Methods to implement**:
```python
class UserService:
    def __init__(self, session: AsyncSession, tenant_key: str)

    # CRUD
    async def list_users(self) -> list[User]
    async def get_user(self, user_id: str) -> User | None
    async def create_user(self, user_data: UserCreate) -> User
    async def update_user(self, user_id: str, user_data: UserUpdate) -> User
    async def delete_user(self, user_id: str) -> bool  # soft delete

    # Validation
    async def check_username_exists(self, username: str) -> bool
    async def check_email_exists(self, email: str) -> bool

    # Password Management
    async def change_password(self, user_id: str, old_password: str, new_password: str) -> bool
    async def reset_password(self, user_id: str) -> bool
    async def verify_password(self, user: User, password: str) -> bool

    # Role Management
    async def change_role(self, user_id: str, new_role: str) -> User

    # Config Management
    async def get_field_priority_config(self, user_id: str) -> dict
    async def update_field_priority_config(self, user_id: str, config: dict) -> dict
    async def reset_field_priority_config(self, user_id: str) -> dict
    async def get_depth_config(self, user_id: str) -> dict
    async def update_depth_config(self, user_id: str, config: dict) -> dict
```

### Phase 2: AuthenticationService

**File**: `src/giljo_mcp/services/auth_service.py`

**Methods to implement**:
```python
class AuthenticationService:
    def __init__(self, session: AsyncSession)

    # Login/Logout
    async def authenticate(self, username: str, password: str) -> User | None
    async def update_last_login(self, user: User) -> None
    async def get_setup_state(self, tenant_key: str) -> SetupState | None

    # API Key Management
    async def list_api_keys(self, user_id: str, include_revoked: bool = False) -> list[APIKey]
    async def create_api_key(self, user_id: str, tenant_key: str, name: str, permissions: list) -> tuple[APIKey, str]
    async def revoke_api_key(self, key_id: str, user_id: str) -> APIKey | None

    # User Registration
    async def register_user(self, user_data: RegisterUserRequest, admin_tenant_key: str) -> User
    async def create_first_admin(self, user_data: RegisterUserRequest, client_ip: str) -> User
    async def check_first_admin_exists(self) -> bool
    async def get_user_count(self) -> int
    async def mark_first_admin_created(self, tenant_key: str) -> None
```

### Phase 3: Extend TaskService

**File**: `src/giljo_mcp/services/task_service.py` (extend existing)

**Methods to add**:
```python
# Add to existing TaskService class
async def get_task(self, task_id: str) -> Task | None
async def delete_task(self, task_id: str) -> bool
async def convert_to_project(self, task_id: str, project_name: str | None, include_subtasks: bool) -> dict
async def get_task_summary(self, product_id: str | None = None) -> dict
async def change_status(self, task_id: str, new_status: str) -> Task
async def get_active_product(self) -> Product | None  # or use ProductService
```

### Phase 4: Migrate Endpoints

**Migration order** (dependency-driven):
1. UserService + migrate users.py (no dependencies)
2. AuthenticationService + migrate auth.py (depends on User model)
3. Extend TaskService + migrate tasks.py (may use ProductService, ProjectService)
4. Migrate messages.py to use MessageService (independent)

**Endpoint migration pattern**:
```python
# BEFORE (non-compliant)
@router.get("/", response_model=list[UserResponse])
async def list_users(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session)
) -> list[UserResponse]:
    stmt = select(User).where(User.tenant_key == current_user.tenant_key)
    result = await db.execute(stmt)
    users = result.scalars().all()
    return [user_to_response(user) for user in users]

# AFTER (compliant)
@router.get("/", response_model=list[UserResponse])
async def list_users(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session)
) -> list[UserResponse]:
    service = UserService(db, tenant_key=current_user.tenant_key)
    users = await service.list_users()
    return [user_to_response(user) for user in users]
```

### Phase 5: Testing

**Test files to create/update**:
- `tests/services/test_user_service.py` (new)
- `tests/services/test_auth_service.py` (new)
- `tests/services/test_task_service.py` (update existing)
- `tests/services/test_message_service.py` (update existing)
- `tests/api/test_users_api.py` (update for service integration)
- `tests/api/test_auth_api.py` (update for service integration)

## Estimated Effort

| Phase | Task | Estimated Time |
|-------|------|----------------|
| 1 | Create UserService | 4-6 hours |
| 2 | Create AuthenticationService | 4-6 hours |
| 3 | Extend TaskService | 2-3 hours |
| 4a | Migrate users.py (10 endpoints) | 3-4 hours |
| 4b | Migrate auth.py (8 endpoints) | 3-4 hours |
| 4c | Migrate tasks.py (8 endpoints) | 2-3 hours |
| 4d | Migrate messages.py (6 endpoints) | 2-3 hours |
| 5 | Add/update tests | 4-6 hours |
| | **Total** | **24-35 hours** |

**Recommendation**: Split into 2-3 sub-handovers:
- 0322A: UserService + users.py migration
- 0322B: AuthenticationService + auth.py migration
- 0322C: TaskService extension + tasks.py + messages.py migration

## Dependencies

- None (no external dependencies)
- Internal: Uses existing service patterns from ProductService, ProjectService
- Database: No schema changes required

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| API contract changes break frontend | Low | High | Keep response schemas identical |
| Test coverage gaps | Medium | Medium | Write tests before migration |
| Performance regression | Low | Low | Service layer adds minimal overhead |
| Multi-tenant isolation bugs | Low | High | Copy existing patterns exactly |

## References

- `handovers/013A_code_review_architecture_status.md` (Section 4: Service Layer Only)
- `docs/SERVICES.md` - Service layer patterns and examples
- `src/giljo_mcp/services/product_service.py` - Reference implementation
- `src/giljo_mcp/services/project_service.py` - Reference implementation
- `src/giljo_mcp/services/task_service.py` - Existing service to extend

## Acceptance Checklist

- [ ] All services follow the pattern in `docs/SERVICES.md`
- [ ] All services include multi-tenant isolation (`tenant_key` filtering)
- [ ] All services use Pydantic schemas for validation
- [ ] All services emit WebSocket events where appropriate
- [ ] All services have comprehensive logging
- [ ] All endpoints are thin request/response translators
- [ ] No direct SQLAlchemy imports in endpoint files
- [ ] All existing API tests pass
- [ ] New service tests achieve >80% coverage
- [ ] Documentation updated (SERVICES.md)
