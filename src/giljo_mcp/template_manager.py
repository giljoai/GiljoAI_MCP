"""
Unified Template Manager for GiljoAI MCP
Consolidates template functionality from Projects 3.4 and 3.9.b
Single source of truth for all template operations
"""

import re
import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import AgentTemplate, TemplateAugmentation
from .database import DatabaseManager

logger = logging.getLogger(__name__)


def apply_augmentation(
    content: str, 
    augmentation: Union[TemplateAugmentation, Dict[str, Any]]
) -> str:
    """
    Apply augmentation to template content.
    Handles both database objects and runtime dictionaries.
    
    Args:
        content: Template content to augment
        augmentation: Either a DB TemplateAugmentation or dict with:
            - type/augmentation_type: append, prepend, replace, inject
            - content: Content to apply
            - target/target_section: Optional target for replace/inject
    
    Returns:
        Augmented content
    """
    # Handle empty augmentation
    if not augmentation or (isinstance(augmentation, dict) and not augmentation):
        return content
    
    # Normalize input to dict format
    if isinstance(augmentation, TemplateAugmentation):
        aug_type = augmentation.augmentation_type
        aug_content = augmentation.content
        target = augmentation.target_section
    else:
        aug_type = augmentation.get("type") or augmentation.get("augmentation_type", "append")
        aug_content = augmentation.get("content", "")
        target = augmentation.get("target") or augmentation.get("target_section", "")
    
    # Apply augmentation based on type
    if aug_type == "append":
        return content + "\n\n" + aug_content
    elif aug_type == "prepend":
        return aug_content + "\n\n" + content
    elif aug_type == "replace" and target:
        return content.replace(target, aug_content)
    elif aug_type == "inject" and target:
        index = content.find(target)
        if index != -1:
            end_index = index + len(target)
            return content[:end_index] + "\n" + aug_content + content[end_index:]
    
    return content


def process_template(
    content: str,
    variables: Optional[Dict[str, Any]] = None,
    augmentations: Optional[List[Union[TemplateAugmentation, Dict]]] = None,
    substitute_first: bool = False
) -> str:
    """
    Process a template with variables and augmentations.
    
    Args:
        content: Base template content
        variables: Variables to substitute
        augmentations: List of augmentations to apply
        substitute_first: If True, substitute variables before augmentations
    
    Returns:
        Processed template content
    """
    processed = content
    
    # Apply variable substitution first if requested
    if substitute_first and variables:
        for key, value in variables.items():
            processed = processed.replace(f"{{{key}}}", str(value))
    
    # Apply augmentations
    if augmentations:
        # Sort by priority if available
        sorted_augs = augmentations
        if all(hasattr(a, 'priority') or 'priority' in a for a in augmentations):
            sorted_augs = sorted(
                augmentations,
                key=lambda x: x.priority if hasattr(x, 'priority') else x.get('priority', 0)
            )
        
        for aug in sorted_augs:
            processed = apply_augmentation(processed, aug)
    
    # Apply variable substitution after if not done before
    if not substitute_first and variables:
        for key, value in variables.items():
            processed = processed.replace(f"{{{key}}}", str(value))
    
    return processed


def extract_variables(content: str) -> List[str]:
    """
    Extract variable names from template content.
    
    Args:
        content: Template content with {variable} placeholders
    
    Returns:
        List of unique variable names in order of first appearance
    """
    seen = set()
    result = []
    for var in re.findall(r'\{(\w+)\}', content):
        if var not in seen:
            seen.add(var)
            result.append(var)
    return result


