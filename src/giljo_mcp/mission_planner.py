"""
Mission Planner for GiljoAI Agent Orchestration MCP Server.

Generates condensed agent missions from product vision analysis.
Achieves context prioritization and orchestration through intelligent context filtering and summarization.

Phase 1 Implementation: Template-based analysis (no LLM calls)

Product Vision: Uses Product.vision_documents relationship (Handover 0128e).
Access via: product.primary_vision_text, product.primary_vision_path, product.vision_is_chunked
See: src/giljo_mcp/models/products.py for helper properties
"""

import logging
import re
from typing import Any, ClassVar, Optional

import tiktoken
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from .config.defaults import DEFAULT_FIELD_PRIORITY
from .database import DatabaseManager
from .json_context_builder import JSONContextBuilder
from .models import Product, Project, User
from .models.context import MCPContextIndex
from .orchestration_types import AgentConfig, Mission, RequirementAnalysis
from .prompt_generation.testing_config_generator import TestingConfigGenerator
from .repositories.context_repository import ContextRepository


logger = logging.getLogger(__name__)


# Default field priorities for context building (Handover 0302, 0303, 0266, 0357)
# Applied when user has no custom field_priority_config
# Imported from unified config.defaults module - normalized to integer format
# v2.0 format: Priority values 1-4 (1=CRITICAL, 2=IMPORTANT, 3=NICE_TO_HAVE, 4=EXCLUDED)
def _normalize_field_priorities(field_priorities: dict[str, Any]) -> dict[str, int]:
    """
    Normalize field_priorities from nested format to integer format.

    Handover 0357: DEFAULT_FIELD_PRIORITIES uses {"field": {"toggle": True, "priority": X}} format
    but mission_planner expects {"field": X} (just integers).

    Args:
        field_priorities: Dict with either nested or integer priority values

    Returns:
        Dict with integer priority values (1-4)
    """
    normalized = {}
    for field_key, value in field_priorities.items():
        if isinstance(value, dict) and "priority" in value:
            # Extract priority from nested format, respecting toggle
            if value.get("toggle", True):
                normalized[field_key] = value["priority"]
            else:
                normalized[field_key] = 4  # EXCLUDED if toggle is off
        elif isinstance(value, int):
            # Already in integer format
            normalized[field_key] = value
        else:
            # Unknown format, default to IMPORTANT
            normalized[field_key] = 2
    return normalized


