# Template Management API Reference

## Overview

The GiljoAI MCP Template Management System provides a unified, database-backed solution for managing agent mission templates. This API replaces the previous hardcoded Python templates with a flexible, performant, and multi-tenant capable system.

**Single Source of Truth**: `src/giljo_mcp/template_manager.py`

## MCP Tools

### 1. list_agent_templates

Lists all available agent templates for the current product.

```python
@mcp.tool
async def list_agent_templates(
    category: Optional[str] = None,
    role: Optional[str] = None,
    is_active: bool = True
) -> List[Dict]
```

**Parameters:**
- `category` (optional): Filter by category ('role', 'project_type', 'custom')
- `role` (optional): Filter by specific role (e.g., 'orchestrator', 'analyzer')
- `is_active`: Only show active templates (default: True)

**Returns:**
```json
[
  {
    "id": "uuid",
    "name": "analyzer",
    "category": "role",
    "description": "General code analysis agent",
    "usage_count": 42,
    "avg_generation_ms": 0.045,
    "version": "1.0.0"
  }
]
```

**Example:**
```python
templates = await mcp.call_tool("list_agent_templates", {
    "category": "role",
    "is_active": true
})
```

### 2. get_agent_template

Retrieves a specific template with optional runtime augmentation.

```python
@mcp.tool
async def get_agent_template(
    name: str,
    augmentations: Optional[str] = None,
    variables: Optional[Dict[str, str]] = None
) -> str
```

**Parameters:**
- `name`: Template name (e.g., 'orchestrator', 'implementer')
- `augmentations` (optional): Additional instructions to append
- `variables` (optional): Variable substitutions for {placeholders}

**Returns:**
Complete template content with augmentations and substitutions applied.

**Example:**
```python
template = await mcp.call_tool("get_agent_template", {
    "name": "implementer",
    "augmentations": "Focus on test coverage and documentation",
    "variables": {
        "project_name": "GiljoAI MCP",
        "primary_goal": "Build template system"
    }
})
```

### 3. create_agent_template

Creates a new reusable agent template.

```python
@mcp.tool
async def create_agent_template(
    name: str,
    category: str,
    template_content: str,
    description: Optional[str] = None,
    role: Optional[str] = None,
    behavioral_rules: Optional[List[str]] = None,
    success_criteria: Optional[List[str]] = None
) -> Dict
```

**Parameters:**
- `name`: Unique template name
- `category`: Template category ('role', 'project_type', 'custom')
- `template_content`: Template text with {variable} placeholders
- `description` (optional): Human-readable description
- `role` (optional): Associated agent role
- `behavioral_rules` (optional): List of behavioral guidelines
- `success_criteria` (optional): List of success metrics

**Returns:**
```json
{
  "id": "uuid",
  "name": "security_specialist",
  "created": true,
  "version": "1.0.0"
}
```

**Example:**
```python
result = await mcp.call_tool("create_agent_template", {
    "name": "security_auditor",
    "category": "custom",
    "template_content": "You are a security specialist for {project_name}...",
    "description": "Security-focused code review agent",
    "behavioral_rules": ["Always check for SQL injection", "Verify auth on all endpoints"],
    "success_criteria": ["No security vulnerabilities found", "All auth properly implemented"]
})
```

### 4. update_agent_template

Updates an existing template (automatically archives previous version).

```python
@mcp.tool
async def update_agent_template(
    name: str,
    template_content: Optional[str] = None,
    description: Optional[str] = None,
    behavioral_rules: Optional[List[str]] = None,
    success_criteria: Optional[List[str]] = None,
    change_reason: str = "Updated via API"
) -> Dict
```

**Parameters:**
- `name`: Template name to update
- `template_content` (optional): New template content
- `description` (optional): Updated description
- `behavioral_rules` (optional): Updated rules
- `success_criteria` (optional): Updated criteria
- `change_reason`: Reason for update (for audit trail)

**Returns:**
```json
{
  "updated": true,
  "version": "1.1.0",
  "archived_version": "1.0.0"
}
```

### 5. archive_template

Manually archives a template version.

```python
@mcp.tool
async def archive_template(
    template_id: str,
    reason: str
) -> Dict
```

**Parameters:**
- `template_id`: Template UUID to archive
- `reason`: Archive reason for audit trail

**Returns:**
```json
{
  "archived": true,
  "archive_id": "uuid",
  "timestamp": "2025-01-14T23:55:00Z"
}
```

### 6. apply_template_augmentation

Applies runtime augmentation to a template without modifying the base.

```python
@mcp.tool
async def apply_template_augmentation(
    template_name: str,
    augmentation_content: str,
    task_context: Optional[str] = None
) -> str
```

**Parameters:**
- `template_name`: Base template to augment
- `augmentation_content`: Additional instructions
- `task_context` (optional): Context for the augmentation

**Returns:**
Augmented template content (base remains unchanged).

**Example:**
```python
augmented = await mcp.call_tool("apply_template_augmentation", {
    "template_name": "tester",
    "augmentation_content": "Focus on performance testing and benchmarks",
    "task_context": "Testing template system performance"
})
```

### 7. get_template_stats

Retrieves usage statistics for templates.

```python
@mcp.tool
async def get_template_stats(
    template_name: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None
) -> Dict
```

