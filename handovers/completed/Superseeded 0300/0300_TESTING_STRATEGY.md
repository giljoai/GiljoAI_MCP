# Handover 0300 Series: Comprehensive Testing Strategy

**Feature**: Context Management System Testing Framework
**Status**: Active Reference Document
**Priority**: P0 - CRITICAL
**Scope**: All handovers 0300-0311 (0311 added 2025-11-16)
**Created**: 2025-11-16
**Last Updated**: 2025-11-16

---

## Executive Summary

This document defines the comprehensive testing strategy for the **Context Management System (0300 series)**, ensuring the field priority system, token budget enforcement, vision chunking, and agent templates work cohesively to deliver context prioritization and orchestration with user transparency and control.

**Why This Matters**: Testing validates not just individual components, but the entire workflow from user configuration → context generation → orchestrator execution. This strategy ensures production-grade quality, prevents regressions, and provides confidence in the context prioritization and orchestration promise.

**Coverage Target**: >80% across all `mission_planner.py` methods, with 100% coverage on critical paths (priority mapping, budget enforcement, chunking).

---

## Test Pyramid Strategy

The Context Management System follows a balanced testing approach:

```
         /\
        /E2E\          5-10%  (Handover 0310)
       /------\        - Full workflow validation
      /Integration\    20-30% (Handovers 0301-0309)
     /------------\    - Cross-component interactions
    /  Unit Tests  \   60-75% (All handovers)
   /________________\  - Business logic in isolation
```

### Test Distribution Rationale

**Unit Tests (60-75%)**:
- Fast execution (<5 seconds total)
- Easy to debug (isolated failures)
- Test business logic exhaustively
- Mock external dependencies (DB, filesystem)

**Integration Tests (20-30%)**:
- Moderate execution time (<2 minutes total)
- Validate component interactions
- Use real database (PostgreSQL test instance)
- Test multi-tenant isolation

**E2E Tests (5-10%)**:
- Slower execution (<10 minutes total)
- Validate critical user journeys
- Test full stack (API → services → DB → frontend)
- Verify production-like scenarios

---

## Test Coverage Goals

### Overall Coverage Target
- **Line Coverage**: >80% for `src/giljo_mcp/mission_planner.py`
- **Branch Coverage**: >75% for all conditional logic
- **Critical Paths**: 100% coverage (no exceptions)

### Critical Paths Requiring 100% Coverage

1. **Priority Mapping** (Handover 0301)
   - `_map_priority_to_detail_level()` - All 5 detail levels tested
   - `_abbreviate_content()` - All abbreviation modes tested
   - `_minimal_content()` - Minimal extraction logic verified

2. **Token Budget Enforcement** (Handover 0304)
   - `_enforce_token_budget()` - Budget overflow handling
   - `_count_tokens()` - Accurate token counting
   - Field exclusion when budget exceeded

3. **Vision Chunking** (Handover 0305)
   - `_retrieve_vision_chunks()` - Chunk retrieval logic
   - `_merge_vision_chunks()` - Chunk concatenation
   - Error handling for missing chunks

4. **Multi-Tenant Isolation** (All handovers)
   - Tenant key validation in all database queries
   - Zero cross-tenant data leakage

---

## Test Data Strategy

### Reusable Fixtures (Shared Across All Handovers)

**File**: `tests/conftest.py` (EXISTING - already has comprehensive fixtures)

