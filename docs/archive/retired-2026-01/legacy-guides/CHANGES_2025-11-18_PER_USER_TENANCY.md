# Per-User Tenancy Policy (2025-11-18)

Status: Adopted

Summary
- Each user is now isolated in their own tenant. A unique `tenant_key` is generated on registration, ignoring any provided tenant key.
- Active Product remains “one per tenant” and therefore behaves as per-user under this policy.
- WebSocket events are tenant-scoped; product status changes trigger `product:status:changed` broadcasts to the user’s tenant.
- MCP is HTTP-only. The stdio adapter is deprecated.

API Changes
- `/api/auth/register` now assigns a generated `tenant_key` per user (request value ignored).
- `/api/v1/products/refresh-active` is the authoritative source for the active product.
- WebSocket event type added: `product:status:changed` with payload `{ tenant_key, product_id, is_active }`.

Frontend Changes
- Active product indicator listens for `product:status:changed` and refreshes automatically.
- Active product count uses `is_active` consistently.

Migration Notes
- Existing users/tenants are preserved. New users get per-user tenants going forward.
- Optional: Provide a guided tool to clone baseline configuration into a new tenant per user (scripts/tenant_tools.py).

Testing
- New tests verify per-user tenancy assignment on registration and WS event emission for product status changes.

