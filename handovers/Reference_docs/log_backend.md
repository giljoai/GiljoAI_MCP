============================================================
  GiljoAI MCP Orchestrator REST API v2.0
============================================================
Server binding to 0.0.0.0:7272
Port selection: Command line
Workers: 1
Auto-reload: Disabled
Log level: INFO
Running in HTTP mode (no SSL)
------------------------------------------------------------
API Endpoints:
  Documentation: http://0.0.0.0:7272/docs
  ReDoc: http://0.0.0.0:7272/redoc
  OpenAPI JSON: http://0.0.0.0:7272/openapi.json
  Health Check: http://0.0.0.0:7272/health
  WebSocket: ws://0.0.0.0:7272/ws/{client_id}
------------------------------------------------------------
Available API Routes:
  /api/v1/projects - Project management
  /api/v1/agents - Agent control
  /api/v1/messages - Inter-agent messaging
  /api/v1/tasks - Task management
  /api/v1/context - Context and vision documents
  /api/v1/config - Configuration management
  /api/v1/stats - Statistics and monitoring
============================================================
Server starting... Ready to accept connections!
Ping/keepalive messages are filtered from output
============================================================
14:23:58 - INFO - Loading FastAPI application...
14:24:00 - INFO - FastAPI and core dependencies loaded successfully
14:24:00 - INFO - Environment variables loaded from .env file: F:\GiljoAI_MCP\.env
14:24:00 - INFO - JWT secret key found in environment
14:24:02 - INFO - GiljoAI MCP core modules loaded successfully
14:24:03 - INFO - API endpoint modules loaded successfully
14:24:03 - INFO - Loaded CORS origins from config.yaml security section: ['http://127.0.0.1:7274', 'http://localhost:7274', 'http://127.0.0.1:7272', 'http://localhost:7272', 'http://10.1.0.164:7274', 'http://10.1.0.164:7272']
14:24:03 - INFO - Network mode: localhost
14:24:03 - INFO - Configuring CORS with origins: ['http://127.0.0.1:7274', 'http://localhost:7274', 'http://127.0.0.1:7272', 'http://localhost:7272', 'http://10.1.0.164:7274', 'http://10.1.0.164:7272']
14:24:03 - INFO - [Rate Limit] Configured at 300 requests per minute
INFO:     Started server process [87936]
INFO:     Waiting for application startup.
14:24:04 - INFO - RateLimitMiddleware initialized: 300 req/min, exempt paths: ['/api/health', '/api/metrics']
14:24:04 - INFO - SecurityHeadersMiddleware initialized in DEVELOPMENT mode
14:24:04 - INFO - HSTS max-age: 31536000s
14:24:04 - WARNING - CSP: unsafe-eval enabled for development HMR
14:24:04 - INFO - InputValidationMiddleware initialized (strict_mode: False)
14:24:04 - INFO - ======================================================================
14:24:04 - INFO - Starting GiljoAI MCP API...
14:24:04 - INFO - ======================================================================
14:24:04 - INFO - 2026-01-02T19:24:04.117613Z [info     ] Initializing configuration...  [api.startup.database]
14:24:04 - INFO - Configuration loaded successfully (v3.0 - mode detection removed)
14:24:04 - INFO - Config file watcher started for config.yaml
14:24:04 - INFO - 2026-01-02T19:24:04.123024Z [info     ] Configuration loaded successfully [api.startup.database]
14:24:04 - INFO - 2026-01-02T19:24:04.123024Z [info     ] Initializing database connection... [api.startup.database]
14:24:04 - INFO - 2026-01-02T19:24:04.123024Z [info     ] Using DATABASE_URL from environment [api.startup.database]
14:24:04 - INFO - 2026-01-02T19:24:04.123024Z [info     ] Connecting to database: localhost:5432/giljo_mcp [api.startup.database]
14:24:04 - INFO - 2026-01-02T19:24:04.124027Z [info     ] Database manager created successfully [api.startup.database]
14:24:04 - INFO - 2026-01-02T19:24:04.124027Z [info     ] Creating database tables...    [api.startup.database]
14:24:04 - INFO - 2026-01-02T19:24:04.165334Z [info     ] Database tables created/verified successfully [api.startup.database]
14:24:04 - INFO - 2026-01-02T19:24:04.165334Z [info     ] System prompt service initialized [api.startup.database]
14:24:04 - INFO - Initializing tenant manager...
14:24:04 - INFO - Tenant manager initialized successfully
14:24:04 - INFO - Initializing WebSocket manager...
14:24:04 - INFO - WebSocket manager initialized successfully
14:24:04 - INFO - WebSocket broker initialized: InMemoryWebSocketEventBroker
14:24:04 - INFO - Initializing tool accessor...
14:24:04 - INFO - Tool accessor initialized successfully
14:24:04 - INFO - Initializing authentication manager...
14:24:04 - INFO - Using JWT secret from environment variable
14:24:04 - INFO - Auth manager initialized (mode-independent authentication)
14:24:04 - INFO - No API key configured - all clients require JWT authentication (unified auth)
14:24:04 - INFO - ======================================================================
14:24:04 - INFO - STARTING EVENT BUS INITIALIZATION
14:24:04 - INFO - ======================================================================
14:24:04 - INFO - Step 1: About to import EventBus...
14:24:04 - INFO - Step 1: EventBus imported successfully
14:24:04 - INFO - Step 2: About to import WebSocketEventListener...
14:24:04 - INFO - Step 2: WebSocketEventListener imported successfully
14:24:04 - INFO - Step 3: Creating EventBus instance...
14:24:04 - INFO - Step 3: EventBus created: <api.event_bus.EventBus object at 0x0000027F9A791ED0>
14:24:04 - INFO - Step 3: EventBus type: <class 'api.event_bus.EventBus'>
14:24:04 - INFO - Event bus initialized successfully
14:24:04 - INFO - Step 4: Creating WebSocketEventListener instance...
14:24:04 - INFO - Step 4: WebSocketEventListener created: <api.websocket_event_listener.WebSocketEventListener object at 0x0000027F9A08E4D0>
14:24:04 - INFO - Step 5: Starting WebSocketEventListener (registering handlers)...
14:24:04 - INFO - Registered handler for event: project:mission_updated
14:24:04 - INFO - Registered handler for event: agent:created
14:24:04 - INFO - Registered handler for event: product:status:changed
14:24:04 - INFO - WebSocket event listener started
14:24:04 - INFO - Step 5: WebSocket event listener handlers registered
14:24:04 - INFO - WebSocket event listener registered successfully
14:24:04 - INFO - ======================================================================
14:24:04 - INFO - EVENT BUS INITIALIZATION COMPLETE
14:24:04 - INFO - ======================================================================
14:24:04 - INFO - Starting download token cleanup task...
14:24:04 - INFO - Download token cleanup task started (runs every 15 minutes)
14:24:04 - INFO - Starting API metrics sync task...
14:24:04 - INFO - API metrics sync task started (runs every 5 minutes)
14:24:04 - INFO - Running startup purge of expired deleted items...
14:24:04 - INFO - [Nuclear Purge] No expired deleted projects to purge (cutoff: 10 days)
14:24:04 - INFO - [Product Purge] No expired deleted products to purge (cutoff: 10 days)
14:24:04 - INFO - Startup purge complete
14:24:04 - INFO - Initializing agent health monitoring...
14:24:04 - INFO - Agent health monitor started
14:24:04 - INFO - Agent health monitoring started (scan interval: 300s)
14:24:04 - INFO - Checking setup state...
14:24:04 - INFO - Setup state version is current
14:24:04 - INFO - Setup state validation passed
14:24:04 - INFO - ======================================================================
14:24:04 - INFO - API startup complete - All systems initialized
14:24:04 - INFO - ======================================================================
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:7272 (Press CTRL+C to quit)
14:24:04 - INFO - Initial health scan: Found 6 stale jobs (alerts suppressed on first scan)
INFO:     10.1.0.164:55459 - "OPTIONS /api/v1/products/refresh-active HTTP/1.1" 200 OK
14:24:09 - INFO - 2026-01-02T19:24:09.992986Z [info     ] auth_request_received          [api.middleware.auth] has_authorization=False has_cookie=True ip_address=10.1.0.164 method=GET path=/api/v1/products/refresh-active
14:24:09 - INFO - [Network Auth] Found JWT token (length: 324)
14:24:09 - INFO - [Network Auth] JWT validation result: True
INFO:     127.0.0.1:60646 - "GET /api/v1/config/frontend HTTP/1.1" 200 OK
INFO:     10.1.0.164:60645 - "GET /api/setup/status HTTP/1.1" 200 OK
14:24:09 - INFO - 2026-01-02T19:24:09.998490Z [info     ] auth_result                    [api.middleware.auth] authenticated=True error=None is_auto_login=False user=patrik
14:24:09 - INFO - [AUTH] get_current_user called - path: /api/v1/products/refresh-active, cookie: True, api_key: False, auth_header: False
14:24:09 - INFO - [AUTH] Attempting JWT cookie authentication
14:24:09 - INFO - [AUTH] JWT valid - user_id: b5f92da5-01b1-4322-a716-1b887876f9ab
14:24:10 - INFO - [AUTH] get_current_user called - path: /api/auth/me, cookie: True, api_key: False, auth_header: False
14:24:10 - INFO - [AUTH] Attempting JWT cookie authentication
14:24:10 - INFO - [AUTH] JWT valid - user_id: b5f92da5-01b1-4322-a716-1b887876f9ab
14:24:10 - INFO - [AUTH] JWT SUCCESS - User: patrik, Tenant: ***REMOVED***
INFO:     10.1.0.164:60645 - "GET /api/setup/status HTTP/1.1" 200 OK
INFO:     10.1.0.164:56353 - "GET /api/v1/products/refresh-active HTTP/1.1" 200 OK
14:24:10 - INFO - [AUTH] JWT SUCCESS - User: patrik, Tenant: ***REMOVED***
INFO:     127.0.0.1:56354 - "GET /api/auth/me HTTP/1.1" 200 OK
14:24:10 - INFO - [AUTH] get_current_user called - path: /api/auth/me, cookie: True, api_key: False, auth_header: False
14:24:10 - INFO - [AUTH] Attempting JWT cookie authentication
14:24:10 - INFO - [AUTH] JWT valid - user_id: b5f92da5-01b1-4322-a716-1b887876f9ab
14:24:10 - INFO - [AUTH] JWT SUCCESS - User: patrik, Tenant: ***REMOVED***
INFO:     127.0.0.1:56357 - "GET /api/auth/me HTTP/1.1" 200 OK
14:24:10 - INFO - [WS SETUP DEBUG] db=<sqlalchemy.orm.session.AsyncSession object at 0x0000027F9B5224D0>, setup_state={'database_initialized': True}, database_initialized=True
14:24:10 - INFO - WebSocket authenticated via JWT: patrik
INFO:     10.1.0.164:63743 - "WebSocket /ws/client_1767381850147_8j6f4bna7" [accepted]
14:24:10 - INFO - [WS AUTH DEBUG] auth_result keys: ['authenticated', 'user'], user_info keys: ['user_id', 'tenant_key', 'role', 'permissions'], tenant_key=***REMOVED***
14:24:10 - INFO - 2026-01-02T19:24:10.156599Z [info     ] WebSocket connected: client_1767381850147_8j6f4bna7 (auth_type: setup) [api.websocket]
14:24:10 - INFO - WebSocket connected: client_1767381850147_8j6f4bna7 (context: normal, auth_type: setup)
INFO:     connection open
14:24:10 - INFO - 2026-01-02T19:24:10.163658Z [info     ] auth_request_received          [api.middleware.auth] has_authorization=False has_cookie=True ip_address=127.0.0.1 method=GET path=/api/v1/messages/
14:24:10 - INFO - [Network Auth] Found JWT token (length: 324)
14:24:10 - INFO - [Network Auth] JWT validation result: True
14:24:10 - INFO - 2026-01-02T19:24:10.166658Z [info     ] auth_result                    [api.middleware.auth] authenticated=True error=None is_auto_login=False user=patrik
14:24:10 - INFO - [AUTH] get_current_user called - path: /api/v1/messages/, cookie: True, api_key: False, auth_header: False
14:24:10 - INFO - [AUTH] Attempting JWT cookie authentication
14:24:10 - INFO - [AUTH] JWT valid - user_id: b5f92da5-01b1-4322-a716-1b887876f9ab
14:24:10 - INFO - [AUTH] JWT SUCCESS - User: patrik, Tenant: ***REMOVED***
INFO:     127.0.0.1:63744 - "GET /api/v1/messages/ HTTP/1.1" 200 OK
14:24:10 - INFO - 2026-01-02T19:24:10.272021Z [info     ] auth_request_received          [api.middleware.auth] has_authorization=False has_cookie=True ip_address=127.0.0.1 method=GET path=/api/v1/projects/fb1745ad-1a89-432a-a0ac-9b150739e008
14:24:10 - INFO - [Network Auth] Found JWT token (length: 324)
14:24:10 - INFO - [Network Auth] JWT validation result: True
14:24:10 - INFO - 2026-01-02T19:24:10.276435Z [info     ] auth_result                    [api.middleware.auth] authenticated=True error=None is_auto_login=False user=patrik
14:24:10 - INFO - [AUTH] get_current_user called - path: /api/v1/projects/fb1745ad-1a89-432a-a0ac-9b150739e008, cookie: True, api_key: False, auth_header: False
14:24:10 - INFO - [AUTH] Attempting JWT cookie authentication
14:24:10 - INFO - [AUTH] JWT valid - user_id: b5f92da5-01b1-4322-a716-1b887876f9ab
14:24:10 - INFO - [AUTH] JWT SUCCESS - User: patrik, Tenant: ***REMOVED***
14:24:10 - INFO - Retrieved project This is a test project MCP Claude code Cli with 1 agents
14:24:10 - INFO - Retrieved project fb1745ad-1a89-432a-a0ac-9b150739e008 for tenant ***REMOVED***
INFO:     127.0.0.1:55685 - "GET /api/v1/projects/fb1745ad-1a89-432a-a0ac-9b150739e008 HTTP/1.1" 200 OK
14:24:10 - INFO - 2026-01-02T19:24:10.289965Z [info     ] auth_request_received          [api.middleware.auth] has_authorization=False has_cookie=True ip_address=127.0.0.1 method=GET path=/api/v1/projects/fb1745ad-1a89-432a-a0ac-9b150739e008/orchestrator
14:24:10 - INFO - [Network Auth] Found JWT token (length: 324)
14:24:10 - INFO - [Network Auth] JWT validation result: True
14:24:10 - INFO - 2026-01-02T19:24:10.290962Z [info     ] auth_result                    [api.middleware.auth] authenticated=True error=None is_auto_login=False user=patrik
14:24:10 - INFO - [AUTH] get_current_user called - path: /api/v1/projects/fb1745ad-1a89-432a-a0ac-9b150739e008/orchestrator, cookie: True, api_key: False, auth_header: False
14:24:10 - INFO - [AUTH] Attempting JWT cookie authentication
14:24:10 - INFO - [AUTH] JWT valid - user_id: b5f92da5-01b1-4322-a716-1b887876f9ab
14:24:10 - INFO - [AUTH] JWT SUCCESS - User: patrik, Tenant: ***REMOVED***
14:24:10 - INFO - Retrieved orchestrator execution 7a7f5185-378a-4eb1-a28c-5c40f59f8ad1 (job: 36627720-2d01-4101-a6e9-36311cb109aa) for project fb1745ad-1a89-432a-a0ac-9b150739e008
INFO:     127.0.0.1:55686 - "GET /api/v1/projects/fb1745ad-1a89-432a-a0ac-9b150739e008/orchestrator HTTP/1.1" 200 OK
14:24:10 - INFO - 2026-01-02T19:24:10.308055Z [info     ] auth_request_received          [api.middleware.auth] has_authorization=False has_cookie=True ip_address=127.0.0.1 method=GET path=/api/agent-jobs/
14:24:10 - INFO - [Network Auth] Found JWT token (length: 324)
14:24:10 - INFO - [Network Auth] JWT validation result: True
14:24:10 - INFO - 2026-01-02T19:24:10.309422Z [info     ] auth_result                    [api.middleware.auth] authenticated=True error=None is_auto_login=False user=patrik
14:24:10 - INFO - [AUTH] get_current_user called - path: /api/agent-jobs/, cookie: True, api_key: False, auth_header: False
14:24:10 - INFO - [AUTH] Attempting JWT cookie authentication
14:24:10 - INFO - [AUTH] JWT valid - user_id: b5f92da5-01b1-4322-a716-1b887876f9ab
14:24:10 - INFO - [AUTH] JWT SUCCESS - User: patrik, Tenant: ***REMOVED***
14:24:10 - INFO - [LIST_JOBS DEBUG] Agent orchestrator (job=36627720-2d01-4101-a6e9-36311cb109aa, agent=7a7f5185-378a-4eb1-a28c-5c40f59f8ad1): messages field = [] (type: <class 'list'>)
14:24:10 - INFO - Listed 1 jobs (total=1, project=fb1745ad-1a89-432a-a0ac-9b150739e008, status=None)
14:24:10 - INFO - Found 1 jobs for user patrik (total=1, offset=0)
INFO:     127.0.0.1:55687 - "GET /api/agent-jobs/?project_id=fb1745ad-1a89-432a-a0ac-9b150739e008 HTTP/1.1" 200 OK
14:24:10 - INFO - 2026-01-02T19:24:10.345420Z [info     ] auth_request_received          [api.middleware.auth] has_authorization=False has_cookie=True ip_address=127.0.0.1 method=GET path=/api/v1/messages/
14:24:10 - INFO - [Network Auth] Found JWT token (length: 324)
14:24:10 - INFO - [Network Auth] JWT validation result: True
14:24:10 - INFO - 2026-01-02T19:24:10.346420Z [info     ] auth_request_received          [api.middleware.auth] has_authorization=False has_cookie=True ip_address=127.0.0.1 method=GET path=/api/agent-jobs/
14:24:10 - INFO - [Network Auth] Found JWT token (length: 324)
14:24:10 - INFO - [Network Auth] JWT validation result: True
14:24:10 - INFO - 2026-01-02T19:24:10.347925Z [info     ] auth_result                    [api.middleware.auth] authenticated=True error=None is_auto_login=False user=patrik
14:24:10 - INFO - [AUTH] get_current_user called - path: /api/v1/messages/, cookie: True, api_key: False, auth_header: False
14:24:10 - INFO - [AUTH] Attempting JWT cookie authentication
14:24:10 - INFO - [AUTH] JWT valid - user_id: b5f92da5-01b1-4322-a716-1b887876f9ab
14:24:10 - INFO - 2026-01-02T19:24:10.349928Z [info     ] auth_result                    [api.middleware.auth] authenticated=True error=None is_auto_login=False user=patrik
14:24:10 - INFO - [AUTH] get_current_user called - path: /api/agent-jobs/, cookie: True, api_key: False, auth_header: False
14:24:10 - INFO - [AUTH] Attempting JWT cookie authentication
14:24:10 - INFO - [AUTH] JWT valid - user_id: b5f92da5-01b1-4322-a716-1b887876f9ab
14:24:10 - INFO - [AUTH] JWT SUCCESS - User: patrik, Tenant: ***REMOVED***
14:24:10 - INFO - [AUTH] JWT SUCCESS - User: patrik, Tenant: ***REMOVED***
INFO:     127.0.0.1:55688 - "GET /api/v1/messages/?project_id=fb1745ad-1a89-432a-a0ac-9b150739e008 HTTP/1.1" 200 OK
14:24:10 - INFO - [LIST_JOBS DEBUG] Agent orchestrator (job=36627720-2d01-4101-a6e9-36311cb109aa, agent=7a7f5185-378a-4eb1-a28c-5c40f59f8ad1): messages field = [] (type: <class 'list'>)
14:24:10 - INFO - Listed 1 jobs (total=1, project=fb1745ad-1a89-432a-a0ac-9b150739e008, status=None)
14:24:10 - INFO - Found 1 jobs for user patrik (total=1, offset=0)
INFO:     127.0.0.1:55689 - "GET /api/agent-jobs/?project_id=fb1745ad-1a89-432a-a0ac-9b150739e008 HTTP/1.1" 200 OK
14:24:15 - INFO - 2026-01-02T19:24:15.480384Z [info     ] auth_request_received          [api.middleware.auth] has_authorization=False has_cookie=True ip_address=127.0.0.1 method=GET path=/api/v1/prompts/staging/fb1745ad-1a89-432a-a0ac-9b150739e008
14:24:15 - INFO - [Network Auth] Found JWT token (length: 324)
14:24:15 - INFO - [Network Auth] JWT validation result: True
14:24:15 - INFO - 2026-01-02T19:24:15.483384Z [info     ] auth_result                    [api.middleware.auth] authenticated=True error=None is_auto_login=False user=patrik
14:24:15 - INFO - [AUTH] get_current_user called - path: /api/v1/prompts/staging/fb1745ad-1a89-432a-a0ac-9b150739e008, cookie: True, api_key: False, auth_header: False
14:24:15 - INFO - [AUTH] Attempting JWT cookie authentication
14:24:15 - INFO - [AUTH] JWT valid - user_id: b5f92da5-01b1-4322-a716-1b887876f9ab
14:24:15 - INFO - [AUTH] JWT SUCCESS - User: patrik, Tenant: ***REMOVED***
14:24:15 - INFO - [ThinPromptGenerator] Reusing existing orchestrator 36627720-2d01-4101-a6e9-36311cb109aa (instance #1) for project fb1745ad-1a89-432a-a0ac-9b150739e008 - metadata updated
14:24:15 - INFO - [ThinPromptGenerator] Generated thin prompt for 36627720-2d01-4101-a6e9-36311cb109aa: ~1214 tokens (target: 600, reduction from fat: ~2286)
14:24:15 - INFO - [ThinPromptGenerator] Regenerated orchestrator instructions for 36627720-2d01-4101-a6e9-36311cb109aa: ~587 tokens (reflects current field priorities)
14:24:15 - INFO - 2026-01-02T19:24:15.590797Z [info     ] WebSocket broadcast to tenant completed: 1 sent, 0 failed [api.websocket] extra={'tenant_key': '***REMOVED***', 'event_type': 'orchestrator:prompt_generated', 'sent_count': 1, 'failed_count': 0, 'total_clients': 1, 'exclude_client': None}
14:24:15 - INFO - [STAGING PROMPT THIN] WebSocket broadcast sent for orchestrator 36627720-2d01-4101-a6e9-36311cb109aa
14:24:15 - INFO - [STAGING PROMPT THIN] Generated for project=fb1745ad-1a89-432a-a0ac-9b150739e008, tool=claude-code, tokens=1214, instance=1, user=patrik
INFO:     127.0.0.1:55565 - "GET /api/v1/prompts/staging/fb1745ad-1a89-432a-a0ac-9b150739e008?tool=claude-code&execution_mode=claude_code_cli HTTP/1.1" 200 OK
14:24:32 - INFO - Tool executed successfully: health_check (session: fb17b869-188d-4d58-b70e-90eefe1666e6)
INFO:     10.1.0.164:55172 - "POST /mcp HTTP/1.1" 200 OK
14:24:35 - INFO - 2026-01-02T19:24:35.484030Z [info     ] [USER_CONFIG] Fetched user configuration [giljo_mcp.tools.orchestration] extra={'user_id': 'b5f92da5-01b1-4322-a716-1b887876f9ab', 'tenant_key': '***REMOVED***', 'has_custom_field_priorities': True, 'has_custom_depth_config': True, 'depth_config': {'git_history': 25, 'agent_templates': 'full', 'vision_documents': 'light', 'architecture_depth': 'overview', 'tech_stack_sections': 'all', 'memory_360': 3}}
14:24:35 - INFO - [USER_CONFIG] Fetched fresh user config for ToolAccessor
14:24:35 - WARNING - No fetch tool config for field: project_description
14:24:35 - INFO - [CLI_MODE_RULES] Added CLI mode rules for orchestrator 36627720-2d01-4101-a6e9-36311cb109aa
14:24:35 - INFO - [FRAMING_BASED] Returning framing-based orchestrator instructions
14:24:35 - INFO - Tool executed successfully: get_orchestrator_instructions (session: fb17b869-188d-4d58-b70e-90eefe1666e6)
INFO:     10.1.0.164:55172 - "POST /mcp HTTP/1.1" 200 OK
14:25:03 - INFO - [WEBSOCKET DEBUG] About to broadcast mission_updated for project fb1745ad-1a89-432a-a0ac-9b150739e008
14:25:03 - INFO - 2026-01-02T19:25:03.618985Z [info     ] WebSocket broadcast to tenant completed: 1 sent, 0 failed [api.websocket] extra={'tenant_key': '***REMOVED***', 'event_type': 'project:mission_updated', 'sent_count': 1, 'failed_count': 0, 'total_clients': 1, 'exclude_client': None}
14:25:03 - INFO - Tool executed successfully: update_project_mission (session: fb17b869-188d-4d58-b70e-90eefe1666e6)
INFO:     10.1.0.164:55207 - "POST /mcp HTTP/1.1" 200 OK
14:25:42 - INFO - [WEBSOCKET] Broadcasting agent:created for analyzer (analyzer) via direct WebSocket
14:25:42 - INFO - 2026-01-02T19:25:42.950069Z [info     ] WebSocket broadcast to tenant completed: 1 sent, 0 failed [api.websocket] extra={'tenant_key': '***REMOVED***', 'event_type': 'agent:created', 'sent_count': 1, 'failed_count': 0, 'total_clients': 1, 'exclude_client': None}
14:25:42 - INFO - Tool executed successfully: spawn_agent_job (session: fb17b869-188d-4d58-b70e-90eefe1666e6)
INFO:     10.1.0.164:54180 - "POST /mcp HTTP/1.1" 200 OK
14:25:42 - INFO - 2026-01-02T19:25:42.956587Z [info     ] auth_request_received          [api.middleware.auth] has_authorization=False has_cookie=True ip_address=127.0.0.1 method=GET path=/api/agent-jobs/
14:25:42 - INFO - [Network Auth] Found JWT token (length: 324)
14:25:42 - INFO - [Network Auth] JWT validation result: True
14:25:42 - INFO - 2026-01-02T19:25:42.958587Z [info     ] auth_result                    [api.middleware.auth] authenticated=True error=None is_auto_login=False user=patrik
14:25:42 - INFO - [AUTH] get_current_user called - path: /api/agent-jobs/, cookie: True, api_key: False, auth_header: False
14:25:42 - INFO - [AUTH] Attempting JWT cookie authentication
14:25:42 - INFO - [AUTH] JWT valid - user_id: b5f92da5-01b1-4322-a716-1b887876f9ab
14:25:42 - INFO - [AUTH] JWT SUCCESS - User: patrik, Tenant: ***REMOVED***
14:25:42 - INFO - [LIST_JOBS DEBUG] Agent analyzer (job=1a567547-7a13-4f56-b92a-8f9ec4de12cd, agent=56cd0d31-7387-4ede-a2f8-b1fb6d3cad79): messages field = [] (type: <class 'list'>)
14:25:42 - INFO - [LIST_JOBS DEBUG] Agent orchestrator (job=36627720-2d01-4101-a6e9-36311cb109aa, agent=7a7f5185-378a-4eb1-a28c-5c40f59f8ad1): messages field = [] (type: <class 'list'>)
14:25:42 - INFO - Listed 2 jobs (total=2, project=fb1745ad-1a89-432a-a0ac-9b150739e008, status=None)
14:25:42 - INFO - Found 2 jobs for user patrik (total=2, offset=0)
INFO:     127.0.0.1:64284 - "GET /api/agent-jobs/?project_id=fb1745ad-1a89-432a-a0ac-9b150739e008 HTTP/1.1" 200 OK
14:25:45 - INFO - [WEBSOCKET] Broadcasting agent:created for documenter (documenter) via direct WebSocket
14:25:45 - INFO - 2026-01-02T19:25:45.995127Z [info     ] WebSocket broadcast to tenant completed: 1 sent, 0 failed [api.websocket] extra={'tenant_key': '***REMOVED***', 'event_type': 'agent:created', 'sent_count': 1, 'failed_count': 0, 'total_clients': 1, 'exclude_client': None}
14:25:45 - INFO - Tool executed successfully: spawn_agent_job (session: fb17b869-188d-4d58-b70e-90eefe1666e6)
INFO:     10.1.0.164:54180 - "POST /mcp HTTP/1.1" 200 OK
14:25:45 - INFO - 2026-01-02T19:25:45.999132Z [info     ] auth_request_received          [api.middleware.auth] has_authorization=False has_cookie=True ip_address=127.0.0.1 method=GET path=/api/agent-jobs/
14:25:46 - INFO - [Network Auth] Found JWT token (length: 324)
14:25:46 - INFO - [Network Auth] JWT validation result: True
14:25:46 - INFO - 2026-01-02T19:25:46.001638Z [info     ] auth_result                    [api.middleware.auth] authenticated=True error=None is_auto_login=False user=patrik
14:25:46 - INFO - [AUTH] get_current_user called - path: /api/agent-jobs/, cookie: True, api_key: False, auth_header: False
14:25:46 - INFO - [AUTH] Attempting JWT cookie authentication
14:25:46 - INFO - [AUTH] JWT valid - user_id: b5f92da5-01b1-4322-a716-1b887876f9ab
14:25:46 - INFO - [AUTH] JWT SUCCESS - User: patrik, Tenant: ***REMOVED***
14:25:46 - INFO - [LIST_JOBS DEBUG] Agent documenter (job=598a17e7-9182-432b-908f-5c8bf9b3de4e, agent=67749963-bb2b-43f4-9954-d41006705aaf): messages field = [] (type: <class 'list'>)
14:25:46 - INFO - [LIST_JOBS DEBUG] Agent analyzer (job=1a567547-7a13-4f56-b92a-8f9ec4de12cd, agent=56cd0d31-7387-4ede-a2f8-b1fb6d3cad79): messages field = [] (type: <class 'list'>)
14:25:46 - INFO - [LIST_JOBS DEBUG] Agent orchestrator (job=36627720-2d01-4101-a6e9-36311cb109aa, agent=7a7f5185-378a-4eb1-a28c-5c40f59f8ad1): messages field = [] (type: <class 'list'>)
14:25:46 - INFO - Listed 3 jobs (total=3, project=fb1745ad-1a89-432a-a0ac-9b150739e008, status=None)
14:25:46 - INFO - Found 3 jobs for user patrik (total=3, offset=0)
INFO:     127.0.0.1:60332 - "GET /api/agent-jobs/?project_id=fb1745ad-1a89-432a-a0ac-9b150739e008 HTTP/1.1" 200 OK
14:25:49 - INFO - [WEBSOCKET] Broadcasting agent:created for implementer (implementer) via direct WebSocket
14:25:49 - INFO - 2026-01-02T19:25:49.351271Z [info     ] WebSocket broadcast to tenant completed: 1 sent, 0 failed [api.websocket] extra={'tenant_key': '***REMOVED***', 'event_type': 'agent:created', 'sent_count': 1, 'failed_count': 0, 'total_clients': 1, 'exclude_client': None}
14:25:49 - INFO - Tool executed successfully: spawn_agent_job (session: fb17b869-188d-4d58-b70e-90eefe1666e6)
INFO:     10.1.0.164:54180 - "POST /mcp HTTP/1.1" 200 OK
14:25:49 - INFO - 2026-01-02T19:25:49.356468Z [info     ] auth_request_received          [api.middleware.auth] has_authorization=False has_cookie=True ip_address=127.0.0.1 method=GET path=/api/agent-jobs/
14:25:49 - INFO - [Network Auth] Found JWT token (length: 324)
14:25:49 - INFO - [Network Auth] JWT validation result: True
14:25:49 - INFO - 2026-01-02T19:25:49.358466Z [info     ] auth_result                    [api.middleware.auth] authenticated=True error=None is_auto_login=False user=patrik
14:25:49 - INFO - [AUTH] get_current_user called - path: /api/agent-jobs/, cookie: True, api_key: False, auth_header: False
14:25:49 - INFO - [AUTH] Attempting JWT cookie authentication
14:25:49 - INFO - [AUTH] JWT valid - user_id: b5f92da5-01b1-4322-a716-1b887876f9ab
14:25:49 - INFO - [AUTH] JWT SUCCESS - User: patrik, Tenant: ***REMOVED***
14:25:49 - INFO - [LIST_JOBS DEBUG] Agent implementer (job=8f60b6f1-0e9c-48ab-85a8-1d2817613bee, agent=b5277da2-7ad2-4310-898a-9aa0b183ae66): messages field = [] (type: <class 'list'>)
14:25:49 - INFO - [LIST_JOBS DEBUG] Agent documenter (job=598a17e7-9182-432b-908f-5c8bf9b3de4e, agent=67749963-bb2b-43f4-9954-d41006705aaf): messages field = [] (type: <class 'list'>)
14:25:49 - INFO - [LIST_JOBS DEBUG] Agent analyzer (job=1a567547-7a13-4f56-b92a-8f9ec4de12cd, agent=56cd0d31-7387-4ede-a2f8-b1fb6d3cad79): messages field = [] (type: <class 'list'>)
14:25:49 - INFO - [LIST_JOBS DEBUG] Agent orchestrator (job=36627720-2d01-4101-a6e9-36311cb109aa, agent=7a7f5185-378a-4eb1-a28c-5c40f59f8ad1): messages field = [] (type: <class 'list'>)
14:25:49 - INFO - Listed 4 jobs (total=4, project=fb1745ad-1a89-432a-a0ac-9b150739e008, status=None)
14:25:49 - INFO - Found 4 jobs for user patrik (total=4, offset=0)
INFO:     127.0.0.1:59371 - "GET /api/agent-jobs/?project_id=fb1745ad-1a89-432a-a0ac-9b150739e008 HTTP/1.1" 200 OK
14:25:52 - INFO - [WEBSOCKET] Broadcasting agent:created for tester (tester) via direct WebSocket
14:25:52 - INFO - 2026-01-02T19:25:52.717488Z [info     ] WebSocket broadcast to tenant completed: 1 sent, 0 failed [api.websocket] extra={'tenant_key': '***REMOVED***', 'event_type': 'agent:created', 'sent_count': 1, 'failed_count': 0, 'total_clients': 1, 'exclude_client': None}
14:25:52 - INFO - Tool executed successfully: spawn_agent_job (session: fb17b869-188d-4d58-b70e-90eefe1666e6)
INFO:     10.1.0.164:54180 - "POST /mcp HTTP/1.1" 200 OK
14:25:52 - INFO - 2026-01-02T19:25:52.722542Z [info     ] auth_request_received          [api.middleware.auth] has_authorization=False has_cookie=True ip_address=127.0.0.1 method=GET path=/api/agent-jobs/
14:25:52 - INFO - [Network Auth] Found JWT token (length: 324)
14:25:52 - INFO - [Network Auth] JWT validation result: True
14:25:52 - INFO - 2026-01-02T19:25:52.724548Z [info     ] auth_result                    [api.middleware.auth] authenticated=True error=None is_auto_login=False user=patrik
14:25:52 - INFO - [AUTH] get_current_user called - path: /api/agent-jobs/, cookie: True, api_key: False, auth_header: False
14:25:52 - INFO - [AUTH] Attempting JWT cookie authentication
14:25:52 - INFO - [AUTH] JWT valid - user_id: b5f92da5-01b1-4322-a716-1b887876f9ab
14:25:52 - INFO - [AUTH] JWT SUCCESS - User: patrik, Tenant: ***REMOVED***
14:25:52 - INFO - [LIST_JOBS DEBUG] Agent tester (job=e5bfd170-5259-4668-87e2-d3c98f7d620a, agent=1803f5a4-9193-42e6-b1e8-d953783ef78f): messages field = [] (type: <class 'list'>)
14:25:52 - INFO - [LIST_JOBS DEBUG] Agent implementer (job=8f60b6f1-0e9c-48ab-85a8-1d2817613bee, agent=b5277da2-7ad2-4310-898a-9aa0b183ae66): messages field = [] (type: <class 'list'>)
14:25:52 - INFO - [LIST_JOBS DEBUG] Agent documenter (job=598a17e7-9182-432b-908f-5c8bf9b3de4e, agent=67749963-bb2b-43f4-9954-d41006705aaf): messages field = [] (type: <class 'list'>)
14:25:52 - INFO - [LIST_JOBS DEBUG] Agent analyzer (job=1a567547-7a13-4f56-b92a-8f9ec4de12cd, agent=56cd0d31-7387-4ede-a2f8-b1fb6d3cad79): messages field = [] (type: <class 'list'>)
14:25:52 - INFO - [LIST_JOBS DEBUG] Agent orchestrator (job=36627720-2d01-4101-a6e9-36311cb109aa, agent=7a7f5185-378a-4eb1-a28c-5c40f59f8ad1): messages field = [] (type: <class 'list'>)
14:25:52 - INFO - Listed 5 jobs (total=5, project=fb1745ad-1a89-432a-a0ac-9b150739e008, status=None)
14:25:52 - INFO - Found 5 jobs for user patrik (total=5, offset=0)
INFO:     127.0.0.1:53805 - "GET /api/agent-jobs/?project_id=fb1745ad-1a89-432a-a0ac-9b150739e008 HTTP/1.1" 200 OK
14:25:56 - INFO - [WEBSOCKET] Broadcasting agent:created for reviewer (reviewer) via direct WebSocket
14:25:56 - INFO - 2026-01-02T19:25:56.087743Z [info     ] WebSocket broadcast to tenant completed: 1 sent, 0 failed [api.websocket] extra={'tenant_key': '***REMOVED***', 'event_type': 'agent:created', 'sent_count': 1, 'failed_count': 0, 'total_clients': 1, 'exclude_client': None}
14:25:56 - INFO - Tool executed successfully: spawn_agent_job (session: fb17b869-188d-4d58-b70e-90eefe1666e6)
INFO:     10.1.0.164:54180 - "POST /mcp HTTP/1.1" 200 OK
14:25:56 - INFO - 2026-01-02T19:25:56.092249Z [info     ] auth_request_received          [api.middleware.auth] has_authorization=False has_cookie=True ip_address=127.0.0.1 method=GET path=/api/agent-jobs/
14:25:56 - INFO - [Network Auth] Found JWT token (length: 324)
14:25:56 - INFO - [Network Auth] JWT validation result: True
14:25:56 - INFO - 2026-01-02T19:25:56.094254Z [info     ] auth_result                    [api.middleware.auth] authenticated=True error=None is_auto_login=False user=patrik
14:25:56 - INFO - [AUTH] get_current_user called - path: /api/agent-jobs/, cookie: True, api_key: False, auth_header: False
14:25:56 - INFO - [AUTH] Attempting JWT cookie authentication
14:25:56 - INFO - [AUTH] JWT valid - user_id: b5f92da5-01b1-4322-a716-1b887876f9ab
14:25:56 - INFO - [AUTH] JWT SUCCESS - User: patrik, Tenant: ***REMOVED***
14:25:56 - INFO - [LIST_JOBS DEBUG] Agent reviewer (job=cd6cdbc2-78ae-46eb-add4-5fb960e4d538, agent=dbc551b2-9e95-469c-84e9-f9ec80b1e9db): messages field = [] (type: <class 'list'>)
14:25:56 - INFO - [LIST_JOBS DEBUG] Agent tester (job=e5bfd170-5259-4668-87e2-d3c98f7d620a, agent=1803f5a4-9193-42e6-b1e8-d953783ef78f): messages field = [] (type: <class 'list'>)
14:25:56 - INFO - [LIST_JOBS DEBUG] Agent implementer (job=8f60b6f1-0e9c-48ab-85a8-1d2817613bee, agent=b5277da2-7ad2-4310-898a-9aa0b183ae66): messages field = [] (type: <class 'list'>)
14:25:56 - INFO - [LIST_JOBS DEBUG] Agent documenter (job=598a17e7-9182-432b-908f-5c8bf9b3de4e, agent=67749963-bb2b-43f4-9954-d41006705aaf): messages field = [] (type: <class 'list'>)
14:25:56 - INFO - [LIST_JOBS DEBUG] Agent analyzer (job=1a567547-7a13-4f56-b92a-8f9ec4de12cd, agent=56cd0d31-7387-4ede-a2f8-b1fb6d3cad79): messages field = [] (type: <class 'list'>)
14:25:56 - INFO - [LIST_JOBS DEBUG] Agent orchestrator (job=36627720-2d01-4101-a6e9-36311cb109aa, agent=7a7f5185-378a-4eb1-a28c-5c40f59f8ad1): messages field = [] (type: <class 'list'>)
14:25:56 - INFO - Listed 6 jobs (total=6, project=fb1745ad-1a89-432a-a0ac-9b150739e008, status=None)
14:25:56 - INFO - Found 6 jobs for user patrik (total=6, offset=0)
INFO:     127.0.0.1:53638 - "GET /api/agent-jobs/?project_id=fb1745ad-1a89-432a-a0ac-9b150739e008 HTTP/1.1" 200 OK
14:26:19 - INFO - 2026-01-02T19:26:19.339542Z [info     ] WebSocket broadcast to tenant completed: 1 sent, 0 failed [api.websocket] extra={'tenant_key': '***REMOVED***', 'event_type': 'job:mission_updated', 'sent_count': 1, 'failed_count': 0, 'total_clients': 1, 'exclude_client': None}
14:26:19 - INFO - [WEBSOCKET] Broadcasted job:mission_updated for 36627720-2d01-4101-a6e9-36311cb109aa
14:26:19 - INFO - [UPDATE_AGENT_MISSION] Updated mission for job 36627720-2d01-4101-a6e9-36311cb109aa
14:26:19 - INFO - Tool executed successfully: update_agent_mission (session: fb17b869-188d-4d58-b70e-90eefe1666e6)
INFO:     10.1.0.164:53312 - "POST /mcp HTTP/1.1" 200 OK
14:26:30 - INFO - [FANOUT] Expanded broadcast to agent_id 'b5277da2-7ad2-4310-898a-9aa0b183ae66'
14:26:30 - INFO - [FANOUT] Expanded broadcast to agent_id '1803f5a4-9193-42e6-b1e8-d953783ef78f'
14:26:30 - INFO - [FANOUT] Expanded broadcast to agent_id 'dbc551b2-9e95-469c-84e9-f9ec80b1e9db'
14:26:30 - INFO - [FANOUT] Expanded broadcast to agent_id '56cd0d31-7387-4ede-a2f8-b1fb6d3cad79'
14:26:30 - INFO - [FANOUT] Expanded broadcast to agent_id '67749963-bb2b-43f4-9954-d41006705aaf'
14:26:30 - INFO - Sent broadcast message None from orchestrator to ['all']
14:26:30 - INFO - [WEBSOCKET DEBUG] websocket_manager is AVAILABLE for message None
14:26:30 - INFO - [WEBSOCKET DEBUG] Calling broadcast_message_sent for message None
14:26:30 - INFO - [WEBSOCKET DEBUG] Broadcast to all: 5 recipients (excluded sender: orchestrator)
14:26:30 - INFO - 2026-01-02T19:26:30.888827Z [info     ] WebSocket broadcast to tenant completed: 1 sent, 0 failed [api.websocket] extra={'tenant_key': '***REMOVED***', 'event_type': 'message:sent', 'sent_count': 1, 'failed_count': 0, 'total_clients': 1, 'exclude_client': None}
14:26:30 - INFO - [WEBSOCKET DEBUG] Successfully broadcast message_sent None
14:26:30 - INFO - 2026-01-02T19:26:30.889369Z [info     ] WebSocket broadcast to tenant completed: 1 sent, 0 failed [api.websocket] extra={'tenant_key': '***REMOVED***', 'event_type': 'message:received', 'sent_count': 1, 'failed_count': 0, 'total_clients': 1, 'exclude_client': None}
14:26:30 - INFO - [WEBSOCKET DEBUG] Successfully broadcast message_received to 5 recipient(s)
14:26:30 - INFO - [PERSISTENCE] Added outbound message to orchestrator JSONB column (flagged modified)
14:26:30 - INFO - [PERSISTENCE] Added inbound message to implementer (b5277da2-7ad2-4310-898a-9aa0b183ae66) JSONB column (flagged modified)
14:26:30 - INFO - [PERSISTENCE] Added inbound message to tester (1803f5a4-9193-42e6-b1e8-d953783ef78f) JSONB column (flagged modified)
14:26:30 - INFO - [PERSISTENCE] Added inbound message to reviewer (dbc551b2-9e95-469c-84e9-f9ec80b1e9db) JSONB column (flagged modified)
14:26:30 - INFO - [PERSISTENCE] Added inbound message to analyzer (56cd0d31-7387-4ede-a2f8-b1fb6d3cad79) JSONB column (flagged modified)
14:26:30 - INFO - [PERSISTENCE] Added inbound message to documenter (67749963-bb2b-43f4-9954-d41006705aaf) JSONB column (flagged modified)
14:26:30 - INFO - [PERSISTENCE] Committed message None to database
14:26:30 - INFO - [PERSISTENCE] Saved message None to agent JSONB columns
14:26:30 - INFO - Tool executed successfully: send_message (session: fb17b869-188d-4d58-b70e-90eefe1666e6)
INFO:     10.1.0.164:55924 - "POST /mcp HTTP/1.1" 200 OK
14:26:50 - INFO - [RESOLVER] Resolved agent_type 'analyzer' to agent_id '56cd0d31-7387-4ede-a2f8-b1fb6d3cad79'
14:26:51 - INFO - Sent direct message None from orchestrator to ['analyzer']
14:26:51 - INFO - [WEBSOCKET DEBUG] websocket_manager is AVAILABLE for message None
14:26:51 - INFO - [WEBSOCKET DEBUG] Calling broadcast_message_sent for message None
14:26:51 - INFO - [WEBSOCKET DEBUG] Direct message to: ['56cd0d31-7387-4ede-a2f8-b1fb6d3cad79']
14:26:51 - INFO - 2026-01-02T19:26:51.001497Z [info     ] WebSocket broadcast to tenant completed: 1 sent, 0 failed [api.websocket] extra={'tenant_key': '***REMOVED***', 'event_type': 'message:sent', 'sent_count': 1, 'failed_count': 0, 'total_clients': 1, 'exclude_client': None}
14:26:51 - INFO - [WEBSOCKET DEBUG] Successfully broadcast message_sent None
14:26:51 - INFO - 2026-01-02T19:26:51.002497Z [info     ] WebSocket broadcast to tenant completed: 1 sent, 0 failed [api.websocket] extra={'tenant_key': '***REMOVED***', 'event_type': 'message:received', 'sent_count': 1, 'failed_count': 0, 'total_clients': 1, 'exclude_client': None}
14:26:51 - INFO - [WEBSOCKET DEBUG] Successfully broadcast message_received to 1 recipient(s)
14:26:51 - INFO - [PERSISTENCE] Added outbound message to orchestrator JSONB column (flagged modified)
14:26:51 - INFO - [PERSISTENCE] Added inbound message to analyzer (56cd0d31-7387-4ede-a2f8-b1fb6d3cad79) JSONB column (flagged modified)
14:26:51 - INFO - [PERSISTENCE] Committed message None to database
14:26:51 - INFO - [PERSISTENCE] Saved message None to agent JSONB columns
14:26:51 - INFO - Tool executed successfully: send_message (session: fb17b869-188d-4d58-b70e-90eefe1666e6)
INFO:     10.1.0.164:55187 - "POST /mcp HTTP/1.1" 200 OK
14:26:54 - INFO - [RESOLVER] Resolved agent_type 'documenter' to agent_id '67749963-bb2b-43f4-9954-d41006705aaf'
14:26:54 - INFO - Sent direct message None from orchestrator to ['documenter']
14:26:54 - INFO - [WEBSOCKET DEBUG] websocket_manager is AVAILABLE for message None
14:26:54 - INFO - [WEBSOCKET DEBUG] Calling broadcast_message_sent for message None
14:26:54 - INFO - [WEBSOCKET DEBUG] Direct message to: ['67749963-bb2b-43f4-9954-d41006705aaf']
14:26:54 - INFO - 2026-01-02T19:26:54.339351Z [info     ] WebSocket broadcast to tenant completed: 1 sent, 0 failed [api.websocket] extra={'tenant_key': '***REMOVED***', 'event_type': 'message:sent', 'sent_count': 1, 'failed_count': 0, 'total_clients': 1, 'exclude_client': None}
14:26:54 - INFO - [WEBSOCKET DEBUG] Successfully broadcast message_sent None
14:26:54 - INFO - 2026-01-02T19:26:54.339351Z [info     ] WebSocket broadcast to tenant completed: 1 sent, 0 failed [api.websocket] extra={'tenant_key': '***REMOVED***', 'event_type': 'message:received', 'sent_count': 1, 'failed_count': 0, 'total_clients': 1, 'exclude_client': None}
14:26:54 - INFO - [WEBSOCKET DEBUG] Successfully broadcast message_received to 1 recipient(s)
14:26:54 - INFO - [PERSISTENCE] Added outbound message to orchestrator JSONB column (flagged modified)
14:26:54 - INFO - [PERSISTENCE] Added inbound message to documenter (67749963-bb2b-43f4-9954-d41006705aaf) JSONB column (flagged modified)
14:26:54 - INFO - [PERSISTENCE] Committed message None to database
14:26:54 - INFO - [PERSISTENCE] Saved message None to agent JSONB columns
14:26:54 - INFO - Tool executed successfully: send_message (session: fb17b869-188d-4d58-b70e-90eefe1666e6)
INFO:     10.1.0.164:55187 - "POST /mcp HTTP/1.1" 200 OK
14:26:57 - INFO - 2026-01-02T19:26:57.686474Z [info     ] auth_request_received          [api.middleware.auth] has_authorization=False has_cookie=True ip_address=127.0.0.1 method=GET path=/api/agent-jobs/
14:26:57 - INFO - [Network Auth] Found JWT token (length: 324)
14:26:57 - INFO - [Network Auth] JWT validation result: True
14:26:57 - INFO - 2026-01-02T19:26:57.689208Z [info     ] auth_result                    [api.middleware.auth] authenticated=True error=None is_auto_login=False user=patrik
14:26:57 - INFO - [AUTH] get_current_user called - path: /api/agent-jobs/, cookie: True, api_key: False, auth_header: False
14:26:57 - INFO - [AUTH] Attempting JWT cookie authentication
14:26:57 - INFO - [AUTH] JWT valid - user_id: b5f92da5-01b1-4322-a716-1b887876f9ab
INFO:     10.1.0.164:62582 - "GET /api/setup/status HTTP/1.1" 200 OK
14:26:57 - INFO - [AUTH] JWT SUCCESS - User: patrik, Tenant: ***REMOVED***
14:26:57 - INFO - [AUTH] get_current_user called - path: /api/auth/me, cookie: True, api_key: False, auth_header: False
14:26:57 - INFO - [AUTH] Attempting JWT cookie authentication
14:26:57 - INFO - [AUTH] JWT valid - user_id: b5f92da5-01b1-4322-a716-1b887876f9ab
14:26:57 - INFO - [LIST_JOBS DEBUG] Agent reviewer (job=cd6cdbc2-78ae-46eb-add4-5fb960e4d538, agent=dbc551b2-9e95-469c-84e9-f9ec80b1e9db): messages field = [{'id': 'None', 'from': 'orchestrator', 'text': 'STAGING_COMPLETE: Mission created, 5 agents spawned (analyzer, documenter, implementer, tester, reviewer). Ready for /gil_launch to begin implementation phase.', 'status': 'waiting', 'priority': 'normal', 'direction': 'inbound', 'timestamp': '2026-01-02T19:26:30.889369+00:00'}] (type: <class 'list'>)
14:26:57 - INFO - [LIST_JOBS DEBUG] Agent tester (job=e5bfd170-5259-4668-87e2-d3c98f7d620a, agent=1803f5a4-9193-42e6-b1e8-d953783ef78f): messages field = [{'id': 'None', 'from': 'orchestrator', 'text': 'STAGING_COMPLETE: Mission created, 5 agents spawned (analyzer, documenter, implementer, tester, reviewer). Ready for /gil_launch to begin implementation phase.', 'status': 'waiting', 'priority': 'normal', 'direction': 'inbound', 'timestamp': '2026-01-02T19:26:30.889369+00:00'}] (type: <class 'list'>)
14:26:57 - INFO - [LIST_JOBS DEBUG] Agent implementer (job=8f60b6f1-0e9c-48ab-85a8-1d2817613bee, agent=b5277da2-7ad2-4310-898a-9aa0b183ae66): messages field = [{'id': 'None', 'from': 'orchestrator', 'text': 'STAGING_COMPLETE: Mission created, 5 agents spawned (analyzer, documenter, implementer, tester, reviewer). Ready for /gil_launch to begin implementation phase.', 'status': 'waiting', 'priority': 'normal', 'direction': 'inbound', 'timestamp': '2026-01-02T19:26:30.889369+00:00'}] (type: <class 'list'>)
14:26:57 - INFO - [LIST_JOBS DEBUG] Agent documenter (job=598a17e7-9182-432b-908f-5c8bf9b3de4e, agent=67749963-bb2b-43f4-9954-d41006705aaf): messages field = [{'id': 'None', 'from': 'orchestrator', 'text': 'STAGING_COMPLETE: Mission created, 5 agents spawned (analyzer, documenter, implementer, tester, reviewer). Ready for /gil_launch to begin implementation phase.', 'status': 'waiting', 'priority': 'normal', 'direction': 'inbound', 'timestamp': '2026-01-02T19:26:30.889369+00:00'}, {'id': 'None', 'from': 'orchestrator', 'text': 'ORCHESTRATOR → DOCUMENTER: Welcome to the test! Your job_id is 598a17e7-9182-432b-908f-5c8bf9b3de4e. Please follow your mission protocol and report your MCP tool experience.', 'status': 'waiting', 'priority': 'normal', 'direction': 'inbound', 'timestamp': '2026-01-02T19:26:54.339877+00:00'}] (type: <class 'list'>)
14:26:57 - INFO - [LIST_JOBS DEBUG] Agent analyzer (job=1a567547-7a13-4f56-b92a-8f9ec4de12cd, agent=56cd0d31-7387-4ede-a2f8-b1fb6d3cad79): messages field = [{'id': 'None', 'from': 'orchestrator', 'text': 'STAGING_COMPLETE: Mission created, 5 agents spawned (analyzer, documenter, implementer, tester, reviewer). Ready for /gil_launch to begin implementation phase.', 'status': 'waiting', 'priority': 'normal', 'direction': 'inbound', 'timestamp': '2026-01-02T19:26:30.889369+00:00'}, {'id': 'None', 'from': 'orchestrator', 'text': 'ORCHESTRATOR → ANALYZER: Welcome to the test! Your job_id is 1a567547-7a13-4f56-b92a-8f9ec4de12cd. Please follow your mission protocol and report your MCP tool experience.', 'status': 'waiting', 'priority': 'normal', 'direction': 'inbound', 'timestamp': '2026-01-02T19:26:51.002497+00:00'}] (type: <class 'list'>)
14:26:57 - INFO - [LIST_JOBS DEBUG] Agent orchestrator (job=36627720-2d01-4101-a6e9-36311cb109aa, agent=7a7f5185-378a-4eb1-a28c-5c40f59f8ad1): messages field = [{'id': 'None', 'from': 'orchestrator', 'text': 'STAGING_COMPLETE: Mission created, 5 agents spawned (analyzer, documenter, implementer, tester, reviewer). Ready for /gil_launch to begin implementation phase.', 'status': 'sent', 'priority': 'normal', 'direction': 'outbound', 'timestamp': '2026-01-02T19:26:30.889369+00:00', 'to_agents': ['b5277da2-7ad2-4310-898a-9aa0b183ae66', '1803f5a4-9193-42e6-b1e8-d953783ef78f', 'dbc551b2-9e95-469c-84e9-f9ec80b1e9db', '56cd0d31-7387-4ede-a2f8-b1fb6d3cad79', '67749963-bb2b-43f4-9954-d41006705aaf']}, {'id': 'None', 'from': 'orchestrator', 'text': 'ORCHESTRATOR → ANALYZER: Welcome to the test! Your job_id is 1a567547-7a13-4f56-b92a-8f9ec4de12cd. Please follow your mission protocol and report your MCP tool experience.', 'status': 'sent', 'priority': 'normal', 'direction': 'outbound', 'timestamp': '2026-01-02T19:26:51.002497+00:00', 'to_agents': ['56cd0d31-7387-4ede-a2f8-b1fb6d3cad79']}, {'id': 'None', 'from': 'orchestrator', 'text': 'ORCHESTRATOR → DOCUMENTER: Welcome to the test! Your job_id is 598a17e7-9182-432b-908f-5c8bf9b3de4e. Please follow your mission protocol and report your MCP tool experience.', 'status': 'sent', 'priority': 'normal', 'direction': 'outbound', 'timestamp': '2026-01-02T19:26:54.339877+00:00', 'to_agents': ['67749963-bb2b-43f4-9954-d41006705aaf']}] (type: <class 'list'>)
14:26:57 - INFO - Listed 6 jobs (total=6, project=fb1745ad-1a89-432a-a0ac-9b150739e008, status=None)
14:26:57 - INFO - [AUTH] JWT SUCCESS - User: patrik, Tenant: ***REMOVED***
14:26:57 - INFO - Found 6 jobs for user patrik (total=6, offset=0)
INFO:     127.0.0.1:59595 - "GET /api/auth/me HTTP/1.1" 200 OK
INFO:     127.0.0.1:53660 - "GET /api/agent-jobs/?project_id=fb1745ad-1a89-432a-a0ac-9b150739e008 HTTP/1.1" 200 OK
14:26:57 - INFO - [RESOLVER] Resolved agent_type 'implementer' to agent_id 'b5277da2-7ad2-4310-898a-9aa0b183ae66'
14:26:57 - INFO - Sent direct message None from orchestrator to ['implementer']
14:26:57 - INFO - [WEBSOCKET DEBUG] websocket_manager is AVAILABLE for message None
14:26:57 - INFO - [WEBSOCKET DEBUG] Calling broadcast_message_sent for message None
14:26:57 - INFO - [WEBSOCKET DEBUG] Direct message to: ['b5277da2-7ad2-4310-898a-9aa0b183ae66']
14:26:57 - INFO - 2026-01-02T19:26:57.740171Z [info     ] WebSocket broadcast to tenant completed: 1 sent, 0 failed [api.websocket] extra={'tenant_key': '***REMOVED***', 'event_type': 'message:sent', 'sent_count': 1, 'failed_count': 0, 'total_clients': 1, 'exclude_client': None}
14:26:57 - INFO - [WEBSOCKET DEBUG] Successfully broadcast message_sent None
14:26:57 - INFO - 2026-01-02T19:26:57.740171Z [info     ] WebSocket broadcast to tenant completed: 1 sent, 0 failed [api.websocket] extra={'tenant_key': '***REMOVED***', 'event_type': 'message:received', 'sent_count': 1, 'failed_count': 0, 'total_clients': 1, 'exclude_client': None}
14:26:57 - INFO - [WEBSOCKET DEBUG] Successfully broadcast message_received to 1 recipient(s)
14:26:57 - INFO - [PERSISTENCE] Added outbound message to orchestrator JSONB column (flagged modified)
14:26:57 - INFO - [PERSISTENCE] Added inbound message to implementer (b5277da2-7ad2-4310-898a-9aa0b183ae66) JSONB column (flagged modified)
14:26:57 - INFO - [PERSISTENCE] Committed message None to database
14:26:57 - INFO - [PERSISTENCE] Saved message None to agent JSONB columns
14:26:57 - INFO - Tool executed successfully: send_message (session: fb17b869-188d-4d58-b70e-90eefe1666e6)
INFO:     10.1.0.164:55187 - "POST /mcp HTTP/1.1" 200 OK
14:27:01 - INFO - [RESOLVER] Resolved agent_type 'tester' to agent_id '1803f5a4-9193-42e6-b1e8-d953783ef78f'
14:27:01 - INFO - Sent direct message None from orchestrator to ['tester']
14:27:01 - INFO - [WEBSOCKET DEBUG] websocket_manager is AVAILABLE for message None
14:27:01 - INFO - [WEBSOCKET DEBUG] Calling broadcast_message_sent for message None
14:27:01 - INFO - [WEBSOCKET DEBUG] Direct message to: ['1803f5a4-9193-42e6-b1e8-d953783ef78f']
14:27:01 - INFO - 2026-01-02T19:27:01.429754Z [info     ] WebSocket broadcast to tenant completed: 1 sent, 0 failed [api.websocket] extra={'tenant_key': '***REMOVED***', 'event_type': 'message:sent', 'sent_count': 1, 'failed_count': 0, 'total_clients': 1, 'exclude_client': None}
14:27:01 - INFO - [WEBSOCKET DEBUG] Successfully broadcast message_sent None
14:27:01 - INFO - 2026-01-02T19:27:01.429754Z [info     ] WebSocket broadcast to tenant completed: 1 sent, 0 failed [api.websocket] extra={'tenant_key': '***REMOVED***', 'event_type': 'message:received', 'sent_count': 1, 'failed_count': 0, 'total_clients': 1, 'exclude_client': None}
14:27:01 - INFO - [WEBSOCKET DEBUG] Successfully broadcast message_received to 1 recipient(s)
14:27:01 - INFO - [PERSISTENCE] Added outbound message to orchestrator JSONB column (flagged modified)
14:27:01 - INFO - [PERSISTENCE] Added inbound message to tester (1803f5a4-9193-42e6-b1e8-d953783ef78f) JSONB column (flagged modified)
14:27:01 - INFO - [PERSISTENCE] Committed message None to database
14:27:01 - INFO - [PERSISTENCE] Saved message None to agent JSONB columns
14:27:01 - INFO - Tool executed successfully: send_message (session: fb17b869-188d-4d58-b70e-90eefe1666e6)
INFO:     10.1.0.164:55187 - "POST /mcp HTTP/1.1" 200 OK
14:27:05 - INFO - [RESOLVER] Resolved agent_type 'reviewer' to agent_id 'dbc551b2-9e95-469c-84e9-f9ec80b1e9db'
14:27:05 - INFO - Sent direct message None from orchestrator to ['reviewer']
14:27:05 - INFO - [WEBSOCKET DEBUG] websocket_manager is AVAILABLE for message None
14:27:05 - INFO - [WEBSOCKET DEBUG] Calling broadcast_message_sent for message None
14:27:05 - INFO - [WEBSOCKET DEBUG] Direct message to: ['dbc551b2-9e95-469c-84e9-f9ec80b1e9db']
14:27:05 - INFO - 2026-01-02T19:27:05.125355Z [info     ] WebSocket broadcast to tenant completed: 1 sent, 0 failed [api.websocket] extra={'tenant_key': '***REMOVED***', 'event_type': 'message:sent', 'sent_count': 1, 'failed_count': 0, 'total_clients': 1, 'exclude_client': None}
14:27:05 - INFO - [WEBSOCKET DEBUG] Successfully broadcast message_sent None
14:27:05 - INFO - 2026-01-02T19:27:05.125355Z [info     ] WebSocket broadcast to tenant completed: 1 sent, 0 failed [api.websocket] extra={'tenant_key': '***REMOVED***', 'event_type': 'message:received', 'sent_count': 1, 'failed_count': 0, 'total_clients': 1, 'exclude_client': None}
14:27:05 - INFO - [WEBSOCKET DEBUG] Successfully broadcast message_received to 1 recipient(s)
14:27:05 - INFO - [PERSISTENCE] Added outbound message to orchestrator JSONB column (flagged modified)
14:27:05 - INFO - [PERSISTENCE] Added inbound message to reviewer (dbc551b2-9e95-469c-84e9-f9ec80b1e9db) JSONB column (flagged modified)
14:27:05 - INFO - [PERSISTENCE] Committed message None to database
14:27:05 - INFO - [PERSISTENCE] Saved message None to agent JSONB columns
14:27:05 - INFO - Tool executed successfully: send_message (session: fb17b869-188d-4d58-b70e-90eefe1666e6)
INFO:     10.1.0.164:55187 - "POST /mcp HTTP/1.1" 200 OK
14:27:40 - INFO - 2026-01-02T19:27:40.400206Z [info     ] WebSocket disconnected: client_1767381850147_8j6f4bna7 [api.websocket]
14:27:40 - INFO - WebSocket disconnected: client_1767381850147_8j6f4bna7
INFO:     connection closed
14:27:40 - INFO - 2026-01-02T19:27:40.508190Z [info     ] auth_request_received          [api.middleware.auth] has_authorization=False has_cookie=True ip_address=10.1.0.164 method=GET path=/api/v1/products/refresh-active
14:27:40 - INFO - [Network Auth] Found JWT token (length: 324)
14:27:40 - INFO - [Network Auth] JWT validation result: True
INFO:     127.0.0.1:62143 - "GET /api/v1/config/frontend HTTP/1.1" 200 OK
INFO:     10.1.0.164:62142 - "GET /api/setup/status HTTP/1.1" 200 OK
14:27:40 - INFO - 2026-01-02T19:27:40.513699Z [info     ] auth_result                    [api.middleware.auth] authenticated=True error=None is_auto_login=False user=patrik
14:27:40 - INFO - [AUTH] get_current_user called - path: /api/v1/products/refresh-active, cookie: True, api_key: False, auth_header: False
14:27:40 - INFO - [AUTH] Attempting JWT cookie authentication
14:27:40 - INFO - [AUTH] JWT valid - user_id: b5f92da5-01b1-4322-a716-1b887876f9ab
INFO:     10.1.0.164:62142 - "GET /api/setup/status HTTP/1.1" 200 OK
14:27:40 - INFO - [AUTH] JWT SUCCESS - User: patrik, Tenant: ***REMOVED***
INFO:     10.1.0.164:49585 - "GET /api/v1/products/refresh-active HTTP/1.1" 200 OK
INFO:     10.1.0.164:62142 - "OPTIONS /api/auth/me HTTP/1.1" 200 OK
INFO:     10.1.0.164:53549 - "OPTIONS /api/auth/me HTTP/1.1" 200 OK
14:27:40 - INFO - [AUTH] get_current_user called - path: /api/auth/me, cookie: True, api_key: False, auth_header: False
14:27:40 - INFO - [AUTH] Attempting JWT cookie authentication
14:27:40 - INFO - [AUTH] JWT valid - user_id: b5f92da5-01b1-4322-a716-1b887876f9ab
14:27:40 - INFO - [AUTH] JWT SUCCESS - User: patrik, Tenant: ***REMOVED***
INFO:     10.1.0.164:49585 - "GET /api/auth/me HTTP/1.1" 200 OK
14:27:40 - INFO - [AUTH] get_current_user called - path: /api/auth/me, cookie: True, api_key: False, auth_header: False
14:27:40 - INFO - [AUTH] Attempting JWT cookie authentication
14:27:40 - INFO - [AUTH] JWT valid - user_id: b5f92da5-01b1-4322-a716-1b887876f9ab
14:27:40 - INFO - [AUTH] JWT SUCCESS - User: patrik, Tenant: ***REMOVED***
INFO:     10.1.0.164:49585 - "GET /api/auth/me HTTP/1.1" 200 OK
F:\GiljoAI_MCP\venv\Lib\site-packages\websockets\legacy\server.py:1178: DeprecationWarning: remove second argument of ws_handler
  warnings.warn("remove second argument of ws_handler", DeprecationWarning)
14:27:40 - INFO - [WS SETUP DEBUG] db=<sqlalchemy.orm.session.AsyncSession object at 0x0000027F9D84AF90>, setup_state={'database_initialized': True}, database_initialized=True
14:27:40 - INFO - WebSocket authenticated via JWT: patrik
INFO:     10.1.0.164:54016 - "WebSocket /ws/client_1767382060544_kk7wl5uop" [accepted]
14:27:40 - INFO - [WS AUTH DEBUG] auth_result keys: ['authenticated', 'user'], user_info keys: ['user_id', 'tenant_key', 'role', 'permissions'], tenant_key=***REMOVED***
14:27:40 - INFO - 2026-01-02T19:27:40.551238Z [info     ] WebSocket connected: client_1767382060544_kk7wl5uop (auth_type: setup) [api.websocket]
14:27:40 - INFO - WebSocket connected: client_1767382060544_kk7wl5uop (context: normal, auth_type: setup)
INFO:     connection open
14:27:40 - INFO - 2026-01-02T19:27:40.557746Z [info     ] auth_request_received          [api.middleware.auth] has_authorization=False has_cookie=True ip_address=127.0.0.1 method=GET path=/api/v1/messages/
14:27:40 - INFO - [Network Auth] Found JWT token (length: 324)
14:27:40 - INFO - [Network Auth] JWT validation result: True
14:27:40 - INFO - 2026-01-02T19:27:40.559748Z [info     ] auth_result                    [api.middleware.auth] authenticated=True error=None is_auto_login=False user=patrik
14:27:40 - INFO - [AUTH] get_current_user called - path: /api/v1/messages/, cookie: True, api_key: False, auth_header: False
14:27:40 - INFO - [AUTH] Attempting JWT cookie authentication
14:27:40 - INFO - [AUTH] JWT valid - user_id: b5f92da5-01b1-4322-a716-1b887876f9ab
14:27:40 - INFO - [AUTH] JWT SUCCESS - User: patrik, Tenant: ***REMOVED***
INFO:     127.0.0.1:63460 - "GET /api/v1/messages/ HTTP/1.1" 200 OK
14:27:40 - INFO - 2026-01-02T19:27:40.567937Z [info     ] auth_request_received          [api.middleware.auth] has_authorization=False has_cookie=True ip_address=127.0.0.1 method=GET path=/api/v1/projects/fb1745ad-1a89-432a-a0ac-9b150739e008
14:27:40 - INFO - [Network Auth] Found JWT token (length: 324)
14:27:40 - INFO - [Network Auth] JWT validation result: True
14:27:40 - INFO - 2026-01-02T19:27:40.569937Z [info     ] auth_result                    [api.middleware.auth] authenticated=True error=None is_auto_login=False user=patrik
14:27:40 - INFO - [AUTH] get_current_user called - path: /api/v1/projects/fb1745ad-1a89-432a-a0ac-9b150739e008, cookie: True, api_key: False, auth_header: False
14:27:40 - INFO - [AUTH] Attempting JWT cookie authentication
14:27:40 - INFO - [AUTH] JWT valid - user_id: b5f92da5-01b1-4322-a716-1b887876f9ab
14:27:40 - INFO - [AUTH] JWT SUCCESS - User: patrik, Tenant: ***REMOVED***
14:27:40 - INFO - Retrieved project This is a test project MCP Claude code Cli with 6 agents
14:27:40 - INFO - Retrieved project fb1745ad-1a89-432a-a0ac-9b150739e008 for tenant ***REMOVED***
INFO:     127.0.0.1:63461 - "GET /api/v1/projects/fb1745ad-1a89-432a-a0ac-9b150739e008 HTTP/1.1" 200 OK
14:27:40 - INFO - 2026-01-02T19:27:40.578227Z [info     ] auth_request_received          [api.middleware.auth] has_authorization=False has_cookie=True ip_address=127.0.0.1 method=GET path=/api/v1/projects/fb1745ad-1a89-432a-a0ac-9b150739e008/orchestrator
14:27:40 - INFO - [Network Auth] Found JWT token (length: 324)
14:27:40 - INFO - [Network Auth] JWT validation result: True
14:27:40 - INFO - 2026-01-02T19:27:40.579229Z [info     ] auth_result                    [api.middleware.auth] authenticated=True error=None is_auto_login=False user=patrik
14:27:40 - INFO - [AUTH] get_current_user called - path: /api/v1/projects/fb1745ad-1a89-432a-a0ac-9b150739e008/orchestrator, cookie: True, api_key: False, auth_header: False
14:27:40 - INFO - [AUTH] Attempting JWT cookie authentication
14:27:40 - INFO - [AUTH] JWT valid - user_id: b5f92da5-01b1-4322-a716-1b887876f9ab
14:27:40 - INFO - [AUTH] JWT SUCCESS - User: patrik, Tenant: ***REMOVED***
14:27:40 - INFO - Retrieved orchestrator execution 7a7f5185-378a-4eb1-a28c-5c40f59f8ad1 (job: 36627720-2d01-4101-a6e9-36311cb109aa) for project fb1745ad-1a89-432a-a0ac-9b150739e008
INFO:     127.0.0.1:63462 - "GET /api/v1/projects/fb1745ad-1a89-432a-a0ac-9b150739e008/orchestrator HTTP/1.1" 200 OK
14:27:40 - INFO - 2026-01-02T19:27:40.586794Z [info     ] auth_request_received          [api.middleware.auth] has_authorization=False has_cookie=True ip_address=127.0.0.1 method=GET path=/api/agent-jobs/
14:27:40 - INFO - [Network Auth] Found JWT token (length: 324)
14:27:40 - INFO - [Network Auth] JWT validation result: True
14:27:40 - INFO - 2026-01-02T19:27:40.588813Z [info     ] auth_result                    [api.middleware.auth] authenticated=True error=None is_auto_login=False user=patrik
14:27:40 - INFO - [AUTH] get_current_user called - path: /api/agent-jobs/, cookie: True, api_key: False, auth_header: False
14:27:40 - INFO - [AUTH] Attempting JWT cookie authentication
14:27:40 - INFO - [AUTH] JWT valid - user_id: b5f92da5-01b1-4322-a716-1b887876f9ab
14:27:40 - INFO - [AUTH] JWT SUCCESS - User: patrik, Tenant: ***REMOVED***
14:27:40 - INFO - [LIST_JOBS DEBUG] Agent reviewer (job=cd6cdbc2-78ae-46eb-add4-5fb960e4d538, agent=dbc551b2-9e95-469c-84e9-f9ec80b1e9db): messages field = [{'id': 'None', 'from': 'orchestrator', 'text': 'STAGING_COMPLETE: Mission created, 5 agents spawned (analyzer, documenter, implementer, tester, reviewer). Ready for /gil_launch to begin implementation phase.', 'status': 'waiting', 'priority': 'normal', 'direction': 'inbound', 'timestamp': '2026-01-02T19:26:30.889369+00:00'}, {'id': 'None', 'from': 'orchestrator', 'text': 'ORCHESTRATOR → REVIEWER: Welcome to the test! Your job_id is cd6cdbc2-78ae-46eb-add4-5fb960e4d538. Please follow your mission protocol and test progress reporting.', 'status': 'waiting', 'priority': 'normal', 'direction': 'inbound', 'timestamp': '2026-01-02T19:27:05.125355+00:00'}] (type: <class 'list'>)
14:27:40 - INFO - [LIST_JOBS DEBUG] Agent tester (job=e5bfd170-5259-4668-87e2-d3c98f7d620a, agent=1803f5a4-9193-42e6-b1e8-d953783ef78f): messages field = [{'id': 'None', 'from': 'orchestrator', 'text': 'STAGING_COMPLETE: Mission created, 5 agents spawned (analyzer, documenter, implementer, tester, reviewer). Ready for /gil_launch to begin implementation phase.', 'status': 'waiting', 'priority': 'normal', 'direction': 'inbound', 'timestamp': '2026-01-02T19:26:30.889369+00:00'}, {'id': 'None', 'from': 'orchestrator', 'text': 'ORCHESTRATOR → TESTER: Welcome to the test! Your job_id is e5bfd170-5259-4668-87e2-d3c98f7d620a. Please follow your mission protocol and validate message reception (individual + broadcast).', 'status': 'waiting', 'priority': 'normal', 'direction': 'inbound', 'timestamp': '2026-01-02T19:27:01.430755+00:00'}] (type: <class 'list'>)
14:27:40 - INFO - [LIST_JOBS DEBUG] Agent implementer (job=8f60b6f1-0e9c-48ab-85a8-1d2817613bee, agent=b5277da2-7ad2-4310-898a-9aa0b183ae66): messages field = [{'id': 'None', 'from': 'orchestrator', 'text': 'STAGING_COMPLETE: Mission created, 5 agents spawned (analyzer, documenter, implementer, tester, reviewer). Ready for /gil_launch to begin implementation phase.', 'status': 'waiting', 'priority': 'normal', 'direction': 'inbound', 'timestamp': '2026-01-02T19:26:30.889369+00:00'}, {'id': 'None', 'from': 'orchestrator', 'text': 'ORCHESTRATOR → IMPLEMENTER: Welcome to the test! Your job_id is 8f60b6f1-0e9c-48ab-85a8-1d2817613bee. Please follow your mission protocol, test the ERROR state, and report your MCP tool experience.', 'status': 'waiting', 'priority': 'normal', 'direction': 'inbound', 'timestamp': '2026-01-02T19:26:57.741674+00:00'}] (type: <class 'list'>)
14:27:40 - INFO - [LIST_JOBS DEBUG] Agent documenter (job=598a17e7-9182-432b-908f-5c8bf9b3de4e, agent=67749963-bb2b-43f4-9954-d41006705aaf): messages field = [{'id': 'None', 'from': 'orchestrator', 'text': 'STAGING_COMPLETE: Mission created, 5 agents spawned (analyzer, documenter, implementer, tester, reviewer). Ready for /gil_launch to begin implementation phase.', 'status': 'waiting', 'priority': 'normal', 'direction': 'inbound', 'timestamp': '2026-01-02T19:26:30.889369+00:00'}, {'id': 'None', 'from': 'orchestrator', 'text': 'ORCHESTRATOR → DOCUMENTER: Welcome to the test! Your job_id is 598a17e7-9182-432b-908f-5c8bf9b3de4e. Please follow your mission protocol and report your MCP tool experience.', 'status': 'waiting', 'priority': 'normal', 'direction': 'inbound', 'timestamp': '2026-01-02T19:26:54.339877+00:00'}] (type: <class 'list'>)
14:27:40 - INFO - [LIST_JOBS DEBUG] Agent analyzer (job=1a567547-7a13-4f56-b92a-8f9ec4de12cd, agent=56cd0d31-7387-4ede-a2f8-b1fb6d3cad79): messages field = [{'id': 'None', 'from': 'orchestrator', 'text': 'STAGING_COMPLETE: Mission created, 5 agents spawned (analyzer, documenter, implementer, tester, reviewer). Ready for /gil_launch to begin implementation phase.', 'status': 'waiting', 'priority': 'normal', 'direction': 'inbound', 'timestamp': '2026-01-02T19:26:30.889369+00:00'}, {'id': 'None', 'from': 'orchestrator', 'text': 'ORCHESTRATOR → ANALYZER: Welcome to the test! Your job_id is 1a567547-7a13-4f56-b92a-8f9ec4de12cd. Please follow your mission protocol and report your MCP tool experience.', 'status': 'waiting', 'priority': 'normal', 'direction': 'inbound', 'timestamp': '2026-01-02T19:26:51.002497+00:00'}] (type: <class 'list'>)
14:27:40 - INFO - [LIST_JOBS DEBUG] Agent orchestrator (job=36627720-2d01-4101-a6e9-36311cb109aa, agent=7a7f5185-378a-4eb1-a28c-5c40f59f8ad1): messages field = [{'id': 'None', 'from': 'orchestrator', 'text': 'STAGING_COMPLETE: Mission created, 5 agents spawned (analyzer, documenter, implementer, tester, reviewer). Ready for /gil_launch to begin implementation phase.', 'status': 'sent', 'priority': 'normal', 'direction': 'outbound', 'timestamp': '2026-01-02T19:26:30.889369+00:00', 'to_agents': ['b5277da2-7ad2-4310-898a-9aa0b183ae66', '1803f5a4-9193-42e6-b1e8-d953783ef78f', 'dbc551b2-9e95-469c-84e9-f9ec80b1e9db', '56cd0d31-7387-4ede-a2f8-b1fb6d3cad79', '67749963-bb2b-43f4-9954-d41006705aaf']}, {'id': 'None', 'from': 'orchestrator', 'text': 'ORCHESTRATOR → ANALYZER: Welcome to the test! Your job_id is 1a567547-7a13-4f56-b92a-8f9ec4de12cd. Please follow your mission protocol and report your MCP tool experience.', 'status': 'sent', 'priority': 'normal', 'direction': 'outbound', 'timestamp': '2026-01-02T19:26:51.002497+00:00', 'to_agents': ['56cd0d31-7387-4ede-a2f8-b1fb6d3cad79']}, {'id': 'None', 'from': 'orchestrator', 'text': 'ORCHESTRATOR → DOCUMENTER: Welcome to the test! Your job_id is 598a17e7-9182-432b-908f-5c8bf9b3de4e. Please follow your mission protocol and report your MCP tool experience.', 'status': 'sent', 'priority': 'normal', 'direction': 'outbound', 'timestamp': '2026-01-02T19:26:54.339877+00:00', 'to_agents': ['67749963-bb2b-43f4-9954-d41006705aaf']}, {'id': 'None', 'from': 'orchestrator', 'text': 'ORCHESTRATOR → IMPLEMENTER: Welcome to the test! Your job_id is 8f60b6f1-0e9c-48ab-85a8-1d2817613bee. Please follow your mission protocol, test the ERROR state, and report your MCP tool experience.', 'status': 'sent', 'priority': 'normal', 'direction': 'outbound', 'timestamp': '2026-01-02T19:26:57.741674+00:00', 'to_agents': ['b5277da2-7ad2-4310-898a-9aa0b183ae66']}, {'id': 'None', 'from': 'orchestrator', 'text': 'ORCHESTRATOR → TESTER: Welcome to the test! Your job_id is e5bfd170-5259-4668-87e2-d3c98f7d620a. Please follow your mission protocol and validate message reception (individual + broadcast).', 'status': 'sent', 'priority': 'normal', 'direction': 'outbound', 'timestamp': '2026-01-02T19:27:01.430755+00:00', 'to_agents': ['1803f5a4-9193-42e6-b1e8-d953783ef78f']}, {'id': 'None', 'from': 'orchestrator', 'text': 'ORCHESTRATOR → REVIEWER: Welcome to the test! Your job_id is cd6cdbc2-78ae-46eb-add4-5fb960e4d538. Please follow your mission protocol and test progress reporting.', 'status': 'sent', 'priority': 'normal', 'direction': 'outbound', 'timestamp': '2026-01-02T19:27:05.125355+00:00', 'to_agents': ['dbc551b2-9e95-469c-84e9-f9ec80b1e9db']}] (type: <class 'list'>)
14:27:40 - INFO - Listed 6 jobs (total=6, project=fb1745ad-1a89-432a-a0ac-9b150739e008, status=None)
14:27:40 - INFO - Found 6 jobs for user patrik (total=6, offset=0)
INFO:     127.0.0.1:63463 - "GET /api/agent-jobs/?project_id=fb1745ad-1a89-432a-a0ac-9b150739e008 HTTP/1.1" 200 OK
14:27:40 - INFO - 2026-01-02T19:27:40.611948Z [info     ] auth_request_received          [api.middleware.auth] has_authorization=False has_cookie=True ip_address=127.0.0.1 method=GET path=/api/v1/messages/
14:27:40 - INFO - [Network Auth] Found JWT token (length: 324)
14:27:40 - INFO - [Network Auth] JWT validation result: True
14:27:40 - INFO - 2026-01-02T19:27:40.612945Z [info     ] auth_request_received          [api.middleware.auth] has_authorization=False has_cookie=True ip_address=127.0.0.1 method=GET path=/api/agent-jobs/
14:27:40 - INFO - [Network Auth] Found JWT token (length: 324)
14:27:40 - INFO - [Network Auth] JWT validation result: True
14:27:40 - INFO - 2026-01-02T19:27:40.614949Z [info     ] auth_result                    [api.middleware.auth] authenticated=True error=None is_auto_login=False user=patrik
14:27:40 - INFO - [AUTH] get_current_user called - path: /api/agent-jobs/, cookie: True, api_key: False, auth_header: False
14:27:40 - INFO - [AUTH] Attempting JWT cookie authentication
14:27:40 - INFO - [AUTH] JWT valid - user_id: b5f92da5-01b1-4322-a716-1b887876f9ab
14:27:40 - INFO - 2026-01-02T19:27:40.615946Z [info     ] auth_result                    [api.middleware.auth] authenticated=True error=None is_auto_login=False user=patrik
14:27:40 - INFO - [AUTH] get_current_user called - path: /api/v1/messages/, cookie: True, api_key: False, auth_header: False
14:27:40 - INFO - [AUTH] Attempting JWT cookie authentication
14:27:40 - INFO - [AUTH] JWT valid - user_id: b5f92da5-01b1-4322-a716-1b887876f9ab
14:27:40 - INFO - [AUTH] JWT SUCCESS - User: patrik, Tenant: ***REMOVED***
14:27:40 - INFO - [AUTH] JWT SUCCESS - User: patrik, Tenant: ***REMOVED***
INFO:     127.0.0.1:63464 - "GET /api/v1/messages/?project_id=fb1745ad-1a89-432a-a0ac-9b150739e008 HTTP/1.1" 200 OK
14:27:40 - INFO - [LIST_JOBS DEBUG] Agent reviewer (job=cd6cdbc2-78ae-46eb-add4-5fb960e4d538, agent=dbc551b2-9e95-469c-84e9-f9ec80b1e9db): messages field = [{'id': 'None', 'from': 'orchestrator', 'text': 'STAGING_COMPLETE: Mission created, 5 agents spawned (analyzer, documenter, implementer, tester, reviewer). Ready for /gil_launch to begin implementation phase.', 'status': 'waiting', 'priority': 'normal', 'direction': 'inbound', 'timestamp': '2026-01-02T19:26:30.889369+00:00'}, {'id': 'None', 'from': 'orchestrator', 'text': 'ORCHESTRATOR → REVIEWER: Welcome to the test! Your job_id is cd6cdbc2-78ae-46eb-add4-5fb960e4d538. Please follow your mission protocol and test progress reporting.', 'status': 'waiting', 'priority': 'normal', 'direction': 'inbound', 'timestamp': '2026-01-02T19:27:05.125355+00:00'}] (type: <class 'list'>)
14:27:40 - INFO - [LIST_JOBS DEBUG] Agent tester (job=e5bfd170-5259-4668-87e2-d3c98f7d620a, agent=1803f5a4-9193-42e6-b1e8-d953783ef78f): messages field = [{'id': 'None', 'from': 'orchestrator', 'text': 'STAGING_COMPLETE: Mission created, 5 agents spawned (analyzer, documenter, implementer, tester, reviewer). Ready for /gil_launch to begin implementation phase.', 'status': 'waiting', 'priority': 'normal', 'direction': 'inbound', 'timestamp': '2026-01-02T19:26:30.889369+00:00'}, {'id': 'None', 'from': 'orchestrator', 'text': 'ORCHESTRATOR → TESTER: Welcome to the test! Your job_id is e5bfd170-5259-4668-87e2-d3c98f7d620a. Please follow your mission protocol and validate message reception (individual + broadcast).', 'status': 'waiting', 'priority': 'normal', 'direction': 'inbound', 'timestamp': '2026-01-02T19:27:01.430755+00:00'}] (type: <class 'list'>)
14:27:40 - INFO - [LIST_JOBS DEBUG] Agent implementer (job=8f60b6f1-0e9c-48ab-85a8-1d2817613bee, agent=b5277da2-7ad2-4310-898a-9aa0b183ae66): messages field = [{'id': 'None', 'from': 'orchestrator', 'text': 'STAGING_COMPLETE: Mission created, 5 agents spawned (analyzer, documenter, implementer, tester, reviewer). Ready for /gil_launch to begin implementation phase.', 'status': 'waiting', 'priority': 'normal', 'direction': 'inbound', 'timestamp': '2026-01-02T19:26:30.889369+00:00'}, {'id': 'None', 'from': 'orchestrator', 'text': 'ORCHESTRATOR → IMPLEMENTER: Welcome to the test! Your job_id is 8f60b6f1-0e9c-48ab-85a8-1d2817613bee. Please follow your mission protocol, test the ERROR state, and report your MCP tool experience.', 'status': 'waiting', 'priority': 'normal', 'direction': 'inbound', 'timestamp': '2026-01-02T19:26:57.741674+00:00'}] (type: <class 'list'>)
14:27:40 - INFO - [LIST_JOBS DEBUG] Agent documenter (job=598a17e7-9182-432b-908f-5c8bf9b3de4e, agent=67749963-bb2b-43f4-9954-d41006705aaf): messages field = [{'id': 'None', 'from': 'orchestrator', 'text': 'STAGING_COMPLETE: Mission created, 5 agents spawned (analyzer, documenter, implementer, tester, reviewer). Ready for /gil_launch to begin implementation phase.', 'status': 'waiting', 'priority': 'normal', 'direction': 'inbound', 'timestamp': '2026-01-02T19:26:30.889369+00:00'}, {'id': 'None', 'from': 'orchestrator', 'text': 'ORCHESTRATOR → DOCUMENTER: Welcome to the test! Your job_id is 598a17e7-9182-432b-908f-5c8bf9b3de4e. Please follow your mission protocol and report your MCP tool experience.', 'status': 'waiting', 'priority': 'normal', 'direction': 'inbound', 'timestamp': '2026-01-02T19:26:54.339877+00:00'}] (type: <class 'list'>)
14:27:40 - INFO - [LIST_JOBS DEBUG] Agent analyzer (job=1a567547-7a13-4f56-b92a-8f9ec4de12cd, agent=56cd0d31-7387-4ede-a2f8-b1fb6d3cad79): messages field = [{'id': 'None', 'from': 'orchestrator', 'text': 'STAGING_COMPLETE: Mission created, 5 agents spawned (analyzer, documenter, implementer, tester, reviewer). Ready for /gil_launch to begin implementation phase.', 'status': 'waiting', 'priority': 'normal', 'direction': 'inbound', 'timestamp': '2026-01-02T19:26:30.889369+00:00'}, {'id': 'None', 'from': 'orchestrator', 'text': 'ORCHESTRATOR → ANALYZER: Welcome to the test! Your job_id is 1a567547-7a13-4f56-b92a-8f9ec4de12cd. Please follow your mission protocol and report your MCP tool experience.', 'status': 'waiting', 'priority': 'normal', 'direction': 'inbound', 'timestamp': '2026-01-02T19:26:51.002497+00:00'}] (type: <class 'list'>)
14:27:40 - INFO - [LIST_JOBS DEBUG] Agent orchestrator (job=36627720-2d01-4101-a6e9-36311cb109aa, agent=7a7f5185-378a-4eb1-a28c-5c40f59f8ad1): messages field = [{'id': 'None', 'from': 'orchestrator', 'text': 'STAGING_COMPLETE: Mission created, 5 agents spawned (analyzer, documenter, implementer, tester, reviewer). Ready for /gil_launch to begin implementation phase.', 'status': 'sent', 'priority': 'normal', 'direction': 'outbound', 'timestamp': '2026-01-02T19:26:30.889369+00:00', 'to_agents': ['b5277da2-7ad2-4310-898a-9aa0b183ae66', '1803f5a4-9193-42e6-b1e8-d953783ef78f', 'dbc551b2-9e95-469c-84e9-f9ec80b1e9db', '56cd0d31-7387-4ede-a2f8-b1fb6d3cad79', '67749963-bb2b-43f4-9954-d41006705aaf']}, {'id': 'None', 'from': 'orchestrator', 'text': 'ORCHESTRATOR → ANALYZER: Welcome to the test! Your job_id is 1a567547-7a13-4f56-b92a-8f9ec4de12cd. Please follow your mission protocol and report your MCP tool experience.', 'status': 'sent', 'priority': 'normal', 'direction': 'outbound', 'timestamp': '2026-01-02T19:26:51.002497+00:00', 'to_agents': ['56cd0d31-7387-4ede-a2f8-b1fb6d3cad79']}, {'id': 'None', 'from': 'orchestrator', 'text': 'ORCHESTRATOR → DOCUMENTER: Welcome to the test! Your job_id is 598a17e7-9182-432b-908f-5c8bf9b3de4e. Please follow your mission protocol and report your MCP tool experience.', 'status': 'sent', 'priority': 'normal', 'direction': 'outbound', 'timestamp': '2026-01-02T19:26:54.339877+00:00', 'to_agents': ['67749963-bb2b-43f4-9954-d41006705aaf']}, {'id': 'None', 'from': 'orchestrator', 'text': 'ORCHESTRATOR → IMPLEMENTER: Welcome to the test! Your job_id is 8f60b6f1-0e9c-48ab-85a8-1d2817613bee. Please follow your mission protocol, test the ERROR state, and report your MCP tool experience.', 'status': 'sent', 'priority': 'normal', 'direction': 'outbound', 'timestamp': '2026-01-02T19:26:57.741674+00:00', 'to_agents': ['b5277da2-7ad2-4310-898a-9aa0b183ae66']}, {'id': 'None', 'from': 'orchestrator', 'text': 'ORCHESTRATOR → TESTER: Welcome to the test! Your job_id is e5bfd170-5259-4668-87e2-d3c98f7d620a. Please follow your mission protocol and validate message reception (individual + broadcast).', 'status': 'sent', 'priority': 'normal', 'direction': 'outbound', 'timestamp': '2026-01-02T19:27:01.430755+00:00', 'to_agents': ['1803f5a4-9193-42e6-b1e8-d953783ef78f']}, {'id': 'None', 'from': 'orchestrator', 'text': 'ORCHESTRATOR → REVIEWER: Welcome to the test! Your job_id is cd6cdbc2-78ae-46eb-add4-5fb960e4d538. Please follow your mission protocol and test progress reporting.', 'status': 'sent', 'priority': 'normal', 'direction': 'outbound', 'timestamp': '2026-01-02T19:27:05.125355+00:00', 'to_agents': ['dbc551b2-9e95-469c-84e9-f9ec80b1e9db']}] (type: <class 'list'>)
14:27:40 - INFO - Listed 6 jobs (total=6, project=fb1745ad-1a89-432a-a0ac-9b150739e008, status=None)
14:27:40 - INFO - Found 6 jobs for user patrik (total=6, offset=0)
INFO:     127.0.0.1:63465 - "GET /api/agent-jobs/?project_id=fb1745ad-1a89-432a-a0ac-9b150739e008 HTTP/1.1" 200 OK
14:27:40 - INFO - 2026-01-02T19:27:40.627017Z [info     ] auth_request_received          [api.middleware.auth] has_authorization=False has_cookie=True ip_address=127.0.0.1 method=GET path=/api/agent-jobs/
14:27:40 - INFO - [Network Auth] Found JWT token (length: 324)
14:27:40 - INFO - [Network Auth] JWT validation result: True
14:27:40 - INFO - 2026-01-02T19:27:40.629024Z [info     ] auth_result                    [api.middleware.auth] authenticated=True error=None is_auto_login=False user=patrik
14:27:40 - INFO - [AUTH] get_current_user called - path: /api/agent-jobs/, cookie: True, api_key: False, auth_header: False
14:27:40 - INFO - [AUTH] Attempting JWT cookie authentication
14:27:40 - INFO - [AUTH] JWT valid - user_id: b5f92da5-01b1-4322-a716-1b887876f9ab
14:27:40 - INFO - [AUTH] JWT SUCCESS - User: patrik, Tenant: ***REMOVED***
14:27:40 - INFO - [LIST_JOBS DEBUG] Agent reviewer (job=cd6cdbc2-78ae-46eb-add4-5fb960e4d538, agent=dbc551b2-9e95-469c-84e9-f9ec80b1e9db): messages field = [{'id': 'None', 'from': 'orchestrator', 'text': 'STAGING_COMPLETE: Mission created, 5 agents spawned (analyzer, documenter, implementer, tester, reviewer). Ready for /gil_launch to begin implementation phase.', 'status': 'waiting', 'priority': 'normal', 'direction': 'inbound', 'timestamp': '2026-01-02T19:26:30.889369+00:00'}, {'id': 'None', 'from': 'orchestrator', 'text': 'ORCHESTRATOR → REVIEWER: Welcome to the test! Your job_id is cd6cdbc2-78ae-46eb-add4-5fb960e4d538. Please follow your mission protocol and test progress reporting.', 'status': 'waiting', 'priority': 'normal', 'direction': 'inbound', 'timestamp': '2026-01-02T19:27:05.125355+00:00'}] (type: <class 'list'>)
14:27:40 - INFO - [LIST_JOBS DEBUG] Agent tester (job=e5bfd170-5259-4668-87e2-d3c98f7d620a, agent=1803f5a4-9193-42e6-b1e8-d953783ef78f): messages field = [{'id': 'None', 'from': 'orchestrator', 'text': 'STAGING_COMPLETE: Mission created, 5 agents spawned (analyzer, documenter, implementer, tester, reviewer). Ready for /gil_launch to begin implementation phase.', 'status': 'waiting', 'priority': 'normal', 'direction': 'inbound', 'timestamp': '2026-01-02T19:26:30.889369+00:00'}, {'id': 'None', 'from': 'orchestrator', 'text': 'ORCHESTRATOR → TESTER: Welcome to the test! Your job_id is e5bfd170-5259-4668-87e2-d3c98f7d620a. Please follow your mission protocol and validate message reception (individual + broadcast).', 'status': 'waiting', 'priority': 'normal', 'direction': 'inbound', 'timestamp': '2026-01-02T19:27:01.430755+00:00'}] (type: <class 'list'>)
14:27:40 - INFO - [LIST_JOBS DEBUG] Agent implementer (job=8f60b6f1-0e9c-48ab-85a8-1d2817613bee, agent=b5277da2-7ad2-4310-898a-9aa0b183ae66): messages field = [{'id': 'None', 'from': 'orchestrator', 'text': 'STAGING_COMPLETE: Mission created, 5 agents spawned (analyzer, documenter, implementer, tester, reviewer). Ready for /gil_launch to begin implementation phase.', 'status': 'waiting', 'priority': 'normal', 'direction': 'inbound', 'timestamp': '2026-01-02T19:26:30.889369+00:00'}, {'id': 'None', 'from': 'orchestrator', 'text': 'ORCHESTRATOR → IMPLEMENTER: Welcome to the test! Your job_id is 8f60b6f1-0e9c-48ab-85a8-1d2817613bee. Please follow your mission protocol, test the ERROR state, and report your MCP tool experience.', 'status': 'waiting', 'priority': 'normal', 'direction': 'inbound', 'timestamp': '2026-01-02T19:26:57.741674+00:00'}] (type: <class 'list'>)
14:27:40 - INFO - [LIST_JOBS DEBUG] Agent documenter (job=598a17e7-9182-432b-908f-5c8bf9b3de4e, agent=67749963-bb2b-43f4-9954-d41006705aaf): messages field = [{'id': 'None', 'from': 'orchestrator', 'text': 'STAGING_COMPLETE: Mission created, 5 agents spawned (analyzer, documenter, implementer, tester, reviewer). Ready for /gil_launch to begin implementation phase.', 'status': 'waiting', 'priority': 'normal', 'direction': 'inbound', 'timestamp': '2026-01-02T19:26:30.889369+00:00'}, {'id': 'None', 'from': 'orchestrator', 'text': 'ORCHESTRATOR → DOCUMENTER: Welcome to the test! Your job_id is 598a17e7-9182-432b-908f-5c8bf9b3de4e. Please follow your mission protocol and report your MCP tool experience.', 'status': 'waiting', 'priority': 'normal', 'direction': 'inbound', 'timestamp': '2026-01-02T19:26:54.339877+00:00'}] (type: <class 'list'>)
14:27:40 - INFO - [LIST_JOBS DEBUG] Agent analyzer (job=1a567547-7a13-4f56-b92a-8f9ec4de12cd, agent=56cd0d31-7387-4ede-a2f8-b1fb6d3cad79): messages field = [{'id': 'None', 'from': 'orchestrator', 'text': 'STAGING_COMPLETE: Mission created, 5 agents spawned (analyzer, documenter, implementer, tester, reviewer). Ready for /gil_launch to begin implementation phase.', 'status': 'waiting', 'priority': 'normal', 'direction': 'inbound', 'timestamp': '2026-01-02T19:26:30.889369+00:00'}, {'id': 'None', 'from': 'orchestrator', 'text': 'ORCHESTRATOR → ANALYZER: Welcome to the test! Your job_id is 1a567547-7a13-4f56-b92a-8f9ec4de12cd. Please follow your mission protocol and report your MCP tool experience.', 'status': 'waiting', 'priority': 'normal', 'direction': 'inbound', 'timestamp': '2026-01-02T19:26:51.002497+00:00'}] (type: <class 'list'>)
14:27:40 - INFO - [LIST_JOBS DEBUG] Agent orchestrator (job=36627720-2d01-4101-a6e9-36311cb109aa, agent=7a7f5185-378a-4eb1-a28c-5c40f59f8ad1): messages field = [{'id': 'None', 'from': 'orchestrator', 'text': 'STAGING_COMPLETE: Mission created, 5 agents spawned (analyzer, documenter, implementer, tester, reviewer). Ready for /gil_launch to begin implementation phase.', 'status': 'sent', 'priority': 'normal', 'direction': 'outbound', 'timestamp': '2026-01-02T19:26:30.889369+00:00', 'to_agents': ['b5277da2-7ad2-4310-898a-9aa0b183ae66', '1803f5a4-9193-42e6-b1e8-d953783ef78f', 'dbc551b2-9e95-469c-84e9-f9ec80b1e9db', '56cd0d31-7387-4ede-a2f8-b1fb6d3cad79', '67749963-bb2b-43f4-9954-d41006705aaf']}, {'id': 'None', 'from': 'orchestrator', 'text': 'ORCHESTRATOR → ANALYZER: Welcome to the test! Your job_id is 1a567547-7a13-4f56-b92a-8f9ec4de12cd. Please follow your mission protocol and report your MCP tool experience.', 'status': 'sent', 'priority': 'normal', 'direction': 'outbound', 'timestamp': '2026-01-02T19:26:51.002497+00:00', 'to_agents': ['56cd0d31-7387-4ede-a2f8-b1fb6d3cad79']}, {'id': 'None', 'from': 'orchestrator', 'text': 'ORCHESTRATOR → DOCUMENTER: Welcome to the test! Your job_id is 598a17e7-9182-432b-908f-5c8bf9b3de4e. Please follow your mission protocol and report your MCP tool experience.', 'status': 'sent', 'priority': 'normal', 'direction': 'outbound', 'timestamp': '2026-01-02T19:26:54.339877+00:00', 'to_agents': ['67749963-bb2b-43f4-9954-d41006705aaf']}, {'id': 'None', 'from': 'orchestrator', 'text': 'ORCHESTRATOR → IMPLEMENTER: Welcome to the test! Your job_id is 8f60b6f1-0e9c-48ab-85a8-1d2817613bee. Please follow your mission protocol, test the ERROR state, and report your MCP tool experience.', 'status': 'sent', 'priority': 'normal', 'direction': 'outbound', 'timestamp': '2026-01-02T19:26:57.741674+00:00', 'to_agents': ['b5277da2-7ad2-4310-898a-9aa0b183ae66']}, {'id': 'None', 'from': 'orchestrator', 'text': 'ORCHESTRATOR → TESTER: Welcome to the test! Your job_id is e5bfd170-5259-4668-87e2-d3c98f7d620a. Please follow your mission protocol and validate message reception (individual + broadcast).', 'status': 'sent', 'priority': 'normal', 'direction': 'outbound', 'timestamp': '2026-01-02T19:27:01.430755+00:00', 'to_agents': ['1803f5a4-9193-42e6-b1e8-d953783ef78f']}, {'id': 'None', 'from': 'orchestrator', 'text': 'ORCHESTRATOR → REVIEWER: Welcome to the test! Your job_id is cd6cdbc2-78ae-46eb-add4-5fb960e4d538. Please follow your mission protocol and test progress reporting.', 'status': 'sent', 'priority': 'normal', 'direction': 'outbound', 'timestamp': '2026-01-02T19:27:05.125355+00:00', 'to_agents': ['dbc551b2-9e95-469c-84e9-f9ec80b1e9db']}] (type: <class 'list'>)
14:27:40 - INFO - Listed 6 jobs (total=6, project=fb1745ad-1a89-432a-a0ac-9b150739e008, status=None)
14:27:40 - INFO - Found 6 jobs for user patrik (total=6, offset=0)
INFO:     127.0.0.1:53305 - "GET /api/agent-jobs/?project_id=fb1745ad-1a89-432a-a0ac-9b150739e008 HTTP/1.1" 200 OK
14:28:46 - INFO - Created new MCP session: 77eb57c0-1889-49bb-8219-79d1df124717 (tenant: ***REMOVED***)
INFO:     10.1.0.164:60591 - "POST /mcp HTTP/1.1" 200 OK
14:28:58 - WARNING - [MCP Session] Deduplicated 1 stale sessions for api_key=18314f67-78c6-4989-9722-2a43f76a5027 tenant=***REMOVED***
INFO:     10.1.0.164:60966 - "POST /mcp HTTP/1.1" 200 OK
14:29:04 - INFO - Synced API metrics for 1 tenants.
14:29:04 - WARNING - Unhealthy job detected: 196d756d-023b-4a80-ab67-0dd2ce6e3fa9
14:29:04 - INFO - 2026-01-02T19:29:04.349451Z [info     ] WebSocket broadcast to tenant completed: 1 sent, 0 failed [api.websocket] extra={'tenant_key': '***REMOVED***', 'event_type': 'agent:health_alert', 'sent_count': 1, 'failed_count': 0, 'total_clients': 1, 'exclude_client': None}
14:29:04 - WARNING - 2026-01-02T19:29:04.349451Z [warning  ] broadcast_health_alert         [api.websocket] health_state=critical job_id=196d756d-023b-4a80-ab67-0dd2ce6e3fa9 minutes_since_update=14822.7