**Key Fixtures**:
```python
@pytest.fixture
async def product_with_full_config(db_manager):
    """Product with all 13 context fields populated (realistic data)"""
    return Product(
        id=uuid4(),
        name="Full Config Product",
        tenant_key="test_tenant",
        vision_document="# Product Vision\n\n" + "Large vision content " * 1000,  # ~3K tokens
        config_data={
            "tech_stack": {
                "languages": ["Python 3.11", "JavaScript ES2022", "TypeScript 5.0"],
                "backend": ["FastAPI", "PostgreSQL 18", "Redis 7"],
                "frontend": ["Vue 3", "Vuetify 3", "Pinia"],
                "infrastructure": ["Docker", "Kubernetes", "Nginx"]
            },
            "architecture": {
                "pattern": "Microservices with event-driven communication",
                "api_style": "REST + GraphQL hybrid",
                "design_patterns": "CQRS, Event Sourcing, Domain-Driven Design"
            },
            "features": {
                "core": ["User authentication", "Field priority system", "Token budget"],
                "advanced": ["Vision chunking", "Real-time WebSocket updates"]
            }
        }
    )


@pytest.fixture
async def product_with_minimal_config(db_manager):
    """Product with only required fields (graceful degradation test)"""
    return Product(
        id=uuid4(),
        name="Minimal Product",
        tenant_key="test_tenant",
        vision_document=None,  # Missing
        config_data=None  # Missing
    )


@pytest.fixture
async def product_with_chunked_vision(db_manager):
    """Product with 50KB vision split into chunks (<25K tokens each)"""
    # Create product
    product = Product(
        id=uuid4(),
        name="Chunked Vision Product",
        tenant_key="test_tenant",
        vision_document=None  # Will be stored as chunks
    )

    # Create vision chunks (simulating large vision document)
    large_content = "# Large Vision Document\n\n" + ("Section content " * 100 + "\n\n") * 50
    # This creates ~50K tokens, split into 3 chunks

    # Store chunks in vision_document_chunks table
    # (Handled by VisionDocumentRepository in actual code)

    return product


@pytest.fixture
async def sample_project(db_manager, product_with_full_config):
    """Project with codebase_summary populated"""
    project = Project(
        id=uuid4(),
        name="Sample Project",
        tenant_key="test_tenant",
        product_id=product_with_full_config.id,
        description="Implement core e-commerce features for MVP",
        mission="Build scalable e-commerce platform"
    )

    # Mock codebase_summary attribute (hybrid property)
    project.codebase_summary = """## Backend Structure
- api/ - FastAPI endpoints (15 modules, 200 LOC each)
- src/core/ - Business logic (20 modules)
- src/services/ - External integrations (Stripe, SendGrid, AWS S3)

## Frontend Structure
- components/ - Vue components (50+ reusable components)
- views/ - Page-level views (Dashboard, Products, Settings)
- stores/ - Pinia state management (Auth, Products, Cart)

## Key Files
- api/app.py - FastAPI application entry point
- src/core/auth.py - JWT authentication & authorization
- components/ProductCatalog.vue - Product listing with filters"""

    return project


@pytest.fixture
def default_field_priorities():
    """Default field priorities for new users"""
    return {
        "product_vision": 10,           # Priority 1 - Always included
        "tech_stack.languages": 10,     # Priority 1
        "tech_stack.backend": 10,       # Priority 1
        "project_description": 8,       # Priority 2 - High priority
        "codebase_summary": 8,          # Priority 2
        "tech_stack.frontend": 6,       # Priority 3 - Include if budget allows
        "architecture": 6,              # Priority 3
        "features.core": 4,             # Low priority
        "tech_stack.infrastructure": 0  # Unassigned - Excluded
    }


@pytest.fixture
def benchmark_timer():
    """Simple timer for performance benchmarking"""
    import time

    class Timer:
        def __init__(self):
            self.times = []

        def start(self):
            self.start_time = time.perf_counter()

        def stop(self):
            elapsed = (time.perf_counter() - self.start_time) * 1000  # ms
            self.times.append(elapsed)
            return elapsed

        def average(self):
            return sum(self.times) / len(self.times) if self.times else 0

        def max(self):
            return max(self.times) if self.times else 0

        def min(self):
            return min(self.times) if self.times else 0

    return Timer()
```

---

## Test Organization

### Directory Structure

```
tests/
├── unit/                                          # Unit tests (fast, no DB)
│   ├── test_mission_planner_priority.py          (0301) Priority mapping logic
│   ├── test_mission_planner_tech_stack.py        (0302) Tech stack extraction
│   ├── test_mission_planner_config.py            (0303) Product config extraction
│   ├── test_mission_planner_budget.py            (0304) Token budget enforcement
│   └── test_mission_planner_chunks.py            (0305) Vision chunk handling
│
├── integration/                                   # Integration tests (PostgreSQL required)
│   ├── test_field_priority_mapping.py            (0301) Priority → detail level
│   ├── test_tech_stack_extraction.py             (0302) JSONB field extraction
│   ├── test_product_config_extraction.py         (0303) Full config parsing
│   ├── test_token_budget_enforcement.py          (0304) Budget overflow handling
│   ├── test_vision_chunking.py                   (0305) Chunk retrieval & merge
│   ├── test_agent_templates_context.py           (0306) Template formatting
│   ├── test_backend_default_priorities.py        (0307) Default priority application
│   ├── test_frontend_token_calculation.py        (0308) Frontend token estimates
│   ├── test_token_estimation_accuracy.py         (0309) Estimation vs actual
│   └── test_context_system_e2e.py                (0310) Full workflow validation
│
├── performance/                                   # Performance benchmarks
│   ├── test_context_generation_performance.py     Context generation < 200ms
│   ├── test_token_estimation_performance.py       Token estimation < 50ms
│   └── test_vision_chunk_retrieval_performance.py Chunk retrieval < 100ms
│
├── frontend/                                      # Frontend component tests
│   └── UserSettings.spec.js                      (0308) Vue component tests
│
├── conftest.py                                    # Shared fixtures (EXISTING)
└── pytest.ini                                     # Pytest configuration
```

