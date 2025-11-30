"""
SerenaInstructionGenerator - Generate Serena MCP usage instructions

Provides comprehensive, token-optimized instructions for using Serena MCP tools.
Serena saves 80-90% tokens by enabling symbolic navigation and search instead of
reading entire files.

Key Features:
- Token-efficient instructions with caching
- Agent-type specific guidance (implementer, tester, architect, documenter)
- Multiple detail levels (minimal, summary, full)
- Clear usage patterns and best practices
- Conditional generation based on serena_mcp.enabled config

Handover 0267: Serena MCP Integration Instructions
"""

import logging
from pathlib import Path
from typing import Optional
from datetime import datetime
import yaml

logger = logging.getLogger(__name__)


class SerenaInstructionGenerator:
    """Generate Serena MCP usage instructions for orchestrators and agents."""

    # Cache for generated instructions to avoid regeneration
    _instruction_cache: dict[str, str] = {}

    # Serena MCP tools organized by category
    SERENA_TOOLS = {
        "Navigation": {
            "get_symbols_overview": {
                "tool": "mcp__serena__get_symbols_overview",
                "purpose": "Get high-level view of symbols in a file (classes, methods, functions)",
                "usage": "Use FIRST to understand file structure before diving deeper",
                "example": 'await get_symbols_overview(relative_path="src/app.py")',
            },
            "find_symbol": {
                "tool": "mcp__serena__find_symbol",
                "purpose": "Find specific symbol by name path (classes, methods, fields)",
                "usage": "Use to locate exact code to read or modify",
                "example": 'await find_symbol(name_path_pattern="MyClass/method_name", relative_path="src/", include_body=True)',
            },
            "find_referencing_symbols": {
                "tool": "mcp__serena__find_referencing_symbols",
                "purpose": "Find all places where a symbol is used",
                "usage": "Use before refactoring to understand impact",
                "example": 'await find_referencing_symbols(name_path="MyClass/old_method", relative_path="src/app.py")',
            },
        },
        "Search": {
            "search_for_pattern": {
                "tool": "mcp__serena__search_for_pattern",
                "purpose": "Search files with regex patterns and get line numbers",
                "usage": "Use for pattern-based discovery (e.g., find all async functions)",
                "example": 'await search_for_pattern(substring_pattern="async def.*handler", relative_path="src/")',
            },
            "list_dir": {
                "tool": "mcp__serena__list_dir",
                "purpose": "List files and directories with optional recursion",
                "usage": "Use to understand project structure without full tree scan",
                "example": 'await list_dir(relative_path="src/components", recursive=True)',
            },
            "find_file": {
                "tool": "mcp__serena__find_file",
                "purpose": "Find files matching glob patterns (*.py, *.ts, etc)",
                "usage": "Use to locate files by name or extension quickly",
                "example": 'await find_file(file_mask="*.py", relative_path="tests/")',
            },
        },
        "Modification": {
            "replace_symbol_body": {
                "tool": "mcp__serena__replace_symbol_body",
                "purpose": "Replace entire symbol body (function, method, class)",
                "usage": "Use for clean, surgical code changes at symbol level",
                "example": 'await replace_symbol_body(name_path="MyClass/method", relative_path="src/app.py", body="def method():\\n    return 42")',
            },
            "insert_before_symbol": {
                "tool": "mcp__serena__insert_before_symbol",
                "purpose": "Insert code before a symbol definition",
                "usage": "Use to add imports, decorators, or preceding code",
                "example": 'await insert_before_symbol(name_path="MyClass", relative_path="src/app.py", body="# Important decorator\\n@new_decorator\\n")',
            },
            "insert_after_symbol": {
                "tool": "mcp__serena__insert_after_symbol",
                "purpose": "Insert code after a symbol definition",
                "usage": "Use to add methods after a class, functions after imports",
                "example": 'await insert_after_symbol(name_path="MyClass", relative_path="src/app.py", body="\\ndef new_function():\\n    pass")',
            },
            "rename_symbol": {
                "tool": "mcp__serena__rename_symbol",
                "purpose": "Rename symbol throughout entire codebase",
                "usage": "Use for safe refactoring across all references",
                "example": 'await rename_symbol(name_path="old_function", relative_path="src/utils.py", new_name="new_function")',
            },
        },
        "Analysis": {
            "think_about_collected_information": {
                "tool": "mcp__serena__think_about_collected_information",
                "purpose": "Reflect on collected code information before implementing",
                "usage": "Use after exploration to ensure you have complete picture",
                "example": "Use when you've collected multiple files and need to assess",
            },
            "think_about_task_adherence": {
                "tool": "mcp__serena__think_about_task_adherence",
                "purpose": "Verify you're still on track with task requirements",
                "usage": "Use before making code changes to confirm alignment",
                "example": "Use before implementing to ensure you understand the requirement",
            },
            "think_about_whether_you_are_done": {
                "tool": "mcp__serena__think_about_whether_you_are_done",
                "purpose": "Verify task completion before declaring done",
                "usage": "Use at end of task to confirm all requirements met",
                "example": "Use when implementation appears complete",
            },
        },
        "Memory": {
            "write_memory": {
                "tool": "mcp__serena__write_memory",
                "purpose": "Store structured information about project for future tasks",
                "usage": "Use to document discoveries (patterns, architecture, conventions)",
                "example": 'await write_memory(memory_file_name="project_architecture", content="...detailed notes...")',
            },
            "read_memory": {
                "tool": "mcp__serena__read_memory",
                "purpose": "Retrieve previously stored project information",
                "usage": "Use to quickly get context from previous work",
                "example": 'await read_memory(memory_file_name="project_architecture")',
            },
        },
    }

    async def generate_instructions(
        self, enabled: bool = True, detail_level: str = "full"
    ) -> str:
        """
        Generate Serena MCP usage instructions.

        Args:
            enabled: Whether Serena MCP is enabled in config
            detail_level: 'minimal', 'summary', or 'full' level of detail

        Returns:
            Formatted instructions string
        """
        # Check cache first
        cache_key = f"serena_instructions_{enabled}_{detail_level}"
        if cache_key in self._instruction_cache:
            logger.debug(f"[SERENA] Cache hit for {cache_key}")
            return self._instruction_cache[cache_key]

        if not enabled:
            instructions = self._generate_disabled_message()
        elif detail_level == "minimal":
            instructions = self._generate_minimal_instructions()
        elif detail_level == "summary":
            instructions = self._generate_summary_instructions()
        else:  # full
            instructions = self._generate_full_instructions()

        # Cache the result
        self._instruction_cache[cache_key] = instructions
        logger.info(
            f"[SERENA] Generated {detail_level} instructions ({len(instructions)} chars)",
            extra={"detail_level": detail_level, "enabled": enabled},
        )

        return instructions

    async def generate_for_agent(
        self, enabled: bool = True, agent_type: str = "implementer"
    ) -> str:
        """
        Generate agent-specific Serena instructions.

        Args:
            enabled: Whether Serena MCP is enabled
            agent_type: Type of agent ('implementer', 'tester', 'architect', 'documenter')

        Returns:
            Agent-specific instructions
        """
        if not enabled:
            return self._generate_disabled_message()

        # Agent-specific detail levels
        detail_map = {
            "implementer": "full",  # Full instructions for code writers
            "tester": "summary",  # Summary for test writers
            "architect": "full",  # Full for design/architecture work
            "documenter": "summary",  # Summary for documentation
            "orchestrator": "full",  # Full for orchestrators
        }

        detail_level = detail_map.get(agent_type, "summary")
        instructions = await self.generate_instructions(enabled=True, detail_level=detail_level)

        # Add agent-specific guidance
        agent_guidance = self._get_agent_specific_guidance(agent_type)
        return instructions + "\n\n" + agent_guidance

    def _generate_disabled_message(self) -> str:
        """Generate minimal message when Serena is disabled."""
        return """
## Serena MCP Not Available

Serena code navigation tools are not currently enabled in this environment.
For token-efficient code exploration, consider enabling Serena MCP in Settings.
"""

    def _generate_minimal_instructions(self) -> str:
        """Generate minimal Serena instructions (for spawned agents)."""
        return """
## Serena MCP - Code Navigation Tools

Serena is available for token-efficient code exploration:

**Navigation Tools:**
- `mcp__serena__get_symbols_overview` - Quick file structure overview
- `mcp__serena__find_symbol` - Find specific code by name
- `mcp__serena__search_for_pattern` - Pattern-based search

**Key Benefit:** Avoid reading entire files (80-90% token savings)

**Usage Pattern:**
1. Use `get_symbols_overview` to understand file structure
2. Use `find_symbol` to locate exact code to read
3. Read only what you need with targeted access

See full documentation in agent mission for complete tool list.
"""

    def _generate_summary_instructions(self) -> str:
        """Generate summary-level Serena instructions."""
        return """
## Serena MCP - Code Navigation & Search Tools

Serena provides token-efficient code exploration by enabling **symbolic navigation** and **pattern search**
instead of reading entire files. This saves **80-90% tokens** compared to full file reads.

### Key Principle

**Structure → Navigate → Search**
- First, understand code STRUCTURE with `get_symbols_overview`
- Then NAVIGATE to specific symbols with `find_symbol`
- Finally SEARCH with patterns for discovery

### Essential Tools

**Navigation** (Understand & Locate):
- `mcp__serena__get_symbols_overview(relative_path)` - View all symbols in a file
- `mcp__serena__find_symbol(name_path_pattern, relative_path, include_body)` - Locate code
- `mcp__serena__find_referencing_symbols(name_path, relative_path)` - Find usage

**Search** (Discover & Analyze):
- `mcp__serena__search_for_pattern(substring_pattern, relative_path)` - Pattern matching
- `mcp__serena__list_dir(relative_path, recursive)` - Directory structure
- `mcp__serena__find_file(file_mask, relative_path)` - File discovery

**Modification** (Safe Editing):
- `mcp__serena__replace_symbol_body(name_path, relative_path, body)` - Update code
- `mcp__serena__insert_before_symbol(name_path, relative_path, body)` - Insert before
- `mcp__serena__insert_after_symbol(name_path, relative_path, body)` - Insert after
- `mcp__serena__rename_symbol(name_path, relative_path, new_name)` - Safe refactoring

### Token Savings Example

**INCORRECT** (reads entire file - 1000+ tokens):
```python
# Reading full file content
with open('src/models.py') as f:
    content = f.read()  # Might be 100KB+ of code
# Then searching through it manually
```

**CORRECT** (uses Serena - 100-200 tokens):
```python
# 1. Get overview (shows all symbols)
symbols = await get_symbols_overview('src/models.py')
# 2. Find exact symbol
user_class = await find_symbol(
    name_path_pattern='User',
    relative_path='src/models.py',
    include_body=True  # Only read what you need
)
```

### Usage Pattern

1. **Explore**: Use `get_symbols_overview` to understand file structure
2. **Locate**: Use `find_symbol` with depth to traverse code hierarchy
3. **Search**: Use `search_for_pattern` for pattern-based discovery
4. **Modify**: Use symbol editing tools for surgical code changes

Always prefer symbolic tools over full file reads. The time saved in token budget
translates to deeper analysis and better implementation quality.
"""

    def _generate_full_instructions(self) -> str:
        """Generate comprehensive Serena MCP instructions."""
        instructions = """
## Serena MCP - Comprehensive Code Navigation & Search System

Serena is a powerful symbol-aware code exploration system that enables **80-90% token savings**
compared to reading entire files. Use Serena's semantic tools instead of generic file operations.

### What is Serena?

Serena provides **semantic code navigation** - you can ask it to find specific classes, methods,
functions, or patterns without reading files line-by-line. This is orders of magnitude more
token-efficient than full file reads.

**Token Comparison:**
- Full file read (100KB code): 25,000+ tokens
- Serena symbol search: 100-500 tokens
- Token savings: 98%+

### Core Principles

**1. Structure First**
Always start by understanding the CODE STRUCTURE before diving into details:
- Use `get_symbols_overview` to see all top-level symbols in a file
- Shows classes, functions, fields, imports, etc.
- Gives you the "map" of the code

**2. Navigate Semantically**
Use symbolic navigation, not string searching:
- `find_symbol` understands code relationships
- Shows you exact location and context
- Can traverse class hierarchies with depth parameter

**3. Search Intelligently**
Use patterns for discovery when you don't know exact names:
- `search_for_pattern` uses regex for flexible matching
- Shows line numbers and context
- Restrict to specific file types or directories

**4. Modify Surgically**
Make precise code changes at symbol level:
- `replace_symbol_body` replaces entire function/class
- `insert_before_symbol` / `insert_after_symbol` for additions
- `rename_symbol` for safe refactoring across codebase

### Complete Tool Reference

"""
        # Add all tools organized by category
        for category, tools in self.SERENA_TOOLS.items():
            instructions += f"\n#### {category} Tools\n\n"
            for tool_name, tool_info in tools.items():
                instructions += f"**{tool_info['tool']}**\n"
                instructions += f"- **Purpose:** {tool_info['purpose']}\n"
                if "usage" in tool_info:
                    instructions += f"- **Usage:** {tool_info['usage']}\n"
                if "example" in tool_info:
                    instructions += f"- **Example:**\n```python\n{tool_info['example']}\n```\n"
                instructions += "\n"

        instructions += """
### Best Practices

#### CORRECT - Token-Efficient Approaches

```python
# 1. Overview first to understand structure
symbols = await get_symbols_overview(relative_path='src/models.py')

# 2. Find specific symbol with body
result = await find_symbol(
    name_path_pattern='User/validate',
    relative_path='src/models.py',
    include_body=True,  # Only read the method body
    depth=0
)

# 3. Search for patterns
matches = await search_for_pattern(
    substring_pattern='class.*Repository',
    relative_path='src/repositories/'
)

# 4. Modify with surgical precision
await replace_symbol_body(
    name_path='User/validate',
    relative_path='src/models.py',
    body='def validate(self):\\n    return self.email is not None'
)
```

#### INCORRECT - Token-Wasteful Approaches

```python
# DON'T: Read entire file
with open('src/models.py') as f:
    content = f.read()  # Wasteful!

# DON'T: Use grep-like tools without path restriction
results = await search_for_pattern('def ')  # Searches entire codebase!

# DON'T: Use include_body without checking if you need it
result = await find_symbol(
    name_path_pattern='User',
    include_body=True,  # Reads entire class if you only need location
    depth=10  # Includes all descendants unnecessarily
)
```

### Agent-Specific Guidance

#### For Implementers (Code Writers)
- Use full instructions for all tool categories
- Combine navigation + modification tools
- Use `find_referencing_symbols` before refactoring
- Use `write_memory` to document patterns discovered

#### For Testers (Test Writers)
- Focus on navigation tools (find_symbol, search_for_pattern)
- Use `find_referencing_symbols` to understand code flow
- Use `get_symbols_overview` for test coverage planning
- Less modification; mostly reading and understanding

#### For Architects (Design & Planning)
- Use `get_symbols_overview` for system structure
- Use `find_symbol` with high depth to understand hierarchies
- Use `search_for_pattern` for design pattern discovery
- Use `write_memory` to document architecture decisions

#### For Documenters (Documentation Writers)
- Focus on navigation and memory tools
- Use `read_memory` to access previous discoveries
- Use `get_symbols_overview` for API documentation
- Use `find_symbol` to understand public interfaces

### Workflow Example: Adding a New Feature

```python
# 1. Understand current structure
overview = await get_symbols_overview(relative_path='src/services/')

# 2. Find related classes
user_service = await find_symbol(
    name_path_pattern='UserService',
    relative_path='src/services/',
    include_body=True
)

# 3. Find all references to understand usage
references = await find_referencing_symbols(
    name_path='UserService',
    relative_path='src/'
)

# 4. Search for similar patterns to follow conventions
patterns = await search_for_pattern(
    substring_pattern='async def.*validate',
    relative_path='src/',
    restrict_search_to_code_files=True
)

# 5. Implement your change surgically
await insert_after_symbol(
    name_path='UserService',
    relative_path='src/services/user.py',
    body='\\n    async def new_method(self):\\n        pass'
)

# 6. Document your discovery
await write_memory(
    memory_file_name='feature_implementation_notes',
    content='Added new_method to UserService following pattern: ...'
)
```

### Tips for Maximum Token Efficiency

1. **Always use overview first** - Understand structure before diving deep
2. **Restrict search scope** - Use `relative_path` to limit searches
3. **Use depth strategically** - Set `depth=1` to get immediate children only
4. **Combine with think tools** - Use reflection tools to verify understanding
5. **Cache results in memory** - Write discoveries to project memory
6. **Use file type filters** - Restrict searches to relevant file types
7. **Leverage symbol information** - Extract what you need from symbol metadata

### Performance Characteristics

| Operation | Tokens | Time | Best For |
|-----------|--------|------|----------|
| Full file read | 5,000-25,000 | Slow | Never (use Serena instead) |
| get_symbols_overview | 100-300 | Fast | Understanding structure |
| find_symbol | 100-500 | Fast | Locating specific code |
| search_for_pattern | 200-800 | Medium | Discovery & analysis |
| find_referencing_symbols | 500-2,000 | Medium | Impact analysis |
| replace_symbol_body | 500-1,500 | Medium | Safe modifications |

### Integration with Project Context

Serena integrates with GiljoAI's context management system:
- Serena tool recommendations are included in orchestrator missions
- Agent-specific Serena guidance is provided in spawned agent instructions
- Serena tool usage is tracked for performance monitoring
- Memory system stores discoveries for reuse across tasks

### Common Patterns by Language

**Python:**
```python
# Find class definitions
await find_symbol(name_path_pattern='MyClass', include_body=False)

# Find async functions
await search_for_pattern(substring_pattern='async def', restrict_search_to_code_files=True)

# Navigate class methods
await find_symbol(name_path_pattern='MyClass', relative_path='src/', depth=1)
```

**TypeScript/JavaScript:**
```python
# Find interfaces
await search_for_pattern(substring_pattern='interface \\w+', glob='*.ts')

# Find class declarations
await find_symbol(name_path_pattern='MyClass', relative_path='src/')

# Find type exports
await search_for_pattern(substring_pattern='export type', glob='**/*.ts')
```

**Go:**
```python
# Find function definitions
await search_for_pattern(substring_pattern='func \\(', glob='*.go')

# Find interface implementations
await find_referencing_symbols(name_path='Reader', relative_path='src/')
```

### Troubleshooting

**"Tool not found" error:**
- Ensure tool name includes `mcp__serena__` prefix
- Check tool is spelled correctly
- Verify Serena MCP is enabled in config

**"Path not found" error:**
- Use relative paths from project root (e.g., 'src/app.py' not '/home/.../src/app.py')
- Verify file/directory exists in project
- Check gitignore doesn't exclude the path

**"Symbol not found" error:**
- Use `get_symbols_overview` first to verify symbol exists
- Check name_path pattern matches symbol naming conventions
- Try substring_matching=True if pattern doesn't match exactly

**Performance is slow:**
- Restrict searches with `relative_path` and `glob` parameters
- Avoid high `depth` values unless needed
- Cache results in memory for reuse

### Advanced Techniques

**Symbol Hierarchy Navigation:**
```python
# Navigate class hierarchy
class_symbols = await find_symbol(
    name_path_pattern='MyClass',
    relative_path='src/',
    depth=1  # Get immediate children (methods)
)

# Then navigate deeper
method_details = await find_symbol(
    name_path_pattern='MyClass/my_method',
    relative_path='src/',
    include_body=True
)
```

**Multi-Step Refactoring:**
```python
# 1. Find all references
refs = await find_referencing_symbols(
    name_path='old_name',
    relative_path='src/'
)

# 2. Check each reference context
for ref in refs:
    # Review snippet context

# 3. Safe rename across codebase
await rename_symbol(
    name_path='old_name',
    relative_path='src/module.py',
    new_name='new_name'
)
```

### Conclusion

Serena transforms code exploration from slow, token-heavy file reading to fast,
precise symbolic navigation. By following the Structure → Navigate → Search pattern,
you can achieve **80-90% token savings** while actually improving code understanding
and implementation quality.

Always ask: "Can I use a Serena tool instead of reading the file?"

The answer is almost always yes.
"""

        return instructions

    def _get_agent_specific_guidance(self, agent_type: str) -> str:
        """Get agent-specific guidance for using Serena."""
        guidance_map = {
            "implementer": """
### Implementer-Specific Guidance

Your role is to write production-grade code. Serena enables you to understand
complex codebases quickly and make surgical modifications.

**Key Workflow:**
1. Use `get_symbols_overview` to understand overall structure
2. Use `find_symbol` to locate code to modify
3. Use `find_referencing_symbols` BEFORE refactoring to understand impact
4. Use symbol modification tools for precise code changes
5. Use `search_for_pattern` to find similar code for consistency

**Tools You'll Use Most:**
- `find_symbol` with `include_body=True` for reading code
- `replace_symbol_body` for implementing changes
- `find_referencing_symbols` for impact analysis
- `rename_symbol` for safe refactoring
- `insert_before_symbol` / `insert_after_symbol` for additions

**Tips:**
- Always check references before renaming or removing code
- Use memory to document conventions discovered
- Follow existing patterns in the codebase
- Test your changes thoroughly before declaring complete
""",
            "tester": """
### Tester-Specific Guidance

Your role is to ensure code quality through testing. Serena helps you understand
code structure and coverage requirements.

**Key Workflow:**
1. Use `get_symbols_overview` to understand code structure
2. Use `find_symbol` to understand functions/classes to test
3. Use `find_referencing_symbols` to understand code flow
4. Use `search_for_pattern` to find similar test patterns

**Tools You'll Use Most:**
- `get_symbols_overview` for coverage planning
- `find_symbol` for understanding code behavior
- `search_for_pattern` to find existing test patterns
- `find_referencing_symbols` to trace code flow

**Tips:**
- Look at existing tests for patterns and conventions
- Understand the full code path before writing tests
- Use memory to document edge cases discovered
- Test both happy paths and error conditions
""",
            "architect": """
### Architect-Specific Guidance

Your role is to design systems and ensure architectural integrity. Serena helps
you understand complex systems and design patterns.

**Key Workflow:**
1. Use `get_symbols_overview` on key modules to understand system structure
2. Use `find_symbol` with high depth to understand hierarchies
3. Use `search_for_pattern` to identify design patterns
4. Use `find_referencing_symbols` to understand dependencies
5. Use `write_memory` to document architectural decisions

**Tools You'll Use Most:**
- `get_symbols_overview` for system structure analysis
- `find_symbol` with `depth>1` to understand hierarchies
- `search_for_pattern` for design pattern discovery
- `write_memory` for documenting architecture

**Tips:**
- Document your architectural discoveries in memory
- Look for design patterns in existing code
- Understand dependency flows before proposing changes
- Consider scalability and maintenance in designs
""",
            "documenter": """
### Documenter-Specific Guidance

Your role is to document code and systems. Serena helps you quickly understand
public APIs and code structure.

**Key Workflow:**
1. Use `get_symbols_overview` to understand module exports
2. Use `find_symbol` to understand public interfaces
3. Use `search_for_pattern` to find examples
4. Use `read_memory` to access previous discoveries
5. Use `write_memory` to store documentation findings

**Tools You'll Use Most:**
- `get_symbols_overview` for public API discovery
- `find_symbol` for understanding function signatures
- `search_for_pattern` for finding usage examples
- `read_memory` to access related documentation

**Tips:**
- Focus on public interfaces, not implementation details
- Find existing examples in tests and usage
- Document use cases and common patterns
- Store findings in memory for consistency
""",
            "orchestrator": """
### Orchestrator-Specific Guidance

Your role is to coordinate specialized agents. Use Serena to understand project
structure and agent capabilities.

**Key Workflow:**
1. Use `get_symbols_overview` to quickly understand project structure
2. Use `find_symbol` to locate key components
3. Use `search_for_pattern` for discovery tasks
4. Use `write_memory` to document findings for spawned agents
5. Use `read_memory` to access shared context

**Tools You'll Use Most:**
- `get_symbols_overview` for rapid structure understanding
- `find_symbol` for key component location
- `search_for_pattern` for discovery
- `write_memory` for context sharing with agents
- `read_memory` for accessing shared knowledge

**Tips:**
- Document project structure in memory
- Share architectural understanding with spawned agents
- Use pattern discovery for finding similar implementations
- Reference previous discoveries to save time
""",
        }

        return guidance_map.get(
            agent_type,
            """
### Agent-Specific Guidance

Use Serena's navigation tools to understand code structure and implement your task.
Follow the Structure → Navigate → Search pattern for token efficiency.
""",
        )

    @classmethod
    def clear_cache(cls) -> None:
        """Clear instruction cache (useful for testing)."""
        cls._instruction_cache.clear()
        logger.info("[SERENA] Instruction cache cleared")
