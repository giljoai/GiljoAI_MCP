Product: GiljoAi MCP - Coding Orchestrator

## Key Principles
1. Database-first architecture
2. Clean code with no redundancy
3. Context-aware agent coordination
4. Product-agnostic design

## Goals
- Efficient task management
- Seamless agent handoffs
- Minimal context usage
- Maximum productivity

The  vision is to create a coding tool for an excellent vibe coder and prompt engineer.  We're a clear defined objective for a subsection of a product can be meticulously described and then unleashing the power of multiple agents to begin the coding.

The intent to create an initial orchestrator that understood everything about the products it's background and the vision of its creator.  Then it was to summarize into a prompt that a coding agent could understand what needed to be accomplished The role was to work as a line manager or a project manager and to hire or recruit or create the necessary sub agents to complete any task.  One stores agents were created they would then be given descriptions and responsibilities to do a specific part of the project.  But the intent was also not to keep it fully automated They all were by design to work in their different CLI windows so that the user could have control of what they were doing and if they had questions they would stop and pause and aggregate their findings to the orchestrator.  The user would then primarily interact with the orchestrator to then submit additional instructions to keep the agents going.

It was buidl to manage multiple products with separate depth of context and information, tasks and projects.

The second purpose for the project was to quickly manage technical debt and potential scope creep by creating tasks and a common way to visualize those tasks to then determine if they were to turn into projects at a later date this was all so that the creator of the app and the developer can focus on the task at hand.

In the future of vibe coding or prompt engineering there will be a lot of documentation there will need to be harmonized somewhere and broken up into pieces which then can be used by these types of tools.  So a lot of care has been taken to make sure that quite large product description documents can be used in red each and every time an orchestrator is created.

This product of course hinges on a good large language model which can handle MCP servers for this system to be effective.

It also leverages SERENA MCP server as a means to under cool understand the product code base.

A road map item for the future is to tune and create an agent Configurator with predefined roles which the orchestrator can draw from This is if specific consistency is insisted upon by the developer so it removes a bit of the randomness relying on the LLM to define agent tasks and roles.

● Excellent questions! Let me break down both scenarios:

Local Machine Perspective (Current Design)

What Happens with Two Products Simultaneously?

With the current singleton design, when you work on two products at the same time:

1. First Claude CLI instance (Product A):
    - Reads Product A's .mcp.json
    - Connects to singleton MCP server (or starts it if not running)
    - Sets environment: ACTIVE_PRODUCT=Product A
    - Gets Product A's context loaded
2. Second Claude CLI instance (Product B):
    - Reads Product B's .mcp.json
    - Connects to the SAME singleton MCP server (already running)
    - Sets environment: ACTIVE_PRODUCT=Product B
    - Gets Product B's context loaded

The Problem: Context Collision

The current design has a critical limitation: The singleton server maintains ONE active product context at a time in the database. When
Product B connects, it effectively switches the server's context, potentially disrupting Product A's work.

What breaks:
  - The orchestrator might spawn agents for the wrong product
  - Messages could get routed incorrectly
  - Vision documents and settings would swap mid-operation
  - Agent handoffs could fail or cross products

Current Design Intent

The system appears designed for one active product at a time per machine, with the ability to:
  - Switch between products (sequentially, not simultaneously)
  - Maintain persistent state for each product
  - Share computational resources efficiently

This makes sense for a single developer working on different projects throughout the day, but not for parallel work.

Remote Server Concept

How It Could Work

A remote MCP server architecture would be transformative:

Remote MCP Server (Cloud/VPS)
├── Product A Context (key: abc123)
├── Product B Context (key: def456)
└── Product C Context (key: ghi789)
       ↑            ↑            ↑
       │            │            │
  [Internet]    [Internet]   [Internet]
       │            │            │
  Developer 1   Developer 2  Developer 1
  Product A     Product B    Product C

