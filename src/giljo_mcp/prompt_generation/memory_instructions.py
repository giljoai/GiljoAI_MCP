"""
Memory Instructions Generator for 360 Memory Context

Generates comprehensive instructions for orchestrators on how to:
1. Read and interpret 360 Memory history
2. Update product memory at project completion
3. Use the close_project_and_update_memory MCP tool
4. Leverage git history alongside 360 Memory

Used by MissionPlanner._extract_product_history() and integrated into
orchestrator context based on field priority levels.

Related Handovers:
- 0135-0139: 360 Memory Management backend
- 0268: 360 Memory Context Implementation
"""

import logging
from typing import Any, Dict, List, Optional


logger = logging.getLogger(__name__)


class MemoryInstructionGenerator:
    """
    Generates priority-aware instructions for orchestrators on 360 Memory usage.

    The 360 Memory system allows products to maintain a sequential history of
    project completions, storing learnings, decisions, and outcomes. This
    enables future projects to benefit from past experience.

    Priority Levels:
    - 0: Excluded (empty string returned)
    - 1-3: Minimal (instructions only, for first projects)
    - 4-6: Abbreviated (brief instructions with example)
    - 7-9: Moderate (detailed instructions with full example)
    - 10: Full (comprehensive guide with all details)
    """

    def generate_context(
        self, sequential_history: Optional[list[dict[str, Any]]], priority: int, git_enabled: bool = False
    ) -> str:
        """
        Generate memory instructions based on priority level.

        Args:
            sequential_history: List of project closeout entries from product_memory
            priority: Field priority (0-10) controlling detail level
            git_enabled: Whether GitHub integration is enabled

        Returns:
            Formatted markdown string with memory instructions, or empty string if priority=0
        """
        # Priority 0: Exclude entirely
        if priority == 0:
            return ""

        # Determine detail level
        detail_level = self._get_detail_level(priority)

        # If no history, provide instructions for first project
        if not sequential_history:
            return self._generate_first_project_instructions(detail_level, git_enabled)

        # Build instructions based on detail level
        if detail_level == "minimal":
            return self._generate_minimal_instructions(sequential_history, git_enabled)
        if detail_level == "abbreviated":
            return self._generate_abbreviated_instructions(sequential_history, git_enabled)
        if detail_level == "moderate":
            return self._generate_moderate_instructions(sequential_history, git_enabled)
        # full
        return self._generate_full_instructions(sequential_history, git_enabled)

    def _get_detail_level(self, priority: int) -> str:
        """
        Map priority (0-10) to detail level.

        Priority ranges:
        - 1-3: minimal
        - 4-6: abbreviated
        - 7-9: moderate
        - 10: full
        """
        if priority <= 3:
            return "minimal"
        if priority <= 6:
            return "abbreviated"
        if priority <= 9:
            return "moderate"
        return "full"

    def _generate_first_project_instructions(self, detail_level: str, git_enabled: bool) -> str:
        """
        Generate instructions for first project (no history).

        This is important to educate orchestrators about the 360 Memory system
        even when there's no prior history to reference.
        """
        sections = [
            "## 360 Memory System Overview",
            "",
            "This product has no project history yet. This is your first project!",
            "",
            "### What is 360 Memory?",
            "",
            "360 Memory is a knowledge base that captures learnings from completed projects.",
            "It stores:",
            "- Project summaries (what was accomplished)",
            "- Key outcomes (measurable results)",
            "- Decisions made (technical choices and rationale)",
            "- Git commits (if GitHub integration enabled)",
            "",
            "### Why Does It Exist?",
            "",
            "360 Memory helps future projects by:",
            "1. Avoiding repeated mistakes",
            "2. Building on successful patterns",
            "3. Maintaining architectural consistency",
            "4. Preserving important design decisions",
            "",
            "### Your Task - Update Memory After Completion",
            "",
            "When this project completes, you MUST call the MCP tool to persist learnings:",
            "",
            "```python",
            "# Close project and update 360 Memory",
            "close_project_and_update_memory(",
            '    project_id="<this_project_id>",',
            '    summary="Brief summary of what was accomplished",',
            "    key_outcomes=[",
            '        "Outcome 1 that was achieved",',
            '        "Outcome 2 that was measurable",',
            "    ],",
            "    decisions_made=[",
            '        "Technical decision 1 and why",',
            '        "Architecture choice and rationale",',
            "    ]",
            ")",
            "```",
            "",
            "### Git Integration",
            "",
        ]

        if git_enabled:
            sections.extend(
                [
                    "GitHub integration is ENABLED. Git commits will be automatically",
                    "captured and attached to your closeout summary.",
                ]
            )
        else:
            sections.extend(
                [
                    "GitHub integration is DISABLED. You'll need to manually include",
                    "important commit references in the summary.",
                ]
            )

        sections.extend(
            [
                "",
                "---",
                "",
                "After you complete this project, future projects in this product will",
                "benefit from your work through the 360 Memory system.",
            ]
        )

        return "\n".join(sections)

    def _generate_minimal_instructions(self, sequential_history: list[dict[str, Any]], git_enabled: bool) -> str:
        """
        Minimal instructions (priority 1-3): Brief overview.
        """
        sections = [
            "## 360 Memory - How to Update",
            "",
            "When your project completes, call the MCP tool:",
            "",
            "```python",
            "close_project_and_update_memory(",
            '    project_id="<project_id>",',
            '    summary="What was accomplished",',
            '    key_outcomes=["Outcome 1", "Outcome 2"],',
            '    decisions_made=["Decision 1", "Decision 2"]',
            ")",
            "```",
            "",
            f"This product has {len(sequential_history)} project(s) in history.",
            "Use past projects to inform your decisions.",
        ]

        return "\n".join(sections)

    def _generate_abbreviated_instructions(self, sequential_history: list[dict[str, Any]], git_enabled: bool) -> str:
        """
        Abbreviated instructions (priority 4-6): More detail than minimal.
        """
        sections = [
            "## 360 Memory - How It Works",
            "",
            f"This product has {len(sequential_history)} previous project(s) recorded.",
            "",
            "### When to Update Memory",
            "",
            "At project completion, call the close_project_and_update_memory MCP tool",
            "to save learnings for future projects.",
            "",
            "### What to Include",
            "",
            "**Summary**: Brief description of what was accomplished",
            "",
            "**Key Outcomes**: Measurable results achieved",
            "```python",
            'key_outcomes=["Feature X released", "Performance improved by Y%"]',
            "```",
            "",
            "**Decisions Made**: Important choices and their rationale",
            "```python",
            'decisions_made=["Chose library A because of B", "Implemented pattern X"]',
            "```",
            "",
            "### Example Call",
            "",
            "```python",
            "close_project_and_update_memory(",
            '    project_id="proj-abc123",',
            '    summary="Implemented authentication system with JWT and refresh tokens",',
            "    key_outcomes=[",
            '        "JWT authentication working in production",',
            '        "99.9% uptime in testing",',
            '        "Users can login within 500ms",',
            "    ],",
            "    decisions_made=[",
            '        "Selected bcrypt for password hashing (industry standard)",',
            '        "Used Redis for token blacklist (performance critical)",',
            '        "Implemented refresh token rotation for security",',
            "    ]",
            ")",
            "```",
        ]

        return "\n".join(sections)

    def _generate_moderate_instructions(self, sequential_history: list[dict[str, Any]], git_enabled: bool) -> str:
        """
        Moderate instructions (priority 7-9): Comprehensive with examples.
        """
        sections = [
            "## 360 Memory - Complete Usage Guide",
            "",
            f"This product has {len(sequential_history)} previous project(s) in history.",
            "",
            "### Understanding 360 Memory",
            "",
            "360 Memory is a structured knowledge base that preserves project learnings.",
            "Each completed project adds to the product's institutional knowledge.",
            "",
            "**Why This Matters:**",
            "- Future projects learn from past decisions",
            "- Architectural consistency is maintained",
            "- Repeated mistakes are avoided",
            "- Successful patterns are reinforced",
            "",
            "### When to Update Memory",
            "",
            "Call close_project_and_update_memory() at project completion, including:",
            "",
            "1. **Project Summary** - What did you build? What problem did it solve?",
            "2. **Key Outcomes** - What measurable results were achieved?",
            "3. **Decisions Made** - What important choices were made? Why?",
            "4. **Git Integration** - Commits automatically captured (if enabled)",
            "",
            "### Detailed Example",
            "",
            "```python",
            "close_project_and_update_memory(",
            '    project_id="proj-auth-2025",',
            '    summary="""',
            "    Implemented multi-factor authentication (MFA) system with TOTP support.",
            "    Integrated with existing JWT authentication. Added recovery codes for",
            "    account lockout scenarios. Achieved 99.5% uptime in staging.",
            '    """,',
            "    key_outcomes=[",
            '        "MFA working with Google Authenticator and Authy",',
            '        "Recovery codes prevent account lockout",',
            '        "Setup time reduced to <2 minutes per user",',
            '        "99.5% uptime achieved in testing",',
            '        "Security audit passed with no critical findings",',
            "    ],",
            "    decisions_made=[",
            '        "Selected TOTP over SMS (better security, no carrier costs)",',
            '        "Implemented recovery codes (prevents lockout)",',
            '        "Stored secret encrypted in database (zero knowledge)",',
            '        "Rate limited auth attempts to prevent brute force",',
            '        "Chose HMAC-SHA1 (industry standard for TOTP)",',
            "    ]",
            ")",
            "```",
            "",
            "### How Future Projects Benefit",
            "",
            "When the next project runs, it will:",
            "1. See your project summary in context",
            "2. Learn from your decisions and outcomes",
            "3. Avoid repeating what didn't work",
            "4. Build on what succeeded",
            "",
            "### Git Integration",
            "",
        ]

        if git_enabled:
            sections.extend(
                [
                    "GitHub integration is ENABLED.",
                    "Git commits are automatically attached to your closeout.",
                    "Include commit references in your summary for clarity.",
                ]
            )
        else:
            sections.extend(
                [
                    "GitHub integration is DISABLED.",
                    "Manually reference important commits in your summary.",
                ]
            )

        sections.extend(
            [
                "",
                "### Pro Tips",
                "",
                "- Be specific in decisions (explain the 'why', not just the 'what')",
                "- Include measurable outcomes (numbers matter)",
                "- Reference outcomes that impact future projects",
                "- Preserve architectural patterns and choices",
            ]
        )

        return "\n".join(sections)

    def _generate_full_instructions(self, sequential_history: list[dict[str, Any]], git_enabled: bool) -> str:
        """
        Full instructions (priority 10): Most comprehensive guide.
        """
        sections = [
            "## 360 Memory - Comprehensive Knowledge Management",
            "",
            f"Product History: {len(sequential_history)} completed project(s)",
            "",
            "### System Overview",
            "",
            "360 Memory is the product's memory system. It captures learnings from",
            "every completed project, creating a knowledge base that informs future work.",
            "",
            "Each project closure documents:",
            "- What was built and why",
            "- Measurable outcomes achieved",
            "- Technical decisions and their rationale",
            "- Git history (if integrated with GitHub)",
            "",
            "### Project Lifecycle and Memory",
            "",
            "**Planning Phase**: Review 360 Memory to understand past approaches",
            "- Check what patterns were successful",
            "- Identify architectural standards used",
            "- Learn from past decision rationale",
            "",
            "**Execution Phase**: Execute the project",
            "- Follow patterns established in past projects",
            "- Document important decisions as you make them",
            "- Measure outcomes as specified",
            "",
            "**Closeout Phase**: Update 360 Memory",
            "- Call close_project_and_update_memory with your learnings",
            "- Preserve decisions for future reference",
            "- Enable future projects to benefit",
            "",
            "### Detailed Example - Complex Project",
            "",
            "Here's a comprehensive example with all fields populated:",
            "",
            "```python",
            "close_project_and_update_memory(",
            '    project_id="proj-payment-gateway-2025",',
            '    summary="""',
            "    Implemented Stripe payment gateway integration with full refund,",
            "    subscription, and webhook handling. Built custom admin dashboard",
            "    for payment reconciliation. Achieved PCI DSS compliance.",
            "    ",
            "    Challenges overcome:",
            "    - Stripe webhook race conditions (solved with idempotency keys)",
            "    - Currency conversion complexity (implemented caching strategy)",
            "    - Refund reconciliation at scale (built batch processing system)",
            "    ",
            "    Final metrics: 99.99% uptime, <100ms gateway response time,",
            "    zero data loss in 3 months of production.",
            '    """,',
            "    key_outcomes=[",
            '        "Stripe integration 100% working with all payment methods",',
            '        "Subscription management with automated billing cycles",',
            '        "Webhook handling with 99.99% uptime",',
            '        "PCI DSS compliance achieved and audited",',
            '        "Payment reconciliation <2 hours for millions in transactions",',
            '        "Customer refunds processed within 30 seconds",',
            '        "Reduced payment failures from 0.5% to 0.02%",',
            '        "Admin dashboard processes 500+ reconciliations/day",',
            "    ],",
            "    decisions_made=[",
            '        "Selected Stripe over alternatives: best API, 24/7 support",',
            '        "Used idempotency keys for webhook safety (prevents duplicates)",',
            '        "Implemented cache for exchange rates (reduced API calls 80%)",',
            '        "Built custom reconciliation (vs using Stripe Reports, cheaper)",',
            '        "Chose PostgreSQL JSON for webhook audit trail (audit required)",',
            '        "Implemented batch refunds (process at 2 AM during low traffic)",',
            '        "Rate limited refund API (prevent abuse, customer feedback)",',
            '        "Encrypted sensitive payment data at rest (PCI requirement)",',
            "    ]",
            ")",
            "```",
            "",
            "### Memory-Driven Development",
            "",
            "**Before Each Sprint:**",
            "1. Review relevant 360 Memory entries",
            "2. Check what patterns were successful in past projects",
            "3. Review decisions that apply to your current work",
            "4. Identify what NOT to repeat",
            "",
            "**During Development:**",
            "1. Make decisions consciously (they'll be in memory)",
            "2. Document your approach for future teams",
            "3. Measure outcomes as you go",
            "4. Track important trade-offs made",
            "",
            "**At Completion:**",
            "1. Synthesize learnings into clear summary",
            "2. List measurable outcomes (with numbers)",
            "3. Explain important decisions and their rationale",
            "4. Close via MCP tool call",
            "",
            "### Decision Quality",
            "",
            "Good decision documentation includes:",
            "- What was chosen",
            "- Why this choice was made",
            "- What alternatives were considered",
            "- Trade-offs that matter to future projects",
            "",
            "Example of excellent decision documentation:",
            "```",
            "Used Redis for session storage because: (1) Sub-millisecond response",
            "times needed for auth on every request, (2) Memcached considered but",
            "no persistence, (3) Postgres too slow at scale, (4) TTL feature built",
            "in for automatic cleanup",
            "```",
            "",
            "### Git Integration",
            "",
        ]

        if git_enabled:
            sections.extend(
                [
                    "GitHub integration is FULLY ENABLED.",
                    "Git commits are automatically captured and linked to your closeout.",
                    "",
                    "The system will:",
                    "- Fetch commits from your configured branch",
                    "- Attach them to the project memory entry",
                    "- Make them searchable alongside your decisions",
                    "- Include them in future project context",
                ]
            )
        else:
            sections.extend(
                [
                    "GitHub integration is currently DISABLED.",
                    "You can enable it in settings to auto-capture commits.",
                    "",
                    "To maximize value without GitHub:",
                    "- Reference commit SHAs in your summary",
                    "- Link to important pull requests",
                    "- Document major code changes",
                ]
            )

        sections.extend(
            [
                "",
                "### Best Practices",
                "",
                "**On Summaries:**",
                "- 2-3 paragraphs is ideal",
                "- Include metrics and numbers",
                "- Highlight unexpected challenges",
                "- Reference architecture or patterns used",
                "",
                "**On Outcomes:**",
                "- Be specific and measurable",
                "- Include both technical and business metrics",
                "- List problems solved",
                "- Include adoption/usage statistics if relevant",
                "",
                "**On Decisions:**",
                "- Include the 'why' not just the 'what'",
                "- Reference alternatives considered",
                "- Note trade-offs (performance vs maintainability, etc.)",
                "- Link to standards or patterns followed",
                "",
                "### Retrieving Memory",
                "",
                "Future projects will automatically see your entries when they run.",
                "Your decisions, outcomes, and patterns become context for them.",
                "Orchestrators will cite specific learnings when making recommendations.",
                "",
                "### Memory Retention",
                "",
                f"This product will preserve all {len(sequential_history)} project memories indefinitely.",
                "They form the institutional knowledge of the product.",
            ]
        )

        return "\n".join(sections)
