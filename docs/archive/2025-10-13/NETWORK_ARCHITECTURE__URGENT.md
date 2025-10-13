# Network Architecture

This document describes how GiljoAI MCP handles communications, including REST, WebSockets, authentication, CORS, and LAN behavior.

## Endpoints
- REST API
  - `/api/v1/*`: core resources (products, projects, agents, messages, tasks, templates, stats, config)
  - `/api/auth`, `/api/users`: authentication and user management
  - `/api/setup/*`: setup and migration utilities (available in setup mode)
  - `/api/network`: network diagnostics and configuration
- WebSocket
  - `/ws/{client_id}`: authenticated, bidirectional updates (heartbeats, subscribe/unsubscribe to entities)

## Authentication
- JWT bearer tokens for browser/API clients; stored in `Authorization: Bearer <token>`.
- API Key support for trusted integrations (set via `API_KEY` env); key passed via query string for WebSockets.
- Localhost auto‑login available for development/setup; network clients must present JWT/API key.
- Frontend axios interceptor checks `/api/setup/status` on 401 before redirecting to `/login` (prevents premature redirect during setup).

## Tenancy
- All requests carry tenant context via `X-Tenant-Key` header.
- WebSocket subscriptions may validate tenant ownership of entities (e.g., projects) before authorizing.
- `TenantManager` centralizes routing and isolation across modules.

## WebSockets
- Endpoint: `/ws/{client_id}`.
- Credentials extracted from query (`api_key`, `token`); validated before `accept()`.
- `WebSocketManager` keeps connections, runs heartbeat, and authorizes subscriptions to entity updates.
- Unauthorized connections are rejected with close codes and error messages.

## CORS and Origins
- CORS configured with explicit origins from `config.yaml` or environment.
- Safe defaults: `http://127.0.0.1:7274` and `http://localhost:7274`.
- Adapter IP detection augments CORS for LAN access (adds `http://<adapter_ip>:7274` and `:5173` for Vite).
- No wildcard origins; warnings logged if wildcards are present in config.

## Ports and Hosts
- Backend REST binds via Uvicorn; local flow assumes `127.0.0.1:7272` for setup wizard links.
- Frontend served on `7274` (or `5173` in dev) and calls REST at `/api`.
- Docker compose templates expose `backend`, `frontend`, and `postgres` with the same semantics.

## Common Flows
- Fresh install: user hits frontend → request 401 → axios checks `/api/setup/status` → if incomplete, router handles `/setup`.
- Completed setup: 401 triggers redirect to `/login` as expected.
- WebSocket client connects with JWT/API key → subscribes to project/agent updates → receives messages and heartbeats.

## Security Considerations
- Middleware order ensures CORS → setup → security headers → rate limit → auth for safe preflight handling.
- Health checks expose minimal details; database and WebSocket states surfaced as healthy/degraded only.

