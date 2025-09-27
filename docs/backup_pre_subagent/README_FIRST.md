# 📋 README_FIRST - GiljoAI MCP Project Index

## Welcome to GiljoAI MCP Development!

This is the root directory for the **GiljoAI MCP Coding Orchestrator** project - a complete multi-agent orchestration system with multi-tenant architecture and enhanced capabilities.

## 🗂️ Directory Structure & Contents

### 📁 Root Files

- **README.md** - Main project documentation and quick start guide
- **CLAUDE.md** - AI assistant instructions and project context
- **requirements.txt** - Python dependencies list
- **config.yaml** - Project configuration settings
- **.mcp.json** - MCP server configuration
- **.env.example** - Environment variable template (copy to .env)
- **docker-compose.yml** - Docker orchestration configuration
- **alembic.ini** - Database migration configuration

### 📁 `/docs/` - Core Documentation Hub

#### 📁 Vision Documents (HIGHEST PRIORITY)

- **📁 `/docs/Vision/`**
  - `VISION_DOCUMENT.md` - Complete vision, roadmap, and strategic goals

#### 📁 Reference Manuals

- **📁 `/docs/manuals/`**
  - `README.md` - Index of all manuals
  - `MCP_TOOLS_MANUAL.md` - Complete reference for 20+ MCP tools
  - `MISSION_TEMPLATES_TESTING_GUIDE.md` - Test suite documentation for mission templates

#### 📄 Project Planning Documents

- `PROJECT_ORCHESTRATION_PLAN.md` - Master plan for 20-project development strategy
- `PROJECT_CARDS.md` - Ready-to-use mission cards for orchestrator projects
- `PROJECT_FLOW_VISUAL.md` - Visual timeline and project dependencies

#### 📄 Technical Documentation

- `TECHNICAL_ARCHITECTURE.md` - System design with OS-neutral requirements
- `PRODUCT_PROPOSAL.md` - Business case and market positioning
- `PROVEN_FEATURES_TO_PRESERVE.md` - Critical features to maintain
- `MESSAGE_QUEUE_GUIDE.md` - Message queue system documentation
- `AGENT_INSTRUCTIONS.md` - Agent behavior and coordination guidelines

#### 🎨 UI/UX Resources

- `color_themes.md` - **MANDATORY** color palette and theme specifications
- `Website colors.txt` - Additional color reference

#### 📄 Navigation & Configuration

- `README_FIRST.md` - This index file (you are here)
- `CONFIGURATION_AND_REFERENCE_INDEX.md` - Complete index of all config files

#### 📁 Development Tracking (Not Indexed)

- **📁 `/docs/Sessions/`** - Agent session memories and project handoffs
- **📁 `/docs/devlog/`** - Development logs and project completion reports

### 📁 `/src/` - Source Code

- **📁 `/src/giljo_mcp/`** - Core application
  - `__init__.py`, `__main__.py` - Package initialization and entry point
  - `server.py` - FastMCP server implementation
  - `models.py` - SQLAlchemy database models
  - `database.py` - Database connection manager
  - `orchestrator.py` - Project and agent orchestration
  - `mission_templates.py` - Dynamic mission generation system
  - `config.py`, `config_manager.py` - Configuration handling
  - `auth.py` - Authentication system
  - `tenant.py` - Multi-tenant isolation
  - `queue.py` - Message queue implementation
  - `discovery.py` - Dynamic context discovery
  - **📁 `/tools/`** - MCP tool implementations
    - `project.py` - Project management tools
    - `agent.py` - Agent management tools
    - `message.py` - Messaging tools
    - `context.py` - Context discovery tools
    - `chunking.py` - Vision document chunking

### 📁 `/tests/` - Test Suite (Code)

- Unit tests and integration tests for all modules
- Test fixtures and data
- **Documentation**: See `/docs/tests/` for test reports and validation

### 📁 `/api/` - API Layer (Code)

- FastAPI application
- REST endpoints
- WebSocket handlers
- **Documentation**: See `/docs/api/api_implementation_guide.md`

### 📁 `/frontend/` - User Interface (PARTIALLY CREATED)

**Already Provided**:

- `/frontend/public/favicon.ico` - ✅ Application favicon
- `/frontend/public/icons/` - ✅ All system icons ready to use
- `/frontend/public/mascot/` - ✅ Animated logo

**To Be Created**:

- Vue 3 application structure
- Components, views, stores
- Build configuration

### 📁 Documentation Organization

#### 📁 `/docs/docker/` - Docker Documentation

