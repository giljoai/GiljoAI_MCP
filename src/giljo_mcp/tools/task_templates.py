"""
Task Template Integration Tools
Integrates with template_manager.py for task-to-project conversion templates
"""

import logging
from typing import Any, Optional

from sqlalchemy import and_, select

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.models import Task
from src.giljo_mcp.template_manager import get_template_manager


logger = logging.getLogger(__name__)


def register_task_template_tools(mcp):
    """Register task template integration tools"""

    @mcp.tool()
    async def get_task_conversion_templates(
        category: Optional[str] = None, priority: Optional[str] = None
    ) -> dict[str, Any]:
        """
        Get available templates for task-to-project conversion

        Args:
            category: Filter by task category (tech_debt, feature, bug_fix, etc.)
            priority: Filter by priority level

        Returns:
            Available conversion templates with descriptions
        """
        try:
            from src.giljo_mcp.tenant import tenant_manager

            tenant_key = tenant_manager.get_current_tenant()
            if not tenant_key:
                return {
                    "success": False,
                    "error": "No active project. Use switch_project first.",
                }

            db_manager = DatabaseManager(is_async=True)
            get_template_manager(db_manager)

            # Common conversion templates organized by category
            conversion_templates = {
                "tech_debt": {
                    "name": "Technical Debt Cleanup",
                    "description": "Convert technical debt tasks into structured cleanup projects",
                    "agents": ["analyzer", "implementer", "tester", "reviewer"],
                    "template_variables": {
                        "debt_type": "Code refactoring, dependency updates, performance optimization",
                        "impact_assessment": "High/Medium/Low impact on system stability",
                        "testing_strategy": "Comprehensive regression testing approach",
                    },
                    "success_criteria": [
                        "Technical debt items documented and prioritized",
                        "Refactoring plan with minimal disruption",
                        "All tests pass after changes",
                        "Code quality metrics improved",
                    ],
                },
                "feature": {
                    "name": "Feature Development",
                    "description": "Convert feature requests into full development projects",
                    "agents": ["analyzer", "implementer", "tester", "documenter"],
                    "template_variables": {
                        "feature_scope": "Detailed feature requirements and boundaries",
                        "user_stories": "User stories and acceptance criteria",
                        "integration_points": "APIs and system integration requirements",
                    },
                    "success_criteria": [
                        "Feature fully implemented and tested",
                        "Documentation updated",
                        "User acceptance criteria met",
                        "Performance requirements satisfied",
                    ],
                },
                "bug_fix": {
                    "name": "Bug Investigation and Fix",
                    "description": "Convert bug reports into systematic investigation projects",
                    "agents": ["analyzer", "implementer", "tester"],
                    "template_variables": {
                        "bug_description": "Detailed bug reproduction steps",
                        "impact_level": "Critical/High/Medium/Low severity assessment",
                        "root_cause_analysis": "Systematic investigation approach",
                    },
                    "success_criteria": [
                        "Root cause identified and documented",
                        "Fix implemented with minimal side effects",
                        "Regression tests added",
                        "Bug verified as resolved",
                    ],
                },
                "research": {
                    "name": "Research and Analysis",
                    "description": "Convert research tasks into structured investigation projects",
                    "agents": ["analyzer", "documenter"],
                    "template_variables": {
                        "research_question": "Specific questions to investigate",
                        "methodology": "Research approach and evaluation criteria",
                        "deliverables": "Expected outcomes and recommendations",
                    },
                    "success_criteria": [
                        "Comprehensive research completed",
                        "Findings documented with recommendations",
                        "Implementation roadmap provided",
                        "Stakeholder review completed",
                    ],
                },
                "optimization": {
                    "name": "Performance Optimization",
                    "description": "Convert performance issues into optimization projects",
                    "agents": ["analyzer", "implementer", "tester"],
                    "template_variables": {
                        "performance_metrics": "Current vs target performance goals",
                        "optimization_areas": "Database, API, frontend, backend focus",
                        "measurement_strategy": "How to validate improvements",
                    },
                    "success_criteria": [
                        "Performance bottlenecks identified",
                        "Optimization implemented with measurable gains",
                        "Performance monitoring established",
                        "Documentation updated with best practices",
                    ],
                },
            }

            # Filter templates if criteria provided
            filtered_templates = {}
            for template_key, template_data in conversion_templates.items():
                if category and template_key != category:
                    continue

                filtered_templates[template_key] = template_data

            return {
                "success": True,
                "templates": filtered_templates,
                "categories": list(conversion_templates.keys()),
                "total_templates": len(filtered_templates),
            }

        except Exception as e:
            logger.exception(f"Failed to get conversion templates: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    async def generate_project_from_task_template(
        task_id: str,
        template_category: str,
        project_name: Optional[str] = None,
        additional_variables: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """
        Generate a complete project configuration from a task using templates

        Args:
            task_id: Source task ID
            template_category: Template category to use
            project_name: Override project name
            additional_variables: Additional template variables

        Returns:
            Complete project configuration ready for creation
        """
        try:
            from src.giljo_mcp.tenant import tenant_manager

            tenant_key = tenant_manager.get_current_tenant()
            if not tenant_key:
                return {
                    "success": False,
                    "error": "No active project. Use switch_project first.",
                }

            db_manager = DatabaseManager(is_async=True)
            template_manager = get_template_manager(db_manager)

            async with db_manager.get_session_async() as session:
                # Get source task
                task_query = select(Task).where(and_(Task.id == task_id, Task.tenant_key == tenant_key))
                task_result = await session.execute(task_query)
                task = task_result.scalar_one_or_none()

                if not task:
                    return {"success": False, "error": f"Task {task_id} not found"}

                # Get template configuration
                templates_result = await get_task_conversion_templates(category=template_category)
                if not templates_result["success"]:
                    return templates_result

                template_config = templates_result["templates"].get(template_category)
                if not template_config:
                    return {
                        "success": False,
                        "error": f"Template category '{template_category}' not found",
                    }

                # Build project configuration
                project_config = {
                    "name": project_name or f"Project: {task.title}",
                    "mission": _generate_project_mission(task, template_config, additional_variables),
                    "agent_sequence": template_config["agents"],
                    "source_task": {
                        "id": str(task.id),
                        "title": task.title,
                        "description": task.description,
                        "category": task.category,
                        "priority": task.priority,
                    },
                    "template_category": template_category,
                    "success_criteria": template_config["success_criteria"],
                    "estimated_agents": len(template_config["agents"]),
                    "template_variables": {
                        **template_config.get("template_variables", {}),
                        **(additional_variables or {}),
                    },
                }

                # Generate agent missions
                agent_missions = {}
                for agent_role in template_config["agents"]:
                    try:
                        mission = await template_manager.get_template(
                            role=agent_role,
                            variables={
                                "project_name": project_config["name"],
                                "project_mission": project_config["mission"],
                                "task_title": task.title,
                                "task_description": task.description or "No description provided",
                                "task_category": task.category or "general",
                                "task_priority": task.priority,
                                **project_config["template_variables"],
                            },
                            project_type=template_category,
                        )
                        agent_missions[agent_role] = mission
                    except Exception as agent_error:
                        logger.warning(f"Failed to generate mission for {agent_role}: {agent_error}")
                        agent_missions[agent_role] = f"Standard {agent_role} mission for {template_category} project"

                project_config["agent_missions"] = agent_missions

                return {
                    "success": True,
                    "project_config": project_config,
                    "ready_for_creation": True,
                    "template_source": template_category,
                }

        except Exception as e:
            logger.exception(f"Failed to generate project from template: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    async def suggest_conversion_template(task_id: str) -> dict[str, Any]:
        """
        Analyze a task and suggest the best conversion template

        Args:
            task_id: Task ID to analyze

        Returns:
            Suggested template with confidence score and reasoning
        """
        try:
            from src.giljo_mcp.tenant import tenant_manager

            tenant_key = tenant_manager.get_current_tenant()
            if not tenant_key:
                return {
                    "success": False,
                    "error": "No active project. Use switch_project first.",
                }

            db_manager = DatabaseManager(is_async=True)
            async with db_manager.get_session_async() as session:
                # Get task details
                task_query = select(Task).where(and_(Task.id == task_id, Task.tenant_key == tenant_key))
                task_result = await session.execute(task_query)
                task = task_result.scalar_one_or_none()

                if not task:
                    return {"success": False, "error": f"Task {task_id} not found"}

                # Analyze task content for template suggestion
                suggestions = _analyze_task_for_template(task)

                return {
                    "success": True,
                    "task_analysis": {
                        "id": str(task.id),
                        "title": task.title,
                        "category": task.category,
                        "priority": task.priority,
                        "description_length": len(task.description or ""),
                    },
                    "suggestions": suggestions,
                    "recommended_template": suggestions[0] if suggestions else None,
                }

        except Exception as e:
            logger.exception(f"Failed to suggest conversion template: {e}")
            return {"success": False, "error": str(e)}


def _generate_project_mission(
    task: Task,
    template_config: dict[str, Any],
    additional_variables: Optional[dict[str, Any]],
) -> str:
    """Generate a comprehensive project mission from task and template"""

    base_mission = f"""
PROJECT GOAL: {task.title}

ORIGIN: Converted from Task ID {task.id}
CATEGORY: {template_config['name']}
PRIORITY: {task.priority.upper()}

DESCRIPTION:
{task.description or 'No detailed description provided - agents should investigate and define scope.'}

TEMPLATE APPROACH:
{template_config['description']}

SUCCESS CRITERIA:
"""

    for i, criterion in enumerate(template_config["success_criteria"], 1):
        base_mission += f"{i}. {criterion}\n"

    if additional_variables:
        base_mission += "\nADDITIONAL CONTEXT:\n"
        for key, value in additional_variables.items():
            base_mission += f"- {key}: {value}\n"

    base_mission += """
ORCHESTRATOR INSTRUCTIONS:
1. Begin with thorough analysis of the original task context
2. Spawn agents according to the template sequence
3. Ensure each agent understands the conversion context
4. Maintain traceability back to the original task
5. Validate success criteria are met before project completion
"""

    return base_mission.strip()


def _analyze_task_for_template(task: Task) -> list[dict[str, Any]]:
    """Analyze task content and suggest appropriate templates"""

    suggestions = []

    # Keywords that suggest different template types
    keyword_mappings = {
        "tech_debt": [
            "refactor",
            "debt",
            "cleanup",
            "optimize",
            "modernize",
            "update dependencies",
            "legacy",
            "deprecated",
            "technical debt",
        ],
        "feature": [
            "feature",
            "new",
            "add",
            "implement",
            "create",
            "develop",
            "enhancement",
            "functionality",
            "capability",
        ],
        "bug_fix": [
            "bug",
            "fix",
            "error",
            "issue",
            "broken",
            "not working",
            "crash",
            "failure",
            "problem",
            "defect",
        ],
        "research": [
            "research",
            "investigate",
            "analyze",
            "study",
            "evaluate",
            "compare",
            "assess",
            "explore",
            "spike",
            "proof of concept",
        ],
        "optimization": [
            "performance",
            "slow",
            "optimization",
            "speed",
            "memory",
            "cpu",
            "database",
            "query",
            "latency",
            "throughput",
        ],
    }

    # Analyze task title and description
    content = f"{task.title} {task.description or ''}".lower()

    for template_type, keywords in keyword_mappings.items():
        matches = sum(1 for keyword in keywords if keyword in content)
        if matches > 0:
            confidence = min(matches * 0.3, 1.0)  # Max confidence of 1.0

            # Boost confidence based on task category match
            if task.category and template_type in task.category.lower():
                confidence = min(confidence + 0.3, 1.0)

            # Boost confidence based on priority for certain types
            if task.priority == "critical" and template_type in [
                "bug_fix",
                "optimization",
            ]:
                confidence = min(confidence + 0.2, 1.0)

            suggestions.append(
                {
                    "template_category": template_type,
                    "confidence": confidence,
                    "matched_keywords": [kw for kw in keywords if kw in content],
                    "reasoning": f"Task content matches {matches} {template_type} keywords",
                }
            )

    # Sort by confidence
    suggestions.sort(key=lambda x: x["confidence"], reverse=True)

    # If no strong matches, suggest based on priority and category
    if not suggestions or suggestions[0]["confidence"] < 0.3:
        fallback_suggestion = {
            "template_category": "feature",
            "confidence": 0.2,
            "matched_keywords": [],
            "reasoning": "Default suggestion - no clear template indicators found",
        }

        if task.priority in ["critical", "high"]:
            fallback_suggestion["template_category"] = "bug_fix"
            fallback_suggestion["reasoning"] = "High priority suggests urgent issue resolution"

        suggestions.append(fallback_suggestion)

    return suggestions[:3]  # Return top 3 suggestions


logger.info("Task template integration tools registered successfully")
