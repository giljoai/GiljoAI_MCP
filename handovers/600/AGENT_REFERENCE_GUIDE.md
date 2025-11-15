# Project 600: Agent Reference Guide

**Include this file as context for ALL Project 600 handovers**

---

## Project Goal

Complete system restoration and validation for GiljoAI MCP. **Zero compromises** - every feature must work, every workflow must pass, every test must succeed. Establish production-ready foundation with 80%+ test coverage, <5 min fresh install, and hybrid self-healing architecture.

---

## 🚨 CRITICAL AUDIT FINDINGS (Handover 0600 - 2025-11-14)

**DATABASE MIGRATION CHAIN IS BROKEN**

- **Status**: Only 18 of 31 tables exist in database
- **Failed At**: Migration `20251029_0073_01`
- **Current Version**: `20251026_224146`
- **Missing**: 14 critical tables (mcp_agent_jobs, vision_documents, etc.)
- **Impact**: Fresh installations IMPOSSIBLE, 0 of 8 workflows functional
- **Required Action**: Execute Handover 0601 IMMEDIATELY before any other work

**Audit Results Summary**:
- API Endpoints: 204 decorators across 60 files ✅
- Services: 10 services, 44+ methods documented ✅
- Tests: 423 files categorized (Unit: 96, Integration: 84, API: 24) ✅
- Coverage Baseline: Cannot establish (blocked by database failure) ⚠️

**Deliverables**: See `handovers/600/0600_audit_report.md` for complete findings.

---

## Core Principles

1. **No Gentle Approach** - Can blow away test data, recreate databases, hard reset if needed
2. **All Features Must Work** - No excuses, no workarounds, no "good enough for now"
3. **Test Everything** - 80%+ coverage minimum, comprehensive E2E validation
4. **Multi-Tenant Secure** - Zero leakage between tenants, enforce isolation everywhere
5. **Self-Healing Architecture** - Baseline schema + on-demand table creation (future-proof)

---

## Critical Constraints

### DO NOT BREAK (Production Features)
- Default tenant creation (first user flow)
- Admin user setup (welcome page → first-login)
- Password change functionality (PIN recovery system)
- Multi-tenant isolation (tenant_id enforcement)
- Service architecture (6 services extracted from god object)
- API routes (84+ endpoints, NO route changes)
- Frontend contracts (WebSocket events, API response schemas)

