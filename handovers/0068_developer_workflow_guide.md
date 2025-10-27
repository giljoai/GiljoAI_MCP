---
Handover 0068: Developer Workflow Guide
Date: 2025-10-27
Status: Ready for Implementation
Priority: MEDIUM
Complexity: LOW
Duration: 8-10 hours
---

# Executive Summary

The GiljoAI MCP Server has comprehensive technical documentation but lacks an end-to-end developer workflow guide that shows how all the pieces fit together. This handover creates a practical, example-driven guide that walks developers through the complete workflow from product creation to mission completion.

**Key Principle**: Documentation should teach through real-world examples, not just reference material. Developers should understand the "why" and "how" of the entire system.

The guide will cover the complete developer journey with concrete examples, code snippets, screenshots, and best practices for each step of the GiljoAI workflow.

---

# Problem Statement

## Current State

Documentation is comprehensive but fragmented:
- CLAUDE.md covers basics
- TECHNICAL_ARCHITECTURE.md covers system design
- Individual handovers cover specific features
- No end-to-end workflow guide
- No practical examples tying everything together
- Developers must piece together the workflow themselves

## Gaps Without This Implementation

1. **No Complete Picture**: Hard to understand how components interact
2. **No Examples**: Theory without practical application
3. **Steep Learning Curve**: Takes days to understand full workflow
4. **No Best Practices**: Developers reinvent patterns
5. **Poor Onboarding**: New team members struggle to get started

---

# Implementation Plan

## Overview

This implementation creates a comprehensive developer workflow guide with real examples, code snippets, and best practices. Pure documentation work - no code changes required.

**Total Estimated Content**: ~6000 words across 3 documentation files

## Guide Structure

**Primary Document**: `docs/DEVELOPER_WORKFLOW_GUIDE.md` (~4000 words)
**Supplementary**: `docs/guides/QUICK_START_TUTORIAL.md` (~1500 words)
**Reference**: `docs/guides/COMMON_PATTERNS.md` (~500 words)

## Phase 1: Main Workflow Guide (4-5 hours)

**File**: `docs/DEVELOPER_WORKFLOW_GUIDE.md` (NEW)

**Table of Contents**:

```markdown
# GiljoAI Developer Workflow Guide

## Table of Contents

1. Introduction
   - What is GiljoAI?
   - Core Concepts
   - The 70% Token Reduction Architecture

2. Setup & Installation
   - Quick Installation
   - First Login & User Creation
   - Configuration Verification

3. The Complete Workflow
   - Step 1: Create a Product
   - Step 2: Upload Vision Documents
   - Step 3: Configure Field Priority
   - Step 4: Create Projects
   - Step 5: Configure Agent Tools (Claude/Codex/Gemini)
   - Step 6: Create/Configure Agents
   - Step 7: Launch Orchestrator
   - Step 8: Review Mission Plan
   - Step 9: Monitor Agent Progress
   - Step 10: Review Completed Work

4. Real-World Example: Building a REST API
   - Product Setup
   - Vision Document Creation
   - Field Priority Configuration
   - Agent Assignment
   - Mission Execution
   - Result Review

5. Advanced Workflows
   - Multi-Agent Coordination
   - Parallel vs Waterfall Workflows
   - Custom Agent Templates
   - Product-Project Hierarchies

6. Best Practices
   - Vision Document Guidelines
   - Field Priority Optimization
   - Agent Selection Strategy
   - Token Budget Management
   - Project Organization

7. Troubleshooting
   - Common Issues & Solutions
   - Debug Mode
   - Log Analysis

8. API Integration
   - REST API Examples
   - WebSocket Events
   - MCP Tool Usage

9. Extending GiljoAI
   - Custom Integrations
   - New MCP Tools
   - Custom Agent Types

10. Appendix
    - Architecture Diagrams
    - API Reference
    - Configuration Reference
```

**Key Sections Content**:

### Section 3: The Complete Workflow

