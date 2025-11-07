# Handover: 0110 - Dashboard API & MCP Call Metrics

**Date:** 2025-11-06
**From Agent:** Gemini
**To Agent:** Next Session
**Priority:** Medium
**Estimated Complexity:** 2-3 Hours
**Status:** Not Started

---

## 1. Task Summary

This project will add two new real-time metrics to the main Dashboard page:
1.  **Total API Calls**: A counter for all HTTP requests received by the backend server.
2.  **Total MCP Calls**: A counter for API requests specifically handled by the MCP tool endpoints.

These metrics will be displayed in new cards next to the existing "Projects" and "Tasks" cards, providing immediate insight into server activity.

## 2. Context and Background

The dashboard currently provides a high-level overview of project and task counts but lacks real-time operational metrics. Understanding the volume of API and MCP traffic is crucial for monitoring server health, identifying usage patterns, and diagnosing performance issues. This feature provides foundational visibility into the server's workload.

## 3. Technical Details

### Backend (FastAPI)

-   **Files to Modify**:
    -   `api/middleware.py`: A new `APIMetricsMiddleware` will be created here.
    -   `api/app.py`: The new middleware will be registered here, and two in-memory counters will be initialized.
    -   `api/endpoints/statistics.py`: A new endpoint will be added to expose the counter values.

-   **API Changes**:
    -   **New Endpoint**: `GET /api/v1/stats/call-counts`
    -   **Response Body**:
        ```json
        {
          "total_api_calls": 1024,
          "total_mcp_calls": 256
        }
        ```

### Frontend (Vue 3 / Vuetify 3)

-   **Files to Modify**:
    -   `frontend/src/views/Dashboard.vue` (or a similar dashboard view component).
    -   A new service file or an existing one (e.g., `frontend/src/services/statisticsService.js`) to handle the API call.

-   **UI Changes**:
    -   Two new cards will be added to the dashboard, styled identically to the existing "Projects" and "Tasks" cards.
    -   Each card will display a title ("Total API Calls", "Total MCP Calls"), the count, and an appropriate Material Design Icon.

## 4. Implementation Plan

### Phase 1: Backend Implementation

1.  **Initialize Counters**: In `api/app.py`, add two global integer variables, `api_call_count` and `mcp_call_count`, initialized to 0.
2.  **Create Middleware**: In `api/middleware.py`, define a new `async` middleware function `APIMetricsMiddleware`.
    -   It will increment `api_call_count` on every request.
    -   It will check if `request.url.path.startswith('/mcp')` and, if so, also increment `mcp_call_count`.
    -   It will then call `await call_next(request)` to pass the request to the next handler.
3.  **Register Middleware**: In `api/app.py`, add the new middleware to the FastAPI app instance using `app.add_middleware()`.
4.  **Create Statistics Endpoint**: In `api/endpoints/statistics.py`, add a new `GET` endpoint `/call-counts` to the existing router that returns the current values of the two global counters.

### Phase 2: Frontend Implementation

1.  **Create API Service**: Create a function in a new or existing service file to make a `GET` request to `/api/v1/stats/call-counts`.
2.  **Update Dashboard Component**:
    -   In the `<script setup>` section of the dashboard view, import the new service function.
    -   Use Vue's `ref` to create two reactive variables for the counts.
    -   In the `onMounted` lifecycle hook, call the service function to fetch the initial counts. Use a `setInterval` to periodically refresh the counts (e.g., every 5 seconds) to provide a near real-time view.
3.  **Add UI Cards**:
    -   In the `<template>` section, duplicate the `v-col` and `v-card` structure used for the existing "Projects" or "Tasks" cards.
    -   Update the titles, icons (`mdi-api`, `mdi-lan`), and bind the card content to the new reactive count variables.

## 5. Testing Requirements

-   **Backend**:
    -   Manually test the new `GET /api/v1/stats/call-counts` endpoint to ensure it returns the correct counts after making several API and MCP calls.
-   **Frontend**:
    -   Load the Dashboard page and verify the two new cards appear correctly.
    -   Verify the cards display the initial counts fetched from the API.
    -   Verify the counts update automatically every few seconds.

## 6. Dependencies and Blockers

-   None. This is a self-contained feature with no external dependencies or blockers.

## 7. Success Criteria

