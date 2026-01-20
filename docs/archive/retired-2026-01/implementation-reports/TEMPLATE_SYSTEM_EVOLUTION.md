# Template System Evolution & Database-Backed Templates

**Document Version**: 10_13_2025  
**Status**: Single Source of Truth  
**Last Updated**: 2025-01-05 (Harmonized)
**Harmonization Status**: ✅ Aligned with codebase

---

## Quick Links to Harmonized Documents

- **[Simple_Vision.md](../handovers/Simple_Vision.md)** - User journey & agent template explanation
- **[start_to_finish_agent_FLOW.md](../handovers/start_to_finish_agent_FLOW.md)** - Technical verification of template seeding flow

**Current Default Agent Templates** (verified in codebase):
- **6 templates seeded per tenant**: orchestrator, implementer, tester, analyzer, reviewer, documenter
- **Seeding trigger**: First user creation (auth.py:910 calls seed_tenant_templates())
- **Source**: `src/giljo_mcp/template_seeder.py::_get_default_templates_v103()`
- **Migration**: `6adac1467121` adds cli_tool, background_color columns to AgentTemplate table

**Agent Template Export** (Handover 0102):
- 15-minute token TTL for secure downloads
- Supports Claude Code, Codex CLI, Gemini CLI
- See Simple_Vision.md for complete export workflow

---

## Overview

GiljoAI MCP v3.0 evolved from a **file-based template system** to a **unified database-backed template management system**. The new `template_manager.py` replaces the legacy `mission_templates.py` system, providing dynamic template creation, multi-tenant isolation, and AI tool preferences.

### Evolution Summary

**Before**: Multiple overlapping template systems
- `mission_templates.py` - Static file-based templates
- Hardcoded agent configurations 
- No runtime template modification
- Limited template customization

**After**: Unified database-backed system
- `template_manager.py` - Single source of truth (342 lines)
- Dynamic template CRUD operations
- Multi-tenant template isolation
- AI tool preferences per template
- Runtime template modification

---

## Architecture Transformation

### Legacy System (Deprecated)

**File Structure**:
```
src/giljo_mcp/
├── mission_templates.py        # ❌ DEPRECATED
├── agent_profiles/             # ❌ OBSOLETE  
│   ├── orchestrator.py
│   ├── implementer.py
│   └── tester.py
└── template_variations/        # ❌ REMOVED
    ├── frontend_specialist.py
    └── database_expert.py
```

**Problems with Legacy System**:
- ❌ **Multiple Sources of Truth**: 3+ overlapping template systems
- ❌ **Static Configuration**: No runtime template changes
- ❌ **No Multi-Tenancy**: Templates shared across all users
- ❌ **Limited Customization**: Hardcoded agent behaviors
- ❌ **Maintenance Overhead**: Duplicate template definitions

### Modern System (Current)

**File Structure**:
```
src/giljo_mcp/
├── template_manager.py         # ✅ SINGLE SOURCE OF TRUTH
├── models.py                   # ✅ Database-backed templates
└── tools/
    ├── template.py             # ✅ Template MCP tools
    └── agent.py                # ✅ Agent orchestration tools
```

**Benefits of Modern System**:
- ✅ **Single Source of Truth**: `template_manager.py` manages everything
- ✅ **Dynamic Templates**: Runtime creation and modification
- ✅ **Multi-Tenant Isolation**: Templates scoped to tenant_key
- ✅ **AI Tool Integration**: Per-template tool preferences
- ✅ **Performance Optimized**: <0.08ms template retrieval

---

## Template Manager Implementation

### Core Architecture

**Location**: `src/giljo_mcp/template_manager.py` (342 lines)

**Key Components**:
```python
class TemplateManager:
    """Unified template management system"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self._template_cache = {}  # Performance optimization
        self._cache_ttl = 3600     # 1-hour cache TTL
    
    # Core CRUD operations
    async def create_template(self, template_data: dict, tenant_key: str) -> AgentTemplate
    async def get_template(self, name: str, tenant_key: str) -> Optional[AgentTemplate]  
    async def update_template(self, template_id: str, updates: dict, tenant_key: str) -> AgentTemplate
    async def delete_template(self, template_id: str, tenant_key: str) -> bool
    async def list_templates(self, tenant_key: str, role_filter: str = None) -> List[AgentTemplate]
    
    # Template processing
    async def render_template(self, template: AgentTemplate, context: dict) -> str
    async def validate_template(self, template_content: str) -> dict
    
    # AI tool integration
    async def get_templates_for_tool(self, tool_name: str, tenant_key: str) -> List[AgentTemplate]
    async def set_template_tool_preference(self, template_id: str, tool_name: str, tenant_key: str) -> bool
```

### Database Schema

