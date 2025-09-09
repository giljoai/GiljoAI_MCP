# GiljoAI MCP - Orchestration Project Cards

## How to Use These Cards

Each card below is ready to be created as a project in AKE-MCP. Copy the mission and use the suggested agents when creating the project through the dashboard or CLI.

---

## PHASE 1: FOUNDATION PROJECTS

### 🏗️ Project 1.1: Core Architecture & Database

**Create Project Command**:
```
Name: GiljoAI Core Architecture
Mission: Create the foundational structure for GiljoAI MCP with SQLAlchemy models supporting both SQLite and PostgreSQL. Set up project structure at F:/GiljoAI_MCP with /src/giljo_mcp/, /tests/, /docs/ directories. Implement DatabaseManager class with connection pooling, create all table models (projects, agents, messages, tasks, sessions), and set up Alembic migrations. Include tenant_key field in all models for multi-tenancy.
Agents: analyzer, architect, implementer, tester
```

**Success Criteria**:
- [ ] Project structure created
- [ ] Database models defined
- [ ] DatabaseManager working
- [ ] Migrations initialized
- [ ] Basic tests passing

---

### 🔐 Project 1.2: Multi-Tenant Schema

**Create Project Command**:
```
Name: GiljoAI Multi-Tenant Implementation  
Mission: Transform the database schema to support multiple concurrent products/projects using tenant_key isolation. Add tenant_key field to all tables, update DatabaseManager queries to filter by tenant_key, create TenantManager class for key generation and validation. Remove is_active limitation allowing unlimited concurrent products. Test isolation between tenants.
Agents: analyzer, architect, implementer, tester
```

**Success Criteria**:
- [ ] Tenant keys in all tables
- [ ] Queries properly scoped
- [ ] Key generation working
- [ ] Isolation verified
- [ ] No single-product limit

---

### ⚙️ Project 1.3: Basic Setup Script

**Create Project Command**:
```
Name: GiljoAI Setup Script
Mission: Create interactive setup.py script that guides users through initial configuration. Prompt for database choice (SQLite for local, PostgreSQL for server), collect credentials if PostgreSQL, generate .env file with all settings, create necessary directories, and provide platform-specific instructions. Make it work on Windows, Mac, and Linux with appropriate path handling.
Agents: analyzer, implementer, documenter
```

**Success Criteria**:
- [ ] Interactive prompts working
- [ ] .env file generated correctly
- [ ] Directories created
- [ ] Works on all platforms
- [ ] Clear instructions provided

---

### 📝 Project 1.4: Configuration Management

**Create Project Command**:
```
Name: GiljoAI Configuration System
Mission: Build configuration management supporting local/LAN/WAN modes. Create config.yaml structure with mode-specific settings, implement ConfigManager class that loads YAML and environment variables, support hot-reloading of configuration, validate all settings on load, and provide smart defaults. Enable mode detection based on configuration.
Agents: architect, implementer, tester
```

**Success Criteria**:
- [ ] config.yaml structure defined
- [ ] ConfigManager class working
- [ ] Environment override support
- [ ] Mode switching works
- [ ] Validation implemented

---

## PHASE 2: MCP INTEGRATION PROJECTS

### 🔧 Project 2.1: FastMCP Server Structure

**Create Project Command**:
```
Name: GiljoAI MCP Server Foundation
Mission: Create FastMCP server structure with proper tool organization and authentication. Set up server.py with FastMCP initialization, organize tools into logical groups (project, agent, messaging, context), implement API key authentication middleware for LAN/WAN modes, add health and ready endpoints, create startup sequence checking database and configuration.
Agents: architect, implementer, tester
```

**Success Criteria**:
- [ ] FastMCP server starts
- [ ] Tool groups organized
- [ ] Authentication ready
- [ ] Health checks working
- [ ] Startup sequence clean

---

### 🛠️ Project 2.2: Tool Implementation

**Create Project Command**:
```
Name: GiljoAI MCP Tools Implementation
Mission: Implement all 20 essential MCP tools with error handling. Create project tools (create_project, list_projects, switch_project, close_project, project_status), agent tools (activate_agent, assign_job, handoff, agent_health, decommission_agent), messaging tools (send_message, get_messages, acknowledge_message, complete_message, broadcast), and context tools (log_task, get_vision, get_product_settings, session_info, help). Each tool must validate inputs and handle errors gracefully.
Agents: analyzer, implementer, tester, documenter
```

**Success Criteria**:
- [ ] All 20 tools implemented
- [ ] Input validation complete
- [ ] Error handling robust
- [ ] Tools properly documented
- [ ] Integration tests passing

---

### 📚 Project 2.3: Vision Chunking System

**Create Project Command**:
```
Name: GiljoAI Vision Chunking
Mission: Port and enhance the vision document chunking system from AKE-MCP. Implement get_vision(part, max_tokens) that chunks documents over 25K tokens, breaks at natural line boundaries, returns total_parts and current_part metadata, creates vision index in database for navigation. Test with documents over 50K tokens ensuring reliable chunking.
Agents: analyzer, implementer, tester
```

