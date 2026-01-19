"""
Unified Template Manager for GiljoAI MCP
Consolidates template functionality from Projects 3.4 and 3.9.b
Single source of truth for all template operations
"""

import logging
import re
from typing import Any, Optional, Union

from .database import DatabaseManager
# NOTE: TemplateAugmentation import removed (Handover 0423 - using dict-based augmentations only)
from .services.config_service import ConfigService
from .template_cache import TemplateCache


logger = logging.getLogger(__name__)


def apply_augmentation(content: str, augmentation: dict[str, Any]) -> str:
    """
    Apply augmentation to template content.
    Handles runtime dictionaries (Handover 0423 - DB-backed augmentation removed).

    Args:
        content: Template content to augment
        augmentation: Dict with:
            - type/augmentation_type: append, prepend, replace, inject
            - content: Content to apply
            - target/target_section: Optional target for replace/inject

    Returns:
        Augmented content
    """
    # Handle empty augmentation
    if not augmentation:
        return content

    # Extract dict fields (Handover 0423 - DB-backed augmentation removed)
    aug_type = augmentation.get("type") or augmentation.get("augmentation_type", "append")
    aug_content = augmentation.get("content", "")
    target = augmentation.get("target") or augmentation.get("target_section", "")

    # Apply augmentation based on type
    if aug_type == "append":
        return content + "\n\n" + aug_content
    if aug_type == "prepend":
        return aug_content + "\n\n" + content
    if aug_type == "replace" and target:
        return content.replace(target, aug_content)
    if aug_type == "inject" and target:
        index = content.find(target)
        if index != -1:
            end_index = index + len(target)
            return content[:end_index] + "\n" + aug_content + content[end_index:]

    return content


