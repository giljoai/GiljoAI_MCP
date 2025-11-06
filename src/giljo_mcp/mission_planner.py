"""
Mission Planner for GiljoAI Agent Orchestration MCP Server.

Generates condensed agent missions from product vision analysis.
Achieves 70% token reduction through intelligent context filtering and summarization.

Phase 1 Implementation: Template-based analysis (no LLM calls)
"""

import logging
import re
from typing import Any, ClassVar, Optional

import tiktoken

from .config.defaults import DEFAULT_FIELD_PRIORITY
from .database import DatabaseManager
from .models import Product, Project, User
from .orchestration_types import AgentConfig, Mission, RequirementAnalysis
from .repositories.context_repository import ContextRepository


logger = logging.getLogger(__name__)


class MissionPlanner:
    """
    Generate mission plans from product vision analysis.

    Phase 1 Implementation: Template-based analysis (no LLM calls)
    Target: 70% token reduction through intelligent context filtering
    """

    def __init__(self, db_manager: DatabaseManager):
        """
        Initialize MissionPlanner.

        Args:
            db_manager: Database manager instance for data access
        """
        self.db_manager = db_manager
        self.context_repo = ContextRepository(db_manager)

        # Initialize tokenizer (cl100k_base encoding for GPT-4/Claude)
        try:
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
        except Exception as e:
            logger.warning(f"Failed to load tiktoken encoding: {e}. Using fallback.")
            self.tokenizer = None

        # Keyword mapping for categorization
        self.keyword_map = {
            "test": ["test", "testing", "pytest", "unittest", "coverage", "qa"],
            "api": ["api", "endpoint", "rest", "graphql", "fastapi", "flask"],
            "database": ["database", "db", "postgresql", "sql", "orm", "sqlalchemy"],
            "frontend": ["frontend", "ui", "ux", "vue", "react", "component"],
            "backend": ["backend", "server", "microservice", "service"],
            "security": ["security", "auth", "oauth", "jwt", "permission"],
            "deployment": ["deploy", "docker", "kubernetes", "ci/cd", "pipeline"],
        }

        # Role-specific keyword filters for vision filtering
        self.role_keywords = {
            "implementer": ["implementation", "code", "architecture", "backend", "api", "develop"],
            "tester": ["test", "quality", "validation", "requirements", "coverage", "qa"],
            "frontend-implementer": ["ui", "ux", "design", "user interface", "components", "frontend"],
            "code-reviewer": ["code", "review", "quality", "standards", "best practices"],
            "documenter": ["documentation", "docs", "readme", "guide", "tutorial"],
            "orchestrator": ["architecture", "coordination", "workflow", "planning", "overview"],
        }

    # Field labels mapping for human-readable display
    FIELD_LABELS: ClassVar[dict[str, str]] = {
        "tech_stack.languages": "Programming Languages",
        "tech_stack.backend": "Backend Stack",
        "tech_stack.frontend": "Frontend Stack",
        "tech_stack.database": "Databases",
        "tech_stack.infrastructure": "Infrastructure",
        "architecture.pattern": "Architecture Pattern",
        "architecture.api_style": "API Style",
        "architecture.design_patterns": "Design Patterns",
        "architecture.notes": "Architecture Notes",
        "features.core": "Core Features",
        "test_config.strategy": "Testing Strategy",
        "test_config.frameworks": "Testing Frameworks",
        "test_config.coverage_target": "Coverage Target",
    }

    def _extract_keywords(self, text: str) -> list[str]:
        """
        Extract keywords from text using predefined keyword mapping.

        Args:
            text: Text to extract keywords from

        Returns:
            List of keyword categories found in text
        """
        if not text:
            return []

        text_lower = text.lower()
        found_keywords = []

        for category, keywords in self.keyword_map.items():
            if any(keyword in text_lower for keyword in keywords):
                found_keywords.append(category)

        return found_keywords

    def _categorize_work(self, keywords: list[str], features: list[str]) -> dict[str, str]:
        """
        Categorize work types based on keywords and features.

        Args:
            keywords: List of keyword categories
            features: List of feature descriptions

        Returns:
            Dictionary mapping agent types to priority levels
        """
        work_types = {}

        # Orchestrator is always required
        work_types["orchestrator"] = "required"

        # Backend/API work
        if any(k in keywords for k in ["api", "backend", "database"]):
            work_types["implementer"] = "high"

        # Testing work
        if "test" in keywords:
            work_types["tester"] = "high"

        # Frontend work
        if "frontend" in keywords:
            work_types["frontend-implementer"] = "high"

        # Complex projects need code review
        if len(keywords) >= 4 or len(features) >= 5:
            work_types["code-reviewer"] = "medium"

        # User-facing projects need documentation
        if "frontend" in keywords or "api" in keywords:
            work_types["documenter"] = "low"

        return work_types

    def _assess_complexity(self, description_length: int, feature_count: int, tech_stack_size: int) -> str:
        """
        Assess project complexity based on multiple factors.

        Args:
            description_length: Length of project description in characters
            feature_count: Number of features
            tech_stack_size: Number of technologies in stack

        Returns:
            Complexity level: 'simple', 'moderate', or 'complex'
        """
        complexity_score = 0

        # Description length scoring
        if description_length > 1000:
            complexity_score += 2
        elif description_length > 500:
            complexity_score += 1

        # Feature count scoring
        if feature_count > 6:
            complexity_score += 2
        elif feature_count > 3:
            complexity_score += 1

        # Tech stack scoring
        if tech_stack_size > 5:
            complexity_score += 2
        elif tech_stack_size > 3:
            complexity_score += 1

        # Determine complexity
        if complexity_score >= 4:
            return "complex"
        if complexity_score >= 2:
            return "moderate"
        return "simple"

    def _estimate_agent_count(self, work_types: dict[str, str], complexity: str) -> int:
        """
        Estimate number of agents needed based on work types and complexity.

        Args:
            work_types: Dictionary of work type to priority mappings
            complexity: Project complexity level

        Returns:
            Estimated number of agents needed
        """
        base_count = len(work_types)

        # Adjust based on complexity
        if complexity == "complex":
            return min(base_count + 2, 8)
        if complexity == "moderate":
            return min(base_count + 1, 6)
        return min(base_count, 4)

    def _count_tokens(self, text: str) -> int:
        """
        Count tokens in text using tiktoken.

        Args:
            text: Text to count tokens for

        Returns:
            Number of tokens
        """
        if not text:
            return 0

        if self.tokenizer:
            try:
                return len(self.tokenizer.encode(text))
            except Exception as e:
                logger.warning(f"Token counting failed: {e}. Using fallback.")

        # Fallback: rough estimate (1 token ≈ 4 characters)
        return len(text) // 4

    def _filter_vision_for_role(self, vision_chunks: list[str], agent_role: str) -> list[str]:
        """
        Filter vision chunks to find most relevant content for agent role.

        Args:
            vision_chunks: List of vision document chunks
            agent_role: Role of the agent

        Returns:
            Top 3 most relevant chunks for the role
        """
        if not vision_chunks:
            return []

        # Get role-specific keywords
        role_keywords = self.role_keywords.get(agent_role, [])

        if not role_keywords:
            # Return first 3 chunks if no role-specific keywords
            return vision_chunks[:3]

        # Score chunks based on keyword relevance
        scored_chunks = []
        for chunk in vision_chunks:
            chunk_lower = chunk.lower()
            score = sum(1 for keyword in role_keywords if keyword in chunk_lower)
            scored_chunks.append((score, chunk))

        # Sort by score (descending) and return top 3
        scored_chunks.sort(key=lambda x: x[0], reverse=True)
        return [chunk for score, chunk in scored_chunks[:3]]

    def _get_role_responsibilities(self, agent_role: str) -> str:
        """
        Get role-specific responsibilities description.

        Args:
            agent_role: Role of the agent

        Returns:
            Description of role responsibilities
        """
        responsibilities = {
            "orchestrator": """
You are the Orchestrator agent responsible for:
- Coordinating all agent activities and ensuring workflow coherence
- Managing inter-agent communication and dependency resolution
- Monitoring project progress and adjusting plans as needed
- Ensuring all agents stay within scope boundaries
- Facilitating collaboration and knowledge sharing between agents
""",
            "implementer": """
You are the Implementer agent responsible for:
- Writing clean, maintainable, production-ready code
- Following established architecture patterns and coding standards
- Implementing features according to requirements and specifications
- Integrating with existing systems and components
- Ensuring code is well-documented and follows best practices
""",
            "tester": """
You are the Tester agent responsible for:
- Creating comprehensive test suites (unit, integration, e2e)
- Ensuring high test coverage and quality standards
- Validating requirements and acceptance criteria
- Identifying edge cases and potential issues
- Running tests and reporting results clearly
""",
            "frontend-implementer": """
You are the Frontend Implementer agent responsible for:
- Building modern, responsive user interfaces
- Implementing reusable UI components
- Ensuring excellent user experience and accessibility
- Following design systems and UI/UX best practices
- Optimizing frontend performance
""",
            "code-reviewer": """
You are the Code Reviewer agent responsible for:
- Reviewing code for quality, maintainability, and best practices
- Identifying potential bugs, security issues, and performance problems
- Ensuring code follows project standards and conventions
- Providing constructive feedback to improve code quality
- Approving code changes before integration
""",
            "documenter": """
You are the Documenter agent responsible for:
- Creating clear, comprehensive documentation
- Writing user guides, API documentation, and tutorials
- Maintaining up-to-date README files
- Documenting architecture decisions and design patterns
- Ensuring documentation is accessible and easy to understand
""",
        }

        return responsibilities.get(
            agent_role,
            f"You are the {agent_role} agent responsible for completing assigned tasks within your domain of expertise.",
        )

    def _get_success_criteria(self, agent_role: str, analysis: RequirementAnalysis) -> str:
        """
        Get success criteria for agent based on role and analysis.

        Args:
            agent_role: Role of the agent
            analysis: Requirement analysis results

        Returns:
            Success criteria description
        """
        base_criteria = """
Success Criteria:
- All assigned tasks completed within scope boundaries
- Work meets quality standards and follows best practices
- Clear communication with other agents when needed
- Deliverables are properly documented
"""

        role_criteria = {
            "implementer": "- All code has appropriate test coverage\n- Code passes linting and static analysis\n- Features work as specified in requirements\n",
            "tester": "- Test coverage meets or exceeds project standards\n- All tests pass consistently\n- Edge cases and error conditions are tested\n",
            "frontend-implementer": "- UI is responsive across all target devices\n- Components are reusable and well-documented\n- Accessibility standards are met\n",
            "code-reviewer": "- All code reviewed for quality and standards\n- Feedback provided constructively\n- No critical issues remain unresolved\n",
            "documenter": "- Documentation is clear and comprehensive\n- All public APIs are documented\n- Examples and tutorials are included\n",
        }

        criteria = base_criteria
        if agent_role in role_criteria:
            criteria += role_criteria[agent_role]

        return criteria

    async def generate_mission(
        self,
        product: Product,
        project_description: str,
        user_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Simplified mission generation for orchestrator integration.

        This is a wrapper around generate_missions that handles the full workflow
        with minimal parameters. Added for Handover 0086A Task 2.1.

        Args:
            product: Product with vision document
            project_description: Project requirements description
            user_id: Optional user ID for field priority configuration

        Returns:
            Dictionary mapping agent roles to Mission objects
        """
        # Log user_id propagation for debugging (Handover 0086A Task 2.1)
        logger.info(
            "Generating mission",
            extra={
                "product_id": str(product.id),
                "user_id": user_id,
                "has_user_id": user_id is not None,
            },
        )

        # For now, return analysis results as this method seems to be called
        # before full mission generation. This allows the orchestrator to proceed.
        # The full generate_missions method will be called later in the workflow.
        analysis = await self.analyze_requirements(product, project_description)

        # Return empty missions dict for now - the orchestrator will call
        # generate_missions later with full context
        return {}

    async def _get_user_configuration(self, user_id: Optional[str]) -> dict:
        """
        Fetch user configuration including field priorities and Serena integration toggle.

        Handover 0086B Task 3.2: Added serena_enabled support

        Returns:
            {
                "field_priority_config": dict or None,
                "token_budget": int,
                "serena_enabled": bool
            }
        """
        if not user_id:
            return {"field_priority_config": None, "token_budget": 2000, "serena_enabled": False}

        try:
            if self.db_manager.is_async:
                async with self.db_manager.get_session_async() as session:
                    from sqlalchemy import select

                    result = await session.execute(select(User).filter_by(id=user_id))
                    user = result.scalar_one_or_none()
            else:
                with self.db_manager.get_session() as session:
                    user = session.query(User).filter_by(id=user_id).first()

            if user and user.field_priority_config:
                # Extract serena_enabled from field_priority_config JSONB
                serena_enabled = user.field_priority_config.get("serena_enabled", False)
                token_budget = user.field_priority_config.get("token_budget", 2000)

                return {
                    "field_priority_config": user.field_priority_config,
                    "token_budget": token_budget,
                    "serena_enabled": serena_enabled,
                }
        except Exception as e:
            logger.warning(f"Failed to fetch user configuration: {e}")

        return {"field_priority_config": None, "token_budget": 2000, "serena_enabled": False}

    async def _fetch_serena_codebase_context(self, project_id: str, tenant_key: str) -> str:
        """
        Fetch codebase context from Serena MCP tool.

        Handover 0086B Task 3.2: Serena integration for mission generation

        This method attempts to fetch codebase analysis from the Serena MCP tool
        (if available). It provides graceful degradation - if Serena is unavailable
        or returns an error, it returns an empty string.

        Args:
            project_id: Project UUID as string
            tenant_key: Tenant key for isolation

        Returns:
            Serena codebase context string, or empty string if unavailable

        Note:
            This is a placeholder implementation. Full Serena integration requires:
            1. MCP client infrastructure (mcp_client.py)
            2. Serena tool registration
            3. Project-to-codebase path mapping
        """
        try:
            # TODO: Implement full Serena MCP integration
            # For now, return empty string (graceful degradation)
            logger.info(
                "Serena integration requested but not yet implemented",
                extra={"project_id": project_id, "tenant_key": tenant_key},
            )
            return ""

            # Future implementation:
            # from src.giljo_mcp.mcp_client import MCPClient
            #
            # mcp_client = MCPClient()
            # result = await mcp_client.call_tool(
            #     tool_name="serena__get_symbols_overview",
            #     arguments={"relative_path": "."}
            # )
            #
            # return result.get("content", "")

        except Exception as e:
            logger.warning(
                f"Failed to fetch Serena context: {e}",
                extra={"project_id": project_id, "tenant_key": tenant_key},
                exc_info=True,
            )
            return ""

    def _get_detail_level(self, priority: int) -> str:
        """Map priority (1-10) to detail level."""
        if priority >= 10:
            return "full"
        if priority >= 7:
            return "moderate"
        if priority >= 4:
            return "abbreviated"
        if priority >= 1:
            return "minimal"
        return "exclude"

    def _abbreviate_codebase_summary(self, codebase_text: Optional[str]) -> str:
        """Reduce codebase summary to 50% tokens."""
        if not codebase_text:
            return ""

        lines = codebase_text.split("\n")
        abbreviated = []
        in_section = False
        section_line_count = 0

        for line in lines:
            stripped = line.strip()

            if stripped.startswith("#"):
                abbreviated.append(line)
                in_section = True
                section_line_count = 0
                continue

            if in_section and section_line_count < 2:
                abbreviated.append(line)
                section_line_count += 1
                continue

            if stripped.startswith(("-", "*", "•")):
                abbreviated.append(line)
                continue

        result = "\n".join(abbreviated)
        if codebase_text:
            reduction = ((len(codebase_text) - len(result)) / len(codebase_text)) * 100
            logger.debug(
                f"Abbreviated codebase: {self._count_tokens(codebase_text)} → {self._count_tokens(result)} tokens ({reduction:.1f}% reduction)"
            )
        return result

    def _minimal_codebase_summary(self, codebase_text: Optional[str]) -> str:
        """Reduce codebase summary to 20% tokens."""
        if not codebase_text:
            return ""

        lines = codebase_text.split("\n")
        minimal = []
        last_was_header = False

        for line in lines:
            stripped = line.strip()

            if stripped.startswith("##") and not stripped.startswith("###"):
                minimal.append(line)
                last_was_header = True
                continue

            if last_was_header and stripped:
                minimal.append(line)
                last_was_header = False
                continue

            last_was_header = False

        result = "\n".join(minimal)
        if codebase_text:
            reduction = ((len(codebase_text) - len(result)) / len(codebase_text)) * 100
            logger.debug(
                f"Minimal codebase: {self._count_tokens(codebase_text)} → {self._count_tokens(result)} tokens ({reduction:.1f}% reduction)"
            )
        return result

    async def _build_context_with_priorities(
        self, product: Product, project: Project, field_priorities: dict = None, user_id: Optional[str] = None, include_serena: bool = False
    ) -> str:
        """
        Build context respecting user's field priorities for 70% token reduction.

        This method orchestrates the field priority system to generate condensed context
        that includes only the most relevant information based on user preferences.
        Achieves significant token reduction while maintaining quality.

        Args:
            product: Product model with vision document and config_data
            project: Project model with description and codebase_summary
            field_priorities: Dict mapping field names to priority (1-10)
                             Higher values = more important. 0 = exclude.
                             Example: {"product_vision": 10, "codebase_summary": 4}
            user_id: User ID for logging and audit trail (optional)
            include_serena: Whether to fetch and include Serena codebase context (MANDATORY if enabled in config.yaml)

        Returns:
            Formatted context string with priority-based detail levels.
            Sections are intelligently abbreviated or excluded based on priorities.

        Detail Level Mapping (via _get_detail_level):
            Priority 10: "full" - Complete content
            Priority 7-9: "moderate" - Slightly condensed
            Priority 4-6: "abbreviated" - 50% token reduction
            Priority 1-3: "minimal" - 80% token reduction (key points only)
            Priority 0: "exclude" - Omitted entirely

        Multi-Tenant Isolation:
            All data access uses product/project models which are already tenant-filtered
            by upstream code. No additional tenant filtering needed here.

        Example Usage:
            context = await planner._build_context_with_priorities(
                product=product,
                project=project,
                field_priorities={
                    "product_vision": 10,      # Full detail
                    "project_description": 8,  # Full detail
                    "codebase_summary": 4,     # Abbreviated (50% tokens)
                    "architecture": 2,         # Minimal (20% tokens)
                },
                user_id=str(user.id)
            )
        """
        # Default to empty dict if not provided
        if field_priorities is None:
            field_priorities = {}

        # Structured logging for debugging and analytics
        logger.info(
            "Building context with field priorities",
            extra={
                "product_id": str(product.id),
                "project_id": str(project.id),
                "tenant_key": product.tenant_key,
                "priorities": field_priorities,
                "user_id": user_id,
                "operation": "build_context_with_priorities",
            },
        )

        context_sections = []
        total_tokens = 0
        tokens_before_reduction = 0  # Track original size for metrics

        # === MANDATORY: Product Name (ALWAYS included - non-negotiable) ===
        product_name_section = f"## Product\n**Name**: {product.name}"
        if product.description:
            product_name_section += f"\n**Description**: {product.description}"
        context_sections.append(product_name_section)
        name_tokens = self._count_tokens(product_name_section)
        total_tokens += name_tokens
        tokens_before_reduction += name_tokens

        logger.debug(
            f"Product name/description: {name_tokens} tokens (MANDATORY)",
            extra={
                "field": "product_name",
                "priority": "MANDATORY",
                "tokens": name_tokens,
            },
        )

        # === MANDATORY: Product Vision (ALWAYS included - non-negotiable) ===
        # Vision document is foundational context that orchestrator needs
        vision_text = product.vision_document or ""
        if vision_text:
            formatted_vision = f"## Product Vision\n{vision_text}"
            context_sections.append(formatted_vision)
            vision_tokens = self._count_tokens(formatted_vision)
            total_tokens += vision_tokens
            tokens_before_reduction += vision_tokens

            logger.debug(
                f"Product vision: {vision_tokens} tokens (MANDATORY - full content)",
                extra={
                    "field": "product_vision",
                    "priority": "MANDATORY",
                    "detail_level": "full",
                    "tokens": vision_tokens,
                },
            )

        # === MANDATORY: Project Description (ALWAYS included - non-negotiable) ===
        desc_text = project.description or ""
        if desc_text:
            formatted_desc = f"## Project Description\n{desc_text}"
            context_sections.append(formatted_desc)
            desc_tokens = self._count_tokens(formatted_desc)
            total_tokens += desc_tokens
            tokens_before_reduction += desc_tokens

            logger.debug(
                f"Project description: {desc_tokens} tokens (MANDATORY - full content)",
                extra={
                    "field": "project_description",
                    "priority": "MANDATORY",
                    "detail_level": "full",
                    "tokens": desc_tokens,
                },
            )

        # === Codebase Summary Section ===
        # Use specialized abbreviation methods that preserve structure
        codebase_priority = field_priorities.get("codebase_summary", 0)
        if codebase_priority > 0:
            codebase_detail = self._get_detail_level(codebase_priority)
            codebase_original = project.codebase_summary or ""

            if codebase_detail == "full" or codebase_detail == "moderate":
                # Full codebase summary
                codebase_text = codebase_original
            elif codebase_detail == "abbreviated":
                # 50% reduction using smart abbreviation (preserves headers, key bullets)
                codebase_text = self._abbreviate_codebase_summary(codebase_original)
            else:  # minimal
                # 80% reduction - headers + first line only
                codebase_text = self._minimal_codebase_summary(codebase_original)

            if codebase_text:
                formatted_codebase = f"## Codebase\n{codebase_text}"
                context_sections.append(formatted_codebase)
                codebase_tokens = self._count_tokens(formatted_codebase)
                total_tokens += codebase_tokens
                tokens_before_reduction += self._count_tokens(f"## Codebase\n{codebase_original}")

                logger.debug(
                    f"Codebase summary: {codebase_tokens} tokens (priority={codebase_priority}, detail={codebase_detail})",
                    extra={
                        "field": "codebase_summary",
                        "priority": codebase_priority,
                        "detail_level": codebase_detail,
                        "tokens": codebase_tokens,
                    },
                )

        # === Architecture Section ===
        # Extract from product.config_data (JSONB field)
        arch_priority = field_priorities.get("architecture", 0)
        if arch_priority > 0 and product.config_data:
            arch_detail = self._get_detail_level(arch_priority)

            # Architecture can be in multiple places in config_data
            arch_text = ""
            if isinstance(product.config_data, dict):
                # Try "architecture" key first (freeform text)
                arch_value = product.config_data.get("architecture", "")

                # Check if architecture is a string or dict
                if isinstance(arch_value, str):
                    arch_text = arch_value
                elif isinstance(arch_value, dict):
                    # Structured architecture fields - combine them
                    pattern = arch_value.get("pattern", "")
                    api_style = arch_value.get("api_style", "")
                    design_patterns = arch_value.get("design_patterns", "")
                    notes = arch_value.get("notes", "")
                    parts = [p for p in [pattern, api_style, design_patterns, notes] if p]
                    arch_text = "\n".join(parts)

            if arch_text and isinstance(arch_text, str):
                if arch_detail == "full" or arch_detail == "moderate":
                    formatted_arch = arch_text
                elif arch_detail == "abbreviated":
                    # Extract first paragraph only
                    paragraphs = arch_text.split("\n\n")
                    formatted_arch = paragraphs[0] if paragraphs else arch_text
                else:  # minimal
                    # Extract first sentence only
                    sentences = arch_text.split(". ")
                    formatted_arch = sentences[0] + "." if sentences else arch_text

                if formatted_arch:
                    formatted_section = f"## Architecture\n{formatted_arch}"
                    context_sections.append(formatted_section)
                    arch_tokens = self._count_tokens(formatted_section)
                    total_tokens += arch_tokens
                    tokens_before_reduction += self._count_tokens(f"## Architecture\n{arch_text}")

                    logger.debug(
                        f"Architecture: {arch_tokens} tokens (priority={arch_priority}, detail={arch_detail})",
                        extra={
                            "field": "architecture",
                            "priority": arch_priority,
                            "detail_level": arch_detail,
                            "tokens": arch_tokens,
                        },
                    )

        # === MANDATORY: Serena Codebase Context (if enabled) ===
        # Serena integration is controlled by user toggle in My Settings → Integrations
        # When enabled, provides intelligent codebase symbols/structure overview
        if include_serena:
            serena_context = await self._fetch_serena_codebase_context(
                project_id=str(project.id),
                tenant_key=product.tenant_key
            )
            if serena_context:
                formatted_serena = f"## Codebase Context (Serena)\n{serena_context}"
                context_sections.append(formatted_serena)
                serena_tokens = self._count_tokens(formatted_serena)
                total_tokens += serena_tokens

                logger.debug(
                    f"Serena codebase context: {serena_tokens} tokens (MANDATORY when enabled)",
                    extra={
                        "field": "serena_context",
                        "priority": "MANDATORY",
                        "tokens": serena_tokens,
                    },
                )
            else:
                logger.info(
                    "Serena enabled but no context returned (graceful degradation)",
                    extra={
                        "project_id": str(project.id),
                        "operation": "build_context_with_priorities",
                    },
                )

        # === Token Reduction Metrics ===
        # Calculate and log token reduction percentage for analytics
        reduction_pct = 0.0
        if tokens_before_reduction > 0:
            reduction_pct = ((tokens_before_reduction - total_tokens) / tokens_before_reduction) * 100

        logger.info(
            f"Context built: {total_tokens} tokens ({reduction_pct:.1f}% reduction)",
            extra={
                "product_id": str(product.id),
                "project_id": str(project.id),
                "total_tokens": total_tokens,
                "tokens_before_reduction": tokens_before_reduction,
                "reduction_percentage": reduction_pct,
                "priorities": field_priorities,
                "user_id": user_id,
                "sections_included": len(context_sections),
                "serena_enabled": include_serena,
                "operation": "build_context_with_priorities",
            },
        )

        # Join all sections with double newlines for readability
        return "\n\n".join(context_sections)

    async def analyze_requirements(self, product: Product, project_description: str) -> RequirementAnalysis:
        """
        Analyze product requirements to determine needed agents and complexity.

        Args:
            product: Product with vision document
            project_description: User's project description

        Returns:
            RequirementAnalysis with work types, complexity, and estimates
        """
        # Extract tech stack from product config
        tech_stack = []
        if product.config_data and "tech_stack" in product.config_data:
            tech_stack = product.config_data["tech_stack"]

        # Extract features from product config
        features = []
        if product.config_data and "features" in product.config_data:
            features = product.config_data["features"]

        # Extract keywords from vision and description
        combined_text = f"{product.vision_document or ''} {project_description}"
        keywords = self._extract_keywords(combined_text)

        # Categorize work types
        work_types = self._categorize_work(keywords, features)

        # Assess complexity
        description_length = len(combined_text)
        complexity = self._assess_complexity(description_length, len(features), len(tech_stack))

        # Estimate agent count
        estimated_agents = self._estimate_agent_count(work_types, complexity)

        return RequirementAnalysis(
            work_types=work_types,
            complexity=complexity,
            tech_stack=tech_stack,
            keywords=keywords,
            estimated_agents_needed=estimated_agents,
            feature_categories=features if features else None,
        )

    def _get_field_priority_config(self, user_id: Optional[str]) -> dict:
        """
        Get user's field priority configuration or default.

        Args:
            user_id: User ID (optional)

        Returns:
            Field priority config dict
        """
        if not user_id:
            return DEFAULT_FIELD_PRIORITY

        # Query user settings
        try:
            user = self.db_manager.session.query(User).filter_by(id=user_id).first()
            if user and user.field_priority_config:
                return user.field_priority_config
        except Exception as e:
            logger.warning(f"Failed to load user field priority config: {e}")

        return DEFAULT_FIELD_PRIORITY

    def _get_field_value(self, config_data: dict, field_path: str):
        """
        Get field value from config_data using dot notation.

        Args:
            config_data: Product config_data dict
            field_path: Dot-separated path (e.g., "tech_stack.languages")

        Returns:
            Field value or None
        """
        keys = field_path.split(".")
        value = config_data

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None

        return value

    def _format_field(self, field_path: str, value) -> str:
        """
        Format field for mission content.

        Args:
            field_path: Field path (e.g., "tech_stack.languages")
            value: Field value

        Returns:
            Formatted section
        """
        label = self.FIELD_LABELS.get(field_path, field_path)

        # Format based on type
        if isinstance(value, list):
            items = "\n".join(f"- {item}" for item in value)
            return f"\n### {label}\n{items}\n"
        if isinstance(value, (int, float)):
            return f"\n### {label}\n{value}%\n"
        return f"\n### {label}\n{value}\n"

    def _build_config_data_section(self, product: Product, priority_config: dict, token_budget: int) -> tuple[str, int]:
        """
        Build config_data section respecting priority and token budget.

        Args:
            product: Product with config_data
            priority_config: Priority configuration
            token_budget: Remaining token budget

        Returns:
            (section_content, tokens_used)
        """
        if not product.config_data:
            return "", 0

        content = "\n## Product Configuration\n"
        tokens_used = self._count_tokens(content)

        # Get fields by priority using the config/defaults.py structure
        fields_dict = priority_config.get("fields", {})

        # Sort fields by priority value
        sorted_fields = sorted(fields_dict.items(), key=lambda x: x[1])

        # Process fields in priority order
        for field_path, priority in sorted_fields:
            field_content = self._get_field_value(product.config_data, field_path)
            if field_content:
                section = self._format_field(field_path, field_content)
                section_tokens = self._count_tokens(section)

                # Priority 1 always included, others respect budget
                if priority == 1 or (tokens_used + section_tokens <= token_budget):
                    content += section
                    tokens_used += section_tokens
                # Stop adding fields if budget exceeded (unless P1)
                elif priority > 1:
                    logger.debug(f"Skipping field {field_path} (priority {priority}) due to token budget")

        return content, tokens_used

    async def _generate_agent_mission(
        self,
        agent_config: AgentConfig,
        analysis: RequirementAnalysis,
        product: Product,
        project: Project,
        vision_chunks: list[str],
        user_id: Optional[str] = None,
        serena_context: str = "",
    ) -> Mission:
        """
        Generate a condensed mission for a specific agent.

        Handover 0086B Task 3.2: Added serena_context parameter

        Args:
            agent_config: Agent configuration
            analysis: Requirement analysis
            product: Product with vision
            project: Project being worked on
            vision_chunks: Filtered vision document chunks
            user_id: User ID for field priority configuration (optional)
            serena_context: Optional Serena codebase context (empty string if disabled)

        Returns:
            Mission object with condensed content (500-1500 tokens)
        """
        # Filter vision chunks for this role
        relevant_chunks = self._filter_vision_for_role(vision_chunks, agent_config.role)

        # Get role-specific content
        responsibilities = self._get_role_responsibilities(agent_config.role)
        success_criteria = self._get_success_criteria(agent_config.role, analysis)

        # Build condensed mission content
        mission_content = f"""# Mission: {agent_config.role.title()} for {project.name}

## Project Context
Product: {product.name}
Project: {project.name}
Mission: {project.mission}
Complexity: {analysis.complexity}

## Your Role
{responsibilities}

## Relevant Vision Sections
"""

        # Add relevant vision chunks
        for i, chunk in enumerate(relevant_chunks, 1):
            mission_content += f"\n### Section {i}\n{chunk}\n"

        # Calculate base token usage
        base_tokens = self._count_tokens(mission_content)

        # Get user's field priority configuration
        priority_config = self._get_field_priority_config(user_id)
        token_budget = priority_config.get("token_budget", 1500)

        # Reserve tokens for footer sections (success criteria, scope, protocol)
        reserved_tokens = 200
        remaining_budget = token_budget - base_tokens - reserved_tokens

        # Add config_data section with priority (Handover 0048)
        if remaining_budget > 0:
            config_section, config_tokens = self._build_config_data_section(product, priority_config, remaining_budget)
            mission_content += config_section
        else:
            logger.warning(
                f"No token budget remaining for config_data section (base={base_tokens}, budget={token_budget})"
            )

        # Handover 0086B Task 3.2: Add Serena codebase context if available
        if serena_context:
            serena_tokens = self._count_tokens(serena_context)
            # Add Serena section (with token budget consideration)
            mission_content += f"""
## Codebase Context (Serena)
{serena_context}
"""
            logger.debug(
                f"Added Serena context to {agent_config.role} mission: {serena_tokens} tokens",
                extra={"agent_role": agent_config.role, "serena_tokens": serena_tokens},
            )

        # Add success criteria
        mission_content += f"\n## Success Criteria\n{success_criteria}"

        # Add scope boundary
        mission_content += f"""
## Scope Boundary
- Focus ONLY on {agent_config.role} responsibilities
- Stay within the context of {project.name}
- Coordinate with other agents through the Orchestrator
- Do not implement features outside your role
"""

        # Add communication protocol
        mission_content += """
## Communication Protocol
- Report progress and blockers to the Orchestrator
- Request clarification when requirements are unclear
- Share insights and findings with relevant agents
- Update mission status regularly
"""

        # Count final tokens
        token_count = self._count_tokens(mission_content)

        # Extract chunk IDs if available
        context_chunk_ids = []
        if hasattr(product, "context_chunks"):
            context_chunk_ids = [chunk.chunk_id for chunk in product.context_chunks[:3]]

        return Mission(
            agent_role=agent_config.role,
            content=mission_content,
            token_count=token_count,
            context_chunk_ids=context_chunk_ids,
            priority=agent_config.priority,
            scope_boundary=f"Focus on {agent_config.role} responsibilities only",
            success_criteria=success_criteria,
            dependencies=None,
        )

    async def generate_missions(
        self,
        analysis: RequirementAnalysis,
        product: Product,
        project: Project,
        selected_agents: list[AgentConfig],
        user_id: Optional[str] = None,
    ) -> dict[str, Mission]:
        """
        Generate condensed missions for all selected agents.

        Args:
            analysis: Requirement analysis results
            product: Product with vision document
            project: Project being worked on
            selected_agents: List of agent configurations
            user_id: User ID for field priority configuration (optional)

        Returns:
            Dictionary mapping agent role to Mission object
        """
        missions = {}

        # Get vision chunks from context repository or vision document
        vision_chunks = []
        if product.chunked:
            # Try to fetch from context repository
            try:
                if self.db_manager.is_async:
                    async with self.db_manager.get_session_async() as session:
                        chunks = self.context_repo.search_chunks(
                            session,
                            product.tenant_key,
                            product.id,
                            query=" ".join(analysis.keywords[:3]),
                            limit=10,
                        )
                        vision_chunks = [chunk.content for chunk in chunks]
                else:
                    with self.db_manager.get_session() as session:
                        chunks = self.context_repo.search_chunks(
                            session,
                            product.tenant_key,
                            product.id,
                            query=" ".join(analysis.keywords[:3]),
                            limit=10,
                        )
                        vision_chunks = [chunk.content for chunk in chunks]
            except Exception as e:
                logger.warning(f"Failed to fetch context chunks: {e}. Using vision document.")
                vision_chunks = []

        # Fallback to vision document if no chunks found
        if not vision_chunks and product.vision_document:
            # Split vision document into rough chunks
            vision_text = product.vision_document
            # Split by double newline (paragraphs) or sections
            chunks = re.split(r"\n\n+|(?=^#{1,3} )", vision_text, flags=re.MULTILINE)
            vision_chunks = [chunk.strip() for chunk in chunks if chunk.strip()]

        # Calculate original token count
        original_tokens = self._count_tokens(product.vision_document or "")

        # Handover 0086B Task 3.2: Fetch Serena toggle from config.yaml (system-wide setting)
        # IMPORTANT: Serena toggle is in My Settings → Integrations and stored in config.yaml
        # NOT in user.field_priority_config (that was old implementation)
        serena_enabled = False
        try:
            from pathlib import Path
            import yaml

            config_path = Path.cwd() / "config.yaml"
            if config_path.exists():
                with open(config_path, encoding="utf-8") as f:
                    config_data = yaml.safe_load(f) or {}
                serena_enabled = config_data.get("features", {}).get("serena_mcp", {}).get("use_in_prompts", False)
        except Exception as e:
            logger.warning(f"Failed to read Serena config: {e}")
            serena_enabled = False

        # Fetch Serena codebase context if enabled
        serena_context = ""
        if serena_enabled:
            serena_context = await self._fetch_serena_codebase_context(
                project_id=str(project.id), tenant_key=product.tenant_key
            )
            if serena_context:
                serena_tokens = self._count_tokens(serena_context)
                logger.info(
                    f"Serena codebase context fetched: {serena_tokens} tokens",
                    extra={
                        "project_id": str(project.id),
                        "tenant_key": product.tenant_key,
                        "user_id": user_id,
                        "serena_tokens": serena_tokens,
                    },
                )
            else:
                logger.info(
                    "Serena enabled but no context returned (graceful degradation)",
                    extra={"project_id": str(project.id), "tenant_key": product.tenant_key, "user_id": user_id},
                )
        else:
            logger.debug(
                "Serena integration disabled by user configuration",
                extra={"project_id": str(project.id), "user_id": user_id},
            )

        # Generate mission for each agent (Handover 0048: pass user_id for field priority)
        for agent_config in selected_agents:
            mission = await self._generate_agent_mission(
                agent_config, analysis, product, project, vision_chunks, user_id, serena_context
            )
            missions[agent_config.role] = mission

        # Calculate total mission tokens
        total_mission_tokens = sum(mission.token_count for mission in missions.values())

        # Calculate reduction percentage
        # We compare original tokens to average per-agent mission tokens
        if original_tokens > 0 and missions:
            avg_mission_tokens = total_mission_tokens / len(missions)
            reduction_percent = ((original_tokens - avg_mission_tokens) / original_tokens) * 100
        else:
            reduction_percent = 0.0

        # Store token metrics
        await self._store_token_metrics(project.id, original_tokens, total_mission_tokens, reduction_percent)

        logger.info(
            f"Generated {len(missions)} missions. "
            f"Token reduction: {reduction_percent:.1f}% "
            f"(Original: {original_tokens}, Per-agent avg: {total_mission_tokens // len(missions) if missions else 0})"
        )

        return missions

    async def _store_token_metrics(
        self,
        project_id: str,
        original_tokens: int,
        total_mission_tokens: int,
        reduction_percent: float,
    ) -> None:
        """
        Store token reduction metrics in project metadata.

        Args:
            project_id: Project ID
            original_tokens: Original vision document token count
            total_mission_tokens: Total tokens across all missions
            reduction_percent: Percentage reduction achieved
        """
        try:
            if self.db_manager.is_async:
                async with self.db_manager.get_session_async() as session:
                    project = await session.get(Project, project_id)
                    if project:
                        if not project.meta_data:
                            project.meta_data = {}
                        project.meta_data["token_metrics"] = {
                            "original_tokens": original_tokens,
                            "total_mission_tokens": total_mission_tokens,
                            "reduction_percent": round(reduction_percent, 2),
                        }
                        await session.commit()
            else:
                with self.db_manager.get_session() as session:
                    project = session.get(Project, project_id)
                    if project:
                        if not project.meta_data:
                            project.meta_data = {}
                        project.meta_data["token_metrics"] = {
                            "original_tokens": original_tokens,
                            "total_mission_tokens": total_mission_tokens,
                            "reduction_percent": round(reduction_percent, 2),
                        }
                        session.commit()

        except Exception as e:
            logger.error(f"Failed to store token metrics: {e}")
