# 📋 README_FIRST - GiljoAI MCP Project Index

## Welcome to GiljoAI MCP Development!

This is the root directory for the **GiljoAI MCP Coding Orchestrator** project - a complete rewrite of AKE-MCP with multi-tenant architecture and enhanced capabilities.

## 🗂️ Directory Structure & Contents

### 📁 Root Files
- **README.md** - Main project documentation and quick start guide
- **requirements.txt** - Python dependencies
- **.mcp.json** - MCP configuration file

### 📁 `/docs/` - Core Documentation
All critical documentation for the project:

- **📁 `/docs/Vision/`** - Vision documents (HIGHEST PRIORITY for orchestrator)
  - `VISION_DOCUMENT.md` - Main vision and roadmap
  
- **📁 `/docs/Sessions/`** - Development session memories
  - `session_001_initial_setup.md` - Initial configuration decisions
  - `session_002_configuration_and_assets.md` - Asset integration and AKE-MCP config
  - `First Memory.md` - Original planning session
  
- **📁 `/docs/devlog/`** - Development logs (track progress here)
  - `2025-01-09_project_inception.md` - Initial project setup
  - Daily development logs will be added as work progresses
  
- **Project Planning Documents**:
  - `PROJECT_CARDS.md` - Ready-to-use missions for orchestrator projects
  - `PROJECT_FLOW_VISUAL.md` - Visual timeline and dependencies
  - `PROJECT_ORCHESTRATION_PLAN.md` - Complete 20-project development strategy
  
- **Technical Documents**:
  - `TECHNICAL_ARCHITECTURE.md` - System design with OS-neutral requirements
  - `PRODUCT_PROPOSAL.md` - Business case and market positioning
  - `PROVEN_FEATURES_TO_PRESERVE.md` - Critical features from AKE-MCP
  - **`color_themes.md`** - 🎨 **MANDATORY UI color palette and theme specifications**
  - `README_FIRST.md` - This navigation index

### 📁 `/src/` - Source Code (TO BE CREATED)
Will contain:
- `/giljo_mcp/` - Main application code
- Python modules for orchestration, database, tools

### 📁 `/api/` - API Layer (TO BE CREATED)
Will contain:
- FastAPI application
- REST endpoints
- WebSocket handlers

### 📁 `/frontend/` - User Interface (PARTIALLY CREATED)
**Already Provided**:
- `/frontend/public/favicon.ico` - ✅ Application favicon
- `/frontend/public/icons/` - ✅ All system icons ready to use
- `/frontend/public/mascot/` - ✅ Animated logo

**To Be Created**:
- Vue 3 application structure
- Components, views, stores
- Build configuration

### 📁 `/tests/` - Test Suite (TO BE CREATED)
Will contain:
- Unit tests
- Integration tests
- Test fixtures

### 📁 `/scripts/` - Utility Scripts (TO BE CREATED)
Will contain:
- Setup scripts
- Migration tools
- Development utilities

### 📁 `/docker/` - Container Definitions (TO BE CREATED)
Will contain:
- Dockerfile
- docker-compose.yml
- Container configurations

## 🚀 Current Status

**Development Phase**: Pre-Foundation
**Next Step**: Create Project 1.1 in AKE-MCP orchestrator

We're about to begin building this system using the AKE-MCP orchestrator to manage its own development through 20 focused projects.

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
   - Review completed projects in AKE-MCP dashboard
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

### Preserved Features from AKE-MCP
- Vision document chunking (50K+ tokens)
- Message acknowledgment arrays
- Dynamic discovery (no static indexing)
- Serena MCP integration

## 🎯 Development Workflow

1. **Create Project in AKE-MCP**
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

- **AKE-MCP Dashboard**: http://localhost:5000
- **Database**: PostgreSQL on localhost:5432
- **Python Version**: 3.8+
- **UI Framework**: Vue 3 + Vite
- **Target Timeline**: 4 weeks (20 projects)

## 🔄 Next Actions

1. Open AKE-MCP dashboard
2. Create Project 1.1: "GiljoAI Core Architecture"
3. Copy mission from `docs/PROJECT_CARDS.md`
4. Let orchestrator begin building
5. Document progress in `/docs/devlog/`

---

*This index will be updated as the project structure evolves during development.*

**Last Updated**: January 2025
**Version**: 0.1.0-pre