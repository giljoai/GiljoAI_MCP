# Frontend Feature Catalogue

**Handover**: 0330
**Date**: 2025-12-05
**Author**: Documentation Manager Agent
**Status**: Complete

## Purpose

Comprehensive catalogue documenting all 21 frontend feature areas in the GiljoAI MCP Vue 3 + Vuetify dashboard. Each feature is documented with purpose, key files, component dependencies, store dependencies, API endpoints, and complexity assessment.

---

## Table of Contents

1. [Authentication UI](#1-authentication-ui)
2. [Dashboard/Home](#2-dashboardhome)
3. [Product Management UI](#3-product-management-ui)
4. [Project Management UI](#4-project-management-ui)
5. [Agent Status Board](#5-agent-status-board)
6. [Task Management UI](#6-task-management-ui)
7. [Message Center](#7-message-center)
8. [Agent Flow Visualization](#8-agent-flow-visualization)
9. [Settings/Configuration](#9-settingsconfiguration)
10. [API Key & Integration Management](#10-api-key--integration-management)
11. [Template Management UI](#11-template-management-ui)
12. [Git Integration](#12-git-integration)
13. [User Management Admin](#13-user-management-admin)
14. [Agent Management](#14-agent-management)
15. [Common Components](#15-common-components)
16. [Navigation](#16-navigation)
17. [WebSocket Integration](#17-websocket-integration)
18. [Composables](#18-composables)
19. [Utility Functions](#19-utility-functions)
20. [Stores - Pinia](#20-stores---pinia)
21. [Routing & App Structure](#21-routing--app-structure)

---

## Feature Details

### 1. Authentication UI

**Purpose**: Handles user authentication flows including login, first-time setup, password recovery, and account creation with PIN-based password reset system.

**Key Files**:
- `src/views/Login.vue` - Main login page
- `src/views/CreateAdminAccount.vue` - First admin account creation
- `src/views/FirstLogin.vue` - First-time login with PIN setup
- `src/components/ForgotPasswordPin.vue` - PIN-based password reset
- `src/views/WelcomeView.vue` - Fresh install welcome page

**Components**:
- Login form with username/password validation
- Admin account creation wizard
- 4-digit PIN recovery system
- Password strength requirements

**Store Dependencies**:
- `stores/user.js` - User authentication state

**API Dependencies**:
- `POST /api/auth/login` - User login with JWT cookies
- `POST /api/auth/create-first-admin` - First admin creation
- `POST /api/auth/check-first-login` - Check if user needs PIN setup
- `POST /api/auth/complete-first-login` - Complete first login with PIN
- `POST /api/auth/verify-pin-and-reset-password` - Reset password via PIN
- `GET /api/setup/status` - Check if fresh install

**Complexity**: **Medium**
- JWT authentication via httpOnly cookies
- Multi-step wizards (first login, PIN setup)
- Rate limiting on PIN attempts
- Fresh install detection logic

---

### 2. Dashboard/Home

**Purpose**: Main dashboard displaying system statistics, active projects, agent monitoring, and setup status banners for LAN configuration and database setup.

**Key Files**:
- `src/views/DashboardView.vue` - Main dashboard view
- `src/views/WelcomeView.vue` - Welcome screen for new users
- `src/components/dashboard/AgentMonitoring.vue` - Real-time agent status

**Components**:
- Stats cards (projects, tasks, agents, messages)
- Setup banners (database, LAN configuration)
- Active product display
- Agent monitoring grid

**Store Dependencies**:
- `stores/projects.js` - Project counts
- `stores/tasks.js` - Task statistics
- `stores/agents.js` - Agent metrics
- `stores/messages.js` - Message counts

**API Dependencies**:
- `GET /api/v1/stats/` - Dashboard statistics
- `GET /api/v1/stats/session/` - Session info
- `GET /api/setup/status` - Setup status

**Complexity**: **Medium**
- Real-time statistics aggregation
- Conditional setup banners
- Multi-source data integration

---

### 3. Product Management UI

**Purpose**: Create, edit, and manage products with vision document uploads, activation controls, soft delete recovery, and Git integration configuration.

**Key Files**:
- `src/views/ProductsView.vue` - Product list and grid view
- `src/components/products/ProductForm.vue` - Create/edit product form
- `src/components/products/ProductDetailsDialog.vue` - Product details modal
- `src/components/products/ProductVisionPanel.vue` - Vision document management
- `src/components/products/DeletedProductsRecoveryDialog.vue` - Recover deleted products
- `src/components/products/ProductDeleteDialog.vue` - Delete confirmation with cascade impact

**Components**:
- Product grid with search/filter/sort
- Vision document upload (chunked, <25K tokens per chunk)
- Activation controls (activate/deactivate)
- Soft delete with recovery
- Cascade impact preview

**Store Dependencies**:
- `stores/products.js` - Product CRUD operations

**API Dependencies**:
- `GET /api/v1/products/` - List products
- `POST /api/v1/products/` - Create product
- `PUT /api/v1/products/{id}/` - Update product
- `DELETE /api/v1/products/{id}/` - Soft delete product
- `POST /api/v1/products/{id}/vision` - Upload vision document
- `GET /api/v1/products/{id}/vision` - List vision documents
- `DELETE /api/v1/products/{id}/vision/{docId}` - Delete vision document
- `POST /api/v1/products/{id}/activate` - Activate product
- `POST /api/v1/products/{id}/deactivate` - Deactivate product
- `GET /api/v1/products/deleted` - List deleted products
- `POST /api/v1/products/{id}/restore` - Restore deleted product
- `GET /api/v1/products/{id}/cascade-impact` - Preview cascade impact

**Complexity**: **High**
- Multi-document vision upload with chunking
- Soft delete with cascade impact analysis
- Active product switching (only one active at a time)
- Git integration configuration

---

### 4. Project Management UI

**Purpose**: Manage project lifecycle with tabs for launching orchestrators, monitoring agent jobs, viewing succession timelines, and closeout workflows.

**Key Files**:
- `src/views/ProjectsView.vue` - Project list and management
- `src/components/projects/LaunchTab.vue` - Orchestrator launch interface (Handover 0243b)
- `src/components/projects/JobsTab.vue` - Agent jobs status board (Handover 0243c)
- `src/components/projects/LaunchSuccessorDialog.vue` - Orchestrator succession
- `src/components/projects/SuccessionTimeline.vue` - Succession lineage visualization
- `src/components/projects/AgentDetailsModal.vue` - Agent job details
- `src/components/projects/AgentMissionEditModal.vue` - Edit agent mission (Handover 0244b)

**Components**:
- Project grid with status filters
- Three-panel launch tab (orchestrator card, agent grid, context estimate)
- Agent status table with real-time updates
- Succession timeline with lineage chain
- Mission editing modal

**Store Dependencies**:
- `stores/projects.js` - Project CRUD
- `stores/projectJobs.js` - Agent jobs for projects
- `stores/orchestration.js` - Orchestrator state

**API Dependencies**:
- `GET /api/v1/projects/` - List projects
- `POST /api/v1/projects/` - Create project
- `PATCH /api/v1/projects/{id}` - Update project
- `POST /api/v1/projects/{id}/activate` - Activate project
- `POST /api/v1/projects/{id}/deactivate` - Deactivate project
- `POST /api/v1/projects/{id}/launch` - Launch orchestrator
- `POST /api/v1/projects/{id}/cancel-staging` - Cancel staging (Handover 0108)
- `GET /api/v1/projects/{id}/orchestrator` - Get orchestrator job
- `GET /api/agent-jobs/` - List agent jobs for project
- `POST /api/agent-jobs/{jobId}/trigger-succession` - Trigger succession
- `PATCH /api/agent-jobs/{jobId}/mission` - Update agent mission

**Complexity**: **High**
- Complex multi-tab interface
- Real-time agent job monitoring
- Orchestrator succession workflow
- Context token estimation
- Claude Code CLI toggle for subagent execution

---

### 5. Agent Status Board

**Purpose**: Reusable status board components for displaying agent health, status chips, action buttons, and read/acknowledge indicators (Handover 0243 GUI Redesign series).

**Key Files**:
- `src/components/StatusBoard/StatusChip.vue` - Status badge with health indicators
- `src/components/StatusBoard/ActionIcons.vue` - Agent action buttons (5 actions)
- `src/components/StatusBoard/JobReadAckIndicators.vue` - Read/acknowledged checkmarks
- `src/components/orchestration/AgentTableView.vue` - Reusable status board table

**Components**:
- Status chip with color coding (waiting/working/blocked/complete/failed/cancelled/decommissioned)
- Health indicator overlay with pulse animation
- Staleness detection (warning after N minutes)
- Action buttons: Launch, Copy, Message, Cancel, Hand Over
- Read/acknowledge checkmarks with dynamic state

**Store Dependencies**:
- `stores/agentJobs.js` - Agent job state
- `stores/projectJobs.js` - Project-specific jobs

**API Dependencies**:
- `GET /api/agent-jobs/` - Agent job list
- `POST /api/agent-jobs/{jobId}/terminate` - Cancel agent

**Complexity**: **Medium**
- Props-based component design
- Event emitters for actions
- Staleness monitoring composable
- Dynamic status configuration

---

### 6. Task Management UI

**Purpose**: Manage tasks with conversion to projects, status tracking, task-to-project converter wizard, and conversion history timeline.

**Key Files**:
- `src/views/TasksView.vue` - Task list and kanban board
- `src/components/TaskConverter.vue` - Task-to-project converter wizard
- `src/components/ConversionHistory.vue` - Task conversion timeline

**Components**:
- Task kanban board (todo/in-progress/done)
- Task-to-project conversion wizard
- Conversion history with lineage tracking

**Store Dependencies**:
- `stores/tasks.js` - Task CRUD and status changes

**API Dependencies**:
- `GET /api/v1/tasks/` - List tasks
- `POST /api/v1/tasks/` - Create task
- `PUT /api/v1/tasks/{id}/` - Update task
- `PATCH /api/v1/tasks/{id}/status/` - Change status
- `POST /api/v1/tasks/{id}/convert` - Convert to project
- `GET /api/v1/tasks/summary/` - Task summary stats

**Complexity**: **Medium**
- Kanban board drag-and-drop
- Multi-step conversion wizard
- Task status state machine

---

### 7. Message Center

**Purpose**: Agent-to-agent messaging, broadcast messages, message threads, read/acknowledge tracking, and real-time message counters (Handover 0326 auto-acknowledge).

**Key Files**:
- `src/views/MessagesView.vue` - Message center main view
- `src/components/messages/MessageList.vue` - Virtual scroll message list
- `src/components/messages/MessageItem.vue` - Individual message card
- `src/components/messages/BroadcastPanel.vue` - Broadcast message form
- `src/components/messages/MessageModal.vue` - Message detail modal
- `src/components/projects/MessageInput.vue` - Message compose input
- `src/components/projects/MessageStream.vue` - Real-time message stream

**Components**:
- Virtual scroll for message list (performance optimization)
- Message item with read/acknowledged badges
- Broadcast panel with priority selection
- Message filtering (inbox/sent/broadcast)
- Auto-acknowledge on receive (Handover 0326)

**Store Dependencies**:
- `stores/messages.js` - Message CRUD and counters

**API Dependencies**:
- `GET /api/v1/messages/` - List messages with filters
- `POST /api/v1/messages/send` - Send unified message (Handover 0299)
- `POST /api/v1/messages/broadcast` - Broadcast to all agents
- `POST /api/agent-jobs/{jobId}/messages` - Send to specific agent

**Complexity**: **Medium**
- Virtual scrolling for performance
- Real-time WebSocket updates
- Auto-acknowledge logic
- Message threading

---

### 8. Agent Flow Visualization

**Purpose**: Interactive agent workflow visualization with mission dashboard, node relationships, artifact timeline, and zoom/pan controls.

**Key Files**:
- `src/components/agent-flow/FlowCanvas.vue` - Main canvas with zoom/pan controls
- `src/components/agent-flow/AgentNode.vue` - Agent node component
- `src/components/agent-flow/MissionDashboard.vue` - Mission progress dashboard
- `src/components/agent-flow/ArtifactTimeline.vue` - Artifact creation timeline
- `src/components/agent-flow/ThreadView.vue` - Thread-based visualization
- `src/components/agent-flow/panels/NodeDetailPanel.vue` - Node details panel
- `src/components/agent-flow/panels/EdgeDetailPanel.vue` - Edge details panel

**Components**:
- SVG-based flow canvas
- Draggable agent nodes
- Connection edges with labels
- Zoom controls (in/out/reset)
- Animation speed selector (fast/normal/slow)
- Mission progress chips

**Store Dependencies**:
- `stores/agentFlow.js` - Flow state, nodes, edges, zoom level

**API Dependencies**:
- `GET /api/agent-jobs/hierarchy` - Agent hierarchy tree
- `GET /api/agent-jobs/{jobId}` - Agent job details

**Complexity**: **High**
- SVG manipulation and rendering
- Pan/zoom transformation matrix
- Node layout algorithms
- Real-time flow updates

---

### 9. Settings/Configuration

**Purpose**: User settings management with 7 tabs: Setup, Appearance, Notifications, Agents, Context, API Keys, and Integrations. Includes context prioritization and orchestration configuration (Handover 0312-0316).

**Key Files**:
- `src/views/UserSettings.vue` - User settings main view (7 tabs)
- `src/views/SystemSettings.vue` - Admin system settings
- `src/components/settings/tabs/NetworkSettingsTab.vue` - Network configuration
- `src/components/settings/tabs/SecuritySettingsTab.vue` - Security settings
- `src/components/settings/tabs/SystemPromptTab.vue` - Orchestrator system prompt
- `src/components/settings/tabs/AdminIntegrationsTab.vue` - Admin integrations

**Components**:
- Theme toggle (dark/light)
- Context priority configuration (9 fields with Priority 1-4)
- Context depth configuration (light/moderate/heavy)
- Agent template selection
- API key management
- Git/Serena integration toggles

**Store Dependencies**:
- `stores/settings.js` - User settings persistence
- `stores/user.js` - User profile

**API Dependencies**:
- `GET /api/v1/settings/general` - General settings
- `PUT /api/v1/settings/general` - Update general settings
- `GET /api/v1/settings/network` - Network settings
- `PUT /api/v1/settings/network` - Update network settings
- `GET /api/v1/users/me/field-priority` - Context priority config
- `PUT /api/v1/users/me/field-priority` - Update priority config
- `POST /api/v1/users/me/field-priority/reset` - Reset to defaults

**Complexity**: **High**
- 7-tab interface with state persistence
- Context management v2.0 (2-dimensional: Priority × Depth)
- System settings require admin role
- Real-time token budget estimation

---

### 10. API Key & Integration Management

**Purpose**: Manage API keys, configure AI tool integrations (Claude, Codex, Gemini), MCP integration cards, and generate configuration snippets.

**Key Files**:
- `src/views/ApiKeysView.vue` - API key management
- `src/views/McpIntegration.vue` - MCP integration setup
- `src/components/ApiKeyManager.vue` - API key CRUD
- `src/components/ApiKeyWizard.vue` - API key creation wizard
- `src/components/AiToolConfigWizard.vue` - AI tool configuration generator
- `src/components/AIToolSetup.vue` - AI tool setup guide
- `src/components/ClaudeCodeExport.vue` - Export Claude Code config
- `src/components/ToolConfigSnippet.vue` - Config snippet viewer
- `src/components/settings/modals/ClaudeConfigModal.vue` - Claude config modal
- `src/components/settings/modals/CodexConfigModal.vue` - Codex config modal
- `src/components/settings/modals/GeminiConfigModal.vue` - Gemini config modal
- `src/components/settings/integrations/McpIntegrationCard.vue` - MCP card component

**Components**:
- API key list with creation/deletion
- AI tool wizard (Claude/Codex/Gemini)
- Config snippet generator (JSON/YAML)
- MCP server configuration
- Download setup guides

**Store Dependencies**:
- `stores/user.js` - API key storage
- `stores/settings.js` - Integration settings

**API Dependencies**:
- `GET /api/auth/api-keys` - List API keys
- `POST /api/auth/api-keys` - Create API key
- `DELETE /api/auth/api-keys/{keyId}` - Delete API key
- `GET /api/ai-tools/supported` - List supported AI tools
- `GET /api/ai-tools/config-generator/{toolName}` - Generate config
- `GET /api/ai-tools/config-generator/{toolName}/markdown` - Download guide

**Complexity**: **Medium**
- Multi-tool configuration generation
- Clipboard integration
- Config template system

---

### 11. Template Management UI

**Purpose**: Agent template management with CRUD operations, archive/restore, version history, template diff viewer, and active agent counter (8 max recommended).

**Key Files**:
- `src/components/TemplateManager.vue` - Main template manager
- `src/components/TemplateArchive.vue` - Template archive viewer

**Components**:
- Template grid with search/filter by category
- Active agent counter (user limit: 8, system reserved: 1 orchestrator)
- Template editor with preview
- Version history with rollback
- Template diff viewer
- Archive/restore functionality

**Store Dependencies**:
- `stores/agents.js` - Agent template state

**API Dependencies**:
- `GET /api/v1/templates/` - List templates
- `POST /api/v1/templates/` - Create template
- `PUT /api/v1/templates/{id}/` - Update template
- `DELETE /api/v1/templates/{id}/` - Delete/archive template
- `GET /api/v1/templates/{id}/history/` - Version history
- `POST /api/v1/templates/{id}/restore/{archiveId}` - Restore version
- `POST /api/v1/templates/{id}/preview/` - Preview template
- `POST /api/v1/templates/{id}/reset/` - Reset to default
- `GET /api/v1/templates/{id}/diff/` - View diff
- `GET /api/v1/templates/stats/active-count` - Active agent count

**Complexity**: **High**
- Version control and diff viewing
- Template preview system
- Active agent limit enforcement
- Archive management

---

### 12. Git Integration

**Purpose**: GitHub integration for commit tracking, 360 memory management, advanced settings configuration, and commit history timeline.

**Key Files**:
- `src/components/GitCommitHistory.vue` - Commit history timeline
- `src/components/GitAdvancedSettingsDialog.vue` - Advanced Git settings
- `src/components/settings/integrations/GitIntegrationCard.vue` - Git integration card

**Components**:
- Git integration toggle (enable/disable)
- Commit history timeline with filters
- Advanced settings (branch, commit limit)
- GitHub token management
- 360 memory integration

**Store Dependencies**:
- `stores/products.js` - Product Git integration settings

**API Dependencies**:
- `GET /api/git/settings` - Get Git settings
- `POST /api/git/toggle` - Enable/disable Git
- `POST /api/git/settings` - Update Git settings
- `GET /api/v1/products/{id}/git-integration` - Product Git config
- `POST /api/v1/products/{id}/git-integration` - Update product Git config

**Complexity**: **Medium**
- GitHub API integration
- Token management
- Commit filtering and pagination

---

### 13. User Management Admin

**Purpose**: Admin user management with user list, role assignment, password resets, user creation/deletion, and profile management.

**Key Files**:
- `src/views/UsersView.vue` - User management view (admin only)
- `src/views/Users.vue` - User list
- `src/components/UserManager.vue` - User CRUD operations
- `src/components/UserProfileDialog.vue` - User profile editor

**Components**:
- User data table with search/filter
- Role assignment (admin/user)
- Password reset (admin can reset user passwords)
- User creation wizard
- User deletion with confirmation

**Store Dependencies**:
- `stores/user.js` - User state and authentication

**API Dependencies**:
- `GET /api/v1/users/` - List users
- `GET /api/v1/users/{userId}` - Get user details
- `PATCH /api/v1/users/{userId}` - Update user
- `DELETE /api/v1/users/{userId}` - Delete user
- `POST /api/users/{userId}/reset-password` - Reset user password (admin)
- `GET /api/v1/users/me` - Get current user

**Complexity**: **Medium**
- Admin role checks
- User CRUD operations
- Password reset workflow

---

### 14. Agent Management

**Purpose**: Agent metrics, health monitoring, agent card displays, orchestrator cards, and agent grid views.

**Key Files**:
- `src/components/AgentCard.vue` - Agent card component
- `src/components/AgentMetrics.vue` - Agent metrics dashboard
- `src/components/orchestration/OrchestratorCard.vue` - Orchestrator card (Handover 0243b)
- `src/components/orchestration/AgentCardGrid.vue` - Agent grid layout
- `src/components/orchestration/CloseoutModal.vue` - Project closeout modal

**Components**:
- Agent card with status/health
- Metrics dashboard (success rate, avg duration)
- Orchestrator card (context tracking, succession status)
- Agent grid layout with filters

**Store Dependencies**:
- `stores/agents.js` - Agent state
- `stores/agentJobs.js` - Agent job metrics

**API Dependencies**:
- `GET /api/agent-jobs/metrics` - Agent metrics
- `GET /api/agent-jobs/{jobId}/status` - Agent status

**Complexity**: **Medium**
- Real-time metrics calculation
- Health status aggregation
- Grid layout responsiveness

---

### 15. Common Components

**Purpose**: Reusable UI components including toast notifications, alerts, loading states, mascot loader, connection status, and badges.

**Key Files**:
- `src/components/ToastManager.vue` - Toast notification manager
- `src/components/ui/AppAlert.vue` - Alert component
- `src/components/MascotLoader.vue` - Gil mascot loading animation
- `src/components/GilMascot.vue` - Gil mascot component
- `src/components/ConnectionStatus.vue` - WebSocket connection status
- `src/components/StatusBadge.vue` - Status badge component
- `src/components/ActiveProductDisplay.vue` - Active product indicator
- `src/components/projects/ChatHeadBadge.vue` - Chat head badge with unread count

**Components**:
- Toast notifications (success/error/warning/info)
- Alerts with variants (tonal/outlined/flat)
- Gil mascot loader (animated SVG)
- Connection status indicator (online/offline/reconnecting)
- Status badges with color coding

**Store Dependencies**:
- `stores/websocket.js` - Connection status
- `stores/products.js` - Active product

**API Dependencies**: None (pure UI components)

**Complexity**: **Low**
- Reusable presentational components
- Event-driven architecture
- Minimal state management

---

### 16. Navigation

**Purpose**: Application navigation with app bar, navigation drawer, layouts, and routing guards.

**Key Files**:
- `src/components/navigation/AppBar.vue` - Top app bar
- `src/components/navigation/NavigationDrawer.vue` - Side navigation drawer
- `src/layouts/DefaultLayout.vue` - Default layout wrapper
- `src/layouts/AuthLayout.vue` - Authentication layout
- `src/components/icons/CodexMarkIcon.vue` - Custom icon components

**Components**:
- App bar with user menu, theme toggle, notifications
- Navigation drawer with menu items
- Default layout (app bar + drawer + content)
- Auth layout (centered, no navigation)

**Store Dependencies**:
- `stores/user.js` - User authentication state
- `stores/settings.js` - Theme settings

**API Dependencies**: None (navigation only)

**Complexity**: **Low**
- Layout composition
- Responsive drawer behavior
- Route-based active state

---

### 17. WebSocket Integration

**Purpose**: Real-time WebSocket connection for agent status updates, message notifications, project events, and product events with auto-reconnect.

**Key Files**:
- `src/stores/websocket.js` - WebSocket connection manager
- `src/composables/useWebSocket.js` - WebSocket composable
- `src/components/WebSocketV2Test.vue` - WebSocket test component
- `src/stores/websocketIntegrations.js` - WebSocket event handlers

**Components**:
- WebSocket connection lifecycle management
- Event handlers for 10+ event types
- Auto-reconnect with exponential backoff
- Connection status monitoring

**Store Dependencies**:
- `stores/websocket.js` - Connection state
- All stores (receive WebSocket events)

**API Dependencies**: WebSocket endpoints
- `ws://[host]:[port]/ws/updates` - WebSocket connection
- Event types: `agent:status`, `message:new`, `project:updated`, `product:activated`, etc.

**Complexity**: **High**
- WebSocket lifecycle management
- Event routing to stores
- Reconnection logic
- Tenant-scoped events

---

### 18. Composables

**Purpose**: Reusable Vue 3 composables for common functionality like toast notifications, clipboard operations, auto-save, keyboard shortcuts, and staleness monitoring.

**Key Files**:
- `src/composables/useToast.js` - Toast notification composable
- `src/composables/useClipboard.js` - Clipboard operations
- `src/composables/useAutoSave.js` - Auto-save functionality
- `src/composables/useKeyboardShortcuts.js` - Keyboard shortcut bindings
- `src/composables/useStalenessMonitor.js` - Agent staleness detection
- `src/composables/useWebSocket.js` - WebSocket composable
- `src/composables/useAgentData.js` - Agent data fetching
- `src/composables/useFieldPriority.js` - Field priority configuration
- `src/composables/useFocusTrap.js` - Focus trap for modals

**Composables**:
- `useToast()` - Show toast notifications
- `useClipboard()` - Copy to clipboard with feedback
- `useAutoSave(data, saveFn, delay)` - Auto-save with debounce
- `useKeyboardShortcuts(shortcuts)` - Register keyboard shortcuts
- `useStalenessMonitor(job, threshold)` - Detect stale agents
- `useWebSocket()` - WebSocket connection
- `useAgentData(jobId)` - Fetch agent data
- `useFieldPriority()` - Context priority config

**Store Dependencies**: Varies by composable

**API Dependencies**: Varies by composable

**Complexity**: **Medium**
- Reactive composition API
- Lifecycle management
- Event cleanup on unmount

---

### 19. Utility Functions

**Purpose**: Utility functions for status configuration, action configuration, formatters, constants, path detection, and config templates.

**Key Files**:
- `src/utils/statusConfig.js` - Status/health configuration utilities
- `src/utils/actionConfig.js` - Action availability and configuration
- `src/utils/formatters.js` - Date/time/number formatters
- `src/utils/constants.js` - Application constants
- `src/utils/pathDetection.js` - Path detection utilities
- `src/utils/configTemplates.js` - Configuration templates

**Utilities**:
- `getStatusConfig(status)` - Get status color/icon/label
- `getHealthConfig(health)` - Get health indicator config
- `isJobStale(job, threshold)` - Check if job is stale
- `formatLastActivity(date)` - Format date to relative time
- `getActionConfig(action, job)` - Get action availability
- `formatDate(date, format)` - Format dates
- `formatTokenCount(count)` - Format token counts
- Configuration templates for Claude/Codex/Gemini

**Store Dependencies**: None (pure functions)

**API Dependencies**: None (pure utilities)

**Complexity**: **Low**
- Pure functions
- No side effects
- Centralized configuration

---

### 20. Stores - Pinia

**Purpose**: Pinia state management stores for products, projects, agents, messages, tasks, settings, orchestration, and WebSocket state.

**Key Files**:
- `src/stores/index.js` - Store registry
- `src/stores/user.js` - User authentication state
- `src/stores/products.js` - Product CRUD state
- `src/stores/projects.js` - Project CRUD state
- `src/stores/agents.js` - Agent state (deprecated, use agentJobs)
- `src/stores/agentJobs.js` - Agent job state
- `src/stores/projectJobs.js` - Project-specific agent jobs
- `src/stores/messages.js` - Message state with counters
- `src/stores/tasks.js` - Task state
- `src/stores/settings.js` - User settings state
- `src/stores/orchestration.js` - Orchestrator state
- `src/stores/agentFlow.js` - Agent flow visualization state
- `src/stores/websocket.js` - WebSocket connection state
- `src/stores/websocketIntegrations.js` - WebSocket event handlers
- `src/stores/projectTabs.js` - Project tab state persistence

**Stores**:
- **user**: Authentication, profile, tenant key
- **products**: Active product, product list, vision documents
- **projects**: Project list, active project, lifecycle actions
- **agentJobs**: Agent job CRUD, status updates
- **projectJobs**: Project-scoped agent jobs
- **messages**: Message list, counters, send/broadcast
- **tasks**: Task kanban, status changes
- **settings**: User settings, theme, context config
- **orchestration**: Orchestrator state, context tracking
- **agentFlow**: Flow nodes, edges, zoom, layout
- **websocket**: Connection state, event handlers
- **projectTabs**: Tab state persistence (LaunchTab, JobsTab)

**API Dependencies**: All API endpoints via `src/services/api.js`

**Complexity**: **High**
- Complex state management
- Action/mutation patterns
- WebSocket event integration
- Computed getters with caching

---

### 21. Routing & App Structure

**Purpose**: Vue Router configuration, route guards, App.vue root component, main.js entry point, and layout composition.

**Key Files**:
- `src/router/index.js` - Vue Router configuration
- `src/App.vue` - Root application component
- `src/main.js` - Application entry point
- `src/layouts/DefaultLayout.vue` - Default layout
- `src/layouts/AuthLayout.vue` - Auth layout
- `src/views/NotFoundView.vue` - 404 page
- `src/views/ServerDownView.vue` - Server error page
- `src/views/LaunchRedirectView.vue` - Launch redirect handler

**Components**:
- Vue Router with route guards
- Layout system (default/auth)
- 404 and error pages
- Redirect handlers
- Authentication guards

**Store Dependencies**:
- `stores/user.js` - Authentication state for route guards

**API Dependencies**: None (routing only)

**Complexity**: **Medium**
- Route guard logic (auth checks)
- Layout composition
- Navigation guards
- Redirect handling

---

## Summary Statistics

| Category | Count | Notes |
|----------|-------|-------|
| Total Features | 21 | Complete frontend feature set |
| High Complexity | 7 | Product Management, Project Management, Agent Status Board, Agent Flow, Settings, Template Management, Stores |
| Medium Complexity | 11 | Authentication, Dashboard, Task Management, Message Center, API Keys, Git Integration, User Management, Agent Management, Composables, Routing |
| Low Complexity | 3 | Common Components, Navigation, Utility Functions |
| Total Vue Components | 100+ | Including views, components, layouts |
| Total Pinia Stores | 14 | User, Products, Projects, Agents, AgentJobs, ProjectJobs, Messages, Tasks, Settings, Orchestration, AgentFlow, WebSocket, WebSocketIntegrations, ProjectTabs |
| Total Composables | 9 | useToast, useClipboard, useAutoSave, useKeyboardShortcuts, useStalenessMonitor, useWebSocket, useAgentData, useFieldPriority, useFocusTrap |
| Total Utility Modules | 6 | statusConfig, actionConfig, formatters, constants, pathDetection, configTemplates |

---

## Technology Stack

- **Framework**: Vue 3 (Composition API)
- **UI Library**: Vuetify 3
- **State Management**: Pinia
- **Routing**: Vue Router 4
- **HTTP Client**: Axios (httpOnly JWT cookies)
- **WebSocket**: Native WebSocket with auto-reconnect
- **Build Tool**: Vite
- **Language**: JavaScript (with some TypeScript components)

---

## Key Architectural Patterns

1. **Composition API**: All components use Vue 3 Composition API with `<script setup>`
2. **Pinia Stores**: Centralized state management with action/getter patterns
3. **Composables**: Reusable logic extracted into composables
4. **Props/Events**: Parent-child communication via props down, events up
5. **WebSocket Integration**: Real-time updates via WebSocket events routed to stores
6. **API Service Layer**: Centralized `src/services/api.js` for all HTTP requests
7. **Route Guards**: Authentication and authorization via Vue Router guards
8. **Layout System**: Flexible layout composition (default/auth)
9. **Utility Functions**: Pure functions for configuration and formatting
10. **Component Testing**: E2E tests for critical workflows (Handover 0243 series)

---

## Related Documentation

- **Backend Architecture**: `docs/SERVER_ARCHITECTURE_TECH_STACK.md`
- **Component API Docs**: `docs/components/`
- **User Guides**: `docs/user_guides/`
- **Handovers**: `handovers/completed/` (0243 GUI Redesign, 0246 Orchestrator, etc.)
- **Testing**: `docs/TESTING.md`

---

## Maintenance Notes

- **GUI Redesign (0243)**: StatusBoard components (StatusChip, ActionIcons) are production-ready with 27+ E2E tests
- **Message Auto-Acknowledge (0326)**: Messages auto-acknowledge on receive, removed acknowledge button from UI
- **Context Management v2.0 (0312-0318)**: 2-dimensional context model (Priority × Depth) fully integrated
- **Orchestrator Workflow (0246)**: Thin-client prompts, dynamic agent discovery, 85% token reduction
- **Agent Job Migration (0119)**: Use `agentJobs` API/store, not deprecated `agents` API

---

**Document Status**: Complete
**Last Updated**: 2025-12-05
**Next Review**: When new frontend features are added
