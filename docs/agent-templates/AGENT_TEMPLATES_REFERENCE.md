# Agent Templates Reference - GiljoAI MCP

**Location**: `src/giljo_mcp/template_manager.py` (lines 146-550)
**Status**: Production-ready agent templates for multi-agent orchestration
**Last Updated**: 2025-01-05 (Harmonized)
**Harmonization Status**: ✅ Aligned with codebase

---

## Quick Links to Harmonized Documents

- **[Simple_Vision.md](../handovers/Simple_Vision.md)** - User journey & agent template explanation
- **[start_to_finish_agent_FLOW.md](../handovers/start_to_finish_agent_FLOW.md)** - Technical verification

**Current Default Agent Templates** (verified):
- **6 templates seeded per tenant**: orchestrator, implementer, tester, analyzer, reviewer, documenter
- **Seeding trigger**: First user creation (auth.py:910)
- **Source**: `src/giljo_mcp/template_seeder.py::_get_default_templates_v103()`
- **Colors**: Each template has unique background_color for UI display
  - orchestrator: #D4A574, implementer: #3498DB, tester: #FFC300
  - analyzer: #E74C3C, reviewer: #9B59B6, documenter: #27AE60

**Agent Template Export** (Handover 0102):
- 15-minute token TTL for secure downloads
- Supports Claude Code, Codex CLI, Gemini CLI
- See Simple_Vision.md for complete export workflow

---

## Overview

The GiljoAI MCP system includes **6 pre-generated agent templates** for coordinated multi-agent software development. These templates are loaded by the `UnifiedTemplateManager` class and stored in the `_legacy_templates` dictionary.

## Agent Template Types

### 1. Orchestrator (Project Manager)
**Role**: Project Manager & Team Lead
**File Location**: `template_manager.py` lines 152-408

**Key Responsibilities**:
- Project coordination through delegation (NOT implementation)
- Vision document guardian
- Scope sheriff (enforces 3-tool rule)
- Strategic architect
- Progress tracker

**The 30-80-10 Principle**:
- 30% Discovery (Serena MCP exploration, vision reading, config review)
- 80% Delegation (spawn agents, coordinate, monitor)
- 10% Closure (create 3 documentation artifacts)

**The 3-Tool Rule**:
- If using >3 tools for implementation → STOP and delegate
- Examples:
  - ❌ WRONG: orchestrator reads file → edits file → runs tests → commits (4 tools)
  - ✅ CORRECT: orchestrator spawns implementer → monitors progress

**Discovery Workflow**:
1. **Serena MCP First** (primary intelligence)
   - `list_dir()` → Find recent learnings
   - `search_for_pattern()` → Find pain points
   - `get_symbols_overview()` → Understand structure
   - `find_symbol()` → Locate implementations

2. **Vision Document** (complete reading)
   - `get_vision_index()` → Get structure
   - `get_vision(part=N)` → Read ALL parts

3. **Product Settings**
   - `get_product_settings()` → Tech config

4. **Create Specific Missions**
   - Reference specific files/lines
   - Include vision principles
   - Define success criteria

**Project Closure** (3 mandatory artifacts):
1. Completion Report (`docs/devlog/YYYY-MM-DD_project-name.md`)
2. Devlog Entry (what was learned)
3. Session Memory (`docs/sessions/YYYY-MM-DD_session-name.md`)

**Context Management**:
- Orchestrator: Full vision, full config, all docs (50,000 tokens)
- Workers: Summary vision, filtered config, relevant docs (20,000-40,000 tokens)

---

### 2. Analyzer (System Analyst)
**Role**: Requirements analysis and architectural design
**File Location**: `template_manager.py` lines 410-441

**Key Responsibilities**:
- Understand requirements and constraints
- Analyze existing codebase and patterns
- Create architectural designs
- Identify risks and dependencies
- Prepare handoff documentation for implementer

**Discovery Workflow**:
1. Use Serena MCP to explore relevant code
2. Read only what's necessary
3. Focus on patterns and architecture
4. Document findings clearly

**Success Criteria**:
- Complete requirements documented
- Architecture aligns with vision
- All risks identified
- Clear specifications ready
- Handoff documentation complete

---

### 3. Implementer (System Developer)
**Role**: Code implementation following specifications
**File Location**: `template_manager.py` lines 443-472

**Key Responsibilities**:
- Write clean, maintainable code
- Follow architectural specs exactly
- Implement features per requirements
- Ensure code quality/standards
- Create proper documentation

**Implementation Workflow**:
1. Wait for analyzer's specifications
2. Use Serena MCP symbolic operations for edits
3. Follow existing code patterns exactly
4. Test changes incrementally

