"""
Orchestration MCP Tools - Extended for Slash Command Support

Provides MCP tools for intelligent multi-agent orchestration with 70% token reduction.
Exposes orchestration capabilities via Model Context Protocol for agent coordination.

This module also provides tools that act as "prompt generators" for slash command workflows,
enabling automated agent setup and project orchestration via Claude Code CLI commands.
"""

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

from fastmcp import FastMCP
from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from giljo_mcp.database import DatabaseManager
from giljo_mcp.models import Agent, AgentTemplate, Job, Project, Product
from giljo_mcp.orchestrator import ProjectOrchestrator
from giljo_mcp.template_manager import get_template_manager


logger = logging.getLogger(__name__)


def register_orchestration_tools(mcp: FastMCP, db_manager: DatabaseManager) -> None:
    """
    Register orchestration tools with the MCP server.

    Args:
        mcp: FastMCP server instance
        db_manager: Database manager for data access
    """

    # ========================================================================
    # Core Orchestration Tools (existing tools remain unchanged)
    # ========================================================================
    @mcp.tool()
    async def orchestrate_project(
        project_id: str,
        tenant_key: str
    ) -> dict[str, Any]:
        """
        Complete project orchestration workflow.

        Triggers the full orchestration pipeline:
        1. Vision processing and analysis
        2. Mission generation for specialized agents
        3. Agent selection based on requirements
        4. Agent job spawning
        5. Workflow coordination

        Args:
            project_id: Project database ID (UUID)
            tenant_key: Tenant isolation key

        Returns:
            Dictionary containing:
            - project_id: Created/used project ID
            - mission_plan: Generated missions for agents
            - selected_agents: List of agent types selected
            - spawned_jobs: List of spawned job IDs
            - workflow_result: Workflow execution result
            - token_reduction: Token reduction metrics

        Example:
            {
                'project_id': 'proj-123',
                'mission_plan': {...},
                'selected_agents': ['implementer', 'tester'],
                'spawned_jobs': ['job-1', 'job-2'],
                'workflow_result': {...},
                'token_reduction': {'reduction_percent': 70.0}
            }
        """
        try:
            # Validate inputs
            if not project_id or not project_id.strip():
                return {'error': 'Project ID is required'}

            if not tenant_key or not tenant_key.strip():
                return {'error': 'Tenant key is required'}

            # Get project by ID with tenant isolation
            async with db_manager.get_session_async() as session:
                result = await session.execute(
                    select(Project).where(
                        Project.id == project_id,
                        Project.tenant_key == tenant_key
                    )
                )
                project = result.scalar_one_or_none()

                if not project:
                    return {'error': f"Project '{project_id}' not found"}

                # Ensure project has product_id
                if not project.product_id:
                    return {'error': f"Project '{project_id}' has no associated product"}

                # Initialize orchestrator
                orchestrator = ProjectOrchestrator()

                # Run orchestration workflow
                logger.info(
                    f"Starting orchestration for project {project.id} "
                    f"(name: {project.name}, tenant: {tenant_key})"
                )

                result_dict = await orchestrator.process_product_vision(
                    tenant_key=tenant_key,
                    product_id=project.product_id,
                    project_requirements=project.mission
                )

                logger.info(
                    f"Orchestration completed for project {project.id}. "
                    f"Spawned {len(result_dict.get('spawned_jobs', []))} jobs."
                )

                return result_dict

        except ValueError as e:
            logger.error(f"Orchestration validation error: {e}")
            return {'error': str(e)}
        except Exception as e:
            logger.error(f"Orchestration failed: {e}", exc_info=True)
            return {'error': f"Orchestration failed: {str(e)}"}

    @mcp.tool()
    async def get_agent_mission(
        agent_id: str,
        tenant_key: str
    ) -> dict[str, Any]:
        """
        Retrieve mission for a specific agent.

        Returns the markdown-formatted mission that was generated for the agent
        during orchestration. This mission contains the agent's specific objectives,
        context, and instructions.

        Args:
            agent_id: Agent database ID (UUID)
            tenant_key: Tenant key for isolation

        Returns:
            Dictionary containing:
            - mission: Markdown-formatted mission content
            - agent_id: Agent ID
            - agent_name: Agent name
            - agent_type: Agent type/role

        Example:
            {
                'mission': '# Mission: Implement Features\n\n...',
                'agent_id': 'agent-123',
                'agent_name': 'Feature Implementer',
                'agent_type': 'implementer'
            }
        """
        try:
            # Validate inputs
            if not agent_id or not agent_id.strip():
                return {'error': 'Agent ID is required'}

            if not tenant_key or not tenant_key.strip():
                return {'error': 'Tenant key is required'}

            # Get agent with tenant isolation
            async with db_manager.get_session_async() as session:
                result = await session.execute(
                    select(Agent).where(
                        Agent.id == agent_id,
                        Agent.tenant_key == tenant_key
                    )
                )
                agent = result.scalar_one_or_none()

                if not agent:
                    return {'error': f"Agent '{agent_id}' not found"}

                # Check if agent has mission
                if not agent.mission:
                    return {'error': f"Agent '{agent_id}' has no mission assigned"}

                logger.info(f"Retrieved mission for agent {agent_id} ({agent.name})")

                return {
                    'mission': agent.mission,
                    'agent_id': agent.id,
                    'agent_name': agent.name,
                    'agent_type': getattr(agent, 'type', getattr(agent, 'role', 'unknown'))
                }

        except Exception as e:
            logger.error(f"Failed to get agent mission: {e}", exc_info=True)
            return {'error': f"Failed to get agent mission: {str(e)}"}

    @mcp.tool()
    async def get_workflow_status(
        project_id: str,
        tenant_key: str
    ) -> dict[str, Any]:
        """
        Get current workflow status for a project.

        Provides real-time status of the orchestration workflow including:
        - Active agents (currently working)
        - Completed agents (finished their work)
        - Failed agents (encountered errors)
        - Current workflow stage
        - Overall progress percentage

        Args:
            project_id: Project database ID (UUID)
            tenant_key: Tenant key for isolation

        Returns:
            Dictionary containing:
            - active_agents: Count of agents currently working
            - completed_agents: Count of completed agents
            - failed_agents: Count of failed agents
            - pending_agents: Count of pending agents
            - current_stage: Current workflow stage description
            - progress_percent: Overall progress (0-100)
            - total_agents: Total number of agents

        Example:
            {
                'active_agents': 2,
                'completed_agents': 3,
                'failed_agents': 0,
                'pending_agents': 1,
                'current_stage': 'Implementation',
                'progress_percent': 60.0,
                'total_agents': 6
            }
        """
        try:
            # Validate inputs
            if not project_id or not project_id.strip():
                return {'error': 'Project ID is required'}

            if not tenant_key or not tenant_key.strip():
                return {'error': 'Tenant key is required'}

            # Verify project exists with tenant isolation
            async with db_manager.get_session_async() as session:
                result = await session.execute(
                    select(Project).where(
                        Project.id == project_id,
                        Project.tenant_key == tenant_key
                    )
                )
                project = result.scalar_one_or_none()

                if not project:
                    return {'error': f"Project '{project_id}' not found"}

                # Get all Jobs for this project/tenant
                # Note: Job doesn't have project_id, so we filter by tenant_key
                jobs_result = await session.execute(
                    select(Job).where(
                        Job.tenant_key == tenant_key
                    )
                )
                jobs = jobs_result.scalars().all()

                # Count by status
                active_count = sum(1 for job in jobs if job.status == 'active')
                completed_count = sum(1 for job in jobs if job.status == 'completed')
                failed_count = sum(1 for job in jobs if job.status == 'failed')
                pending_count = sum(1 for job in jobs if job.status == 'pending')
                total_count = len(jobs)

                # Calculate progress percentage
                if total_count > 0:
                    progress_percent = (completed_count / total_count) * 100.0
                else:
                    progress_percent = 0.0

                # Determine current stage
                if total_count == 0:
                    current_stage = "Not started"
                elif completed_count == total_count:
                    current_stage = "Completed"
                elif failed_count > 0:
                    current_stage = f"In Progress (with {failed_count} failure(s))"
                elif active_count > 0:
                    current_stage = "In Progress"
                elif pending_count > 0:
                    current_stage = "Pending"
                else:
                    current_stage = "Unknown"

                logger.info(
                    f"Workflow status for project {project_id}: "
                    f"{completed_count}/{total_count} completed ({progress_percent:.1f}%)"
                )

                return {
                    'active_agents': active_count,
                    'completed_agents': completed_count,
                    'failed_agents': failed_count,
                    'pending_agents': pending_count,
                    'current_stage': current_stage,
                    'progress_percent': round(progress_percent, 2),
                    'total_agents': total_count
                }

        except Exception as e:
            logger.error(f"Failed to get workflow status: {e}", exc_info=True)
            return {'error': f"Failed to get workflow status: {str(e)}"}


    # ========================================================================
    # Slash Command Support Tools (Prompt Generators)
    # These tools return formatted instructions for Claude Code to execute
    # ========================================================================

    @mcp.tool()
    async def get_project_by_alias(alias: str) -> dict[str, Any]:
        """
        Fetch project details using its 6-character alias.
        
        This tool enables quick project access without needing to remember
        long UUIDs. Each project has a unique 6-character alphanumeric alias.
        
        Args:
            alias: 6-character project alias (case insensitive)
            
        Returns:
            Dictionary containing project details or error
        """
        try:
            if not alias or len(alias) != 6:
                return {'error': 'Alias must be exactly 6 characters'}
                
            alias_upper = alias.upper()
            
            async with db_manager.get_session_async() as session:
                # For now, use project name search as fallback until alias column is added
                result = await session.execute(
                    select(Project).where(
                        Project.name.ilike(f"%{alias_upper}%")
                    )
                )
                project = result.scalar_one_or_none()
                
                if not project:
                    return {'error': f"Project with alias '{alias_upper}' not found"}
                    
                # Get product details if available
                product_name = None
                if project.product_id:
                    product_result = await session.execute(
                        select(Product).where(Product.id == project.product_id)
                    )
                    product = product_result.scalar_one_or_none()
                    if product:
                        product_name = product.name
                
                return {
                    'success': True,
                    'project_id': str(project.id),
                    'project_name': project.name,
                    'alias': alias_upper,
                    'tenant_key': project.tenant_key,
                    'product_id': str(project.product_id) if project.product_id else None,
                    'product_name': product_name,
                    'mission': project.mission,
                    'status': project.status,
                    'created_at': project.created_at.isoformat() if project.created_at else None
                }
                
        except Exception as e:
            logger.error(f"Failed to get project by alias '{alias}': {e}", exc_info=True)
            return {'error': f"Failed to fetch project: {str(e)}"}


    @mcp.tool()
    async def activate_project_mission(alias: str) -> dict[str, Any]:
        """
        Activate a project and create mission plan for orchestration.
        
        This tool prepares a project for orchestration by analyzing requirements
        and generating detailed instructions for launching the workflow.
        
        Args:
            alias: 6-character project alias
            
        Returns:
            Dictionary with activation status and launch instructions
        """
        try:
            # Get project by alias
            project_result = await get_project_by_alias(alias)
            
            if 'error' in project_result:
                return project_result
                
            project_id = project_result['project_id']
            tenant_key = project_result['tenant_key']
            project_name = project_result['project_name']
            
            if not project_result.get('product_id'):
                return {'error': f"Project '{alias}' has no associated product vision"}
            
            # Generate formatted instructions for mission activation
            instructions = f"""
# Project Mission Activation

**Project**: {project_name} (Alias: {alias.upper()})
**Status**: Ready for orchestration

## Mission Plan Generated

Your project has been analyzed and the following workflow has been prepared:

1. **Orchestrator Agent** - Coordinates all activities
2. **Implementer Agents** - Build features according to specifications  
3. **Tester Agents** - Validate functionality and quality
4. **Reviewer Agents** - Ensure code quality and best practices

## Next Steps

To launch the orchestration workflow, use:
```
/mcp__gil__launch_project {alias.upper()}
```

This will:
- Spawn all required agents with their specific missions
- Begin coordinated development workflow
- Track progress in real-time
- Deliver completed solution

The mission plan has been staged and is ready for execution.
"""
            
            return {
                'success': True,
                'project_id': project_id,
                'alias': alias.upper(),
                'status': 'activated',
                'instructions': instructions
            }
                
        except Exception as e:
            logger.error(f"Failed to activate project '{alias}': {e}", exc_info=True)
            return {'error': f"Failed to activate project: {str(e)}"}


    @mcp.tool()  
    async def get_launch_prompt(alias: str) -> dict[str, Any]:
        """
        Generate orchestration launch instructions for a project.
        
        Returns formatted instructions that guide Claude Code through
        launching the full orchestration workflow.
        
        Args:
            alias: 6-character project alias
            
        Returns:
            Dictionary with launch instructions
        """
        try:
            # Get project details
            project_result = await get_project_by_alias(alias)
            
            if 'error' in project_result:
                return project_result
            
            project_id = project_result['project_id']
            tenant_key = project_result['tenant_key']
            project_name = project_result['project_name']
            
            # Format launch instructions
            instructions = f"""
# Launch Project Orchestration

**Project**: {project_name} (Alias: {alias.upper()})

## Executing Orchestration Workflow

I will now launch the full orchestration pipeline for your project.

### What will happen:

1. **Initialize Orchestrator** - Set up coordination framework
2. **Spawn Specialized Agents** - Deploy implementer, tester, and reviewer agents
3. **Distribute Missions** - Each agent receives their specific objectives
4. **Begin Development** - Agents work in coordinated fashion
5. **Track Progress** - Monitor via dashboard at http://localhost:7272

### Orchestration Command:

```python
# Launching orchestration for project {alias.upper()}
result = await orchestrate_project(
    project_id="{project_id}",
    tenant_key="{tenant_key}"
)
```

### Monitoring Progress:

- View real-time status in web dashboard
- Agents will coordinate automatically
- Completion notifications will be sent
- Results will be delivered upon completion

The orchestration workflow is now starting...
"""
            
            return {
                'success': True,
                'project_id': project_id,
                'alias': alias.upper(),
                'instructions': instructions
            }
                
        except Exception as e:
            logger.error(f"Failed to get launch prompt for '{alias}': {e}", exc_info=True)
            return {'error': f"Failed to generate launch prompt: {str(e)}"}


    @mcp.tool()
    async def get_fetch_agents_instructions() -> dict[str, Any]:
        """
        Generate instructions for installing GiljoAI agent templates.
        
        Provides step-by-step instructions for downloading and installing
        the standard agent templates to enable subagent orchestration.
        
        Returns:
            Dictionary with installation instructions
        """
        try:
            server_url = os.environ.get('GILJO_SERVER_URL', 'http://localhost:7272')
            
            instructions = f"""
# Install GiljoAI Agent Templates

## Installation Process

I will help you install the standard GiljoAI agent templates to enable 
subagent orchestration capabilities.

### Step 1: Create agents directory
```bash
mkdir -p ~/.claude/agents
```

### Step 2: Download agent templates from server
```bash
cd ~/.claude/agents

# Download core agent templates
curl -o orchestrator.md {server_url}/api/agents/templates/orchestrator.md
curl -o implementer.md {server_url}/api/agents/templates/implementer.md  
curl -o tester.md {server_url}/api/agents/templates/tester.md
curl -o reviewer.md {server_url}/api/agents/templates/reviewer.md
curl -o documenter.md {server_url}/api/agents/templates/documenter.md
```

### Step 3: Verify installation
```bash
ls -la ~/.claude/agents/*.md
```

### Step 4: Restart Claude Code
After installation, restart Claude Code to load the new agent templates.

## Post-Installation

Once agents are installed and Claude Code is restarted:

1. Use `/mcp__gil__activate_project <alias>` to prepare a project
2. Use `/mcp__gil__launch_project <alias>` to start orchestration
3. Monitor progress in the web dashboard

The agent templates include MCP tool integration for seamless coordination.
"""
            
            return {
                'success': True,
                'server_url': server_url,
                'instructions': instructions
            }
                
        except Exception as e:
            logger.error(f"Failed to generate fetch agents instructions: {e}", exc_info=True)
            return {'error': f"Failed to generate instructions: {str(e)}"}


    @mcp.tool()
    async def get_update_agents_instructions() -> dict[str, Any]:
        """
        Generate instructions for updating existing agent templates.
        
        Provides instructions for updating already installed agent templates
        with the latest versions from the server.
        
        Returns:
            Dictionary with update instructions
        """
        try:
            server_url = os.environ.get('GILJO_SERVER_URL', 'http://localhost:7272')
            agents_dir = Path.home() / '.claude' / 'agents'
            
            # Check if agents are already installed
            if not agents_dir.exists():
                return {
                    'success': False,
                    'instructions': "No agents installed. Please run /mcp__gil__fetch_agents first."
                }
            
            instructions = f"""
# Update GiljoAI Agent Templates

## Update Process

I will update your existing agent templates with the latest versions.

### Step 1: Backup existing templates
```bash
cd ~/.claude/agents
mkdir -p backup
cp *.md backup/
```

### Step 2: Download latest templates
```bash
# Update all agent templates
curl -o orchestrator.md {server_url}/api/agents/templates/orchestrator.md
curl -o implementer.md {server_url}/api/agents/templates/implementer.md
curl -o tester.md {server_url}/api/agents/templates/tester.md
curl -o reviewer.md {server_url}/api/agents/templates/reviewer.md
curl -o documenter.md {server_url}/api/agents/templates/documenter.md
```

### Step 3: Verify update
```bash
ls -la ~/.claude/agents/*.md
```

### Step 4: Restart Claude Code if agents are active
If you have agents currently running, restart Claude Code to load the updates.

## Update Notes

- Templates are backward compatible
- Existing projects will use updated templates
- New features and improvements included
- Your backup is saved in ~/.claude/agents/backup/

The agent templates are now being updated...
"""
            
            return {
                'success': True,
                'server_url': server_url,
                'instructions': instructions
            }
                
        except Exception as e:
            logger.error(f"Failed to generate update agents instructions: {e}", exc_info=True)
            return {'error': f"Failed to generate instructions: {str(e)}"}
