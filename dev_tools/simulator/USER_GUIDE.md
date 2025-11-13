Dev Tools Simulator — Quick User Manual

This simulator helps you rapidly test Products, Projects, Tasks, Jobs, Messaging, and MCP without touching the main UI.

Launch
- Windows: run `dev_tools/simulator/run.bat`
- macOS/Linux: run `bash dev_tools/simulator/run.sh`
- Open `http://localhost:7390`

Tip: If the app fails to start with `ModuleNotFoundError: dev_tools`, always launch via the provided run script so PYTHONPATH is set.

Authenticate
- API Key: Paste your API key in `API Key (X-API-Key)` and click `Use API Key`.
- Login: Enter username/password and click `Login`.

Start/Stop Services
- Start API: Click `Start API` (uses repo Python to run `api/run_api.py`).
- Start FE: Click `Start FE` (serves `frontend/dist` on port 7274).
- Status: Click `Status` to see running PIDs/ports.
- Stop API / Stop FE: Use the respective buttons to stop.

Global
- Generate Dataset: Creates 10 products × 10 projects × 10 tasks with SIM_ names.
- Cleanup Created: Deletes/cancels everything created during this simulator session.
- Purge SIM_*: Best‑effort delete/cancel for any SIM_* entities found.
- Global Log: Shows results of all actions.

Product Tab
1) Create Product
   - Enter a name (or leave empty to auto‑generate) and click `Create Product`.
   - Copy the returned `id` from the Product log JSON.
2) Activate / Deactivate / Delete
   - Paste the Product ID into `Product ID` and click the needed action.
3) Upload Vision
   - Choose a `.md` or `.txt` file and click `Upload Vision`.
   - The response shows chunk counts when successful.

Project Tab
1) Create Project
   - Enter a project name and mission.
   - Optional: paste Product ID to link the project.
   - Click `Create Project` and copy the returned `id`.
2) Cancel / Restore
   - Paste `Project ID`, click `Cancel` or `Restore`.

Task Tab
1) Create Task
   - Enter a task title.
   - Optional: Product ID and/or Project ID to scope it.
   - Click `Create Task` and copy returned `id`.
2) Delete Task
   - Paste `Task ID` and click `Delete Task`.
3) Convert → Project
   - Paste `Task ID` and click `Convert → Project` to create a project from the task.

Jobs Tab
- Orchestrate
  - Paste `Project ID` and click `Orchestrate` to run orchestration.
- Workflow Status
  - Paste `Project ID` and click `Workflow Status` to view progress.

Messaging Tab
1) Send
   - `to_agents`: comma‑separated agent names (e.g., `analyzer,tester`).
   - `Project ID` and message content, then click `Send`.
   - Copy returned message `id` if needed.
2) Acknowledge/Complete
   - Paste `Message ID`, set `Agent name` and `Result` (for complete), then click `Acknowledge` or `Complete`.

MCP Tab
- Initialize: Click `Initialize`.
- Tools List: Click `Tools List` to fetch server tool catalog.

Stop
- Stop FE and Stop API with the header buttons.
- Close the simulator page/tab.

Troubleshooting
- Import error at startup: always launch via the provided run script.
- Port already in use: stop existing services (or restart machine) and start again.
- Auth errors: verify API key validity or the username/password.

