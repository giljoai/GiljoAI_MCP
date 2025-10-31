"""
Orchestrator Staging Prompt Generator (Handover 0079)

THE HEART OF GILJOAI - Generates comprehensive, intelligent orchestrator prompts
that enable AI agents to discover context via MCP, create condensed missions,
and coordinate multi-agent workflows within token budgets.

Key Features:
- MCP-only context aggregation (remote-safe, no local file reads)
- Dynamic field priority integration (user-configured)
- 20K token budget management (Claude 25K limit - 5K safety buffer)
- 70% token reduction architecture
- Multi-tool support (Claude Code, Codex, Gemini)
- Eloquent, production-grade instructions

Author: GiljoAI Development Team
Date: 2025-10-31
Priority: MISSION CRITICAL
"""

import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.giljo_mcp.models import Project, Product, VisionDocument, MCPContextIndex, AgentTemplate
from src.giljo_mcp.template_manager import UnifiedTemplateManager

logger = logging.getLogger(__name__)


# Token calculation constants
CHARS_PER_TOKEN = 4  # Standard estimate: 1 token ≈ 4 characters
DEFAULT_TOKEN_BUDGET = 20000  # Claude 25K limit - 5K safety buffer
ORCHESTRATOR_RESERVE = 5000  # Reserved for orchestrator overhead
PER_AGENT_RESERVE = 500  # Reserved per agent (template + context)
MAX_AGENT_TYPES = 8  # Hard limit on agent diversity


@dataclass
class ContextData:
    """Aggregated context from MCP discovery."""
    product: Optional[Product]
    project: Project
    vision_chunks: List[Dict[str, Any]]
    field_priorities: Dict[str, int]
    agent_templates: List[Dict[str, Any]]
    product_settings: Dict[str, Any]

    @property
    def summary(self) -> Dict[str, Any]:
        """Context summary for response metadata."""
        return {
            "product_name": self.product.name if self.product else None,
            "project_name": self.project.name,
            "vision_chunk_count": len(self.vision_chunks),
            "field_count": len(self.field_priorities),
            "template_count": len(self.agent_templates),
        }


@dataclass
class TokenEstimate:
    """Token usage estimate with budget validation."""
    prompt_tokens: int
    mission_tokens: int
    agent_tokens: int
    total: int
    budget: int
    utilization_percent: float
    within_budget: bool
    warnings: List[str]

    @classmethod
    def calculate(cls, prompt: str, agent_count: int, budget: int = DEFAULT_TOKEN_BUDGET) -> 'TokenEstimate':
        """Calculate token estimate for generated prompt."""
        prompt_tokens = len(prompt) // CHARS_PER_TOKEN
        mission_tokens = prompt_tokens - ORCHESTRATOR_RESERVE
        agent_tokens = agent_count * PER_AGENT_RESERVE
        total = prompt_tokens + agent_tokens

        utilization = (total / budget) * 100
        within_budget = total <= budget

        warnings = []
        if total > budget:
            warnings.append(f"Token budget exceeded! {total} > {budget} (over by {total - budget})")
        elif utilization > 90:
            warnings.append(f"Token budget critical: {utilization:.1f}% utilized")
        elif utilization > 80:
            warnings.append(f"Token budget high: {utilization:.1f}% utilized")

        return cls(
            prompt_tokens=prompt_tokens,
            mission_tokens=mission_tokens,
            agent_tokens=agent_tokens,
            total=total,
            budget=budget,
            utilization_percent=round(utilization, 1),
            within_budget=within_budget,
            warnings=warnings
        )