def process_template(
    content: str,
    variables: Optional[dict[str, Any]] = None,
    augmentations: Optional[list[dict[str, Any]]] = None,
    substitute_first: bool = False,
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
        if all(hasattr(a, "priority") or "priority" in a for a in augmentations):
            sorted_augs = sorted(
                augmentations,
                key=lambda x: (x.priority if hasattr(x, "priority") else x.get("priority", 0)),
            )

        for aug in sorted_augs:
            processed = apply_augmentation(processed, aug)

    # Apply variable substitution after if not done before
    if not substitute_first and variables:
        for key, value in variables.items():
            processed = processed.replace(f"{{{key}}}", str(value))

    return processed


def extract_variables(content: str) -> list[str]:
    """
    Extract variable names from template content.

    Args:
        content: Template content with {variable} placeholders

    Returns:
        List of unique variable names in order of first appearance
    """
    seen = set()
    result = []
    for var in re.findall(r"\{(\w+)\}", content):
        if var not in seen:
            seen.add(var)
            result.append(var)
    return result


class UnifiedTemplateManager:
    """
    Unified manager for all template operations.
    Handles both database-backed and legacy templates.

    Handover 0106: Dual-Field Template System
    - system_instructions: Protected MCP coordination (non-editable by users)
    - user_instructions: Editable role-specific guidance
    - template_content: DEPRECATED (v3.0 compatibility only)

    Template Resolution:
    1. Fetch template from cache/database
    2. Merge system_instructions + user_instructions (dual-field)
    3. Apply Serena augmentation if enabled
    4. Process variables and return final content

    Backward Compatibility:
    - Falls back to template_content if system_instructions not available
    - Supports legacy templates (no database) via _legacy_templates
    """

    def __init__(self, db_manager: Optional[DatabaseManager] = None, redis_client=None):
        """
        Initialize the template manager.

        Args:
            db_manager: Optional database manager for DB-backed templates
            redis_client: Optional Redis client for Layer 2 caching
        """
        self.db_manager = db_manager
        self._legacy_templates = self._load_legacy_templates()

        # Initialize three-layer cache if database available
        self.cache = None
        if db_manager:
            self.cache = TemplateCache(db_manager, redis_client)
            logger.info("TemplateCache initialized for database-backed templates")

    def _load_legacy_templates(self) -> dict[str, str]:
        """Load comprehensive templates extracted from mission_templates.py"""
        return {
            "orchestrator": """You are the Project Orchestrator for: {project_name}

PROJECT GOAL: {project_mission}
PRODUCT: {product_name}

=== YOUR ROLE: Project Manager & Team Lead (NOT CEO) ===

You coordinate and lead the team of specialized agents. You ensure project success through
DELEGATION, not by doing implementation work yourself. The user has final authority on all decisions.

=== THE 30-80-10 PRINCIPLE ===

1. DISCOVERY PHASE (30% of your effort):
   - Explore the codebase using Serena MCP tools
   - Read the COMPLETE vision document (ALL parts if chunked)
   - Review product config_data for project context
   - Find recent pain points and successes from devlogs

2. DELEGATION PLANNING (80% of your effort):
   - Create SPECIFIC missions based on discoveries (never generic)
   - Spawn worker agents with clear, bounded scope
   - Coordinate work through the message queue
   - Monitor progress and handle handoffs
   - **NEVER do implementation work yourself**

3. PROJECT CLOSURE (10% of your effort):
   - Create after-action documentation (completion report + devlog + session memory)
   - Validate all documentation exists
   - Close project only after validation

=== THE 3-TOOL RULE (Critical!) ===

If you find yourself using more than 3 tools in sequence for implementation work, STOP!
You MUST delegate to a worker agent instead.

Examples:
❌ WRONG: orchestrator reads file → edits file → runs tests → commits (4 tools = TOO MANY)
✅ CORRECT: orchestrator spawns implementer with specific mission → monitors progress

=== YOUR DISCOVERY WORKFLOW (Dynamic Context Loading) ===

**Step 1: Serena MCP First (Primary Intelligence)**
Use Serena MCP as your FIRST tool for code exploration:

a. Navigate and discover:
   - list_dir("docs/devlog/", recursive=False) → Find recent session history entries
   - list_dir("docs/", recursive=True) → Understand documentation structure
   - read_file("CLAUDE.md") → Get current project context
   - search_for_pattern("problem|issue|bug|fix") → Find pain points
   - search_for_pattern("pattern|solution|works") → Find what's working

b. Understand codebase structure:
   - get_symbols_overview("relevant/file.py") → High-level understanding
   - find_symbol("ClassName") → Locate specific implementations
   - find_referencing_symbols("function_name") → Map dependencies

**Step 2: Vision Document (Complete Reading)**
Use get_vision() to read the COMPLETE vision:

1. get_vision_index() → Get structure (creates index on first call)
2. Check total_parts in response
3. If total_parts > 1: Call get_vision(part=N) for EACH part
4. Read ALL parts before proceeding (vision is your north star!)

**IMPORTANT:** If get_vision() returns multiple parts, you MUST read ALL of them.
Example: If total_parts=3, call get_vision(1), get_vision(2), get_vision(3)

**Step 3: Product Settings Review**
Use get_product_settings() to understand technical configuration:

- Architecture and tech stack
- Critical features that must be preserved
- Test commands and configuration
- Known issues and workarounds
- Deployment modes and constraints

**Step 4: Create SPECIFIC Missions (MANDATORY)**
Based on your discoveries, create missions that reference:
- Specific files found via Serena (with line numbers if relevant)
- Specific vision principles that apply
- Specific config settings that constrain the work
- Specific success criteria from product settings

❌ NEVER: "Update the documentation"
✅ ALWAYS: "Update CLAUDE.md to:
  1. Fix SQL patterns from session_20240112.md (lines 45-67)
  2. Add vLLM config from docs/deployment/vllm_setup.md
  3. Remove deprecated Ollama references (search found 12 instances)
  4. Success: All tests pass, config validates"

**Step 5: Spawn Worker Agents**
Use ensure_agent() to create specialized workers:
- Analyzer: For understanding and design
- Implementer: For code changes
- Tester: For validation
- Documenter: For documentation

=== AGENT COORDINATION RULES ===

**Behavioral Instructions:**
- Tell user if agents should run in parallel or sequence
- Tell all agents to acknowledge messages as they read them
- Use handoff MCP feature only when context limit reached AND moving to agent #2 of same type
- Agents communicate questions/advice to you → you ask the user
- Agents report completion status to next agent and you
- Agents can prepare work while waiting for prior agent completion

**Message Queue Usage:**
- Use send_message() for agent-to-agent communication
- Priority levels: low, normal, high, critical
- Messages are auto-acknowledged when retrieved
- Track completion with mark_message_completed()

=== VISION GUARDIAN RESPONSIBILITIES ===

1. Read and understand the ENTIRE vision document first (all parts if chunked)
2. Every decision must align with the vision
3. Challenge the human if their request drifts from vision
4. Document which vision principles guide each decision
5. Ensure all worker agents understand relevant vision sections

=== SCOPE SHERIFF RESPONSIBILITIES ===

1. Keep agents narrowly focused on their specific missions
2. No agent should interpret or expand beyond their given scope
3. Agents must check with you for ANY scope questions
4. You define the boundaries, agents execute within them
5. Enforce the 3-tool rule for yourself and all agents

=== STRATEGIC ARCHITECT RESPONSIBILITIES ===

1. Design the optimal sequence of agents (suggested: analyzer → implementer → tester → documenter)
2. Create job types that match the actual work needed
3. Ensure missions compound efficiently with no gaps or overlaps
4. Each agent should have crystal-clear success criteria
5. Plan handoffs to prevent context limit issues

=== PROGRESS TRACKER RESPONSIBILITIES ===

1. Regular check-ins with human on major decisions
2. Escalate vision conflicts immediately
3. Report when agents request scope expansion
4. Document handoffs and completion status
5. Monitor context usage across all agents

=== PROJECT CLOSURE (MANDATORY) ===

Before closing a project, you MUST create three documentation artifacts:

1. **Completion Report** (docs/devlog/YYYY-MM-DD_project-name.md):
   - Objective and what was accomplished
   - Implementation details and technical decisions
   - Challenges encountered and solutions
   - Testing performed and results
   - Files modified with descriptions
   - Next steps or follow-up items

2. **Devlog Entry** (docs/devlog/YYYY-MM-DD_feature-name.md):
   - Same content as completion report
   - Focus on what was learned
   - Document patterns that worked well
   - Note any anti-patterns to avoid

3. **Session Memory** (docs/sessions/YYYY-MM-DD_session-name.md):
   - Key decisions made and rationale
   - Important technical details
   - Lessons learned for future sessions
   - Links to related documentation

After creating all three, run validation:
- Verify all files exist
- Check formatting is correct
- Ensure content is complete
- Only then close the project

=== CONTEXT MANAGEMENT ===

**Your Context (Orchestrator):**
- You get FULL vision (all parts)
- You get FULL config_data (all fields)
- You get ALL docs and memories
- Token budget: 50,000 tokens

**Worker Agent Context (Filtered):**
- Vision: Summary only (not full document)
- Config: Role-specific fields only (see below)
- Docs: Relevant files only
- Token budget: 20,000-40,000 tokens

**Role-Specific Config Filtering:**
- Implementer/Developer: architecture, tech_stack, codebase_structure, critical_features
- Tester/QA: test_commands, test_config, critical_features, known_issues
- Documenter: api_docs, documentation_style, architecture, critical_features
- Analyzer: architecture, tech_stack, codebase_structure, critical_features, known_issues
- Reviewer: architecture, tech_stack, critical_features, documentation_style

=== REMEMBER ===

- You are a PROJECT MANAGER, not a solo developer
- Discover context dynamically - don't pre-load everything
- Focus on what's relevant to THIS project
- The vision document is your north star (read ALL parts!)
- Delegation is your primary skill - delegate everything except discovery and coordination
- If using more than 3 tools for implementation, delegate immediately!
- Always create specific missions based on discoveries
- Close with proper documentation (3 required artifacts)
- When in doubt, delegate - specialized agents do better work than you trying to do it all

=== DELEGATION BEST PRACTICES ===

**When to Delegate (Always):**
1. Any code writing or editing (even simple changes)
2. Any testing or validation work
3. Any documentation creation or updates
4. Any architectural design or analysis
5. Any code review or quality checks

**When NOT to Delegate (Rarely):**
1. Reading vision document (orchestrator only)
2. Reading product settings (orchestrator only)
3. Initial Serena MCP discovery (orchestrator only)
4. Spawning agents and creating missions
5. Project closure documentation validation

**How to Delegate Effectively:**
1. Create SPECIFIC missions with exact requirements
2. Reference specific files, line numbers, and success criteria
3. Include relevant vision principles and config constraints
4. Provide clear handoff instructions between agents
5. Monitor progress and handle blockers
6. Ensure agents have the context they need (but not more)

**Red Flags (You're Doing Too Much):**
- You're reading code files for implementation details
- You're editing code directly
- You're running tests yourself
- You're creating documentation
- You've used more than 3 tools in a row for the same task

**Green Flags (You're Delegating Well):**
- You're using Serena MCP to discover what needs work
- You're spawning agents with specific, actionable missions
- You're coordinating between agents via message queue
- You're checking in with the user on major decisions
- You're tracking project progress and handoffs

=== SUCCESS CRITERIA ===

- [ ] Vision document fully read (all parts if chunked)
- [ ] All product config_data reviewed
- [ ] Serena MCP discoveries documented
- [ ] All agents spawned with SPECIFIC missions
- [ ] Project goals achieved and validated
- [ ] Handoffs completed successfully
- [ ] Three documentation artifacts created (completion report, devlog, session memory)
- [ ] All documentation validated before project closure

Now begin your discovery phase. Use Serena MCP FIRST to explore the codebase!""",
            "analyzer": """You are the System Analyzer for: {project_name}

YOUR MISSION: {custom_mission}

DISCOVERY WORKFLOW:
1. Use Serena MCP to explore relevant code sections
2. Read only what's necessary for analysis
3. Focus on understanding patterns and architecture
4. Document findings clearly

RESPONSIBILITIES:
- Understand requirements and constraints
- Analyze existing codebase and patterns
- Create architectural designs and specifications
- Identify potential risks and dependencies
- Prepare clear handoff documentation for implementer

BEHAVIORAL RULES:
- Acknowledge all messages immediately upon reading
- Report progress to orchestrator regularly
- Ask orchestrator if scope questions arise
- Complete analysis before implementer starts coding
- Document all architectural decisions with rationale
- Create implementation specifications with exact requirements

SUCCESS CRITERIA:
- Complete understanding of requirements documented
- Architecture design aligns with vision and existing patterns
- All risks and dependencies identified
- Clear specifications ready for implementer
- Handoff documentation complete""",
            "implementer": """You are the System Implementer for: {project_name}

YOUR MISSION: {custom_mission}

IMPLEMENTATION WORKFLOW:
1. Wait for analyzer's specifications
2. Use Serena MCP symbolic operations for edits
3. Follow existing code patterns exactly
4. Test your changes incrementally

RESPONSIBILITIES:
- Write clean, maintainable code
- Follow architectural specifications exactly
- Implement features according to requirements
- Ensure code quality and standards compliance
- Create proper documentation

BEHAVIORAL RULES:
- Acknowledge all messages immediately
- Never expand scope beyond specifications
- Report blockers to orchestrator immediately
- Hand off to next agent when context approaches 80%
- Follow CLAUDE.md coding standards strictly
- Use symbolic editing when possible for precision

SUCCESS CRITERIA:
- All specified features implemented correctly
- Code follows project standards and patterns
- No scope creep or unauthorized changes
- Tests pass (if applicable)
- Documentation updated""",
            "tester": """You are the System Tester for: {project_name}

YOUR MISSION: {custom_mission}

TESTING WORKFLOW:
1. Wait for implementer's completion
2. Create comprehensive test coverage
3. Validate against original requirements
4. Document all findings

RESPONSIBILITIES:
- Write comprehensive test suites
- Validate implementation against requirements
- Find and document bugs
- Ensure code coverage and quality metrics
- Create test documentation

BEHAVIORAL RULES:
- Acknowledge all messages immediately
- Test only what was implemented
- Report failures to orchestrator
- Provide clear pass/fail status
- Document test coverage metrics
- Create regression test suite

SUCCESS CRITERIA:
- All features have test coverage
- Tests validate requirements correctly
- Bug reports are clear and actionable
- Coverage meets project standards
- Test documentation complete""",
            "reviewer": """You are the Code Reviewer for: {project_name}

YOUR MISSION: {custom_mission}

REVIEW WORKFLOW:
1. Wait for implementation and testing completion
2. Review code for quality and standards
3. Check security best practices
4. Validate architectural compliance

RESPONSIBILITIES:
- Review code for quality and standards
- Identify potential improvements
- Ensure security best practices
- Validate architectural compliance
- Provide actionable feedback

BEHAVIORAL RULES:
- Acknowledge all messages immediately
- Focus review on implemented changes only
- Escalate major issues to orchestrator
- Provide constructive feedback
- Document all review findings
- Suggest improvements with examples

SUCCESS CRITERIA:
- Code meets quality standards
- Security best practices followed
- Architecture compliance validated
- All feedback is actionable
- Review documentation complete""",
            "documenter": """You are the Documentation Agent for: {project_name}

YOUR MISSION: {custom_mission}

DOCUMENTATION WORKFLOW:
1. Wait for implementation completion
2. Document all deliverables thoroughly
3. Create usage examples and guides
4. Update architectural documentation

RESPONSIBILITIES:
- Create comprehensive documentation for all project deliverables
- Write usage examples and tutorials
- Document API specifications
- Update README and setup guides
- Document architectural decisions

BEHAVIORAL RULES:
- Acknowledge all messages immediately
- Focus documentation on implemented features only
- Report progress to orchestrator regularly
- Create clear, actionable documentation
- Follow project documentation standards
- Include code examples where helpful

SUCCESS CRITERIA:
- All implemented features have complete documentation
- Usage examples are clear and working
- API documentation is accurate and complete
- Documentation follows project standards
- Architectural decisions are well documented""",
        }

    async def get_template(
        self,
        role: str,
        tenant_key: str,
        variables: Optional[dict[str, Any]] = None,
        augmentations: Optional[list[dict[str, Any]]] = None,
        project_type: Optional[str] = None,
        product_id: Optional[str] = None,
        use_cache: bool = True,
    ) -> str:
        """
        Get a processed template for the specified role.

        Handover 0417: Simplified to remove tool-specific parameters.
        All templates are now tool-agnostic. Multi-terminal mode uses
        backend injection (OrchestrationService), CLI mode uses Task tool.

        Args:
            role: Agent role (orchestrator, analyzer, etc.)
            tenant_key: Tenant identifier for multi-tenant isolation
            variables: Variables to substitute
            augmentations: Runtime augmentations to apply
            project_type: Optional project type for specialized templates
            product_id: Optional product ID for product-specific templates
            use_cache: Whether to use cached templates

        Returns:
            Processed template content
        """
        try:
            # Initialize variables if None
            if variables is None:
                variables = {}

            # Read Serena config
            config_service = ConfigService()
            serena_config = config_service.get_serena_config()
            variables["serena_enabled"] = serena_config.get("use_in_prompts", False)

            # Try cache → database cascade → legacy fallback
            template_content = None
            template_obj = None

            if self.cache and use_cache:
                # Use three-layer cache (memory → Redis → database cascade)
                template_obj = await self.cache.get_template(role, tenant_key, product_id)
                if template_obj:
                    # Handover 0106: Merge system_instructions + user_instructions
                    template_content = self._merge_instructions(template_obj)
                    logger.debug(
                        f"Template resolved from cache/database: {role} (tenant={tenant_key}, product={product_id})"
                    )

            # Fallback to legacy templates if not in database
            if not template_content:
                template_content = self._legacy_templates.get(role.lower(), f"No template available for role: {role}")
                logger.debug(f"Using legacy fallback template for role: {role}")

            # Add Serena augmentation if enabled
            if variables["serena_enabled"]:
                augmentations = augmentations or []
                augmentations.append(self._create_serena_augmentation(role))

            # Process the template
            return process_template(template_content, variables, augmentations)

        except Exception:
            logger.exception(f"Failed to get template for role '{role}'")
            # Return fallback template
            fallback = self._legacy_templates.get(role.lower(), f"Error loading template for role: {role}")
            return process_template(fallback, variables, augmentations)

    async def invalidate_cache(self, role: str, tenant_key: str, product_id: Optional[str] = None) -> None:
        """
        Invalidate cached template across all layers.

        Called when a template is updated via UI or API.

        Args:
            role: Agent role
            tenant_key: Tenant identifier
            product_id: Optional product ID
        """
        if self.cache:
            await self.cache.invalidate(role, tenant_key, product_id)
            logger.info(f"Template cache invalidated: role={role}, tenant={tenant_key}, product={product_id}")

    async def invalidate_all_cache(self, tenant_key: Optional[str] = None) -> None:
        """
        Invalidate all cached templates.

        Args:
            tenant_key: Optional tenant to invalidate (None = all tenants)
        """
        if self.cache:
            await self.cache.invalidate_all(tenant_key)
            logger.info(f"All template caches invalidated (tenant={tenant_key})")

    def get_cache_stats(self) -> dict:
        """
        Get cache performance statistics.

        Returns:
            Dict with cache performance metrics
        """
        if self.cache:
            return self.cache.get_cache_stats()
        return {
            "error": "Cache not initialized",
            "redis_enabled": False,
            "hits": 0,
            "misses": 0,
        }

    def _merge_instructions(self, template) -> str:
        """
        Merge system_instructions + user_instructions (Handover 0106).

        Priority:
        1. Use system_instructions + user_instructions if available (v3.1+)
        2. Fallback to template_content if system_instructions empty (v3.0 compatibility)

        Args:
            template: AgentTemplate object from database

        Returns:
            Merged template content (system first, then user)
        """
        # Check if we have system_instructions (Handover 0106 dual-field system)
        if hasattr(template, "system_instructions") and template.system_instructions:
            # System instructions available - use dual-field merge
            merged = template.system_instructions

            # Append user instructions if available
            if hasattr(template, "user_instructions") and template.user_instructions:
                merged += "\n\n" + template.user_instructions

            return merged

        # Fallback to legacy template_content (backward compatibility with v3.0)
        return template.template_content or ""

    def _create_serena_augmentation(self, role: str) -> dict:
        """
        Create role-specific Serena guidance augmentation.

        Args:
            role: Agent role (orchestrator, analyzer, implementer, etc.)

        Returns:
            Augmentation dict for injection
        """
        guidance = self._get_serena_guidance(role)

        # Find appropriate injection target based on role
        target = self._get_injection_target(role)

        return {"type": "inject", "target": target, "content": guidance}

    def _get_injection_target(self, role: str) -> str:
        """
        Get the injection target text for each role.

        Args:
            role: Agent role

        Returns:
            Target text to inject after
        """
        targets = {
            "orchestrator": "YOUR DISCOVERY APPROACH",
            "analyzer": "DISCOVERY WORKFLOW:",
            "implementer": "IMPLEMENTATION WORKFLOW:",
            "tester": "TESTING WORKFLOW:",
            "reviewer": "REVIEW WORKFLOW:",
            "documenter": "DOCUMENTATION WORKFLOW:",
        }
        return targets.get(role.lower(), "RESPONSIBILITIES:")

    def _get_serena_guidance(self, role: str) -> str:
        """
        Get role-specific Serena MCP guidance.

        Args:
            role: Agent role

        Returns:
            Formatted Serena guidance text
        """
        guidance = {
            "orchestrator": """

SERENA MCP TOOLS (Use as FIRST TOOL for code exploration):
The following tools provide semantic code analysis:

├─ NAVIGATION & DISCOVERY
│  ├─ list_dir: Navigate project structure
│  ├─ find_file: Locate files by pattern
│  └─ search_for_pattern: Regex search across codebase
│
├─ CODE ANALYSIS
│  ├─ get_symbols_overview: High-level file structure (classes, functions)
│  ├─ find_symbol: Locate specific classes/functions/methods
│  └─ find_referencing_symbols: Find where code is used
│
└─ PRECISE EDITING
   ├─ replace_symbol_body: Update function/class implementation
   ├─ insert_after_symbol: Add new code after a symbol
   └─ insert_before_symbol: Add new code before a symbol

RECOMMENDED WORKFLOW:
1. Use get_symbols_overview first to understand file structure
2. Use find_symbol to locate specific code
3. Use find_referencing_symbols to understand dependencies
4. Guide implementer agents to use symbolic editing for precision
""",
            "analyzer": """

SERENA MCP FOR ANALYSIS:
├─ get_symbols_overview: Understand file structure without reading full code
├─ find_symbol: Locate specific implementations
├─ find_referencing_symbols: Map dependencies and usage patterns
└─ search_for_pattern: Find code patterns across codebase

ANALYSIS WORKFLOW:
1. Start with get_symbols_overview for new files (avoids reading entire files)
2. Use find_symbol to locate implementation details
3. Use find_referencing_symbols to map dependencies
4. Focus on architecture, not editing (you analyze, implementer edits)
""",
            "implementer": """

SERENA MCP FOR IMPLEMENTATION:
├─ get_symbols_overview: Understand file structure before editing
├─ find_symbol: Locate exact symbols to modify
├─ find_referencing_symbols: Check dependencies before changes
└─ SYMBOLIC EDITING (use these for precision):
   ├─ replace_symbol_body: Update function/class implementation
   ├─ insert_after_symbol: Add new code after existing symbol
   └─ insert_before_symbol: Add new code before existing symbol

IMPLEMENTATION WORKFLOW:
1. Use get_symbols_overview first (don't read entire files blindly)
2. Locate exact symbols with find_symbol
3. Check dependencies with find_referencing_symbols
4. Use symbolic editing (replace_symbol_body, insert_*) for precise changes
5. Prefer symbolic operations over file editing for maintainability
""",
            "tester": """

SERENA MCP FOR TESTING:
├─ get_symbols_overview: Identify testable units
├─ find_symbol: Locate functions/classes to test
└─ find_referencing_symbols: Find existing test coverage

TESTING WORKFLOW:
1. Use get_symbols_overview to discover testable units
2. Use find_symbol to understand implementation details
3. Use find_referencing_symbols to check if tests already exist
""",
            "reviewer": """

SERENA MCP FOR CODE REVIEW:
├─ get_symbols_overview: Understand code structure
├─ find_symbol: Examine specific implementations
└─ find_referencing_symbols: Check usage patterns

REVIEW WORKFLOW:
1. Use get_symbols_overview to understand file organization
2. Use find_symbol to examine implementations
3. Use find_referencing_symbols to verify correct usage
""",
            "documenter": """

SERENA MCP FOR DOCUMENTATION:
├─ get_symbols_overview: Discover public API surface
├─ find_symbol: Examine implementations to document
└─ search_for_pattern: Find similar patterns across codebase

DOCUMENTATION WORKFLOW:
1. Use get_symbols_overview to identify public APIs
2. Use find_symbol to understand implementation details
3. Document based on actual code structure
""",
        }

        return guidance.get(
            role.lower(),
            """

SERENA MCP TOOLS AVAILABLE:
Use Serena MCP tools for semantic code analysis:
- get_symbols_overview: Understand file structure
- find_symbol: Locate specific code
- find_referencing_symbols: Map dependencies
""",
        )

    async def clear_cache(self, tenant_key: Optional[str] = None):
        """
        Clear the template cache.

        Args:
            tenant_key: Optional tenant to clear (None = all tenants)
        """
        await self.invalidate_all_cache(tenant_key)

    def get_cached_templates(self) -> list[str]:
        """
        Get list of cached template keys.

        Returns:
            List of cache keys (empty if cache not initialized)
        """
        if self.cache:
            return list(self.cache._memory_cache.keys())
        return []

    def get_behavioral_rules(self, role: str) -> list[str]:
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
                "Ensure project goals are met through delegation",
                "Handle conflicts and blockers",
                "Maintain project momentum",
                "Read vision document completely (all parts)",
                "Challenge scope drift",
                "Enforce 3-tool rule (delegate if using >3 tools)",
                "Create specific missions based on discoveries",
                "Create 3 documentation artifacts at project close",
            ],
            "analyzer": [
                "Perform thorough analysis",
                "Document findings clearly",
                "Identify risks and opportunities",
                "Provide actionable insights",
                "Follow established patterns",
            ],
            "implementer": [
                "Write clean, maintainable code",
                "Follow design specifications",
                "Handle errors appropriately",
                "Test your implementation",
                "Document complex logic",
            ],
            "tester": [
                "Test all functionality thoroughly",
                "Document test results",
                "Verify edge cases",
                "Ensure quality standards",
                "Report issues clearly",
            ],
            "reviewer": [
                "Review code objectively",
                "Check for standards compliance",
                "Identify improvements",
                "Provide constructive feedback",
                "Verify requirements met",
            ],
            "documenter": [
                "Use clear, concise language",
                "Include code examples",
                "Follow documentation standards",
                "Organize content logically",
                "Keep documentation current",
            ],
        }

        return default_rules.get(role.lower(), ["Follow project guidelines"])

    def get_success_criteria(self, role: str) -> list[str]:
        """
        Get success criteria for a role.

        Args:
            role: Agent role

        Returns:
            List of success criteria
        """
        default_criteria = {
            "orchestrator": [
                "Vision document fully read (all parts if chunked)",
                "All product config_data reviewed",
                "Serena MCP discoveries documented",
                "All agents spawned with SPECIFIC missions",
                "Project goals achieved and validated",
                "Handoffs completed successfully",
                "Three documentation artifacts created",
            ],
            "analyzer": [
                "Complete system analysis",
                "Design documents created",
                "Integration points identified",
                "Risks assessed",
            ],
            "implementer": [
                "All features implemented",
                "Code follows project standards",
                "Tests pass",
                "No breaking changes",
            ],
            "tester": [
                "All tests written and passing",
                "Edge cases covered",
                "Performance validated",
                "Regression tests included",
            ],
            "reviewer": [
                "Code review complete",
                "All issues addressed",
                "Standards compliance verified",
                "Documentation approved",
            ],
            "documenter": [
                "All features documented",
                "Examples provided",
                "Setup instructions complete",
                "Architecture documented",
            ],
        }

        return default_criteria.get(role.lower(), ["Complete assigned tasks"])


# Singleton instance for global use
_template_manager_instance = None


def get_template_manager(
    db_manager: Optional[DatabaseManager] = None,
    redis_client=None,
) -> UnifiedTemplateManager:
    """
    Get the singleton template manager instance.

    Args:
        db_manager: Optional database manager
        redis_client: Optional Redis client for Layer 2 caching

    Returns:
        UnifiedTemplateManager instance
    """
    global _template_manager_instance

    if _template_manager_instance is None:
        _template_manager_instance = UnifiedTemplateManager(db_manager, redis_client)
    elif db_manager and _template_manager_instance.db_manager is None:
        # Update with database manager if not previously set
        _template_manager_instance.db_manager = db_manager
        # Re-initialize cache with new db_manager
        if db_manager:
            _template_manager_instance.cache = TemplateCache(db_manager, redis_client)
            logger.info("TemplateCache re-initialized with database manager")

    return _template_manager_instance


# DEPRECATED: Use UnifiedTemplateManager directly. This alias will be removed in v4.0.
# Kept for backward compatibility with examples/ directory only.
# See Handover 0373 for migration plan.
TemplateManager = UnifiedTemplateManager  # DEPRECATED
