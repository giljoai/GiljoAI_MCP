# GiljoAI MCP API Reference

Complete API documentation with request/response examples for all 20 MCP tools.

## Table of Contents

1. [Project Management Tools](#project-management-tools)
2. [Agent Management Tools](#agent-management-tools)
3. [Message Communication Tools](#message-communication-tools)
4. [Context & Vision Tools](#context--vision-tools)

---

## Project Management Tools

**Note**: Projects are created via REST API (`POST /api/v1/projects/`), not MCP tools. See REST API documentation for project creation.

### 1. list_projects

Lists all projects with optional status filter.

**Request:**

```json
{
  "tool": "list_projects",
  "parameters": {
    "status": "active" // optional: "active", "completed", "archived"
  }
}
```

**Response:**

```json
{
  "success": true,
  "projects": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "E-commerce Platform",
      "status": "active",
      "created": "2025-09-16T10:30:00Z",
      "agent_count": 4,
      "message_count": 127
    },
    {
      "id": "660f9500-f39c-52e5-b827-557766551111",
      "name": "API Gateway",
      "status": "active",
      "created": "2025-09-15T14:20:00Z",
      "agent_count": 3,
      "message_count": 89
    }
  ],
  "total": 2
}
```

### 2. gil_activate

Activates a project to prepare orchestrator staging.

**Request:**

```json
{
  "tool": "gil_activate",
  "parameters": {
    "project_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

**Response:**

```json
{
  "success": true,
  "project": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "E-commerce Platform",
    "status": "active"
  },
  "message": "Project activated: E-commerce Platform. Orchestrator staging ready."
}
```

### 3. close_project

Closes a completed project with summary.

**Request:**

```json
{
  "tool": "close_project",
  "parameters": {
    "project_id": "550e8400-e29b-41d4-a716-446655440000",
    "summary": "Successfully implemented e-commerce platform with all requested features. System passed all tests and is deployed to production."
  }
}
```

**Response:**

```json
{
  "success": true,
  "project": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "E-commerce Platform",
    "status": "completed",
    "closed": "2025-09-20T16:45:00Z",
    "summary": "Successfully implemented e-commerce platform...",
    "statistics": {
      "duration_hours": 96,
      "agents_used": 8,
      "messages_sent": 432,
      "tasks_completed": 67
    }
  }
}
```

### 4. update_project_mission

Updates the mission field after orchestrator analysis.

**Request:**

```json
{
  "tool": "update_project_mission",
  "parameters": {
    "project_id": "550e8400-e29b-41d4-a716-446655440000",
    "mission": "ENHANCED MISSION: Build modern e-commerce platform\n\nPHASE 1: User System\n- JWT authentication with refresh tokens\n- Role-based access (admin, vendor, customer)\n- Profile management with avatar upload\n\nPHASE 2: Product Catalog\n- Category hierarchy with filters\n- Search with Elasticsearch\n- Image gallery with CDN\n\nPHASE 3: Payment Processing\n- Stripe integration\n- Multiple currency support\n- Invoice generation"
  }
}
```

**Response:**

```json
{
  "success": true,
  "project_id": "550e8400-e29b-41d4-a716-446655440000",
  "mission_updated": true,
  "timestamp": "2025-09-16T10:35:00Z"
}
```

### 5. project_status

Gets comprehensive project status.

**Request:**

```json
{
  "tool": "project_status",
  "parameters": {
    "project_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

**Response:**

```json
{
  "success": true,
  "project": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "E-commerce Platform",
    "status": "active",
    "created": "2025-09-16T10:30:00Z",
    "mission": "Build modern e-commerce platform..."
  },
  "agents": [
    {
      "name": "orchestrator",
      "status": "active",
      "context_used": 45000,
      "context_budget": 150000,
      "messages_pending": 2
    },
    {
      "name": "backend_dev",
      "status": "active",
      "context_used": 32000,
      "context_budget": 150000,
      "messages_pending": 5
    }
  ],
  "statistics": {
    "total_agents": 4,
    "active_agents": 4,
    "total_messages": 127,
    "pending_messages": 12,
    "completed_tasks": 23,
    "pending_tasks": 8
  },
  "recent_activity": [
    {
      "timestamp": "2025-09-16T15:20:00Z",
      "type": "message",
      "from": "orchestrator",
      "to": "backend_dev",
      "content": "Please implement user authentication module"
    }
  ]
}
```

---

## Agent Management Tools

### 6. ensure_agent

Ensures an agent exists (idempotent - safe for workers).

**Request:**

```json
{
  "tool": "ensure_agent",
  "parameters": {
    "project_id": "550e8400-e29b-41d4-a716-446655440000",
    "agent_name": "security_auditor",
    "mission": "Review code for security vulnerabilities, focusing on OWASP Top 10"
  }
}
```

**Response:**

```json
{
  "success": true,
  "agent": "security_auditor",
  "job_id": "job_789",
  "is_reopen": false,
  "context": {
    "project_id": "550e8400-e29b-41d4-a716-446655440000",
    "project_name": "E-commerce Platform",
    "context_budget": 150000,
    "context_used": 0
  },
  "message": "Agent security_auditor created successfully"
}
```

### 7. activate_agent

Activates orchestrator agent (triggers immediate discovery workflow).

**Request:**

```json
{
  "tool": "activate_agent",
  "parameters": {
    "project_id": "550e8400-e29b-41d4-a716-446655440000",
    "agent_name": "orchestrator",
    "mission": "Analyze project requirements and coordinate development team to build e-commerce platform"
  }
}
```

**Response:**

```json
{
  "success": true,
  "agent": "orchestrator",
  "job_id": "job_001",
  "workflow_triggered": true,
  "discovery_status": "started",
  "context": {
    "project_id": "550e8400-e29b-41d4-a716-446655440000",
    "vision_documents": 3,
    "context_index_ready": true
  },
  "message": "Orchestrator activated and discovery workflow initiated"
}
```

### 8. assign_job

Assigns a job to an agent with tasks and scope.

**Request:**

```json
{
  "tool": "assign_job",
  "parameters": {
    "agent_name": "backend_dev",
    "job_type": "implementation",
    "project_id": "550e8400-e29b-41d4-a716-446655440000",
    "tasks": [
      "Implement JWT authentication with refresh tokens",
      "Create user registration and login endpoints",
      "Add password reset functionality with email verification",
      "Implement role-based access control middleware"
    ],
    "scope_boundary": "Only modify files in src/auth/ and src/middleware/. Do not modify database schemas without approval.",
    "vision_alignment": "Aligns with Phase 1: User System as defined in project vision document"
  }
}
```

**Response:**

```json
{
  "success": true,
  "job": {
    "id": "job_456",
    "agent": "backend_dev",
    "type": "implementation",
    "status": "assigned",
    "tasks": [
      {
        "id": "task_001",
        "description": "Implement JWT authentication with refresh tokens",
        "status": "pending"
      },
      {
        "id": "task_002",
        "description": "Create user registration and login endpoints",
        "status": "pending"
      },
      {
        "id": "task_003",
        "description": "Add password reset functionality with email verification",
        "status": "pending"
      },
      {
        "id": "task_004",
        "description": "Implement role-based access control middleware",
        "status": "pending"
      }
    ],
    "scope_boundary": "Only modify files in src/auth/...",
    "vision_alignment": "Aligns with Phase 1..."
  }
}
```

### 9. handoff

Transfers work from one agent to another.

**Request:**

```json
{
  "tool": "handoff",
  "parameters": {
    "from_agent": "backend_dev",
    "to_agent": "tester",
    "project_id": "550e8400-e29b-41d4-a716-446655440000",
    "context": {
      "completed_work": [
        "JWT authentication implemented",
        "User registration/login endpoints created",
        "Password reset with email verification added",
        "RBAC middleware configured"
      ],
      "test_requirements": {
        "endpoints": [
          "POST /api/auth/register",
          "POST /api/auth/login",
          "POST /api/auth/refresh",
          "POST /api/auth/reset-password"
        ],
        "test_users": {
          "admin": "admin@test.com",
          "vendor": "vendor@test.com",
          "customer": "customer@test.com"
        },
        "coverage_target": 90
      },
      "notes": "All endpoints use JWT. Refresh tokens expire after 7 days. Rate limiting is 5 requests per minute for auth endpoints."
    }
  }
}
```

**Response:**

```json
{
  "success": true,
  "handoff": {
    "id": "handoff_123",
    "from": "backend_dev",
    "to": "tester",
    "timestamp": "2025-09-16T14:30:00Z",
    "context_transferred": true
  },
  "message": "Work successfully handed off from backend_dev to tester"
}
```

### 10. agent_health

Checks agent health and context usage.

**Request:**

```json
{
  "tool": "agent_health",
  "parameters": {
    "agent_name": "backend_dev"
  }
}
```

**Response:**

```json
{
  "success": true,
  "agent": "backend_dev",
  "health": {
    "status": "healthy",
    "context_used": 75000,
    "context_budget": 150000,
    "context_percentage": 50,
    "messages_pending": 3,
    "messages_processed": 42,
    "tasks_completed": 12,
    "tasks_pending": 2,
    "uptime_seconds": 3600,
    "last_activity": "2025-09-16T15:25:00Z"
  },
  "warnings": [],
  "recommendations": []
}
```

**Response (with warnings):**

```json
{
  "success": true,
  "agent": "frontend_dev",
  "health": {
    "status": "warning",
    "context_used": 140000,
    "context_budget": 150000,
    "context_percentage": 93,
    "messages_pending": 15,
    "messages_processed": 89,
    "tasks_completed": 23,
    "tasks_pending": 8,
    "uptime_seconds": 7200,
    "last_activity": "2025-09-16T15:20:00Z"
  },
  "warnings": ["Context usage above 90%", "High message backlog (15 pending)"],
  "recommendations": [
    "Consider handoff to fresh agent soon",
    "Process pending messages or spawn helper"
  ]
}
```

### 11. decommission_agent

Gracefully ends an agent's work.

**Request:**

```json
{
  "tool": "decommission_agent",
  "parameters": {
    "agent_name": "security_auditor",
    "project_id": "550e8400-e29b-41d4-a716-446655440000",
    "reason": "Security audit completed, all vulnerabilities addressed"
  }
}
```

**Response:**

```json
{
  "success": true,
  "agent": "security_auditor",
  "decommission": {
    "timestamp": "2025-09-16T16:00:00Z",
    "reason": "Security audit completed, all vulnerabilities addressed",
    "final_stats": {
      "tasks_completed": 15,
      "messages_processed": 38,
      "context_used": 42000,
      "runtime_hours": 4.5
    },
    "handoff_complete": true
  }
}
```

---

## Message Communication Tools

### 12. send_message

Sends message to one or more agents.

**Request:**

```json
{
  "tool": "send_message",
  "parameters": {
    "to_agents": ["frontend_dev", "backend_dev"],
    "content": "Please coordinate on the API contract for user authentication. Frontend needs endpoint documentation and response schemas.",
    "project_id": "550e8400-e29b-41d4-a716-446655440000",
    "message_type": "direct",
    "priority": "high",
    "from_agent": "orchestrator"
  }
}
```

**Response:**

```json
{
  "success": true,
  "message": {
    "id": "msg_789",
    "from": "orchestrator",
    "to": ["frontend_dev", "backend_dev"],
    "content": "Please coordinate on the API contract...",
    "type": "direct",
    "priority": "high",
    "created": "2025-09-16T11:00:00Z",
    "status": "sent"
  },
  "delivery": {
    "frontend_dev": "pending",
    "backend_dev": "pending"
  }
}
```

### 13. get_messages

Retrieves pending messages for an agent.

**Request:**

```json
{
  "tool": "get_messages",
  "parameters": {
    "agent_name": "frontend_dev",
    "project_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

**Response:**

```json
{
  "success": true,
  "agent": "frontend_dev",
  "count": 3,
  "messages": [
    {
      "id": "msg_789",
      "from": "orchestrator",
      "type": "direct",
      "subject": null,
      "content": "Please coordinate on the API contract...",
      "priority": "high",
      "created": "2025-09-16T11:00:00Z"
    },
    {
      "id": "msg_790",
      "from": "backend_dev",
      "type": "direct",
      "subject": "API Documentation Ready",
      "content": "Auth endpoints documented at /docs/api/auth.md",
      "priority": "normal",
      "created": "2025-09-16T11:30:00Z"
    },
    {
      "id": "msg_791",
      "from": "system",
      "type": "broadcast",
      "subject": "Daily Standup",
      "content": "Please update your task status in the project board",
      "priority": "low",
      "created": "2025-09-16T09:00:00Z"
    }
  ]
}
```

### 14. acknowledge_message

Marks message as received by agent.

**Request:**

```json
{
  "tool": "acknowledge_message",
  "parameters": {
    "message_id": "msg_789",
    "agent_name": "frontend_dev"
  }
}
```

**Response:**

```json
{
  "success": true,
  "message_id": "msg_789",
  "agent": "frontend_dev",
  "acknowledged": true,
  "timestamp": "2025-09-16T11:05:00Z"
}
```

### 15. complete_message

Marks message as completed with result.

**Request:**

```json
{
  "tool": "complete_message",
  "parameters": {
    "message_id": "msg_789",
    "agent_name": "frontend_dev",
    "result": "API contract reviewed and integrated. Created TypeScript interfaces for all auth endpoints. Updated API service layer to match new contract."
  }
}
```

**Response:**

```json
{
  "success": true,
  "message_id": "msg_789",
  "agent": "frontend_dev",
  "completed": true,
  "result": "API contract reviewed and integrated...",
  "timestamp": "2025-09-16T12:00:00Z"
}
```

### 16. broadcast

Broadcasts message to all agents in project.

**Request:**

```json
{
  "tool": "broadcast",
  "parameters": {
    "content": "ATTENTION: Code freeze at 5 PM today for release 1.0. Please commit all changes and ensure tests are passing.",
    "project_id": "550e8400-e29b-41d4-a716-446655440000",
    "priority": "high"
  }
}
```

**Response:**

```json
{
  "success": true,
  "broadcast": {
    "id": "broadcast_456",
    "content": "ATTENTION: Code freeze at 5 PM...",
    "priority": "high",
    "timestamp": "2025-09-16T14:00:00Z",
    "recipients": ["orchestrator", "backend_dev", "frontend_dev", "tester"],
    "recipient_count": 4
  }
}
```

### 17. log_task

Quick task capture for tracking.

**Request:**

```json
{
  "tool": "log_task",
  "parameters": {
    "content": "Investigate slow query performance on product search endpoint",
    "category": "optimization",
    "priority": "medium"
  }
}
```

**Response:**

```json
{
  "success": true,
  "task": {
    "id": "task_999",
    "content": "Investigate slow query performance on product search endpoint",
    "category": "optimization",
    "priority": "medium",
    "created": "2025-09-16T13:45:00Z",
    "status": "logged"
  }
}
```

---

## Context & Vision Tools

### 18. get_vision

Gets vision document (auto-chunks for 50K+ tokens).

**Request:**

```json
{
  "tool": "get_vision",
  "parameters": {
    "part": 1,
    "max_tokens": 20000
  }
}
```

**Response:**

```json
{
  "success": true,
  "vision": {
    "part": 1,
    "total_parts": 3,
    "content": "# E-Commerce Platform Vision\n\n## Executive Summary\nWe are building a next-generation e-commerce platform that combines modern architecture with exceptional user experience...\n\n## Core Values\n- Performance: Sub-second page loads\n- Security: Bank-grade encryption\n- Scalability: Support 1M+ concurrent users\n\n## Technical Architecture\n\n### Frontend\n- React 18 with TypeScript\n- Next.js for SSR/SSG\n- Tailwind CSS for styling\n- Redux Toolkit for state management\n\n### Backend\n- Node.js with Express\n- PostgreSQL database\n- Redis for caching\n- Elasticsearch for search\n\n### Infrastructure\n- Docker containers\n- Kubernetes orchestration\n- AWS cloud hosting\n- CloudFront CDN\n\n[... continued for 20000 tokens ...]",
    "tokens": 19847,
    "has_next": true
  }
}
```

### 19. get_vision_index

Gets vision document index for navigation (ORCHESTRATOR ONLY).

**Request:**

```json
{
  "tool": "get_vision_index",
  "parameters": {}
}
```

**Response:**

```json
{
  "success": true,
  "index": {
    "total_files": 5,
    "total_tokens": 52341,
    "chunk_count": 3,
    "files": [
      {
        "name": "PRODUCT_VISION.md",
        "path": "docs/Vision/PRODUCT_VISION.md",
        "size": 15234,
        "tokens": 18500,
        "topics": ["architecture", "requirements", "user stories"],
        "chunks": [1, 2]
      },
      {
        "name": "TECHNICAL_SPEC.md",
        "path": "docs/Vision/TECHNICAL_SPEC.md",
        "size": 12456,
        "tokens": 15200,
        "topics": ["api design", "database schema", "security"],
        "chunks": [2]
      },
      {
        "name": "UI_DESIGN.md",
        "path": "docs/Vision/UI_DESIGN.md",
        "size": 8900,
        "tokens": 10800,
        "topics": ["wireframes", "user flow", "design system"],
        "chunks": [2, 3]
      },
      {
        "name": "DEPLOYMENT.md",
        "path": "docs/Vision/DEPLOYMENT.md",
        "size": 5670,
        "tokens": 6841,
        "topics": ["ci/cd", "monitoring", "scaling"],
        "chunks": [3]
      }
    ],
    "chunk_boundaries": [
      { "chunk": 1, "start_token": 0, "end_token": 20000 },
      { "chunk": 2, "start_token": 20001, "end_token": 40000 },
      { "chunk": 3, "start_token": 40001, "end_token": 52341 }
    ]
  }
}
```

### 20. get_context_index

Gets context index for intelligent querying.

**Request:**

```json
{
  "tool": "get_context_index",
  "parameters": {
    "product_id": "prod_123" // optional
  }
}
```

**Response:**

```json
{
  "success": true,
  "context_index": {
    "product_id": "prod_123",
    "product_name": "GiljoAI MCP Orchestrator",
    "documents": [
      {
        "name": "architecture",
        "sections": [
          "overview",
          "database_design",
          "api_layer",
          "orchestration_engine"
        ],
        "last_updated": "2025-09-15T10:00:00Z"
      },
      {
        "name": "api_reference",
        "sections": [
          "project_tools",
          "agent_tools",
          "message_tools",
          "context_tools"
        ],
        "last_updated": "2025-09-16T14:00:00Z"
      },
      {
        "name": "deployment_guide",
        "sections": [
          "local_setup",
          "lan_deployment",
          "wan_deployment",
          "scaling"
        ],
        "last_updated": "2025-09-14T16:30:00Z"
      }
    ],
    "total_sections": 12,
    "searchable": true
  }
}
```

### 21. get_context_section

Retrieves specific content section.

**Request:**

```json
{
  "tool": "get_context_section",
  "parameters": {
    "document_name": "architecture",
    "section_name": "database_design",
    "product_id": "prod_123" // optional
  }
}
```

**Response:**

```json
{
  "success": true,
  "section": {
    "document": "architecture",
    "section": "database_design",
    "content": "## Database Design\n\n### Core Tables\n\n#### projects\n- id: UUID primary key\n- name: VARCHAR(255)\n- mission: TEXT\n- tenant_key: VARCHAR(100) for isolation\n- status: ENUM('active', 'completed', 'archived')\n- created_at: TIMESTAMP\n- updated_at: TIMESTAMP\n\n#### agents\n- id: UUID primary key\n- project_id: UUID foreign key\n- name: VARCHAR(100)\n- mission: TEXT\n- context_budget: INTEGER default 150000\n- context_used: INTEGER default 0\n- status: ENUM('active', 'idle', 'decommissioned')\n\n#### messages\n- id: UUID primary key\n- project_id: UUID foreign key\n- from_agent: VARCHAR(100)\n- to_agents: JSON array\n- content: TEXT\n- type: ENUM('direct', 'broadcast')\n- priority: ENUM('high', 'normal', 'low')\n- acknowledged_by: JSON array\n- completed_by: JSON array\n\n### Relationships\n- One project has many agents\n- One project has many messages\n- Messages use JSON arrays for multi-recipient support\n\n### Indexes\n- projects: (tenant_key, status)\n- agents: (project_id, status)\n- messages: (project_id, created_at)",
    "tokens": 1250
  }
}
```

### 22. get_product_settings

Gets all product settings for analysis.

**Request:**

```json
{
  "tool": "get_product_settings",
  "parameters": {
    "product_id": "prod_123" // optional
  }
}
```

**Response:**

```json
{
  "success": true,
  "settings": {
    "product": {
      "id": "prod_123",
      "name": "GiljoAI MCP Orchestrator",
      "version": "1.0.0",
      "environment": "development"
    },
    "orchestration": {
      "max_agents": 20,
      "context_budget_default": 150000,
      "message_timeout_seconds": 300,
      "handoff_grace_period_seconds": 60,
      "auto_decommission": true
    },
    "database": {
      "type": "postgresql",
      "path": "giljo.db",
      "pool_size": 5,
      "journal_mode": "WAL"
    },
    "features": {
      "vision_chunking": true,
      "message_acknowledgments": true,
      "dynamic_discovery": true,
      "template_system": true,
      "multi_tenancy": true
    },
    "limits": {
      "max_vision_tokens": 100000,
      "max_message_size": 50000,
      "max_tasks_per_job": 100,
      "max_concurrent_projects": 10
    }
  }
}
```

### 23. session_info

Gets current session statistics.

**Request:**

```json
{
  "tool": "session_info",
  "parameters": {}
}
```

**Response:**

```json
{
  "success": true,
  "session": {
    "id": "session_abc123",
    "started": "2025-09-16T09:00:00Z",
    "uptime_seconds": 25200,
    "uptime_human": "7 hours",
    "statistics": {
      "total_projects": 5,
      "active_projects": 2,
      "total_agents": 23,
      "active_agents": 8,
      "messages_sent": 1247,
      "messages_pending": 34,
      "tasks_completed": 189,
      "tasks_pending": 42,
      "context_used_total": 890000,
      "api_calls": 3456
    },
    "performance": {
      "avg_message_latency_ms": 125,
      "avg_task_completion_minutes": 15,
      "cache_hit_rate": 0.87,
      "error_rate": 0.002
    },
    "resources": {
      "memory_used_mb": 256,
      "cpu_percent": 15,
      "disk_used_mb": 1024,
      "network_io_mb": 512
    }
  }
}
```

### 24. recalibrate_mission

Notifies agents about mission changes.

**Request:**

```json
{
  "tool": "recalibrate_mission",
  "parameters": {
    "project_id": "550e8400-e29b-41d4-a716-446655440000",
    "changes_summary": "Priority shift: Focus on mobile-first design. Payment processing moved to Phase 4. Add real-time inventory tracking to Phase 2."
  }
}
```

**Response:**

```json
{
  "success": true,
  "recalibration": {
    "project_id": "550e8400-e29b-41d4-a716-446655440000",
    "timestamp": "2025-09-16T13:00:00Z",
    "changes_summary": "Priority shift: Focus on mobile-first design...",
    "agents_notified": [
      "orchestrator",
      "frontend_dev",
      "backend_dev",
      "tester"
    ],
    "notification_count": 4,
    "rediscovery_triggered": true
  }
}
```

### 25. help

Gets documentation for all available tools.

**Request:**

```json
{
  "tool": "help",
  "parameters": {}
}
```

**Response:**

```json
{
  "success": true,
  "help": {
    "total_tools": 25,
    "categories": {
      "project_management": {
        "count": 5,
        "tools": [
          {
            "name": "list_projects",
            "description": "List all projects with optional status filter",
            "parameters": ["status"],
            "example": "list_projects(status='active')"
          },
          {
            "name": "project_status",
            "description": "Get comprehensive project status",
            "parameters": ["project_id"],
            "example": "project_status(project_id='uuid')"
          }
          // ... other project tools
          // Note: Project creation uses REST API (POST /api/v1/projects/)
        ]
      },
      "agent_management": {
        "count": 6,
        "tools": [
          {
            "name": "ensure_agent",
            "description": "Ensure an agent exists (idempotent - safe for workers)",
            "parameters": ["project_id", "agent_name", "mission"],
            "example": "ensure_agent(project_id='uuid', agent_name='tester')"
          }
          // ... other agent tools
        ]
      },
      "message_communication": {
        "count": 6,
        "tools": [
          {
            "name": "send_message",
            "description": "Send message to one or more agents",
            "parameters": [
              "to_agents",
              "content",
              "project_id",
              "message_type",
              "priority",
              "from_agent"
            ],
            "example": "send_message(to_agents=['dev'], content='Please review', project_id='uuid')"
          }
          // ... other message tools
        ]
      },
      "context_vision": {
        "count": 8,
        "tools": [
          {
            "name": "get_vision",
            "description": "Get vision document (auto-chunks for 50K+ tokens)",
            "parameters": ["part", "max_tokens"],
            "example": "get_vision(part=1, max_tokens=20000)"
          }
          // ... other context tools
        ]
      }
    },
    "usage_tips": [
      "Use ensure_agent() for workers - it's idempotent",
      "Only use activate_agent() for orchestrator",
      "Always acknowledge messages when received",
      "Vision documents auto-chunk at 50K+ tokens",
      "Use project tenant keys for isolation"
    ]
  }
}
```

---

## Error Response Format

All tools return consistent error responses:

```json
{
  "success": false,
  "error": {
    "code": "AGENT_NOT_FOUND",
    "message": "Agent 'unknown_agent' not found in project",
    "details": {
      "agent_name": "unknown_agent",
      "project_id": "550e8400-e29b-41d4-a716-446655440000"
    }
  },
  "timestamp": "2025-09-16T15:30:00Z"
}
```

### Common Error Codes

- `PROJECT_NOT_FOUND` - Project ID doesn't exist
- `AGENT_NOT_FOUND` - Agent name not found in project
- `MESSAGE_NOT_FOUND` - Message ID doesn't exist
- `CONTEXT_OVERFLOW` - Agent context budget exceeded
- `INVALID_PARAMETERS` - Missing or invalid parameters
- `PERMISSION_DENIED` - Operation not allowed
- `RATE_LIMITED` - Too many requests
- `DATABASE_ERROR` - Database operation failed
- `VISION_PART_NOT_FOUND` - Requested vision part doesn't exist
- `HANDOFF_FAILED` - Agent handoff couldn't complete

---

## Rate Limits

Default rate limits per tenant:

- **Project operations**: 10 per minute
- **Agent operations**: 100 per minute
- **Message operations**: 1000 per minute
- **Context operations**: 500 per minute

---

## WebSocket Events

For real-time updates, connect to the WebSocket endpoint:

```javascript
const ws = new WebSocket("ws://localhost:8080/ws");

ws.on("message", (data) => {
  const event = JSON.parse(data);

  switch (event.type) {
    case "agent.created":
      console.log(`New agent: ${event.agent_name}`);
      break;

    case "message.sent":
      console.log(`Message from ${event.from} to ${event.to}`);
      break;

    case "task.completed":
      console.log(`Task completed: ${event.task_id}`);
      break;

    case "project.status_changed":
      console.log(`Project ${event.project_id} is now ${event.status}`);
      break;
  }
});
```

---

_Last Updated: 2025-09-16_
_API Version: 1.0.0_