### MUST PRESERVE (Architecture)
- Service layer pattern (ProductService, ProjectService, TaskService, MessageService, ContextService, OrchestrationService)
- API modular structure (api/endpoints/*.py)
- Multi-tenant database isolation (tenant_id in all queries)
- Soft delete pattern (deleted_at timestamp, 10-day recovery)
- Single active product per tenant (partial unique index enforcement)
- Single active project per product (cascade deactivation)

---

## Key Locations

### Backend Core
- **Models**: `src/giljo_mcp/models/` (31 tables, SQLAlchemy)
- **Services**: `src/giljo_mcp/services/` (6 services - ProductService, ProjectService, TaskService, MessageService, ContextService, OrchestrationService)
- **API**: `api/endpoints/` (14 files, 84+ endpoints)
- **MCP Tools**: `src/giljo_mcp/tools/` (20+ MCP tools - thin client, succession, templates)
- **Utilities**: `src/giljo_mcp/utils/` (decorators, helpers, validators)

### Database
- **Migrations**: `migrations/versions/` (44 migration files)
- **Critical Migration**: `20251114_create_missing_base_tables.py` (creates 14 missing tables, runs at position 44 - NEEDS REORDERING)

### Frontend
- **Components**: `frontend/src/components/` (Vue 3 + Vuetify)
- **API Client**: `frontend/src/services/api.js` (centralized API calls)
- **WebSocket**: `frontend/src/services/websocket.js` (real-time updates)

### Tests
- **Unit**: `tests/unit/` (service tests, model tests, tool tests)
- **Integration**: `tests/integration/` (service coordination, multi-tenant isolation)
- **E2E**: `tests/e2e/` (workflow validation, end-to-end scenarios)
- **API**: `tests/api/` (endpoint tests, authentication, response schemas)
- **Performance**: `tests/performance/` (benchmarks, load tests)

---

## Database Schema (31 Tables)

### Core Tables
- users, tenants, products, projects, tasks
- templates, template_archives (6 default templates per tenant)
- settings (user + admin settings)

### MCP Agent Tables
- mcp_agent_jobs (agent lifecycle: pending → in_progress → completed/failed)
- agent_messages (JSONB communication queue)
- context_usage (context tracking for succession)
- orchestrator_instances (lineage tracking: spawned_by chain)
- succession_handovers (handover summaries <10K tokens)

### Additional Tables (18)
- agent_job_results, agent_logs, api_keys, audit_logs, auth_tokens
- config_data (JSONB), deleted_projects (soft delete recovery)
- file_uploads, health_checks, integration_configs, migrations
- notifications, permissions, roles, sessions, webhooks
- workflow_states, websocket_connections

### Migration Status (CRITICAL - Updated from Handover 0601 Investigation)
- **45 migrations** exist (complex dependency chain)
- **ARCHITECTURAL ISSUE**: Migration chain has chicken-and-egg conflict
  - Migration `20251114` (position 44): Creates 14 tables with complete schemas
  - Migrations 1-43: Incrementally ADD columns to these same tables
  - **Conflict**: Moving 20251114 early causes "column already exists" errors
  - **Impact**: Fresh installations IMPOSSIBLE (18/31 tables), cannot simply reorder
- **Current version**: `20251026_224146` (October 2025)
- **Missing tables**: 14 critical tables (mcp_agent_jobs, vision_documents, settings, etc.)
- **Root cause**: Complete table creation at end of chain vs. incremental column additions throughout chain
- **Fix required**: Handover 0601b - Migration Chain Architectural Refactor (16-20 hours)
  - Split into minimal base schemas early + conditional backfill late
  - Modify 15+ migrations to use conditional column additions (IF NOT EXISTS)
  - Test both fresh install and incremental upgrade paths
- **Workaround**: Use existing database for testing (skip fresh install validation temporarily)
- **Status**: Handover 0601 investigation complete, architectural refactor required before Phase 1

---

## Common Patterns

### Service Pattern
```python
# src/giljo_mcp/services/product_service.py

from sqlalchemy.orm import Session
from src.giljo_mcp.models import Product

class ProductService:
    def __init__(self, db: Session):
        self.db = db

    def create_product(self, tenant_id: int, data: dict):
        """Create product with multi-tenant isolation"""
        product = Product(tenant_id=tenant_id, **data)
        self.db.add(product)
        self.db.commit()
        self.db.refresh(product)
        return product

    def get_product(self, tenant_id: int, product_id: int):
        """Get product with tenant isolation"""
        return self.db.query(Product).filter(
            Product.id == product_id,
            Product.tenant_id == tenant_id  # CRITICAL: Always filter by tenant_id
        ).first()
```

### API Endpoint Pattern
```python
# api/endpoints/products.py

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from src.giljo_mcp.services.product_service import ProductService
from api.dependencies import get_db, get_current_user

router = APIRouter()

@router.post("/api/v1/products")
def create_product(data: ProductCreate, db: Session = Depends(get_db), user = Depends(get_current_user)):
    """Create product (tenant isolated)"""
    service = ProductService(db)
    return service.create_product(tenant_id=user.tenant_id, data=data.dict())
```

### Test Pattern
```python
# tests/unit/test_product_service.py

import pytest
from src.giljo_mcp.services.product_service import ProductService

def test_create_product_success(db_session, tenant):
    """Test product creation with valid data"""
    service = ProductService(db_session)
    data = {"name": "Test Product", "description": "Test"}
    product = service.create_product(tenant_id=tenant.id, data=data)

    assert product.id is not None
    assert product.name == "Test Product"
    assert product.tenant_id == tenant.id

def test_get_product_tenant_isolation(db_session, tenant_a, tenant_b, product_a):
    """Test tenant cannot access other tenant's product"""
    service = ProductService(db_session)
    result = service.get_product(tenant_id=tenant_b.id, product_id=product_a.id)

    assert result is None  # Tenant B cannot see Tenant A's product
```

---

## Quality Standards

### Code Quality
- **Linting**: Ruff + Black compliant (no errors)
- **Type Hints**: Full type hints everywhere (mypy clean)
- **Docstrings**: All public methods documented
- **Error Handling**: Comprehensive try/except with logging

### Testing Quality
- **Coverage**: 80%+ per module (85%+ for critical services)
- **Test Types**: Unit (all methods) + Integration (multi-tenant) + E2E (workflows)
- **Assertions**: Clear, specific assertions (not just "assert result")
- **Fixtures**: Reusable fixtures for tenant, user, product, project setup

### Documentation Quality
- **Clarity**: Write for humans - concise, clear, practical
- **Code Examples**: All examples tested and working
- **Links**: All links verified (no broken links)
- **Accuracy**: Documentation matches code (update docs when code changes)

---

## Reference Documents

### Master Plan
- **Primary**: `handovers/600/PROJECTPLAN_600_MASTER.md` (this project's master plan)

### Historical Context
- **Refactoring Journey**: `handovers/REFACTORING_ROADMAP_0120-0130.md` (0120-0130 service extraction)
- **Plan 500 Template**: `handovers/Projectplan_500.md` (similar project structure - inspiration)

### Architecture Docs
- **System Overview**: `docs/GILJOAI_MCP_PURPOSE.md`
- **Architecture**: `docs/SERVER_ARCHITECTURE_TECH_STACK.md`
- **Installation**: `docs/INSTALLATION_FLOW_PROCESS.md`

---

## Testing Commands

### Fresh Install Test
```bash
dropdb giljo_mcp && createdb giljo_mcp
python install.py
# Expected: <5 min, 31 tables created, default tenant + admin user
```

### Unit Tests
```bash
# All unit tests
pytest tests/unit/ -v --cov=src/giljo_mcp --cov-report=html

# Single service
pytest tests/unit/test_product_service.py -v --cov=src/giljo_mcp/services/product_service.py --cov-report=term-missing

# Expected: 80%+ coverage, all tests pass
```

### Integration Tests
```bash
pytest tests/integration/ -v
# Expected: 100% passing, multi-tenant isolation verified
```

### E2E Tests
```bash
pytest tests/e2e/ -v
# Expected: All 8 workflows pass
```

### API Tests
```bash
pytest tests/api/ -v
# Expected: All 84+ endpoints tested, 100% passing
```

### Full Test Suite
```bash
pytest tests/ -v --cov=src/giljo_mcp --cov-report=html
# Expected: 80%+ coverage, 100% passing, <30 min execution
```

---

## Success Validation

### Each Handover Produces
1. **Working Code** - Feature implemented and functional
2. **Passing Tests** - All tests green (unit + integration + E2E as applicable)
3. **Documentation** - Updated docs (code comments, handover report)
4. **Git Commit** - Clean commit message following conventions
5. **Validation Report** - Handover completion document with metrics

### Handover Completion Checklist
- [ ] Code implemented and tested locally
- [ ] All tests pass (pytest output captured)
- [ ] Coverage target met (80%+ or as specified)
- [ ] Multi-tenant isolation verified (if applicable)
- [ ] Documentation updated (if applicable)
- [ ] Git commit created with descriptive message
- [ ] Handover report created (deliverables, metrics, validation)
- [ ] PR created (for CCW branches) or committed to master (for CLI)

---

## Quick Start for Agents

### CLI (Local) Agent Workflow
1. Read assigned handover file: `handovers/600/06XX_handover_name.md`
2. Read this reference guide for universal context
3. Execute tasks sequentially (database access available)
4. Run tests locally: `pytest tests/unit/test_X.py -v --cov`
5. Commit to master: `git add . && git commit -m "feat: Handover 06XX complete"`
6. Create handover report: `handovers/600/06XX_completion_report.md`

### CCW (Cloud) Agent Workflow
1. Create CCW branch: `06XX-feature-name`
2. Read assigned handover file: `handovers/600/06XX_handover_name.md`
3. Read this reference guide for universal context
4. Execute tasks in parallel (no database access - mock if needed)
5. Run tests in branch (capture output for PR)
6. Create PR with test results in description
7. Create handover report in PR description or separate file

---

## Common Pitfalls to Avoid

1. **Forgetting Tenant Isolation** - ALWAYS filter by tenant_id in queries
2. **Breaking API Routes** - Never change route paths, only internal implementation
3. **Skipping Tests** - Every feature needs tests (80%+ coverage non-negotiable)
4. **Hardcoding Paths** - Use `pathlib.Path()` for cross-platform compatibility
5. **Ignoring Multi-Tenant** - Test both same-tenant and cross-tenant scenarios
6. **Incomplete Error Handling** - Catch exceptions, log errors, return proper HTTP status codes
7. **Outdated Documentation** - Update docs when code changes (keep in sync)

---

**Document Control**:
- **Created**: 2025-11-14
- **Version**: 1.0
- **Status**: Active - Universal Reference
- **Audience**: ALL Project 600 agents (deep-researcher, tdd-implementor, api-tester, integration-tester, architectural-engineer, database-architect, documentation-specialist)
