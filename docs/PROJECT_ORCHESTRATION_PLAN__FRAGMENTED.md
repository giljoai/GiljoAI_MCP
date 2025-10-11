# GiljoAI MCP - CLI-Focused Project Orchestration Plan

## Leveraging Claude Code Sub-Agents for Simplified CLI Architecture

## Executive Summary

The CLI-focused architecture leverages Claude Code's native sub-agent capability to create a streamlined, command-line-driven development environment. This revision demonstrates how we'll integrate sub-agents with a CLI-first approach while preserving the core value of GiljoAI-MCP as the persistent brain for AI development teams.

## What Changed with CLI Sub-Agents

### Before (Complex)

- Multiple terminal windows required
- Complex installation procedures
- Platform-specific setup challenges
- High cognitive overhead for developers
- Inconsistent user experience

### After (Elegant CLI)

- Single Python-based CLI installer
- Direct, synchronous sub-agent control
- MCP provides persistent project management
- Cross-platform execution
- 70% reduction in setup complexity

## Revised CLI Architecture

```
┌──────────────────────────────────────────────┐
│          GiljoAI-MCP (The Brain)            │
│  • Project State Persistence                │
│  • Cross-Session Coordination               │
│  • CLI Task Management                      │
│  • Vision Document Tracking                 │
└────────────┬─────────────────────────────────┘
             │ MCP CLI Protocol
             ↓
┌──────────────────────────────────────────────┐
│      Claude Code (The Execution Engine)      │
│  CLI Orchestrator (Project Manager)          │
│      ├── Spawns Sub-Agent: Analyzer          │
│      ├── Spawns Sub-Agent: Developer         │
│      ├── Spawns Sub-Agent: Tester            │
│      └── Spawns Sub-Agent: Reviewer          │
└──────────────────────────────────────────────┘
```

## Core CLI Value Proposition

### GiljoAI-MCP Provides (CLI-Powered):

- **Multi-Session Memory** - Work persists across terminal sessions
- **Team Coordination** - Multiple developers, different times
- **Task Pipeline** - Capture TODOs, convert to actionable projects
- **Vision Persistence** - Manage large project context documents
- **Universal Integration** - GitHub, local repositories, flexible workflows

### Claude Code Provides (Via CLI Sub-Agents):

- **Direct Execution** - Runs agents through command-line interface
- **Synchronous Delegation** - Spawn specialized sub-agents immediately
- **Native Git Integration** - Direct repository operations
- **Comprehensive Testing** - Run tests directly from CLI
- **Minimal Configuration** - Simple, reproducible setup

## Key CLI Design Principles

1. **Single Command Execution**
   ```bash
   python -m giljo_mcp install      # Universal installer
   python -m giljo_mcp project new  # Create new project
   python -m giljo_mcp agent spawn  # Spawn development agent
   ```

2. **Configuration Simplicity**
   - Centralized config in `~/.giljo/config.yaml`
   - Environment-aware settings
   - Minimal required parameters

3. **Transparent Logging**
   - Detailed CLI logs
   - Optional verbose mode
   - Log rotation and management

## Migration Strategy: CLI-First Approach

### Simplified Onboarding

```bash
# Quick Start
git clone https://github.com/giljoai/mcp.git
cd mcp
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
python install.py         # Universal CLI installer
```

### Development Workflow

```bash
# Project Management
giljo project create      # Initialize new project
giljo project list        # Show active projects
giljo project switch      # Change active context

# Agent Management
giljo agent list          # Show available agents
giljo agent spawn         # Create new development agent
giljo agent logs          # View agent interaction history
```

## Success Metrics (CLI Focus)

- **Installation Time**: 10 minutes → 2 minutes
- **Setup Complexity**: Reduced by 75%
- **Cross-Platform Support**: Improved to 99%
- **First-Time User Experience**: Simplified dramatically

## Risk Mitigation

### Technical Risks

- **Platform Compatibility**
  - Mitigation: Comprehensive testing across Windows, macOS, Linux
  - Use `pathlib` for universal path handling

- **Dependency Management**
  - Mitigation: Strict `requirements.txt`
  - Use virtual environments by default

### User Adoption Risks

- **Learning Curve**
  - Mitigation: Comprehensive CLI help system
  - Inline documentation for all commands

- **Feature Parity**
  - Mitigation: Ensure all workflows supported via CLI
  - Gradual, transparent feature rollout

## Conclusion

The CLI-first approach transforms GiljoAI-MCP from a complex multi-terminal system to an elegant, powerful development companion. We're not just building a tool—we're creating a streamlined, developer-focused AI coding assistant.

**From complex setup to CLI simplicity. Let's build!**

---

_This orchestration plan leverages CLI sub-agents to deliver GiljoAI MCP faster, simpler, and more effectively._