**AgentTemplate Model**:
```python
class AgentTemplate(Base):
    __tablename__ = 'agent_templates'
    
    # Primary identification
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_key = Column(String(36), nullable=False, index=True)  # Multi-tenant isolation
    
    # Template metadata
    name = Column(String(255), nullable=False)
    role = Column(String(100), nullable=False)  # orchestrator, implementer, tester, etc.
    description = Column(Text)
    version = Column(String(20), default="1.0.0")
    
    # AI tool preferences (NEW in v3.0)
    preferred_tool = Column(String(50), default="claude")  # claude, codex, gemini
    
    # Template content
    system_prompt = Column(Text, nullable=False)
    context_filters = Column(JSON, default=list)      # Role-based context filtering
    tools_enabled = Column(JSON, default=list)        # MCP tools for this role
    
    # Configuration
    max_context_tokens = Column(Integer, default=50000)
    temperature = Column(Float, default=0.7)
    max_response_tokens = Column(Integer, default=4000)
    
    # Template behavior
    handoff_triggers = Column(JSON, default=list)     # Auto-handoff conditions
    specialization_areas = Column(JSON, default=list) # Areas of expertise
    
    # Metadata
    is_active = Column(Boolean, default=True)
    created_by = Column(String(36))  # User ID
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_templates_tenant_role', 'tenant_key', 'role'),
        Index('idx_templates_tenant_name', 'tenant_key', 'name'),
        Index('idx_templates_tenant_tool', 'tenant_key', 'preferred_tool'),
        Index('idx_templates_active', 'is_active', 'tenant_key'),
    )
```

### Template CRUD Operations

**Create Template**:
```python
async def create_template(
    self, 
    template_data: dict, 
    tenant_key: str,
    created_by: str = None
) -> AgentTemplate:
    """Create new agent template with validation"""
    
    # Validate template data
    validation_result = await self.validate_template(template_data['system_prompt'])
    if not validation_result['valid']:
        raise ValueError(f"Invalid template: {validation_result['errors']}")
    
    # Check for duplicate names within tenant
    existing = await self.get_template(template_data['name'], tenant_key)
    if existing:
        raise ValueError(f"Template '{template_data['name']}' already exists")
    
    # Create template instance
    template = AgentTemplate(
        tenant_key=tenant_key,
        name=template_data['name'],
        role=template_data['role'],
        description=template_data.get('description', ''),
        preferred_tool=template_data.get('preferred_tool', 'claude'),
        system_prompt=template_data['system_prompt'],
        context_filters=template_data.get('context_filters', []),
        tools_enabled=template_data.get('tools_enabled', []),
        max_context_tokens=template_data.get('max_context_tokens', 50000),
        temperature=template_data.get('temperature', 0.7),
        handoff_triggers=template_data.get('handoff_triggers', []),
        specialization_areas=template_data.get('specialization_areas', []),
        created_by=created_by
    )
    
    async with self.db_manager.get_session_async() as session:
        session.add(template)
        await session.commit()
        await session.refresh(template)
    
    # Update cache
    self._update_cache(template)
    
    return template
```

**Get Template with Caching**:
```python
async def get_template(
    self, 
    name: str, 
    tenant_key: str
) -> Optional[AgentTemplate]:
    """Get template with performance caching"""
    
    cache_key = f"{tenant_key}:{name}"
    
    # Check cache first
    if cache_key in self._template_cache:
        cached_entry = self._template_cache[cache_key]
        if time.time() - cached_entry['timestamp'] < self._cache_ttl:
            return cached_entry['template']
    
    # Query database
    async with self.db_manager.get_session_async() as session:
        stmt = select(AgentTemplate).where(
            and_(
                AgentTemplate.name == name,
                AgentTemplate.tenant_key == tenant_key,
                AgentTemplate.is_active == True
            )
        )
        result = await session.execute(stmt)
        template = result.scalar_one_or_none()
    
    # Update cache
    if template:
        self._update_cache(template)
    
    return template

def _update_cache(self, template: AgentTemplate):
    """Update template cache with TTL"""
    cache_key = f"{template.tenant_key}:{template.name}"
    self._template_cache[cache_key] = {
        'template': template,
        'timestamp': time.time()
    }
```

**Template Rendering**:
```python
async def render_template(
    self, 
    template: AgentTemplate, 
    context: dict
) -> str:
    """Render template with dynamic context injection"""
    
    # Base template variables
    template_vars = {
        'agent_role': template.role,
        'tenant_key': template.tenant_key,
        'preferred_tool': template.preferred_tool,
        'max_context_tokens': template.max_context_tokens,
        'tools_enabled': template.tools_enabled,
        'specialization_areas': template.specialization_areas
    }
    
    # Merge with provided context
    template_vars.update(context)
    
    # Apply context filters
    if template.context_filters:
        filtered_context = self._apply_context_filters(
            template_vars, 
            template.context_filters
        )
        template_vars.update(filtered_context)
    
    # Render template using Jinja2
    try:
        from jinja2 import Template
        jinja_template = Template(template.system_prompt)
        rendered = jinja_template.render(**template_vars)
        
        return rendered
        
    except Exception as e:
        raise ValueError(f"Template rendering failed: {str(e)}")

def _apply_context_filters(self, context: dict, filters: list) -> dict:
    """Apply role-based context filtering"""
    
    filtered_context = {}
    
    for filter_rule in filters:
        filter_type = filter_rule.get('type')
        filter_value = filter_rule.get('value')
        
        if filter_type == 'include_keys':
            # Only include specified keys
            for key in filter_value:
                if key in context:
                    filtered_context[key] = context[key]
                    
        elif filter_type == 'exclude_keys':
            # Exclude specified keys
            filtered_context.update({
                k: v for k, v in context.items() 
                if k not in filter_value
            })
            
        elif filter_type == 'role_specific':
            # Role-specific context inclusion
            role = context.get('agent_role')
            if role and role in filter_value:
                filtered_context.update(filter_value[role])
    
    return filtered_context
```