class UnifiedTemplateManager:
    """
    Unified manager for all template operations.
    Handles both database-backed and legacy templates.
    """
    
    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        """
        Initialize the template manager.
        
        Args:
            db_manager: Optional database manager for DB-backed templates
        """
        self.db_manager = db_manager
        self._template_cache = {}
        self._legacy_templates = self._load_legacy_templates()
    
    def _load_legacy_templates(self) -> Dict[str, str]:
        """Load legacy hardcoded templates for fallback"""
        return {
            "orchestrator": """You are the Project Orchestrator for: {project_name}

PROJECT GOAL: {project_mission}
PRODUCT: {product_name}

YOUR DISCOVERY APPROACH (Dynamic Context Loading):
1. Read the vision document using get_vision()
2. Review product settings with get_product_settings()
3. Use Serena MCP to explore the codebase
4. Only load what's relevant to this specific project

YOUR RESPONSIBILITIES:
- Create any agents with ANY job types you deem necessary
- Define precise missions for each agent based on discoveries
- Choose optimal implementation approach
- Design the agent pipeline that best achieves the goal""",
            
            "analyzer": """You are the Analyzer Agent for: {project_name}

PROJECT GOAL: {project_mission}

YOUR MISSION:
Perform deep analysis of the system to understand requirements, identify patterns,
and design optimal solutions that align with project goals.

YOUR APPROACH:
1. Analyze existing code structure and patterns
2. Identify integration points and dependencies
3. Design solutions that follow established patterns
4. Document findings and recommendations""",
            
            "implementer": """You are the Implementation Agent for: {project_name}

PROJECT GOAL: {project_mission}

YOUR MISSION:
Implement the required functionality following design specifications and project standards.

YOUR APPROACH:
1. Follow design specifications exactly
2. Write clean, maintainable code
3. Add appropriate error handling
4. Test your implementation
5. Document complex logic""",
            
            "tester": """You are the Testing Agent for: {project_name}

PROJECT GOAL: {project_mission}

YOUR MISSION:
Ensure quality through comprehensive testing of all functionality.

YOUR APPROACH:
1. Write comprehensive test cases
2. Test all functionality thoroughly
3. Verify edge cases
4. Document test results
5. Report any issues found""",
            
            "reviewer": """You are the Review Agent for: {project_name}

PROJECT GOAL: {project_mission}

YOUR MISSION:
Review code and documentation to ensure quality, standards compliance, and completeness.

YOUR APPROACH:
1. Review code for quality and standards
2. Verify requirements are met
3. Check for security issues
4. Ensure documentation is complete
5. Provide constructive feedback""",
            
            "documenter": """You are the Documentation Agent for: {project_name}

PROJECT GOAL: {project_mission}

YOUR MISSION:
Create comprehensive documentation for all project deliverables.

YOUR APPROACH:
1. Document all implemented features
2. Create usage examples and tutorials
3. Write API documentation
4. Update README and setup guides
5. Document architectural decisions"""
        }
    
    async def get_template(
        self,
        role: str,
        variables: Optional[Dict[str, Any]] = None,
        augmentations: Optional[List[Union[TemplateAugmentation, Dict]]] = None,
        project_type: Optional[str] = None,
        product_id: Optional[str] = None,
        use_cache: bool = True
    ) -> str:
        """
        Get a processed template for the specified role.
        
        Args:
            role: Agent role (orchestrator, analyzer, etc.)
            variables: Variables to substitute
            augmentations: Runtime augmentations to apply
            project_type: Optional project type for specialized templates
            product_id: Optional product ID for product-specific templates
            use_cache: Whether to use cached templates
        
        Returns:
            Processed template content
        """
        try:
            # Try database first if available
            if self.db_manager:
                template_content = await self._get_db_template(
                    role, project_type, product_id, use_cache
                )
            else:
                # Fall back to legacy templates
                template_content = self._legacy_templates.get(
                    role.lower(),
                    f"No template available for role: {role}"
                )
            
            # Process the template
            return process_template(template_content, variables, augmentations)
            
        except Exception as e:
            logger.error(f"Failed to get template for role '{role}': {e}")
            # Return fallback template
            fallback = self._legacy_templates.get(
                role.lower(),
                f"Error loading template for role: {role}"
            )
            return process_template(fallback, variables, augmentations)
    
    async def _get_db_template(
        self,
        role: str,
        project_type: Optional[str],
        product_id: Optional[str],
        use_cache: bool
    ) -> str:
        """Get template from database with caching"""
        cache_key = f"{role}_{project_type}_{product_id}"
        
        if use_cache and cache_key in self._template_cache:
            return self._template_cache[cache_key]
        
        async with self.db_manager.get_session() as session:
            # Build query
            query = select(AgentTemplate).where(
                AgentTemplate.role == role,
                AgentTemplate.is_active == True
            )
            
            # Add filters
            if product_id:
                query = query.where(AgentTemplate.product_id == product_id)
            if project_type:
                query = query.where(AgentTemplate.project_type == project_type)
            
            # Try to get most specific template first
            result = await session.execute(query)
            template = result.scalar_one_or_none()
            
            # Fall back to default template for role
            if not template:
                query = select(AgentTemplate).where(
                    AgentTemplate.role == role,
                    AgentTemplate.is_active == True,
                    AgentTemplate.is_default == True
                )
                result = await session.execute(query)
                template = result.scalar_one_or_none()
            
            if template:
                # Update usage stats
                template.usage_count += 1
                template.last_used_at = datetime.utcnow()
                await session.commit()
                
                # Cache the template
                if use_cache:
                    self._template_cache[cache_key] = template.template_content
                
                return template.template_content
            
            # Fall back to legacy template
            return self._legacy_templates.get(
                role.lower(),
                f"No template available for role: {role}"
            )
    
    def clear_cache(self):
        """Clear the template cache"""
        self._template_cache.clear()
        logger.info("Template cache cleared")
    
    def get_cached_templates(self) -> List[str]:
        """Get list of cached template keys"""
        return list(self._template_cache.keys())
    
    def get_behavioral_rules(self, role: str) -> List[str]:
        """
        Get behavioral rules for a role.
        
        Args:
            role: Agent role
        
        Returns:
            List of behavioral rules
        """
        default_rules = {
            "orchestrator": [
                "Coordinate all agents effectively",
                "Ensure project goals are met",
                "Handle conflicts and blockers",
                "Maintain project momentum",
                "Read vision document completely",
                "Challenge scope drift"
            ],
            "analyzer": [
                "Perform thorough analysis",
                "Document findings clearly",
                "Identify risks and opportunities",
                "Provide actionable insights",
                "Follow established patterns"
            ],
            "implementer": [
                "Write clean, maintainable code",
                "Follow design specifications",
                "Handle errors appropriately",
                "Test your implementation",
                "Document complex logic"
            ],
            "tester": [
                "Test all functionality thoroughly",
                "Document test results",
                "Verify edge cases",
                "Ensure quality standards",
                "Report issues clearly"
            ],
            "reviewer": [
                "Review code objectively",
                "Check for standards compliance",
                "Identify improvements",
                "Provide constructive feedback",
                "Verify requirements met"
            ],
            "documenter": [
                "Use clear, concise language",
                "Include code examples",
                "Follow documentation standards",
                "Organize content logically",
                "Keep documentation current"
            ]
        }
        
        return default_rules.get(role.lower(), ["Follow project guidelines"])
    
    def get_success_criteria(self, role: str) -> List[str]:
        """
        Get success criteria for a role.
        
        Args:
            role: Agent role
        
        Returns:
            List of success criteria
        """
        default_criteria = {
            "orchestrator": [
                "Vision document fully read",
                "All agents spawned with clear missions",
                "Project goals achieved",
                "Handoffs completed successfully"
            ],
            "analyzer": [
                "Complete system analysis",
                "Design documents created",
                "Integration points identified",
                "Risks assessed"
            ],
            "implementer": [
                "All features implemented",
                "Code follows project standards",
                "Tests pass",
                "No breaking changes"
            ],
            "tester": [
                "All tests written and passing",
                "Edge cases covered",
                "Performance validated",
                "Regression tests included"
            ],
            "reviewer": [
                "Code review complete",
                "All issues addressed",
                "Standards compliance verified",
                "Documentation approved"
            ],
            "documenter": [
                "All features documented",
                "Examples provided",
                "Setup instructions complete",
                "Architecture documented"
            ]
        }
        
        return default_criteria.get(role.lower(), ["Complete assigned tasks"])


# Singleton instance for global use
_template_manager_instance = None


def get_template_manager(db_manager: Optional[DatabaseManager] = None) -> UnifiedTemplateManager:
    """
    Get the singleton template manager instance.
    
    Args:
        db_manager: Optional database manager
    
    Returns:
        UnifiedTemplateManager instance
    """
    global _template_manager_instance
    
    if _template_manager_instance is None:
        _template_manager_instance = UnifiedTemplateManager(db_manager)
    elif db_manager and _template_manager_instance.db_manager is None:
        # Update with database manager if not previously set
        _template_manager_instance.db_manager = db_manager
    
    return _template_manager_instance