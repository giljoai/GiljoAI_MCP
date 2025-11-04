# Handover 0087: Token Estimation Active Product Link (Completed/Retired)
<!-- Harmonized on 2025-11-04; API doc added: docs/api/projects_endpoints.md → GET /products/active/token-estimate -->

Status: Completed (retired)
Date: 2025-11-02

Summary
- Issue: Backend endpoint for active product token estimation called a wrong helper function, breaking the Context tab’s token estimate in User Settings.
- Fix: Use `_get_nested_value` to extract nested fields from `product.config_data`.

Verification
- Endpoint: `GET /api/v1/products/active/token-estimate` exists and runs the correct helper.
  - File: `api/endpoints/products.py:632`, uses `_get_nested_value` at `api/endpoints/products.py:707`.
- Frontend: UserSettings.vue calls the endpoint via `fetchActiveProductTokenEstimate()` and displays results.

Notes
- Further recommendations from 0087 about user-specific field priority in mission generation are addressed in later handovers (0086A/0086B). User ID propagation exists in the orchestrator and MissionPlanner wrappers.