```markdown
## Step 1: Create a Product

A **Product** is the top-level container for your development work. Think of it as a software project that will have multiple features (projects) built by AI agents.

### Via Dashboard

1. Navigate to Products view
2. Click "Create Product"
3. Fill in details:
   - Name: "TaskMaster API"
   - Description: "RESTful API for task management"
4. Click "Create"

### Via API

\`\`\`bash
curl -X POST http://localhost:7272/api/v1/products \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "TaskMaster API",
    "description": "RESTful API for task management"
  }'
\`\`\`

**Result**: Product created with UUID, inactive by default.

---

## Step 2: Upload Vision Documents

Vision documents define what you want to build. They can be:
- Product Requirements Documents (PRDs)
- Feature specifications
- User stories
- Technical architecture docs
- API specifications

### Best Practices

- **Keep it focused**: 1-3 documents per product
- **Be specific**: Include acceptance criteria
- **Structure matters**: Use headings, lists, code blocks
- **Token budget**: Aim for 1000-2000 tokens per document

### Example Vision Document

Create `vision/taskmaster_api_vision.md`:

\`\`\`markdown
# TaskMaster API - Product Vision

## Overview
Build a RESTful API for task management with user authentication,
CRUD operations, and real-time updates via WebSocket.

## Features

### 1. User Authentication
- JWT-based authentication
- Registration endpoint: POST /api/v1/auth/register
- Login endpoint: POST /api/v1/auth/login
- Password hashing with bcrypt

### 2. Task Management
- Create tasks: POST /api/v1/tasks
- List tasks: GET /api/v1/tasks
- Update task: PATCH /api/v1/tasks/{id}
- Delete task: DELETE /api/v1/tasks/{id}

### 3. Real-time Updates
- WebSocket endpoint: ws://localhost:8000/ws
- Broadcast task changes to connected clients

## Technical Requirements
- Python 3.11+
- FastAPI framework
- PostgreSQL database
- SQLAlchemy ORM
- JWT authentication
- WebSocket support

## Acceptance Criteria
- All endpoints return proper HTTP status codes
- Authentication required for task operations
- WebSocket broadcasts task changes
- 95%+ test coverage
\`\`\`

### Upload to GiljoAI

\`\`\`bash
curl -X POST http://localhost:7272/api/v1/products/{product_id}/vision \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "file=@vision/taskmaster_api_vision.md"
\`\`\`

**Result**: Vision document uploaded, ready for analysis.

---

## Step 3: Configure Field Priority

Field Priority defines what's important and what to ignore. This is the key to
the 70% token reduction - agents receive only relevant information.

### Understanding Field Priority

GiljoAI uses a 2000-token budget for mission context. Field Priority configuration
tells the system:
- What fields are HIGH priority (always include)
- What fields are MEDIUM priority (include if space available)
- What fields are LOW priority (exclude)

### Example Configuration

Navigate to Product > Configure Field Priority:

\`\`\`json
{
  "code_fields": {
    "function_signatures": "HIGH",
    "docstrings": "HIGH",
    "type_hints": "HIGH",
    "implementation_details": "MEDIUM",
    "comments": "LOW"
  },
  "documentation_fields": {
    "api_endpoints": "HIGH",
    "request_examples": "HIGH",
    "response_schemas": "HIGH",
    "error_codes": "MEDIUM",
    "change_history": "LOW"
  },
  "test_fields": {
    "test_cases": "HIGH",
    "assertions": "HIGH",
    "mocks": "MEDIUM",
    "fixtures": "LOW"
  }
}
\`\`\`

**Best Practice**: Start with this template and adjust based on your product's needs.

---

## Step 4: Activate Product

Before creating projects or launching agents, **activate** the product:

\`\`\`bash
curl -X POST http://localhost:7272/api/v1/products/{product_id}/activate \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
\`\`\`

**Important**: Only ONE product can be active per tenant (Handover 0050).
Activating a product deactivates others.

---

## Step 5: Create Projects

Projects are specific features or milestones within a product.

\`\`\`bash
curl -X POST http://localhost:7272/api/v1/projects \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "User Authentication",
    "description": "Implement JWT-based authentication endpoints",
    "product_id": "PRODUCT_UUID"
  }'
\`\`\`

**Result**: Project created under active product.

---

## Step 6: Configure Agent Tools

Navigate to Settings > Integrations and configure external tools:

### Claude Code
- Enable: Yes
- MCP Server URL: http://localhost:7272

### Codex (Optional)
- Enable: Yes
- API Key: YOUR_OPENAI_API_KEY
- Model: gpt-4

### Gemini (Optional)
- Enable: Yes
- API Key: YOUR_GOOGLE_API_KEY
- Model: gemini-2.0-flash-exp

---

## Step 7: Create Agents

Create agents and assign tools:

\`\`\`bash
curl -X POST http://localhost:7272/api/v1/agents \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Backend Developer",
    "agent_type": "backend",
    "capabilities": ["python", "fastapi", "sqlalchemy", "postgresql"],
    "tool_config": {
      "tool_type": "claude",
      "tool_config": {}
    }
  }'
\`\`\`

**Best Practice**: Create specialized agents:
- Backend Developer (Claude) - API implementation
- Frontend Developer (Codex) - UI components
- Test Engineer (Gemini) - Test coverage

---

## Step 8: Launch Orchestrator

Click "Launch Orchestrator" button in Products view:

1. **Preview Mode**: System generates mission plan
2. **Review Summary**:
   - Mission count: 3
   - Selected agents: Backend Developer, Test Engineer
   - Token usage: 1847 / 2000 (92%)
   - Workflow type: Waterfall
3. **Confirm Launch**: Agents start work

---

## Step 9: Monitor Progress

Watch real-time updates in dashboard:

- **Agent Cards**: Show active jobs per agent
- **Job Status**: Pending → Acknowledged → In Progress → Complete
- **Progress Bars**: Real-time completion percentage
- **WebSocket Updates**: Live status changes

---

## Step 10: Review Results

Once jobs complete:

1. View completed artifacts in Projects view
2. Download generated code
3. Review agent communication logs
4. Test implementation
5. Iterate if needed
```

