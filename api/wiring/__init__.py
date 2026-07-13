# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""api.wiring — focused FastAPI assembly modules extracted from api/app.py.

BE-6042b behavior-preserving split: ``api/app.py`` stays the single assembler
(``create_app`` + module-level ``app``) and retains the lifespan/startup phase
sequence; the stateless wiring groups (middleware, routers, websocket handlers,
route/event handlers, OpenAPI servers) live here as free functions that
``app.py`` imports and re-invokes in the same order, so the route table and
middleware stack resolve identically.

CE-only. No module here imports from any ``saas/`` tree; SaaS endpoint/middleware
registration is reached via the conditional ``GILJO_MODE`` gate inside
``routers`` and ``middleware`` exactly as before.
"""
