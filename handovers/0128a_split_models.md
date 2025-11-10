# Handover 0128a: Split models.py God Object

**Status:** Ready to Execute
**Priority:** P1 - HIGH
**Estimated Duration:** 2-3 days
**Agent Budget:** 150K tokens
**Depends On:** 0127c (Deprecated code removed)

---

## Executive Summary

### The Problem

`src/giljo_mcp/models.py` is a 2,271-line GOD OBJECT containing ALL database models in a single file. This violates single responsibility principle and makes the code difficult to navigate and maintain.

### Current State

```
src/giljo_mcp/models.py (2,271 lines)
├── Base classes and mixins
├── User model
├── Session model
├── ApiKey model
├── Product model
├── Project model
├── MCPAgentJob model
├── AgentMessage model
├── Template model
├── TemplateVersion model
├── Task model
├── Context model
└── 15+ other models...
```

### Target State

```
src/giljo_mcp/models/
├── __init__.py         # Re-export all for backward compatibility
├── base.py            # Base, TenantMixin, TimestampMixin (~100 lines)
├── auth.py            # User, Session, ApiKey (~300 lines)
├── products.py        # Product, ProductSettings (~200 lines)
├── projects.py        # Project, ProjectStatus (~250 lines)
├── agents.py          # MCPAgentJob, AgentMessage (~400 lines)
├── templates.py       # Template, TemplateVersion (~300 lines)
├── tasks.py           # Task, TaskStatus (~200 lines)
├── context.py         # Context, ContextChunk (~200 lines)
└── config.py          # Configuration, Settings (~200 lines)
```

---

## Critical Requirement

### ZERO Breaking Changes

The refactoring MUST maintain 100% backward compatibility:

```python
# This MUST continue to work:
from src.giljo_mcp.models import User, Project, MCPAgentJob

# Even though internally it becomes:
from src.giljo_mcp.models.auth import User
from src.giljo_mcp.models.projects import Project
from src.giljo_mcp.models.agents import MCPAgentJob
```

---

## Implementation Plan

### Phase 1: Analysis and Planning (2-3 hours)

**Step 1.1: Map Current Models**

```bash
# Extract all class definitions
grep "^class.*Base):" src/giljo_mcp/models.py
grep "^class.*TenantMixin):" src/giljo_mcp/models.py

# Count lines per model (approximate)
# Document model dependencies and relationships
```

**Step 1.2: Plan Module Structure**

Group related models logically:

| Module | Models | Lines (est) |
|--------|--------|-------------|
| base.py | Base, TenantMixin, TimestampMixin | 100 |
| auth.py | User, Session, ApiKey, Role, Permission | 300 |
| products.py | Product, ProductSettings | 200 |
| projects.py | Project, ProjectStatus, ProjectCompletion | 250 |
| agents.py | MCPAgentJob, AgentMessage, AgentStatus | 400 |
| templates.py | Template, TemplateVersion, TemplateHistory | 300 |
| tasks.py | Task, TaskStatus, TaskAssignment | 200 |
| context.py | Context, ContextChunk, ContextIndex | 200 |
| config.py | Configuration, Settings, TenantConfig | 200 |

**Step 1.3: Identify Cross-Dependencies**

Document relationships between models:
- Project → Product (foreign key)
- MCPAgentJob → Project (foreign key)
- Task → Project (foreign key)
- Template → Product (foreign key)

### Phase 2: Create Module Structure (1-2 hours)

**Step 2.1: Create Directory**

```bash
# Create models package
mkdir -p src/giljo_mcp/models

# Create initial files
touch src/giljo_mcp/models/__init__.py
touch src/giljo_mcp/models/base.py
touch src/giljo_mcp/models/auth.py
touch src/giljo_mcp/models/products.py
touch src/giljo_mcp/models/projects.py
touch src/giljo_mcp/models/agents.py
touch src/giljo_mcp/models/templates.py
touch src/giljo_mcp/models/tasks.py
touch src/giljo_mcp/models/context.py
touch src/giljo_mcp/models/config.py
```