---

## Multi-Tenant Template System

### Tenant Isolation

**Template Scoping**:
```python
async def list_templates(
    self, 
    tenant_key: str, 
    role_filter: str = None,
    tool_filter: str = None
) -> List[AgentTemplate]:
    """List templates with multi-tenant filtering"""
    
    async with self.db_manager.get_session_async() as session:
        stmt = select(AgentTemplate).where(
            and_(
                AgentTemplate.tenant_key == tenant_key,
                AgentTemplate.is_active == True
            )
        )
        
        # Apply optional filters
        if role_filter:
            stmt = stmt.where(AgentTemplate.role == role_filter)
        
        if tool_filter:
            stmt = stmt.where(AgentTemplate.preferred_tool == tool_filter)
        
        # Order by creation date (newest first)
        stmt = stmt.order_by(AgentTemplate.created_at.desc())
        
        result = await session.execute(stmt)
        templates = result.scalars().all()
    
    return list(templates)
```

### Cross-Tenant Template Sharing

**System Templates**:
```python
async def get_system_templates(self) -> List[AgentTemplate]:
    """Get system-wide templates available to all tenants"""
    
    async with self.db_manager.get_session_async() as session:
        stmt = select(AgentTemplate).where(
            and_(
                AgentTemplate.tenant_key == "system",  # Special tenant for system templates
                AgentTemplate.is_active == True
            )
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

async def copy_system_template_to_tenant(
    self, 
    system_template_id: str, 
    target_tenant: str,
    customizations: dict = None
) -> AgentTemplate:
    """Copy system template to specific tenant with optional customizations"""
    
    # Get system template
    async with self.db_manager.get_session_async() as session:
        stmt = select(AgentTemplate).where(
            and_(
                AgentTemplate.id == system_template_id,
                AgentTemplate.tenant_key == "system"
            )
        )
        result = await session.execute(stmt)
        system_template = result.scalar_one_or_none()
    
    if not system_template:
        raise ValueError(f"System template {system_template_id} not found")
    
    # Create tenant-specific copy
    tenant_template_data = {
        'name': f"{system_template.name}_copy",
        'role': system_template.role,
        'description': system_template.description,
        'preferred_tool': system_template.preferred_tool,
        'system_prompt': system_template.system_prompt,
        'context_filters': system_template.context_filters,
        'tools_enabled': system_template.tools_enabled,
        'max_context_tokens': system_template.max_context_tokens,
        'temperature': system_template.temperature,
        'handoff_triggers': system_template.handoff_triggers,
        'specialization_areas': system_template.specialization_areas
    }
    
    # Apply customizations if provided
    if customizations:
        tenant_template_data.update(customizations)
    
    return await self.create_template(tenant_template_data, target_tenant)
```

---

## AI Tool Integration

### Template-Level Tool Preferences

**Tool Assignment**:
```python
async def set_template_tool_preference(
    self, 
    template_id: str, 
    tool_name: str, 
    tenant_key: str
) -> bool:
    """Set AI tool preference for specific template"""
    
    if tool_name not in ['claude', 'codex', 'gemini']:
        raise ValueError(f"Unsupported AI tool: {tool_name}")
    
    async with self.db_manager.get_session_async() as session:
        stmt = select(AgentTemplate).where(
            and_(
                AgentTemplate.id == template_id,
                AgentTemplate.tenant_key == tenant_key
            )
        )
        result = await session.execute(stmt)
        template = result.scalar_one_or_none()
        
        if not template:
            return False
        
        template.preferred_tool = tool_name
        template.updated_at = func.now()
        
        await session.commit()
        
        # Clear cache for this template
        cache_key = f"{tenant_key}:{template.name}"
        if cache_key in self._template_cache:
            del self._template_cache[cache_key]
    
    return True

async def get_templates_for_tool(
    self, 
    tool_name: str, 
    tenant_key: str
) -> List[AgentTemplate]:
    """Get all templates configured for specific AI tool"""
    
    async with self.db_manager.get_session_async() as session:
        stmt = select(AgentTemplate).where(
            and_(
                AgentTemplate.tenant_key == tenant_key,
                AgentTemplate.preferred_tool == tool_name,
                AgentTemplate.is_active == True
            )
        ).order_by(AgentTemplate.role, AgentTemplate.name)
        
        result = await session.execute(stmt)
        return list(result.scalars().all())
```

### Tool-Specific Template Rendering