---

## Performance Testing

### Benchmarks (Per Component)

| Component | Target | Measurement |
|-----------|--------|-------------|
| Priority mapping (`_map_priority_to_detail_level()`) | <1ms | Single priority resolution |
| Tech stack extraction (`_extract_tech_stack()`) | <10ms | Parse JSONB config_data |
| Product config extraction (`_extract_product_config()`) | <20ms | Full config parsing |
| Token counting (`_count_tokens()`) | <5ms | 1000-token string |
| Vision chunk retrieval (`_retrieve_vision_chunks()`) | <100ms | Fetch 3 chunks from DB |
| **Complete context build** | **<200ms** | **Full context generation** |

### Load Testing Scenarios

**Scenario 1: Concurrent Context Generation**
- 100 concurrent users generating context
- Each user has different field priorities
- Verify: No performance degradation, no race conditions

**Scenario 2: Large Vision Documents**
- Vision document: 1MB (split into 40 chunks)
- Verify: Chunk retrieval stays under 100ms
- Verify: Memory usage stays under 100MB

**Scenario 3: Multi-Tenant Load**
- 1000 products across 100 tenants
- Verify: Multi-tenant isolation maintained
- Verify: No cross-tenant data leaks under load

### Performance Regression Detection

**Baseline Establishment**:
```bash
# Run performance tests and save baseline
pytest tests/performance/ --benchmark-save=baseline

# Compare future runs against baseline
pytest tests/performance/ --benchmark-compare=baseline
```

**CI/CD Integration**:
- Fail build if performance degrades >10%
- Alert if any benchmark exceeds target threshold

---

## Test Execution Strategy

### Per-Handover Testing (During Development)

**Unit Tests** (Fast feedback loop):
```bash
# Handover 0301: Priority mapping
pytest tests/unit/test_mission_planner_priority.py -v

# Handover 0302: Tech stack extraction
pytest tests/unit/test_mission_planner_tech_stack.py -v

# Handover 0303: Product config extraction
pytest tests/unit/test_mission_planner_config.py -v

# Handover 0304: Token budget enforcement
pytest tests/unit/test_mission_planner_budget.py -v

# Handover 0305: Vision chunking
pytest tests/unit/test_mission_planner_chunks.py -v
```

**Integration Tests** (Requires PostgreSQL):
```bash
# Run integration tests for specific handover
pytest tests/integration/test_field_priority_mapping.py -v

# Run with coverage
pytest tests/integration/test_field_priority_mapping.py --cov=src/giljo_mcp/mission_planner --cov-report=html
```

### Full Suite Testing (Before Phase 4 Completion)

**Complete Test Suite**:
```bash
# All tests with coverage report
pytest tests/ --cov=src/giljo_mcp --cov-report=html --cov-report=term -v

# Filter to mission_planner only
pytest tests/ --cov=src/giljo_mcp/mission_planner --cov-report=html -v

# Run only 0300 series tests (using markers)
pytest tests/ -m "context_management" -v
```

**Coverage Validation**:
```bash
# Check coverage meets 80% threshold
pytest tests/ --cov=src/giljo_mcp/mission_planner --cov-fail-under=80
```

**Performance Benchmarks**:
```bash
# Run performance tests with detailed output
pytest tests/performance/ --benchmark-only --benchmark-verbose
```

---

## CI/CD Integration

### Pre-Commit Hooks (Local Development)

**File**: `.pre-commit-config.yaml`
```yaml
repos:
  - repo: local
    hooks:
      - id: unit-tests
        name: Run unit tests
        entry: pytest tests/unit/ -v
        language: system
        pass_filenames: false
        always_run: true
```

### Pull Request Validation (GitHub Actions)

