# GiljoAI MCP Coding Orchestrator

> Transform AI coding assistants into orchestrated development teams

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-green)](https://fastapi.tiangolo.com/)
[![Vue 3](https://img.shields.io/badge/Vue-3.0%2B-brightgreen)](https://vuejs.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

## What is GiljoAI MCP?

GiljoAI MCP Coding Orchestrator is a sophisticated multi-agent orchestration system that solves the fundamental limitation of AI context windows. By orchestrating teams of specialized AI agents that work together, it enables developers to tackle projects of unlimited complexity while maintaining full control and visibility.

### Key Features

- 🤖 **Multi-Agent Orchestration**: Coordinate specialized agents (analyzer, developer, tester, reviewer)
- 📚 **Vision Document Chunking**: Handle 50K+ token documents elegantly
- 💬 **Never Lose Messages**: PostgreSQL-backed message queue with acknowledgment tracking
- 🔍 **Dynamic Discovery**: No static indexing - always fresh context via Serena MCP
- 🏗️ **Progressive Architecture**: Same code runs locally or scales to cloud
- 🔐 **Multi-Tenant Ready**: Project isolation via tenant keys from day one
- ⚡ **Real-time Updates**: WebSocket-powered live dashboard
- 🎨 **Professional UI**: Vue 3 + Vuetify 3 with custom theme system
- 🖼️ **Visual Assets Ready**: Icons, mascot, and branding included
- 🌐 **Cross-Platform**: OS-neutral code works on Windows, Mac, Linux

## Quick Start

### Prerequisites

- Python 3.8+
- PostgreSQL 12+ (optional, SQLite works for local)
- Node.js 16+ (for UI development)
- Git

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/giljo-mcp.git
cd giljo-mcp

# Run setup script
python setup.py

# Follow the interactive prompts to configure:
# - Database (SQLite for local, PostgreSQL for teams)
# - Paths and directories
# - Initial configuration
```

### Starting the System

```bash
# Start everything
python -m giljo_mcp start

# Or start components individually
python -m giljo_mcp server  # MCP server only
python -m giljo_mcp ui       # Dashboard only
```

### Access the Dashboard

Open your browser to: http://localhost:5000

## Architecture Overview

```
Local Mode (Default)          →  LAN Mode (Teams)      →  Cloud Mode (Scale)
SQLite + localhost            →  PostgreSQL + API Keys  →  Managed Service
Single developer              →  Small team             →  Global deployment
```

## Project Structure

```
giljo_mcp/
├── docs/          # All documentation
│   ├── Vision/    # Vision documents (highest priority)
│   ├── Sessions/  # Development session memories
│   └── devlog/    # Development logs
├── frontend/      # Vue 3 dashboard
│   └── public/    # Static assets (PROVIDED)
│       ├── favicon.ico
│       ├── icons/      # System icons
│       └── mascot/     # Animated logo
├── src/           # Core application code (TO BE CREATED)
├── api/           # REST & WebSocket APIs (TO BE CREATED)
├── tests/         # Test suite (TO BE CREATED)
├── scripts/       # Setup and utilities (TO BE CREATED)
└── docker/        # Container definitions (TO BE CREATED)
```

## Development Status

**Current Phase**: Foundation (Week 1 of 4)

We're building GiljoAI MCP using the existing AKE-MCP orchestrator through 20 focused projects:

- [ ] Phase 1: Foundation & Database
- [ ] Phase 2: MCP Integration  
- [ ] Phase 3: Orchestration Engine
- [ ] Phase 4: User Interface
- [ ] Phase 5: Deployment & Polish
- [ ] Phase 6: Integrations & Optimization

See [PROJECT_ORCHESTRATION_PLAN.md](docs/PROJECT_ORCHESTRATION_PLAN.md) for details.

## Documentation

- [Vision Document](docs/Vision/VISION_DOCUMENT.md) - Product vision and roadmap
- [Technical Architecture](docs/TECHNICAL_ARCHITECTURE.md) - System design
- [Project Cards](docs/PROJECT_CARDS.md) - Development project descriptions
- [Project Flow](docs/PROJECT_FLOW_VISUAL.md) - Visual timeline and dependencies
- [Color Themes](docs/color_themes.md) - UI color palette specifications
- [Navigation Guide](docs/README_FIRST.md) - Complete project index

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
- ✅ Orchestrator mission templates
- ✅ Serena MCP integration with token optimization

## Serena Integration & Token Optimization

GiljoAI MCP includes a sophisticated token optimization layer for Serena MCP:

- **SerenaOptimizer Class**: Enforces symbolic operations over file reads
- **Auto-injection**: Optimization rules added to all agent missions
- **Token Monitoring**: Real-time usage tracking and alerts
- **90% Reduction**: Typical token usage reduced by 90%
- **Smart Defaults**: `max_answer_chars=1000` enforced automatically

## License

MIT License - See [LICENSE](LICENSE) file for details

## Support

- Documentation: [/docs](docs/)
- Issues: [GitHub Issues](https://github.com/yourusername/giljo-mcp/issues)
- Discussions: [GitHub Discussions](https://github.com/yourusername/giljo-mcp/discussions)

---

*From local machine to global scale, we're orchestrating the future of AI development.*