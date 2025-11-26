# Handover 0249a: Closeout Endpoint Implementation

**Date**: 2025-11-25
**Status**: Ready for Implementation
**Priority**: CRITICAL (Production Blocker)
**Estimated Time**: 1 day
**Dependencies**: None
**Parent**: Handover 0249 (Project Closeout Workflow)

---

## Problem Statement

CloseoutModal.vue (line 203) calls GET /api/projects/{projectId}/closeout but this endpoint doesn't exist, causing a 404 error in production. The modal expects a specific response schema with a dynamic checklist and closeout prompt, but there's no backend implementation to serve this data.

**Current Behavior**:
```javascript
// CloseoutModal.vue line 203 (broken)
const response = await api.get(`/api/projects/${props.projectId}/closeout`)
// Expected: { checklist: [...], closeout_prompt: "..." }
// Actual: 404 Not Found
```

**Required Behavior**:
- GET /api/projects/{project_id}/closeout returns 200 with valid schema
- Dynamic checklist based on project state
- Closeout prompt with MCP command template
- Tenant isolation enforced
- Error handling for edge cases

---

## Scope

**In Scope**:
1. Create GET /api/projects/{project_id}/closeout endpoint
2. Implement ProjectService.get_closeout_data() method
3. Dynamic checklist generation logic
4. Closeout prompt template with MCP command
5. Unit tests for service method
6. Integration tests for endpoint

**Out of Scope**:
- MCP tool integration (Handover 0249b)
- UI wiring (Handover 0249c)
- 360 Memory updates (Handover 0249b)
- Rich entry writing (Handover 0249b)

**Note**: This endpoint returns data FOR CloseoutModal, not for memory writing. The actual memory update happens in 0249b when the MCP tool is called.

---

## Tasks

- [ ] Create GET /api/projects/{project_id}/closeout endpoint in completion.py
- [ ] Implement ProjectService.get_closeout_data() method
- [ ] Add dynamic checklist generation logic
- [ ] Create closeout prompt template with MCP command
- [ ] Add ProjectCloseoutDataResponse schema to prompt.py
- [ ] Write unit tests for get_closeout_data()
- [ ] Write integration tests for /closeout endpoint
- [ ] Verify tenant isolation
- [ ] Test error cases (project not found, wrong tenant)

---

## Implementation Details

### 1. API Endpoint Signature

**File**: `F:\GiljoAI_MCP\api\endpoints\completion.py`

**Add new endpoint**:
```python
@router.get(
    "/{project_id}/closeout",
    response_model=ProjectCloseoutDataResponse,
    summary="Get project closeout data (checklist + prompt)",
    tags=["Projects"],
)
async def get_project_closeout_data(
    project_id: str,
    tenant_key: str = Depends(get_tenant_key),
    db_manager: DatabaseManager = Depends(get_db_manager),
) -> ProjectCloseoutDataResponse:
    """
    Get dynamic closeout checklist and AI-generated prompt for project completion.

    Called by CloseoutModal.vue (line 203) when user clicks "Close Out Project".

    Returns:
        - checklist: List of completion requirements (4+ items)
        - closeout_prompt: MCP command template for orchestrator
        - project_name: Project name for display
        - agent_count: Number of agents in project
        - all_agents_complete: Whether all agents finished successfully

    Raises:
        404: Project not found or tenant access denied
        500: Database error
    """
    tenant_manager = TenantManager()
    tenant_manager.set_current_tenant(tenant_key)

    project_service = ProjectService(db_manager, tenant_manager)

    result = await project_service.get_closeout_data(project_id)

    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result.get("error", "Project not found")
        )

    return ProjectCloseoutDataResponse(**result["data"])
```

### 2. Response Schema

**File**: `F:\GiljoAI_MCP\api\schemas\prompt.py`

**Add new schema** (after ProjectCompleteResponse):
```python
class ProjectCloseoutDataResponse(BaseModel):
    """
    Schema for project closeout data response.
    GET /api/projects/{project_id}/closeout

    Used by CloseoutModal.vue to display checklist and prompt.
    """

    checklist: list[str] = Field(
        ...,
        description="Dynamic checklist items based on project state",
        min_items=3
    )
    closeout_prompt: str = Field(
        ...,
        description="AI-generated closeout prompt with MCP command template",
        min_length=100
    )
    project_name: str = Field(..., description="Project name")
    project_id: str = Field(..., description="Project UUID")
    agent_count: int = Field(..., ge=0, description="Number of agents in project")
    all_agents_complete: bool = Field(..., description="Whether all agents finished successfully")
    has_failed_agents: bool = Field(..., description="Whether any agents failed")
    has_git_commits: bool = Field(
        default=False,
        description="Whether project has Git commits (if GitHub enabled)"
    )

    model_config = ConfigDict(from_attributes=True)
```