**Step 2.2: Create base.py First**

```python
# src/giljo_mcp/models/base.py
"""Base models and mixins for database models."""

from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class TenantMixin:
    """Mixin for multi-tenant isolation."""

    tenant_key = Column(String, nullable=False, index=True)


class TimestampMixin:
    """Mixin for automatic timestamps."""

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SoftDeleteMixin:
    """Mixin for soft delete functionality."""

    deleted = Column(Boolean, default=False, nullable=False)
    deleted_at = Column(DateTime, nullable=True)
```

### Phase 3: Split Models Systematically (4-6 hours)

**Step 3.1: Move Auth Models**

```python
# src/giljo_mcp/models/auth.py
"""Authentication and authorization models."""

from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship

from .base import Base, TenantMixin, TimestampMixin


class User(Base, TenantMixin, TimestampMixin):
    """User model for authentication."""

    __tablename__ = 'users'

    id = Column(String, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)

    # Relationships
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    api_keys = relationship("ApiKey", back_populates="user", cascade="all, delete-orphan")


class Session(Base, TenantMixin, TimestampMixin):
    """User session model."""

    __tablename__ = 'sessions'

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey('users.id'), nullable=False)
    token = Column(String, unique=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)

    # Relationships
    user = relationship("User", back_populates="sessions")


class ApiKey(Base, TenantMixin, TimestampMixin):
    """API key model for programmatic access."""

    __tablename__ = 'api_keys'

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey('users.id'), nullable=False)
    key = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    expires_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)

    # Relationships
    user = relationship("User", back_populates="api_keys")
```

**Step 3.2: Move Product Models**

```python
# src/giljo_mcp/models/products.py
"""Product-related models."""

from sqlalchemy import Column, String, Text, JSON, Boolean
from sqlalchemy.orm import relationship

from .base import Base, TenantMixin, TimestampMixin


class Product(Base, TenantMixin, TimestampMixin):
    """Product model."""

    __tablename__ = 'products'

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    settings = Column(JSON, default={})
    status = Column(String, default='inactive')
    is_active = Column(Boolean, default=False)

    # Relationships
    projects = relationship("Project", back_populates="product")
    templates = relationship("Template", back_populates="product")
```

**Step 3.3: Continue for All Models**

Follow same pattern for:
- projects.py (Project, ProjectStatus)
- agents.py (MCPAgentJob, AgentMessage)
- templates.py (Template, TemplateVersion)
- tasks.py (Task, TaskStatus)
- context.py (Context, ContextChunk)
- config.py (Configuration, Settings)

### Phase 4: Create Compatibility Layer (2-3 hours)

**Step 4.1: Create __init__.py for Re-exports**

```python
# src/giljo_mcp/models/__init__.py
"""
Database models package.

This module re-exports all models for backward compatibility.
Existing code can continue to import from src.giljo_mcp.models
"""

# Base classes
from .base import (
    Base,
    TenantMixin,
    TimestampMixin,
    SoftDeleteMixin
)

# Auth models
from .auth import (
    User,
    Session,
    ApiKey
)

# Product models
from .products import (
    Product
)

# Project models
from .projects import (
    Project,
    ProjectStatus
)

# Agent models
from .agents import (
    MCPAgentJob,
    AgentMessage
)

# Template models
from .templates import (
    Template,
    TemplateVersion
)

# Task models
from .tasks import (
    Task,
    TaskStatus
)

# Context models
from .context import (
    Context,
    ContextChunk
)

# Configuration models
from .config import (
    Configuration,
    Settings
)

# Export all for from src.giljo_mcp.models import *
__all__ = [
    # Base
    'Base',
    'TenantMixin',
    'TimestampMixin',
    'SoftDeleteMixin',

    # Auth
    'User',
    'Session',
    'ApiKey',

    # Products
    'Product',

    # Projects
    'Project',
    'ProjectStatus',

    # Agents
    'MCPAgentJob',
    'AgentMessage',

    # Templates
    'Template',
    'TemplateVersion',

    # Tasks
    'Task',
    'TaskStatus',

    # Context
    'Context',
    'ContextChunk',

    # Config
    'Configuration',
    'Settings',
]
```