class OrchestratorPromptGenerator:
    """
    Generates comprehensive orchestrator staging prompts.

    This is THE critical component - the heart of GiljoAI orchestration.
    Transforms raw product/project data into actionable, token-efficient
    orchestrator instructions that enable intelligent multi-agent workflows.

    Architecture:
    - Layer 1: Context Aggregator (MCP discovery engine)
    - Layer 2: Prompt Template Engine (eloquent instruction generator)
    - Layer 3: Response Formatter (clean output)

    Usage:
        generator = OrchestratorPromptGenerator(db_session, tenant_key)
        result = await generator.generate(project_id, tool="claude-code")
        prompt = result["prompt"]  # Ready to paste into CLI
    """

    def __init__(self, db: AsyncSession, tenant_key: str):
        """
        Initialize prompt generator.

        Args:
            db: Database session for queries
            tenant_key: Tenant isolation key
        """
        self.db = db
        self.tenant_key = tenant_key
        self.token_budget = DEFAULT_TOKEN_BUDGET
        self.orchestrator_reserve = ORCHESTRATOR_RESERVE
        self.per_agent_reserve = PER_AGENT_RESERVE
        self.max_agents = MAX_AGENT_TYPES

        # Template manager for agent catalog
        self.template_manager = UnifiedTemplateManager(db)

    async def generate(self, project_id: str, tool: str = "claude-code") -> Dict[str, Any]:
        """
        Main entry point - generates complete orchestrator staging prompt.

        Process:
        1. Gather context via MCP-simulated queries
        2. Build prompt sections (5 phases)
        3. Assemble final prompt
        4. Validate token budget
        5. Return structured response

        Args:
            project_id: Project UUID
            tool: Target AI tool (claude-code, codex, gemini)

        Returns:
            Dict containing:
                - prompt: Full orchestrator instructions
                - token_estimate: Estimated token usage
                - budget_utilization: Percentage of budget used
                - context_included: Summary of included context
                - warnings: Budget/priority warnings
                - tool: Target tool identifier

        Raises:
            ValueError: Project not found or invalid tool
        """
        logger.info(f"[PROMPT GEN] Generating staging prompt for project={project_id}, tool={tool}")

        # Validate tool
        if tool not in ["claude-code", "codex", "gemini"]:
            raise ValueError(f"Invalid tool: {tool}. Must be claude-code, codex, or gemini")

        # Phase 1: Gather context via MCP-simulated queries
        context = await self._gather_context(project_id)

        # Phase 2: Build prompt sections
        sections = await self._build_prompt_sections(context, tool)

        # Phase 3: Assemble final prompt
        final_prompt = self._assemble_prompt(sections, context, tool)

        # Phase 4: Validate token budget
        estimate = TokenEstimate.calculate(
            final_prompt,
            len(context.agent_templates),
            self.token_budget
        )

        # Log generation
        logger.info(
            f"[PROMPT GEN] Generated prompt - tokens={estimate.total}, "
            f"utilization={estimate.utilization_percent}%, "
            f"within_budget={estimate.within_budget}"
        )

        if estimate.warnings:
            logger.warning(f"[PROMPT GEN] Warnings: {estimate.warnings}")

        # Phase 5: Return structured response
        return {
            "prompt": final_prompt,
            "token_estimate": estimate.total,
            "budget_utilization": f"{estimate.utilization_percent}%",
            "context_included": context.summary,
            "warnings": estimate.warnings,
            "tool": tool,
            "estimate_details": {
                "prompt_tokens": estimate.prompt_tokens,
                "mission_tokens": estimate.mission_tokens,
                "agent_tokens": estimate.agent_tokens,
                "total_tokens": estimate.total
            }
        }

    async def _gather_context(self, project_id: str) -> ContextData:
        """
        Gather all context via MCP-simulated database queries.

        Simulates MCP tool calls:
        - get_product(project_id)
        - get_product_settings(product_id)
        - get_vision_index(product_id)
        - get_vision(product_id, chunk_id)
        - get_context(product_id, field_priorities=true)
        - list_templates(tenant_key)

        Args:
            project_id: Project UUID

        Returns:
            ContextData with all aggregated information

        Raises:
            ValueError: Project not found or inaccessible
        """
        logger.debug(f"[CONTEXT] Gathering context for project={project_id}")

        # Get project with tenant isolation
        stmt = select(Project).where(
            Project.id == project_id,
            Project.tenant_key == self.tenant_key
        )
        result = await self.db.execute(stmt)
        project = result.scalar_one_or_none()

        if not project:
            raise ValueError(f"Project {project_id} not found or not accessible")

        # Get product (if project is associated)
        product = None
        if project.product_id:
            stmt = select(Product).where(
                Product.id == project.product_id,
                Product.tenant_key == self.tenant_key
            )
            result = await self.db.execute(stmt)
            product = result.scalar_one_or_none()

        # Get vision documents (token-aware)
        vision_chunks = await self._fetch_vision_chunks(product.id if product else None)

        # Get field priorities
        field_priorities = await self._fetch_field_priorities(product.id if product else None)

        # Get agent templates
        agent_templates = await self._fetch_agent_templates()

        # Get product settings
        product_settings = self._extract_product_settings(product)

        logger.debug(
            f"[CONTEXT] Gathered - vision_chunks={len(vision_chunks)}, "
            f"field_priorities={len(field_priorities)}, "
            f"templates={len(agent_templates)}"
        )

        return ContextData(
            product=product,
            project=project,
            vision_chunks=vision_chunks,
            field_priorities=field_priorities,
            agent_templates=agent_templates,
            product_settings=product_settings
        )

    async def _fetch_vision_chunks(self, product_id: Optional[str]) -> List[Dict[str, Any]]:
        """Fetch vision document chunks (token-aware, priority-filtered)."""
        if not product_id:
            return []

        # Get vision documents for product
        stmt = select(VisionDocument).where(
            VisionDocument.product_id == product_id,
            VisionDocument.is_active == True
        ).limit(5)  # Limit to top 5 vision docs

        result = await self.db.execute(stmt)
        vision_docs = result.scalars().all()

        chunks = []
        for doc in vision_docs:
            chunks.append({
                "id": doc.id,
                "title": doc.title,
                "version": doc.version,
                "content_preview": doc.content[:500] if doc.content else doc.file_path,
                "is_chunked": doc.is_chunked
            })

        return chunks

    async def _fetch_field_priorities(self, product_id: Optional[str]) -> Dict[str, int]:
        """Fetch user-configured field priorities."""
        if not product_id:
            return {}

        # Get product with config_data
        stmt = select(Product).where(Product.id == product_id)
        result = await self.db.execute(stmt)
        product = result.scalar_one_or_none()

        if not product or not product.config_data:
            return {}

        # Extract field priorities from config_data
        field_priorities = product.config_data.get("field_priorities", {})

        # Default priorities if not configured
        if not field_priorities:
            field_priorities = {
                "tech_stack": 1,  # Critical
                "architecture": 1,  # Critical
                "features": 2,  # Important
                "dependencies": 2,  # Important
            }

        return field_priorities

    async def _fetch_agent_templates(self) -> List[Dict[str, Any]]:
        """Fetch available agent templates for tenant."""
        # Get active templates for tenant
        stmt = select(AgentTemplate).where(
            AgentTemplate.tenant_key == self.tenant_key,
            AgentTemplate.is_active == True
        ).limit(self.max_agents)  # Enforce max agent types

        result = await self.db.execute(stmt)
        templates = result.scalars().all()

        template_list = []
        for template in templates:
            template_list.append({
                "name": template.name,
                "agent_type": template.agent_type,
                "tool": template.tool or "claude",
                "description": template.description[:200] if template.description else "No description"
            })

        return template_list

    def _extract_product_settings(self, product: Optional[Product]) -> Dict[str, Any]:
        """Extract product settings (tech stack, features, etc.)."""
        if not product or not product.config_data:
            return {}

        return {
            "tech_stack": product.config_data.get("tech_stack", "Not specified"),
            "architecture": product.config_data.get("architecture", "Not specified"),
            "features": product.config_data.get("features", []),
            "dependencies": product.config_data.get("dependencies", [])
        }

    async def _build_prompt_sections(self, context: ContextData, tool: str) -> Dict[str, str]:
        """
        Build all 5 prompt sections.

        Sections:
        1. Project Mission & Context Budget
        2. Phase 1: Intelligent Discovery
        3. Phase 2: Mission Creation
        4. Phase 3: Agent Selection
        5. Phase 4: Coordination Protocol
        6. Phase 5: Execution

        Returns:
            Dict mapping section names to content
        """
        sections = {}

        # Section 1: Header & Budget
        sections["header"] = self._build_header_section(context)

        # Section 2: Phase 1 - Discovery
        sections["discovery"] = self._build_discovery_section(context, tool)

        # Section 3: Phase 2 - Mission
        sections["mission"] = self._build_mission_section(context)

        # Section 4: Phase 3 - Agents
        sections["agents"] = self._build_agent_selection_section(context)

        # Section 5: Phase 4 - Coordination
        sections["coordination"] = self._build_coordination_section(tool)

        # Section 6: Phase 5 - Execution
        sections["execution"] = self._build_execution_section(context)

        return sections

    def _build_header_section(self, context: ContextData) -> str:
        """Build header with project info and token budget."""
        product_name = context.product.name if context.product else "No Product"
        project_name = context.project.name
        project_desc = context.project.description or "No description provided"

        agent_count = len(context.agent_templates)
        agent_tokens = agent_count * self.per_agent_reserve
        remaining_budget = self.token_budget - self.orchestrator_reserve - agent_tokens

        return f"""ORCHESTRATOR STAGING PROMPT
═══════════════════════════════════════════════════════════

🎯 PROJECT MISSION
──────────────────
Project: {project_name}
Product: {product_name}
Description: {project_desc}

📊 YOUR CONTEXT BUDGET
──────────────────────
Total Budget: {self.token_budget:,} tokens
Reserved for You: {self.orchestrator_reserve:,} tokens (orchestrator overhead)
Per-Agent Reserve: {self.per_agent_reserve} tokens × {agent_count} agents = {agent_tokens:,} tokens
Mission Content Budget: {remaining_budget:,} tokens

⚠️ CRITICAL: Stay within budget or agents will fail to spawn!
"""

    def _build_discovery_section(self, context: ContextData, tool: str) -> str:
        """Build Phase 1: Intelligent Discovery instructions."""
        product_id = context.product.id if context.product else "N/A"
        vision_count = len(context.vision_chunks)
        priority_fields = [k for k, v in context.field_priorities.items() if v == 1]

        return f"""
🔍 PHASE 1: INTELLIGENT DISCOVERY (30% of effort)
──────────────────────────────────────────────────

You have access to MCP tools to discover context. Use them STRATEGICALLY:

1️⃣ Product Understanding
   → get_product('{product_id}')
   Returns: Tech stack, features, architecture, dependencies

2️⃣ Vision Document Navigation
   → get_vision_index('{product_id}')
   Returns: List of {vision_count} vision chunks with topics

   → get_vision('{product_id}', chunk_id)
   ⚠️ TOKEN AWARE: Only fetch Priority 1-2 chunks
   ⚠️ BUDGET: Each chunk ~500 tokens, fetch wisely!

3️⃣ Field Priority Configuration
   → get_context('{product_id}', field_priorities=true)
   Returns: User's priority settings (1=critical, 2=important, 3-4=optional)

   🎯 PRIORITY 1 FIELDS (MUST INCLUDE): {', '.join(priority_fields) if priority_fields else 'None configured'}
   🎯 RULE: Only include Priority 1 fields in mission
   🎯 RULE: Include Priority 2 if token budget allows
   🎯 RULE: NEVER include Priority 3-4 (user marked optional)

4️⃣ Available Agent Templates
   → list_templates('{context.tenant_key if hasattr(context, 'tenant_key') else self.tenant_key}')
   Returns: {len(context.agent_templates)} agent types you can assign
   ⚠️ LIMIT: Max {self.max_agents} agent types (hard constraint)
"""

    def _build_mission_section(self, context: ContextData) -> str:
        """Build Phase 2: Mission Creation instructions."""
        return """
📝 PHASE 2: MISSION CREATION (40% of effort)
──────────────────────────────────────────────

Based on discovery, create a CONDENSED mission following these patterns:

✅ DO:
- Extract SPECIFIC requirements from vision (not generic)
- Break down into clear, measurable objectives
- Include technical constraints from product settings
- Reference priority fields only
- Target 3,000-5,000 tokens for mission text

❌ DON'T:
- Copy entire vision documents (condense!)
- Include low-priority fields (user doesn't care)
- Create generic missions (be specific!)
- Exceed token budget (agents won't spawn!)

🎯 Mission Format:
\"\"\"
MISSION: {concise_title}

OBJECTIVES:
1. {specific_objective_1}
2. {specific_objective_2}
...

TECHNICAL CONTEXT:
- Tech Stack: {from_product_settings}
- Architecture: {from_vision_priority_1}
- Constraints: {from_field_priorities}

SUCCESS CRITERIA:
- {measurable_criterion_1}
- {measurable_criterion_2}
\"\"\"
"""

    def _build_agent_selection_section(self, context: ContextData) -> str:
        """Build Phase 3: Agent Selection instructions."""
        template_names = [t["name"] for t in context.agent_templates]
        template_list = ", ".join(template_names) if template_names else "None available"

        return f"""
👥 PHASE 3: AGENT SELECTION (20% of effort)
────────────────────────────────────────────

Select agents using intelligent allocation:

Available Templates: {template_list}

🎯 Selection Rules:
1. Max {self.max_agents} agent types (system constraint)
2. Match agent capabilities to mission requirements
3. Consider tool routing (Claude Code can spawn sub-agents)
4. Reserve {self.per_agent_reserve} tokens per agent for templates

📊 Token Calculation Per Agent:
- Agent template prompt: ~300 tokens
- Mission context for agent: ~200 tokens
- Tool definitions: ~100 tokens
Total: {self.per_agent_reserve} tokens per agent

Example Selections:
- Simple project: 3-4 agents (implementer, tester, documenter)
- Complex project: 6-8 agents (add analyzer, reviewer, optimizer)
"""

    def _build_coordination_section(self, tool: str) -> str:
        """Build Phase 4: Coordination Protocol instructions."""
        tool_specific = ""

        if tool == "claude-code":
            tool_specific = """
For Claude Code:
- ONE prompt launches all agents (sub-agent spawning)
- Orchestrator coordinates via internal messages
- Parallel execution supported
"""
        elif tool == "codex":
            tool_specific = """
For Codex:
- Each agent gets separate terminal window
- Sequential coordination via MCP messages
- Manual prompt copy-paste per agent
"""
        elif tool == "gemini":
            tool_specific = """
For Gemini:
- Each agent gets separate terminal window
- Sequential coordination via MCP messages
- Manual prompt copy-paste per agent
"""

        return f"""
🔄 PHASE 4: COORDINATION PROTOCOL (10% of effort)
──────────────────────────────────────────────────

Establish agent communication patterns:

✅ MANDATORY RULES:
1. All agents MUST acknowledge jobs: acknowledge_job(job_id)
2. Progress reporting: report_progress(job_id, percent, message)
3. Status updates to orchestrator: send_message(to=['orchestrator'], ...)
4. Questions ONLY to orchestrator (not user directly)

📡 MCP Communication Tools:
- send_message(to, message, project_id, from_agent)
- acknowledge_message(message_id)
- get_messages(agent_name, project_id)

🎭 Tool-Specific Workflows:

{tool_specific}
"""

    def _build_execution_section(self, context: ContextData) -> str:
        """Build Phase 5: Execution instructions."""
        project_id = context.project.id

        return f"""
⚡ PHASE 5: EXECUTION (Complete your work!)
────────────────────────────────────────────

Now that you have instructions, EXECUTE:

1. Run discovery (MCP calls)
2. Create condensed mission (respecting token budget)
3. Select agents (max {self.max_agents}, within budget)
4. Report back via update_mission('{project_id}', mission_text)
5. Report agents via select_agents('{project_id}', agent_list)

🎯 FINAL VALIDATION:
- Total tokens < {self.token_budget:,}? ✓
- Mission includes Priority 1 fields? ✓
- Agent count ≤ {self.max_agents}? ✓
- All agents have assigned missions? ✓

═══════════════════════════════════════════════════════════
END ORCHESTRATOR STAGING PROMPT
"""

    def _assemble_prompt(self, sections: Dict[str, str], context: ContextData, tool: str) -> str:
        """Assemble all sections into final prompt."""
        return (
            sections["header"] +
            sections["discovery"] +
            sections["mission"] +
            sections["agents"] +
            sections["coordination"] +
            sections["execution"]
        )
