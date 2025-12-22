"""
Generic Agent Template - Unified prompt for all agents in multi-terminal mode.

This template is used by ALL agent types (implementer, tester, reviewer, etc.)
in Generic/Legacy mode. The Orchestrator injects agent-specific IDs, and the
agent fetches its actual mission and behavior protocol from the database.

Handover 0246b: Generic Agent Template Implementation
Handover 0349: Delegate lifecycle behavior to get_agent_mission/full_protocol
"""


class GenericAgentTemplate:
    """
    Generic template providing unified wiring for multi-terminal agent execution.

    Variable Injection (by Orchestrator):
    - {agent_id}: UUID of this agent execution (AgentExecution.agent_id)
    - {job_id}: UUID of this job (AgentJob.job_id)
    - {product_id}: UUID of the product context
    - {project_id}: UUID of the project context
    - {tenant_key}: Tenant isolation key

    Mission + Protocol (by Agent):
    - Agent calls: mcp__giljo-mcp__get_agent_mission(agent_job_id, tenant_key)
    - Receives: mission (what to do) + full_protocol (how to behave)
    - Executes: According to mission and full_protocol returned by server
    """

    def __init__(self) -> None:
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

        Args:
            agent_id: UUID of agent instance (must be non-empty)
            job_id: UUID of job (AgentJob work order, must be non-empty)
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

        # NOTE: This template intentionally delegates lifecycle behavior to
        # the server-side protocol returned by get_agent_mission()
        template = f"""# GENERIC AGENT - MULTI-TERMINAL MODE

## Your Identity

- **Agent ID**: {agent_id}
- **Job ID**: {job_id}
- **Product**: {product_id}
- **Project**: {project_id}
- **Tenant**: {tenant_key}

---

## MCP Tool Wiring (How to Talk to the Server)

MCP tools are **native tools** (like Read/Write/Bash/Glob), already connected in this environment.

- CORRECT: Call `mcp__giljo-mcp__*` tools directly
- WRONG: Use of `curl`, raw HTTP requests, SDKs, or custom clients

Key tools used by this agent:
- `mcp__giljo-mcp__get_agent_mission(agent_job_id, tenant_key)` – Fetches mission + protocol
- `mcp__giljo-mcp__report_progress(job_id, progress)` – Progress and check-ins
- `mcp__giljo-mcp__complete_job(job_id, result)` – Completion
- `mcp__giljo-mcp__report_error(job_id, error)` – Blocking errors

---

## Standard Protocol (Behavior Comes From Server)

Your **authoritative behavior and lifecycle** are defined by the server and
returned with your mission.

1. **First action (mandatory)**
   Call:
   ```python
   result = mcp__giljo-mcp__get_agent_mission(
       agent_job_id="{job_id}",
       tenant_key="{tenant_key}"
   )
   ```

2. **Read the response**
   You will receive at least:
   - `mission`: Full text of your assignment
   - `full_protocol`: Multi-phase lifecycle protocol (startup, planning,
     execution, progress, messaging, completion, error handling)

3. **Follow `full_protocol` exactly**
   - Use `full_protocol` as your single source of truth for:
     - Startup and TodoWrite planning
     - Progress reporting and check-ins
     - Message handling and context requests
     - Completion and error handling
   - Do **not** invent a different lifecycle; if you are unsure, re-read
     `full_protocol`.

---

## Your Mission

Your mission is stored in the database and fetched via
`mcp__giljo-mcp__get_agent_mission`. After the call above:

- Use `result["mission"]` as the concrete work you must perform.
- Use any additional context fields in the response
  (project/product/agent metadata) to guide decisions.

If `result["success"]` is false:
- Report the error via:
  ```python
  mcp__giljo-mcp__report_error(
      job_id="{job_id}",
      error="describe what failed and why"
  )
  ```
- Do not proceed until the issue is resolved.

---

## Expectations (Role-Agnostic)

Regardless of agent type (implementer, tester, reviewer, analyzer, documenter):

- Obey `full_protocol` from the server.
- Keep work within the mission scope.
- Include `tenant_key` on all MCP tool calls to maintain tenant isolation.
- Favor small, incremental changes with clear progress reports.
"""

        return template
