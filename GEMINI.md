# GiljoAI MCP Coding Orchestrator

## Project Overview

This project is a full-stack web application called GiljoAI MCP (Coding Orchestrator). Its purpose is to orchestrate teams of specialized AI agents to overcome the context limitations of large language models. The application consists of a Python backend and a Vue.js-based frontend.

**Backend:**

*   **Framework:** FastAPI
*   **Database:** PostgreSQL with SQLAlchemy for ORM
*   **Authentication:** JWT token-based authentication
*   **Key Libraries:** Pydantic for data validation, Alembic for database migrations.

**Frontend:**

*   **Framework:** Vue 3 with the Composition API
*   **Build Tool:** Vite
*   **UI Library:** Vuetify 3 (Material Design)
*   **State Management:** Pinia
*   **HTTP Client:** Axios
*   **Real-time Updates:** WebSockets (via `socket.io-client`)

**Development & Tooling:**

*   **Linting:** Ruff
*   **Formatting:** Black
*   **Type Checking:** mypy
*   **Testing:** pytest (backend), Vitest (frontend)

## Building and Running

The primary method for building and running the application is through the unified startup script.

**To start the application:**

```bash
python startup.py
```

This single command handles the following:

1.  **Dependency Checks:** Verifies Python, PostgreSQL, pip, and npm are installed.
2.  **Requirement Installation:** Installs all necessary Python packages from `requirements.txt` and frontend packages from `frontend/package.json`.
3.  **Database Connectivity:** Ensures a connection to the PostgreSQL database can be established and runs migrations.
4.  **Service Startup:** Launches the FastAPI backend and the Vite frontend development server.
5.  **Browser Launch:** Opens the application in a web browser.

*   **First-time launch:** The application will open to a setup wizard.
*   **Subsequent launches:** The application will open to the dashboard.

**Access URLs:**

*   **Dashboard:** `http://localhost:7274`
*   **API:** `http://localhost:7272`
*   **API Documentation (Swagger UI):** `http://localhost:7272/docs`

**Startup Options:**

The `startup.py` script accepts several flags to modify its behavior:

*   `--check-only`: Checks dependencies and exits without starting services.
*   `--verbose` or `-v`: Shows the output from the backend and frontend servers in separate console windows (on Windows) or streams them to the current terminal.
*   `--no-browser`: Prevents the script from automatically opening a web browser.
*   `--no-migrations`: Skips the automatic database migration step.

## Development Conventions

The project follows standard Python and Vue.js development conventions.

*   **Code Style:** The project uses `black` for Python code formatting and `prettier` for the frontend. `ruff` is used for Python linting. These are enforced through a pre-commit hook.
*   **Testing:** The project uses `pytest` for backend unit and integration testing. Tests are located in the `tests/` directory. The frontend uses `vitest` for its tests.
*   **Type Hinting:** The project uses `mypy` for static type checking in the backend.
*   **Dependencies:** Python dependencies are managed in `requirements.txt` and defined in `pyproject.toml`. Frontend dependencies are in `frontend/package.json`.