"""
Mission Template Generator for GiljoAI MCP Orchestrator.

Provides comprehensive mission templates for orchestrator and agents with:
- Vision guardian responsibilities
- Scope sheriff enforcement
- Dynamic discovery workflows
- Behavioral instructions
- Project-type aware customization
"""

from typing import Dict, Optional, Any
from .enums import AgentRole, ProjectType


class MissionTemplateGenerator:
    """
    Generates comprehensive mission templates for orchestrator and agents.
    
    Features:
    - Dynamic template generation with variable substitution
    - Vision guardian and scope sheriff instructions
    - Role-specific behavioral guidelines
    - Project-type aware customization
    - Chunked vision reading instructions
    """
    
    # Comprehensive orchestrator template with vision guardian and scope sheriff
    ORCHESTRATOR_TEMPLATE = """You are the Project Orchestrator for: {project_name}

PROJECT GOAL: {project_mission}
PRODUCT: {product_name}

YOUR DISCOVERY APPROACH (Dynamic Context Loading):
1. Read the vision document using get_vision()
   - IMPORTANT: If it returns multiple parts (check total_parts in response), call it multiple times
   - Example: If total_parts=3, call get_vision(part=1), get_vision(part=2), get_vision(part=3)
   - Read ALL parts to get complete vision before proceeding
2. Review product settings with get_product_settings() - understand technical configuration
3. Use Serena MCP to explore the codebase for implementation details
4. Only load what's relevant to this specific project

YOUR AUTHORITY:
- Create any agents with ANY job types you deem necessary
- Define precise missions for each agent based on discoveries
- Choose optimal implementation approach
- Design the agent pipeline that best achieves the goal

YOUR RESPONSIBILITIES:

1. VISION GUARDIAN:
   - Read and understand the ENTIRE vision document first (all parts if chunked)
   - Every decision must align with the vision
   - Challenge the human if their request drifts from vision
   - Document which vision principles guide each decision

2. SCOPE SHERIFF:
   - Keep agents narrowly focused on their specific missions
   - No agent should interpret or expand beyond their given scope
   - Agents must check with you for ANY scope questions
   - You define the boundaries, agents execute within them

3. STRATEGIC ARCHITECT:
   - Design the optimal sequence of agents (suggested: analyzer, implementer, tester)
   - Create job types that match the actual work needed
   - Ensure missions compound efficiently with no gaps or overlaps
   - Each agent should have crystal-clear success criteria

4. PROGRESS TRACKER:
   - Regular check-ins with human on major decisions
   - Escalate vision conflicts immediately
   - Report when agents request scope expansion
   - Document handoffs and completion status

BEHAVIORAL INSTRUCTIONS:
- Tell user if agents should run in parallel at start or started in order
- Tell all agents to acknowledge messages as they read them
- Only use handoff MCP feature upon context limit and moving to agent #2 of same type
- Agents should communicate questions and advice to the orchestrator who will ask the user
- Agents shall communicate status when completed to the next agent and report to orchestrator
- Agents can start preparing work and plan while waiting for completion message from prior agent

REMEMBER:
- Discover context dynamically - don't pre-load everything
- Focus on what's relevant to THIS project
- You have Serena MCP to help explore the codebase
- The vision document is your north star
- If get_vision() returns parts, read ALL parts before proceeding"""

    # Role-specific agent templates
    ANALYZER_TEMPLATE = """You are the System Analyzer for: {project_name}

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
- Handoff documentation complete"""

    IMPLEMENTER_TEMPLATE = """You are the System Implementer for: {project_name}

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
- Documentation updated"""

    TESTER_TEMPLATE = """You are the System Tester for: {project_name}

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
- Test documentation complete"""

    REVIEWER_TEMPLATE = """You are the Code Reviewer for: {project_name}

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
- Review documentation complete"""

    # Project-type specific customizations
    PROJECT_TYPE_CUSTOMIZATIONS = {
        ProjectType.FOUNDATION: {
            "focus": "Database schema, core models, and basic infrastructure",
            "key_concerns": ["Data integrity", "Schema design", "Migration support"],
            "suggested_agents": ["analyzer", "implementer", "tester"]
        },
        ProjectType.MCP_INTEGRATION: {
            "focus": "MCP protocol implementation and tool registration",
            "key_concerns": ["Protocol compliance", "Tool validation", "Error handling"],
            "suggested_agents": ["analyzer", "implementer", "tester", "reviewer"]
        },
        ProjectType.ORCHESTRATION: {
            "focus": "Agent coordination, message routing, and workflow management",
            "key_concerns": ["Concurrency", "State management", "Message reliability"],
            "suggested_agents": ["analyzer", "implementer", "tester"]
        },
        ProjectType.USER_INTERFACE: {
            "focus": "Dashboard, visualizations, and user interactions",
            "key_concerns": ["UX design", "Responsiveness", "Accessibility"],
            "suggested_agents": ["analyzer", "implementer", "tester", "reviewer"]
        },
        ProjectType.DEPLOYMENT: {
            "focus": "Packaging, distribution, and production readiness",
            "key_concerns": ["Security", "Performance", "Scalability"],
            "suggested_agents": ["analyzer", "implementer", "tester", "reviewer"]
        }
    }
    
    def __init__(self):
        """Initialize the template generator."""
        self.templates = {
            AgentRole.ORCHESTRATOR: self.ORCHESTRATOR_TEMPLATE,
            AgentRole.ANALYZER: self.ANALYZER_TEMPLATE,
            AgentRole.IMPLEMENTER: self.IMPLEMENTER_TEMPLATE,
            AgentRole.TESTER: self.TESTER_TEMPLATE,
            AgentRole.REVIEWER: self.REVIEWER_TEMPLATE
        }
    
    def generate_orchestrator_mission(
        self,
        project_name: str,
        project_mission: str,
        product_name: str = "GiljoAI-MCP Coding Orchestrator",
        additional_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate comprehensive orchestrator mission with vision guardian role.
        
        Args:
            project_name: Name of the project
            project_mission: Project mission/goals
            product_name: Product being built
            additional_context: Optional additional context
            
        Returns:
            Complete orchestrator mission template
        """
        template_vars = {
            "project_name": project_name,
            "project_mission": project_mission,
            "product_name": product_name
        }
        
        mission = self.ORCHESTRATOR_TEMPLATE.format(**template_vars)
        
        # Add project-type specific guidance if available
        if additional_context and "project_type" in additional_context:
            project_type = additional_context["project_type"]
            if project_type in self.PROJECT_TYPE_CUSTOMIZATIONS:
                customization = self.PROJECT_TYPE_CUSTOMIZATIONS[project_type]
                mission += f"\n\nPROJECT TYPE GUIDANCE:\n"
                mission += f"- Focus: {customization['focus']}\n"
                mission += f"- Key Concerns: {', '.join(customization['key_concerns'])}\n"
                mission += f"- Suggested Agents: {', '.join(customization['suggested_agents'])}"
        
        return mission
    
    def generate_agent_mission(
        self,
        role: AgentRole,
        project_name: str,
        custom_mission: Optional[str] = None,
        additional_instructions: Optional[str] = None
    ) -> str:
        """
        Generate role-specific agent mission with behavioral instructions.
        
        Args:
            role: Agent role
            project_name: Name of the project
            custom_mission: Optional custom mission override
            additional_instructions: Optional additional instructions
            
        Returns:
            Complete agent mission template
        """
        if role not in self.templates:
            raise ValueError(f"Unknown role: {role}")
        
        # Get base template
        template = self.templates[role]
        
        # Prepare template variables
        template_vars = {
            "project_name": project_name,
            "custom_mission": custom_mission or self._get_default_mission(role)
        }
        
        # Generate mission
        mission = template.format(**template_vars)
        
        # Add additional instructions if provided
        if additional_instructions:
            mission += f"\n\nADDITIONAL INSTRUCTIONS:\n{additional_instructions}"
        
        return mission
    
    def generate_handoff_instructions(
        self,
        from_role: AgentRole,
        to_role: AgentRole,
        context_summary: str
    ) -> str:
        """
        Generate handoff instructions between agents.
        
        Args:
            from_role: Source agent role
            to_role: Target agent role
            context_summary: Summary of work completed
            
        Returns:
            Handoff instructions
        """
        instructions = f"""HANDOFF FROM {from_role.value.upper()} TO {to_role.value.upper()}

CONTEXT SUMMARY:
{context_summary}

HANDOFF PROTOCOL:
1. {to_role.value}: Acknowledge receipt of this handoff immediately
2. Review the context summary and any attached artifacts
3. Ask {from_role.value} for clarification if needed (via orchestrator)
4. Begin your work based on the provided context
5. Report progress to orchestrator regularly

CONTINUITY REQUIREMENTS:
- Maintain consistency with work already completed
- Follow the same patterns and standards used by {from_role.value}
- Reference previous decisions and implementations
- Build upon the existing foundation without breaking changes

COMMUNICATION:
- Direct questions to orchestrator for user clarification
- Report blockers immediately
- Provide status updates at major milestones
- Document your decisions for the next agent"""
        
        return instructions
    
    def generate_parallel_startup_instructions(
        self,
        agents: list[str],
        project_name: str
    ) -> str:
        """
        Generate instructions for parallel agent startup.
        
        Args:
            agents: List of agent names to start in parallel
            project_name: Name of the project
            
        Returns:
            Parallel startup instructions
        """
        agent_list = ", ".join(agents)
        
        instructions = f"""PARALLEL AGENT STARTUP for {project_name}

AGENTS TO START IN PARALLEL:
{agent_list}

COORDINATION PROTOCOL:
1. All agents start simultaneously
2. Each agent acknowledges their mission immediately
3. Agents work on independent preparation tasks
4. Synchronization points defined by orchestrator
5. Message passing for dependencies

PARALLEL WORK GUIDELINES:
- Analyzer: Begin requirements analysis and design
- Implementer: Review codebase and prepare environment
- Tester: Design test strategy and prepare test framework
- Reviewer: Familiarize with coding standards and review criteria

SYNCHRONIZATION:
- Wait for explicit "proceed" message before dependent work
- Report readiness to orchestrator when preparation complete
- Coordinate through message queue for shared resources
- Escalate conflicts to orchestrator immediately"""
        
        return instructions
    
    def generate_context_limit_instructions(
        self,
        agent_name: str,
        context_used: int,
        context_budget: int
    ) -> str:
        """
        Generate instructions for handling context limits.
        
        Args:
            agent_name: Name of the agent
            context_used: Tokens used so far
            context_budget: Total token budget
            
        Returns:
            Context limit handling instructions
        """
        usage_percentage = (context_used / context_budget) * 100
        
        instructions = f"""CONTEXT LIMIT APPROACHING for {agent_name}

CURRENT STATUS:
- Context Used: {context_used:,} tokens
- Context Budget: {context_budget:,} tokens
- Usage: {usage_percentage:.1f}%

IMMEDIATE ACTIONS:
1. Complete current task if possible
2. Document all work completed so far
3. Prepare comprehensive handoff package
4. Identify remaining work items
5. Signal orchestrator for handoff

HANDOFF PREPARATION:
- Summary of completed work
- List of pending tasks with priorities
- Current state and context
- Any blockers or issues encountered
- Recommendations for next agent

CONTINUITY CHECKLIST:
□ All code changes committed
□ Documentation updated
□ Test results recorded
□ Design decisions documented
□ Dependencies identified
□ Next steps clearly defined"""
        
        return instructions
    
    def _get_default_mission(self, role: AgentRole) -> str:
        """Get default mission for a role."""
        default_missions = {
            AgentRole.ANALYZER: "Analyze requirements, design architecture, and create specifications",
            AgentRole.IMPLEMENTER: "Implement features according to specifications and standards",
            AgentRole.TESTER: "Create comprehensive tests and validate implementation",
            AgentRole.REVIEWER: "Review code for quality, security, and compliance"
        }
        return default_missions.get(role, f"Execute {role.value} responsibilities")
    
    def get_behavioral_rules(self, role: AgentRole) -> list[str]:
        """
        Get behavioral rules for a specific role.
        
        Args:
            role: Agent role
            
        Returns:
            List of behavioral rules
        """
        common_rules = [
            "Acknowledge all messages immediately upon reading",
            "Report progress to orchestrator regularly",
            "Ask orchestrator if scope questions arise",
            "Document all decisions with rationale",
            "Follow project standards strictly"
        ]
        
        role_specific_rules = {
            AgentRole.ANALYZER: [
                "Complete analysis before implementation begins",
                "Create detailed specifications",
                "Identify all dependencies upfront"
            ],
            AgentRole.IMPLEMENTER: [
                "Never expand scope beyond specifications",
                "Use symbolic editing for precision",
                "Test changes incrementally"
            ],
            AgentRole.TESTER: [
                "Test only implemented features",
                "Provide clear pass/fail status",
                "Document coverage metrics"
            ],
            AgentRole.REVIEWER: [
                "Focus on implemented changes only",
                "Provide constructive feedback",
                "Escalate major issues immediately"
            ]
        }
        
        rules = common_rules.copy()
        if role in role_specific_rules:
            rules.extend(role_specific_rules[role])
        
        return rules
    
    def generate_acknowledgment_instruction(self) -> str:
        """Generate standard message acknowledgment instruction."""
        return """MESSAGE ACKNOWLEDGMENT PROTOCOL:
- Acknowledge EVERY message immediately upon reading
- Use acknowledge_message() MCP tool for each message
- Process messages in order received
- Report acknowledgment failures to orchestrator
- Never proceed without acknowledging prior messages"""