### 3. Service Method Implementation

**File**: `F:\GiljoAI_MCP\src\giljo_mcp\services\project_service.py`

**Add new method** (after get_project_summary):
```python
async def get_closeout_data(self, project_id: str) -> dict[str, Any]:
    """
    Generate dynamic closeout checklist and prompt for project completion.

    Called by GET /api/projects/{project_id}/closeout endpoint.

    Checklist Generation Logic:
    - All agents completed successfully
    - No failed agents
    - Project has meaningful work done (agents > 0)
    - Git commits present (if GitHub integration enabled)

    Prompt Template:
    - MCP command format: close_project_and_update_memory(...)
    - Project context (name, mission preview)
    - Summary template with guidance
    - Key outcomes template
    - Decisions made template

    Args:
        project_id: Project UUID

    Returns:
        Dict with success status and ProjectCloseoutDataResponse data:
        - checklist: List of completion requirements
        - closeout_prompt: MCP command template
        - project_name: Project name
        - agent_count: Number of agents
        - all_agents_complete: Whether all agents finished
        - has_failed_agents: Whether any agents failed
        - has_git_commits: Whether Git commits exist

    Example:
        >>> result = await service.get_closeout_data("abc-123")
        >>> print(result["data"]["checklist"])
        ['✅ All agents completed', '✅ No failed agents', ...]
    """
    try:
        async with self.db_manager.get_session_async() as session:
            # Fetch project with tenant validation
            result = await session.execute(
                select(Project).where(
                    and_(
                        Project.id == project_id,
                        Project.tenant_key == self.tenant_manager.get_current_tenant()
                    )
                )
            )
            project = result.scalar_one_or_none()

            if not project:
                return {"success": False, "error": "Project not found"}

            # Get agent job counts by status
            job_counts_result = await session.execute(
                select(MCPAgentJob.status, func.count(MCPAgentJob.id).label("count"))
                .where(
                    and_(
                        MCPAgentJob.project_id == project_id,
                        MCPAgentJob.tenant_key == self.tenant_manager.get_current_tenant()
                    )
                )
                .group_by(MCPAgentJob.status)
            )
            job_counts_raw = job_counts_result.all()

            # Build job counts dict
            job_counts = {status: count for status, count in job_counts_raw}

            total_agents = sum(job_counts.values())
            completed_agents = job_counts.get("completed", 0) + job_counts.get("complete", 0)
            failed_agents = job_counts.get("failed", 0)
            active_agents = (
                job_counts.get("working", 0) +
                job_counts.get("waiting", 0) +
                job_counts.get("preparing", 0)
            )

            all_agents_complete = (
                total_agents > 0 and
                completed_agents == total_agents and
                active_agents == 0
            )
            has_failed_agents = failed_agents > 0

            # Check GitHub integration status
            has_git_commits = False
            if project.product_id:
                from giljo_mcp.models.products import Product

                product_result = await session.execute(
                    select(Product).where(Product.id == project.product_id)
                )
                product = product_result.scalar_one_or_none()

                if product and product.product_memory:
                    git_config = product.product_memory.get("git_integration", {})
                    if git_config.get("enabled", False):
                        # Check if repo has commits (simplified check)
                        has_git_commits = git_config.get("repo_name") is not None

            # Generate dynamic checklist
            checklist = []

            if all_agents_complete:
                checklist.append("✅ All agents completed successfully")
            else:
                checklist.append(f"⚠️  {completed_agents}/{total_agents} agents completed")

            if not has_failed_agents:
                checklist.append("✅ No failed agents")
            else:
                checklist.append(f"❌ {failed_agents} agent(s) failed")

            if total_agents > 0:
                checklist.append(f"✅ Project has meaningful work ({total_agents} agents)")
            else:
                checklist.append("⚠️  No agents in project (empty project)")

            if has_git_commits:
                checklist.append("✅ Git commits will be included in 360 Memory")
            else:
                checklist.append("ℹ️  No Git integration (manual summary will be used)")

            # Generate closeout prompt with MCP command template
            mission_preview = (project.mission[:200] + "...") if len(project.mission) > 200 else project.mission

            closeout_prompt = f"""# Project Closeout: {project.name}

## Project Summary
**Project ID**: {project_id}
**Mission**: {mission_preview}
**Agents**: {total_agents} total ({completed_agents} completed, {failed_agents} failed)

## MCP Command Template

Use this command to close out the project and update 360 Memory:

```python
close_project_and_update_memory(
    project_id="{project_id}",
    summary=\"\"\"
    [Write a comprehensive 2-3 paragraph summary of what was accomplished in this project.
    Include high-level outcomes, technical decisions, and overall progress.]
    \"\"\",
    key_outcomes=[
        "Outcome 1: [Describe key deliverable or achievement]",
        "Outcome 2: [Describe key deliverable or achievement]",
        "Outcome 3: [Describe key deliverable or achievement]",
    ],
    decisions_made=[
        "Decision 1: [Describe architectural or technical decision made]",
        "Decision 2: [Describe architectural or technical decision made]",
    ],
    tenant_key="{self.tenant_manager.get_current_tenant()}"
)
```

## Guidance

**Summary Tips**:
- Focus on the "why" not just the "what"
- Highlight technical decisions and tradeoffs
- Note any blockers encountered and how they were resolved

**Key Outcomes**:
- List tangible deliverables (features, fixes, refactors)
- Quantify where possible (e.g., "Reduced API latency by 40%")
- Include test coverage improvements if applicable

**Decisions Made**:
- Document architectural choices (e.g., "Chose PostgreSQL over MongoDB for...")
- Note design patterns adopted
- Record technology selections and rationale

This information will be stored in the product's 360 Memory for future reference.
"""

            return {
                "success": True,
                "data": {
                    "checklist": checklist,
                    "closeout_prompt": closeout_prompt,
                    "project_name": project.name,
                    "project_id": project_id,
                    "agent_count": total_agents,
                    "all_agents_complete": all_agents_complete,
                    "has_failed_agents": has_failed_agents,
                    "has_git_commits": has_git_commits,
                }
            }

    except Exception as e:
        self._logger.exception(f"Failed to get closeout data: {e}")
        return {"success": False, "error": str(e)}
```