**File**: `.github/workflows/pr_validation.yml`
```yaml
name: PR Validation

on: [pull_request]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-asyncio pytest-cov

      - name: Run unit tests
        run: pytest tests/unit/ -v --cov=src/giljo_mcp --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage.xml

  integration-tests:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:18
        env:
          POSTGRES_PASSWORD: test_password
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-asyncio pytest-cov

      - name: Run integration tests
        run: pytest tests/integration/ -v --cov=src/giljo_mcp --cov-fail-under=80
        env:
          DATABASE_URL: postgresql://postgres:test_password@localhost/giljo_mcp_test

  performance-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Run performance benchmarks
        run: pytest tests/performance/ --benchmark-only --benchmark-compare=baseline
```

### Coverage Gates

**Fail Build If**:
- Overall coverage <80%
- Critical path coverage <100%
- Performance regression >10%
- Any integration test fails

---

## Manual Testing Checklist

For each handover, manual verification steps:

### Handover 0301: Priority Mapping
- [ ] Open User Settings → Field Priorities
- [ ] Drag field to Priority 1 tier
- [ ] Verify context preview shows full detail
- [ ] Drag field to Priority 3 tier
- [ ] Verify context preview shows minimal detail
- [ ] Set field to Unassigned
- [ ] Verify field excluded from context

### Handover 0302: Tech Stack Extraction
- [ ] Edit product config → Add tech_stack.languages
- [ ] Verify token estimate updates in UI
- [ ] Generate context preview
- [ ] Verify "Programming Languages: Python, JavaScript" appears

### Handover 0303: Product Config Extraction
- [ ] Edit product config → Add features.core
- [ ] Verify field appears in Field Priorities UI
- [ ] Assign priority and generate context
- [ ] Verify features appear in context string

### Handover 0304: Token Budget Enforcement
- [ ] Set field priorities to exceed budget
- [ ] Verify context preview truncates fields
- [ ] Verify warning message displayed
- [ ] Verify token count matches budget limit

### Handover 0305: Vision Chunking
- [ ] Upload vision document >50KB
- [ ] Verify chunks created in database
- [ ] Generate context with product_vision Priority 1
- [ ] Verify all chunks merged correctly

### Handover 0306: Agent Templates
- [ ] Verify "Available Agents" section in context preview
- [ ] Verify agent templates formatted correctly
- [ ] Verify templates respect token budget

### Handover 0307: Default Priorities
- [ ] Create new user account
- [ ] Verify field_priority_config is NULL
- [ ] Generate context
- [ ] Verify defaults applied (Priority 1 fields included)

### Handover 0308: Field Labels & Tooltips
- [ ] Open Field Priorities UI
- [ ] Hover over field card
- [ ] Verify tooltip displays field description
- [ ] Verify labels human-readable

### Handover 0309: Token Estimation
- [ ] Edit product vision document
- [ ] Verify token estimates update in real-time
- [ ] Compare estimate vs actual context tokens
- [ ] Verify within 5% accuracy

### Handover 0311: 360 Memory + Git Integration (Added 2025-11-16)
- [ ] Create product with 5+ project learnings in product_memory.learnings
- [ ] Set "360 Memory" field priority to 10 (full)
- [ ] Generate context and verify ALL learnings with outcomes + decisions included
- [ ] Change priority to 7 (moderate), verify last 5 learnings with outcomes only
- [ ] Change priority to 4 (abbreviated), verify last 3 learnings summary only
- [ ] Change priority to 1 (minimal), verify last 1 learning summary only
- [ ] Set priority to 0 (exclude), verify NO 360 Memory in context
- [ ] Enable Git integration toggle at /settings → Integrations
- [ ] Generate context and verify git command instructions included
- [ ] Disable Git toggle, verify git instructions NOT included
- [ ] Enable both 360 Memory (priority 7) + Git, verify BOTH included and combined correctly
- [ ] Verify token counting includes 360 Memory + Git in budget

### Handover 0310: E2E Validation
- [ ] Complete full workflow: signup → create product → configure priorities → generate context
- [ ] Stage project and verify orchestrator receives correct context
- [ ] Verify multi-tenant isolation (create second tenant, verify no cross-contamination)
- [ ] Verify ALL 9 context sources operational (including 360 Memory + Git)

---

## Regression Prevention

### Baseline Tests (Must Never Break)