**Claude Code Templates**:
```python
def _render_claude_template(self, template: AgentTemplate, context: dict) -> str:
    """Render template optimized for Claude Code CLI"""
    
    claude_context = {
        **context,
        'supports_sub_agents': True,
        'real_time_updates': True,
        'mcp_tools_available': template.tools_enabled,
        'orchestration_mode': 'sub_agent'
    }
    
    return self.render_template(template, claude_context)

def _render_codex_template(self, template: AgentTemplate, context: dict) -> str:
    """Render template optimized for CODEX CLI"""
    
    codex_context = {
        **context,
        'supports_sub_agents': False,
        'orchestration_mode': 'manual',
        'coordination_required': True,
        'copy_paste_workflow': True
    }
    
    # Add manual coordination instructions
    manual_instructions = self._generate_manual_coordination_guide(template)
    codex_context['manual_instructions'] = manual_instructions
    
    return self.render_template(template, codex_context)

def _render_gemini_template(self, template: AgentTemplate, context: dict) -> str:
    """Render template optimized for Gemini CLI"""
    
    gemini_context = {
        **context,
        'supports_sub_agents': False,
        'orchestration_mode': 'guided',
        'analysis_focused': True,
        'context_sharing': True
    }
    
    return self.render_template(template, gemini_context)
```

---

## Template Examples

### Orchestrator Template

**Role**: Central coordination and project management

```python
ORCHESTRATOR_TEMPLATE = {
    'name': 'orchestrator_v3',
    'role': 'orchestrator',
    'preferred_tool': 'claude',
    'description': 'Central agent for project coordination and multi-agent orchestration',
    'system_prompt': '''
You are a Project Orchestrator for GiljoAI MCP, coordinating multiple specialized agents to complete complex development projects.

## Your Role & Responsibilities

**Primary Function**: Coordinate specialized agents to achieve project goals efficiently
- Analyze project requirements and break into agent-specific tasks
- Assign work to appropriate specialists (Database, API, Frontend, Testing, etc.)
- Monitor progress and handle agent handoffs when context limits approached
- Ensure project coherence and integration between agent contributions

## Available Specialist Agents

{% for tool in tools_enabled %}
- **{{ tool.name }}**: {{ tool.description }}
{% endfor %}

## Project Context

**Tenant**: {{ tenant_key }}
**Preferred AI Tool**: {{ preferred_tool }}
**Max Context**: {{ max_context_tokens }} tokens
**Project**: {{ project_name if project_name else "Not specified" }}

## Orchestration Guidelines

1. **Task Breakdown**: Analyze requirements and create specific missions for specialists
2. **Agent Selection**: Choose appropriate agents based on task requirements and availability
3. **Context Management**: Monitor token usage and trigger handoffs at 80% context utilization
4. **Integration**: Ensure specialist outputs integrate coherently
5. **Quality Control**: Review specialist work before final integration

## Handoff Triggers
{% for trigger in handoff_triggers %}
- {{ trigger }}
{% endfor %}

## Coordination Protocol

When assigning tasks to specialists:
1. Provide clear, specific mission statements
2. Include relevant project context and constraints
3. Specify expected deliverables and success criteria
4. Coordinate dependencies between agents
5. Handle integration and conflict resolution

Begin by analyzing the current project requirements and identifying the most appropriate specialist agents to engage.
''',
    'context_filters': [
        {
            'type': 'role_specific',
            'value': {
                'orchestrator': ['project_overview', 'agent_status', 'task_dependencies']
            }
        }
    ],
    'tools_enabled': [
        'create_project', 'ensure_agent', 'assign_job', 'send_message', 
        'get_messages', 'agent_health', 'handoff', 'project_status'
    ],
    'specialization_areas': [
        'project_management', 'agent_coordination', 'task_breakdown', 
        'integration_management', 'quality_control'
    ],
    'handoff_triggers': [
        'context_utilization > 80%',
        'task_complexity_exceeds_expertise',
        'specialist_required',
        'integration_phase_reached'
    ]
}
```

### Database Expert Template

**Role**: Database design, optimization, and data management

