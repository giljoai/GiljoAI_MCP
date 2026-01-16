# Gemini CLI vs Claude Code CLI: Agent Template Format Comparison

## Executive Summary

Your MCP server managing agent templates needs to handle **fundamentally different architectures**:

| Aspect | Gemini CLI | Claude Code CLI |
|--------|------------|-----------------|
| **Primary Format** | TOML + JSON | Markdown + YAML frontmatter |
| **Agent Definition** | Extensions (`gemini-extension.json`) | Agent files (`.md` with frontmatter) |
| **Commands** | TOML files (`.toml`) | Markdown files (`.md`) |
| **Context Files** | `GEMINI.md` (plain markdown) | `CLAUDE.md` (plain markdown) |
| **Skills** | N/A (not native) | `SKILL.md` with YAML frontmatter |
| **Subagent Status** | Experimental/Community | Native & mature |

---

## Claude Code CLI Agent Template Format

### File Structure
```
~/.claude/
├── agents/                     # User-level agents
│   └── code-reviewer.md
├── commands/                   # User-level commands
│   └── review.md
├── skills/                     # User-level skills
│   └── my-skill/
│       └── SKILL.md
└── CLAUDE.md                   # Global context

.claude/                        # Project-level
├── agents/
├── commands/
├── skills/
└── CLAUDE.md
```

### Agent Template Format (Your `analyzer.md` Example)

**Format:** Markdown with YAML frontmatter

```yaml
---
name: analyzer                              # Required: unique identifier
description: Analysis specialist...          # Required: when to invoke
model: sonnet                               # Optional: sonnet, opus, haiku, inherit
color: red                                  # Optional: visual identifier
tools: Read, Glob, Grep, Bash               # Optional: tool restrictions
permissionMode: default                     # Optional: permission handling
skills: skill1, skill2                      # Optional: auto-load skills
hooks:                                      # Optional: lifecycle hooks
  PreToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "./validate.sh"
---

## Role-Specific Instructions

You are an analysis specialist responsible for...

Your primary responsibilities:
- Analyze user requirements
- Identify technical constraints
...
```

### Configuration Fields

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Lowercase with hyphens |
| `description` | Yes | Natural language - triggers automatic invocation |
| `tools` | No | Comma-separated list; omit to inherit all |
| `model` | No | `sonnet`, `opus`, `haiku`, or `inherit` |
| `permissionMode` | No | `default`, `acceptEdits`, `bypassPermissions`, `plan`, `ignore` |
| `skills` | No | Auto-load specific skills |
| `hooks` | No | PreToolUse, PostToolUse lifecycle hooks |
| `color` | No | Visual theme identifier |

### Command Format

**Format:** Markdown with optional YAML frontmatter

```yaml
---
description: Creates a git commit with a semantic message
argument-hint: [message]
allowed-tools: Bash(git diff:*)
---

ADD all modified and new files to git.
THEN commit with a clear and concise one-line commit message...

Use the output of !"git status" to inform the commit.
```

**Arguments:** Use `$ARGUMENTS` or positional `$1`, `$2`

### Skills Format (SKILL.md)

```yaml
---
name: skill-name
description: Brief overview triggering invocation
allowed-tools: Bash, Read
version: 1.0.0
---

# Skill Instructions

Purpose explanation and detailed instructions...
```

---

## Gemini CLI Template Format

### File Structure
```
~/.gemini/
├── extensions/                 # User extensions
│   └── my-extension/
│       ├── gemini-extension.json
│       ├── GEMINI.md
│       └── commands/
│           └── deploy.toml
├── commands/                   # Global commands
│   └── test/
│       └── gen.toml
├── settings.json
└── GEMINI.md                   # Global context

.gemini/                        # Project-level
├── extensions/
├── commands/
├── agents/                     # Community pattern (not native)
│   ├── tasks/
│   ├── plans/
│   ├── logs/
│   └── workspace/
└── GEMINI.md
```

### Extension Format (Primary Agent Container)

**Format:** JSON (`gemini-extension.json`)

```json
{
  "name": "my-extension",
  "version": "1.0.0",
  "mcpServers": {
    "my-server": {
      "command": "node my-server.js"
    }
  },
  "contextFileName": "GEMINI.md",
  "excludeTools": ["run_shell_command(rm -rf)"]
}
```

### Configuration Fields (Extension)

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Lowercase with hyphens, matches directory name |
| `version` | Yes | Semantic version |
| `mcpServers` | No | MCP server configurations |
| `contextFileName` | No | Context file name (defaults to `GEMINI.md`) |
| `excludeTools` | No | Tools to disable |

### Command Format

**Format:** TOML (`.toml`)

```toml
# ~/.gemini/commands/test/gen.toml
# Invoked as: /test:gen "Create a test for the login button"

description = "Generates a unit test based on a description."

prompt = """
You are an expert test engineer.
Based on the following requirement, please write a comprehensive 
unit test using the Jest testing framework.

Requirement: {{args}}
"""
```

**Arguments:** Use `{{args}}` placeholder

### Subagent Approaches (Experimental/Community)

Gemini CLI does **not have native subagent file format** comparable to Claude Code. Current approaches:

