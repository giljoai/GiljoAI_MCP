# Project 3.9.b: Agent Template Database Schema Design

## Executive Summary
This document outlines the database schema design for migrating the hardcoded template system from `mission_templates.py` to a database-backed solution with versioning, multi-tenancy, and runtime augmentation support.

## Analysis of Current System

### Existing Template Implementation
- **Location**: `src/giljo_mcp/mission_templates.py`
- **Structure**: Python classes with hardcoded template strings
- **Templates**: 5 role-based templates (Orchestrator, Analyzer, Implementer, Tester, Reviewer)
- **Features**: Variable substitution, project-type customization, behavioral rules
- **Integration**: Used by `orchestrator.py` lines 331 and 338 for agent spawning

### Current Architecture Patterns (from models.py)
- UUID primary keys using `String(36)`
- Multi-tenant isolation via `tenant_key`
- JSON columns for flexible metadata
- Timestamps with `server_default=func.now()`
- Proper relationship definitions with cascade options
- Index optimization for query performance

## Database Schema Design

### 1. AgentTemplate Table
Stores the base agent templates with product-specific isolation.

```sql
CREATE TABLE agent_templates (
    id VARCHAR(36) PRIMARY KEY DEFAULT (uuid()),
    tenant_key VARCHAR(36) NOT NULL,
    product_id VARCHAR(36) REFERENCES products(id),
    
    -- Template identification
    name VARCHAR(100) NOT NULL,  -- e.g., 'orchestrator', 'analyzer'
    category VARCHAR(50) NOT NULL,  -- 'role', 'project_type', 'custom'
    role VARCHAR(50),  -- AgentRole enum value
    project_type VARCHAR(50),  -- ProjectType enum value
    
    -- Template content
    template_content TEXT NOT NULL,  -- The actual template with {variables}
    variables JSON DEFAULT '[]',  -- List of required variables
    behavioral_rules JSON DEFAULT '[]',  -- Role-specific rules
    success_criteria JSON DEFAULT '[]',  -- Success metrics
    
    -- Usage tracking
    usage_count INTEGER DEFAULT 0,
    last_used_at TIMESTAMP,
    avg_generation_ms FLOAT,  -- Performance tracking
    
    -- Metadata
    description TEXT,
    version VARCHAR(20) DEFAULT '1.0.0',
    is_active BOOLEAN DEFAULT TRUE,
    is_default BOOLEAN DEFAULT FALSE,  -- One default per role
    tags JSON DEFAULT '[]',
    meta_data JSON DEFAULT '{}',
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP,
    created_by VARCHAR(100),
    
    -- Constraints
    UNIQUE KEY uq_template_name (product_id, name, version),
    INDEX idx_template_tenant (tenant_key),
    INDEX idx_template_product (product_id),
    INDEX idx_template_category (category),
    INDEX idx_template_role (role),
    INDEX idx_template_active (is_active)
);
```

### 2. TemplateArchive Table
Stores historical versions of templates for audit and rollback.

```sql
CREATE TABLE template_archives (
    id VARCHAR(36) PRIMARY KEY DEFAULT (uuid()),
    tenant_key VARCHAR(36) NOT NULL,
    template_id VARCHAR(36) NOT NULL,
    product_id VARCHAR(36) REFERENCES products(id),
    
    -- Archived template data (snapshot)
    name VARCHAR(100) NOT NULL,
    category VARCHAR(50) NOT NULL,
    role VARCHAR(50),
    template_content TEXT NOT NULL,
    variables JSON,
    behavioral_rules JSON,
    success_criteria JSON,
    
    -- Archive metadata
    version VARCHAR(20) NOT NULL,
    archive_reason VARCHAR(255),
    archive_type VARCHAR(20) DEFAULT 'manual',  -- 'manual', 'auto', 'scheduled'
    archived_by VARCHAR(100),
    archived_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Performance snapshot
    usage_count_at_archive INTEGER,
    avg_generation_ms_at_archive FLOAT,
    
    -- Restoration tracking
    is_restorable BOOLEAN DEFAULT TRUE,
    restored_at TIMESTAMP,
    restored_by VARCHAR(100),
    
    meta_data JSON DEFAULT '{}',
    
    -- Indexes
    INDEX idx_archive_tenant (tenant_key),
    INDEX idx_archive_template (template_id),
    INDEX idx_archive_product (product_id),
    INDEX idx_archive_version (version),
    INDEX idx_archive_date (archived_at)
);
```

### 3. TemplateAugmentation Table
Stores runtime augmentations that can be applied to base templates.