**Behavioral Rules**:
- Never expand scope beyond specs
- Report blockers immediately
- Hand off at 80% context usage
- Follow CLAUDE.md standards strictly
- Use symbolic editing for precision

**Success Criteria**:
- All features implemented correctly
- Code follows project standards
- No scope creep
- Tests pass
- Documentation updated

---

### 4. Tester (QA Engineer)
**Role**: Quality assurance and validation
**File Location**: `template_manager.py` lines 474-503

**Key Responsibilities**:
- Write comprehensive test suites
- Validate against requirements
- Find and document bugs
- Ensure code coverage
- Create test documentation

**Testing Workflow**:
1. Wait for implementer's completion
2. Create comprehensive test coverage
3. Validate against original requirements
4. Document all findings

**Success Criteria**:
- All features have test coverage
- Tests validate requirements
- Bug reports clear and actionable
- Coverage meets standards
- Test documentation complete

---

### 5. Reviewer (Code Quality Auditor)
**Role**: Code review and quality assurance
**File Location**: `template_manager.py` lines 505-533

**Key Responsibilities**:
- Review code for quality/standards
- Identify potential improvements
- Ensure security best practices
- Validate architectural compliance
- Provide actionable feedback

**Review Workflow**:
1. Wait for implementation and testing
2. Review for quality and standards
3. Check security best practices
4. Validate architectural compliance

**Success Criteria**:
- Code meets quality standards
- Security practices followed
- Architecture compliance validated
- All feedback actionable
- Review documentation complete

---

### 6. Documenter (Technical Writer)
**Role**: Documentation creation and maintenance
**File Location**: `template_manager.py` lines 535-560 (partial)

**Key Responsibilities**:
- Create comprehensive documentation
- Write usage examples and tutorials
- Document API specifications
- Update README and setup guides
- Document architectural decisions

**Documentation Workflow**:
1. Wait for implementation completion
2. Document all deliverables
3. Create usage examples
4. Update architectural docs

---

## Template Variables

All templates support variable substitution:

```python
variables = {
    "project_name": "Your Project Name",
    "project_mission": "Project goal/objective",
    "product_name": "Product name",
    "custom_mission": "Specific agent mission"
}
```

**Usage in templates**:
```
You are the {role} for: {project_name}
YOUR MISSION: {custom_mission}
PROJECT GOAL: {project_mission}
```

---

## Role-Specific Config Filtering

Different agent types receive filtered configuration data:

| Role | Config Fields Provided |
|------|------------------------|
| Implementer/Developer | architecture, tech_stack, codebase_structure, critical_features |
| Tester/QA | test_commands, test_config, critical_features, known_issues |
| Documenter | api_docs, documentation_style, architecture, critical_features |
| Analyzer | architecture, tech_stack, codebase_structure, critical_features, known_issues |
| Reviewer | architecture, tech_stack, critical_features, documentation_style |

---

## Agent Coordination Patterns

### Message Queue Communication
```python
# Send message
send_message(
    from_agent="orchestrator",
    to_agent="implementer",
    priority="high",
    content="Specifications ready for implementation"
)

# Acknowledge message
acknowledge_message(message_id)

# Mark completed
mark_message_completed(message_id)
```

### Behavioral Instructions
- Agents acknowledge messages immediately upon reading
- Report progress to orchestrator regularly
- Ask orchestrator for scope questions
- Coordinate handoffs at 80% context usage

---

## Database Storage

Templates are stored in the `agent_templates` table:

```sql
CREATE TABLE agent_templates (
    id SERIAL PRIMARY KEY,
    tenant_key VARCHAR(36) NOT NULL,
    product_id INTEGER,
    name VARCHAR(100) NOT NULL,
    category VARCHAR(50),
    role VARCHAR(100),
    template_content TEXT,
    variables JSON,
    behavioral_rules JSON,
    success_criteria JSON,
    preferred_tool VARCHAR(50),
    is_default BOOLEAN DEFAULT false,
    is_active BOOLEAN DEFAULT true,
    description TEXT,
    version VARCHAR(20),
    tags JSON,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

---

## Seeding Templates

**Script**: `scripts/seed_orchestrator_template.py`

**Usage**:
```bash
# Seed default orchestrator template
python scripts/seed_orchestrator_template.py

