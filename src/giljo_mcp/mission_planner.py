"""
Mission Planner for GiljoAI Agent Orchestration MCP Server.

Generates condensed agent missions from product vision analysis.
Achieves context prioritization and orchestration through intelligent context filtering and summarization.

Phase 1 Implementation: Template-based analysis (no LLM calls)

⚠️  IMPORTANT - Product Vision Field Migration (Handover 0128e):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
This file has been migrated to use Product.vision_documents relationship.
DO NOT use deprecated Product fields (vision_path, vision_document, vision_type, chunked).
✅ Use: product.primary_vision_text, product.primary_vision_path, product.vision_is_chunked
See: src/giljo_mcp/models/products.py for helper properties
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import logging
import re
from typing import Any, ClassVar, Optional

import tiktoken
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .config.defaults import DEFAULT_FIELD_PRIORITY
from .database import DatabaseManager
from .models import Product, Project, User
from .models.context import MCPContextIndex
from .orchestration_types import AgentConfig, Mission, RequirementAnalysis
from .prompt_generation.testing_config_generator import TestingConfigGenerator
from .repositories.context_repository import ContextRepository


logger = logging.getLogger(__name__)


# Default field priorities for context building (Handover 0302, 0303)
# Applied when user has no custom field_priority_config
# Ensures meaningful context even for new users who haven't customized priorities
# Default field priorities for context building (Handover 0302, 0303, 0266)
# Applied when user has no custom field_priority_config
# Ensures meaningful context even for new users who haven't customized priorities
# Updated to v2.0 format: Priority values 1-4, new category names (Handover 0266)
DEFAULT_FIELD_PRIORITIES = {
    # v2.0 categories with priority levels (1=CRITICAL, 2=IMPORTANT, 3=NICE_TO_HAVE, 4=EXCLUDED)
    "product_core": 1,  # CRITICAL - Always include product name, description, features
    "vision_documents": 2,  # IMPORTANT - Include vision docs if budget allows
    "agent_templates": 2,  # IMPORTANT - Agent templates for spawning
    "project_context": 1,  # CRITICAL - Current project metadata
    "memory_360": 3,  # NICE_TO_HAVE - Historical project outcomes
    "git_history": 3,  # NICE_TO_HAVE - Recent commits
    "tech_stack": 2,  # IMPORTANT - Programming languages, frameworks, databases
    "architecture": 2,  # IMPORTANT - Architecture patterns, API style, design patterns
    "testing": 2,  # IMPORTANT - Quality standards, testing strategy, frameworks
    # Legacy v1.0 fields (kept for backward compatibility during transition)
    # These will be removed in v4.0
    "product_memory.sequential_history": 3,  # Maps to NICE_TO_HAVE
    "config_data.architecture": 4,  # Maps to EXCLUDED
    "config_data.test_methodology": 2,  # Maps to IMPORTANT
    "config_data.coding_standards": 3,  # Maps to NICE_TO_HAVE
    "config_data.deployment_strategy": 4,  # Maps to EXCLUDED
}


class MissionPlanner:
    """
    Generate mission plans from product vision analysis.

    Phase 1 Implementation: Template-based analysis (no LLM calls)
    Target: context prioritization and orchestration through intelligent context filtering
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
        "agent_templates": "Available Agent Templates",
        "test_config.coverage_target": "Coverage Target",
        # Config data fields (Handover 0303)
        "config_data.architecture": "System Architecture",
        "config_data.test_methodology": "Test Methodology",
        "config_data.agent_execution_methodologies": "Agent Execution Methods",
        "config_data.deployment_strategy": "Deployment Strategy",
        "config_data.coding_standards": "Coding Standards",
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
                    from sqlalchemy import select

                    result = session.execute(select(User).filter_by(id=user_id))
                    user = result.scalar_one_or_none()

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
        """
        Map priority to detail level.

        Handover 0266: Updated for v2.0 priority system (1-4 scale).

        v2.0 Priority Mapping:
        - Priority 1 (CRITICAL)     -> "full" (100% of content, always included)
        - Priority 2 (IMPORTANT)    -> "moderate" (75% of content)
        - Priority 3 (NICE_TO_HAVE) -> "abbreviated" (50% of content)
        - Priority 4 (EXCLUDED)     -> "exclude" (0% - omitted entirely)

        v1.0 Legacy Support (for backward compatibility):
        - Priority 10   -> "full"
        - Priority 7-9  -> "moderate"
        - Priority 4-6  -> "abbreviated"
        - Priority 1-3  -> "minimal"
        - Priority 0    -> "exclude"

        Args:
            priority: Field importance weight (v2.0: 1-4, v1.0: 0-10)

        Returns:
            Detail level string: "full", "moderate", "abbreviated", "minimal", "exclude"

        Detail Levels:
            - "full": Complete content (~100% of original tokens)
            - "moderate": Slightly condensed (~75% of original tokens)
            - "abbreviated": Significantly condensed (~50% of original tokens)
            - "minimal": Key points only (~20% of original tokens)
            - "exclude": Omitted entirely (0 tokens)
        """
        # v2.0 priority system (1-4 scale)
        if priority <= 4:
            if priority == 1:
                return "full"  # CRITICAL - always include
            elif priority == 2:
                return "moderate"  # IMPORTANT - include if budget allows
            elif priority == 3:
                return "abbreviated"  # NICE_TO_HAVE - include if space remains
            elif priority == 4:
                return "exclude"  # EXCLUDED - never include
            else:
                return "exclude"  # Priority 0 or negative = exclude

        # v1.0 legacy support (0-10 scale)
        # Keep for backward compatibility during transition period
        elif priority >= 10:
            return "full"  # 0% context prioritization
        elif priority >= 7:
            return "moderate"  # 25% context prioritization
        elif priority >= 4:
            return "abbreviated"  # 50% context prioritization
        elif priority >= 1:
            return "minimal"  # 80% context prioritization
        else:
            return "exclude"  # 100% context prioritization (omitted)  # 100% context prioritization (omitted)

    def _should_include_field(self, priority: int) -> bool:
        """
        Check if a field should be included based on its priority.

        Handover 0266: Support for both v2.0 and v1.0 priority systems.

        v2.0: Priority 1-3 are included, Priority 4 is excluded.
        v1.0: Priority > 0 is included, Priority 0 is excluded.

        Args:
            priority: Field priority value

        Returns:
            True if field should be included, False if excluded
        """
        if priority <= 0:
            return False  # No priority or negative = exclude

        # v2.0 system: 1-3 included, 4 excluded
        if priority <= 4:
            return priority < 4

        # v1.0 system: any positive value is included
        return True

    def _extract_config_field(self, product: Product, field_name: str, detail_level: str) -> Optional[str]:
        """
        Extract arbitrary config_data field with detail level applied.

        Supports both string and dict values in config_data JSONB.
        Replaces hardcoded architecture extraction (backward compatible).

        Args:
            product: Product instance with config_data
            field_name: Field key in config_data (e.g., "test_methodology")
            detail_level: Context prioritization level ("full", "abbreviated", "minimal")

        Returns:
            Formatted field text with detail level applied, or None if field missing

        Examples:
            >>> # String value
            >>> config_data = {"test_methodology": "TDD with pytest"}
            >>> _extract_config_field(product, "test_methodology", "full")
            "TDD with pytest"

            >>> # Dict value (like architecture)
            >>> config_data = {"architecture": {"pattern": "MVC", "api": "REST"}}
            >>> _extract_config_field(product, "architecture", "full")
            "MVC; REST"
        """
        if not product.config_data or not isinstance(product.config_data, dict):
            return None

        # Get field value from config_data
        field_value = product.config_data.get(field_name)
        if not field_value:
            return None

        # Handle string values (most common)
        if isinstance(field_value, str):
            field_text = field_value

        # Handle dict values (like architecture with subfields)
        elif isinstance(field_value, dict):
            # Combine all non-empty dict values
            parts = [str(v) for v in field_value.values() if v]
            field_text = "; ".join(parts)

        # Handle list values
        elif isinstance(field_value, list):
            field_text = ", ".join(str(item) for item in field_value)

        # Handle other JSON types
        else:
            field_text = str(field_value)

        if not field_text.strip():
            return None

        # Apply detail level context prioritization
        if detail_level == "minimal":
            # 20% of original (truncate to first 100 chars)
            return field_text[:100] + ("..." if len(field_text) > 100 else "")
        if detail_level == "abbreviated":
            # 50% of original (truncate to first 250 chars)
            return field_text[:250] + ("..." if len(field_text) > 250 else "")
        # "full"
        # 100% - no reduction
        return field_text

    async def _get_vision_overview(
        self,
        session: AsyncSession,
        product: Product,
    ) -> dict | None:
        """
        Generate minimal vision overview instead of full content.

        Handover 0345a: Reduces orchestrator instructions from 25K+ to ~2-3K tokens
        by replacing full vision body with metadata + fetch instructions.

        Returns:
            dict with keys: total_chunks, total_tokens, fetch_instruction
            None if no chunks exist

        Example:
            {
                "total_chunks": 5,
                "total_tokens": 125000,
                "fetch_instruction": "You have 5 vision chunks (~125,000 tokens). Use fetch_vision_document(chunk=N) to read them."
            }
        """
        # Query chunk metadata only (not content) for efficiency
        stmt = (
            select(
                func.count(MCPContextIndex.id).label("chunk_count"),
                func.sum(MCPContextIndex.token_count).label("total_tokens"),
            )
            .where(
                MCPContextIndex.tenant_key == product.tenant_key,
                MCPContextIndex.product_id == product.id,
            )
        )
        result = await session.execute(stmt)
        row = result.one()

        if row.chunk_count == 0:
            return None

        total_tokens = row.total_tokens or 0

        return {
            "total_chunks": row.chunk_count,
            "total_tokens": total_tokens,
            "fetch_instruction": f"You have {row.chunk_count} vision chunks (~{total_tokens:,} tokens). Use fetch_vision_document(chunk=N) to read them."
        }

    async def _get_relevant_vision_chunks(
        self, session, product, project, max_tokens: int | None = None
    ) -> list[dict]:
        """
        Retrieve vision chunks, optionally ranked by relevance to project description.

        IMPORTANT: Full context policy - pass max_tokens=None to fetch ALL chunks
        without truncation. Vision chunks are pre-sized at ~25K tokens on upload
        for optimal AI ingestion.

        Args:
            session: Database session for chunk queries
            product: Product model with vision documents
            project: Project model with description (used for relevance ranking)
            max_tokens: Maximum tokens to include from chunks, or None for ALL chunks

        Returns:
            List of chunk dicts with 'content' and 'relevance_score' keys.
            Empty list if no chunks found or vision not chunked.

        Multi-Tenant Isolation:
            Queries filter by product.tenant_key and product.id automatically.

        Algorithm:
            1. Check if product has chunked vision documents
            2. Query mcp_context_index for chunks linked to vision_document_id
            3. Rank chunks by relevance to project.description
            4. If max_tokens=None, return ALL chunks (full context policy)
            5. Otherwise, return top N chunks within token budget

        Example (full context):
            chunks = await planner._get_relevant_vision_chunks(
                session=session,
                product=product,
                project=project,
                max_tokens=None  # Fetch ALL chunks
            )

        Example (with budget):
            chunks = await planner._get_relevant_vision_chunks(
                session=session,
                product=product,
                project=project,
                max_tokens=8000  # Limit to 8K tokens
            )
        """
        from sqlalchemy import select

        from src.giljo_mcp.models.context import MCPContextIndex

        # Check if product has chunked vision documents
        if not product.vision_documents:
            logger.debug(
                "No vision documents found",
                extra={"product_id": str(product.id), "operation": "get_relevant_vision_chunks"},
            )
            return []

        # Get active chunked vision documents
        chunked_docs = [
            doc for doc in product.vision_documents if doc.is_active and doc.chunked and doc.chunk_count > 0
        ]

        if not chunked_docs:
            logger.debug(
                "No chunked vision documents found",
                extra={
                    "product_id": str(product.id),
                    "total_docs": len(product.vision_documents),
                    "operation": "get_relevant_vision_chunks",
                },
            )
            return []

        # Get vision_document_ids for query
        vision_doc_ids = [doc.id for doc in chunked_docs]

        # Query chunks from mcp_context_index
        stmt = (
            select(MCPContextIndex)
            .where(
                MCPContextIndex.tenant_key == product.tenant_key,
                MCPContextIndex.vision_document_id.in_(vision_doc_ids),
            )
            .order_by(MCPContextIndex.chunk_order)
        )

        result = await session.execute(stmt)
        chunks = result.scalars().all()

        if not chunks:
            logger.warning(
                "Chunks marked but not found in database",
                extra={
                    "product_id": str(product.id),
                    "vision_doc_ids": vision_doc_ids,
                    "operation": "get_relevant_vision_chunks",
                },
            )
            return []

        logger.info(
            f"Retrieved {len(chunks)} chunks for relevance ranking",
            extra={
                "product_id": str(product.id),
                "project_id": str(project.id),
                "chunk_count": len(chunks),
                "operation": "get_relevant_vision_chunks",
            },
        )

        # Rank chunks by relevance to project description
        ranked_chunks = self._rank_chunk_relevance(chunks=chunks, project_description=project.description or "")

        # Full context policy: if max_tokens=None, return ALL chunks without truncation
        if max_tokens is None:
            # Add token counts to each chunk for reference
            for chunk_data in ranked_chunks:
                chunk_data["tokens"] = self._count_tokens(chunk_data["content"])

            total_tokens = sum(c["tokens"] for c in ranked_chunks)
            logger.info(
                f"Full context: returning ALL {len(ranked_chunks)} chunks ({total_tokens} tokens)",
                extra={
                    "product_id": str(product.id),
                    "project_id": str(project.id),
                    "chunks_returned": len(ranked_chunks),
                    "total_tokens": total_tokens,
                    "max_tokens": "unlimited",
                    "operation": "get_relevant_vision_chunks",
                },
            )
            return ranked_chunks

        # Token budget mode: select top chunks within budget
        selected_chunks = []
        total_tokens = 0

        for chunk_data in ranked_chunks:
            chunk_tokens = self._count_tokens(chunk_data["content"])

            if total_tokens + chunk_tokens > max_tokens:
                logger.debug(
                    f"Token budget reached: {total_tokens}/{max_tokens}",
                    extra={
                        "total_tokens": total_tokens,
                        "max_tokens": max_tokens,
                        "chunks_selected": len(selected_chunks),
                        "operation": "get_relevant_vision_chunks",
                    },
                )
                break

            chunk_data["tokens"] = chunk_tokens
            selected_chunks.append(chunk_data)
            total_tokens += chunk_tokens

        logger.info(
            f"Selected {len(selected_chunks)} chunks ({total_tokens} tokens)",
            extra={
                "product_id": str(product.id),
                "project_id": str(project.id),
                "chunks_selected": len(selected_chunks),
                "total_chunks": len(chunks),
                "total_tokens": total_tokens,
                "max_tokens": max_tokens,
                "reduction_pct": ((len(chunks) - len(selected_chunks)) / len(chunks) * 100) if chunks else 0,
                "operation": "get_relevant_vision_chunks",
            },
        )

        return selected_chunks

    def _rank_chunk_relevance(self, chunks: list, project_description: str) -> list[dict]:
        """
        Rank chunks by relevance to project description using keyword matching.

        Algorithm:
            1. Extract keywords from project description (lowercase, dedupe)
            2. For each chunk, count keyword matches in content
            3. Calculate relevance score: matches / total_keywords
            4. Sort chunks by score (descending)

        Args:
            chunks: List of MCPContextIndex model instances
            project_description: Project description text for keyword extraction

        Returns:
            List of dicts sorted by relevance (highest first):
            [
                {'content': '...', 'relevance_score': 0.85, 'chunk_id': '...'},
                {'content': '...', 'relevance_score': 0.72, 'chunk_id': '...'},
            ]

        Future Enhancement:
            - Use semantic embeddings (sentence-transformers)
            - TF-IDF scoring
            - Named entity recognition
        """
        import re

        # Extract keywords from project description
        # Remove common stop words and punctuation
        stop_words = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
            "from",
            "up",
            "about",
            "into",
            "through",
            "during",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "being",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "should",
            "could",
            "may",
            "might",
            "must",
            "can",
            "this",
            "that",
            "these",
            "those",
            "i",
            "you",
            "he",
            "she",
            "it",
            "we",
            "they",
            "them",
            "their",
            "what",
            "which",
            "who",
            "when",
            "where",
            "why",
            "how",
        }

        # Tokenize and clean project description
        words = re.findall(r"\b\w+\b", project_description.lower())
        keywords = [w for w in words if w not in stop_words and len(w) > 2]

        if not keywords:
            # No keywords - return chunks in original order with neutral score
            logger.debug(
                "No keywords extracted from project description",
                extra={"project_description_length": len(project_description), "operation": "rank_chunk_relevance"},
            )
            return [{"content": chunk.content, "relevance_score": 0.5, "chunk_id": chunk.chunk_id} for chunk in chunks]

        logger.debug(
            f"Extracted {len(keywords)} keywords for ranking",
            extra={
                "keywords": keywords[:10],  # First 10 for logging
                "total_keywords": len(keywords),
                "operation": "rank_chunk_relevance",
            },
        )

        # Score each chunk
        scored_chunks = []
        for chunk in chunks:
            chunk_text = (chunk.content or "").lower()
            matches = sum(1 for keyword in keywords if keyword in chunk_text)
            relevance_score = matches / len(keywords) if keywords else 0

            scored_chunks.append(
                {
                    "content": chunk.content,
                    "relevance_score": relevance_score,
                    "chunk_id": chunk.chunk_id,
                    "matches": matches,
                }
            )

        # Sort by relevance (descending)
        scored_chunks.sort(key=lambda x: x["relevance_score"], reverse=True)

        logger.debug(
            f"Ranked {len(scored_chunks)} chunks (top score: {scored_chunks[0]['relevance_score']:.2f})",
            extra={
                "total_chunks": len(scored_chunks),
                "top_score": scored_chunks[0]["relevance_score"] if scored_chunks else 0,
                "operation": "rank_chunk_relevance",
            },
        )

        return scored_chunks

    def _format_tech_stack(self, tech_stack: dict, detail_level: str) -> str:
        """
        Format tech stack dictionary into readable markdown.

        Applies detail level reduction to optimize token usage.

        Args:
            tech_stack: Dict with categories like {"languages": [...], "backend": [...]}
            detail_level: "full", "moderate", "abbreviated", or "minimal"

        Returns:
            Formatted markdown string with tech stack information

        Detail Level Behavior:
            full: All categories, all values
            moderate: All categories, first 3 values per category
            abbreviated: Primary categories only (languages, backend, frontend, database)
            minimal: Languages + first backend/frontend only (80% reduction)

        Example:
            >>> _format_tech_stack(
            ...     {"languages": ["Python", "TypeScript"], "backend": ["FastAPI"]},
            ...     "full"
            ... )
            "**Languages**: Python, TypeScript\\n**Backend**: FastAPI"
        """
        if not tech_stack or not isinstance(tech_stack, dict):
            return ""

        # Category display order (Handover 0302)
        # "technologies" added to support normalized list->dict conversion
        category_order = ["technologies", "languages", "backend", "frontend", "database", "deployment", "testing"]

        # Filter categories based on detail level
        if detail_level == "minimal":
            # Languages + primary backend/frontend only (80% reduction)
            # Include "technologies" for fallback list format
            allowed_categories = ["technologies", "languages", "backend", "frontend"]
        elif detail_level == "abbreviated":
            # Primary categories only (50% reduction)
            allowed_categories = ["technologies", "languages", "backend", "frontend", "database"]
        else:
            # Full or moderate - show all categories
            allowed_categories = category_order

        formatted_lines = []

        for category in category_order:
            if category not in allowed_categories:
                continue

            values = tech_stack.get(category, [])
            if not values:
                continue  # Skip empty categories

            # Apply value condensation based on detail level
            if detail_level == "minimal":
                # Show only first value for backend/frontend
                if category in ["backend", "frontend"]:
                    values = values[:1]
                # Show all languages (critical)
            elif detail_level == "moderate":
                # Show first 3 values per category
                values = values[:3]
            # full/abbreviated show all values in allowed categories

            # Format category name (capitalize first letter)
            category_label = category.replace("_", " ").capitalize()

            # Join values with commas (handle both string and list types)
            if isinstance(values, str):
                # Already a string - use as-is
                values_str = values
            elif isinstance(values, list):
                # List of values - join with commas
                values_str = ", ".join(str(v) for v in values)
            else:
                # Fallback for other types - convert to string
                values_str = str(values)

            formatted_lines.append(f"**{category_label}**: {values_str}")

        return "\n".join(formatted_lines)

    # Section name mapping for human-readable priority framing
    SECTION_NAMES = {
        "product_core": "Product Context",
        "vision_documents": "Product Vision",
        "project_context": "Project Context",
        "agent_templates": "Agent Templates",
        "memory_360": "360 Memory",
        "git_history": "Git History",
        "tech_stack": "Tech Stack",
        "architecture": "Architecture",
        "testing": "Testing Configuration",
        "testing_config": "Testing Configuration",  # Backward compatibility alias
    }

    def _apply_priority_framing(self, section_name: str, content: str, priority: int, category_key: str) -> str:
        """
        Apply priority-based framing to a context section.

        Wraps context content with priority-specific headers and guidance language
        to help orchestrators understand the importance of each section.

        Args:
            section_name: Human-readable section name (e.g., "Vision Documents")
            content: The actual content to wrap
            priority: Priority level (1=CRITICAL, 2=IMPORTANT, 3=REFERENCE, 4=EXCLUDED)
            category_key: Backend category key (for mapping to SECTION_NAMES)

        Returns:
            Framed content with priority headers, or empty string if excluded (priority 4)

        Priority Framing Levels:
            - Priority 1 (CRITICAL): Strong header with "REQUIRED FOR ALL OPERATIONS"
            - Priority 2 (IMPORTANT): Medium header with "High priority context"
            - Priority 3 (REFERENCE): Light header with "Supplemental information"
            - Priority 4 (EXCLUDED): Returns empty string (0 bytes)

        Example Output (Priority 1):
            ## **CRITICAL: Product Context** (Priority 1)
            **REQUIRED FOR ALL OPERATIONS**

            **Why This Matters**: This is CRITICAL context - all agents must align with this information.

            [original content here]
        """
        # Priority 4 = EXCLUDED - return nothing
        if priority == 4:
            return ""

        # Priority 1 = CRITICAL
        if priority == 1:
            return f"""## **CRITICAL: {section_name}** (Priority 1)
**REQUIRED FOR ALL OPERATIONS**

**Why This Matters**: This is CRITICAL context - all agents must align with this information.

{content}
"""

        # Priority 2 = IMPORTANT
        elif priority == 2:
            return f"""## **IMPORTANT: {section_name}** (Priority 2)
**High priority context**

{content}
"""

        # Priority 3 = REFERENCE
        elif priority == 3:
            return f"""## {section_name} (Priority 3 - REFERENCE)
**Supplemental information**

{content}
"""

        # Fallback: no framing (shouldn't happen with valid priorities)
        return content

    async def _build_context_with_priorities(
        self,
        product: Product,
        project: Project,
        field_priorities: dict = None,
        depth_config: dict = None,
        user_id: Optional[str] = None,
        include_serena: bool = False,
    ) -> str:
        """
        Build context respecting user's field priorities and depth configuration.

        This method orchestrates the field priority system and depth controls to generate
        condensed context that includes only the most relevant information at appropriate
        detail levels based on user preferences.

        Args:
            product: Product model with vision document and config_data
            project: Project model with description and mission
            field_priorities: Dict mapping field names to priority (1-4)
                             1=CRITICAL, 2=IMPORTANT, 3=NICE_TO_HAVE, 4=EXCLUDED
                             Example: {"vision_documents": 2, "tech_stack": 2}
            depth_config: Dict mapping field names to depth levels
                         Controls HOW MUCH detail to include for each field
                         Example: {"memory_360": 3, "git_history": 10, "agent_templates": "full"}
            user_id: User ID for logging and audit trail (optional)
            include_serena: Whether to fetch and include Serena codebase context (MANDATORY if enabled in config.yaml)

        Returns:
            Formatted context string with priority-based and depth-based filtering.
            Sections are intelligently abbreviated or excluded based on priorities and depth.

        Priority Level Mapping (v2.0):
            Priority 1: CRITICAL - Always included with full detail
            Priority 2: IMPORTANT - Included with high priority
            Priority 3: NICE_TO_HAVE - Included if space allows
            Priority 4: EXCLUDED - Omitted entirely (returns empty string)

        Depth Level Mapping (Handover 0283):
            360 Memory: 1/3/5/10 projects (number of sequential history entries)
            Git History: 5/10/25/50/100 commits (number in git log examples)
            Agent Templates: "type_only" or "full" (name/type/version vs full description)

        Multi-Tenant Isolation:
            All data access uses product/project models which are already tenant-filtered
            by upstream code. No additional tenant filtering needed here.

        Example Usage:
            context = await planner._build_context_with_priorities(
                product=product,
                project=project,
                field_priorities={
                    "vision_documents": 2,     # IMPORTANT - include vision docs
                    "project_description": 8,  # Full detail
                    "tech_stack": 8,           # Moderate-high detail
                    "config_data.architecture": 4,  # Abbreviated (50% tokens)
                },
                depth_config={
                    "memory_360": 3,            # Show 3 most recent projects
                    "git_history": 10,          # Show 10 commits in examples
                    "agent_templates": "full"   # Full agent descriptions
                },
                user_id=str(user.id)
            )
        """
        # Default to empty dict if not provided
        if field_priorities is None:
            field_priorities = {}

        # Handover 0283: Default depth configuration for backward compatibility
        if depth_config is None:
            depth_config = {
                "memory_360": 5,  # Default: 5 projects (moderate)
                "git_history": 20,  # Default: 20 commits (moderate)
                "agent_templates": "full",  # Default: full descriptions
            }

        # Fix #1: Apply default field priorities when user has no config
        # This ensures meaningful context even for new users who haven't customized priorities
        # User-provided priorities take precedence via dict merge
        if not field_priorities:
            # Empty dict - use defaults
            effective_priorities = DEFAULT_FIELD_PRIORITIES.copy()
            logger.debug(
                "No user field priorities configured - applying defaults",
                extra={
                    "default_priorities": DEFAULT_FIELD_PRIORITIES,
                    "operation": "build_context_with_priorities",
                },
            )
        else:
            # User has configured priorities - use them (no defaults)
            # This maintains user control and avoids unexpected behavior
            effective_priorities = field_priorities
            logger.debug(
                "Using user-configured field priorities",
                extra={
                    "user_priorities": field_priorities,
                    "operation": "build_context_with_priorities",
                },
            )

        # Structured logging for debugging and analytics
        logger.info(
            "Building context with field priorities and depth configuration",
            extra={
                "product_id": str(product.id),
                "project_id": str(project.id),
                "tenant_key": product.tenant_key,
                "priorities": field_priorities,
                "depth_config": depth_config,
                "user_id": user_id,
                "operation": "build_context_with_priorities",
            },
        )

        context_sections = []
        total_tokens = 0
        tokens_before_reduction = 0  # Track original size for metrics

        # === Product Name/Description (product_core priority) ===
        # Get priority for product_core (defaults to 1 if not specified)
        product_core_priority = effective_priorities.get("product_core", 1)

        if product_core_priority != 4:  # Not excluded
            product_content = f"**Name**: {product.name}"
            if product.description:
                product_content += f"\n**Description**: {product.description}"

            # Apply priority framing
            framed_product = self._apply_priority_framing(
                section_name=self.SECTION_NAMES.get("product_core", "Product Context"),
                content=product_content,
                priority=product_core_priority,
                category_key="product_core",
            )

            if framed_product:
                context_sections.append(framed_product)
            name_tokens = self._count_tokens(framed_product if framed_product else product_content)
            total_tokens += name_tokens
            tokens_before_reduction += name_tokens

            logger.debug(
                f"Product name/description: {name_tokens} tokens (priority={product_core_priority})",
                extra={
                    "field": "product_core",
                    "priority": product_core_priority,
                    "tokens": name_tokens,
                },
            )

        # === Product Vision (vision_documents priority) ===
        # Handover 0345e: Use depth configuration for semantic compression levels
        # Levels: light (5K), moderate (12.5K), heavy (25K), full (all chunks)
        # Handover 0282: Fixed key from "product_vision" to "vision_documents" (v2.0 field name)

        vision_priority = effective_priorities.get("vision_documents", 4)  # Default: EXCLUDED (user opt-in)
        if vision_priority > 0 and vision_priority != 4:  # Not excluded
            # Get depth configuration (Handover 0345e)
            vision_depth = depth_config.get("vision_documents", "moderate")  # Default to moderate

            # DEBUG: Handover 0346 - Trace vision depth configuration
            logger.info(
                f"[VISION_DEPTH_DEBUG] depth_config received: {depth_config}",
                extra={"operation": "_build_context_with_priorities"}
            )
            logger.info(
                f"[VISION_DEPTH_DEBUG] vision_depth value: '{vision_depth}' (from depth_config.get('vision_documents'))",
                extra={"operation": "_build_context_with_priorities"}
            )

            # Check if product has vision documents
            if product.vision_documents:
                async with self.db_manager.get_session_async() as session:
                    from sqlalchemy import select
                    from src.giljo_mcp.models.products import VisionDocument

                    # Get active vision document with summaries
                    stmt = select(VisionDocument).where(
                        VisionDocument.product_id == product.id,
                        VisionDocument.tenant_key == product.tenant_key,
                        VisionDocument.is_active == True
                    ).order_by(VisionDocument.display_order).limit(1)

                    result = await session.execute(stmt)
                    vision_doc = result.scalar_one_or_none()

                    if vision_doc:
                        vision_content = None
                        estimated_original_tokens = vision_doc.original_token_count or 0

                        # DEBUG: Handover 0346 - Trace summarization state
                        logger.info(
                            f"[VISION_DEPTH_DEBUG] vision_doc.is_summarized: {vision_doc.is_summarized}",
                            extra={"has_light": vision_doc.summary_light is not None, "has_mod": vision_doc.summary_moderate is not None, "has_heavy": vision_doc.summary_heavy is not None}
                        )

                        # Select appropriate content based on depth configuration
                        if vision_depth == "full":
                            logger.info("[VISION_DEPTH_DEBUG] Taking FULL path - fetching all chunks")
                            # Fetch all original chunks
                            vision_chunks = await self._get_relevant_vision_chunks(
                                session=session,
                                product=product,
                                project=project,
                                max_tokens=None,  # All chunks
                            )
                            if vision_chunks:
                                vision_content = "\n\n".join([chunk["content"] for chunk in vision_chunks])
                                estimated_original_tokens = sum(chunk.get("tokens", 0) for chunk in vision_chunks)
                        elif vision_doc.is_summarized:
                            # Use pre-computed semantic summary based on depth
                            logger.info(f"[VISION_DEPTH_DEBUG] Taking SUMMARIZED path - vision_depth='{vision_depth}'")
                            if vision_depth == "light" and vision_doc.summary_light:
                                logger.info("[VISION_DEPTH_DEBUG] Using summary_light")
                                vision_content = vision_doc.summary_light
                                estimated_original_tokens = vision_doc.original_token_count or 0
                            elif vision_depth == "moderate" and vision_doc.summary_moderate:
                                logger.info("[VISION_DEPTH_DEBUG] Using summary_moderate")
                                vision_content = vision_doc.summary_moderate
                                estimated_original_tokens = vision_doc.original_token_count or 0
                            elif vision_depth == "heavy" and vision_doc.summary_heavy:
                                logger.info("[VISION_DEPTH_DEBUG] Using summary_heavy")
                                vision_content = vision_doc.summary_heavy
                                estimated_original_tokens = vision_doc.original_token_count or 0
                            else:
                                logger.info(f"[VISION_DEPTH_DEBUG] Falling back to any available summary (requested '{vision_depth}' not available)")
                                # Fallback to moderate if requested level unavailable
                                vision_content = vision_doc.summary_moderate or vision_doc.summary_heavy or vision_doc.summary_light
                                estimated_original_tokens = vision_doc.original_token_count or 0
                        else:
                            # Not summarized - fallback to chunks with conservative limit
                            logger.info("[VISION_DEPTH_DEBUG] Taking FALLBACK path - not summarized, using chunks with 15K limit")
                            vision_chunks = await self._get_relevant_vision_chunks(
                                session=session,
                                product=product,
                                project=project,
                                max_tokens=15000,  # Conservative fallback
                            )
                            if vision_chunks:
                                vision_content = "\n\n".join([chunk["content"] for chunk in vision_chunks])
                                estimated_original_tokens = vision_doc.total_tokens or 15000

                        if vision_content:
                            # Apply priority framing
                            formatted_vision = self._apply_priority_framing(
                                section_name=self.SECTION_NAMES.get("vision_documents", "Product Vision"),
                                content=vision_content,
                                priority=vision_priority,
                                category_key="vision_documents",
                            )

                            if formatted_vision:
                                context_sections.append(formatted_vision)
                            vision_tokens = self._count_tokens(formatted_vision)
                            total_tokens += vision_tokens
                            tokens_before_reduction += estimated_original_tokens

                            logger.info(
                                f"Product vision ({vision_depth} depth): {vision_tokens} tokens "
                                f"(compressed from ~{estimated_original_tokens:,} tokens)",
                                extra={
                                    "field": "vision_documents",
                                    "priority": vision_priority,
                                    "depth": vision_depth,
                                    "tokens": vision_tokens,
                                    "original_tokens": estimated_original_tokens,
                                    "tokens_saved": estimated_original_tokens - vision_tokens,
                                    "is_summarized": vision_doc.is_summarized,
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

        # === Config Data Fields Section (Handover 0303) ===
        # Generic extraction for all config_data fields that are prioritized
        # Replaces hardcoded architecture extraction with scalable pattern
        config_fields_to_extract = [
            "architecture",  # System architecture
            "test_methodology",  # Testing approach (TDD, BDD, etc.)
            "coding_standards",  # Code quality standards
            "deployment_strategy",  # Deployment approach
            "agent_execution_methodologies",  # How agents should execute work
        ]

        for field_name in config_fields_to_extract:
            # Check both old key format (backward compat) and new config_data.* format
            field_key = f"config_data.{field_name}"
            legacy_key = field_name if field_name == "architecture" else None

            # Try new format first, then fall back to legacy
            field_priority = effective_priorities.get(field_key, 0)
            if field_priority == 0 and legacy_key:
                field_priority = effective_priorities.get(legacy_key, 0)

            if self._should_include_field(field_priority):
                field_detail = self._get_detail_level(field_priority)
                field_text = self._extract_config_field(product, field_name, field_detail)

                if field_text:
                    # Get human-readable label
                    field_label = self.FIELD_LABELS.get(field_key, field_name.replace("_", " ").title())

                    # Apply priority framing
                    formatted_section = self._apply_priority_framing(
                        section_name=field_label, content=field_text, priority=field_priority, category_key=field_key
                    )

                    # Add to context sections (if not excluded)
                    if formatted_section:
                        context_sections.append(formatted_section)

                    field_tokens = self._count_tokens(formatted_section)
                    total_tokens += field_tokens

                    # Track token metrics (use full text for "before" comparison)
                    full_text = self._extract_config_field(product, field_name, "full")
                    if full_text:
                        tokens_before_reduction += self._count_tokens(f"## {field_label}\n{full_text}")

                    logger.debug(
                        f"{field_label}: {field_tokens} tokens (priority={field_priority}, detail={field_detail})",
                        extra={
                            "field": field_key,
                            "priority": field_priority,
                            "detail_level": field_detail,
                            "tokens": field_tokens,
                        },
                    )

        # === Tech Stack Section ===
        # Extract from product.config_data (JSONB field) - Handover 0302
        tech_stack_priority = effective_priorities.get("tech_stack", 0)
        if tech_stack_priority > 0 and product.config_data:
            tech_stack_detail = self._get_detail_level(tech_stack_priority)

            # Extract tech_stack from config_data (may be dict, list, or string)
            tech_stack_raw = product.config_data.get("tech_stack", {})

            # Normalize to dict format for _format_tech_stack
            if isinstance(tech_stack_raw, list):
                # Convert list format ["Python 3.11+", "PostgreSQL"] to dict
                tech_stack_data = {"technologies": tech_stack_raw}
            elif isinstance(tech_stack_raw, str):
                # Convert string format to dict
                tech_stack_data = {"technologies": [tech_stack_raw]}
            elif isinstance(tech_stack_raw, dict):
                # Normalize dict values to ensure they're lists (not strings)
                # This prevents character-by-character iteration in _format_tech_stack
                tech_stack_data = {}
                for key, value in tech_stack_raw.items():
                    if isinstance(value, list):
                        tech_stack_data[key] = value
                    elif isinstance(value, str):
                        # Don't split strings - keep as single item list
                        tech_stack_data[key] = [value] if value else []
                    elif value is not None:
                        # Convert other types to single-item list
                        tech_stack_data[key] = [str(value)]
                    else:
                        tech_stack_data[key] = []
            else:
                tech_stack_data = {}

            if tech_stack_data and isinstance(tech_stack_data, dict):
                # Format using specialized formatter
                formatted_tech_stack = self._format_tech_stack(tech_stack_data, tech_stack_detail)

                if formatted_tech_stack:
                    # Apply priority framing
                    formatted_section = self._apply_priority_framing(
                        section_name=self.SECTION_NAMES.get("tech_stack", "Tech Stack"),
                        content=formatted_tech_stack,
                        priority=tech_stack_priority,
                        category_key="tech_stack",
                    )

                    # Add to context sections (if not excluded)
                    if formatted_section:
                        context_sections.append(formatted_section)
                    tech_stack_tokens = self._count_tokens(formatted_section)
                    total_tokens += tech_stack_tokens

                    # Calculate original tokens for reduction metrics
                    original_tech_stack = self._format_tech_stack(tech_stack_data, "full")
                    tokens_before_reduction += self._count_tokens(f"## Tech Stack\n{original_tech_stack}")

                    logger.debug(
                        f"Tech stack: {tech_stack_tokens} tokens (priority={tech_stack_priority}, detail={tech_stack_detail})",
                        extra={
                            "field": "tech_stack",
                            "priority": tech_stack_priority,
                            "detail_level": tech_stack_detail,
                            "tokens": tech_stack_tokens,
                        },
                    )

        # === Testing Configuration Section (Handover 0271) ===
        # Provides testing standards, quality expectations, and TDD guidance
        # Handover 0282: Fixed key from "testing_config" to "testing" (v2.0 field name)
        testing_priority = effective_priorities.get("testing", 4)  # Default: EXCLUDED (user opt-in)
        if testing_priority > 0:
            testing_context = await self._extract_testing_config(product, testing_priority)

            if testing_context:
                # Apply priority framing
                framed_testing = self._apply_priority_framing(
                    section_name=self.SECTION_NAMES.get("testing", "Testing Configuration"),
                    content=testing_context,
                    priority=testing_priority,
                    category_key="testing",  # Handover 0282: v2.0 field name
                )

                if framed_testing:  # Only add if not excluded
                    context_sections.append(framed_testing)
                testing_tokens = self._count_tokens(framed_testing if framed_testing else testing_context)
                total_tokens += testing_tokens

                # Calculate original tokens for reduction metrics
                full_testing_context = await self._extract_testing_config(product, priority=1)
                tokens_before_reduction += self._count_tokens(full_testing_context)

                logger.debug(
                    f"Testing configuration: {testing_tokens} tokens (priority={testing_priority})",
                    extra={
                        "field": "testing",  # Handover 0282: v2.0 field name
                        "priority": testing_priority,
                        "tokens": testing_tokens,
                        "product_id": str(product.id),
                    },
                )

        # === MANDATORY: Serena Codebase Context (if enabled) ===
        # Serena integration is controlled by user toggle in My Settings → Integrations
        # When enabled, provides intelligent codebase symbols/structure overview
        if include_serena:
            serena_context = await self._fetch_serena_codebase_context(
                project_id=str(project.id), tenant_key=product.tenant_key
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

        # === CONTEXT SOURCE 9: 360 Memory + Git Integration ===
        # 360 Memory provides historical context from previous projects (Handovers 0135-0139)
        # Git integration adds CLI command instructions for commit history (Handover 013B)
        # Both are controlled by field priorities and user toggles
        # Handover 0283: Apply depth configuration to control detail level

        # 360 Memory extraction (priority-based with depth control)
        # Handover 0282: Fixed key from "product_memory.sequential_history" to "memory_360" (v2.0 field name)
        history_priority = effective_priorities.get("memory_360", 4)  # Default: EXCLUDED (user opt-in)
        if history_priority > 0:
            # Handover 0283: Apply depth configuration (number of projects to show)
            memory_depth = depth_config.get("memory_360", 5)  # Default: 5 projects

            history_context = await self._extract_product_history(product, history_priority, max_entries=memory_depth)
            if history_context:
                # Apply priority framing
                framed_history = self._apply_priority_framing(
                    section_name=self.SECTION_NAMES.get("memory_360", "360 Memory"),
                    content=history_context,
                    priority=history_priority,
                    category_key="memory_360",
                )

                if framed_history:  # Only add if not excluded
                    context_sections.append(framed_history)
                history_tokens = self._count_tokens(framed_history if framed_history else history_context)
                total_tokens += history_tokens

                logger.debug(
                    f"Added 360 Memory context: {history_tokens} tokens (priority={history_priority}, depth={memory_depth} projects)",
                    extra={
                        "field": "memory_360",  # Handover 0282: v2.0 field name
                        "priority": history_priority,
                        "depth": memory_depth,
                        "tokens": history_tokens,
                        "product_id": str(product.id),
                    },
                )

        # Git integration (toggle-based, not priority-driven)
        # Handover 0283: Apply depth configuration to git commit limit
        git_config = product.product_memory.get("git_integration", {}) if product.product_memory else {}
        if git_config.get("enabled"):
            # Handover 0283: Override commit_limit with depth configuration
            git_depth = depth_config.get("git_history", 20)  # Default: 20 commits
            git_config_with_depth = git_config.copy()
            git_config_with_depth["commit_limit"] = git_depth

            git_instructions = self._inject_git_instructions(git_config_with_depth)
            context_sections.append(git_instructions)
            git_tokens = self._count_tokens(git_instructions)
            total_tokens += git_tokens

            logger.debug(
                f"Added Git instructions: {git_tokens} tokens (depth={git_depth} commits)",
                extra={
                    "field": "git_integration",
                    "priority": "TOGGLE",
                    "depth": git_depth,
                    "tokens": git_tokens,
                    "product_id": str(product.id),
                },
            )

        # === Token Reduction Metrics ===
        # Calculate and log context prioritization percentage for analytics
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
                "depth_config": depth_config,
                "user_id": user_id,
                "sections_included": len(context_sections),
                "serena_enabled": include_serena,
                "operation": "build_context_with_priorities",
            },
        )

        # Join all sections with double newlines for readability
        return "\n\n".join(context_sections)

    async def _extract_product_history(self, product: Product, priority: int, max_entries: int = 10) -> str:
        """
        Extract project history from product_memory.sequential_history with priority-based detail levels.

        Includes comprehensive instructions for orchestrators on:
        - How to read and interpret 360 Memory history
        - How to update memory at project completion
        - MCP tool usage examples
        - Git integration status

        Priority-based detail levels (controls content detail per entry):
        - 10 (full): Summary + outcomes + decisions + instructions
        - 7-9 (moderate): Summary + outcomes + detailed instructions
        - 4-6 (abbreviated): Summary only + abbreviated instructions
        - 1-3 (minimal): Summary only + minimal instructions
        - 0 (exclude): Return empty string

        Args:
            product: Product model with product_memory JSONB field containing sequential_history array
            priority: Field priority (0-10 scale) controlling detail level of EACH entry
            max_entries: Number of history entries to include (controlled by depth config, Handover 0283)

        Returns:
            Formatted markdown string with historical context + memory instructions, or empty string if excluded

        Multi-Tenant Isolation:
            Product is already tenant-filtered by upstream code. No additional filtering needed.
        """
        from src.giljo_mcp.prompt_generation.memory_instructions import MemoryInstructionGenerator

        # Priority 0: Exclude entirely
        if priority == 0:
            return ""

        # Check if product has history
        if not product.product_memory:
            return ""

        history = product.product_memory.get("sequential_history", [])

        # Filter out None/invalid entries (defensive against malformed data)
        valid_history = [h for h in history if h is not None and isinstance(h, dict)]

        # Check git integration status
        git_integration = product.product_memory.get("git_integration", {})
        git_enabled = git_integration.get("enabled", False)

        # If no valid history, just return instructions for first project
        if not valid_history:
            instructions_gen = MemoryInstructionGenerator()
            return instructions_gen.generate_context(sequential_history=[], priority=priority, git_enabled=git_enabled)

        # Sort by sequence descending (most recent first)
        sorted_history = sorted(valid_history, key=lambda x: x.get("sequence", 0), reverse=True)

        # Determine detail level based on priority (controls content detail, not count)
        detail_level = self._get_detail_level(priority)

        # Handover 0283: Use max_entries to determine count (controlled by depth config)
        # Priority controls the detail level of EACH entry, not the number of entries
        entries_to_show = sorted_history[:max_entries]

        # Build formatted context - historical entries first
        sections = ["## Historical Context (360 Memory)\n"]
        sections.append(
            f"Product has {len(valid_history)} previous project(s) in history. "
            f"Showing {len(entries_to_show)} most recent:\n"
        )

        # Format each history entry
        for entry in entries_to_show:
            seq = entry.get("sequence", "?")
            project_name = entry.get("project_name", "Unknown Project")
            timestamp = entry.get("timestamp", "")[:10]  # YYYY-MM-DD only
            summary = entry.get("summary", "")

            # Add learning header and summary
            sections.append(f"### Learning #{seq} - {project_name} ({timestamp})")
            sections.append(f"{summary}\n")

            # Add outcomes for moderate and full detail levels
            if detail_level in ["moderate", "full"]:
                outcomes = entry.get("key_outcomes", [])
                if outcomes:
                    sections.append("**Key Outcomes:**")
                    for outcome in outcomes:
                        sections.append(f"- {outcome}")
                    sections.append("")

            # Add decisions for full detail level only
            if detail_level == "full":
                decisions = entry.get("decisions_made", [])
                if decisions:
                    sections.append("**Decisions Made:**")
                    for decision in decisions:
                        sections.append(f"- {decision}")
                    sections.append("")

        # Add memory instructions from MemoryInstructionGenerator
        instructions_gen = MemoryInstructionGenerator()
        memory_instructions = instructions_gen.generate_context(
            sequential_history=valid_history, priority=priority, git_enabled=git_enabled
        )

        # Combine history entries with instructions
        if memory_instructions:
            sections.append("\n" + memory_instructions)

        result = "\n".join(sections)

        logger.debug(
            f"Extracted 360 Memory history: {len(entries_to_show)} entries + instructions, "
            f"{self._count_tokens(result)} tokens (detail={detail_level})",
            extra={
                "product_id": str(product.id),
                "priority": priority,
                "detail_level": detail_level,
                "entries_shown": len(entries_to_show),
                "total_entries": len(valid_history),
                "tokens": self._count_tokens(result),
            },
        )

        return result

    def _inject_git_instructions(self, git_config: dict) -> str:
        """
        Inject git command instructions when Git integration is enabled.

        This method adds INSTRUCTIONS for CLI agents to run git commands using the user's
        local credentials. It does NOT fetch commits (that happens in CLI execution).

        Related Handover: 013B (Git integration refactor - simplified toggle model)

        Args:
            git_config: Git integration config from product_memory.git_integration
                       Expected keys: enabled (bool), commit_limit (int), default_branch (str)

        Returns:
            Formatted markdown string with git command examples and guidance (~250 tokens)

        Token Budget:
            Fixed ~250 tokens (minimal variation based on config values)

        Example:
            git_config = {
                "enabled": True,
                "commit_limit": 20,
                "default_branch": "main"
            }
            git_instructions = planner._inject_git_instructions(git_config)
        """
        commit_limit = git_config.get("commit_limit", 20)

        instructions = [
            "## Git Integration\n",
            "You have access to git commands for additional historical context. "
            "Use these commands to see recent work:\n",
            "**Recommended Commands:**",
            "```bash",
            "# Recent commit history",
            f"git log --oneline -{commit_limit}",
            "",
            "# Recent changes with author and date",
            'git log --since="1 week ago" --pretty=format:"%h - %s (%an, %ar)"',
            "",
            "# Current branch status",
            "git branch --show-current",
            "git status --short",
            "",
            "# See what changed in recent commits",
            "git show --stat HEAD~5..HEAD",
            "```\n",
            "**Important**: Combine git history with 360 Memory history above for complete context.\n",
        ]

        result = "\n".join(instructions)

        logger.debug(
            f"Injected Git instructions: {self._count_tokens(result)} tokens",
            extra={
                "commit_limit": commit_limit,
                "tokens": self._count_tokens(result),
            },
        )

        return result

    async def _extract_testing_config(self, product: Product, priority: int) -> str:
        """
        Extract and format testing configuration for orchestrator context.

        Uses TestingConfigGenerator to provide priority-based testing guidance.

        Args:
            product: Product model containing testing configuration
            priority: Field priority (1-4) controlling detail level

        Returns:
            Formatted testing context (empty if priority=4 or no config)
        """
        # Get testing config from product.config_data
        config_data = product.config_data or {}
        testing_config = config_data.get("testing_config", {})

        # Generate context using TestingConfigGenerator
        testing_context = TestingConfigGenerator.generate_context(testing_config=testing_config, priority=priority)

        # Log the operation
        logger.debug(
            "Extracted testing configuration",
            extra={
                "product_id": str(product.id),
                "priority": priority,
                "has_config": bool(testing_config),
                "tokens": self._count_tokens(testing_context) if testing_context else 0,
            },
        )

        return testing_context

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
        combined_text = f"{product.primary_vision_text} {project_description}"
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
            from sqlalchemy import select

            with self.db_manager.get_session() as session:
                result = session.execute(select(User).filter_by(id=user_id))
                user = result.scalar_one_or_none()
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
            dependencies=None,  # Will be populated in generate_missions
        )

    def _detect_agent_dependencies(
        self, mission_content: str, agent_role: str, all_agent_roles: list[str]
    ) -> list[str]:
        """
        Detect which agents this agent depends on based on mission content.

        Handover 0118: Dependency detection for automatic coordination code injection.

        Scans mission content for dependency indicators like:
        - "wait for <agent>"
        - "after <agent> completes"
        - "depends on <agent>"
        - "requires <agent> to finish"

        Args:
            mission_content: Mission text to scan
            agent_role: Role of the agent being checked
            all_agent_roles: List of all agent roles in the project

        Returns:
            List of agent roles this agent depends on (empty if no dependencies)

        Example:
            >>> mission = "Wait for implementer and documenter to complete before analyzing"
            >>> deps = planner._detect_agent_dependencies(mission, "analyzer", ["implementer", "documenter", "analyzer"])
            >>> deps
            ['implementer', 'documenter']
        """
        dependencies = []

        # Dependency patterns to search for
        dependency_patterns = [
            r"wait for (\w+)",
            r"after (\w+) completes?",
            r"depends? on (\w+)",
            r"requires? (\w+) to finish",
            r"when (\w+) (?:is|are) done",
            r"once (\w+) finishes?",
        ]

        # Convert mission to lowercase for case-insensitive matching
        mission_lower = mission_content.lower()

        # Check each pattern
        for pattern in dependency_patterns:
            matches = re.findall(pattern, mission_lower, re.IGNORECASE)
            for match in matches:
                # Check if match is an agent role (or close match)
                for role in all_agent_roles:
                    if role.lower() in match.lower() or match.lower() in role.lower():
                        if role != agent_role and role not in dependencies:
                            dependencies.append(role)

        logger.debug(
            f"Detected dependencies for {agent_role}: {dependencies}",
            extra={"agent_role": agent_role, "dependencies": dependencies},
        )

        return dependencies

    def _add_dependency_coordination_code(self, mission_content: str, agent_role: str, dependencies: list[str]) -> str:
        """
        Inject dependency coordination code into agent mission.

        Handover 0118: Auto-generate dependency waiting logic for agents.

        This adds explicit coordination code that:
        1. Checks for COMPLETE messages from dependencies
        2. Waits up to 5 minutes (10 checks × 30 seconds)
        3. Escalates to orchestrator if timeout

        Args:
            mission_content: Original mission text
            agent_role: Type of agent (e.g., "analyzer")
            dependencies: List of agent types this agent depends on

        Returns:
            Enhanced mission with dependency coordination code

        Note:
            Only adds coordination if dependencies list is non-empty.
        """
        if not dependencies:
            return mission_content

        # Generate dependency list as string
        deps_str = ", ".join(dependencies)
        deps_set_str = "{" + ", ".join([f'"{dep}"' for dep in dependencies]) + "}"

        dependency_code = f"""

## CRITICAL: DEPENDENCY COORDINATION (Handover 0118)

**Dependencies:** This mission requires {deps_str} to complete first.

**YOU MUST wait for dependencies before starting work.**

### Coordination Protocol

**BEFORE STARTING WORK**, execute this dependency waiting logic:

```python
# Dependency coordination for {agent_role}
dependencies_met = False
max_checks = 10  # 5 minutes total (30 sec × 10)
check_count = 0
required_deps = {deps_set_str}
completed_deps = set()

while not dependencies_met and check_count < max_checks:
    # Check for messages from orchestrator and other agents
    messages = receive_messages(
        agent_id="<AGENT_ID>",
        tenant_key="<TENANT_KEY>"
    )

    # Look for completion messages
    for msg in messages:
        # Check for COMPLETE messages from dependencies
        if msg.message_type == "COMPLETE" and msg.from_agent in required_deps:
            completed_deps.add(msg.from_agent)
            logger.info(f"Dependency met: {{msg.from_agent}} completed")

        # Check for explicit DEPENDENCY_MET from orchestrator
        elif msg.message_type == "DEPENDENCY_MET" and msg.to_agent == "<AGENT_TYPE>":
            # Orchestrator explicitly notified us all dependencies are met
            dependencies_met = True
            logger.info("Orchestrator confirmed all dependencies met")
            break

    # Check if all dependencies satisfied
    if required_deps.issubset(completed_deps):
        dependencies_met = True
        logger.info(f"All dependencies met: {{completed_deps}}")
        break

    # Still waiting
    if not dependencies_met:
        check_count += 1
        still_waiting = required_deps - completed_deps

        # Send status update to orchestrator
        send_message(
            from_agent="<AGENT_TYPE>",
            to_agent="orchestrator",
            message_type="STATUS",
            content=f"Waiting for dependencies: {{', '.join(still_waiting)}}. Check {{check_count}}/10.",
            tenant_key="<TENANT_KEY>"
        )

        logger.info(f"Waiting for dependencies ({{check_count}}/10): {{still_waiting}}")

        # Wait 30 seconds before checking again
        import time
        time.sleep(30)

# After waiting loop
if not dependencies_met:
    # Timeout - escalate to orchestrator
    logger.error(f"TIMEOUT: Dependencies not met after 5 minutes. Still waiting for: {{required_deps - completed_deps}}")

    send_message(
        from_agent="<AGENT_TYPE>",
        to_agent="orchestrator",
        message_type="BLOCKER",
        content=f"TIMEOUT: Dependencies not met after 5 minutes. Still waiting for: {{', '.join(required_deps - completed_deps)}}. Please advise.",
        tenant_key="<TENANT_KEY>"
    )

    # STOP and wait for orchestrator response
    # Do not proceed with mission until orchestrator provides guidance

else:
    # Dependencies met - acknowledge and proceed
    logger.info("All dependencies satisfied. Beginning work.")

    send_message(
        from_agent="<AGENT_TYPE>",
        to_agent="orchestrator",
        message_type="ACKNOWLEDGMENT",
        content=f"All dependencies met ({{', '.join(completed_deps)}}). Beginning work now.",
        tenant_key="<TENANT_KEY>"
    )
```

### IMPORTANT

- **DO NOT start work** until `dependencies_met == True`
- **DO NOT skip** the dependency checking logic
- **DO wait** for orchestrator response if timeout occurs
- **DO send** status updates every 30 seconds while waiting

Once dependencies are confirmed met, proceed with your mission tasks below.

---
"""

        # Insert dependency code at the beginning of mission (after header/title)
        # Find a good insertion point (after first header if exists)
        lines = mission_content.split("\n")
        insert_index = 0

        # Find first non-header, non-empty line (good insertion point)
        for i, line in enumerate(lines):
            if line.strip() and not line.startswith("#"):
                insert_index = i
                break

        # Insert dependency code
        lines_before = lines[:insert_index]
        lines_after = lines[insert_index:]

        enhanced_mission = "\n".join(lines_before) + dependency_code + "\n".join(lines_after)

        logger.info(
            f"Added dependency coordination code to {agent_role} mission",
            extra={"agent_role": agent_role, "dependencies": dependencies, "added_lines": dependency_code.count("\n")},
        )

        return enhanced_mission

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
        if product.vision_is_chunked:
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
        if not vision_chunks and product.primary_vision_text:
            # Split vision document into rough chunks
            vision_text = product.primary_vision_text
            # Split by double newline (paragraphs) or sections
            chunks = re.split(r"\n\n+|(?=^#{1,3} )", vision_text, flags=re.MULTILINE)
            vision_chunks = [chunk.strip() for chunk in chunks if chunk.strip()]

        # Calculate original token count
        original_tokens = self._count_tokens(product.primary_vision_text)

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

        # Handover 0118: Detect dependencies and inject coordination code
        # Second pass: Now that all missions are generated, detect dependencies
        all_agent_roles = [agent.role for agent in selected_agents]

        for agent_config in selected_agents:
            mission = missions[agent_config.role]

            # Detect dependencies from mission content
            detected_deps = self._detect_agent_dependencies(mission.content, agent_config.role, all_agent_roles)

            if detected_deps:
                # Inject dependency coordination code into mission content
                enhanced_content = self._add_dependency_coordination_code(
                    mission.content, agent_config.role, detected_deps
                )

                # Update mission with enhanced content and dependencies
                missions[agent_config.role] = Mission(
                    agent_role=mission.agent_role,
                    content=enhanced_content,
                    token_count=self._count_tokens(enhanced_content),
                    context_chunk_ids=mission.context_chunk_ids,
                    priority=mission.priority,
                    scope_boundary=mission.scope_boundary,
                    success_criteria=mission.success_criteria,
                    dependencies=detected_deps,
                )

                logger.info(
                    f"Enhanced {agent_config.role} mission with dependency coordination",
                    extra={
                        "agent_role": agent_config.role,
                        "dependencies": detected_deps,
                        "token_count": missions[agent_config.role].token_count,
                    },
                )

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
            f"Context prioritization: {reduction_percent:.1f}% "
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
        Store context prioritization metrics in project metadata.

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