### 4. Checklist Generation Rules

**Dynamic Checklist Items** (4-5 items):

1. Agent Completion Status:
   - ✅ "All agents completed successfully" (if all complete)
   - ⚠️ "X/Y agents completed" (if some incomplete)

2. Failure Status:
   - ✅ "No failed agents" (if no failures)
   - ❌ "X agent(s) failed" (if failures exist)

3. Meaningful Work:
   - ✅ "Project has meaningful work (X agents)" (if agents > 0)
   - ⚠️ "No agents in project (empty project)" (if agents = 0)

4. Git Integration:
   - ✅ "Git commits will be included in 360 Memory" (if GitHub enabled)
   - ℹ️ "No Git integration (manual summary will be used)" (if GitHub disabled)

**Emoji Legend**:
- ✅ = Success (green checkmark)
- ⚠️ = Warning (yellow warning)
- ❌ = Error (red X)
- ℹ️ = Info (blue info)

### 5. Closeout Prompt Template

**Structure**:
```markdown
# Project Closeout: {project_name}

## Project Summary
[Project metadata: ID, mission preview, agent counts]

## MCP Command Template
[Formatted Python code block with close_project_and_update_memory() call]

## Guidance
[Tips for writing summary, key_outcomes, decisions_made]
```

**Key Features**:
- Pre-filled project_id and tenant_key
- Template strings for summary, outcomes, decisions
- Inline guidance comments
- Ready to copy-paste into orchestrator

---

## Testing Strategy

### Unit Tests (test_project_service.py)

**File**: `F:\GiljoAI_MCP\tests\services\test_project_service.py`

