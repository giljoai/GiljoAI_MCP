# GiljoAI MCP Coding Orchestrator

## Project Overview

This project is a full-stack web application called GiljoAI MCP (Coding Orchestrator). Its purpose is to orchestrate teams of specialized AI agents to overcome the context limitations of large language models. The application consists of a Python backend and a JavaScript-based frontend.

**Backend:**

*   **Framework:** FastAPI
*   **Database:** PostgreSQL 18 with SQLAlchemy for ORM
*   **Authentication:** JWT token-based authentication
*   **Key Libraries:** Pydantic for data validation, Alembic for database migrations.

**Frontend:**

*   **Framework:** Vue 3 with the Composition API
*   **UI Library:** Vuetify 3 (Material Design 3)
*   **HTTP Client:** Axios
*   **Real-time Updates:** WebSockets

**Development & Tooling:**

*   **Linting:** Ruff
*   **Formatting:** Black
*   **Type Checking:** mypy
*   **Testing:** pytest

## Building and Running

The primary method for building and running the application is through the unified startup script.

**To start the application:**

```bash
python startup.py
```

This single command handles the following:

1.  **Dependency Checks:** Verifies Python, PostgreSQL, pip, and npm are installed.
2.  **Requirement Installation:** Installs all necessary Python packages from `requirements.txt`.
3.  **Database Connectivity:** Ensures a connection to the PostgreSQL database can be established.
4.  **Service Startup:** Launches the FastAPI backend and the Vue.js frontend.
5.  **Browser Launch:** Opens the application in a web browser.

*   **First-time launch:** The application will open to a setup wizard at `http://localhost:7274/setup`.
*   **Subsequent launches:** The application will open to the dashboard.

**Access URLs:**

*   **Dashboard:** `http://localhost:7274`
*   **API:** `http://localhost:7272`
*   **API Documentation (Swagger UI):** `http://localhost:7272/docs`

**Development Mode:**

To run the application in development mode with auto-reloading:

```bash
python startup.py --dev
```

## Development Conventions

The project follows standard Python development conventions.

*   **Code Style:** The project uses `black` for code formatting and `ruff` for linting. These are enforced through a pre-commit hook.
*   **Testing:** The project uses `pytest` for unit and integration testing. Tests are located in the `tests/` directory.
*   **Type Hinting:** The project uses `mypy` for static type checking.
*   **Dependencies:** Python dependencies are managed in `requirements.txt` and defined in `pyproject.toml`. Frontend dependencies are in `package.json`.