```python
DATABASE_EXPERT_TEMPLATE = {
    'name': 'database_expert_v3',
    'role': 'database_expert', 
    'preferred_tool': 'claude',
    'description': 'Database specialist for schema design, optimization, and data management',
    'system_prompt': '''
You are a Database Expert specializing in PostgreSQL database design, optimization, and data architecture for GiljoAI MCP projects.

## Your Expertise Areas

**Database Design**:
- Normalized schema design with proper relationships
- Multi-tenant database architecture with tenant_key isolation
- Index optimization for query performance
- Data integrity constraints and validation

**PostgreSQL Specialization**:
- PostgreSQL 18 features and optimizations
- JSON/JSONB column usage for flexible data
- Advanced indexing (GIN, GiST, partial indexes)
- Query optimization and performance tuning

**GiljoAI MCP Database Patterns**:
- Tenant isolation at row level (tenant_key filtering)
- Agent state tracking and context management  
- Template storage and versioning
- Message queue and task management tables

## Project Context

**Database Type**: PostgreSQL 18
**Multi-Tenant**: {{ tenant_key }} isolation required
**AI Tool**: {{ preferred_tool }}

## Your Responsibilities

1. **Schema Design**: Create normalized, efficient database schemas
2. **Multi-Tenant Architecture**: Ensure proper tenant_key isolation
3. **Performance Optimization**: Design indexes and optimize queries
4. **Data Migration**: Handle schema changes and data migrations
5. **Integration**: Work with API developers for data layer integration

## Database Standards

```sql
-- Example multi-tenant table structure
CREATE TABLE example_table (
    id VARCHAR(36) PRIMARY KEY,
    tenant_key VARCHAR(36) NOT NULL,  -- Required for isolation
    -- ... other columns
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Required index for tenant isolation
CREATE INDEX idx_example_tenant ON example_table(tenant_key);
```

## Tools Available
{% for tool in tools_enabled %}
- {{ tool }}
{% endfor %}

## Handoff Conditions
- When database schema is complete and ready for API integration
- When context approaches token limit ({{ max_context_tokens }})
- When specialized frontend or API work is required

Focus on creating robust, scalable database solutions that support the multi-tenant architecture of GiljoAI MCP.
''',
    'context_filters': [
        {
            'type': 'include_keys',
            'value': ['database_schema', 'existing_models', 'performance_requirements', 'multi_tenant_config']
        },
        {
            'type': 'exclude_keys', 
            'value': ['frontend_components', 'ui_styling', 'javascript_code']
        }
    ],
    'tools_enabled': [
        'get_product_config', 'get_context', 'send_message', 
        'git_status', 'git_commit', 'complete_message'
    ],
    'specialization_areas': [
        'postgresql', 'database_design', 'schema_optimization', 
        'multi_tenant_architecture', 'data_modeling', 'query_optimization'
    ],
    'handoff_triggers': [
        'schema_design_complete',
        'database_ready_for_api_integration', 
        'context_utilization > 80%'
    ]
}
```

### Frontend Specialist Template

**Role**: UI/UX development and frontend implementation

```python
FRONTEND_SPECIALIST_TEMPLATE = {
    'name': 'frontend_specialist_v3',
    'role': 'frontend_specialist',
    'preferred_tool': 'claude',
    'description': 'Frontend specialist for Vue 3, Vuetify, and user interface development',
    'system_prompt': '''
You are a Frontend Specialist focused on Vue 3 + Vuetify development for GiljoAI MCP applications.

## Your Technical Stack

**Core Technologies**:
- Vue 3 with Composition API
- Vuetify 3 (Material Design 3)
- TypeScript/JavaScript
- Vite build system
- Pinia state management

**GiljoAI MCP Frontend Architecture**:
- Real-time updates via WebSocket
- JWT authentication integration
- Multi-tenant UI data isolation
- Responsive design (mobile, tablet, desktop)
- Dark/light theme support

## Project Context

**Frontend Framework**: Vue 3 + Vuetify 3
**State Management**: Pinia
**Build Tool**: Vite
**Tenant**: {{ tenant_key }}
**AI Tool**: {{ preferred_tool }}

## Your Responsibilities

1. **Component Development**: Create reusable Vue 3 components
2. **State Management**: Implement Pinia stores for data flow
3. **API Integration**: Connect frontend to FastAPI backend
4. **WebSocket Integration**: Real-time updates for agent status
5. **Responsive Design**: Ensure mobile and desktop compatibility
6. **Authentication UI**: Login, password change, setup flows

## Component Architecture

```vue
<template>
  <v-container>
    <!-- Vuetify components following Material Design 3 -->
    <v-card>
      <v-card-title>{{ title }}</v-card-title>
      <v-card-text>
        <!-- Component content -->
      </v-card-text>
    </v-card>
  </v-container>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useStore } from '@/stores/example'

// Composition API pattern
const store = useStore()
const title = ref('Component Title')
</script>
```

## Design Standards

- **Material Design 3**: Follow Vuetify 3 design principles
- **Accessibility**: WCAG compliance for all components
- **Performance**: Lazy loading and code splitting
- **Responsive**: Mobile-first responsive design
- **Theme Support**: Dark/light mode compatibility

## Available Tools
{% for tool in tools_enabled %}
- {{ tool }}
{% endfor %}

## Integration Points

- **API Endpoints**: RESTful API communication
- **WebSocket**: Real-time agent status updates
- **Authentication**: JWT token management
- **Routing**: Vue Router with authentication guards

## Handoff Conditions
- When frontend implementation is complete and integrated with backend
- When context utilization approaches {{ max_context_tokens }} tokens  
- When backend API or database changes are required

Create modern, responsive user interfaces that provide excellent user experience for GiljoAI MCP's multi-agent orchestration capabilities.
''',
    'context_filters': [
        {
            'type': 'include_keys',
            'value': ['ui_requirements', 'design_system', 'api_endpoints', 'websocket_events']
        },
        {
            'type': 'exclude_keys',
            'value': ['database_schema', 'sql_queries', 'backend_logic']
        }
    ],
    'tools_enabled': [
        'get_product_config', 'get_context', 'send_message',
        'git_status', 'git_commit', 'complete_message'
    ],
    'specialization_areas': [
        'vue3', 'vuetify', 'javascript', 'typescript', 'responsive_design', 
        'websocket_integration', 'state_management', 'ui_ux_design'
    ],
    'handoff_triggers': [
        'frontend_implementation_complete',
        'api_integration_required',
        'context_utilization > 80%'
    ]
}
```

