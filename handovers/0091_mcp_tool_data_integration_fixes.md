# Handover 0091: MCP Tool Data Integration Fixes

**Date**: November 3, 2025
**Author**: Claude Code Session
**Status**: IDENTIFIED - FIXES NEEDED
**Impact**: CRITICAL - Tools callable but returning empty/error data
**Prerequisite**: Handover 0089 (MCP HTTP Tool Catalog Fix)

## Executive Summary

While Handover 0089 successfully exposed all MCP tools via HTTP, testing revealed that many tools are not returning actual data. Database queries have issues with tenant isolation, missing data relationships, and empty content fields. This handover identifies and fixes these data integration issues.

## Test Results from Fresh Agent

### ✅ Tools That Connect Successfully
1. `health_check` - Server operational
2. `get_orchestrator_instructions` - Returns structure but **empty mission**
3. `list_projects` - Lists projects
4. `get_project` - Returns basic metadata

### ❌ Tools with Data Issues

#### Empty Data Returns
- `get_orchestrator_instructions` - **mission field empty**
- `list_templates` - Returns empty list
- `get_template` - Names only, no content
- `discover_context` - Returns empty context
- `get_context_summary` - Placeholder text only
- `search_context` - Empty results
- `get_file_context` - Empty context object

#### Database Errors
- `list_messages` - "Multiple rows found"
- `list_agents` - "Multiple rows found"
- `list_tasks` - "Multiple rows found"

#### Session Issues
- `switch_project` - Session management error

## Root Cause Analysis

### Issue 1: Empty Mission in Orchestrator Instructions
**Location**: `src/giljo_mcp/tools/tool_accessor.py:1225-1347`

**Problem**:
```python
condensed_mission = await planner._build_context_with_priorities(
    product=product,
    project=project,
    field_priorities=field_priorities,
    user_id=user_id
)
```
The `_build_context_with_priorities` is returning empty string.

**Root Cause**: Product context fields not populated or mission planner not accessing them correctly.

### Issue 2: Multiple Rows Found Errors
**Location**: `src/giljo_mcp/tools/tool_accessor.py:569-611`

**Problem**:
```python
project_query = select(Project).where(Project.tenant_key == tenant_key)
project_result = await session.execute(project_query)
project = project_result.scalar_one_or_none()  # Fails with multiple projects
```

**Root Cause**: Query should filter for ACTIVE project, not just tenant.

### Issue 3: Empty Template Content
**Location**: Template manager not returning actual template content

**Problem**: Templates exist but content field not being populated in responses.

## Proposed Fixes

### Fix 1: Orchestrator Mission Generation
```python
# In get_orchestrator_instructions
async def get_orchestrator_instructions(self, orchestrator_id: str, tenant_key: str):
    # ... existing code ...

    # FIX: Ensure product has context
    if product and product.product_context:
        # Build mission from product context
        mission_parts = []

        # Add product vision
        if product.vision_summary:
            mission_parts.append(f"Vision: {product.vision_summary}")

        # Add project description
        if project.description:
            mission_parts.append(f"Project Goal: {project.description}")

        # Add tech stack from product context
        context = product.product_context or {}
        if context.get('tech_stack'):
            mission_parts.append(f"Tech Stack: {context['tech_stack']}")

        condensed_mission = "\n\n".join(mission_parts)
    else:
        # Fallback to project description
        condensed_mission = project.description or "No mission defined"
```

### Fix 2: Project Query Filtering
```python
# In list_agents, list_tasks, list_messages
async def list_agents(self, status: Optional[str] = None):
    # ... existing code ...

    # FIX: Filter for active project only
    project_query = select(Project).where(
        and_(
            Project.tenant_key == tenant_key,
            Project.status == 'active'  # Add status filter
        )
    )
    project_result = await session.execute(project_query)
    project = project_result.scalar_one_or_none()

    # If still multiple, get most recent
    if not project:
        project_query = select(Project).where(
            Project.tenant_key == tenant_key
        ).order_by(Project.created_at.desc()).limit(1)
        project_result = await session.execute(project_query)
        project = project_result.scalar_one_or_none()
```

### Fix 3: Template Content Population
```python
# In list_templates
async def list_templates(self):
    # ... existing code ...

    templates = []
    for t in template_results:
        templates.append({
            "name": t.name,
            "role": t.role,
            "description": t.description,
            "content": t.template_content,  # ADD: Include actual content
            "variables": t.variables,
            "success_criteria": t.success_criteria
        })
```