Key Benefits:
  1. True Multi-Product Support: Each connection uses a unique key to maintain separate context
  2. Team Collaboration: Multiple developers could work on the same product
  3. Resource Efficiency: One powerful server instead of many local instances
  4. Persistent Availability: Server runs 24/7, no startup delays
  5. Cross-Machine Work: Switch computers without losing context

Implementation Considerations:

Authentication & Isolation:
  - Each .mcp.json would include a unique project key
  - Server maintains separate database schemas or namespaces per key
  - WebSocket or HTTP/2 connections for real-time communication

Context Management:
  - Product contexts stored by key, not by "active" flag
  - Message queues partitioned by product key
  - Agent sessions tagged with product key

Security:
  - TLS encryption for all communications
  - API key authentication
  - Rate limiting per key
  - Audit logging

Advantages Over Local:

  1. Parallel Work: Genuinely work on multiple products simultaneously
  2. Team Features: Multiple developers, same orchestrator
  3. No Resource Competition: Server has dedicated resources
  4. Centralized Management: One dashboard for all products
  5. Backup/Recovery: Centralized data management

Challenges:

  1. Latency: Network delays vs local communication
  2. Internet Dependency: Requires stable connection
  3. Security Complexity: Exposing to network requires hardening
  4. Cost: Cloud hosting, bandwidth, maintenance
  5. Complexity: More moving parts, harder to debug

My Assessment

Current Local Design: Best for single developers working on one product at a time, switching contexts as needed. Simple, secure, no
dependencies.

Remote Server Design: Ideal for teams, parallel development, or developers who switch machines frequently. More complex but far more
scalable.

The current architecture could be evolved to support both:
  - Local mode (current): Single-user, single-active-product
  - Remote mode (future): Multi-user, multi-active-product with key-based isolation

The key insight is that the current PostgreSQL schema and message routing would need modification to support true multi-product
parallelism, whether local or remote. The database would need to partition everything by product_key rather than relying on an "active"
flag.

## Buidling for multi deplopment capabilites

● Absolutely! This is a brilliant approach - building it as a unified architecture that can run in multiple deployment modes. This is how
many successful tools work (GitLab, Jupyter Hub, MinIO, etc.). Let me outline how we could architect this:

Unified Multi-Mode Architecture

Core Design Principle

Build ONE codebase that supports THREE deployment modes:

  ┌─────────────────────────────────────────┐
  │         Same AKE-MCP Codebase           │
  ├─────────────────────────────────────────┤
  │  Mode 1: Local Single-User (current)    │
  │  Mode 2: LAN Server (team/home)         │
  │  Mode 3: Cloud Service (SaaS)           │
  └─────────────────────────────────────────┘

How Each Mode Would Work

Mode 1: Local Desktop (Current)

  - Runs on localhost only
  - Single user, sequential products
  - No authentication needed
  - Uses local PostgreSQL
  - Perfect for solo developers