---

## MCP Tools Integration

### Template Management Tools

**Location**: `src/giljo_mcp/tools/template.py`

**Core Tools**:
```python
@mcp.tool()
async def create_template(
    name: str,
    role: str, 
    system_prompt: str,
    tenant_key: str,
    preferred_tool: str = "claude",
    description: str = "",
    context_filters: List[dict] = None,
    tools_enabled: List[str] = None
) -> dict:
    """Create new agent template"""
    
    template_manager = get_template_manager()
    
    template_data = {
        'name': name,
        'role': role,
        'description': description,
        'preferred_tool': preferred_tool,
        'system_prompt': system_prompt,
        'context_filters': context_filters or [],
        'tools_enabled': tools_enabled or []
    }
    
    try:
        template = await template_manager.create_template(template_data, tenant_key)
        
        return {
            'success': True,
            'template_id': template.id,
            'name': template.name,
            'role': template.role,
            'preferred_tool': template.preferred_tool,
            'message': f'Template "{name}" created successfully'
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'message': f'Failed to create template "{name}"'
        }

@mcp.tool()
async def get_template(name: str, tenant_key: str) -> dict:
    """Retrieve agent template by name"""
    
    template_manager = get_template_manager()
    
    try:
        template = await template_manager.get_template(name, tenant_key)
        
        if not template:
            return {
                'success': False,
                'message': f'Template "{name}" not found'
            }
        
        return {
            'success': True,
            'template': {
                'id': template.id,
                'name': template.name,
                'role': template.role,
                'description': template.description,
                'preferred_tool': template.preferred_tool,
                'system_prompt': template.system_prompt,
                'context_filters': template.context_filters,
                'tools_enabled': template.tools_enabled,
                'max_context_tokens': template.max_context_tokens,
                'specialization_areas': template.specialization_areas,
                'created_at': template.created_at.isoformat(),
                'updated_at': template.updated_at.isoformat()
            }
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'message': f'Failed to retrieve template "{name}"'
        }

@mcp.tool()
async def list_templates(
    tenant_key: str,
    role_filter: str = None,
    tool_filter: str = None
) -> dict:
    """List all templates for tenant with optional filters"""
    
    template_manager = get_template_manager()
    
    try:
        templates = await template_manager.list_templates(
            tenant_key=tenant_key,
            role_filter=role_filter,
            tool_filter=tool_filter
        )
        
        template_list = []
        for template in templates:
            template_list.append({
                'id': template.id,
                'name': template.name,
                'role': template.role,
                'description': template.description,
                'preferred_tool': template.preferred_tool,
                'specialization_areas': template.specialization_areas,
                'created_at': template.created_at.isoformat(),
                'is_active': template.is_active
            })
        
        return {
            'success': True,
            'templates': template_list,
            'count': len(template_list),
            'filters_applied': {
                'role': role_filter,
                'tool': tool_filter
            }
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'message': 'Failed to list templates'
        }

@mcp.tool()
async def update_template(
    template_id: str,
    tenant_key: str,
    updates: dict
) -> dict:
    """Update existing template"""
    
    template_manager = get_template_manager()
    
    try:
        template = await template_manager.update_template(
            template_id=template_id,
            updates=updates,
            tenant_key=tenant_key
        )
        
        return {
            'success': True,
            'template_id': template.id,
            'name': template.name,
            'message': f'Template "{template.name}" updated successfully'
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'message': f'Failed to update template {template_id}'
        }
```

---

## Performance & Optimization

### Template Caching