### Section 4: Real-World Example

(Detailed walkthrough of building TaskMaster API with actual commands, expected outputs, and screenshots)

### Section 5: Advanced Workflows

(Multi-agent coordination examples, parallel workflows, custom templates)

### Section 6: Best Practices

```markdown
## Vision Document Guidelines

### ✅ Good Vision Document

- Clear structure with headers
- Specific acceptance criteria
- Concrete examples (API endpoints, schemas)
- Technical constraints listed
- Reasonable scope (1-2 features)

### ❌ Poor Vision Document

- Vague requirements ("make it fast")
- No acceptance criteria
- Too broad scope (entire system)
- No technical details
- Conflicting requirements

## Field Priority Optimization

### Rule of Thumb

- HIGH: Information agents need for every task (20-30% of fields)
- MEDIUM: Helpful context (40-50% of fields)
- LOW: Nice-to-have or auto-generated (20-30% of fields)

### Token Budget Math

- 2000 tokens total budget
- Reserve 200 tokens for mission instructions
- Reserve 300 tokens for field priority config
- 1500 tokens available for vision context
- HIGH priority fields fill first, MEDIUM if space remains

## Agent Selection Strategy

### Specialization Wins

Create focused agents:
- ✅ "REST API Developer" (Python, FastAPI)
- ❌ "Full Stack Developer" (too broad)

### Tool Selection

- **Claude Code**: Best for Python, comprehensive reasoning
- **Codex**: Best for JavaScript/TypeScript, fast iteration
- **Gemini**: Best for testing, multimodal analysis

### Agent Count

- Simple projects: 1-2 agents
- Medium projects: 3-4 agents
- Complex projects: 5-6 agents maximum
```

## Phase 2: Quick Start Tutorial (2-3 hours)

**File**: `docs/guides/QUICK_START_TUTORIAL.md` (NEW)

**30-Minute Tutorial**: Build a simple Flask API with GiljoAI

```markdown
# Quick Start Tutorial: Build a Flask API in 30 Minutes

## Prerequisites

- GiljoAI installed and running
- Claude Code configured
- 30 minutes of time

## What We'll Build

A simple Flask API with:
- GET /api/hello - Returns greeting
- POST /api/echo - Echoes back JSON

## Step 1: Create Product (5 minutes)

... (step-by-step with screenshots)

## Step 2: Write Vision Document (5 minutes)

... (example vision doc)

## Step 3: Configure & Launch (5 minutes)

... (field priority, activation)

## Step 4: Create Agent & Launch Orchestrator (10 minutes)

... (agent creation, mission launch)

## Step 5: Test the Result (5 minutes)

... (testing generated API)

## What You Learned

- Product creation workflow
- Vision document structure
- Field priority configuration
- Agent assignment
- Orchestrator launch
- Result verification
```

## Phase 3: Common Patterns Reference (1-2 hours)

**File**: `docs/guides/COMMON_PATTERNS.md` (NEW)

**Quick Reference**: Code snippets for common tasks