- `docker_setup_guide.md` - Complete Docker setup instructions
- `docker_deployment_guide.md` - Production deployment guide
- `docker_compose_plan.md` - Docker Compose configuration details
- **📁 `/docs/docker/tests/`** - Docker testing documentation
  - Test plans and reports
  - Health check patterns

#### 📁 `/docs/scripts/` - Scripts Documentation

- `scripts_setup_guide.md` - Setup and utility scripts documentation

#### 📁 `/docs/tests/` - Test Documentation

- `test_validation_checklist.md` - Testing checklist
- `TEST_VALIDATION_REPORT.md` - Complete validation report
- `WEBSOCKET_SECURITY_VALIDATION.md` - WebSocket security testing

#### 📁 `/docs/api/` - API Documentation

- `api_implementation_guide.md` - API implementation details

### 📁 `/scripts/` - Utility Scripts (Code - TO BE CREATED)

Will contain:

- Setup scripts
- Migration tools
- Development utilities

### 📁 `/docker/` - Container Definitions (Code)

Contains:

- Dockerfile
- docker-compose.yml
- Container configurations

## 🚀 Current Status

**Development Phase**: Phase 2 - MCP Integration (Project 2.2 Complete)
**Completed**: Projects 1.1-1.4 (Foundation) and 2.1-2.2 (MCP Tools)
**Next Step**: Project 2.3 - Orchestration Core

We're about to begin building this system using orchestration to manage its own development through 20 focused projects.

## 📝 How to Navigate This Project

1. **First Time?**

   - Read `README.md` for overview
   - Check `docs/Vision/VISION_DOCUMENT.md` for goals
   - Review `docs/PROJECT_ORCHESTRATION_PLAN.md` for development strategy

2. **Starting Development?**

   - Open `docs/PROJECT_CARDS.md` for ready-to-use project missions
   - Check `docs/PROJECT_FLOW_VISUAL.md` for dependencies
   - Read `docs/Sessions/` for context and decisions

3. **Contributing Code?**

   - Review `docs/TECHNICAL_ARCHITECTURE.md` for design patterns
   - **IMPORTANT**: Follow OS-neutral coding requirements (see Cross-Platform section)
   - Check `docs/PROVEN_FEATURES_TO_PRESERVE.md` for critical features

4. **Tracking Progress?**
   - Check `/docs/devlog/` for daily development logs
   - Review completed projects in orchestrator dashboard
   - Update session memories in `/docs/Sessions/`

## ⚠️ Critical Requirements

### OS-Neutral Code (MANDATORY)

All code MUST work on Windows, Mac, and Linux:

- Use `pathlib.Path()` for all file paths
- Never hardcode path separators
- Test on multiple platforms
- See `docs/TECHNICAL_ARCHITECTURE.md` for examples

### UI/UX Design Requirements

- **MUST use color themes from `/docs/color_themes.md`**
- Vue 3 + Vuetify 3 for components
- Dark/light mode support with theme colors
- All buttons, charts, and visuals follow theme
- WCAG 2.1 AA accessibility compliance

### Multi-Tenant Architecture

- Every operation must use tenant keys
- No single-product limitations
- Concurrent project support from day one

### Core Features Implemented

- Vision document chunking (50K+ tokens)
- Message acknowledgment arrays
- Dynamic discovery (no static indexing)
- Serena MCP integration

## 🎯 Development Workflow

1. **Create Project in Orchestrator**

   - Use missions from `docs/PROJECT_CARDS.md`
   - Follow phase order in `docs/PROJECT_FLOW_VISUAL.md`

2. **Monitor Progress**

   - Dashboard at http://localhost:5000
   - Check agent messages
   - Review generated code

3. **Document Progress**

   - Update `/docs/devlog/` daily
   - Add session memories
   - Track decisions and learnings

4. **Test Incrementally**
   - Don't wait until end
   - Test each project's deliverables
   - Verify cross-platform compatibility

## 📞 Quick References

- **Orchestrator Dashboard**: http://localhost:5000
- **Database**: PostgreSQL on localhost:5432
- **Python Version**: 3.8+
- **UI Framework**: Vue 3 + Vite
- **Target Timeline**: 4 weeks (20 projects)

## 🔄 Next Actions

1. Open orchestrator dashboard
2. Create Project 1.1: "GiljoAI Core Architecture"
3. Copy mission from `docs/PROJECT_CARDS.md`
4. Let orchestrator begin building
5. Document progress in `/docs/devlog/`

---

_This index will be updated as the project structure evolves during development._

**Last Updated**: January 2025
**Version**: 0.1.0-pre