**Add test cases**:
```python
@pytest.mark.asyncio
async def test_get_closeout_data_all_agents_complete(
    project_service, mock_db_session, sample_project
):
    """Test closeout data when all agents completed successfully."""
    # Setup: Project with 3 completed agents, 0 failed
    # Assert: checklist includes "All agents completed successfully"
    # Assert: all_agents_complete = True
    # Assert: closeout_prompt includes MCP command template
    pass

@pytest.mark.asyncio
async def test_get_closeout_data_with_failed_agents(
    project_service, mock_db_session, sample_project
):
    """Test closeout data when some agents failed."""
    # Setup: Project with 2 completed, 1 failed agent
    # Assert: checklist includes "1 agent(s) failed"
    # Assert: has_failed_agents = True
    pass

@pytest.mark.asyncio
async def test_get_closeout_data_with_git_integration(
    project_service, mock_db_session, sample_project, sample_product
):
    """Test closeout data when GitHub integration enabled."""
    # Setup: Product with git_integration.enabled = True
    # Assert: checklist includes "Git commits will be included"
    # Assert: has_git_commits = True
    pass

@pytest.mark.asyncio
async def test_get_closeout_data_tenant_isolation(
    project_service, mock_db_session, sample_project
):
    """Test tenant isolation for closeout data."""
    # Setup: Project with different tenant_key
    # Assert: Returns error "Project not found"
    pass
```

### Integration Tests (test_completion_endpoints.py)

**File**: `F:\GiljoAI_MCP\tests\integration\test_completion_endpoints.py`

**Add test cases**:
```python
@pytest.mark.asyncio
async def test_get_closeout_data_endpoint_success(test_client, test_project):
    """Test GET /api/projects/{id}/closeout returns valid data."""
    response = await test_client.get(
        f"/api/projects/{test_project.id}/closeout",
        headers={"Authorization": f"Bearer {test_token}"}
    )

    assert response.status_code == 200
    data = response.json()

    assert "checklist" in data
    assert len(data["checklist"]) >= 3
    assert "closeout_prompt" in data
    assert "close_project_and_update_memory" in data["closeout_prompt"]
    assert data["project_id"] == test_project.id
    assert data["project_name"] == test_project.name

@pytest.mark.asyncio
async def test_get_closeout_data_project_not_found(test_client):
    """Test closeout endpoint returns 404 for non-existent project."""
    response = await test_client.get(
        "/api/projects/nonexistent-id/closeout",
        headers={"Authorization": f"Bearer {test_token}"}
    )

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()

@pytest.mark.asyncio
async def test_get_closeout_data_tenant_isolation(test_client, test_project):
    """Test closeout endpoint enforces tenant isolation."""
    # Setup: Use different tenant's token
    response = await test_client.get(
        f"/api/projects/{test_project.id}/closeout",
        headers={"Authorization": f"Bearer {other_tenant_token}"}
    )

    assert response.status_code == 404
```

---

## Success Criteria

- ✅ GET /api/projects/{id}/closeout endpoint returns 200 with valid schema
- ✅ Response schema matches ProjectCloseoutDataResponse
- ✅ Checklist includes 4+ items with emoji indicators
- ✅ Closeout prompt includes MCP command template with pre-filled values
- ✅ Tenant isolation enforced (404 for wrong tenant)
- ✅ Unit tests achieve >80% coverage for get_closeout_data()
- ✅ Integration tests verify endpoint behavior
- ✅ Error handling for edge cases (project not found, wrong tenant)
- ✅ CloseoutModal.vue can successfully fetch data (manual verification)

---

## Rollback Plan

If issues arise:
1. Comment out endpoint in completion.py
2. Revert schema changes in prompt.py
3. Remove get_closeout_data() method from project_service.py
4. CloseoutModal will return to 404 state (no worse than before)

---

## Related Files

**Modified**:
- `F:\GiljoAI_MCP\api\endpoints\completion.py` (new endpoint)
- `F:\GiljoAI_MCP\api\schemas\prompt.py` (new schema)
- `F:\GiljoAI_MCP\src\giljo_mcp\services\project_service.py` (new method)

**Test Files**:
- `F:\GiljoAI_MCP\tests\services\test_project_service.py` (new tests)
- `F:\GiljoAI_MCP\tests\integration\test_completion_endpoints.py` (new tests)

**Reference**:
- `F:\GiljoAI_MCP\frontend\src\components\projects\CloseoutModal.vue` (consumer)

---

**Next**: Proceed to Handover 0249b (360 Memory Workflow Integration) after this handover is complete.
