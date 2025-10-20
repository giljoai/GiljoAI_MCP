"""
Mission Planner for GiljoAI Agent Orchestration MCP Server.

Generates condensed agent missions from product vision analysis.
Achieves 70% token reduction through intelligent context filtering and summarization.

Phase 1 Implementation: Template-based analysis (no LLM calls)
"""

import logging
import re
from typing import Dict, List

import tiktoken

from .database import DatabaseManager
from .models import Product, Project
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

    def _extract_keywords(self, text: str) -> List[str]:
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

    def _categorize_work(self, keywords: List[str], features: List[str]) -> Dict[str, str]:
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

    def _assess_complexity(
        self, description_length: int, feature_count: int, tech_stack_size: int
    ) -> str:
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
        elif complexity_score >= 2:
            return "moderate"
        else:
            return "simple"

    def _estimate_agent_count(self, work_types: Dict[str, str], complexity: str) -> int:
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
        elif complexity == "moderate":
            return min(base_count + 1, 6)
        else:
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

    def _filter_vision_for_role(
        self, vision_chunks: List[str], agent_role: str
    ) -> List[str]:
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

    def _get_success_criteria(
        self, agent_role: str, analysis: RequirementAnalysis
    ) -> str:
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
            "tester": f"- Test coverage meets or exceeds project standards\n- All tests pass consistently\n- Edge cases and error conditions are tested\n",
            "frontend-implementer": "- UI is responsive across all target devices\n- Components are reusable and well-documented\n- Accessibility standards are met\n",
            "code-reviewer": "- All code reviewed for quality and standards\n- Feedback provided constructively\n- No critical issues remain unresolved\n",
            "documenter": "- Documentation is clear and comprehensive\n- All public APIs are documented\n- Examples and tutorials are included\n",
        }

        criteria = base_criteria
        if agent_role in role_criteria:
            criteria += role_criteria[agent_role]

        return criteria

    async def analyze_requirements(
        self, product: Product, project_description: str
    ) -> RequirementAnalysis:
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
        complexity = self._assess_complexity(
            description_length, len(features), len(tech_stack)
        )

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

    async def _generate_agent_mission(
        self,
        agent_config: AgentConfig,
        analysis: RequirementAnalysis,
        product: Product,
        project: Project,
        vision_chunks: List[str],
    ) -> Mission:
        """
        Generate a condensed mission for a specific agent.

        Args:
            agent_config: Agent configuration
            analysis: Requirement analysis
            product: Product with vision
            project: Project being worked on
            vision_chunks: Filtered vision document chunks

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

        # Add tech stack
        if analysis.tech_stack:
            mission_content += f"\n## Technology Stack\n"
            for tech in analysis.tech_stack:
                mission_content += f"- {tech}\n"

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

        # Count tokens
        token_count = self._count_tokens(mission_content)

        # Extract chunk IDs if available
        context_chunk_ids = []
        if hasattr(product, "context_chunks"):
            context_chunk_ids = [
                chunk.chunk_id for chunk in product.context_chunks[:3]
            ]

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
        selected_agents: List[AgentConfig],
    ) -> Dict[str, Mission]:
        """
        Generate condensed missions for all selected agents.

        Args:
            analysis: Requirement analysis results
            product: Product with vision document
            project: Project being worked on
            selected_agents: List of agent configurations

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
            chunks = re.split(r'\n\n+|(?=^#{1,3} )', vision_text, flags=re.MULTILINE)
            vision_chunks = [chunk.strip() for chunk in chunks if chunk.strip()]

        # Calculate original token count
        original_tokens = self._count_tokens(product.vision_document or "")

        # Generate mission for each agent
        for agent_config in selected_agents:
            mission = await self._generate_agent_mission(
                agent_config, analysis, product, project, vision_chunks
            )
            missions[agent_config.role] = mission

        # Calculate total mission tokens
        total_mission_tokens = sum(mission.token_count for mission in missions.values())

        # Calculate reduction percentage
        # We compare original tokens to average per-agent mission tokens
        if original_tokens > 0 and missions:
            avg_mission_tokens = total_mission_tokens / len(missions)
            reduction_percent = (
                (original_tokens - avg_mission_tokens) / original_tokens
            ) * 100
        else:
            reduction_percent = 0.0

        # Store token metrics
        await self._store_token_metrics(
            project.id, original_tokens, total_mission_tokens, reduction_percent
        )

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