**Memory Cache Implementation**:
```python
class TemplateManager:
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self._template_cache = {}
        self._cache_ttl = 3600  # 1 hour
        self._cache_stats = {
            'hits': 0,
            'misses': 0,
            'invalidations': 0
        }
    
    async def get_template(self, name: str, tenant_key: str) -> Optional[AgentTemplate]:
        """Get template with performance caching"""
        
        cache_key = f"{tenant_key}:{name}"
        current_time = time.time()
        
        # Check cache
        if cache_key in self._template_cache:
            cached_entry = self._template_cache[cache_key]
            if current_time - cached_entry['timestamp'] < self._cache_ttl:
                self._cache_stats['hits'] += 1
                return cached_entry['template']
            else:
                # Cache expired
                del self._template_cache[cache_key]
        
        # Cache miss - query database
        self._cache_stats['misses'] += 1
        template = await self._query_template_from_db(name, tenant_key)
        
        if template:
            self._template_cache[cache_key] = {
                'template': template,
                'timestamp': current_time
            }
        
        return template
    
    def invalidate_cache(self, tenant_key: str = None, template_name: str = None):
        """Invalidate cache entries"""
        
        if tenant_key and template_name:
            # Invalidate specific template
            cache_key = f"{tenant_key}:{template_name}"
            if cache_key in self._template_cache:
                del self._template_cache[cache_key]
                self._cache_stats['invalidations'] += 1
        elif tenant_key:
            # Invalidate all templates for tenant
            keys_to_delete = [
                key for key in self._template_cache.keys()
                if key.startswith(f"{tenant_key}:")
            ]
            for key in keys_to_delete:
                del self._template_cache[key]
                self._cache_stats['invalidations'] += 1
        else:
            # Clear entire cache
            self._cache_stats['invalidations'] += len(self._template_cache)
            self._template_cache.clear()
    
    def get_cache_stats(self) -> dict:
        """Get cache performance statistics"""
        total_requests = self._cache_stats['hits'] + self._cache_stats['misses']
        hit_rate = self._cache_stats['hits'] / total_requests if total_requests > 0 else 0
        
        return {
            'hits': self._cache_stats['hits'],
            'misses': self._cache_stats['misses'],
            'hit_rate': f"{hit_rate:.2%}",
            'cached_items': len(self._template_cache),
            'invalidations': self._cache_stats['invalidations']
        }
```

### Database Optimization

**Query Performance**:
```sql
-- Optimized indexes for template queries
CREATE INDEX CONCURRENTLY idx_templates_tenant_role_active 
ON agent_templates(tenant_key, role, is_active) 
WHERE is_active = true;

CREATE INDEX CONCURRENTLY idx_templates_tenant_tool_active 
ON agent_templates(tenant_key, preferred_tool, is_active) 
WHERE is_active = true;

CREATE INDEX CONCURRENTLY idx_templates_search 
ON agent_templates 
USING gin(to_tsvector('english', name || ' ' || description || ' ' || role));

-- Query performance analysis
EXPLAIN (ANALYZE, BUFFERS) 
SELECT * FROM agent_templates 
WHERE tenant_key = 'default' 
  AND role = 'orchestrator' 
  AND is_active = true;
```

**Template Rendering Performance**:
```python
import cProfile
import pstats
from functools import wraps

def profile_template_rendering(func):
    """Decorator to profile template rendering performance"""
    
    @wraps(func)
    async def wrapper(*args, **kwargs):
        profiler = cProfile.Profile()
        profiler.enable()
        
        try:
            result = await func(*args, **kwargs)
            return result
        finally:
            profiler.disable()
            
            # Log performance stats
            stats = pstats.Stats(profiler)
            stats.sort_stats('cumulative')
            
            # Extract key metrics
            total_calls = stats.total_calls
            total_time = stats.total_tt
            
            logger.info(f"Template rendering: {total_calls} calls, {total_time:.4f}s total")
    
    return wrapper

@profile_template_rendering
async def render_template(self, template: AgentTemplate, context: dict) -> str:
    """Profiled template rendering"""
    # ... template rendering logic
```

---

## Migration Guide

### From Legacy System

**Migration Script**:
```python
async def migrate_legacy_templates():
    """Migrate from legacy mission_templates.py to database-backed system"""
    
    # Import legacy templates
    from giljo_mcp.legacy import mission_templates
    
    template_manager = TemplateManager(db_manager)
    migration_results = []
    
    # Convert each legacy template
    for legacy_template in mission_templates.TEMPLATES:
        try:
            # Map legacy format to new format
            new_template_data = {
                'name': legacy_template['name'],
                'role': legacy_template.get('role', 'general'),
                'description': legacy_template.get('description', ''),
                'preferred_tool': 'claude',  # Default to Claude
                'system_prompt': legacy_template['prompt'],
                'context_filters': [],  # Will need manual configuration
                'tools_enabled': legacy_template.get('tools', []),
                'max_context_tokens': legacy_template.get('max_tokens', 50000)
            }
            
            # Create new template
            new_template = await template_manager.create_template(
                template_data=new_template_data,
                tenant_key='default'
            )
            
            migration_results.append({
                'legacy_name': legacy_template['name'],
                'new_id': new_template.id,
                'status': 'success'
            })
            
        except Exception as e:
            migration_results.append({
                'legacy_name': legacy_template.get('name', 'unknown'),
                'error': str(e),
                'status': 'failed'
            })
    
    return migration_results

# Migration verification
async def verify_migration():
    """Verify migration completed successfully"""
    
    template_manager = TemplateManager(db_manager)
    
    # Check template count
    templates = await template_manager.list_templates('default')
    print(f"Migrated {len(templates)} templates")
    
    # Verify key templates exist
    key_roles = ['orchestrator', 'database_expert', 'frontend_specialist', 'tester']
    for role in key_roles:
        role_templates = await template_manager.list_templates('default', role_filter=role)
        if role_templates:
            print(f"✅ {role}: {len(role_templates)} templates")
        else:
            print(f"❌ {role}: No templates found")
    
    return True
```

---

## Testing Strategy

### Unit Tests