# Import and normalize unified defaults
DEFAULT_FIELD_PRIORITIES = _normalize_field_priorities(DEFAULT_FIELD_PRIORITY.get("priorities", {}))


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
        except (KeyError, ValueError, OSError) as e:
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
            except (ValueError, TypeError, AttributeError) as e:
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
        await self.analyze_requirements(product, project_description)

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
        except SQLAlchemyError as e:
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
            if priority == 2:
                return "moderate"  # IMPORTANT - include if budget allows
            if priority == 3:
                return "abbreviated"  # NICE_TO_HAVE - include if space remains
            if priority == 4:
                return "exclude"  # EXCLUDED - never include
            return "exclude"  # Priority 0 or negative = exclude

        # v1.0 legacy support (0-10 scale)
        # Keep for backward compatibility during transition period
        if priority >= 10:
            return "full"  # 0% context prioritization
        if priority >= 7:
            return "moderate"  # 25% context prioritization
        if priority >= 4:
            return "abbreviated"  # 50% context prioritization
        if priority >= 1:
            return "minimal"  # 80% context prioritization
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
        stmt = select(
            func.count(MCPContextIndex.id).label("chunk_count"),
            func.sum(MCPContextIndex.token_count).label("total_tokens"),
        ).where(
            MCPContextIndex.tenant_key == product.tenant_key,
            MCPContextIndex.product_id == product.id,
        )
        result = await session.execute(stmt)
        row = result.one()

        if row.chunk_count == 0:
            return None

        total_tokens = row.total_tokens or 0

        return {
            "total_chunks": row.chunk_count,
            "total_tokens": total_tokens,
            "fetch_instruction": f"You have {row.chunk_count} vision chunks (~{total_tokens:,} tokens). Use fetch_vision_document(chunk=N) to read them.",
        }

    async def _get_relevant_vision_chunks(self, session, product, project, max_tokens: int | None = None) -> list[dict]:
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
    SECTION_NAMES: ClassVar[dict[str, str]] = {
        "product_core": "Product Context",
        "vision_documents": "Product Vision",
        "project_description": "Project Description",
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
        if priority == 2:
            return f"""## **IMPORTANT: {section_name}** (Priority 2)
**High priority context**

{content}
"""

        # Priority 3 = REFERENCE
        if priority == 3:
            return f"""## {section_name} (Priority 3 - REFERENCE)
**Supplemental information**

{content}
"""

        # Fallback: no framing (shouldn't happen with valid priorities)
        return content

    async def _get_active_vision_doc(self, product: Product):
        """
        Get active vision document for product (Handover 0347b).

        Args:
            product: Product model with vision_documents relationship

        Returns:
            VisionDocument: Active vision document or None
        """
        async with self.db_manager.get_session_async() as session:
            from sqlalchemy import select

            from src.giljo_mcp.models.products import VisionDocument

            # Get active vision document
            # Order by display_order first, then created_at DESC (consistent with existing logic)
            stmt = (
                select(VisionDocument)
                .where(
                    VisionDocument.product_id == product.id,
                    VisionDocument.tenant_key == product.tenant_key,
                    VisionDocument.is_active,
                )
                .order_by(VisionDocument.display_order, VisionDocument.created_at.desc())
                .limit(1)
            )

            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def _get_memory_summary(self, session, product_id: str, tenant_key: str, max_entries: int = 3) -> dict:
        """
        Get brief summary of 360 memory for reference tier (Handover 0347b).

        Updated in Handover 0390b: Reads from product_memory_entries table.

        Args:
            session: AsyncSession for database access
            product_id: Product UUID
            tenant_key: Tenant identifier
            max_entries: Maximum number of project entries to include

        Returns:
            dict: Summary with project count and fetch tool pointer
        """
        from src.giljo_mcp.repositories.product_memory_repository import ProductMemoryRepository

        repo = ProductMemoryRepository()

        # Get recent projects for brief summary
        recent_projects = await repo.get_entries_for_context(
            session=session,
            product_id=product_id,
            tenant_key=tenant_key,
            limit=max_entries,
        )

        total_projects = len(recent_projects)

        if total_projects == 0:
            return {"total_projects": 0, "summary": "No project history available", "fetch_tool": None}

        return {
            "total_projects": total_projects,
            "recent_count": len(recent_projects),
            "recent_summaries": [
                {
                    "sequence": p.get("sequence"),
                    "project_name": p.get("project_name", "Unnamed Project"),
                    "timestamp": p.get("timestamp"),
                }
                for p in recent_projects
            ],
        }

    def _generate_mandatory_read_instruction(self, product: Product, vision_doc) -> str:
        """
        Generate mandatory read instruction for FULL vision depth mode (Handover 0347e).

        Creates strong compliance language instructing orchestrator to fetch
        ALL vision chunks before proceeding. This is NOT optional.

        Args:
            product: Product model
            vision_doc: VisionDocument model with chunk metadata

        Returns:
            str: Mandatory instruction with strong prohibition language

        Example Output:
            "## Vision Document - REQUIRED READING

            **User has configured FULL context depth for this product.**

            BEFORE creating your mission plan, you MUST:
            1. Fetch ALL vision document chunks using pagination
            2. Read and internalize the complete product vision
            3. Reference specific vision elements in your mission plan

            This is NOT optional. The user explicitly requested full context depth.
            Skipping this step violates the user's configuration intent."
        """
        chunk_count = vision_doc.chunk_count or 0

        instruction = f"""## Vision Document - REQUIRED READING

**User has configured FULL context depth for {product.name}.**

BEFORE creating your mission plan, you MUST:
1. Fetch ALL {chunk_count} vision document chunks using pagination
2. Read and internalize the complete product vision
3. Reference specific vision elements in your mission plan

This is NOT optional. The user explicitly requested full context depth.
Skipping this step violates the user's configuration intent.

### Why Full Context Matters
The user has chosen FULL depth to ensure you have complete understanding
of the product vision, architecture decisions, and strategic direction.
Partial reading defeats the purpose of this configuration."""

        return instruction

    def _generate_fetch_commands(self, product_id: str, chunk_count: int) -> list[str]:
        """
        Generate list of fetch commands for vision chunks (Handover 0347e).

        Creates executable fetch commands for each chunk using MCP tool syntax.

        Args:
            product_id: Product UUID as string
            chunk_count: Total number of chunks to fetch

        Returns:
            list[str]: List of fetch command strings

        Example:
            >>> _generate_fetch_commands("abc-123", 3)
            [
                'fetch_vision_document(product_id="abc-123", offset=0, limit=1)  # Chunk 1',
                'fetch_vision_document(product_id="abc-123", offset=1, limit=1)  # Chunk 2',
                'fetch_vision_document(product_id="abc-123", offset=2, limit=1)  # Chunk 3'
            ]
        """
        commands = []
        for i in range(chunk_count):
            cmd = f'fetch_vision_document(product_id="{product_id}", offset={i}, limit=1)  # Chunk {i + 1}'
            commands.append(cmd)
        return commands

    def _summarize_vision_content(self, vision_content: str, ratio: float) -> str:
        """
        Summarize vision content to specified ratio (Handover 0347e).

        MVP Implementation: Simple truncation to achieve target ratio.
        Future: Use extractive summarization (LSA, TextRank) or LLM condensation.

        Args:
            vision_content: Full vision document text
            ratio: Target ratio (0.33 for light, 0.66 for medium)

        Returns:
            str: Truncated content at specified ratio

        Example:
            >>> content = "A" * 10000
            >>> summary = _summarize_vision_content(content, 0.33)
            >>> len(summary)
            3300
        """
        if not vision_content:
            return ""

        # MVP: Simple truncation
        target_length = int(len(vision_content) * ratio)
        return vision_content[:target_length]

    def _create_priority_frame(self, priority: int, field_name: str) -> dict:
        """
        Create priority framing metadata for orchestrator clarity (Handover 0347 fix).

        This ensures the consuming agent understands the priority level and required action
        for each context field, regardless of which tier it's placed in.

        Args:
            priority: Priority level (1=CRITICAL, 2=IMPORTANT, 3=REFERENCE)
            field_name: Name of the field for context

        Returns:
            dict: Priority framing metadata with clear instructions

        Example:
            >>> frame = self._create_priority_frame(1, "vision_documents")
            >>> frame["tier"]
            'critical'
            >>> "MUST" in frame["instruction"]
            True
        """
        PRIORITY_FRAMES = {
            1: {
                "level": 1,
                "tier": "critical",
                "label": "CRITICAL",
                "instruction": f"🔴 CRITICAL: '{field_name}' is essential context. You MUST read and internalize this before creating your mission plan.",
                "action": "MUST_READ_IMMEDIATELY",
                "skip_allowed": False,
            },
            2: {
                "level": 2,
                "tier": "important",
                "label": "IMPORTANT",
                "instruction": f"🟡 IMPORTANT: '{field_name}' contains high-priority context. Read this for informed decision-making.",
                "action": "SHOULD_READ",
                "skip_allowed": False,
            },
            3: {
                "level": 3,
                "tier": "reference",
                "label": "REFERENCE",
                "instruction": f"🟢 REFERENCE: '{field_name}' is available for deeper context. Fetch on-demand when needed.",
                "action": "FETCH_IF_NEEDED",
                "skip_allowed": True,
            },
        }

        return PRIORITY_FRAMES.get(priority, PRIORITY_FRAMES[3])

    def _add_to_tier_by_priority(
        self, builder: "JSONContextBuilder", field_name: str, priority: int, content: dict
    ) -> None:
        """
        Add field to appropriate tier based on priority value (Handover 0347 fix).

        This helper enables fields to be placed in ANY tier (critical/important/reference)
        based on user configuration, fixing the bug where fields were hardcoded to single tiers.

        Args:
            builder: JSONContextBuilder instance
            field_name: Name of the field to add
            priority: Priority level (1=critical, 2=important, 3=reference)
            content: Field content dict (will have priority frame added)

        Example:
            # User sets vision_documents to priority 1 (CRITICAL)
            >>> self._add_to_tier_by_priority(builder, "vision_documents", 1, vision_content)
            # Field is now in critical tier with priority framing
        """
        # Add priority framing to content
        framed_content = {"_priority_frame": self._create_priority_frame(priority, field_name), **content}

        if priority == 1:
            builder.add_critical(field_name)
            builder.add_critical_content(field_name, framed_content)
        elif priority == 2:
            builder.add_important(field_name)
            builder.add_important_content(field_name, framed_content)
        elif priority == 3:
            builder.add_reference(field_name)
            builder.add_reference_content(field_name, framed_content)

    def _get_tier_framing(self, tier: str, base_framing: str) -> str:
        """
        Add tier-specific prefix to framing text (Handover 0350b).

        Args:
            tier: Tier name ('critical', 'important', 'reference')
            base_framing: Base description of the field

        Returns:
            Framing text with appropriate prefix (REQUIRED/RECOMMENDED/OPTIONAL)
        """
        prefixes = {
            "critical": "REQUIRED: ",
            "important": "RECOMMENDED: ",
            "reference": "OPTIONAL: ",
        }
        prefix = prefixes.get(tier, "")

        # Don't duplicate prefix if already present
        if base_framing.startswith(prefix):
            return base_framing
        return prefix + base_framing

    def _build_fetch_instructions(
        self,
        product: "Product",
        project: "Project",
        field_priorities: dict,
        depth_config: dict,
    ) -> dict:
        """
        Build framing instructions for context fetch tools (Handover 0350b).

        Maps user's field priorities to tier-based fetch instructions.
        Each instruction includes: tool name, params, framing text, token estimate.

        This method is the core of the framing-based architecture that replaces
        inline context (~4-8K tokens) with fetch pointers (~500 tokens).

        Args:
            product: Product model with metadata
            project: Project model with metadata
            field_priorities: Dict mapping field names to priority (1-4)
                             1=CRITICAL, 2=IMPORTANT, 3=REFERENCE, 4=EXCLUDED
            depth_config: Dict mapping field names to depth levels
                         Controls HOW MUCH detail to fetch for each field

        Returns:
            {
                "critical": [{"field": "product_core", "tool": "fetch_context", ...}],
                "important": [...],
                "reference": [...]
            }
        """
        instructions = {"critical": [], "important": [], "reference": []}
        tier_map = {1: "critical", 2: "important", 3: "reference"}

        # Tool configuration mapping - defines how each field maps to fetch_context
        tool_configs = {
            "product_core": {
                "tool": "fetch_context",
                "category": "product_core",
                "framing": "Product name, description, and core features. Essential foundation for all work.",
            },
            "vision_documents": {
                "tool": "fetch_context",
                "category": "vision_documents",
                "framing": "Product vision and strategic direction. Use pagination for large documents.",
                "supports_pagination": True,
                "depth_aware": True,
            },
            "tech_stack": {
                "tool": "fetch_context",
                "category": "tech_stack",
                "framing": "Programming languages, frameworks, and databases. Critical for implementation decisions.",
            },
            "architecture": {
                "tool": "fetch_context",
                "category": "architecture",
                "framing": "System architecture patterns, API style, and design principles.",
            },
            "testing": {
                "tool": "fetch_context",
                "category": "testing",
                "framing": "Quality standards, testing strategy, and frameworks.",
            },
            "memory_360": {
                "tool": "fetch_context",
                "category": "memory_360",
                "framing": "Historical project outcomes and cumulative product knowledge.",
                "depth_aware": True,
            },
            "git_history": {
                "tool": "fetch_context",
                "category": "git_history",
                "framing": "Recent git commits aggregated across projects.",
                "depth_aware": True,
            },
            "agent_templates": {
                "tool": "fetch_context",
                "category": "agent_templates",
                "framing": "Available agent templates for spawning specialized agents.",
                "depth_aware": True,
            },
        }

        # Fields that are already inlined in the response (no fetch needed)
        inlined_fields = {"project_description"}

        # Iterate through field priorities and build instructions
        for field, priority in field_priorities.items():
            if priority >= 4:  # Excluded
                continue

            # Skip fields that are already inlined in the response
            if field in inlined_fields:
                continue

            config = tool_configs.get(field)
            if not config:
                logger.warning(f"No fetch tool config for field: {field}")
                continue

            tier = tier_map.get(priority, "reference")

            # Build instruction entry
            instruction = {
                "field": field,
                "tool": config["tool"],
                "params": {
                    "category": config["category"],
                    "product_id": str(product.id),
                    "tenant_key": product.tenant_key,
                },
                "framing": self._get_tier_framing(tier, config["framing"]),
            }

            # Add pagination support flag if applicable
            if config.get("supports_pagination"):
                instruction["supports_pagination"] = True

            # Add depth-specific params if applicable
            if config.get("depth_aware"):
                if field == "vision_documents":
                    # Vision docs use depth for summary level (light/medium/full)
                    # Handover 0352: light=33% summary, medium=66% summary, full=paginated chunks
                    vision_depth = depth_config.get("vision_documents", "light")
                    instruction["params"]["depth"] = vision_depth

                    # Update framing based on depth
                    vision_framing = {
                        "light": "33% summarized vision document (single response).",
                        "medium": "66% summarized vision document (single response).",
                        "full": "Complete vision document (paginated, call until has_more=false).",
                    }
                    base_framing = vision_framing.get(vision_depth, vision_framing["light"])
                    instruction["framing"] = self._get_tier_framing(tier, base_framing)

                    # Only add pagination params for full depth
                    if vision_depth == "full":
                        instruction["params"]["offset"] = 0
                        instruction["supports_pagination"] = True
                    else:
                        # Remove pagination flag for light/medium (single response)
                        instruction.pop("supports_pagination", None)
                elif field == "memory_360":
                    instruction["params"]["limit"] = depth_config.get("memory_360", 5)
                elif field == "git_history":
                    instruction["params"]["limit"] = depth_config.get("git_history", 20)
                elif field == "agent_templates":
                    agent_depth = depth_config.get("agent_templates", "type_only")
                    # Handover 0351: Skip fetch for type_only (already inline in response)
                    # Only include fetch instruction when full templates needed
                    if agent_depth == "type_only":
                        continue  # Already inline - no fetch needed
                    instruction["params"]["depth"] = agent_depth
                    instruction["framing"] = self._get_tier_framing(
                        tier, "Full agent templates with complete prompts for spawning."
                    )

            instructions[tier].append(instruction)

        return instructions
        # Priority 4 (EXCLUDED) - do nothing

    async def _get_full_agent_templates(self, tenant_key: str, session: AsyncSession) -> list[dict]:
        """
        Fetch full agent templates for tenant (Handover 0347d).

        Returns complete agent template data including full content field
        for "full" depth mode. This provides orchestrators with complete
        agent prompts for nuanced task assignment (~2500 tokens/agent).

        Args:
            tenant_key: Tenant isolation key
            session: SQLAlchemy AsyncSession

        Returns:
            List of agent template dicts with all fields:
            [
                {
                    "name": "backend-integration-tester",
                    "role": "Backend Integration Tester",
                    "description": "Specialist in backend integration testing...",
                    "content": "# Backend Integration Tester Agent\n\n...",  # Full prompt
                    "cli_tool": "claude-code",
                    "background_color": "#4CAF50",
                    "category": "testing"
                },
                ...
            ]

        Multi-Tenant Isolation:
            Filters by tenant_key and is_active=True

        Token Impact:
            Full mode: ~2500 tokens per agent (5 agents = ~12,500 tokens)
            Type-only mode should NOT call this function
        """
        from sqlalchemy import and_, select

        from src.giljo_mcp.models import AgentTemplate

        # Query active agent templates for tenant
        stmt = (
            select(AgentTemplate)
            .where(
                and_(
                    AgentTemplate.tenant_key == tenant_key,
                    AgentTemplate.is_active,
                )
            )
            .order_by(AgentTemplate.name)
        )

        result = await session.execute(stmt)
        templates = result.scalars().all()

        # Convert to dict format with all fields
        template_dicts = []
        for template in templates:
            template_dicts.append(
                {
                    "name": template.name,
                    "role": template.role,
                    "description": template.description or "",
                    "content": template.system_instructions or "",  # Full prompt content
                    "cli_tool": template.cli_tool or "claude-code",
                    "background_color": template.background_color or "#808080",
                    "category": template.category or "general",
                }
            )

        logger.debug(
            f"Fetched {len(template_dicts)} full agent templates",
            extra={
                "tenant_key": tenant_key,
                "template_count": len(template_dicts),
                "operation": "_get_full_agent_templates",
            },
        )

        return template_dicts

    async def _build_context_with_priorities(
        self,
        product: Product,
        project: Project,
        field_priorities: dict = None,
        depth_config: dict = None,
        user_id: Optional[str] = None,
        include_serena: bool = False,
    ) -> dict:
        """
        Build JSON context respecting user's field priorities and depth configuration (Handover 0347b).

        This method orchestrates the field priority system and depth controls to generate
        structured JSON context organized by priority tiers (critical/important/reference).

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
            dict: JSON structure with priority-based organization:
                {
                    "priority_map": {
                        "critical": ["product_core", "tech_stack"],
                        "important": ["architecture", "testing"],
                        "reference": ["vision_documents", "memory_360"]
                    },
                    "critical": {
                        "product_core": {...},  # Full inline content
                        "tech_stack": {...}
                    },
                    "important": {
                        "architecture": {...},  # Condensed + fetch pointer
                        "testing": {...}
                    },
                    "reference": {
                        "vision_documents": {...},  # Summary + fetch tool
                        "memory_360": {...}
                    }
                }

        Priority Level Mapping (v2.0):
            Priority 1: CRITICAL - Always included with full detail (in critical tier)
            Priority 2: IMPORTANT - Condensed content + fetch pointers (in important tier)
            Priority 3: NICE_TO_HAVE - Summaries + fetch tools (in reference tier)
            Priority 4: EXCLUDED - Omitted entirely

        Token Target: <2,000 tokens (down from ~21,000 markdown approach)
        """
        # Default to empty dict if not provided
        if field_priorities is None:
            field_priorities = {}
        if depth_config is None:
            depth_config = {
                "memory_360": 5,  # Default: 5 projects
                "git_history": 20,  # Default: 20 commits
                "agent_templates": "full",  # Default: full descriptions
            }

        # Apply default field priorities when user has no config
        if not field_priorities:
            effective_priorities = DEFAULT_FIELD_PRIORITIES.copy()
            logger.debug(
                "No user field priorities configured - applying defaults",
                extra={
                    "default_priorities": DEFAULT_FIELD_PRIORITIES,
                    "operation": "build_context_with_priorities",
                },
            )
        else:
            effective_priorities = field_priorities
            logger.debug(
                "Using user-configured field priorities",
                extra={
                    "user_priorities": field_priorities,
                    "operation": "build_context_with_priorities",
                },
            )

        # Initialize JSONContextBuilder
        builder = JSONContextBuilder()

        # === CRITICAL TIER (Priority 1): Full inline content ===

        # Product Core (name, description, features)
        product_core_priority = effective_priorities.get("product_core", 1)
        if product_core_priority in [1, 2, 3]:  # Process unless EXCLUDED (4)
            product_core_content = {
                "name": product.name,
                "description": product.description or "",
                "tenant_key": product.tenant_key,
            }
            self._add_to_tier_by_priority(builder, "product_core", product_core_priority, product_core_content)

        # Project Description (MANDATORY - always included)
        builder.add_critical("project_description")
        builder.add_critical_content(
            "project_description", {"name": project.name, "description": project.description or ""}
        )

        # Tech Stack
        tech_stack_priority = effective_priorities.get("tech_stack", 2)
        if tech_stack_priority in [1, 2, 3] and product.config_data:  # Process unless EXCLUDED (4)
            tech_stack_raw = product.config_data.get("tech_stack", {})

            # Normalize to dict format
            if isinstance(tech_stack_raw, list):
                tech_stack_data = {"technologies": tech_stack_raw}
            elif isinstance(tech_stack_raw, str):
                tech_stack_data = {"technologies": [tech_stack_raw]}
            elif isinstance(tech_stack_raw, dict):
                tech_stack_data = tech_stack_raw
            else:
                tech_stack_data = {}

            if tech_stack_data:
                self._add_to_tier_by_priority(builder, "tech_stack", tech_stack_priority, tech_stack_data)

        # === IMPORTANT TIER (Priority 2): Condensed content + fetch pointers ===

        # Architecture
        arch_priority = effective_priorities.get("architecture", 2)
        if arch_priority in [1, 2, 3] and product.config_data:  # Process unless EXCLUDED (4)
            arch_text = product.config_data.get("architecture", "")
            if arch_text:
                arch_content = {
                    "summary": arch_text[:500] + "..." if len(arch_text) > 500 else arch_text,
                    "fetch_tool": "fetch_architecture(product_id)",
                    "detail_level": "condensed",
                }
                self._add_to_tier_by_priority(builder, "architecture", arch_priority, arch_content)

        # Testing Configuration
        # Note: Database stores testing data under "test_config" key
        testing_priority = effective_priorities.get("testing", 2)
        if testing_priority in [1, 2, 3] and product.config_data:  # Process unless EXCLUDED (4)
            testing_data = product.config_data.get("test_config", {})
            # Check if any testing fields have content
            has_testing_content = any(
                [
                    testing_data.get("quality_standards"),
                    testing_data.get("strategy"),
                    testing_data.get("frameworks"),
                    testing_data.get("coverage_target"),
                ]
            )
            if testing_data and has_testing_content:
                testing_content = {
                    "quality_standards": testing_data.get("quality_standards", ""),
                    "strategy": testing_data.get("strategy", ""),
                    "frameworks": testing_data.get("frameworks", ""),
                    "coverage_target": testing_data.get("coverage_target", 80),
                    "fetch_tool": "fetch_testing_config(product_id)",
                    "detail_level": "condensed",
                }
                self._add_to_tier_by_priority(builder, "testing", testing_priority, testing_content)

        # Agent Templates (Handover 0347d: 2-level depth system)
        # FIX (0347 production bug): Handle ALL priority tiers (1/2/3), not just priority 2
        agent_templates_priority = effective_priorities.get("agent_templates", 2)
        if agent_templates_priority in [1, 2, 3]:  # Process unless EXCLUDED (4)
            # Get depth configuration (default: type_only for token efficiency)
            agent_depth = depth_config.get("agent_templates", "type_only")

            # Handover 0357: Trace incoming depth_config for debugging
            logger.debug(
                "[AGENT_TEMPLATES] Processing with depth configuration",
                extra={
                    "agent_templates_priority": agent_templates_priority,
                    "agent_depth": agent_depth,
                    "depth_config_input": depth_config,
                    "effective_depth": agent_depth,
                },
            )

            # Fetch templates from database
            async with self.db_manager.get_session_async() as session:
                full_templates = await self._get_full_agent_templates(product.tenant_key, session)

            if agent_depth == "full":
                # Full mode: Complete agent templates with prompts (~2500 tokens/agent)
                agent_content = {
                    "depth": "full",
                    "detail_level": "complete_prompts",
                    "templates": full_templates,
                    "instruction": "All agent templates included with full prompts for nuanced task assignment.",
                    "token_impact": f"~{len(full_templates) * 2500} tokens (full prompts)",
                    "usage_note": "Review agent capabilities before spawning. Match task requirements to agent strengths.",
                }

                logger.info(
                    f"Agent templates: FULL mode (priority {agent_templates_priority}) - {len(full_templates)} complete prompts",
                    extra={
                        "template_count": len(full_templates),
                        "depth": "full",
                        "priority": agent_templates_priority,
                        "estimated_tokens": len(full_templates) * 2500,
                    },
                )
            else:
                # Type-only mode (default): Minimal metadata only (~50 tokens/agent)
                minimal_templates = []
                for template in full_templates:
                    desc = template.get("description", "")
                    truncated_desc = desc[:200] + "..." if len(desc) > 200 else desc

                    minimal_templates.append(
                        {
                            "name": template["name"],
                            "role": template["role"],
                            "description": truncated_desc,
                        }
                    )

                agent_content = {
                    "depth": "type_only",
                    "detail_level": "minimal_metadata",
                    "templates": minimal_templates,
                    "fetch_tool": "get_available_agents(tenant_key, active_only=True)",
                    "instruction": "Agent templates listed with basic metadata. Call get_available_agents() for complete details if needed.",
                    "token_impact": f"~{len(minimal_templates) * 50} tokens (type only)",
                }

                logger.info(
                    f"Agent templates: TYPE_ONLY mode (priority {agent_templates_priority}) - {len(minimal_templates)} minimal entries",
                    extra={
                        "template_count": len(minimal_templates),
                        "depth": "type_only",
                        "priority": agent_templates_priority,
                        "estimated_tokens": len(minimal_templates) * 50,
                    },
                )

            # Add to appropriate tier based on user's priority setting
            self._add_to_tier_by_priority(builder, "agent_templates", agent_templates_priority, agent_content)

        # === REFERENCE TIER (Priority 3): Summaries + fetch tools ===

        # Vision Documents (Handover 0347e: 4-level depth system)
        # FIX (0347 production bug): Handle ALL priority tiers (1/2/3), not just priority 3
        vision_priority = effective_priorities.get("vision_documents", 4)
        if vision_priority in [1, 2, 3]:  # Process unless EXCLUDED (4)
            vision_doc = await self._get_active_vision_doc(product)
            if vision_doc:
                # Get depth configuration (default: light)
                # Handover 0352: 'optional' deprecated, normalized to 'light' in _get_user_config
                vision_depth = depth_config.get("vision_documents", "light")

                # Build vision content based on depth configuration
                # Depth handling is INDEPENDENT of priority tier - user controls both dimensions
                vision_content_data = None

                if vision_depth in ("optional", "none"):
                    # Pointer + fetch commands (~200 tokens) - same structure as "full" but optional
                    # "none" = UI toggle value, "optional" = legacy/backend name
                    # Both mean: "available if agent needs it" - not mandatory
                    fetch_commands = self._generate_fetch_commands(str(product.id), vision_doc.chunk_count or 0)

                    vision_content_data = {
                        "status": "AVAILABLE_IF_NEEDED",
                        "instruction": "Vision document available if you need deeper product context. Fetch on-demand.",
                        "document_name": vision_doc.document_name or "Product Vision",
                        "total_tokens": vision_doc.original_token_count or 0,
                        "chunk_count": vision_doc.chunk_count or 0,
                        "fetch_commands": fetch_commands,
                        "when_to_fetch": [
                            "When you need detailed product vision context",
                            "When project requirements reference vision elements",
                            "When making architecture decisions aligned with vision",
                        ],
                        "note": "Reading is OPTIONAL. Only fetch if task requires vision document details.",
                        "depth": "optional",
                    }

                elif vision_depth == "light":
                    # 33% SUMY-summarized content from DB (~10-12K tokens)
                    # Uses pre-computed summary_light field (LSA algorithm)
                    summary_content = vision_doc.summary_light or ""
                    summary_tokens = vision_doc.summary_light_tokens or self._count_tokens(summary_content)

                    if summary_content:
                        vision_content_data = {
                            "status": "INLINE_SUMMARY",
                            "coverage": "33% of original vision (SUMY LSA)",
                            "inline_content": summary_content,
                            "document_name": vision_doc.document_name or "Product Vision",
                            "original_tokens": vision_doc.original_token_count or 0,
                            "summary_tokens": summary_tokens,
                            "fetch_tool": "fetch_vision_document(product_id, offset, limit)",
                            "note": "This is a 33% SUMY summary. Use fetch_vision_document() for complete content.",
                            "depth": "light",
                        }
                    else:
                        # Fallback if summary not yet generated
                        vision_content_data = {
                            "status": "SUMMARY_NOT_AVAILABLE",
                            "document_name": vision_doc.document_name or "Product Vision",
                            "total_tokens": vision_doc.original_token_count or 0,
                            "chunk_count": vision_doc.chunk_count or 0,
                            "fetch_tool": "fetch_vision_document(product_id, offset, limit)",
                            "note": "Light summary not yet generated. Use fetch_vision_document() to read full content.",
                            "depth": "light",
                        }

                elif vision_depth == "medium":
                    # 66% SUMY-summarized content from DB (~20-24K tokens)
                    # Uses pre-computed summary_medium field (LSA algorithm)
                    summary_content = vision_doc.summary_medium or ""
                    summary_tokens = vision_doc.summary_medium_tokens or self._count_tokens(summary_content)

                    if summary_content:
                        vision_content_data = {
                            "status": "INLINE_SUMMARY",
                            "coverage": "66% of original vision (SUMY LSA)",
                            "inline_content": summary_content,
                            "document_name": vision_doc.document_name or "Product Vision",
                            "original_tokens": vision_doc.original_token_count or 0,
                            "summary_tokens": summary_tokens,
                            "fetch_tool": "fetch_vision_document(product_id, offset, limit)",
                            "note": "This is a 66% SUMY summary. Use fetch_vision_document() for complete content.",
                            "depth": "medium",
                        }
                    else:
                        # Fallback if summary not yet generated
                        vision_content_data = {
                            "status": "SUMMARY_NOT_AVAILABLE",
                            "document_name": vision_doc.document_name or "Product Vision",
                            "total_tokens": vision_doc.original_token_count or 0,
                            "chunk_count": vision_doc.chunk_count or 0,
                            "fetch_tool": "fetch_vision_document(product_id, offset, limit)",
                            "note": "Medium summary not yet generated. Use fetch_vision_document() to read full content.",
                            "depth": "medium",
                        }

                elif vision_depth == "full":
                    # Pointer + MANDATORY read instruction (~200 tokens + fetch cost)
                    # This is the user's explicit request for complete vision document reading
                    mandatory_instruction = self._generate_mandatory_read_instruction(product, vision_doc)
                    fetch_commands = self._generate_fetch_commands(str(product.id), vision_doc.chunk_count or 0)

                    vision_content_data = {
                        "status": "REQUIRED_READING",
                        "mandatory_instruction": mandatory_instruction,
                        "document_name": vision_doc.document_name or "Product Vision",
                        "total_tokens": vision_doc.original_token_count or 0,
                        "chunk_count": vision_doc.chunk_count or 0,
                        "fetch_commands": fetch_commands,
                        "warning": "User explicitly configured FULL depth. You MUST fetch ALL chunks before proceeding.",
                        "reading_sequence": f"Execute fetch commands in order: chunks 0 to {(vision_doc.chunk_count or 1) - 1}",
                        "depth": "full",
                    }

                else:
                    # Unknown depth - fallback to optional
                    logger.warning(
                        f"Unknown vision depth '{vision_depth}', falling back to 'optional'",
                        extra={"vision_depth": vision_depth, "product_id": str(product.id)},
                    )
                    vision_content_data = {
                        "status": "AVAILABLE_ON_REQUEST",
                        "document_name": vision_doc.document_name or "Product Vision",
                        "total_tokens": vision_doc.original_token_count or 0,
                        "chunk_count": vision_doc.chunk_count or 0,
                        "fetch_tool": "fetch_vision_document(product_id, offset, limit)",
                        "depth": "optional",
                    }

                # Add to appropriate tier based on user's priority setting
                if vision_content_data:
                    self._add_to_tier_by_priority(builder, "vision_documents", vision_priority, vision_content_data)

                    logger.info(
                        f"Vision documents: depth={vision_depth}, priority={vision_priority} - added to tier",
                        extra={
                            "vision_depth": vision_depth,
                            "priority": vision_priority,
                            "chunk_count": vision_doc.chunk_count or 0,
                            "total_tokens": vision_doc.original_token_count or 0,
                        },
                    )

        # 360 Memory
        # FIX (0347 production bug): Handle ALL priority tiers (1/2/3), not just priority 3
        memory_priority = effective_priorities.get("memory_360", 4)
        if memory_priority in [1, 2, 3]:  # Process unless EXCLUDED (4)
            memory_depth = depth_config.get("memory_360", 5)
            memory_summary = await self._get_memory_summary(
                session=session, product_id=str(product.id), tenant_key=product.tenant_key, max_entries=memory_depth
            )

            # Add depth information to the summary
            memory_content = {
                **memory_summary,
                "depth_config": memory_depth,
                "fetch_tool": f"fetch_360_memory(product_id, limit={memory_depth})",
            }

            self._add_to_tier_by_priority(builder, "memory_360", memory_priority, memory_content)

        # Git History
        # FIX (0347 production bug): Check priority AND enabled status
        git_priority = effective_priorities.get("git_history", 4)
        git_config = product.product_memory.get("git_integration", {}) if product.product_memory else {}
        if git_priority in [1, 2, 3] and git_config.get("enabled"):  # Process if priority set AND enabled
            git_depth = depth_config.get("git_history", 20)

            git_content = {
                "enabled": True,
                "commit_limit": git_depth,
                "repository": git_config.get("repository", ""),
                "fetch_tool": "fetch_git_history(product_id, limit)",
                "instruction": f"Call fetch_git_history() to get last {git_depth} commits",
            }

            self._add_to_tier_by_priority(builder, "git_history", git_priority, git_content)

        # Serena Codebase Context (MANDATORY if enabled)
        if include_serena:
            serena_context = await self._fetch_serena_codebase_context(
                project_id=str(project.id), tenant_key=product.tenant_key
            )
            if serena_context:
                builder.add_critical("serena_context")
                builder.add_critical_content(
                    "serena_context",
                    {
                        "summary": serena_context[:1000] + "..." if len(serena_context) > 1000 else serena_context,
                        "full_content_chars": len(serena_context),
                    },
                )

        # Build final JSON structure
        result = builder.build()

        # Calculate token estimate
        import json

        json_str = json.dumps(result)
        estimated_tokens = len(json_str) // 4

        logger.info(
            f"JSON context built: {estimated_tokens} tokens",
            extra={
                "product_id": str(product.id),
                "project_id": str(project.id),
                "estimated_tokens": estimated_tokens,
                "priorities": field_priorities,
                "depth_config": depth_config,
                "user_id": user_id,
                "critical_fields": len(result.get("critical", {})),
                "important_fields": len(result.get("important", {})),
                "reference_fields": len(result.get("reference", {})),
                "serena_enabled": include_serena,
                "operation": "build_context_with_priorities_json",
            },
        )

        return result

    async def _extract_product_history(
        self,
        session,
        product_id: str,
        tenant_key: str,
        priority: int,
        max_entries: int = 10,
        product: Optional[Product] = None,
    ) -> str:
        """
        Extract project history from product_memory_entries table with priority-based detail levels.

        Updated in Handover 0390b: Reads from product_memory_entries table instead of JSONB.

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
            session: AsyncSession for database access
            product_id: Product UUID
            tenant_key: Tenant identifier
            priority: Field priority (0-10 scale) controlling detail level of EACH entry
            max_entries: Number of history entries to include (controlled by depth config, Handover 0283)
            product: Optional Product model (for git integration config access)

        Returns:
            Formatted markdown string with historical context + memory instructions, or empty string if excluded

        Multi-Tenant Isolation:
            Repository filters by tenant_key automatically.
        """
        from src.giljo_mcp.prompt_generation.memory_instructions import MemoryInstructionGenerator
        from src.giljo_mcp.repositories.product_memory_repository import ProductMemoryRepository

        # Priority 0: Exclude entirely
        if priority == 0:
            return ""

        # Fetch history from table
        repo = ProductMemoryRepository()
        history = await repo.get_entries_for_context(
            session=session,
            product_id=product_id,
            tenant_key=tenant_key,
            limit=max_entries,
        )

        # Check git integration status (still in JSONB)
        git_enabled = False
        if product and product.product_memory:
            git_integration = product.product_memory.get("git_integration", {})
            git_enabled = git_integration.get("enabled", False)

        # If no history, return instructions for first project
        if not history:
            instructions_gen = MemoryInstructionGenerator()
            return instructions_gen.generate_context(sequential_history=[], priority=priority, git_enabled=git_enabled)

        # Determine detail level based on priority (controls content detail, not count)
        detail_level = self._get_detail_level(priority)

        # Build formatted context - historical entries first
        sections = ["## Historical Context (360 Memory)\n"]
        sections.append(
            f"Product has {len(history)} previous project(s) in history. Showing {len(history)} most recent:\n"
        )

        # Format each history entry
        for entry in history:
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
            sequential_history=history, priority=priority, git_enabled=git_enabled
        )

        # Combine history entries with instructions
        if memory_instructions:
            sections.append("\n" + memory_instructions)

        result = "\n".join(sections)

        logger.debug(
            f"Extracted 360 Memory history: {len(history)} entries + instructions, "
            f"{self._count_tokens(result)} tokens (detail={detail_level})",
            extra={
                "product_id": product_id,
                "priority": priority,
                "detail_level": detail_level,
                "entries_shown": len(history),
                "total_entries": len(history),
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
        except SQLAlchemyError as e:
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
            except SQLAlchemyError as e:
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
        except (OSError, yaml.YAMLError, KeyError, ValueError, TypeError) as e:
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

        except SQLAlchemyError:
            logger.exception("Failed to store token metrics")