```sql
CREATE TABLE template_augmentations (
    id VARCHAR(36) PRIMARY KEY DEFAULT (uuid()),
    tenant_key VARCHAR(36) NOT NULL,
    template_id VARCHAR(36) REFERENCES agent_templates(id),
    
    -- Augmentation details
    name VARCHAR(100) NOT NULL,
    augmentation_type VARCHAR(50) NOT NULL,  -- 'append', 'prepend', 'replace', 'inject'
    target_section VARCHAR(100),  -- Which section to augment
    content TEXT NOT NULL,
    conditions JSON DEFAULT '{}',  -- When to apply this augmentation
    priority INTEGER DEFAULT 0,  -- Order of application
    
    -- Usage
    is_active BOOLEAN DEFAULT TRUE,
    usage_count INTEGER DEFAULT 0,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP,
    
    -- Indexes
    INDEX idx_augment_tenant (tenant_key),
    INDEX idx_augment_template (template_id),
    INDEX idx_augment_active (is_active)
);
```

### 4. TemplateUsageStats Table
Tracks template usage for optimization and recommendations.

```sql
CREATE TABLE template_usage_stats (
    id VARCHAR(36) PRIMARY KEY DEFAULT (uuid()),
    tenant_key VARCHAR(36) NOT NULL,
    template_id VARCHAR(36) REFERENCES agent_templates(id),
    agent_id VARCHAR(36) REFERENCES agents(id),
    project_id VARCHAR(36) REFERENCES projects(id),
    
    -- Usage details
    used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    generation_ms INTEGER,  -- Time to generate
    variables_used JSON,  -- Actual variables substituted
    augmentations_applied JSON DEFAULT '[]',  -- List of augmentation IDs
    
    -- Outcome tracking
    agent_completed BOOLEAN,
    agent_success_rate FLOAT,
    tokens_used INTEGER,
    
    -- Indexes
    INDEX idx_usage_tenant (tenant_key),
    INDEX idx_usage_template (template_id),
    INDEX idx_usage_project (project_id),
    INDEX idx_usage_date (used_at)
);
```

## SQLAlchemy Models

```python
# To be added to src/giljo_mcp/models.py

class AgentTemplate(Base):
    """Agent template model with multi-tenant support."""
    __tablename__ = "agent_templates"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_key = Column(String(36), nullable=False)
    product_id = Column(String(36), ForeignKey("products.id"), nullable=True)
    
    # Template identification
    name = Column(String(100), nullable=False)
    category = Column(String(50), nullable=False)
    role = Column(String(50), nullable=True)
    project_type = Column(String(50), nullable=True)
    
    # Template content
    template_content = Column(Text, nullable=False)
    variables = Column(JSON, default=list)
    behavioral_rules = Column(JSON, default=list)
    success_criteria = Column(JSON, default=list)
    
    # Usage tracking
    usage_count = Column(Integer, default=0)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    avg_generation_ms = Column(Float, nullable=True)
    
    # Metadata
    description = Column(Text, nullable=True)
    version = Column(String(20), default="1.0.0")
    is_active = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)
    tags = Column(JSON, default=list)
    meta_data = Column(JSON, default=dict)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by = Column(String(100), nullable=True)
    
    # Relationships
    archives = relationship("TemplateArchive", back_populates="template")
    augmentations = relationship("TemplateAugmentation", back_populates="template")
    usage_stats = relationship("TemplateUsageStats", back_populates="template")
    
    __table_args__ = (
        UniqueConstraint("product_id", "name", "version", name="uq_template_name"),
        Index("idx_template_tenant", "tenant_key"),
        Index("idx_template_product", "product_id"),
        Index("idx_template_category", "category"),
        Index("idx_template_role", "role"),
        Index("idx_template_active", "is_active"),
    )


class TemplateArchive(Base):
    """Template archive model for version history."""
    __tablename__ = "template_archives"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_key = Column(String(36), nullable=False)
    template_id = Column(String(36), ForeignKey("agent_templates.id"), nullable=False)
    product_id = Column(String(36), ForeignKey("products.id"), nullable=True)
    
    # Archived template data
    name = Column(String(100), nullable=False)
    category = Column(String(50), nullable=False)
    role = Column(String(50), nullable=True)
    template_content = Column(Text, nullable=False)
    variables = Column(JSON, default=list)
    behavioral_rules = Column(JSON, default=list)
    success_criteria = Column(JSON, default=list)
    
    # Archive metadata
    version = Column(String(20), nullable=False)
    archive_reason = Column(String(255), nullable=True)
    archive_type = Column(String(20), default="manual")
    archived_by = Column(String(100), nullable=True)
    archived_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Performance snapshot
    usage_count_at_archive = Column(Integer, nullable=True)
    avg_generation_ms_at_archive = Column(Float, nullable=True)
    
    # Restoration tracking
    is_restorable = Column(Boolean, default=True)
    restored_at = Column(DateTime(timezone=True), nullable=True)
    restored_by = Column(String(100), nullable=True)
    
    meta_data = Column(JSON, default=dict)
    
    # Relationships
    template = relationship("AgentTemplate", back_populates="archives")
    
    __table_args__ = (
        Index("idx_archive_tenant", "tenant_key"),
        Index("idx_archive_template", "template_id"),
        Index("idx_archive_product", "product_id"),
        Index("idx_archive_version", "version"),
        Index("idx_archive_date", "archived_at"),
    )


class TemplateAugmentation(Base):
    """Template augmentation model for runtime customization."""
    __tablename__ = "template_augmentations"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_key = Column(String(36), nullable=False)
    template_id = Column(String(36), ForeignKey("agent_templates.id"), nullable=False)
    
    # Augmentation details
    name = Column(String(100), nullable=False)
    augmentation_type = Column(String(50), nullable=False)
    target_section = Column(String(100), nullable=True)
    content = Column(Text, nullable=False)
    conditions = Column(JSON, default=dict)
    priority = Column(Integer, default=0)
    
    # Usage
    is_active = Column(Boolean, default=True)
    usage_count = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    template = relationship("AgentTemplate", back_populates="augmentations")
    
    __table_args__ = (
        Index("idx_augment_tenant", "tenant_key"),
        Index("idx_augment_template", "template_id"),
        Index("idx_augment_active", "is_active"),
    )


class TemplateUsageStats(Base):
    """Template usage statistics for optimization."""
    __tablename__ = "template_usage_stats"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_key = Column(String(36), nullable=False)
    template_id = Column(String(36), ForeignKey("agent_templates.id"), nullable=False)
    agent_id = Column(String(36), ForeignKey("agents.id"), nullable=True)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=True)
    
    # Usage details
    used_at = Column(DateTime(timezone=True), server_default=func.now())
    generation_ms = Column(Integer, nullable=True)
    variables_used = Column(JSON, default=dict)
    augmentations_applied = Column(JSON, default=list)
    
    # Outcome tracking
    agent_completed = Column(Boolean, nullable=True)
    agent_success_rate = Column(Float, nullable=True)
    tokens_used = Column(Integer, nullable=True)
    
    # Relationships
    template = relationship("AgentTemplate", back_populates="usage_stats")
    
    __table_args__ = (
        Index("idx_usage_tenant", "tenant_key"),
        Index("idx_usage_template", "template_id"),
        Index("idx_usage_project", "project_id"),
        Index("idx_usage_date", "used_at"),
    )
```