**Success Criteria**:
- [ ] Chunking logic working
- [ ] Natural boundary breaking
- [ ] Index creation functional
- [ ] 50K+ documents handled
- [ ] Metadata accurate

---

### ✅ Project 2.4: Message Acknowledgment

**Create Project Command**:
```
Name: GiljoAI Message Acknowledgment
Mission: Implement complete message acknowledgment system with PostgreSQL arrays. Add acknowledged_by and completed_by arrays to messages, implement acknowledge_message and complete_message functions, add auto-acknowledgment when messages are retrieved, track acknowledgment timestamps, and prevent message deletion ensuring audit trail. Include message completion notes.
Agents: architect, implementer, tester
```

**Success Criteria**:
- [ ] Array fields working
- [ ] Acknowledgment tracking
- [ ] Auto-acknowledge on read
- [ ] Completion notes stored
- [ ] No message deletion

---

## PHASE 3: ORCHESTRATION PROJECTS

### 🎯 Project 3.1: Project/Agent Management

**Create Project Command**:
```
Name: GiljoAI Orchestration Core
Mission: Build orchestration engine for project and agent lifecycle management. Create ProjectOrchestrator class managing project states, implement agent spawning with role-based missions, build handoff mechanism for context limits, add context usage tracking with color indicators, and implement clean agent decommissioning. Support multiple concurrent projects per tenant.
Agents: analyzer, architect, implementer, tester
```

**Success Criteria**:
- [ ] Project lifecycle working
- [ ] Agent spawning functional
- [ ] Handoffs implemented
- [ ] Context tracking accurate
- [ ] Multi-project support

---

### 📬 Project 3.2: Message Queue & Routing

**Create Project Command**:
```
Name: GiljoAI Message Queue System
Mission: Implement database-backed message queue with intelligent routing. Create MessageQueue class with priority handling, implement broadcast messaging to all agents, add project-scoped message routing, build message monitoring with statistics, detect stuck messages, and ensure ACID compliance. Messages must never be lost even during crashes.
Agents: architect, implementer, tester
```

**Success Criteria**:
- [ ] Queue operations reliable
- [ ] Priority routing works
- [ ] Broadcast functional
- [ ] Statistics accurate
- [ ] Crash recovery tested

---

### 🔍 Project 3.3: Dynamic Discovery

**Create Project Command**:
```
Name: GiljoAI Dynamic Discovery
Mission: Implement dynamic context discovery system eliminating static indexing. Create priority-based discovery (vision → config → docs → memories), implement path resolution from configuration, add hooks for Serena MCP integration, build selective context loading based on agent role, ensure fresh reads without caching. Remove all static indexing code.
Agents: analyzer, architect, implementer
```

**Success Criteria**:
- [ ] Priority system working
- [ ] Dynamic path resolution
- [ ] Selective loading functional
- [ ] No static indexes
- [ ] Fresh context guaranteed

---

### 📋 Project 3.4: Orchestrator Templates

**Create Project Command**:
```
Name: GiljoAI Mission Templates
Mission: Create comprehensive mission generation system for orchestrators and agents. Port the proven orchestrator mission template with vision guardian and scope sheriff roles, add chunked vision reading instructions, create role-specific agent missions, ensure consistent behavior across all orchestrators, and include dynamic discovery instructions. Templates must be detailed and actionable.
Agents: analyzer, implementer, documenter
```

**Success Criteria**:
- [ ] Mission generator working
- [ ] Templates comprehensive
- [ ] Role-specific missions
- [ ] Consistent instructions
- [ ] Discovery guidance included

---

## PHASE 4: USER INTERFACE PROJECTS

### 🌐 Project 4.1: API Endpoints

**Create Project Command**:
```
Name: GiljoAI REST API
Mission: Build comprehensive FastAPI REST API for all system functions. Create project management endpoints (CRUD operations), agent control endpoints, message and task endpoints, configuration management endpoints, and statistics/monitoring endpoints. Include proper error handling, input validation, and OpenAPI documentation. Support both JSON and WebSocket responses.
Agents: architect, implementer, tester, documenter
```

**Success Criteria**:
- [ ] All endpoints implemented
- [ ] OpenAPI docs generated
- [ ] Validation working
- [ ] Error handling complete
- [ ] Tests comprehensive

---

### 💻 Project 4.2: Dashboard Foundation

**Create Project Command**:
```
Name: GiljoAI Dashboard UI
Mission: Create modern responsive dashboard using Vue 3 + Vite with Vuetify 3 components. Use provided assets from /frontend/public/ including favicon.ico, icons folder with all system icons, and mascot folder with animated logo. Implement project management interface, agent monitoring views with health indicators, message center with acknowledgment tracking, task management interface, and settings/configuration pages. Apply color themes from /docs/color_themes.md. Ensure mobile-responsive design. All icons and visual assets are already provided - focus on integration not asset creation.
Agents: analyzer, designer, implementer, tester
```