-   The two new metric cards are present on the Dashboard.
-   The "Total API Calls" card accurately reflects the total number of requests made to the server since the last restart.
-   The "Total MCP Calls" card accurately reflects the total number of requests made to `/mcp/*` endpoints.
-   The implementation has no noticeable negative impact on server performance.

## 8. Rollback Plan

-   **Backend**: The middleware registration in `api/app.py` can be commented out, and the new endpoint in `api/endpoints/statistics.py` can be removed.
-   **Frontend**: The changes to the dashboard view component can be reverted via `git checkout`.

The changes are isolated and can be easily reverted without affecting other application functionality.

---

## 9. Development Log

### Phase 1: Initial Dashboard Metrics (API & MCP Calls)

1.  **Project Documentation**: Created this handover document to outline the project scope, plan, and impact analysis.

2.  **Backend Implementation**:
    *   **`api/app.py`**: Added `api_call_count` and `mcp_call_count` to the `APIState` class and registered the new `APIMetricsMiddleware`.
    *   **`api/middleware.py`**: Created the `APIMetricsMiddleware` to increment the global counters on each request.
    *   **`api/endpoints/statistics.py`**: Added the `GET /api/v1/stats/call-counts` endpoint to expose the new metrics.

3.  **Frontend Implementation (`frontend/src/views/DashboardView.vue`)**:
    *   Located the `DashboardView.vue` component.
    *   Added `apiCallCount` and `mcpCallCount` reactive variables.
    *   Implemented the `fetchCallCounts` function to retrieve the metrics.
    *   Used `setInterval` in the `onMounted` hook to refresh the data every 5 seconds and cleared it in `onUnmounted`.
    *   Added two new `v-card` elements to the template to display the API and MCP call counts.

### Phase 2: Enhanced Tenant-Specific Metrics

Following the initial implementation, the scope was expanded to include more detailed, tenant-specific metrics with a persistent storage mechanism.

1.  **Hybrid Metrics Strategy**: Agreed on a hybrid approach for API/MCP call counts to ensure both real-time accuracy and data persistence. This involves using in-memory counters for live data and a background task to periodically sync data to the database.

2.  **Database Modifications**:
    *   **`src/giljo_mcp/models.py`**: Added a new `ApiMetrics` table model to store daily, tenant-specific call counts.
    *   **Troubleshooting**: Encountered and resolved an Alembic migration failure (`Target database is not up to date`). This was caused by a discrepancy between the SQLAlchemy models and the database schema for the `mcp_agent_jobs` table.
    *   **Model Correction**: Corrected the `job_metadata` column in the `MCPAgentJob` model from `JSON` to `JSONB` to align with the database and support GIN indexes.
    *   **Migration Generation**: Successfully generated and applied the database migration to create the `api_metrics` table.

3.  **Backend Refactoring (Tenant-Aware Metrics)**:
    *   **`api/app.py`**:
        *   Modified `api_call_count` and `mcp_call_count` in `APIState` from integers to dictionaries to hold per-tenant counts.
        *   Implemented the `sync_api_metrics_to_db` background task to run every 5 minutes, which upserts the in-memory counts to the `api_metrics` table and then clears the in-memory counters.
    *   **`api/middleware.py`**:
        *   Updated `APIMetricsMiddleware` to retrieve the `tenant_key` from the request state and increment the count for the specific tenant in the new dictionary structure.
    *   **`api/endpoints/statistics.py`**:
        *   Modified the `GET /call-counts` endpoint to be tenant-aware. It now calculates the total count by summing the persisted value from the `api_metrics` table and the current in-memory value for the requesting tenant.
        *   Updated the `SystemStatsResponse` model to include `total_agents_spawned`, `total_jobs_completed`, and `projects_finished`.
        *   Modified the `get_system_statistics` endpoint to be fully tenant-aware, filtering all its database queries by the user's `tenant_key`.
        *   Added new queries to this endpoint to count total agents spawned and completed jobs for the tenant.

4.  **Frontend Enhancements (`frontend/src/views/DashboardView.vue`)**:
    *   Created a new `systemStats` reactive variable to hold the results from the `/api/v1/stats/system` endpoint.
    *   Updated the `refreshData` function to call this endpoint.
    *   Modified the main `stats` computed property to derive its values from the new `systemStats` object.
    *   Added three new `v-card` elements to the template to display "Agents Spawned", "Jobs Done", and "Projects Finished".
