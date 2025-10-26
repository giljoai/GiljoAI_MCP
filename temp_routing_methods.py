    # ========================================================================
    # HANDOVER 0045 - Phase 3: Multi-Tool Agent Orchestration Routing
    # ========================================================================

    async def _get_agent_template(
        self, role: str, tenant_key: str, product_id: Optional[str] = None
    ) -> Optional[AgentTemplate]:
        """
        Get agent template for role with cascade resolution.

        Resolution order (highest to lowest priority):
        1. Product-specific template (if product_id provided)
        2. Tenant-specific template (user customizations)
        3. System default template (is_default=True)

        Args:
            role: Agent role name (e.g., "implementer", "tester")
            tenant_key: Tenant key for multi-tenant isolation
            product_id: Optional product ID for product-specific templates

        Returns:
            AgentTemplate instance or None if no template found

        Multi-tenant isolation:
            - Only returns templates owned by tenant
            - No cross-tenant leakage possible
        """
        async with self.db_manager.get_session_async() as session:
            # Try product-specific template first (if product_id provided)
            if product_id:
                stmt = select(AgentTemplate).where(
                    AgentTemplate.tenant_key == tenant_key,
                    AgentTemplate.role == role,
                    AgentTemplate.product_id == product_id,
                    AgentTemplate.is_active == True,
                )
                result = await session.execute(stmt)
                template = result.scalar_one_or_none()
                if template:
                    logger.info(
                        f"[_get_agent_template] Found product-specific template for "
                        f"role={role}, product={product_id}, tenant={tenant_key}"
                    )
                    return template

            # Try tenant-specific template (no product_id constraint)
            stmt = select(AgentTemplate).where(
                AgentTemplate.tenant_key == tenant_key,
                AgentTemplate.role == role,
                AgentTemplate.product_id == None,
                AgentTemplate.is_active == True,
            )
            result = await session.execute(stmt)
            template = result.scalar_one_or_none()
            if template:
                logger.info(
                    f"[_get_agent_template] Found tenant-specific template for "
                    f"role={role}, tenant={tenant_key}"
                )
                return template

            # Try system default template (is_default=True, any tenant)
            stmt = select(AgentTemplate).where(
                AgentTemplate.role == role,
                AgentTemplate.is_default == True,
                AgentTemplate.is_active == True,
            )
            result = await session.execute(stmt)
            template = result.scalar_one_or_none()
            if template:
                logger.info(
                    f"[_get_agent_template] Found system default template for role={role}"
                )
                return template

            logger.warning(
                f"[_get_agent_template] No template found for role={role}, "
                f"tenant={tenant_key}, product={product_id}"
            )
            return None

    async def _spawn_claude_code_agent(
        self,
        project: Project,
        role: AgentRole,
        template: AgentTemplate,
        custom_mission: Optional[str] = None,
        additional_instructions: Optional[str] = None,
    ) -> Agent:
        """
        Spawn Claude Code agent (hybrid mode with auto-export).

        Process:
        1. Auto-export template to .claude/agents/<role>.md
        2. Generate mission with MCP coordination instructions
        3. Apply Serena optimization
        4. Create Agent record with mode='claude'

        Args:
            project: Project instance
            role: Agent role enum
            template: AgentTemplate instance
            custom_mission: Optional custom mission override
            additional_instructions: Optional additional instructions

        Returns:
            Created Agent instance with mode='claude'

        Integration:
            - Exports template using single-template export function
            - Includes MCP checkpoint instructions in mission
            - Applies Serena optimization for token reduction
        """
        # 1. Auto-export template to .claude/agents/<role>.md
        export_dir = Path.cwd() / ".claude" / "agents"
        export_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{template.name}.md"
        file_path = export_dir / filename

        # Simple template export (inline implementation)
        try:
            # Generate YAML frontmatter
            frontmatter = f"""---
name: {template.name}
role: {template.role or template.name}
tool: {template.tool}
description: {template.description or 'No description'}
---

"""

            # Build complete file content
            content_parts = [frontmatter]
            content_parts.append(template.template_content.strip())
            content_parts.append("\n")

            # Add behavioral rules if present
            if template.behavioral_rules and len(template.behavioral_rules) > 0:
                content_parts.append("\n## Behavioral Rules\n")
                content_parts.extend(f"- {rule}\n" for rule in template.behavioral_rules)

            # Add success criteria if present
            if template.success_criteria and len(template.success_criteria) > 0:
                content_parts.append("\n## Success Criteria\n")
                content_parts.extend(
                    f"- {criterion}\n" for criterion in template.success_criteria
                )

            # Write file
            full_content = "".join(content_parts)
            file_path.write_text(full_content, encoding="utf-8")

            logger.info(
                f"[_spawn_claude_code_agent] Exported template: {template.name} to {file_path}"
            )

        except Exception as e:
            logger.exception(
                f"[_spawn_claude_code_agent] Failed to export template {template.name}: {e}"
            )
            # Continue without export - not critical

        # 2. Generate mission with MCP coordination instructions
        if custom_mission:
            mission = custom_mission
        else:
            # Generate mission using template generator
            mission = await self.template_generator.generate_agent_mission(
                role=role.value,
                project_name=project.name,
                custom_mission=None,
                additional_instructions=additional_instructions,
            )

        # Add MCP coordination protocol to mission
        mcp_instructions = self._generate_mcp_instructions(project.tenant_key, role.value)
        mission = f"{mission}\n\n{mcp_instructions}"

        # 3. Apply Serena optimization
        try:
            optimizer = self._get_serena_optimizer(project.tenant_key)
            injector = MissionOptimizationInjector(optimizer)

            context_data = {
                "project_id": project.id,
                "project_type": "general",
                "codebase_size": "medium",
                "primary_language": "python",
            }

            optimized_mission = await injector.inject_optimization_rules(
                agent_role=role.value, mission=mission, context_data=context_data
            )

            logger.info(
                f"[_spawn_claude_code_agent] Enhanced {role.value} agent mission with Serena optimization"
            )
            mission = optimized_mission

        except Exception as e:
            logger.warning(
                f"[_spawn_claude_code_agent] Failed to inject Serena optimization: {e}"
            )
            # Continue with original mission

        # 4. Create Agent record with mode='claude'
        agent = Agent(
            tenant_key=project.tenant_key,
            project_id=project.id,
            name=role.value,
            role=role.value,
            mission=mission,
            status="active",
            context_used=0,
            mode="claude",
            job_id=None,  # No job for Claude Code agents
            meta_data={
                "template_id": template.id,
                "template_name": template.name,
                "tool": template.tool,
                "exported_path": str(file_path),
            },
        )

        logger.info(
            f"[_spawn_claude_code_agent] Created Claude Code agent: role={role.value}, "
            f"template={template.name}, project={project.id}"
        )

        return agent

    async def _spawn_legacy_agent(
        self,
        project: Project,
        role: AgentRole,
        template: AgentTemplate,
        custom_mission: Optional[str] = None,
        additional_instructions: Optional[str] = None,
    ) -> Agent:
        """
        Spawn legacy agent (Codex/Gemini with job queue).

        Process:
        1. Create MCP job via AgentJobManager
        2. Generate CLI prompt with MCP tool examples
        3. Create Agent record with mode='codex'/'gemini', job_id, status='waiting_acknowledgment'
        4. Store CLI prompt in Agent metadata

        Args:
            project: Project instance
            role: Agent role enum
            template: AgentTemplate instance
            custom_mission: Optional custom mission override
            additional_instructions: Optional additional instructions

        Returns:
            Created Agent instance with mode='codex' or 'gemini', linked to job

        Integration:
            - Uses AgentJobManager for job creation
            - Links Agent to MCPAgentJob via job_id
            - Generates copy-paste ready CLI prompt
        """
        # 1. Generate mission
        if custom_mission:
            mission = custom_mission
        else:
            mission = await self.template_generator.generate_agent_mission(
                role=role.value,
                project_name=project.name,
                custom_mission=None,
                additional_instructions=additional_instructions,
            )

        # Add MCP coordination protocol
        mcp_instructions = self._generate_mcp_instructions(project.tenant_key, role.value)
        full_mission = f"{mission}\n\n{mcp_instructions}"

        # 2. Create MCP job via AgentJobManager
        job = self.agent_job_manager.create_job(
            tenant_key=project.tenant_key,
            agent_type=role.value,
            mission=full_mission,
            spawned_by=None,  # Could track parent orchestrator if needed
            context_chunks=[],  # Could include relevant context chunk IDs
        )

        logger.info(
            f"[_spawn_legacy_agent] Created MCP job: job_id={job.job_id}, "
            f"agent_type={role.value}, tenant={project.tenant_key}"
        )

        # 3. Generate CLI prompt with MCP tool examples
        cli_prompt = self._generate_cli_prompt(
            job=job,
            template=template,
            project=project,
            tenant_key=project.tenant_key,
        )

        # 4. Create Agent record linked to job
        agent = Agent(
            tenant_key=project.tenant_key,
            project_id=project.id,
            name=role.value,
            role=role.value,
            mission=full_mission,
            status="waiting_acknowledgment",
            context_used=0,
            mode=template.tool,  # 'codex' or 'gemini'
            job_id=job.job_id,
            meta_data={
                "template_id": template.id,
                "template_name": template.name,
                "tool": template.tool,
                "cli_prompt": cli_prompt,
                "mcp_job_id": job.job_id,
            },
        )

        logger.info(
            f"[_spawn_legacy_agent] Created {template.tool} agent: role={role.value}, "
            f"job_id={job.job_id}, project={project.id}"
        )

        return agent

    def _generate_mcp_instructions(self, tenant_key: str, agent_role: str) -> str:
        """
        Generate MCP coordination protocol instructions.

        Includes:
        - Checkpoint recommendations (every 2-3 tasks)
        - MCP tool call examples (acknowledge_job, report_progress, complete_job, report_error)
        - Tenant-specific examples (include tenant_key)

        Args:
            tenant_key: Tenant key for multi-tenant isolation
            agent_role: Agent role for contextualized examples

        Returns:
            Formatted MCP instructions text
        """
        return f"""
## MCP Coordination Protocol

**IMPORTANT**: Use MCP tools for coordination and progress tracking.

### Checkpointing Guidelines
- Report progress every 2-3 completed tasks
- Use `report_progress` tool to save state
- Include files modified and context used
- Request handoff if context usage exceeds 25K tokens

### MCP Tool Examples

1. **Acknowledge Job** (First step after assignment):
```
acknowledge_job(
    job_id="<your-job-id>",
    agent_id="{agent_role}",
    tenant_key="{tenant_key}"
)
```

2. **Report Progress** (After completing tasks):
```
report_progress(
    job_id="<your-job-id>",
    completed_todo="Implemented user authentication module",
    files_modified=["src/auth.py", "tests/test_auth.py"],
    context_used=15000,
    tenant_key="{tenant_key}"
)
```

3. **Complete Job** (When mission accomplished):
```
complete_job(
    job_id="<your-job-id>",
    result={{
        "summary": "Successfully implemented feature X",
        "files_created": ["src/new_module.py"],
        "files_modified": ["src/main.py"],
        "tests_written": ["tests/test_new_module.py"],
        "coverage": "95%",
        "notes": "All tests passing"
    }},
    tenant_key="{tenant_key}"
)
```

4. **Report Error** (If blocking issues encountered):
```
report_error(
    job_id="<your-job-id>",
    error_type="test_failure",  # build_failure, test_failure, validation_error, dependency_error, runtime_error, unknown
    error_message="<full error details>",
    context="What you were doing when error occurred",
    tenant_key="{tenant_key}"
)
```

5. **Get Next Instruction** (Check for orchestrator messages):
```
get_next_instruction(
    job_id="<your-job-id>",
    agent_type="{agent_role}",
    tenant_key="{tenant_key}"
)
```

### Tenant Isolation
All MCP tool calls MUST include `tenant_key="{tenant_key}"` for multi-tenant isolation.
"""

    def _generate_cli_prompt(
        self,
        job: MCPAgentJob,
        template: AgentTemplate,
        project: Project,
        tenant_key: str,
    ) -> str:
        """
        Generate copy-paste ready CLI prompt for Codex/Gemini agents.

        Includes:
        - Job information (job_id, agent_type)
        - Mission text
        - Behavioral rules from template
        - Success criteria from template
        - MCP tool call examples (tenant-specific)

        Args:
            job: MCPAgentJob instance
            template: AgentTemplate instance
            project: Project instance
            tenant_key: Tenant key for multi-tenant isolation

        Returns:
            Formatted CLI prompt ready for copy-paste

        Usage:
            User copies this prompt and pastes into Codex/Gemini CLI
        """
        behavioral_rules = ""
        if template.behavioral_rules and len(template.behavioral_rules) > 0:
            behavioral_rules = "\n## Behavioral Rules\n" + "\n".join(
                f"- {rule}" for rule in template.behavioral_rules
            )

        success_criteria = ""
        if template.success_criteria and len(template.success_criteria) > 0:
            success_criteria = "\n## Success Criteria\n" + "\n".join(
                f"- {criterion}" for criterion in template.success_criteria
            )

        mcp_instructions = self._generate_mcp_instructions(tenant_key, job.agent_type)

        return f"""
# {template.name} Agent - Job {job.job_id}

## Job Information
- **Job ID**: `{job.job_id}`
- **Agent Type**: `{job.agent_type}`
- **Project**: {project.name}
- **Tenant**: `{tenant_key}`
- **Status**: {job.status}

## Mission
{job.mission}

{behavioral_rules}

{success_criteria}

{mcp_instructions}

## Getting Started

1. **First Step**: Acknowledge this job
   ```
   acknowledge_job(
       job_id="{job.job_id}",
       agent_id="{job.agent_type}",
       tenant_key="{tenant_key}"
   )
   ```

2. **Work on mission**: Follow the mission instructions above

3. **Report progress**: Every 2-3 completed tasks
   ```
   report_progress(
       job_id="{job.job_id}",
       completed_todo="Description of what you completed",
       files_modified=["list", "of", "files"],
       context_used=<estimated_tokens>,
       tenant_key="{tenant_key}"
   )
   ```

4. **Complete job**: When mission accomplished
   ```
   complete_job(
       job_id="{job.job_id}",
       result={{
           "summary": "Mission summary",
           "files_created": [],
           "files_modified": [],
           "tests_written": [],
           "coverage": "percentage",
           "notes": "additional notes"
       }},
       tenant_key="{tenant_key}"
   )
   ```

---
**Copy this entire prompt and paste into your Codex/Gemini CLI to begin work.**
"""