**Template Manager Tests**:
```python
import pytest
from unittest.mock import AsyncMock, MagicMock

class TestTemplateManager:
    
    @pytest.fixture
    async def template_manager(self):
        db_manager = AsyncMock()
        return TemplateManager(db_manager)
    
    async def test_create_template(self, template_manager):
        """Test template creation"""
        
        template_data = {
            'name': 'test_template',
            'role': 'tester',
            'system_prompt': 'You are a test agent',
            'preferred_tool': 'claude'
        }
        
        template = await template_manager.create_template(
            template_data, 
            tenant_key='test_tenant'
        )
        
        assert template.name == 'test_template'
        assert template.role == 'tester'
        assert template.tenant_key == 'test_tenant'
        assert template.preferred_tool == 'claude'
    
    async def test_get_template_caching(self, template_manager):
        """Test template caching behavior"""
        
        # First call should hit database
        template1 = await template_manager.get_template('test', 'tenant1')
        
        # Second call should hit cache
        template2 = await template_manager.get_template('test', 'tenant1')
        
        # Verify cache stats
        stats = template_manager.get_cache_stats()
        assert stats['hits'] >= 1
        assert stats['hit_rate'] > '0%'
    
    async def test_template_rendering(self, template_manager):
        """Test template rendering with context"""
        
        template = AgentTemplate(
            name='test_template',
            role='tester',
            system_prompt='Hello {{ agent_role }}, tenant: {{ tenant_key }}',
            tenant_key='test_tenant'
        )
        
        context = {'additional_info': 'test context'}
        
        rendered = await template_manager.render_template(template, context)
        
        assert 'Hello tester' in rendered
        assert 'tenant: test_tenant' in rendered
    
    async def test_multi_tenant_isolation(self, template_manager):
        """Test tenant isolation in template queries"""
        
        # Create templates for different tenants
        await template_manager.create_template({
            'name': 'shared_name',
            'role': 'tester',
            'system_prompt': 'Tenant A template'
        }, 'tenant_a')
        
        await template_manager.create_template({
            'name': 'shared_name',
            'role': 'tester', 
            'system_prompt': 'Tenant B template'
        }, 'tenant_b')
        
        # Verify isolation
        template_a = await template_manager.get_template('shared_name', 'tenant_a')
        template_b = await template_manager.get_template('shared_name', 'tenant_b')
        
        assert 'Tenant A' in template_a.system_prompt
        assert 'Tenant B' in template_b.system_prompt
        assert template_a.tenant_key != template_b.tenant_key
```

### Integration Tests

**Database Integration**:
```python
async def test_template_crud_operations():
    """Test full CRUD cycle with real database"""
    
    # Use test database
    test_db_manager = DatabaseManager("postgresql://test:test@localhost/giljo_test")
    template_manager = TemplateManager(test_db_manager)
    
    # Create
    template_data = {
        'name': 'integration_test',
        'role': 'tester',
        'system_prompt': 'Integration test template',
        'preferred_tool': 'claude'
    }
    
    created = await template_manager.create_template(template_data, 'test_tenant')
    assert created.id is not None
    
    # Read
    retrieved = await template_manager.get_template('integration_test', 'test_tenant')
    assert retrieved.id == created.id
    assert retrieved.system_prompt == 'Integration test template'
    
    # Update
    updates = {'system_prompt': 'Updated test template'}
    updated = await template_manager.update_template(created.id, updates, 'test_tenant')
    assert updated.system_prompt == 'Updated test template'
    
    # Delete
    deleted = await template_manager.delete_template(created.id, 'test_tenant')
    assert deleted is True
    
    # Verify deletion
    not_found = await template_manager.get_template('integration_test', 'test_tenant')
    assert not_found is None
```

---

## Future Enhancements

### Planned Features

**Template Versioning**:
- Version control for template changes
- Rollback capabilities
- Change history tracking
- Diff visualization

**Advanced Template Features**:
- Template inheritance and composition
- Conditional template logic  
- Dynamic context injection
- Template performance analytics

**AI Tool Optimization**:
- Tool-specific template optimization
- Performance profiling per tool
- Automatic tool selection based on task
- Cross-tool template compatibility

### Experimental Features

**Template Marketplace**:
- Community template sharing
- Template ratings and reviews
- Import/export functionality
- Template discovery and search

**AI-Assisted Template Creation**:
- Generate templates from task descriptions
- Optimize templates based on usage patterns
- Suggest template improvements
- Automated template testing

---

**See Also**:
- [AI Tool Configuration Management](AI_TOOL_CONFIGURATION_MANAGEMENT.md) - AI tool integration with templates
- [Server Architecture & Tech Stack](SERVER_ARCHITECTURE_TECH_STACK.md) - Database and technical implementation
- [GiljoAI MCP Purpose](GILJOAI_MCP_PURPOSE.md) - Multi-agent orchestration context
- [User Structures & Tenants](USER_STRUCTURES_TENANTS.md) - Multi-tenant template isolation

---

*This document provides comprehensive coverage of GiljoAI MCP's template system evolution as the single source of truth for the October 13, 2025 documentation harmonization.*