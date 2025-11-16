# GiljoAI MCP Server - Single Source of Truth Workflow Documentation

**Version**: 3.1+
**Last Updated**: 2025-01-16
**Status**: Canonical Reference

---

## Table of Contents

1. [System Architecture Overview](#1-system-architecture-overview)
2. [Installation & Setup Flow](#2-installation--setup-flow)
3. [Initial Configuration Workflows](#3-initial-configuration-workflows)
4. [Product Management Workflow](#4-product-management-workflow)
5. [Project Management Workflow](#5-project-management-workflow)
6. [Task Management Workflow](#6-task-management-workflow)
7. [Agent Template Management](#7-agent-template-management)
8. [Project Orchestration Workflow (Jobs)](#8-project-orchestration-workflow-jobs)
9. [Agent Execution Workflows](#9-agent-execution-workflows)
10. [Messaging & Communication](#10-messaging--communication)
11. [MCP Tools Reference](#11-mcp-tools-reference)
12. [Admin & User Settings](#12-admin--user-settings)
13. [Key Concepts & Terminology](#13-key-concepts--terminology)

---

## 1. System Architecture Overview

### 1.1 Operational Architecture

```
┌─────────────────────────────────────────────────────────┐
│              GiljoAI MCP Server (LAN/WAN/Hosted)        │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌────────────────┐    ┌──────────────────┐           │
│  │  Web Frontend  │    │  MCP over HTTP   │           │
│  │  Visualization │    │  Server          │           │
│  │  (Vue 3)       │    │                  │           │
│  └────────┬───────┘    └────────┬─────────┘           │
│           │                     │                      │
│           └──────────┬──────────┘                      │
│                      │                                 │
│           ┌──────────▼───────────┐                     │
│           │  Backend (FastAPI)   │                     │
│           │  + PostgreSQL DB     │                     │
│           └──────────────────────┘                     │
└─────────────────────────────────────────────────────────┘
                       │
         ┌─────────────┼─────────────┐
         │             │             │
    ┌────▼───┐    ┌────▼───┐   ┌────▼───┐
    │Browser │    │  MCP   │   │  MCP   │
    │        │    │Enabled │   │Enabled │
    │        │    │CLI Tool│   │CLI Tool│
    └────────┘    └────────┘   └────────┘
   Developer PC  Developer PC  Developer PC
```

**Key Components**:
- **Web Frontend**: Port 7274 (Vuetify + Vue 3)
- **Backend API**: Port 7272 (FastAPI)
- **Database**: PostgreSQL 18+ (required, not SQLite)
- **MCP Protocol**: HTTP (not STDIO)
- **Multi-Tenant**: API key/Bearer token isolation

### 1.2 Multi-User Architecture

Multiple developers can connect simultaneously:
- Each tenant has isolated data space
- Unique API/Bearer keys per tenant
- Separate agent templates, products, projects
- Isolated message threads

### 1.3 Application Layers

```
┌──────────────────────────────────────────────────┐
│         PostgreSQL Database (Multi-Tenant)       │
├──────────────────────────────────────────────────┤
│    Tenant Management (Users, Admin Controls)     │
├──────────────────────────────────────────────────┤
│          MCP Integration Layer                   │
│  • CLI Tool Integration (Claude, Codex, Gemini)  │
│  • Slash Command Setup                           │
│  • Agent Template Import/Export                  │
├──────────────────────────────────────────────────┤
│            Core Business Logic                   │
│  • Task, Product, Project Management             │
│  • Jobs Management (MCPAgentJob)                 │
│  • Context Management with Priority Assignment   │
├──────────────────────────────────────────────────┤
│         Agent Orchestration Layer                │
│  • Agent Templates (Max 8 types active)          │
│  • Mission Generation (Database-driven)          │
│  • Job Assignment & Status Tracking              │
│  • Message Center (agent_communication_queue)    │
└──────────────────────────────────────────────────┘
```

**Critical Features**:
- **OS Agnostic**: Cross-platform Python/FastAPI
- **Public IP Access**: Not localhost-only for users
- **Localhost Internal**: Backend ↔ Frontend ↔ PostgreSQL communication
- **MCP over HTTP**: Not STDIO (network-based)
- **Auth Always Enabled**: No defaults (admin created via /welcome)

---

## 2. Installation & Setup Flow

### 2.1 Installation Process

```
┌─────────────────────┐
│ Download from       │
│ GitHub              │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Run:                │
│ python startup.py   │  ← Single command for everything
│                     │
│ (OS Agnostic)       │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ First Run Detection │
│ (Checks for admin)  │
└──────────┬──────────┘
           │
    ┌──────▼──────┐
    │ Admin user  │
    │ exists?     │
    └──────┬──────┘
           │
    ┌──────▼─────────┐
    │ NO             │ YES
    │                │
    ▼                ▼
┌─────────────┐  ┌────────────────┐
│Setup Wizard │  │Start Services  │
│Opens in     │  │& Dashboard     │
│Browser      │  └────────────────┘
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────┐
│ Setup Steps (Interactive):          │
│ 1. IP address binding config        │
│ 2. PostgreSQL check (creds test)    │
│ 3. Dependency install                │
│ 4. Database setup (migrations)       │
│ 5. Agent template seeding            │
│ 6. Admin user creation (FIRST)       │
│ 7. Launch instructions displayed     │
└─────────────────────────────────────┘
```

**Installation Details**:
- **Command**: `python startup.py` (one command for everything)
- **First Run**: Automatically detects no admin → launches setup wizard
- **Subsequent Runs**: Detects admin → starts services + opens dashboard
- **Database**: PostgreSQL 18+ required (password: typically "4010" for dev)
- **Dependencies**: Auto-installed via requirements.txt
- **Agent Templates**: Seeded during first run (8 default types)

### 2.2 First Run Configuration

```
┌──────────────────────┐
│ Browse to:           │
│ http://{ip}:7274/    │
│ setup                │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ Setup Wizard Steps:  │
│                      │
│ Step 1: Admin User   │
│ Step 2: Database     │
│ Step 3: Network      │
│ Step 4: MCP Tools    │
│ Step 5: Serena (opt) │
│ Step 6: Complete     │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ Admin Created        │
│ → Tenant Created     │
│ → Welcome Dashboard  │
└──────────────────────┘
```

**Key Points**:
- No default admin/admin credentials
- First user becomes admin
- Tenant auto-created for admin
- Authentication always enabled

---

## 3. Initial Configuration Workflows

### 3.1 Application Setup Overview

After first login, navigate to **User Settings** for initial configuration:

```
┌─────────────────┐
│ User Settings   │
│ Menu            │
└────────┬────────┘
         │
    ┌────▼────────────────────────────────────┐
    │                                         │
    ▼                                         ▼
┌─────────────────┐                  ┌─────────────────┐
│ 1. MCP Setup    │                  │ 4. Context      │
│ (Tool Attach)   │                  │ Priority Setup  │
└────────┬────────┘                  └─────────────────┘
         │
         ▼
┌─────────────────┐
│ 2. Slash        │
│ Commands Setup  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 3. Serena MCP   │
│ Enable/Config   │
└─────────────────┘
```

### 3.2 MCP CLI Setup Workflow

**Purpose**: Connect Claude Code CLI, Codex CLI, or Gemini CLI to GiljoAI MCP Server

```
┌──────────────────┐
│ User Settings    │
│ → Integrations   │
│ → MCP Setup      │
└────────┬─────────┘
         │
         ▼
┌───────────────────────────────────────┐
│ Auto-Generated Prompt (Static)        │
│ • Includes tenant-specific API key    │
│ • Format varies by CLI tool:          │
│   - Claude Code: API Key              │
│   - Codex: Bearer Key                 │
│   - Gemini: API Key                   │
└────────┬──────────────────────────────┘
         │
         ▼
┌──────────────────┐
│ User copies      │
│ prompt and       │
│ pastes in CLI    │
│ terminal         │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ MCP configures   │
│ per CLI syntax   │
│ (JSON config)    │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ CLI tool now     │
│ authenticated    │
│ to tenant ID     │
└──────────────────┘
```

**Alternative**: Direct download link for manual ZIP installation

### 3.3 Slash Command Setup Workflow

**Purpose**: Install GiljoAI slash commands into CLI tool

```
┌──────────────────┐
│ User Settings    │
│ → Integrations   │
│ → Slash Commands │
└────────┬─────────┘
         │
         ▼
┌───────────────────────────────────────┐
│ Copyable Prompt (Static)              │
│ • Downloads ZIP from server           │
│ • Installs to .claude/commands/       │
└────────┬──────────────────────────────┘
         │
         ▼
┌──────────────────┐
│ Paste in CLI     │
│ → Agent downloads│
│ → ZIP extracts   │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Reboot CLI tool  │
│ → Commands appear│
└────────┬─────────┘
         │
         ▼
┌──────────────────────────────┐
│ Slash commands now available:│
│ /gil_create_task             │
│ /gil_activate_project        │
│ /gil_handover                │
│ (Requires MCP connection)    │
└──────────────────────────────┘
```

**Note**: Slash commands require connected MCP server to function

### 3.4 Agent Template Export (Claude Code CLI Only)

**Purpose**: Install agent templates for Claude Code subagent system

```
┌──────────────────┐
│ User Settings    │
│ → Integrations   │
│ → Agent Import   │
└────────┬─────────┘
         │
         ▼
┌───────────────────────────────────────┐
│ Copyable Prompt (Static)              │
│ • Downloads enabled agent *.md files  │
│ • Installs to .claude/agents/         │
│ • Uses download token (15-min TTL)    │
└────────┬──────────────────────────────┘
         │
         ▼
┌──────────────────┐
│ Paste in Claude  │
│ Code CLI         │
│ → Agents download│
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Reboot Claude    │
│ Code CLI         │
│ → Templates load │
└────────┬─────────┘
         │
         ▼
┌──────────────────────────────┐
│ Subagents now available for  │
│ orchestration (max 8 types)  │
└──────────────────────────────┘
```

**Note**: Only enabled agent templates are exported (managed via Agent Template Manager)

### 3.5 Serena MCP Integration Setup

**Purpose**: Enable Serena's symbolic code navigation tools

```
┌──────────────────┐
│ User Settings    │
│ → Integrations   │
│ → Serena MCP     │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Enable/Disable   │
│ Toggle           │
└────────┬─────────┘
         │
         ▼
┌───────────────────────────────────────┐
│ Advanced Settings (Optional):         │
│ • Use in Prompts                      │
│ • Tailor by Mission Type              │
│ • Dynamic Tool Catalog                │
│ • Prefer Range Reads                  │
│ • Max Range Lines                     │
│ • Context Halo Lines                  │
└────────┬──────────────────────────────┘
         │
         ▼
┌───────────────────────────────────────┐
│ Effect:                               │
│ • Modifies orchestrator prompts       │
│ • Tells agents about Serena tools     │
│ • Enables find_symbol(), get_symbols  │
└───────────────────────────────────────┘
```

**When Enabled**: Orchestrator and agents receive instructions about Serena symbolic code navigation tools

### 3.6 Context Priority Configuration

**Purpose**: Configure which product fields are prioritized during perpetual context management

```
┌──────────────────┐
│ User Settings    │
│ → Context        │
└────────┬─────────┘
         │
         ▼
┌───────────────────────────────────────────────┐
│ Field Priority Configuration (Drag & Drop):   │
│                                               │
│ Priority 1: Vision Document                   │
│ Priority 2: Tech Stack                        │
│ Priority 3: Product Description               │
│ Priority 4: Project Description               │
│ Priority 5: Agent Behavior Settings           │
│ Priority 6: Testing Methodology               │
│ ...                                           │
└────────┬──────────────────────────────────────┘
         │
         ▼
┌───────────────────────────────────────────────┐
│ Effect During Orchestration:                  │
│ • Fields included top-to-bottom               │
│ • Stops when context budget reached           │
│ • Enables perpetual context management        │
│ • Stored in user settings (tenant-specific)   │
└───────────────────────────────────────────────┘
```

**Default Budget**: 150,000 tokens (configurable)
**Purpose**: Manage perpetual context across long-running projects without hitting limits

---

## 4. Product Management Workflow

### 4.1 Product Creation Flow

```
┌──────────────────┐
│ Create Product   │
└────────┬─────────┘
         │
         ▼
┌────────────────────────────────────┐
│ Product Name & Description         │
│ (Used as Context Source)           │
└────────┬───────────────────────────┘
         │
         ▼
┌────────────────────────────────────┐
│ Project Path (Optional)            │
│ (Future Use)                       │
└────────┬───────────────────────────┘
         │
         ▼
┌────────────────────────────────────┐
│ Vision Document Upload             │
│ • Chunked for RAG                  │
│ • <25K tokens per chunk            │
│ • Multiple docs supported          │
│ (Used as Context Source)           │
└────────┬───────────────────────────┘
         │
         ▼
┌────────────────────────────────────┐
│ Tech Stack Fields (Several)        │
│ • Language, Framework, Database    │
│ • Infrastructure, Deployment       │
│ (Used as Context Source)           │
└────────┬───────────────────────────┘
         │
         ▼
┌────────────────────────────────────┐
│ Additional Product Fields:         │
│ • Agent Behavior Settings          │
│ • Test Methodology                 │
│ • Execution Methodologies          │
│ (Used as Context Source)           │
└────────┬───────────────────────────┘
         │
         ▼
┌────────────────────────────────────┐
│ Save Product                       │
│ → Creates Product ID               │
│ → Added in INACTIVE state          │
│ → Appears as card in UI            │
└────────────────────────────────────┘
```

**Important Notes**:
- Product form is actively saved in session cache (navigate back/forth without losing data)
- Only one product can be active per tenant at any time
- Product data serves as primary context source for orchestration

### 4.2 Product Activation Workflow

```
┌──────────────────┐
│ Existing Product │
│ Card             │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Click Activate   │
└────────┬─────────┘
         │
    ┌────▼────┐
    │ Another │
    │ product │
    │ active? │
    └────┬────┘
         │
    ┌────▼────┬────────┐
    │ YES     │ NO     │
    │         │        │
    ▼         ▼        │
┌─────────┐  │        │
│ Warning │  │        │
│ "Will   │  │        │
│ deact." │  │        │
└────┬────┘  │        │
     │       │        │
     ▼       ▼        │
┌──────────────┐      │
│ Deactivate   │      │
│ Other Product│      │
└──────┬───────┘      │
       │              │
       ▼              │
┌───────────────────┐ │
│ Deactivate Any    │ │
│ Active Projects   │ │
└────────┬──────────┘ │
         │            │
         └────┬───────┘
              │
              ▼
┌──────────────────────┐
│ New Product Activated│
│ • Badge on card      │
│ • Badge in header    │
└──────────────────────┘
```

**Constraint**: Only one active product per tenant (enforced at database level)

---

## 5. Project Management Workflow

### 5.1 Project Creation Workflow

```
┌──────────────────┐
│ Create Project   │
└────────┬─────────┘
         │
         ▼
┌─────────────────────────────────────┐
│ Project Name                        │
└────────┬────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│ Project Description (IMPORTANT)     │
│ • Human-written requirements        │
│ • INPUT for orchestrator to analyze │
│ • NOT the AI-generated mission      │
│ (Used as Context Source)            │
└────────┬────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│ Context Budget (Optional)           │
│ • Default: 150,000 tokens           │
│ • Manages perpetual context         │
└────────┬────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│ Mission Field (Display Only)        │
│ • Shows if AI-generated mission     │
│ • Populated during staging          │
│ • NOT editable by user              │
└────────┬────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│ Save Project                        │
│ → Project appears in list           │
│ → Default: INACTIVE status          │
└─────────────────────────────────────┘
```

**Critical Distinction**:
- **Project.description**: User-written requirements (INPUT)
- **Project.mission**: AI-generated execution plan (OUTPUT - created during staging)

### 5.2 Project Activation Workflow

```
┌──────────────────┐
│ Project List     │
│ (Select Project) │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Click Activate   │
└────────┬─────────┘
         │
    ┌────▼─────┐
    │ Already  │
    │ active   │
    │ project? │
    └────┬─────┘
         │
    ┌────▼───┬────────┐
    │ YES    │ NO     │
    │        │        │
    ▼        ▼        │
┌────────────┐        │
│ Deactivate │        │
│ Current    │        │
│ Active     │        │
│ Project    │        │
└──────┬─────┘        │
       │              │
       └──────┬───────┘
              │
              ▼
┌───────────────────────────┐
│ New Project Activated     │
│ → status = 'active'       │
│ → Dynamic link created:   │
│   /projects/{id}?via=jobs │
└──────┬────────────────────┘
       │
       ▼
┌───────────────────────────┐
│ Navigation Available:     │
│ • [Launch Project] button │
│ • Jobs sidebar link       │
└───────────────────────────┘
```

**Endpoint**: `POST /api/v1/projects/{project_id}/activate`
**Constraint**: Only one active project per product (enforced)

### 5.3 Project Modification & States

**Project States**:
- `inactive`: Created but not selected
- `active`: Currently selected for work
- `staging`: Orchestrator generating mission (transient)
- `running`: Jobs in progress
- `paused`: Temporarily stopped (can reactivate)
- `completed`: All work finished
- `cancelled`: Stopped permanently (can restore)

**State Transitions**:
```
inactive → activate() → active → launch() → staging
staging → (orchestrator done) → running
running → complete() → completed
running → cancel() → cancelled
active → deactivate() → paused
paused → activate() → active
cancelled → restore() → inactive
```

**Important**:
- Cancelled/Completed/Deactivated projects keep ALL data (mission, agents, messages)
- Can be re-activated or restored
- Soft delete with 10-day expiry for deleted projects

---

## 6. Task Management Workflow

### 6.1 Task Creation Flow

```
┌──────────────────┐
│ Create Task      │
│ (Web or Slash)   │
└────────┬─────────┘
         │
    ┌────▼──────────────┐
    │ Via Web UI        │ Via Slash Command
    │                   │
    ▼                   ▼
┌─────────────┐   ┌──────────────────┐
│ Task Name   │   │ /gil_create_task │
│ Settings    │   │ "content here"   │
│ • Priority  │   │                  │
│ • Status    │   │ → Dumps to list  │
│ • Desc      │   │ → Random name    │
└──────┬──────┘   │ → Default        │
       │          │   settings       │
       │          └──────┬───────────┘
       └─────────────────┘
                  │
                  ▼
┌───────────────────────────────────────┐
│ Active Product?                       │
└────────┬──────────────────────────────┘
         │
    ┌────▼────┬────────┐
    │ YES     │ NO     │
    │         │        │
    ▼         ▼        │
┌────────────────┐     │
│ Tagged with    │     │
│ Product ID     │     │
└──────┬─────────┘     │
       │               │
       │          ┌────▼────┐
       │          │ NULL    │
       │          │ Tagged  │
       │          └────┬────┘
       │               │
       └───────┬───────┘
               │
               ▼
┌──────────────────────────┐
│ Task appears in list     │
│ • Product-scoped tasks   │
│   show when product      │
│   active                 │
│ • NULL tasks show always │
└──────────────────────────┘
```

**Task Properties**:
- **Status**: To Do, In Progress, Completed
- **Priority**: Low, Medium, High
- **Description**: User-written details
- **Convert to Project**: Available when product active

### 6.2 Task Conversion to Project

```
┌──────────────────┐
│ Task with Active │
│ Product          │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Click "Convert   │
│ to Project"      │
└────────┬─────────┘
         │
         ▼
┌─────────────────────────────────┐
│ New Project Created:            │
│ • Name: Task name               │
│ • Description: Task description │
│ • Product ID: Active product    │
│ • Status: INACTIVE (default)    │
└─────────────────────────────────┘
```

**Constraint**: Can only convert tasks to projects when a product is active

---

## 7. Agent Template Management

### 7.1 Agent Template System

**Agent Types** (Max 8 active types simultaneously):
- Orchestrator (protected, admin-only edit)
- Implementer
- Tester
- Reviewer
- Documenter
- Frontend Agent
- Backend Agent
- DevOps Agent
- (User-defined types)

**Unlimited Instances**: Multiple agents of same type can be assigned (e.g., Implementer_1, Implementer_2)

### 7.2 Agent Template Workflow

```
┌──────────────────────────┐
│ Installation seeds       │
│ 8 default agent types    │
│ (Unique per tenant)      │
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│ Agent Template Manager   │
│ (User Settings → Agents) │
└──────────┬───────────────┘
           │
      ┌────▼────────────────────┐
      │ Agent Actions:          │
      │ • Edit Template         │
      │ • Duplicate             │
      │ • Version History       │
      │ • Preview               │
      │ • Compare w/ Default    │
      │ • Reset to Default      │
      │ • Delete                │
      │ • Enable/Disable        │
      └──────┬──────────────────┘
             │
        ┌────▼────┐
        │ Enable  │
        │ Agent?  │
        └────┬────┘
             │
        ┌────▼────┬────────┐
        │ YES     │ NO     │
        │         │        │
        ▼         ▼        │
┌───────────────────┐      │
│ Agent Enabled     │      │
│ • *.md created    │      │
│ • Staged on server│      │
│ • Available for   │      │
│   orchestrator    │      │
│ • Exportable to   │      │
│   Claude Code CLI │      │
└────────┬──────────┘      │
         │                 │
         └────────┬────────┘
                  │
                  ▼
┌───────────────────────────────┐
│ Only Enabled Agents:          │
│ • Appear in orchestrator      │
│   selection pool              │
│ • Can be spawned for jobs     │
│ (Max 8 agent types enabled)   │
└───────────────────────────────┘
```

**Agent Template Fields**:
- **Name**: Human-readable identifier
- **Role**: Brief description (e.g., "Implements backend features")
- **Template**: Markdown instructions with {placeholders}
- **Tool Access**: MCP tools available to agent
- **Active**: Enable/disable toggle

**Orchestrator Protection**:
- Orchestrator template can only be edited in Admin Settings
- Warnings displayed when modifying
- Critical for system functionality

---

## 8. Project Orchestration Workflow (Jobs)

This is the core workflow where projects transform into executable agent work.

### 8.1 Jobs Page Access

```
┌──────────────────┐
│ Project Activated│
└────────┬─────────┘
         │
         ▼
┌───────────────────────────────────┐
│ Dynamic Link Created:             │
│ http://{host}:7274/projects/      │
│ {project_id}?via=jobs             │
└────────┬──────────────────────────┘
         │
         ▼
┌───────────────────────────────────┐
│ Access via:                       │
│ • [Launch Project] button (list)  │
│ • Jobs sidebar link               │
└────────┬──────────────────────────┘
         │
         ▼
┌───────────────────────────────────┐
│ Jobs Page Opened                  │
│ → TAB: "Launch" (default view)    │
└───────────────────────────────────┘
```

### 8.2 Project Staging Workflow (Part 1 - Preparation)

**Initial State**: Jobs page, "Launch" tab

```
┌────────────────────────────────────┐
│ Launch Tab UI Elements:            │
│                                    │
│ ┌────────────────────────┐         │
│ │ [> Activate Project]   │         │
│ │ Button                 │         │
│ └────────────────────────┘         │
│                                    │
│ ┌────────────────────────┐         │
│ │ Project Description    │         │
│ │ (Editable)             │         │
│ └────────────────────────┘         │
│                                    │
│ ┌────────────────────────┐         │
│ │ Orchestrator Generated │         │
│ │ Mission (Empty)        │         │
│ └────────────────────────┘         │
│                                    │
│ ┌────────────────────────┐         │
│ │ Orchestrator Agent Card│         │
│ │ - agent_ID: {uuid}     │         │
│ │ - Role: Coordinator    │         │
│ └────────────────────────┘         │
└────────────────────────────────────┘
```

### 8.3 Project Staging Workflow (Part 2 - Orchestrator Execution)

**User Action**: Click **[> Activate Project]** button

```
┌────────────────────────────────────┐
│ Button Click                       │
└──────────┬─────────────────────────┘
           │
           ▼
┌────────────────────────────────────────────────┐
│ Backend: ProjectService.launch_project()       │
│ → Creates orchestrator MCPAgentJob             │
│ → Status: "waiting"                            │
│ → Stores in database                           │
└──────────┬─────────────────────────────────────┘
           │
           ▼
┌────────────────────────────────────────────────┐
│ Frontend: Display Thin Orchestrator Prompt    │
│ → Copyable text (~10 lines)                    │
│ → Includes orchestrator_id                     │
│ → Includes tenant_key                          │
│ → Instructions to fetch from MCP               │
└──────────┬─────────────────────────────────────┘
           │
           ▼
┌────────────────────────────────────┐
│ USER ACTION:                       │
│ Copy thin prompt → Paste in CLI    │
└──────────┬─────────────────────────┘
           │
           ▼
┌────────────────────────────────────────────────┐
│ Orchestrator (in CLI Terminal):               │
│                                                │
│ Step 1: Health check                          │
│   → health_check()                             │
│                                                │
│ Step 2: Fetch instructions via MCP            │
│   → get_orchestrator_instructions(             │
│       orchestrator_id='{uuid}',                │
│       tenant_key='{key}'                       │
│     )                                          │
│                                                │
│ Returns:                                       │
│ {                                              │
│   "project_description": "User requirements",  │
│   "mission": "Condensed context with           │
│               field priorities applied",       │
│   "product_context": "Vision + Tech Stack",    │
│   "agent_templates": [list of enabled agents], │
│   "field_priorities": {priority config},       │
│   "context_budget": 150000,                    │
│   "estimated_tokens": 6000                     │
│ }                                              │
└──────────┬─────────────────────────────────────┘
           │
           ▼
┌────────────────────────────────────────────────┐
│ Orchestrator Analyzes Context:                │
│                                                │
│ 1. READ Project.description (requirements)     │
│ 2. ANALYZE requirements vs product vision      │
│ 3. BREAK DOWN into agent-specific work items  │
│ 4. CREATE condensed mission plan               │
│ 5. SELECT appropriate agents from templates    │
│ 6. ASSIGN work to each agent                   │
└──────────┬─────────────────────────────────────┘
           │
           ▼
┌────────────────────────────────────────────────┐
│ Orchestrator Persists Mission:                │
│   → update_project_mission(                    │
│       project_id='{uuid}',                     │
│       mission='Generated mission plan',        │
│       tenant_key='{key}'                       │
│     )                                          │
│                                                │
│ → WebSocket event broadcasts to UI             │
│ → Mission appears in Jobs window               │
└──────────┬─────────────────────────────────────┘
           │
           ▼
┌────────────────────────────────────────────────┐
│ Orchestrator Spawns Agent Jobs:               │
│                                                │
│ For each selected agent:                      │
│   spawn_agent_job(                             │
│     agent_type='implementer',                  │
│     agent_name='Backend Implementer',          │
│     mission='Build user auth module...',       │
│     project_id='{uuid}',                       │
│     tenant_key='{key}',                        │
│     parent_job_id='{orchestrator_id}'          │
│   )                                            │
│                                                │
│ Returns: {                                     │
│   agent_job_id: '{uuid}',                      │
│   agent_prompt: '~10 line thin prompt'         │
│ }                                              │
│                                                │
│ → WebSocket events update UI                   │
│ → Agent cards appear with job IDs              │
└──────────┬─────────────────────────────────────┘
           │
           ▼
┌────────────────────────────────────┐
│ UI Updates:                        │
│ • Mission displayed                │
│ • Agent cards shown with IDs       │
│ • [Launch Jobs] button enabled     │
│ • Tab: "Implementation" available  │
└────────────────────────────────────┘
```

**Critical MCP Tools Used**:
- `health_check()`: Verify MCP connection
- `get_orchestrator_instructions()`: Fetch context for staging
- `update_project_mission()`: Persist generated mission
- `spawn_agent_job()`: Create agent jobs with database-stored missions

**Database-Driven Prompts**:
- Agent missions stored in `MCPAgentJob.mission` field
- Thin prompts (~10 lines) reference database-stored content
- Orchestrator fetches full context via MCP (not copy-paste)

### 8.4 Jobs Page State After Staging

**Launch Tab** now shows:
```
┌────────────────────────────────────┐
│ ✓ Mission Generated                │
│                                    │
│ ┌────────────────────────┐         │
│ │ Orchestrator Mission:  │         │
│ │                        │         │
│ │ Phase 1: Setup Auth    │         │
│ │ Phase 2: Implement API │         │
│ │ Phase 3: Testing       │         │
│ │ Phase 4: Documentation │         │
│ └────────────────────────┘         │
│                                    │
│ Agent Cards:                       │
│ ┌────────────────────────┐         │
│ │ Orchestrator           │         │
│ │ ID: abc123             │         │
│ │ Status: waiting        │         │
│ └────────────────────────┘         │
│                                    │
│ ┌────────────────────────┐         │
│ │ Backend Implementer    │         │
│ │ ID: def456             │         │
│ │ Job: Build auth module │         │
│ │ Status: waiting        │         │
│ └────────────────────────┘         │
│                                    │
│ ┌────────────────────────┐         │
│ │ Tester                 │         │
│ │ ID: ghi789             │         │
│ │ Job: Validate auth     │         │
│ │ Status: waiting        │         │
│ └────────────────────────┘         │
│                                    │
│ ┌────────────────────────┐         │
│ │ [Launch Jobs]          │         │
│ └────────────────────────┘         │
└────────────────────────────────────┘
```

---

## 9. Agent Execution Workflows

### 9.1 Implementation Tab Overview

**User Action**: Click **[Launch Jobs]** after staging complete

```
┌────────────────────────────────────┐
│ Navigate to: "Implementation" Tab  │
└──────────┬─────────────────────────┘
           │
           ▼
┌────────────────────────────────────────────────┐
│ Implementation Tab UI:                         │
│                                                │
│ ┌────────────────────────────────┐             │
│ │ Mode Toggle:                   │             │
│ │ ○ Claude Code CLI Mode         │             │
│ │ ● Legacy CLI Mode (default)    │             │
│ └────────────────────────────────┘             │
│                                                │
│ Orchestrator Card:                             │
│ ┌────────────────────────────────┐             │
│ │ [Copy Prompt] (Legacy)         │             │
│ │ [Disabled] (Claude Code)       │             │
│ └────────────────────────────────┘             │
│                                                │
│ Agent Cards (Dynamic based on mode):           │
│ ┌────────────────────────────────┐             │
│ │ Backend Implementer            │             │
│ │ [Copy Prompt] (Legacy)         │             │
│ │ [Disabled] (Claude Code)       │             │
│ └────────────────────────────────┘             │
└────────────────────────────────────────────────┘
```

### 9.2 Claude Code CLI Mode (Single Terminal, Subagents)

**When Toggled**: Claude Code CLI mode selected

```
┌────────────────────────────────────┐
│ Mode: Claude Code CLI              │
└──────────┬─────────────────────────┘
           │
           ▼
┌────────────────────────────────────────────────┐
│ UI Changes:                                    │
│ • Orchestrator [Copy Prompt] ENABLED           │
│ • All agent [Copy Prompt] buttons DISABLED     │
│ • Instructions: "Copy orchestrator prompt only"│
└──────────┬─────────────────────────────────────┘
           │
           ▼
┌────────────────────────────────────┐
│ USER ACTION:                       │
│ Copy orchestrator prompt           │
│ → Paste in SINGLE Claude Code CLI  │
└──────────┬─────────────────────────┘
           │
           ▼
┌────────────────────────────────────────────────┐
│ Orchestrator in Claude Code CLI:              │
│                                                │
│ 1. Fetches mission (already done)              │
│ 2. Reads spawned agent jobs from database      │
│ 3. Uses Claude Code's NATIVE subagent system   │
│ 4. Spawns subagents using built-in Task tool   │
│ 5. Coordinates parallel or sequential work     │
│                                                │
│ Subagents automatically:                       │
│ • Fetch missions via get_agent_mission()       │
│ • Execute work in background                   │
│ • Report progress via MCP tools                │
│ • Coordinate via message queue                 │
└──────────┬─────────────────────────────────────┘
           │
           ▼
┌────────────────────────────────────┐
│ SINGLE TERMINAL WORKFLOW           │
│ • Orchestrator manages all         │
│ • Subagents run in background      │
│ • Progress visible in dashboard    │
└────────────────────────────────────┘
```

**Advantages**:
- Single terminal window
- Native Claude Code subagent coordination
- Automatic agent lifecycle management
- Built-in parallelization

### 9.3 Legacy CLI Mode (Multiple Terminals, Manual)

**When Toggled**: Legacy CLI mode selected (default)

```
┌────────────────────────────────────┐
│ Mode: Legacy CLI                   │
└──────────┬─────────────────────────┘
           │
           ▼
┌────────────────────────────────────────────────┐
│ UI Changes:                                    │
│ • Orchestrator [Copy Prompt] ENABLED           │
│ • All agent [Copy Prompt] buttons ENABLED      │
│ • Instructions: "Launch orchestrator first     │
│   to determine parallel vs sequential"         │
└──────────┬─────────────────────────────────────┘
           │
           ▼
┌────────────────────────────────────┐
│ USER ACTION 1:                     │
│ Copy orchestrator prompt           │
│ → Paste in Terminal 1 (Orchestrator│
│   window)                          │
└──────────┬─────────────────────────┘
           │
           ▼
┌────────────────────────────────────────────────┐
│ Orchestrator Terminal:                         │
│ • Determines work order                        │
│ • Instructs via message queue                  │
│ • Monitors progress                            │
│ • Unlocks individual agent prompts in UI       │
└──────────┬─────────────────────────────────────┘
           │
           ▼
┌────────────────────────────────────┐
│ USER ACTION 2:                     │
│ Copy each agent prompt             │
│ → Paste in separate terminals:     │
│   Terminal 2: Backend Implementer  │
│   Terminal 3: Tester               │
│   Terminal 4: Reviewer             │
│   etc.                             │
└──────────┬─────────────────────────┘
           │
           ▼
┌────────────────────────────────────┐
│ MULTIPLE TERMINAL WORKFLOW         │
│ • Each agent in own window         │
│ • Manual coordination              │
│ • Progress visible in dashboard    │
└────────────────────────────────────┘
```

**Supports**: Claude Code CLI, Codex CLI, Gemini CLI

### 9.4 Agent Execution Flow (Both Modes)

**Common Pattern** for all agents:

```
┌────────────────────────────────────┐
│ Agent Started (via paste)          │
└──────────┬─────────────────────────┘
           │
           ▼
┌────────────────────────────────────────────────┐
│ Agent Thin Prompt (~10 lines):                │
│                                                │
│ I am Backend Implementer (Agent implementer).  │
│                                                │
│ IDENTITY:                                      │
│ - Agent ID: def456                             │
│ - Agent Type: implementer                      │
│ - Project ID: proj123                          │
│ - Parent Orchestrator: abc123                  │
│                                                │
│ INSTRUCTIONS:                                  │
│ 1. Fetch mission: get_agent_mission(           │
│      agent_job_id='def456',                    │
│      tenant_key='tenant-abc'                   │
│    )                                           │
│ 2. Execute mission                             │
│ 3. Report progress: report_progress(...)       │
│ 4. Coordinate via: send_message(...)           │
│                                                │
│ Begin by fetching your mission.                │
└──────────┬─────────────────────────────────────┘
           │
           ▼
┌────────────────────────────────────────────────┐
│ Agent Execution:                               │
│                                                │
│ Step 1: Fetch Mission                          │
│   result = get_agent_mission(                  │
│     agent_job_id='def456',                     │
│     tenant_key='tenant-abc'                    │
│   )                                            │
│                                                │
│   Returns: {                                   │
│     agent_job_id: 'def456',                    │
│     agent_name: 'Backend Implementer',         │
│     agent_type: 'implementer',                 │
│     mission: 'Build user auth module           │
│               using JWT tokens...',            │
│     project_id: 'proj123',                     │
│     estimated_tokens: 2000,                    │
│     thin_client: true                          │
│   }                                            │
│                                                │
│ Step 2: Acknowledge Job                        │
│   acknowledge_job(                             │
│     job_id='def456',                           │
│     agent_id='def456',                         │
│     tenant_key='tenant-abc'                    │
│   )                                            │
│   → Status: waiting → active                   │
│                                                │
│ Step 3: Execute Work                           │
│   • Read codebase                              │
│   • Implement features                         │
│   • Write tests                                │
│   • Report progress incrementally              │
│                                                │
│ Step 4: Report Progress                        │
│   await report_progress(                       │
│     job_id='def456',                           │
│     completed_todo='Implemented JWT auth',     │
│     files_modified=['src/auth.py'],            │
│     context_used=5000,                         │
│     tenant_key='tenant-abc'                    │
│   )                                            │
│   → Updates UI via WebSocket                   │
│   → Stored in message queue                    │
│                                                │
│ Step 5: Complete Job                           │
│   complete_job(                                │
│     job_id='def456',                           │
│     result={                                   │
│       summary: 'Completed auth module',        │
│       files_created: ['src/auth.py'],          │
│       tests_written: ['test_auth.py'],         │
│       coverage: '95%'                          │
│     },                                         │
│     tenant_key='tenant-abc'                    │
│   )                                            │
│   → Status: active → completed                 │
│   → Agent card updates in UI                   │
└────────────────────────────────────────────────┘
```

### 9.5 Agent Job Lifecycle States

**7-State Model** (enforced in database):
1. `waiting`: Job created, agent not started
2. `active`: Agent acknowledged, preparing to work
3. `working`: Agent actively executing
4. `complete`: Job finished successfully
5. `failed`: Job encountered error
6. `blocked`: Job waiting for dependency
7. `cancelled`: Job manually stopped

**State Transitions**:
```
waiting → acknowledge_job() → active
active → start work → working
working → complete_job() → complete
working → report_error() → failed
working → dependency wait → blocked
any → cancel → cancelled
```

---

## 10. Messaging & Communication

### 10.1 Message Architecture

**Database Table**: `agent_communication_queue`

**Message Types**:
- `progress`: Incremental work updates
- `user_feedback`: Direct user messages
- `orchestrator_instruction`: Orchestrator directives
- `handoff_request`: Context succession signals
- `context_warning`: Token limit warnings
- `error`: Agent error reports
- `error_recovery`: Recovery guidance

### 10.2 Message Flow

```
┌────────────────────────────────────┐
│ Agent Working                      │
└──────────┬─────────────────────────┘
           │
           ▼
┌────────────────────────────────────────────────┐
│ Agent reports progress:                        │
│   await report_progress(                       │
│     job_id='def456',                           │
│     completed_todo='Built login endpoint',     │
│     files_modified=['src/auth/login.py'],      │
│     context_used=8000,                         │
│     tenant_key='tenant-abc'                    │
│   )                                            │
└──────────┬─────────────────────────────────────┘
           │
           ▼
┌────────────────────────────────────────────────┐
│ Backend stores in message queue:               │
│   INSERT INTO agent_communication_queue (      │
│     job_id, tenant_key, from_agent,            │
│     to_agent, message_type, content,           │
│     priority, metadata, read_at                │
│   ) VALUES (                                   │
│     'def456', 'tenant-abc', 'def456',          │
│     NULL, 'progress', 'Built login endpoint',  │
│     1, {files: [...], context: 8000}, NULL     │
│   )                                            │
└──────────┬─────────────────────────────────────┘
           │
           ▼
┌────────────────────────────────────────────────┐
│ WebSocket broadcasts to frontend:              │
│   event: 'agent:progress'                      │
│   data: {                                      │
│     agent_id: 'def456',                        │
│     project_id: 'proj123',                     │
│     message: 'Built login endpoint',           │
│     files_modified: ['src/auth/login.py'],     │
│     context_used: 8000                         │
│   }                                            │
└──────────┬─────────────────────────────────────┘
           │
           ▼
┌────────────────────────────────────┐
│ UI Message Pane Updates            │
│ • Shows new message                │
│ • Updates progress indicator       │
│ • Agent card status updates        │
└────────────────────────────────────┘
```

### 10.3 User-to-Agent Messaging

**Via Dashboard**:
```
┌────────────────────────────────────┐
│ Message Pane in Implementation Tab │
└──────────┬─────────────────────────┘
           │
           ▼
┌────────────────────────────────────┐
│ User types message:                │
│ "Please prioritize security tests" │
│                                    │
│ Target:                            │
│ ○ Orchestrator Direct              │
│ ● Broadcast to All Agents          │
└──────────┬─────────────────────────┘
           │
           ▼
┌────────────────────────────────────────────────┐
│ Backend: send_message()                        │
│   to_agent: 'broadcast' (or specific ID)       │
│   message_type: 'user_feedback'                │
│   priority: 2 (high)                           │
└──────────┬─────────────────────────────────────┘
           │
           ▼
┌────────────────────────────────────────────────┐
│ Agents poll via get_next_instruction():        │
│   result = await get_next_instruction(         │
│     job_id='def456',                           │
│     agent_type='implementer',                  │
│     tenant_key='tenant-abc'                    │
│   )                                            │
│                                                │
│   Returns: {                                   │
│     has_updates: true,                         │
│     instructions: [                            │
│       'USER FEEDBACK: Please prioritize        │
│        security tests'                         │
│     ],                                         │
│     handoff_requested: false,                  │
│     context_warning: false                     │
│   }                                            │
│                                                │
│ → Agent reads and acts on feedback             │
└────────────────────────────────────────────────┘
```

**Message Auditing**:
- All messages stored in database
- Audit trail for compliance
- Currently informational (future: full auditing)

### 10.4 Agent-to-Agent Coordination

**Orchestrator-to-Agent**:
```
┌────────────────────────────────────┐
│ Orchestrator monitors progress     │
└──────────┬─────────────────────────┘
           │
           ▼
┌────────────────────────────────────────────────┐
│ Detects backend completed:                     │
│ → Send directive to tester:                    │
│                                                │
│   await send_message(                          │
│     job_id='orch123',                          │
│     to_agent='tester',                         │
│     message='Backend auth complete.            │
│              Begin validation tests.',         │
│     tenant_key='tenant-abc',                   │
│     priority=2                                 │
│   )                                            │
└──────────┬─────────────────────────────────────┘
           │
           ▼
┌────────────────────────────────────┐
│ Tester receives via                │
│ get_next_instruction()             │
│ → Acts on directive                │
└────────────────────────────────────┘
```

---

## 11. MCP Tools Reference

### 11.1 Orchestration Tools (Staging Phase)

**`get_orchestrator_instructions(orchestrator_id, tenant_key)`**
- **Purpose**: Fetch context for orchestrator to analyze and create mission
- **Returns**: Condensed mission with field priorities applied (~6K tokens vs 60K)
- **Used During**: Project staging (orchestrator creates mission plan)

**`update_project_mission(project_id, mission, tenant_key)`**
- **Purpose**: Persist AI-generated mission to database
- **Effect**: Mission appears in UI, enables job launch

**`spawn_agent_job(agent_type, agent_name, mission, project_id, tenant_key, parent_job_id)`**
- **Purpose**: Create specialist agent job (orchestrator delegates work)
- **Returns**: Thin prompt (~10 lines) + agent_job_id
- **Database**: Stores mission in MCPAgentJob.mission field

### 11.2 Agent Execution Tools (Jobs Phase)

**`get_agent_mission(agent_job_id, tenant_key)`**
- **Purpose**: Fetch agent-specific mission from database
- **Returns**: Agent mission, context, estimated tokens
- **Architecture**: Thin client pattern (mission fetched, not copy-pasted)

**`acknowledge_job(job_id, agent_id, tenant_key)`**
- **Purpose**: Claim job (pending → active transition)
- **Returns**: Job details, next instructions

**`report_progress(job_id, completed_todo, files_modified, context_used, tenant_key)`**
- **Purpose**: Report incremental progress
- **Effect**: Updates message queue, broadcasts via WebSocket
- **Warnings**: Context usage warnings at 83%, 93%, 97%

**`get_next_instruction(job_id, agent_type, tenant_key)`**
- **Purpose**: Poll message queue for new instructions
- **Returns**: Unread messages (user feedback, orchestrator directives, warnings)

**`complete_job(job_id, result, tenant_key)`**
- **Purpose**: Mark job complete with results
- **Returns**: Completion confirmation, optional next job

**`report_error(job_id, error_type, error_message, context, tenant_key)`**
- **Purpose**: Report error, pause job for review
- **Effect**: Job → failed, orchestrator notified

**`send_message(job_id, to_agent, message, tenant_key, priority)`**
- **Purpose**: Inter-agent communication
- **Used By**: Orchestrator coordination, agent collaboration

### 11.3 Succession Tools (Context Handover)

**`spawn_succession_orchestrator(current_orchestrator_id, tenant_key)`**
- **Purpose**: Create successor orchestrator when context limit reached
- **Trigger**: 90% context capacity (default)
- **Returns**: New orchestrator with handover summary

### 11.4 Context Tools

**`get_product_context(product_id, tenant_key, field_priorities)`**
- **Purpose**: Fetch product context with priority filtering
- **Returns**: Condensed context based on priorities

**`get_project_summary(project_id, tenant_key)`**
- **Purpose**: Generate project summary for handovers
- **Returns**: Condensed project state

---

## 12. Admin & User Settings

### 12.1 Admin Settings

**Access**: Admin role only

**Categories**:
1. **Network Configuration**
   - External Host IP
   - API Port (default: 7272)
   - Frontend Port (default: 7274)
   - CORS Origins

2. **Database**
   - Host (localhost for internal)
   - Port (5432)
   - DB Name (giljo_mcp)
   - Username/Password
   - Test Connection

3. **Integrations**
   - Lists MCP integrations
   - How integrations work (docs)

4. **Security**
   - Cookie Domain Whitelist
   - Session settings

5. **System**
   - Orchestrator Template Editor (protected)
   - User Management (future)

### 12.2 User Settings

**Access**: All authenticated users

**Setup Tab**:
- MCP tool integration prompts
- Slash command setup
- Agent template import
- (Static prompts - copy/paste)

**Agents Tab**:
- Agent Template Manager
- Enable/disable agents
- Edit templates
- Version history
- Compare with defaults

**Context Tab**:
- Field Priority Configuration
- Drag & drop prioritization
- Context budget settings
- Used as context source during orchestration

**Appearance Tab**:
- Themes
- Mascot
- Display settings
- Tooltips
- High contrast

**Notifications Tab**:
- Message notifications
- Agent notifications
- Display location

**System Tab**:
- Orchestrator template viewer (read-only for non-admins)

---

## 13. Key Concepts & Terminology

### 13.1 Critical Distinctions

**Project.description vs Project.mission**:
- **description**: Human-written requirements (INPUT for orchestrator)
- **mission**: AI-generated execution plan (OUTPUT from orchestrator)

**Activate vs Stage vs Launch**:
- **Activate** (Product/Project): Set as active (one per tenant/product)
- **Launch** (Project): Create orchestrator job and generate staging prompt
- **Staging**: Orchestrator analyzes requirements and creates mission (transient state)

**Thin Client vs Fat Client**:
- **Thin Client**: Prompts are ~10 lines, fetch instructions from database via MCP
- **Fat Client**: Prompts include full context (old architecture, deprecated)

**Static Prompts vs Database-Driven Prompts**:
- **Static Prompts**: Copy-paste for initial setup (MCP attachment, slash commands, agent import)
- **Database-Driven Prompts**: Agent job instructions stored in database, fetched via MCP tools

### 13.2 Perpetual Context Management

**Not** "70% token reduction" → **Now** "Perpetual context and conveniences"

**Concept**: Manage unlimited project context across long-running work without hitting limits

**How**:
1. Field priorities determine what's included
2. Context budget enforces limits
3. Orchestrator succession at 90% capacity
4. Handover summaries condense context
5. Agents work with relevant subsets

**Benefits**:
- Work on projects longer than 200K tokens
- Automatic context handoffs
- No manual copy-paste context management

### 13.3 Agent Workflow Modes

**Claude Code CLI Mode**:
- Single terminal
- Orchestrator uses native subagent system
- Automatic coordination
- Parallel execution

**Legacy CLI Mode**:
- Multiple terminals (one per agent)
- Manual prompt copy-paste
- Sequential/parallel determined by orchestrator
- Supports Claude Code, Codex, Gemini CLI

### 13.4 Job Lifecycle

**States**: `waiting → active → working → complete/failed/blocked/cancelled`

**Phases**:
1. **Staging**: Orchestrator creates mission, spawns jobs
2. **Launch**: User initiates agent execution
3. **Execution**: Agents work, report progress
4. **Completion**: Jobs finish, project closes

### 13.5 Multi-Tenant Isolation

**Isolation Levels**:
- Tenant-specific data (products, projects, tasks, jobs)
- Tenant-specific agent templates
- Tenant-specific message queues
- API/Bearer key authentication

**No Cross-Tenant Leakage**: Enforced at database query level

---

## Appendix A: Workflow Quick Reference

### Product Workflow
```
Create → Activate → (Create Projects) → Deactivate
```

### Project Workflow
```
Create → Activate → Launch → (Staging) → (Execution) → Complete/Cancel
```

### Agent Workflow
```
Enable Template → Orchestrator Selects → Job Spawned →
Agent Fetches Mission → Acknowledges → Works → Reports Progress → Completes
```

### Task Workflow
```
Create → (Product Active?) → Convert to Project
```

---

## Appendix B: Database Schema (Key Tables)

### Products
- `id`, `tenant_key`, `name`, `description`, `vision_documents`, `tech_stack`, `status`

### Projects
- `id`, `tenant_key`, `product_id`, `name`, `description`, `mission`, `status`, `context_budget`

### MCPAgentJob
- `job_id`, `tenant_key`, `project_id`, `agent_type`, `agent_name`, `mission`, `status`, `spawned_by`, `context_budget`, `context_used`, `instance_number`

### agent_communication_queue
- `id`, `job_id`, `tenant_key`, `from_agent`, `to_agent`, `message_type`, `content`, `priority`, `metadata`, `read_at`

### AgentTemplate
- `id`, `tenant_key`, `name`, `role`, `description`, `template_content`, `is_active`, `is_system_default`

---

## Appendix C: Port Reference

- **Frontend**: 7274 (Vue 3 dashboard)
- **Backend API**: 7272 (FastAPI)
- **Database**: 5432 (PostgreSQL default)

---

## Appendix D: File Paths

**Agent Templates (Exported)**:
- `~/.claude/agents/*.md` (Claude Code CLI)

**Slash Commands**:
- `~/.claude/commands/*.md` (Claude Code CLI)

**Database**:
- Connection via `config.yaml` (gitignored)

**Logs**:
- `logs/app.log` (API server)
- `logs/mcp_adapter.log` (MCP server)

---

**End of Single Source of Truth Workflow Documentation**

*This document supersedes all previous workflow documentation and serves as the canonical reference for GiljoAI MCP Server v3.1+. Last verified against codebase: 2025-01-16*
