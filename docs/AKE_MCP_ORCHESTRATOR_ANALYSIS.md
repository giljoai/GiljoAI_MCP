# AKE-MCP Orchestrator Architecture Analysis
**Comprehensive Extraction for GiljoAI-MCP Implementation**

**Date:** January 7, 2025  
**Source Project:** AKE-MCP (F:/AKE-MCP)  
**Target Project:** GiljoAI-MCP (F:/GiljoAI_MCP)  
**Analysis Focus:** Orchestrator agent implementation, profiling systems, coordination patterns

---

## Executive Summary

AKE-MCP implements a **Project Manager-style orchestrator** using a **dynamic discovery** approach where agents explore context on-demand rather than consuming pre-built static contexts. The orchestrator acts as a CEO/Project Manager that:

1. **Discovers context dynamically** using MCP tools (Serena MCP, get_vision, etc.)
2. **Creates specific missions** for worker agents based on discoveries
3. **Spawns and coordinates agents** through a database-driven message queue
4. **Delegates work** rather than executing implementation itself
5. **Monitors progress** and handles handoffs between agents

**Key Innovation:** Hierarchical context loading where the orchestrator gets FULL context (vision + all config), while worker agents get FILTERED context based on their role.

**Project Locations:**
- AKE-MCP Source: `F:/AKE-MCP/`
- Key Files:
  - `server.py` - MCP tools and orchestrator mission (lines 150-400)
  - `core/orchestrator.py` - Agent sequencing and handoffs
  - `core/session_manager.py` - Context management and hierarchical loading
  - `core/message_queue.py` - Inter-agent communication
  - `sql/01_create_new_tables.sql` - Database schema

---

## Table of Contents

1. [Orchestrator Role Definition](#1-orchestrator-role-definition)
2. [Profiling System Architecture](#2-profiling-system-architecture)
3. [Agent Spawning and Coordination](#3-agent-spawning-and-coordination)
4. [Dynamic Discovery Workflow](#4-dynamic-discovery-workflow)
5. [Vision Document Management](#5-vision-document-management)
6. [MCP Tools Architecture](#6-mcp-tools-architecture)
7. [Database Architecture](#7-database-architecture)
8. [Key Patterns for Implementation](#8-key-patterns-for-giljoai-mcp-implementation)
9. [Implementation Checklist](#9-implementation-checklist-for-giljoai-mcp)
10. [File Locations Reference](#10-file-locations-reference)
11. [Key Insights and Recommendations](#11-key-insights-and-recommendations)

---