```markdown
# Common Patterns & Code Snippets

## Authentication

### Get JWT Token

\`\`\`bash
TOKEN=$(curl -X POST http://localhost:7272/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "your_password"}' \
  | jq -r '.access_token')
\`\`\`

## Product Management

### Create Product with Vision

\`\`\`bash
# Create product
PRODUCT_ID=$(curl -X POST http://localhost:7272/api/v1/products \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "My Product", "description": "..."}' \
  | jq -r '.id')

# Upload vision
curl -X POST http://localhost:7272/api/v1/products/$PRODUCT_ID/vision \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@vision.md"

# Activate
curl -X POST http://localhost:7272/api/v1/products/$PRODUCT_ID/activate \
  -H "Authorization: Bearer $TOKEN"
\`\`\`

## Agent Coordination

### Create Agent Job Manually

\`\`\`python
from src.giljo_mcp.tools.agent_coordination import agent_coordination

job = await agent_coordination.create_agent_job(
    agent_id="AGENT_UUID",
    mission="Implement user authentication endpoint",
    product_id="PRODUCT_UUID",
    priority=8,
    metadata={"project_id": "PROJECT_UUID"}
)
\`\`\`

### Monitor Job Progress

\`\`\`python
status = await agent_coordination.get_agent_job_status("JOB_UUID")
print(f"Status: {status['status']}, Progress: {status['progress']}%")
\`\`\`

... (more patterns)
```

## Phase 4: Integration with Existing Docs (1 hour)

**Update `docs/README_FIRST.md`**:

```markdown
## 📚 Documentation Index

**Start Here**:
- [Developer Workflow Guide](DEVELOPER_WORKFLOW_GUIDE.md) - Complete workflow from setup to mission completion
- [Quick Start Tutorial](guides/QUICK_START_TUTORIAL.md) - 30-minute hands-on tutorial
- [Common Patterns](guides/COMMON_PATTERNS.md) - Code snippets reference

**Core Concepts**:
- ... (existing links)
```

**Update `CLAUDE.md`**:

```markdown
## 📋 Quick Reference

**For Developers**:
- [Complete Workflow Guide](docs/DEVELOPER_WORKFLOW_GUIDE.md)
- [30-Minute Tutorial](docs/guides/QUICK_START_TUTORIAL.md)
```

---

# Files to Create/Modify

1. **docs/DEVELOPER_WORKFLOW_GUIDE.md** (~4000 words, NEW)
   - Complete workflow guide with examples

2. **docs/guides/QUICK_START_TUTORIAL.md** (~1500 words, NEW)
   - 30-minute hands-on tutorial

3. **docs/guides/COMMON_PATTERNS.md** (~500 words, NEW)
   - Code snippets reference

4. **docs/README_FIRST.md** (+20 lines)
   - Add links to new guides

5. **CLAUDE.md** (+10 lines)
   - Add quick reference links

**Total**: ~6000 words across 5 files (3 new, 2 modified)

---

# Success Criteria

## Content Quality
- Complete workflow from start to finish
- Real-world examples that work
- Code snippets tested and accurate
- Clear explanations of "why" not just "how"
- Visual aids (architecture diagrams, screenshots)

## Usability
- New developers can follow tutorial successfully
- Examples copy-paste-able
- Common questions answered
- Troubleshooting section helpful
- Quick reference accessible

## Coverage
- All major workflows documented
- Best practices for each step
- Common pitfalls explained
- Advanced patterns included
- API examples for programmatic use

---

# Related Handovers

All handovers (0019-0067) inform this guide. Key references:
- **Handover 0020**: Orchestrator Enhancement (mission workflow)
- **Handover 0048**: Field Priority Configuration (token optimization)
- **Handover 0050**: Single Active Product (product management)
- **Handover 0060**: MCP Agent Coordination (tool usage)
- **Handover 0061**: Orchestrator Launch UI (launch workflow)

---

# Risk Assessment

**Complexity**: LOW (documentation only)
**Risk**: NONE (no code changes)
**Breaking Changes**: None
**Maintenance**: Moderate (must update as features change)

---

# Timeline Estimate

**Phase 1**: 4-5 hours (Main workflow guide)
**Phase 2**: 2-3 hours (Quick start tutorial)
**Phase 3**: 1-2 hours (Common patterns)
**Phase 4**: 1 hour (Integration)

**Total**: 8-10 hours for experienced technical writer

---

**Decision Recorded By**: System Architect (Documentation Manager)
**Date**: 2025-10-27
**Priority**: MEDIUM (improves developer onboarding and productivity)

---

**End of Handover 0068**