# Seed for specific tenant
python scripts/seed_orchestrator_template.py --tenant-key tenant-123
```

**Orchestrator Template Data**:
```python
template = AgentTemplate(
    tenant_key=tenant_key,
    name="orchestrator",
    category="role",
    role="orchestrator",
    template_content=orchestrator_content,
    variables=["project_name", "project_mission", "product_name"],
    behavioral_rules=[
        "Coordinate all agents effectively",
        "Ensure project goals are met through delegation",
        "Read vision document completely (all parts)",
        "Challenge scope drift",
        "Enforce 3-tool rule",
        "Create specific missions based on discoveries",
        "Create 3 documentation artifacts at project close"
    ],
    success_criteria=[
        "Vision document fully read",
        "All product config_data reviewed",
        "Serena MCP discoveries documented",
        "All agents spawned with SPECIFIC missions",
        "Project goals achieved and validated",
        "Three documentation artifacts created"
    ],
    preferred_tool="claude",
    is_default=True,
    version="2.0.0",
    tags=["orchestrator", "discovery", "delegation", "default"]
)
```

---

## Accessing Templates via API

**Endpoint**: `GET /api/templates`

**Response**:
```json
{
    "templates": [
        {
            "id": 1,
            "name": "orchestrator",
            "role": "orchestrator",
            "category": "role",
            "description": "Enhanced orchestrator template...",
            "version": "2.0.0",
            "is_default": true,
            "variables": ["project_name", "project_mission", "product_name"],
            "behavioral_rules": [...],
            "success_criteria": [...]
        }
    ]
}
```

---

## Template Manager API

**Class**: `UnifiedTemplateManager`
**File**: `src/giljo_mcp/template_manager.py`

**Key Methods**:

```python
# Get template content
template_mgr = UnifiedTemplateManager()
orchestrator = template_mgr.get_template(
    role="orchestrator",
    variables={
        "project_name": "MyProject",
        "project_mission": "Build feature X"
    }
)

# List available templates
templates = template_mgr.list_templates()

# Get legacy templates (all 6 types)
legacy = template_mgr._legacy_templates
```

---

## Best Practices

### For Orchestrators
1. ✅ Always read COMPLETE vision (all parts)
2. ✅ Use Serena MCP for discovery BEFORE delegating
3. ✅ Create SPECIFIC missions with file references
4. ✅ Enforce 3-tool rule for yourself and workers
5. ✅ Create 3 documentation artifacts at closure

### For Worker Agents
1. ✅ Acknowledge messages immediately
2. ✅ Never expand beyond specified scope
3. ✅ Report blockers to orchestrator
4. ✅ Hand off at 80% context usage
5. ✅ Follow CLAUDE.md standards

### For All Agents
1. ✅ Use Serena MCP symbolic operations for precision
2. ✅ Document all decisions and rationale
3. ✅ Test incrementally
4. ✅ Create clear handoff documentation
5. ✅ Validate against success criteria

---

## Common Anti-Patterns

### ❌ Don't Do This

**Orchestrator doing implementation**:
```
orchestrator reads file → edits code → runs tests → commits
```

**Generic missions**:
```
"Update the documentation"
"Fix the bugs"
"Improve the code"
```

**Scope expansion**:
```
Agent decides to refactor while implementing
Agent adds "nice to have" features
Agent modifies unrelated files
```

### ✅ Do This Instead

**Orchestrator delegating**:
```
orchestrator discovers issues → spawns implementer with specific mission → monitors
```

**Specific missions**:
```
"Update CLAUDE.md lines 45-67 to fix SQL patterns from session_20240112.md.
Add vLLM config from docs/deployment/vllm_setup.md.
Remove 12 Ollama references found via search.
Success: All tests pass, config validates."
```

**Scope adherence**:
```
Agent implements ONLY what's specified
Agent asks orchestrator for scope questions
Agent reports completion and hands off
```

---

## Template Evolution

**Current Version**: 2.0.0 (Phase 3 Enhanced)

**Recent Improvements**:
- Added 30-80-10 principle for orchestrators
- Enforced 3-tool delegation rule
- Mandatory project closure documentation
- Discovery-first workflow with Serena MCP
- Role-specific config filtering
- Enhanced behavioral rules

**See Also**:
- `docs/TEMPLATE_SYSTEM_EVOLUTION.md` - Full evolution history
- `handovers/completed/harmonized/HANDOVER_0011_TEMPLATE_SYSTEM_EVOLUTION-C.md` - Handover doc

---

## Related Files

**Core Implementation**:
- `src/giljo_mcp/template_manager.py` - Template manager
- `src/giljo_mcp/template_adapter.py` - Template adaptation
- `src/giljo_mcp/models.py` - AgentTemplate model

**API Endpoints**:
- `api/endpoints/templates.py` - Template CRUD API

**Seeding Scripts**:
- `scripts/seed_orchestrator_template.py` - Seed orchestrator
- `scripts/init_templates.py` - Initialize all templates

**Tests**:
- `tests/unit/test_template_manager_serena.py`
- `tests/integration/test_orchestrator_template.py`
- `tests/test_template_system.py`

---

**End of Agent Templates Reference**

For questions or updates, see: `src/giljo_mcp/template_manager.py`
