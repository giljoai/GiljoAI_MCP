*** New Product fields ***
## Tab 1 Basic Info 
# Product Information - Page title
Product Name = field

Project Path (optional) = field
Hint = File system path to your product folder. Required for exporting agents.

Description (Context for Orchestrator) = Field
Hint: This description will be used by the orchestrator for mission generation

Core Features = Field
Hint: Main functionality and capabilities of this product

## Tab 2 Vision Docs
# Vision Documents - Page title
instruction = Upload product requirements, proposals, specifications (.md, .txt files)
Choose filesNo file chosen = field/file select
Hint= Select multiple files (Ctrl/Cmd + Click)

## Tab 3 Tech Stack
# Technology Stack Configuration - page title
Programming Languages = Field
Hint in field: Python 3.11, JavaScript ES2023, TypeScript 5.2
HintList all programming languages used (comma-separated or line-by-line)

Frontend Frameworks & Libraries = field
Hint in field: Vue 3, Vuetify 3, Pinia, Vue Router
Hint = List frontend technologies (frameworks, libraries, tools)

Backend Frameworks & Services = field
Hint in field:FastAPI 0.104, SQLAlchemy 2.0, Alembic, asyncio
Hint = List backend technologies (frameworks, ORMs, services)

Databases & Data Storage = field
Hint in field:PostgreSQL 16, Redis 7, Vector embeddings (pgvector)
Hint = List databases and data storage solutions

Infrastructure & DevOps = field
Docker, Kubernetes, GitHub Actions CI/CD, AWS (EC2, S3, RDS)
Hint = List infrastructure and deployment tools

## Tab 4 Architecture
# Architecture & Design Patterns - page title
Primary Architecture Pattern = field
Hint in field:Modular Monolith with Event-Driven components, CQRS for high-traffic modules
Hint = Describe the overall system architecture approach

Design Patterns & Principles = field
Hint in field:Repository Pattern, Dependency Injection, Factory Pattern, SOLID principles
Hint = List design patterns and architectural principles used

PI Style & Communication = field
Hint in field:REST API (OpenAPI 3.0), WebSocket for real-time updates, GraphQL for complex queries
Hint = Describe API communication patterns and protocols

Architecture Notes = field
Hint = Additional architectural decisions, constraints, or context

## Tab 5 Testing
# Quality Standards & Testing Configuration

Quality Standards = field
Hint in field:e.g., Code review required, 80% coverage, zero critical bugs, all tests passing before merge
Hint = Define your quality expectations for testing and development

TDD (Test-Driven Development) = drop down field
- TDD
- BDD
- MANUAL TESTING
- E2D-First
- Integration-First
- HYBRID APPROACH

Testing Strategy & Approach = field
Hint in field:Choose the primary testing methodology for this product
Hint = Test Coverage Target: 80%

Testing Frameworks & Tools = field
Hint in field:pytest, pytest-asyncio, Playwright, coverage.py
Hint = List testing frameworks and quality assurance tools


## project descriotion is not in product template
this is in the project the user creates

## Tasks are not in product template
there are in their own function and table as tasks

## Agent templates are not in product template
agent templates are in the template manager