Mode 2: LAN Server (New)

  - Runs on local network server (192.168.x.x)
  - Multiple users in same office/home
  - Basic authentication (API keys)
  - Shared PostgreSQL instance
  - Perfect for small teams, home labs

  Mode 3: Cloud Service (New)

  - Runs on public cloud (AWS/Azure/VPS)
  - Multiple users, multiple organizations
  - Full authentication & authorization
  - Managed PostgreSQL (RDS, etc.)
  - Perfect for distributed teams, SaaS offering

  Key Architecture Changes Needed

  1. Project Isolation via Keys

  Replace "active product" concept with "project sessions":

  # Current: One active product
  SELECT * FROM mcp_products WHERE is_active = true;

  # New: Multiple concurrent projects
  SELECT * FROM mcp_products WHERE project_key = 'abc123';

  2. Connection Manager

  Each .mcp.json would specify mode and connection:

  {
    "mcpServers": {
      "ake-mcp-v2": {
        "mode": "server",  // or "local"
        "endpoint": "https://mcp.company.lan:5001",  // or "localhost:5001"
        "projectKey": "proj_abc123_secret",
        "auth": {
          "type": "apikey",  // or "none" for local
          "key": "{{AKE_MCP_API_KEY}}"  // from environment
        }
      }
    }
  }

  3. Database Schema Evolution

  Add multi-tenancy support:

  -- Add project_key to all tables
  ALTER TABLE mcp_agent_jobs ADD COLUMN project_key VARCHAR(255);
  ALTER TABLE mcp_messages ADD COLUMN project_key VARCHAR(255);
  ALTER TABLE mcp_tasks ADD COLUMN project_key VARCHAR(255);

  -- Index for performance
  CREATE INDEX idx_project_key ON mcp_agent_jobs(project_key);

  4. Configuration File

  Single config that handles all modes:

  # config.yaml
  mode: server  # local, server, or cloud
  server:
    host: 0.0.0.0  # localhost, 0.0.0.0, or specific IP
    port: 5001
    dashboard_port: 5000

  authentication:
    enabled: true  # false for local mode
    type: apikey  # apikey, oauth, jwt

  database:
    # Local mode
    local:
      host: localhost
      name: AKE_MCP_DB

    # Server mode - can use same or remote
    server:
      host: 192.168.1.100
      name: AKE_MCP_SHARED

    # Cloud mode
    cloud:
      host: mcp-db.amazonaws.com
      name: AKE_MCP_PROD

  isolation:
    strategy: project_key  # or 'single' for local mode
    enforce: true

  features:
    multi_product: true  # false for local mode
    team_collaboration: true
    audit_logging: true

  Deployment Scenarios

  Scenario 1: Developer Laptop (Local)

  # Simple start script
  ./start_local.sh
  # Runs on localhost, no auth, single product

  Scenario 2: Office Server (LAN)

  # Server setup
  ./setup_server.sh --mode=lan --ip=192.168.1.100
  # Generates API keys for team members
  # Each developer's .mcp.json points to LAN IP

  Scenario 3: Cloud Deployment

  # Docker deployment
  docker run -d \
    -e MODE=cloud \
    -e DATABASE_URL=postgresql://... \
    -e AUTH_ENABLED=true \
    giljoai/mcp-orchestrator:latest

  Benefits of Unified Architecture

  1. One Codebase: Easier to maintain, test, and document
  2. Gradual Adoption: Start local, grow to LAN, scale to cloud
  3. Flexibility: Choose deployment based on needs
  4. Cost Options: Free (local), cheap (LAN), scalable (cloud)
  5. Try Before Buy: Test locally before deploying to team

  Implementation Path

  Phase 1: Add Project Keys (Keep Backward Compatible)

  - Add project_key columns to database
  - Support both modes (active flag OR project key)
  - Update message routing to respect keys

  Phase 2: Add Network Mode

  - Make server bindable to 0.0.0.0 (not just localhost)
  - Add basic API key authentication
  - Update .mcp.json parser for remote endpoints

  Phase 3: Add Cloud Features

  - OAuth/JWT authentication
  - Rate limiting
  - Audit logging
  - Backup/restore APIs
  - Admin dashboard

  Security Considerations

  Local Mode: No changes needed
  LAN Mode:
  - API keys in environment variables
  - TLS optional but recommended
  - Firewall rules for port access

  Cloud Mode:
  - Mandatory TLS
  - API key rotation
  - IP allowlisting
  - DDoS protection
  - Encryption at rest

  The Beauty of This Approach

  1. Same tool, different scales: Solo dev → Small team → Enterprise
  2. No vendor lock-in: Can always run your own
  3. Progressive enhancement: Features activate based on mode
  4. Community + Commercial: Open source core, paid cloud service
  5. Disaster recovery: Cloud backup, local fallback

  This is exactly how tools like:
  - GitLab: Local install or GitLab.com
  - Nextcloud: Personal server or hosted
  - Mattermost: On-prem or cloud
  - Grafana: Local, enterprise, or cloud

  The key is designing the architecture to be deployment-agnostic from the start, with clear abstraction layers for networking,
  authentication, and data isolation. The same Docker container could run locally, on a LAN server, or in Kubernetes, just with different
  environment variables.