**Success Criteria**:
- [ ] Framework chosen and setup
- [ ] Core views implemented
- [ ] Responsive design working
- [ ] Navigation smooth
- [ ] Data binding functional

---

### ⚡ Project 4.3: Real-time WebSockets

**Create Project Command**:
```
Name: GiljoAI Real-time Updates
Mission: Add WebSocket support for real-time updates. Implement WebSocket server in FastAPI, create client-side connection management with auto-reconnect, stream agent status updates live, push message notifications instantly, show progress indicators for long operations, and handle connection drops gracefully. Dashboard must feel alive and responsive.
Agents: architect, implementer, tester
```

**Success Criteria**:
- [ ] WebSocket server working
- [ ] Auto-reconnect functional
- [ ] Live updates streaming
- [ ] Progress indicators smooth
- [ ] Connection resilient

---

### 🎨 Project 4.4: UI Polish & Themes

**Create Project Command**:
```
Name: GiljoAI UI Enhancement
Mission: Polish dashboard with professional UI/UX using color themes defined in /docs/color_themes.md. Implement dark/light theme switching with CSS variables from the provided palette, add smooth transitions and animations, create loading and error states with theme colors, implement toast notifications, add keyboard shortcuts for power users, ensure WCAG 2.1 AA accessibility standards, and make tables sortable/filterable. All colors, buttons, and visual elements MUST match the specifications in color_themes.md. UI must feel professional and cohesive with the brand identity.
Agents: designer, implementer, tester
```

**Success Criteria**:
- [ ] Theme switching works
- [ ] Animations smooth
- [ ] States well-designed
- [ ] Shortcuts functional
- [ ] Accessibility validated

---

## PHASE 5: DEPLOYMENT PROJECTS

### 🐳 Project 5.1: Docker Packaging

**Create Project Command**:
```
Name: GiljoAI Docker Deployment
Mission: Create Docker containers for easy deployment. Write multi-stage Dockerfile minimizing image size, create docker-compose.yml for full stack, handle environment variables properly, set up volume mappings for persistence, add health checks and restart policies, create both development and production configurations. Test on Windows Docker Desktop and Linux.
Agents: architect, implementer, tester, documenter
```

**Success Criteria**:
- [ ] Images build successfully
- [ ] Compose stack runs
- [ ] Volumes persist data
- [ ] Health checks pass
- [ ] Both dev/prod configs work

---

### 🧙 Project 5.2: Enhanced Setup Wizard

**Create Project Command**:
```
Name: GiljoAI Setup Enhancement
Mission: Create polished setup experience with smart defaults. Enhance setup.py with optional GUI using tkinter, add platform detection for OS-specific setup, check for dependencies and offer installation, create first-run wizard walking through configuration, add migration tool from AKE-MCP database, and import/export configuration capabilities. Make onboarding delightful.
Agents: analyzer, designer, implementer, tester
```

**Success Criteria**:
- [ ] GUI option working
- [ ] Platform detection accurate
- [ ] Dependencies checked
- [ ] Migration tool functional
- [ ] Import/export working

---

### 📖 Project 5.3: Documentation & Examples

**Create Project Command**:
```
Name: GiljoAI Documentation
Mission: Create comprehensive documentation and examples. Write clear README with 5-minute quickstart, create user guide covering all features, document all 20 MCP tools with examples, add 3 example projects showing different use cases, outline troubleshooting for common issues, and create architecture diagrams. Documentation must be searchable and versioned.
Agents: analyzer, writer, reviewer
```

**Success Criteria**:
- [ ] README compelling
- [ ] User guide complete
- [ ] Tool docs comprehensive
- [ ] Examples working
- [ ] Troubleshooting helpful

---

### ✔️ Project 5.4: Testing & Validation

**Create Project Command**:
```
Name: GiljoAI Test Suite
Mission: Create comprehensive test suite ensuring reliability. Write unit tests achieving 80%+ code coverage, create integration tests for full workflows, add load tests simulating 100+ concurrent agents, test multi-tenant isolation thoroughly, verify 50K+ token vision handling, test both SQLite and PostgreSQL modes, and create performance benchmarks. All tests must be automated.
Agents: analyzer, tester, implementer
```

**Success Criteria**:
- [ ] 80%+ coverage achieved
- [ ] Integration tests pass
- [ ] Load tests successful
- [ ] Isolation verified
- [ ] Performance acceptable

---

## Orchestration Tips

### Creating Projects in Order:
1. Start with Phase 1 projects (Foundation)
2. Each phase builds on the previous
3. Some projects within a phase can run in parallel
4. Use handoffs to pass context between projects

### Managing Context:
- Break large projects into smaller ones if needed
- Use project completion notes for handoffs
- Document decisions in session memories
- Keep vision document updated

### Monitoring Progress:
- Check dashboard regularly
- Review agent messages
- Validate deliverables
- Test incrementally

---

*These project cards are designed to be executed sequentially through the AKE-MCP orchestrator, building GiljoAI MCP systematically.*