**Critical Tests** (If these fail, DO NOT MERGE):
1. `test_full_priority_all_fields()` - Ensures Priority 10 includes full content
2. `test_priority_zero_excludes_field()` - Ensures Priority 0 excludes fields
3. `test_multi_tenant_isolation_in_logging()` - Prevents tenant data leaks
4. `test_token_budget_accuracy_across_system()` - Validates token counting accuracy
5. `test_default_priority_application_for_new_users()` - Ensures new users get defaults

### Backward Compatibility

**Version Compatibility Tests**:
```python
@pytest.mark.asyncio
async def test_old_field_priority_config_format_supported(db_session):
    """
    REGRESSION: Ensure old field_priority_config format still works

    GIVEN: User with legacy field_priority_config format
    WHEN: Generating context
    THEN: System handles gracefully (no errors, applies defaults)
    """
    # Test that old format {"field_name": 1} still works
    # alongside new format {"fields": {"field_name": 1}}
    pass
```

**Database Migration Tests**:
```python
@pytest.mark.asyncio
async def test_database_migration_preserves_priorities(db_session):
    """
    REGRESSION: Database migrations preserve user field priorities

    GIVEN: User with custom field priorities
    WHEN: Database migration runs
    THEN: Field priorities preserved exactly
    """
    pass
```

---

## Test Maintenance

### When to Update Tests

**Trigger Events**:
1. **Business Logic Change**: Update affected unit tests immediately
2. **Database Schema Change**: Update integration tests to match new schema
3. **API Endpoint Change**: Update API tests and E2E tests
4. **Performance Regression**: Add new performance benchmark

### Test Refactoring Guidelines

**Avoid Duplication**:
- Extract common test setup to fixtures
- Reuse helper functions across test files
- Share test data via conftest.py

**Maintain Clarity**:
- Keep test names descriptive (`test_priority_10_includes_full_content`)
- Use GIVEN-WHEN-THEN structure in docstrings
- Add comments for non-obvious assertions

### Archiving Obsolete Tests

**When to Archive**:
- Feature removed from product
- Test replaced by better version
- Technology deprecated (e.g., old field priority format)

**Archive Location**: `tests/archived/` (NOT deleted - preserved for reference)

---

## Test Data Dependencies

### Database Test Data

**Isolation**: Each test creates its own data (no shared state)

**Cleanup**: Use fixtures with teardown to clean up test data

**Example**:
```python
@pytest.fixture
async def test_product(db_session, tenant_key):
    """Create test product, auto-cleanup after test"""
    from src.giljo_mcp.services.product_service import ProductService

    service = ProductService(db_session, tenant_key)
    product = await service.create_product({"name": "Test Product"})

    yield product

    # Cleanup after test
    await service.delete_product(product.id)
```

### External Service Mocking

**Mock External APIs**:
```python
@pytest.fixture
def mock_websocket_manager(monkeypatch):
    """Mock WebSocket manager to avoid real WS connections"""
    from unittest.mock import AsyncMock

    mock_ws = AsyncMock()
    monkeypatch.setattr("src.giljo_mcp.websocket_manager", mock_ws)
    return mock_ws
```

---

## Related Documentation

- **TESTING.md**: [F:\GiljoAI_MCP\docs\TESTING.md](../docs/TESTING.md) - General testing patterns
- **SERVICES.md**: [F:\GiljoAI_MCP\docs\SERVICES.md](../docs/SERVICES.md) - Service layer architecture
- **Handover 0310**: [0310_integration_testing_validation.md](0310_integration_testing_validation.md) - E2E test specifications

---

## Quick Reference Commands

### Run All 0300 Series Tests
```bash
# Unit + Integration + Performance
pytest tests/unit/test_mission_planner*.py tests/integration/test_*_extraction.py tests/performance/ -v
```

### Coverage Report (HTML)
```bash
pytest tests/ --cov=src/giljo_mcp/mission_planner --cov-report=html
open htmlcov/index.html  # macOS/Linux
start htmlcov/index.html  # Windows
```

### Performance Benchmarks
```bash
pytest tests/performance/ --benchmark-only --benchmark-verbose
```

### Single Test Execution
```bash
# Run one specific test
pytest tests/unit/test_mission_planner_priority.py::test_full_priority_all_fields -v -s
```

---

**Last Updated**: 2025-11-16
**Status**: Active Reference Document
**Version**: 1.1 (Added 0311 test requirements)
**Next Review**: After Handover 0310 completion

**Changelog**:
- **v1.1 (2025-11-16)**: Added test requirements for handover 0311 (360 Memory + Git integration)
