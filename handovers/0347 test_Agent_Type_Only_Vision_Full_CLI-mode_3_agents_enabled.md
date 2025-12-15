# Test Capture: Orchestrator Instructions

This is a test capture of orchestrator instructions from the GiljoAI MCP server.

Claude Code CLI mode toggle on

Context settings, 
Project Context Always Critical
Priority Configuration (What to Fetch)
Toggle fields on/off to include/exclude from context. Set priority for included fields.
Product Description Important 2
Tech Stack Important 2
Architecture Reference 3
Testing Reference 3

Depth Configuration (How Much Detail)
Control the level of detail for context fields with adjustable depth.
Vision Documents Full (Mandatory complete read) full Critical 1
360 Memory 3 projects 3 Critical 1
Git History 25 commits  25 Critical 1
Agent Templates Type Only (~250 tokens for 5 agents) type_only Critical 1


### Below is the get_orchestrator_intructions out put based on the above settings

**Orchestrator ID:** `6792fae5-c46b-4ed7-86d6-df58aa833df3`
**Tenant Key:** `***REMOVED***`
**Timestamp:** 2025-12-14

---

## Full JSON Response

```json
{
  "orchestrator_id": "6792fae5-c46b-4ed7-86d6-df58aa833df3",
  "project_id": "97d95e5a-51dd-47ae-92de-7f8839de503a",
  "project_name": "Project 1 Start project esting claude code",
  "project_description": "This project is about setting up the proper folder structure and index of all files that needs to be built for this application.  Each folder should have a small script file describing in 200 words what should go into the folder and in a root folder called /docs should be an index file listing the proposed folder architecture for the project.  You are also to prepare an initial readme.md no more than 500 words and requirments.txt",
  "mission": "## Serena MCP Available\n\nSerena MCP symbolic code navigation is enabled for token-efficient codebase exploration.\nKey tools: find_symbol, get_symbols_overview, search_for_pattern, replace_symbol_body.\nSerena provides 80-90% token savings vs full file reads.\n\n---\n\n{\n  \"priority_map\": {\n    \"critical\": [\n      \"project_description\"\n    ],\n    \"important\": [],\n    \"reference\": []\n  },\n  \"critical\": {\n    \"project_description\": {\n      \"name\": \"Project 1 Start project esting claude code\",\n      \"description\": \"This project is about setting up the proper folder structure and index of all files that needs to be built for this application.  Each folder should have a small script file describing in 200 words what should go into the folder and in a root folder called /docs should be an index file listing the proposed folder architecture for the project.  You are also to prepare an initial readme.md no more than 500 words and requirments.txt\"\n    }\n  },\n  \"important\": {},\n  \"reference\": {}\n}",
  "context_budget": 150000,
  "context_used": 0,
  "agent_templates": [
    {
      "name": "documenter",
      "role": "documenter",
      "description": "Documentation specialist for clear, comprehensive project documentation"
    },
    {
      "name": "tester",
      "role": "tester",
      "description": "Testing specialist for comprehensive test coverage and quality assurance"
    },
    {
      "name": "reviewer",
      "role": "reviewer",
      "description": "Code review specialist for quality assurance and best practices enforcement"
    }
  ],
  "agent_discovery_tool": "get_available_agents()",
  "field_priorities": {
    "testing": 3,
    "memory_360": 1,
    "tech_stack": 2,
    "git_history": 1,
    "architecture": 3,
    "product_core": 2,
    "agent_templates": 1,
    "project_context": 1,
    "vision_documents": 1
  },
  "token_reduction_applied": true,
  "estimated_tokens": 249,
  "instance_number": 1,
  "thin_client": true,
  "agent_spawning_constraint": {
    "mode": "strict_task_tool",
    "allowed_agent_types": [
      "documenter",
      "tester",
      "reviewer"
    ],
    "instruction": "CRITICAL: You MUST use Claude Code's native Task tool for agent spawning. The agent_type parameter must be EXACTLY one of the allowed template names. Use agent_name for descriptive labels (displayed in UI). Allowed agent types: ['documenter', 'tester', 'reviewer']"
  },
  "cli_mode_rules": {
    "agent_type_usage": "MUST match template 'name' field exactly for Task tool. This is the filename without .md extension (e.g., 'implementer', 'analyzer').",
    "agent_name_usage": "Descriptive label for UI display only - NOT for Task tool. Can be any human-readable name (e.g., 'Folder Structure Implementer').",
    "task_tool_mapping": "Task(subagent_type=X) where X = agent_type value from spawn_agent_job. Claude Code's Task tool finds agents by filename, so agent_type must match exactly.",
    "validation": "soft",
    "template_locations": [
      "{project}/.claude/agents/ (priority 1 - project agents)",
      "~/.claude/agents/ (priority 2 - user agents)"
    ],
    "agent_type_is_truth": {
      "statement": "agent_type is the SINGLE SOURCE OF TRUTH for Task tool operations",
      "usage": "spawn_agent_job(agent_type=X) → Task(subagent_type=X)",
      "agent_name_purpose": "Display label ONLY - never for tool calling"
    },
    "forbidden_patterns": [
      {
        "pattern": "Task(subagent_type=agent_name)",
        "reason": "agent_name is display only"
      },
      {
        "pattern": "Task(subagent_type='Backend Implementor')",
        "reason": "Creative variation will fail"
      },
      {
        "pattern": "Task(subagent_type='frontend-impl')",
        "reason": "Hyphenated variation will fail"
      },
      {
        "pattern": "Task(subagent_type='IMPLEMENTER')",
        "reason": "Case mismatch will fail"
      },
      {
        "pattern": "Any variation of agent_type",
        "reason": "Only exact agent_type value works"
      }
    ],
    "lifecycle_flow": [
      {
        "phase": 1,
        "name": "Staging",
        "operation": "spawn_agent_job(agent_type='X')",
        "param": "agent_type"
      },
      {
        "phase": 2,
        "name": "Job Created",
        "operation": "Job.agent_type = 'X'",
        "param": "agent_type"
      },
      {
        "phase": 3,
        "name": "Launch",
        "operation": "Task(subagent_type='X')",
        "param": "agent_type"
      },
      {
        "phase": 4,
        "name": "File Lookup",
        "operation": "Claude Code finds X.md",
        "param": "agent_type"
      }
    ]
  },
  "spawning_examples": [
    {
      "scenario": "Two implementers with different tasks",
      "calls": [
        "spawn_agent_job(agent_type=\"implementer\", agent_name=\"Folder Scaffolder\", ...)",
        "spawn_agent_job(agent_type=\"implementer\", agent_name=\"README Writer\", ...)"
      ],
      "note": "Both use agent_type='implementer' - the template name"
    }
  ]
}
```