**Step 4.2: Handle Circular Dependencies**

For models with circular dependencies, use string references:

```python
# In products.py
projects = relationship("Project", back_populates="product")

# In projects.py
product = relationship("Product", back_populates="projects")
```

### Phase 5: Migration Process (2-3 hours)

**Step 5.1: Backup Original**

```bash
# Create backup
cp src/giljo_mcp/models.py src/giljo_mcp/models.py.original

# Verify backup
ls -la src/giljo_mcp/models.py.original
```

**Step 5.2: Test Import Compatibility**

```python
# test_compatibility.py
"""Test that all imports still work."""

# Old style (must work)
from src.giljo_mcp.models import User, Project, MCPAgentJob
print("✅ Old imports work")

# New style (should also work)
from src.giljo_mcp.models.auth import User
from src.giljo_mcp.models.projects import Project
from src.giljo_mcp.models.agents import MCPAgentJob
print("✅ New imports work")

# Verify same classes
from src.giljo_mcp.models import User as OldUser
from src.giljo_mcp.models.auth import User as NewUser
assert OldUser is NewUser
print("✅ Classes are identical")
```

**Step 5.3: Update Internal Imports (Optional)**

While maintaining backward compatibility, optionally update internal imports to be more specific:

```python
# Can update internal code from:
from src.giljo_mcp.models import User, Project

# To more specific:
from src.giljo_mcp.models.auth import User
from src.giljo_mcp.models.projects import Project
```

### Phase 6: Validation (2-3 hours)

**Step 6.1: Test All Imports**

```bash
# Test that all files compile
find . -name "*.py" -exec python -m py_compile {} \;

# Test critical imports
python test_compatibility.py
```

**Step 6.2: Run Test Suite**

```bash
# All tests should pass without changes
pytest tests/ -v

# Specific model tests
pytest tests/unit/test_models.py -v
```

**Step 6.3: Test Application**

```bash
# Start application
python startup.py --dev

# Test basic operations
# - User login
# - Product creation
# - Project creation
# - Agent job spawning
```

**Step 6.4: Remove Original File**

```bash
# Only after everything works
rm src/giljo_mcp/models.py

# Keep backup for safety
ls -la src/giljo_mcp/models.py.original
```

---

## Validation Checklist

- [ ] All models successfully split into modules
- [ ] models/__init__.py exports all models
- [ ] Backward compatibility maintained
- [ ] No import errors anywhere
- [ ] Test suite passes 100%
- [ ] Application starts successfully
- [ ] Database operations work
- [ ] Original models.py removed
- [ ] Backup preserved

---

## Risk Assessment

**Risk 1: Breaking Imports**
- **Impact:** CRITICAL
- **Mitigation:** __init__.py re-exports everything

**Risk 2: Circular Dependencies**
- **Impact:** HIGH
- **Mitigation:** Use string references in relationships

**Risk 3: Missing Models**
- **Impact:** HIGH
- **Mitigation:** Comprehensive inventory before starting

---

## Rollback Plan

```bash
# If anything breaks
mv src/giljo_mcp/models.py.original src/giljo_mcp/models.py
rm -rf src/giljo_mcp/models/
git checkout .
```

---

## Expected Outcomes

### Before
- Single 2,271-line file
- Difficult to navigate
- Merge conflicts likely
- Hard to understand model relationships

### After
- 10 focused files (~200-400 lines each)
- Clear domain separation
- Easier maintenance
- Better code organization
- 100% backward compatible

---

**Created:** 2025-11-10
**Priority:** P1 - HIGH
**Complete After:** 0127c (Deprecated code removal)