## MCP Tool Interface Design

### 1. list_agent_templates
```python
async def list_agent_templates(
    product_id: Optional[str] = None,
    category: Optional[str] = None,
    role: Optional[str] = None,
    include_inactive: bool = False
) -> List[Dict]:
    """
    List available agent templates with filtering.
    
    Returns:
        List of template summaries with id, name, role, usage_count
    """
```

### 2. get_agent_template
```python
async def get_agent_template(
    name: str,
    product_id: Optional[str] = None,
    version: Optional[str] = None,
    augmentations: Optional[List[str]] = None,
    variables: Optional[Dict[str, Any]] = None
) -> str:
    """
    Retrieve a template with optional augmentations and variable substitution.
    
    Returns:
        Generated template string with substitutions applied
    """
```

### 3. create_agent_template
```python
async def create_agent_template(
    name: str,
    category: str,
    template_content: str,
    product_id: Optional[str] = None,
    role: Optional[str] = None,
    variables: Optional[List[str]] = None,
    behavioral_rules: Optional[List[str]] = None,
    success_criteria: Optional[List[str]] = None,
    description: Optional[str] = None
) -> Dict:
    """
    Create a new agent template.
    
    Returns:
        Created template details with ID
    """
```

### 4. update_agent_template
```python
async def update_agent_template(
    template_id: str,
    template_content: Optional[str] = None,
    behavioral_rules: Optional[List[str]] = None,
    success_criteria: Optional[List[str]] = None,
    archive_reason: str = "Update via MCP tool"
) -> Dict:
    """
    Update an existing template (auto-archives previous version).
    
    Returns:
        Updated template details
    """
```

### 5. archive_template
```python
async def archive_template(
    template_id: str,
    reason: str,
    archive_type: str = "manual"
) -> Dict:
    """
    Archive a template version.
    
    Returns:
        Archive record details
    """
```

### 6. restore_template
```python
async def restore_template(
    archive_id: str,
    as_new_version: bool = True
) -> Dict:
    """
    Restore an archived template.
    
    Returns:
        Restored template details
    """
```

