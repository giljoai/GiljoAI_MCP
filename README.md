# GiljoAI MCP Coding Orchestrator

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-green)](https://fastapi.tiangolo.com/)
[![Vue 3](https://img.shields.io/badge/Vue-3.0%2B-brightgreen)](https://vuejs.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)
[![Setup Time](https://img.shields.io/badge/Setup-5%20minutes-success)]()
[![Context](https://img.shields.io/badge/Context-Unlimited-orange)]()

**Break through AI context limits. Orchestrate teams of specialized AI agents.**

[**5-Minute Quick Start**](#5-minute-quick-start) | [**Features**](#key-features) | [**Architecture**](#architecture-overview) | [**Documentation**](#documentation)

</div>

---

## 🚨 The Problem

Every AI coding assistant hits the same wall:
- **Context Window Limits**: Even 200k tokens isn't enough for real projects
- **Session Amnesia**: Lose valuable context between sessions  
- **No Coordination**: Multiple AI instances can't work together
- **Task Fragmentation**: Technical debt identified but never tracked

## 💡 The Solution  

**GiljoAI MCP** orchestrates multiple specialized AI agents that work together as a coordinated team:

```
Your Request → Orchestrator → [Analyzer, Developer, Tester, Reviewer] → Complete Solution
```

Each agent maintains focused context within limits while the orchestrator manages the big picture. It's like having an entire development team, not just one assistant.

## 🎯 Why GiljoAI MCP?

- **🚀 Unlimited Project Complexity**: Break through context limits with multi-agent orchestration
- **🧠 Persistent Memory**: Never lose work between sessions with database-backed storage
- **👥 Real Team Coordination**: Agents hand off work, share context, and collaborate
- **📊 Complete Visibility**: Watch your AI team work in real-time via the dashboard
- **🔧 Production Ready**: From SQLite on your laptop to PostgreSQL in the cloud
- **🎨 Beautiful UI**: Professional Vue 3 dashboard with custom themes

## ⚡ 5-Minute Quick Start

### Prerequisites
```bash
# You need:
- Python 3.8+
- Git
- 5 minutes ⏱️
```

### Install and Run

```bash
# 1. Clone and enter directory (30 seconds)
git clone https://github.com/yourusername/giljo-mcp.git
cd giljo-mcp

# 2. Run interactive setup (2 minutes)
python setup.py
# → Choose: 1) SQLite (recommended for quick start)
# → Press Enter for all defaults
# → Setup creates all directories and config files

# 3. Install dependencies (1 minute)
pip install -r requirements.txt

# 4. Start the orchestrator (30 seconds)
python -m giljo_mcp start
# ✨ Server running at http://localhost:6000

# 5. Create your first orchestration (1 minute)
# Open browser to http://localhost:6000
# Click "New Project" and paste:
#   "Analyze my Python project and suggest improvements"
```

### 🎉 That's it! Your first AI team is now working!

### What Just Happened?

1. **Setup** created your local database and configuration
2. **Server** started the orchestration engine and dashboard
3. **Orchestrator** spawned specialized agents for your task
4. **Agents** are now analyzing, coding, and reviewing in parallel
5. **Dashboard** shows real-time progress and results

### Next Steps

```bash
# Watch your agents work
open http://localhost:6000

# Try a complex task
"Refactor my authentication system to use JWT tokens"

# See available MCP tools
python -m giljo_mcp tools

# Read the full documentation
python -m giljo_mcp docs
```

## Quick Start

### Advanced Setup Options

```bash
# Production setup with PostgreSQL
python setup.py --production

# LAN setup for team sharing
python setup.py --lan

# Docker setup
docker-compose up -d

# Development mode with hot reload
python -m giljo_mcp dev
```

## 🎯 Key Features

### Multi-Agent Orchestration
Coordinate specialized agents that work together on complex tasks:

| Agent Type | Specialization | Example Tasks |
|------------|---------------|---------------|
| **Analyzer** | Code analysis & architecture | "Audit my codebase for security issues" |
| **Developer** | Implementation & refactoring | "Add OAuth2 authentication" |
| **Tester** | Testing & validation | "Create unit tests for auth module" |
| **Reviewer** | Code review & optimization | "Optimize database queries" |
| **Documenter** | Documentation & guides | "Generate API documentation" |

### Vision Document System
50K+ token documents guide every agent decision:
```python
# Your product vision becomes the AI team's north star
vision = "Build a secure, scalable authentication system"
agents.align_to_vision(vision)  # All agents now share this goal
```

### Database-Backed Message Queue
Never lose messages between agents:
```sql
-- PostgreSQL stores every message, decision, and handoff
SELECT * FROM messages WHERE status = 'pending' AND agent = 'developer';
-- Result: Complete audit trail and recovery capability
```

### Dynamic Discovery via Serena MCP
Agents explore codebases intelligently:
```python
# Instead of static indexing
old_way = index_entire_codebase()  # Slow, outdated

# Dynamic discovery
new_way = agent.explore_as_needed()  # Fast, always fresh
```

### Progressive Architecture
```
Local (You) → LAN (Your Team) → WAN (Your Company) → Cloud (The World)
   SQLite        PostgreSQL         PostgreSQL+TLS      Managed Service
   1 user        10 users            100 users          10,000+ users
```

Same codebase scales without rewrites!

## 📦 Installation Options

### Option 1: Quick Install (Recommended)
```bash
# One-line install
curl -sSL https://giljo.ai/install.sh | bash

# Or with pip
pip install giljo-mcp
```

### Option 2: From Source  
```bash
# Clone repository
git clone https://github.com/yourusername/giljo-mcp.git
cd giljo-mcp

# Run interactive setup
python setup.py

# Install dependencies
pip install -r requirements.txt
```

### Option 3: Docker
```bash
# Using Docker Compose
docker-compose up -d

# Or Docker directly
docker run -p 6000:6000 giljo/mcp-orchestrator
```

## 🖥️ Dashboard & Control Center

Access the real-time dashboard at: **http://localhost:6000**

<div align="center">

| Dashboard Feature | What You See |
|-------------------|--------------|
| **Live Agent Status** | Watch agents work in real-time |
| **Message Flow** | See how agents communicate |
| **Task Progress** | Track project completion |
| **Token Usage** | Monitor context consumption |
| **Performance Metrics** | Optimize orchestration |

</div>

## 🏗️ Architecture

### System Layers
```
┌─────────────────────────────────────┐
│         Web Dashboard (Vue 3)       │ ← Real-time monitoring
├─────────────────────────────────────┤
│      REST API + WebSocket API       │ ← External integration
├─────────────────────────────────────┤
│      MCP Protocol (20+ tools)       │ ← Agent communication
├─────────────────────────────────────┤
│        Orchestration Engine         │ ← Brain of the system
├─────────────────────────────────────┤
│  Database (SQLite/PostgreSQL)       │ ← Persistent storage
└─────────────────────────────────────┘
```

### Deployment Evolution

| Mode | Use Case | Database | Auth | Setup Time |
|------|----------|----------|------|------------|
| **Local** | Personal dev | SQLite | None | 5 minutes |
| **LAN** | Small team | PostgreSQL | API Keys | 15 minutes |
| **WAN** | Remote team | PostgreSQL | OAuth/TLS | 30 minutes |
| **Cloud** | Enterprise | Distributed | SSO | Managed |

## Project Structure

```
giljo_mcp/
├── Docs/          # All documentation (centralized)
│   ├── Vision/    # Vision documents (highest priority)
│   ├── Sessions/  # Development session memories
│   ├── devlog/    # Development logs
│   ├── api/       # API documentation
│   ├── docker/    # Docker setup and deployment guides
│   ├── scripts/   # Scripts documentation
│   ├── tests/     # Test reports and validation
│   └── manuals/   # Reference manuals
├── frontend/      # Vue 3 dashboard
│   └── public/    # Static assets (PROVIDED)
│       ├── favicon.ico
│       ├── icons/      # System icons
│       └── mascot/     # Animated logo
├── src/           # Core application code
├── api/           # REST & WebSocket APIs
├── tests/         # Test suite code
├── scripts/       # Setup and utilities
└── docker/        # Container definitions
```

## Development Status

**Current Phase**: Orchestration Engine (Phase 3)
**Latest Milestone**: Project 3.9.b Template Management v2 - 100% Complete!

Building GiljoAI MCP using the AKE-MCP orchestrator through 20 focused projects:

- [x] Phase 1: Foundation & Database (Projects 1.1-1.4) ✅
- [x] Phase 2: MCP Integration (Projects 2.1-2.3) ✅
- [x] Phase 3: Orchestration Engine (Projects 3.1-3.9.b) ✅
  - Latest: Template system consolidated with <0.08ms performance
- [ ] Phase 4: User Interface
- [ ] Phase 5: Deployment & Polish

See [PROJECT_ORCHESTRATION_PLAN.md](Docs/PROJECT_ORCHESTRATION_PLAN.md) for details.

## 🚀 Example Orchestrations

### Example 1: Complete Feature Development
```python
# Request: "Add user authentication with JWT tokens"

orchestrator.spawn_agents([
    Analyzer("Review existing auth code"),
    Developer("Implement JWT authentication"),  
    Tester("Write auth test suite"),
    Reviewer("Security audit the implementation")
])

# Result: Complete, tested, reviewed feature in 1 hour
```

### Example 2: Codebase Refactoring
```python
# Request: "Refactor database layer to use SQLAlchemy"

orchestrator.coordinate([
    Analyzer("Map current database usage"),
    Developer("Migrate to SQLAlchemy models"),
    Tester("Ensure backward compatibility"),
    Documenter("Update API documentation")
])

# Result: Safe, incremental refactoring with zero downtime
```

### Example 3: Bug Hunt & Fix
```python
# Request: "Find and fix all SQL injection vulnerabilities"

orchestrator.execute([
    Analyzer("Scan for SQL injection patterns"),
    Developer("Fix vulnerable queries"),
    Tester("Verify fixes with security tests"),
    Reviewer("Validate security improvements")
])

# Result: Comprehensive security fixes with proof
```

## 🆚 How We Compare

| Feature | GiljoAI MCP | GitHub Copilot | Cursor | Codeium |
|---------|-------------|----------------|--------|---------|
| **Multi-Agent Teams** | ✅ Unlimited | ❌ Single | ❌ Single | ❌ Single |
| **Context Limit** | ✅ Unlimited* | ⚠️ 8K | ⚠️ 24K | ⚠️ 16K |
| **Session Memory** | ✅ Persistent | ❌ Lost | ❌ Lost | ❌ Lost |
| **Team Coordination** | ✅ Built-in | ❌ None | ❌ None | ❌ None |
| **Self-Hosted** | ✅ Yes | ❌ No | ❌ No | ⚠️ Enterprise |
| **Custom Agents** | ✅ Yes | ❌ No | ❌ No | ❌ No |
| **Real-time Dashboard** | ✅ Yes | ❌ No | ❌ No | ❌ No |
| **Database Backed** | ✅ Yes | ❌ No | ❌ No | ❌ No |

*Via multi-agent orchestration

## Documentation

### Core Documentation
- [Vision Document](Docs/Vision/VISION_DOCUMENT.md) - Product vision and roadmap
- [Technical Architecture](Docs/TECHNICAL_ARCHITECTURE.md) - System design
- [Project Cards](Docs/PROJECT_CARDS.md) - Development project descriptions
- [Project Flow](Docs/PROJECT_FLOW_VISUAL.md) - Visual timeline and dependencies
- [Color Themes](Docs/color_themes.md) - UI color palette specifications
- [Navigation Guide](Docs/README_FIRST.md) - Complete project index

### Implementation Guides
- [API Implementation](Docs/api/api_implementation_guide.md) - REST API details
- [Template API Reference](Docs/api/templates.md) - Template management system API
- [Template Migration Guide](Docs/guides/template_migration.md) - Migrate from legacy templates
- [Docker Setup](Docs/docker/docker_setup_guide.md) - Container configuration
- [Docker Deployment](Docs/docker/docker_deployment_guide.md) - Production deployment
- [Scripts Setup](Docs/scripts/scripts_setup_guide.md) - Utility scripts

### Architecture Decision Records
- [Template Consolidation](Docs/adr/003_template_consolidation.md) - Why we unified 3 systems into 1

### Testing Documentation
- [Test Documentation](Docs/tests/CONSOLIDATED_TEST_DOCUMENTATION.md) - Complete testing guide
- [Docker Tests](Docs/docker/tests/) - Container testing reports

## Contributing

This project is currently in active development. Contributions welcome after initial release!

## Tech Stack

- **Backend**: Python, FastAPI, SQLAlchemy
- **Frontend**: Vue 3, Vite, Vuetify 3, Tailwind CSS
- **Database**: SQLite (local) / PostgreSQL (production)
- **Protocol**: Model Context Protocol (MCP)
- **Deployment**: Docker, pip installable

## Features Carried Forward from AKE-MCP

- ✅ Vision document chunking (50K+ tokens)
- ✅ Message acknowledgment arrays
- ✅ Dynamic discovery architecture
- ✅ Database-first message queue
- ✅ Orchestrator mission templates (now database-backed via template_manager.py)
- ✅ Serena MCP integration with token optimization
- ✅ Template consolidation from 3 systems to 1 unified solution

## Serena Integration & Token Optimization

GiljoAI MCP includes a sophisticated token optimization layer for Serena MCP:

- **SerenaOptimizer Class**: Enforces symbolic operations over file reads
- **Auto-injection**: Optimization rules added to all agent missions
- **Token Monitoring**: Real-time usage tracking and alerts
- **90% Reduction**: Typical token usage reduced by 90%
- **Smart Defaults**: `max_answer_chars=1000` enforced automatically

## License

MIT License - See [LICENSE](LICENSE) file for details

## 🤝 Community & Support

### Get Help
- 📚 **Documentation**: [/Docs](Docs/) - Comprehensive guides
- 💬 **Discord**: [Join our community](https://discord.gg/giljo-mcp) 
- 🐛 **Issues**: [GitHub Issues](https://github.com/yourusername/giljo-mcp/issues)
- 💡 **Discussions**: [GitHub Discussions](https://github.com/yourusername/giljo-mcp/discussions)

### Quick Links
- [Vision Document](Docs/Vision/VISION_DOCUMENT.md) - Our roadmap
- [API Reference](Docs/api/api_implementation_guide.md) - REST API
- [MCP Tools Manual](Docs/manuals/MCP_TOOLS_MANUAL.md) - All 20 tools
- [Docker Guide](Docs/docker/docker_deployment_guide.md) - Production deployment

## 🎯 Roadmap

| Phase | Timeline | Status | Features |
|-------|----------|--------|----------|
| **Foundation** | Q1 2025 | ✅ Complete | Multi-tenant, SQLite, Setup |
| **MCP Integration** | Q1 2025 | ✅ Complete | 20 tools, Serena MCP |
| **Orchestration** | Q1 2025 | ✅ Complete | Templates, Message Queue |
| **User Interface** | Q2 2025 | 🚧 In Progress | Vue Dashboard, WebSocket |
| **Cloud Platform** | Q3 2025 | 📋 Planned | SaaS, Enterprise |

## 🙏 Acknowledgments

Built with:
- [FastMCP](https://github.com/fastmcp/fastmcp) - MCP protocol implementation
- [FastAPI](https://fastapi.tiangolo.com/) - Modern web framework
- [SQLAlchemy](https://www.sqlalchemy.org/) - Database ORM
- [Vue 3](https://vuejs.org/) - Progressive UI framework
- [AKE-MCP](https://github.com/yourusername/ake-mcp) - Orchestration inspiration

---

<div align="center">

**🚀 From local machine to global scale, we're orchestrating the future of AI development.**

Made with ❤️ by the GiljoAI Team

[Website](https://giljo.ai) | [Blog](https://blog.giljo.ai) | [Twitter](https://twitter.com/giljoai)

</div>