1. **Official (In Development):** TypeScript `SubagentConfig` interface
   ```typescript
   interface SubagentConfig {
     model: string;
     temp: number;
     top_p: number;
   }
   ```

2. **Community Pattern (filesystem-as-state):**
   - Tasks stored as JSON files in `.gemini/agents/tasks/`
   - Plans as Markdown in `.gemini/agents/plans/`
   - Agents launched via shell commands with `-e` extension flag

---

## Side-by-Side Comparison

### Agent/Subagent Definition

**Claude Code:**
```yaml
---
name: code-reviewer
description: Reviews code for quality
tools: Read, Glob, Grep
model: sonnet
---

You are a code reviewer...
```

**Gemini CLI (Extension + Context):**
```json
// gemini-extension.json
{
  "name": "code-reviewer",
  "version": "1.0.0",
  "excludeTools": ["write_file"]
}
```
```markdown
<!-- GEMINI.md -->
You are a code reviewer...
```

### Commands

**Claude Code:**
```yaml
---
description: Review code changes
allowed-tools: Bash(git diff:*)
---

Review the code changes: $ARGUMENTS
```

**Gemini CLI:**
```toml
description = "Review code changes"

prompt = """
Review the code changes: {{args}}
"""
```

### Key Syntax Differences

| Feature | Claude Code | Gemini CLI |
|---------|-------------|------------|
| **Frontmatter delimiter** | `---` (YAML) | N/A (TOML/JSON) |
| **Argument placeholder** | `$ARGUMENTS`, `$1` | `{{args}}` |
| **File injection** | `@filename` | `@{path/to/file}` |
| **Shell execution** | `!"command"` | `!{command}` |
| **Multi-line strings** | Native markdown | `"""..."""` (TOML) |
| **Tool restriction** | `tools:` frontmatter | `excludeTools` JSON |
| **Model selection** | `model: sonnet` | Extension-level or API param |

---

## MCP Server Implementation Recommendations

### Unified Schema Proposal

For your MCP server, consider a normalized internal format that maps to both:

```typescript
interface AgentTemplate {
  // Core Identity
  name: string;
  description: string;
  version?: string;
  
  // Execution Config
  model?: 'sonnet' | 'opus' | 'haiku' | 'inherit' | 'gemini-2.5-pro';
  tools?: string[];          // Allowed tools
  excludeTools?: string[];   // Blocked tools
  
  // Context
  systemPrompt: string;      // Main instructions
  contextFiles?: string[];   // Additional context imports
  
  // Platform-specific
  claudeConfig?: {
    color?: string;
    permissionMode?: string;
    hooks?: object;
    skills?: string[];
  };
  geminiConfig?: {
    mcpServers?: object;
    excludeTools?: string[];  // Can include command restrictions
  };
}
```

### Export Functions

```typescript
function exportToClaudeCode(template: AgentTemplate): string {
  // Generate Markdown with YAML frontmatter
  const frontmatter = {
    name: template.name,
    description: template.description,
    ...(template.model && { model: template.model }),
    ...(template.tools && { tools: template.tools.join(', ') }),
    ...template.claudeConfig
  };
  
  return `---
${yaml.stringify(frontmatter)}---

${template.systemPrompt}`;
}

function exportToGeminiCLI(template: AgentTemplate): {
  extension: object;
  context: string;
  commands?: object[];
} {
  return {
    extension: {
      name: template.name,
      version: template.version || '1.0.0',
      contextFileName: 'GEMINI.md',
      ...(template.excludeTools && { excludeTools: template.excludeTools }),
      ...template.geminiConfig
    },
    context: template.systemPrompt
  };
}
```

---

## Critical Differences for Your MCP Server

1. **No 1:1 Subagent Mapping:** Gemini CLI lacks a native markdown-based agent file format. You'll need to generate extension packages (folder with JSON + MD).

2. **Tool Syntax Differs:**
   - Claude: `tools: Read, Bash(git:*)` (allow-list with patterns)
   - Gemini: `excludeTools: ["run_shell_command(rm -rf)"]` (deny-list with patterns)

3. **Argument Handling:**
   - Claude: `$ARGUMENTS` or `$1`, `$2`
   - Gemini: `{{args}}`

4. **Model Specification:**
   - Claude: Per-agent `model:` field
   - Gemini: API/runtime parameter, not file-level

5. **Hooks/Lifecycle:**
   - Claude: Native hooks in frontmatter
   - Gemini: Separate `hooks/hooks.json` in extensions

6. **File Structure:**
   - Claude: Single `.md` file per agent
   - Gemini: Directory with multiple files (`gemini-extension.json`, `GEMINI.md`, `commands/*.toml`)

---

## Sources

- [Claude Code Subagents Documentation](https://code.claude.com/docs/en/sub-agents)
- [Gemini CLI Extensions Documentation](https://geminicli.com/docs/extensions/)
- [Gemini CLI Custom Commands](https://geminicli.com/docs/cli/custom-commands/)
- [GitHub: google-gemini/gemini-cli](https://github.com/google-gemini/gemini-cli)
- Community implementations: pauldatta/gemini-cli-commands-demo