### Fix 4: Context Discovery Implementation
```python
# In discover_context
async def discover_context(self, project_id: Optional[str] = None):
    # FIX: Implement actual context discovery
    tenant_key = self.tenant_manager.get_current_tenant()

    async with self.db_manager.get_session_async() as session:
        # Get project
        if project_id:
            project = await session.get(Project, project_id)
        else:
            # Get active project
            result = await session.execute(
                select(Project).where(
                    and_(
                        Project.tenant_key == tenant_key,
                        Project.status == 'active'
                    )
                )
            )
            project = result.scalar_one_or_none()

        if not project:
            return {"error": "No active project"}

        # Get product
        product = None
        if project.product_id:
            product = await session.get(Product, project.product_id)

        context = {
            "project": {
                "id": str(project.id),
                "name": project.name,
                "description": project.description,
                "vision_files": project.vision_files or []
            }
        }

        if product:
            context["product"] = {
                "id": str(product.id),
                "name": product.name,
                "context": product.product_context or {},
                "tech_stack": product.product_context.get('tech_stack') if product.product_context else None
            }

        return {"success": True, "context": context}
```

## Test Suite Requirements

### Integration Tests Needed
```python
# tests/integration/test_mcp_tools_data.py

async def test_orchestrator_instructions_has_mission():
    """Verify mission field is populated"""
    result = await tool_accessor.get_orchestrator_instructions(
        orchestrator_id="test-orch-id",
        tenant_key="test-tenant"
    )
    assert result.get("mission")
    assert len(result["mission"]) > 0

async def test_list_agents_single_project():
    """Verify no multiple rows error"""
    result = await tool_accessor.list_agents()
    assert result.get("success")
    assert "Multiple rows" not in str(result.get("error", ""))

async def test_template_content_populated():
    """Verify templates have content"""
    result = await tool_accessor.list_templates()
    if result.get("templates"):
        template = result["templates"][0]
        assert template.get("content")

async def test_context_discovery():
    """Verify context returns data"""
    result = await tool_accessor.discover_context()
    assert result.get("context")
    assert result["context"].get("project")
```

## Implementation Plan

### Phase 1: Critical Fixes (Immediate)
1. Fix project query filtering (multiple rows error)
2. Implement mission generation from product context
3. Add proper error handling for missing data

### Phase 2: Data Population (Next)
1. Ensure templates have content
2. Implement context discovery
3. Fix search functionality

### Phase 3: Testing & Validation
1. Create integration test suite
2. Test with fresh orchestrator instance
3. Validate all 29 tools return data

## Deployment Steps

1. **Apply Code Fixes**:
   ```bash
   # Update tool_accessor.py with fixes
   # Update mission_planner.py if needed
   ```

2. **Run Tests**:
   ```bash
   pytest tests/integration/test_mcp_tools_data.py -v
   ```

3. **Restart Server**:
   ```bash
   python startup.py
   ```

4. **Test with Orchestrator**:
   - Create new orchestrator instance
   - Verify mission is populated
   - Test agent listing works
   - Confirm context discovery returns data

## Success Criteria

- [ ] Orchestrator instructions contain non-empty mission
- [ ] No "multiple rows found" errors
- [ ] Templates return actual content
- [ ] Context discovery returns project/product data
- [ ] All 29 tools return meaningful data
- [ ] Fresh orchestrator can execute project successfully

## Risk Mitigation

### Backward Compatibility
- All fixes maintain existing API contracts
- Add fallbacks for missing data
- Log warnings for data issues

### Data Migration
- May need script to populate missing product_context
- Consider default templates if none exist
- Add data validation on startup

## Related Handovers

- **0089**: MCP HTTP Tool Catalog Fix (prerequisite)
- **0088**: Thin Client Architecture (context for mission generation)
- **0041**: Agent Template Management (template content)

## Next Steps

1. **Immediate**: Apply critical fixes for project queries
2. **Today**: Implement mission generation logic
3. **Tomorrow**: Complete test suite and validate
4. **This Week**: Full integration testing with orchestrator

## Notes

This is a data integration issue, not an MCP protocol issue. The tools are callable but need proper database queries and data population logic. The fresh agent test proved the MCP HTTP connection works perfectly - now we need to ensure the tools return meaningful data.

**Priority**: CRITICAL - Orchestrators cannot function without mission data