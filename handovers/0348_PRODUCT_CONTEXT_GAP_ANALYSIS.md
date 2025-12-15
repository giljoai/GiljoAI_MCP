# 0348 – Project Context Gap Analysis (TinyContacts)

## Scope

This document tracks gaps between:
- The **Product card UI** (`/Products`)
- The **Project card / Project Context (Always Critical)** (`/projects`)
and the mission JSON used by `get_orchestrator_instructions` for TinyContacts.

Initial focus is on:
- Product name (product‑level)
- Project path (product/project‑level, depending on DB model)
- Product description (product‑level)
- Project description label (project‑level, Always Critical)

Further fields (core features, tech stack, etc.) can be added in follow‑up passes.

## Current Behaviour (Observed)

- **Product Name**
  - Source: Product card in `/Products` UI.
  - Backend representation: `important.product_core.name = "TinyContacts"`.
  - Status: **Working** – value is present and correctly surfaced into the orchestrator JSON.

- **Project Path**
  - Source: Product card (DB field, expected to be something like `F:\TinyContacts` or a relative equivalent).
  - Backend representation: **Missing** – no `project_path` or similar field appears in the `get_orchestrator_instructions` JSON.
  - Project Context block (Always Critical): does **not** currently show project path.
  - Status: **Not working** – value stored in DB is not flowing through to orchestrator output.

- **Descriptions (Context for Orchestrator)**
  - **Product description (product‑level)**
    - Source: Product card long description field, e.g.:
      - Starts with “Modern contact management application for individuals and small teams. Streamlined CRUD interface…” and includes detailed behaviour and non‑functional requirements.
    - Backend representation:
      - Appears under `important.product_core.description`, but in captured output it is truncated (e.g. `…7076 chars truncated…`).
    - Status: **Partially working** – field exists, but full content is not reliably available to agents.
  - **Project description (project‑level, Always Critical)**
    - Source: Project record from `/projects`, e.g.:
      - “This project is about setting up the proper folder structure and index of all files that needs to be built for this application…”
    - Backend representation:
      - Present as `project_description` at the top level of the JSON and again under `critical.project_description`.
      - Included in `priority_map.critical` and effectively treated as Critical Project Context.
    - UI representation:
      - Currently shown in the user context space under a label that reads **Product Description**, even though the data is project‑scoped.
    - Status: **Working but mislabelled** – semantics are correct in JSON, but the UI label is misleading.

## Expected Behaviour

- **Project Context – Always Critical**
  - Must always include, at minimum:
    - **Product Name** – from product card (`product_core.name`).
    - **Project Path** – from DB field mapped for this product.
    - **Project Description** – full, untruncated text from the project description field (from `/projects`), clearly labelled as **Project Description** in the UI.
  - These values should be:
    - Present in the orchestrator JSON returned by `get_orchestrator_instructions`.
    - Rendered in the UI panel labelled **Project Context – Always Critical** with no truncation that removes important semantics.

## Known Gaps

1. **Project Path Missing from Orchestrator Output**
   - DB contains a project path for TinyContacts (e.g. `F:\\TinyContacts`), but:
     - No corresponding field exists in the JSON output (`project_path` or equivalent).
     - Project Context panel cannot show it, because it is never injected into the mission / project_context block.

2. **Description Truncated in Orchestrator JSON**
   - Long description for TinyContacts is stored in the DB but:
     - The captured JSON shows the description truncated (`…7076 chars truncated…`).
     - Agents may not see key requirements (core features, performance, accessibility, v2/v3 roadmap hints).

3. **Project Context Block Not a First‑Class JSON Object**
   - `field_priorities` includes `project_context: 1 (Critical)`, but:
     - There is no explicit `project_context` object in the `critical`/`important` sections.
     - The Always Critical UI block has to infer content from scattered fields instead of a dedicated structure.

4. **UI Mislabel – Project Description Shown as Product Description**
   - The non‑toggleable project‑level description shown in the user context space:
     - Is sourced from `/projects` and surfaces as `project_description` in JSON.
     - Is currently labelled as **Product Description** in the UI.
   - This mislabel can confuse users about the Product → Project hierarchy and where the text originates.

6. **Architecture Declared as Reference but Data Missing**
   - UI configuration exposes **Architecture – Reference / 3**.
   - JSON output only contains:
     - `priority_map.reference` entry for `architecture`.
     - `field_priorities.architecture = 3`.
   - Expected architecture content from the Product config includes:
     - **Primary Architecture Pattern** – e.g. modular monolith with service layer separation; FastAPI routers + service layer + SQLAlchemy models; WebSockets for real-time; component-based frontend using TanStack Query and React hooks.
     - **Design Patterns and Principles** – Repository, Dependency Injection, Factory, SOLID, Adapter, Strategy, Observer, Singleton, MVC-style separation.
     - **API Style & Communication** – REST + JSON, OpenAPI 3.0, WebSockets (v2.0), multipart/form-data for photo uploads, SSE, HTTP/2, CORS configuration.
     - **Architecture Notes** – local-first (SQLite → PostgreSQL), zero-config defaults, storage abstraction for future S3/GCS, async/await usage, optimistic UI, `pathlib.Path` for all paths, Alembic migrations, `/api/v1/` versioning, caching strategy, security practices.
   - None of this appears as a dedicated `architecture` block or attached `fetch_tool` in the mission JSON; only the priority metadata is present.

