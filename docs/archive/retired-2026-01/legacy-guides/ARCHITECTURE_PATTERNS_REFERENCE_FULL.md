# GiljoAI MCP - Architecture Patterns Reference

**Version**: 3.1+ (Post-Nuclear Reset)  
**Created**: 2025-11-16  
**Purpose**: Comprehensive reference for maintaining architectural harmony across all development  
**Source**: Analysis of handover 013A and codebase patterns

This document captures the established architectural patterns from the GiljoAI MCP codebase (handovers 0500-0601+) to ensure consistency and harmony across all future development work.

---

## Executive Summary

**Key Principle**: Service Layer Architecture with Multi-Tenant Isolation

All development must follow these core patterns:
- **Service Layer Only**: All business logic in `src/giljo_mcp/services/`, endpoints are thin translators
- **Multi-Tenant First**: Every query MUST filter by `tenant_key`
- **Soft Deletes**: User-facing entities use `deleted_at` timestamps
- **JSONB for Flexibility**: Use JSONB for config data, not rigid schemas
- **Real-Time Updates**: WebSocket events via HTTP bridge for cross-process communication
- **Testing Coverage**: >80% coverage with integration + unit tests

---

## Table of Contents

1. [Service Layer Patterns](#1-service-layer-patterns)
2. [Database Patterns](#2-database-patterns)
3. [API Endpoint Patterns](#3-api-endpoint-patterns)
4. [Frontend Patterns](#4-frontend-patterns)
5. [Testing Patterns](#5-testing-patterns)
6. [WebSocket Event Patterns](#6-websocket-event-patterns)
7. [Cross-Cutting Concerns](#7-cross-cutting-concerns)
8. [Common Pitfalls](#8-common-pitfalls)

---