### 7. create_template_augmentation
```python
async def create_template_augmentation(
    template_id: str,
    name: str,
    augmentation_type: str,  # 'append', 'prepend', 'replace', 'inject'
    content: str,
    target_section: Optional[str] = None,
    conditions: Optional[Dict] = None,
    priority: int = 0
) -> Dict:
    """
    Create a template augmentation.
    
    Returns:
        Created augmentation details
    """
```

### 8. get_template_usage_stats
```python
async def get_template_usage_stats(
    template_id: Optional[str] = None,
    project_id: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None
) -> Dict:
    """
    Get template usage statistics.
    
    Returns:
        Usage statistics with performance metrics
    """
```

### 9. recommend_template
```python
async def recommend_template(
    project_type: str,
    role: str,
    context: Optional[Dict] = None
) -> Dict:
    """
    Get template recommendation based on project type and context.
    
    Returns:
        Recommended template with confidence score
    """
```

### 10. validate_template
```python
async def validate_template(
    template_content: str,
    variables: Optional[Dict[str, Any]] = None
) -> Dict:
    """
    Validate template syntax and variables.
    
    Returns:
        Validation result with any errors/warnings
    """
```

## Migration Strategy

### Phase 1: Database Setup
1. Create new tables using Alembic migration
2. Add SQLAlchemy models to models.py
3. Create database indices for performance

### Phase 2: Data Migration
1. Parse existing templates from mission_templates.py
2. Insert base templates into agent_templates table
3. Set default flags for standard roles
4. Create initial version entries in archives

### Phase 3: MCP Tool Implementation
1. Implement all 10 MCP tools in mcp_tools.py
2. Add caching layer for frequently used templates
3. Implement performance monitoring

### Phase 4: Integration
1. Update orchestrator.py to use database templates
2. Maintain backward compatibility during transition
3. Add feature flag for gradual rollout

## Performance Considerations

### Caching Strategy
- In-memory cache for frequently used templates
- Redis cache for distributed deployments
- Cache invalidation on template updates
- Target: <0.1ms template generation

### Query Optimization
- Composite indices on (product_id, name, version)
- Partial indices on active templates only
- Materialized views for usage statistics
- Connection pooling for concurrent access

### Monitoring
- Track template generation time
- Monitor cache hit rates
- Alert on performance degradation
- Usage pattern analysis for optimization

## Security Considerations

### Access Control
- Product-level isolation via tenant_key
- Role-based template access
- Audit trail for all modifications
- Sensitive variable masking

### Template Injection Prevention
- Variable validation before substitution
- Template content sanitization
- SQL injection prevention via parameterized queries
- XSS prevention for web interfaces

## Testing Requirements

### Unit Tests
- Template CRUD operations
- Variable substitution
- Augmentation application
- Version control operations

### Integration Tests
- Orchestrator integration
- Multi-tenant isolation
- Performance benchmarks
- Cache behavior

### Load Tests
- Concurrent template generation
- Cache performance under load
- Database connection pooling
- Memory usage patterns

## Success Metrics

1. ✅ All 5 base templates migrated to database
2. ✅ <0.1ms average template generation time
3. ✅ 100% backward compatibility maintained
4. ✅ Zero cross-tenant data leakage
5. ✅ Complete audit trail for changes
6. ✅ MCP tools fully functional
7. ✅ Augmentation system operational
8. ✅ Usage statistics tracking active

## Next Steps for Implementer

1. Create Alembic migration script for new tables
2. Add SQLAlchemy models to models.py
3. Implement MCP tools in order of priority
4. Create migration script for existing templates
5. Update orchestrator.py integration
6. Write comprehensive tests
7. Document usage examples

## Appendix: Template Migration Mapping

### From mission_templates.py to Database

| Python Class | Database Table | Template Name | Category | Role |
|--------------|---------------|---------------|----------|------|
| ORCHESTRATOR_TEMPLATE | agent_templates | orchestrator | role | orchestrator |
| ANALYZER_TEMPLATE | agent_templates | analyzer | role | analyzer |
| IMPLEMENTER_TEMPLATE | agent_templates | implementer | role | implementer |
| TESTER_TEMPLATE | agent_templates | tester | role | tester |
| REVIEWER_TEMPLATE | agent_templates | reviewer | role | reviewer |

### Variable Mapping

Current variables in templates:
- `{project_name}` - Project name
- `{project_mission}` - Project mission/goals
- `{product_name}` - Product being built
- `{custom_mission}` - Custom mission override

These will be stored in the `variables` JSON column as:
```json
["project_name", "project_mission", "product_name", "custom_mission"]
```

## Conclusion

This design provides a robust, scalable, and maintainable template management system that:
- Preserves all existing functionality
- Adds versioning and audit capabilities
- Enables runtime customization via augmentations
- Provides comprehensive usage analytics
- Maintains strict multi-tenant isolation
- Achieves sub-millisecond performance targets

The implementer should proceed with this design to build the template management system.