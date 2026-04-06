# Critical Hub Files Analysis

**Generated:** 2025-02-06
**Source:** Dependency graph analysis (2,494 files scanned)

## Overview

This analysis identifies "hub files" - files with 50+ dependents that represent critical coupling points in the codebase. These files may need refactoring to reduce monolithic dependencies.

## Critical Hub Files (7 total)

### 1. `src/giljo_mcp/models/__init__.py`
**314 dependents** | **0 dependencies** | **Layer: model** | **Risk: CRITICAL**

**Analysis:**
- Highest dependency count in entire codebase
- Likely exports all model classes for easy importing
- Classic barrel file pattern creating tight coupling

**Recommendation:**
- Consider splitting into domain-specific barrel files (e.g., `models/agents.py`, `models/products.py`)
- Encourage direct imports from model files instead of through `__init__.py`
- Gradual migration: deprecate bulk exports, add explicit imports

---

### 2. `src/giljo_mcp/models/agent_identity.py`
**149 dependents** | **0 dependencies** | **Layer: model** | **Risk: CRITICAL**

**Analysis:**
- Second-highest dependency count
- Core model for agent system
- Used across services, API endpoints, and tools

**Recommendation:**
- This is likely acceptable coupling (core domain model)
- Consider splitting if it contains business logic (should be in services)
- Ensure it's a pure data model with no side effects

---

### 3. `src/giljo_mcp/database.py`
**143 dependents** | **0 dependencies** | **Layer: api** | **Risk: CRITICAL**

**Analysis:**
- Third-highest dependency count
- Likely provides database session management
- Central infrastructure component

**Recommendation:**
- This level of coupling is expected for infrastructure
- Ensure it only provides session/connection management
- Move any business logic to service layer

---

### 4. `frontend/src/services/api.js`
**84 dependents** | **2 dependencies** | **Layer: frontend** | **Risk: CRITICAL**

**Analysis:**
- Frontend API client hub
- All components likely import this for API calls
- Highest dependency in frontend layer

**Recommendation:**
- Consider domain-specific API modules (e.g., `agentsApi.js`, `productsApi.js`)
- Use composition pattern: export specialized clients from main api.js
- Reduces bundle size for tree-shaking

---

### 5. `src/giljo_mcp/tenant.py`
**73 dependents** | **0 dependencies** | **Layer: api** | **Risk: CRITICAL**

**Analysis:**
- Multi-tenant isolation utilities
- Cross-cutting concern used everywhere

**Recommendation:**
- This coupling is acceptable for tenant isolation (security concern)
- Ensure it's purely functional (no state)
- Consider middleware pattern to reduce direct imports

---

### 6. `src/giljo_mcp/models/products.py`
**59 dependents** | **0 dependencies** | **Layer: model** | **Risk: CRITICAL**

**Analysis:**
- Core Product model
- Used across product management features

**Recommendation:**
- Acceptable coupling for core domain model
- Review if contains business logic → move to ProductService
- Keep as pure data model

---

### 7. `src/giljo_mcp/models/projects.py`
**50 dependents** | **0 dependencies** | **Layer: model** | **Risk: CRITICAL**

**Analysis:**
- Core Project model
- Just crossed the 50-dependent threshold

**Recommendation:**
- Monitor as codebase grows
- Currently acceptable for core domain model
- Ensure separation of model definition from business logic

---

## Refactoring Priority Matrix

| Priority | File | Dependents | Reason |
|----------|------|------------|--------|
| **HIGH** | `models/__init__.py` | 314 | Barrel file - can be split by domain |
| **MEDIUM** | `frontend/src/services/api.js` | 84 | Can be split into domain APIs |
| **LOW** | `models/agent_identity.py` | 149 | Core domain model (acceptable) |
| **LOW** | `database.py` | 143 | Infrastructure (acceptable) |
| **LOW** | `tenant.py` | 73 | Security concern (acceptable) |
| **LOW** | `models/products.py` | 59 | Core domain model (acceptable) |
| **LOW** | `models/projects.py` | 50 | Core domain model (acceptable) |

## Refactoring Strategies

### 1. Barrel File Splitting (models/__init__.py)

**Before:**
```python
# models/__init__.py
from .agent_identity import AgentIdentity
from .products import Product
from .projects import Project
# ... 20+ more exports
```

**After:**
```python
# models/agents.py
from .agent_identity import AgentIdentity
from .agent_job import AgentJob

# models/products.py
from .products import Product
from .vision_documents import VisionDocument

# Encourage direct imports:
from giljo_mcp.models.agent_identity import AgentIdentity
# Instead of:
from giljo_mcp.models import AgentIdentity
```

### 2. Frontend API Splitting

**Before:**
```javascript
// api.js - 2000 lines
export const agentsApi = { ... }
export const productsApi = { ... }
export const projectsApi = { ... }
```

**After:**
```javascript
// api/agents.js
export const agentsApi = { ... }

// api/products.js
export const productsApi = { ... }

// api/index.js (aggregator)
export * from './agents'
export * from './products'
```

## Monitoring

**Rerun analysis monthly** to track:
- New files crossing 50-dependent threshold
- Reduction in coupling after refactoring
- Risk level changes

**Command:**
```bash
python scripts/build_dep_graph_part1.py
python scripts/remove_archived_from_graph.py
python scripts/update_dependency_graph.py
python scripts/add_hub_files_table.py
```

---

**Next Steps:**
1. Review `models/__init__.py` for domain-based splitting
2. Consider frontend API modularization in next sprint
3. Monitor other files approaching 50-dependent threshold
