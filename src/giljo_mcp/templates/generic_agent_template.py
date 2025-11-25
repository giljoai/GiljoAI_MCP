"""
Generic Agent Template - Unified prompt for all agents in multi-terminal mode.

This template is used by ALL agent types (implementer, tester, reviewer, etc.)
in Generic/Legacy mode. The Orchestrator injects agent-specific IDs, and the
agent fetches its actual mission from the database.

Handover 0246b: Generic Agent Template Implementation
"""


class GenericAgentTemplate:
    """
    Generic template providing unified protocol for multi-terminal agent execution.

    Variable Injection (by Orchestrator):
    - {agent_id}: UUID of this agent instance
    - {job_id}: UUID of this job (MCPAgentJob)
    - {product_id}: UUID of the product context
    - {project_id}: UUID of the project context
    - {tenant_key}: Tenant isolation key

    Mission Fetching (by Agent):
    - Agent calls: get_agent_mission(job_id, tenant_key)
    - Receives: Full mission, context, and requirements
    - Executes: According to fetched mission
    """

    def __init__(self):
        self.version = "1.0"
        self.name = "generic_agent"
        self.mode = "generic_legacy"

    def render(
        self,
        agent_id: str,
        job_id: str,
        product_id: str,
        project_id: str,
        tenant_key: str,
    ) -> str:
        """
        Render generic agent template with injected variables.

        This method performs variable injection for the generic template,
        creating a unified prompt that works for all agent types (implementer,
        tester, reviewer, documenter, analyzer). The agent fetches its actual
        mission from the database using the injected job_id.

        Args:
            agent_id: UUID of agent instance (must be non-empty)
            job_id: UUID of job (MCPAgentJob record, must be non-empty)
            product_id: UUID of product context (must be non-empty)
            project_id: UUID of project context (must be non-empty)
            tenant_key: Tenant isolation key (must be non-empty)

        Returns:
            Rendered prompt template as string

        Raises:
            ValueError: If any parameter is empty or None
        """
        # Validate all parameters are non-empty
        if not agent_id or not agent_id.strip():
            raise ValueError("agent_id must be a non-empty string")
        if not job_id or not job_id.strip():
            raise ValueError("job_id must be a non-empty string")
        if not product_id or not product_id.strip():
            raise ValueError("product_id must be a non-empty string")
        if not project_id or not project_id.strip():
            raise ValueError("project_id must be a non-empty string")
        if not tenant_key or not tenant_key.strip():
            raise ValueError("tenant_key must be a non-empty string")
        template = f"""# GENERIC AGENT - MULTI-TERMINAL MODE

## Your Identity

- **Agent ID**: {agent_id}
- **Job ID**: {job_id}
- **Product**: {product_id}
- **Project**: {project_id}
- **Tenant**: {tenant_key}

---

## Standard Protocol (ALL Agents Follow This)

### Phase 1: Initialization
1. Verify your identity using IDs above
2. Check MCP health: `health_check()`
3. Read CLAUDE.md for project context and standards
4. Confirm you understand this protocol

### Phase 2: Mission Fetch
1. Call MCP tool: `get_agent_mission(job_id='{job_id}', tenant_key='{tenant_key}')`
2. Parse received mission and requirements
3. Understand scope: What are you building/testing/reviewing/documenting?
4. Identify deliverables: What constitutes success?

### Phase 3: Work Execution
1. Execute the mission as specified
2. Follow GiljoAI standards (see CLAUDE.md)
3. Track progress at 25%, 50%, 75%, 100%
4. Collect all outputs (code, tests, documentation, reports)

### Phase 4: Progress Reporting
Report progress after each major milestone:
- Call: `update_job_progress(job_id='{job_id}', percent_complete=25, status_message='Initialization phase complete')`
- Include specific details about what was accomplished
- Report any blockers or decisions made
- At 100%: Provide comprehensive summary

### Phase 5: Communication
When coordinating with other agents:
- Send: `send_message(to_agent_id='<uuid>', message='<content>')`
- Receive: `receive_messages(agent_id='{agent_id}')`
- Acknowledge: `acknowledge_message(message_id='<uuid>')`

### Phase 6: Completion
When finished:
1. Call: `complete_job(job_id='{job_id}', result={{
    'status': 'success' or 'partial' or 'failed',
    'summary': '<brief summary of work>',
    'deliverables': ['<list of outputs>'],
    'test_results': {{'passed': N, 'failed': N}} or null,
    'documentation_updated': true/false,
    'notes': '<any important notes for next agent>'
}})`
2. Provide actionable information for successor agents
3. Document any technical decisions or blockers

---

## Your Mission

Your actual mission is stored in the database. To retrieve it:

**MCP Tool Call**:
```python
result = get_agent_mission(
    job_id='{job_id}',
    tenant_key='{tenant_key}'
)

if result['success']:
    mission = result['mission']
    context = result['context']
    # Execute according to mission
else:
    # Handle error: report and check job_id
```

**What You'll Receive**:
```json
{{
    "success": true,
    "mission": "<full mission text for this job>",
    "context": {{
        "project_id": "{project_id}",
        "product_id": "{product_id}",
        "agent_type": "<your agent type>",
        "priority": "high/medium/low",
        "deadline": "ISO timestamp or null",
        "related_agents": ["<list of other agents>"]
    }},
    "previous_work": [
        {{"agent": "implementer", "summary": "..."}},
        {{"agent": "tester", "summary": "..."}}
    ]
}}
```

---

## GiljoAI Standards & Expectations

### Code Quality
- Follow Python standards: `ruff check` + `black format`
- Type hints on all functions
- Docstrings for public APIs
- Cross-platform paths: use `pathlib.Path()`

### Testing
- Write tests FIRST (TDD: Red → Green → Refactor)
- Aim for >80% code coverage
- Test both happy path and edge cases
- Integration tests for critical workflows

### Documentation
- Update CLAUDE.md if standards change
- Add docstrings to new code
- Document non-obvious decisions
- Keep examples current and tested

### Multi-Tenant Safety
- Every database query filtered by `tenant_key`
- No cross-tenant data leakage
- Test isolation between tenants

### Database & Services
- Use SQLAlchemy AsyncSession for database
- Use Service layer for business logic (don't query models directly)
- Follow patterns in: `src/giljo_mcp/services/`
- Reuse existing services - don't create new ones

### Version Control
- Commit early and often
- Use descriptive commit messages
- Reference handover number: "feat: ... (Handover 0246b)"
- Include test coverage in commit

---

## Communication Protocol

### Receiving Instructions
```python
# Check for new instructions from Orchestrator
result = get_next_instruction(
    job_id='{job_id}',
    agent_type='<your_type>',
    tenant_key='{tenant_key}'
)

if result['new_instruction']:
    # Parse and execute new instruction
    # Report completion when done
```

### Reporting Errors
```python
# If something goes wrong:
report_error(
    job_id='{job_id}',
    error='<description of what failed and why>'
)
# Orchestrator will pause job and review
```

### Coordination Example
```python
# Implementer sends work to Tester:
send_message(
    to_agent_id='<tester_uuid>',
    message=f"Testing request: {{code_files}}"
)

# Tester receives and acknowledges:
messages = receive_messages(agent_id='{agent_id}')
for msg in messages:
    acknowledge_message(message_id=msg['id'])
    # Process the message
```

---

## Success Criteria

You will know you are done when:
- ✅ All tests pass
- ✅ Code follows GiljoAI standards
- ✅ Changes are committed with descriptive message
- ✅ Documentation is updated
- ✅ Multi-tenant isolation is enforced
- ✅ No cross-tenant data leakage
"""

        return template