**Parameters:**
- `template_name` (optional): Specific template or all
- `date_from` (optional): Start date (ISO format)
- `date_to` (optional): End date (ISO format)

**Returns:**
```json
{
  "template_name": "orchestrator",
  "usage_count": 156,
  "avg_generation_ms": 0.042,
  "success_rate": 0.94,
  "total_augmentations": 23,
  "most_common_variables": ["project_name", "agent_list"],
  "last_used": "2025-01-14T23:50:00Z"
}
```

### 8. suggest_template

AI-powered template recommendation based on task description.

```python
@mcp.tool
async def suggest_template(
    task_description: str,
    project_type: Optional[str] = None
) -> Dict
```

**Parameters:**
- `task_description`: Description of the task
- `project_type` (optional): Type of project

**Returns:**
```json
{
  "recommended": "analyzer",
  "confidence": 0.87,
  "reason": "Task involves code analysis and architecture review",
  "alternatives": ["reviewer", "security_auditor"]
}
```

### 9. migrate_templates

One-time migration tool to import templates from Python code.

```python
@mcp.tool
async def migrate_templates(
    source: str = "mission_templates.py",
    dry_run: bool = False
) -> Dict
```

**Parameters:**
- `source`: Source file to migrate from
- `dry_run`: Preview migration without executing

**Returns:**
```json
{
  "migrated": 5,
  "templates": ["orchestrator", "analyzer", "implementer", "tester", "documenter"],
  "errors": [],
  "duration_ms": 145
}
```

## Python API (TemplateManager)

### Initialization

```python
from giljo_mcp.template_manager import TemplateManager

# Create manager instance
tm = TemplateManager(
    session=db_session,
    tenant_key="tenant-uuid",
    product_id="product-uuid"
)
```

### Core Methods

#### get_template()

```python
template = await tm.get_template(
    name="analyzer",
    augmentations="Focus on security",
    variables={"project_name": "MyProject"}
)
```

#### create_template()

```python
template_id = await tm.create_template(
    name="custom_agent",
    category="custom",
    content="Template content...",
    variables=["var1", "var2"]
)
```

#### apply_augmentation()

Polymorphic method handling both DB objects and runtime strings:

```python
# With DB object
augmented = tm.apply_augmentation(
    template_obj,  # AgentTemplate instance
    "Additional instructions"
)

# With string content
augmented = tm.apply_augmentation(
    "Base template content",
    "Additional instructions"
)
```

#### substitute_variables()

```python
result = tm.substitute_variables(
    "Hello {name}, working on {project}",
    {"name": "Agent", "project": "GiljoAI"}
)
# Returns: "Hello Agent, working on GiljoAI"
```

#### extract_variables()

```python
variables = tm.extract_variables("Template with {var1} and {var2}")
# Returns: ["var1", "var2"]
```

## Performance Characteristics

| Operation | Target | Actual | Notes |
|-----------|--------|--------|-------|
| Get Template | <0.1ms | <0.05ms | With caching |
| Apply Augmentation | <0.1ms | <0.03ms | In-memory operation |
| Variable Substitution | <0.1ms | <0.03ms | Regex-based |
| Create Template | <10ms | <8ms | Database write |
| List Templates | <5ms | <3ms | Indexed query |

## Error Handling

All tools return structured errors:

```json
{
  "error": "TemplateNotFound",
  "message": "Template 'unknown' does not exist",
  "suggestions": ["analyzer", "implementer"]
}
```

Common error codes:
- `TemplateNotFound`: Template doesn't exist
- `DuplicateTemplate`: Name already exists
- `InvalidVariables`: Missing required variables
- `AugmentationError`: Failed to apply augmentation
- `PermissionDenied`: Multi-tenant isolation violation

## Multi-Tenant Isolation

Templates are automatically scoped by:
1. `tenant_key`: Organization-level isolation
2. `product_id`: Product-level isolation

Cross-tenant access is prevented at the database level with foreign key constraints and query filters.

## Caching Strategy

- **In-Memory Cache**: Frequently used templates (<1min TTL)
- **Cache Keys**: `{tenant_key}:{product_id}:{template_name}:{version}`
- **Invalidation**: On update, archive, or delete
- **Hit Rate Target**: >90% for common templates

## Migration from Legacy System

### Before (mission_templates.py):
```python
from giljo_mcp.mission_templates import MissionTemplateGenerator
gen = MissionTemplateGenerator()
mission = gen.get_agent_mission("analyzer", project_name="Test")
```

### After (template_manager.py):
```python
from giljo_mcp.template_manager import TemplateManager
tm = TemplateManager(session, tenant_key, product_id)
mission = await tm.get_template("analyzer", variables={"project_name": "Test"})
```

The adapter layer ensures backward compatibility during transition.

## Best Practices

1. **Always specify variables** when using templates with placeholders
2. **Use augmentations** for task-specific customization instead of creating new templates
3. **Monitor performance metrics** to identify slow templates
4. **Archive templates** before major changes for rollback capability
5. **Tag templates** appropriately for better organization
6. **Set success criteria** to enable outcome tracking
7. **Use suggest_template()** for optimal template selection

## Version History

- **v2.0.0** (2025-01-14): Complete rewrite with database backend
- **v1.0.0** (2025-01-11): Initial Python-based implementation (deprecated)