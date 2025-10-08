# GiljoAI MCP Documentation Index

This file provides an index of the documentation files available in the 'docs' directory, as well as insights and key points gained from analyzing these documents. This section summarizes your current understanding of GiljoAI-MCP based on the analyzed documentation files.

## Current Understanding of GiljoAI-MCP

Based on the analysis of the documentation files in this project, here are some insights about GiljoAI-MCP:

- Implements a Project Manager-style orchestrator using dynamic discovery approach for mission creation and delegating work to worker agents
- Focuses on cross-platform compatibility with support for Windows, Linux, and macOS
- Transitioned from supporting multiple databases to PostgreSQL 18 exclusive architecture
- Utilizes database-driven message queue for agent communication and coordination
- Implements hierarchical context loading (full context for orchestrator, filtered context for worker agents)
- Emphasizes code portability and security best practices
- Provides platform-specific installation requirements for PostgreSQL 18, Python 3.11+, Node.js 18+

## Documentation Files Analysis

The following sections provide summaries of each documentation file in the 'docs' directory, which can be helpful for understanding the project's architecture, design principles, best practices, and more.

### docs/AGENT_INSTRUCTIONS.md
Suggested Folder: F:\GiljoAI_MCP\docs\agents\
- **Summary:** Instructions on agent functionality, configuration, and usage.
- **Key Points:**
  - Agent types (orchestrator, worker)
  - Configuration options (context loading, mission delegation)
  - Usage examples

### docs/AI_CODING_TOOLS_COMPARISON.md
Suggested Folder: F:\GiljoAI_MCP\docs\ai_tools\
- **Summary:** Comparison of AI coding tools and their features.
- **Key Points:**
  - Tool features (code completion, debugging, testing)
  - Performance comparison

### docs/AKE_MCP_ORCHESTRATOR_ANALYSIS.md
Suggested Folder: F:\GiljoAI_MCP\docs\orchestrator\
- **Summary:** Analysis of AKE-MCP orchestrator architecture, focusing on implementing similar functionality in GiljoAI-MCP.
- **Key Points:**
  - Implements a Project Manager-style orchestrator using dynamic discovery approach
  - Uses MCP tools (Serena MCP, get_vision, etc.) for context discovery and mission creation
  - Utilizes database-driven message queue for agent communication and coordination
  - Delegates work to worker agents rather than executing implementation itself
  - Monitors progress and handles handoffs between agents
  - Implements hierarchical context loading (full context for orchestrator, filtered context for worker agents)

### docs/INSTALLER_MIGRATION_SUMMARY_2025_09_30.md
Suggested Folder: F:\GiljoAI_MCP\docs\installer\
- **Summary:** Summary of changes made in installer migration from multiple databases to PostgreSQL 18 exclusive architecture.
- **Key Points:**
  - Transitioned to PostgreSQL 18 exclusive architecture by removing SQLite and MySQL support
  - Standardized installation procedure to a single CLI command: python install.py
  - Enhanced error handling and security configurations
  - Improved performance with faster installation time, reduced complexity, better resource utilization, and more predictable behavior
  - Recommended updating existing installations using provided migration scripts

### ... (rest of the files)