7. **Testing Declared as Reference but Data Missing**
   - UI configuration exposes **Testing – Reference / 3** with:
     - A **Quality Standards** field.
     - A **Testing Strategy & Approach** dropdown.
     - A **Coverage target slider**.
     - A **Testing Frameworks & Tools** multi-line field.
   - JSON output only contains:
     - `priority_map.reference` entry for `testing`.
     - `field_priorities.testing = 3`.
   - Expected testing content from the Product config includes, for example:
     - Strategy / approach text (from the dropdown-driven field).
     - Coverage target value (e.g. 80–90%).
     - Tools such as: pytest, pytest-asyncio, pytest-cov, httpx, Faker, Vitest, React Testing Library, Cypress, MSW, c8, Ruff, Black, ESLint, Prettier, mypy, TypeScript compiler, pre-commit hooks.
   - None of this appears as a dedicated `testing` block or via a `fetch_tool`; agents only see that Testing exists as a low-priority reference category.

8. **Vision Documents Optional in UI but Missing in JSON**
   - UI configuration exposes **Vision Documents – Optional / Reference / 3** with an “orchestrator decides” behaviour.
   - JSON output currently shows:
     - `priority_map.important` entry for `vision_documents`.
     - `field_priorities.vision_documents = 2`.
   - Gaps:
     - No dedicated `vision_documents` block is present (no summary, no depth/limit, no `fetch_tool`).
     - Priority/label mismatch between UI (Reference / 3, optional) and JSON (Important / 2).
   - Expected behaviour:
     - A structured `vision_documents` config that tells the agent **how to fetch** vision documents when needed (e.g. `fetch_vision_documents(product_id, depth_config)`), plus an explicit “optional” flag for orchestrator decision-making.

## Proposed Next Steps (High‑Level)

These are design targets for implementation tasks; detailed tickets can be derived later.

- **PC‑1: Add Project Path to Orchestrator JSON**
  - Ensure backend includes a `project_path` (or `project_root`) field in the JSON returned by `get_orchestrator_instructions`, sourced from the product record.
  - Add this field into a dedicated `project_context` object that is tagged as Critical.

- **PC‑2: Preserve Full Description**
  - Remove or increase any truncation limits for the product description in the orchestrator response, or:
    - Provide a clear `summary` + `full_description_fetch_tool` pattern instead of silent truncation.
  - Guarantee that the Project Context panel and agents can access the full description text when needed.

- **PC‑3: First‑Class `project_context` Structure**
  - Introduce a `project_context` block in the mission JSON, e.g.:
    - `project_context: { name, project_path, description, product_id, product_key }`.
  - Mark it as Critical (`_priority_frame`, `field_priorities.project_context = 1`) and have the UI read from it directly.

- **PC‑4: Rename UI Label to “Project Description”**
  - In the user context space backed by `/projects`:
    - Change the label of the non‑toggleable description field from **Product Description** to **Project Description**.
  - Ensure this naming is consistent with:
    - The `/projects` API model.
    - The `project_description` fields in `get_orchestrator_instructions` JSON.
    - The Product → Project hierarchy shown elsewhere in the UI.



## Notes

- Frontend location: `/Products` page, product cards and edit form.
- Backend impact: `get_orchestrator_instructions` response builder and any intermediate DTOs that map product data to mission JSON.
- This document is intentionally narrow in scope; additional gaps (tech stack, core features, vision documents, etc.) should be appended in subsequent 0348‑series updates once verified.

## JSONB Structure Considerations

- PostgreSQL `jsonb` is **not** a limiting factor for these changes.
- We can safely add richer nested objects (e.g. `project_context`, `product_description`, `project_path`) into the stored mission/template JSON.
- The real work is in:
  - Updating the **mission JSON builder** to emit the new structure from existing product/project DB fields.
  - Ensuring all **consumers** of this JSON (orchestrator, MCP layer, UI) tolerate the richer shape and use the new fields instead of inferring from scattered keys.
  - Adjusting **UI bindings** so:
    - “Product Description (Important / 2)” is backed by the product‑level description block.
    - “Project Context (Always Critical)” is backed by a dedicated `project_context` block (project name, path, description).
