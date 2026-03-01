# Core Tests

**Baseline (post-0750b triage):** 167 test files, 1,238 passing, 522 skipped, 0 failed.
This IS the complete test suite. 470+ stale/broken test files were deliberately removed in 0750b.
Do NOT treat the test count as low or attempt to restore deleted tests. Write new tests alongside new features.

Tests listed below must always pass. Failures here block merges.

## Tenant Isolation (SaaS Critical)

- `tests/test_tenant_isolation.py`
- `tests/test_tenant_isolation_demo.py`
- `tests/test_tenant_key_fix.py`
- `tests/test_multi_tenant_comprehensive.py`
- `tests/services/test_tenant_isolation_services.py`
- `tests/services/test_project_tenant_isolation_regression.py`
- `tests/services/test_task_tenant_isolation_regression.py`
- `tests/services/test_message_tenant_isolation_regression.py`
- `tests/services/test_orchestration_tenant_isolation_regression.py`
- `tests/services/test_medium_tenant_isolation_regression.py`
- `tests/integration/test_multi_tenant_isolation.py`
- `tests/integration/test_user_tenant_isolation.py`
- `tests/integration/test_field_priority_tenant_isolation.py`
- `tests/smoke/test_tenant_isolation_smoke.py`

## Service Layer (Business Logic)

- `tests/services/test_auth_service.py`
- `tests/services/test_auth_service_api_key_limits.py`
- `tests/services/test_consolidation_service.py`
- `tests/services/test_message_service_0372_unification.py`
- `tests/services/test_message_service_contract.py`
- `tests/services/test_message_service_counters_0387f.py`
- `tests/services/test_message_service_empty_state.py`
- `tests/services/test_message_service_staging_directive.py`
- `tests/services/test_message_service_websocket_injection.py`
- `tests/services/test_orchestration_service_agent_mission.py`
- `tests/services/test_orchestration_service_cli_rules.py`
- `tests/services/test_orchestration_service_context.py`
- `tests/services/test_orchestration_service_dual_model.py`
- `tests/services/test_orchestration_service_full.py`
- `tests/services/test_orchestration_service_instructions.py`
- `tests/services/test_orchestration_service_phase_labels.py`
- `tests/services/test_orchestration_service_protocol.py`
- `tests/services/test_orchestration_service_safety.py`
- `tests/services/test_orchestration_service_team_awareness.py`
- `tests/services/test_orchestration_service_websocket_emissions.py`
- `tests/services/test_org_service.py`
- `tests/services/test_product_service_exceptions.py`
- `tests/services/test_product_service_memory_read.py`
- `tests/services/test_product_service_project_deactivation.py`
- `tests/services/test_product_service_quality_standards.py`
- `tests/services/test_product_service_session_management.py`
- `tests/services/test_project_service_closeout_data.py`
- `tests/services/test_project_service_exceptions.py`
- `tests/services/test_project_service_memory_delete.py`
- `tests/services/test_project_service_orchestrator_dedup.py`
- `tests/services/test_task_service_enhanced.py`
- `tests/services/test_task_service_exceptions.py`
- `tests/services/test_template_service.py`
- `tests/services/test_user_service.py`
- `tests/unit/test_config_service.py`
- `tests/unit/test_context_service.py`
- `tests/unit/test_frontend_config_service.py`
- `tests/unit/test_message_service.py`
- `tests/unit/test_orchestration_service.py`
- `tests/unit/test_product_service.py`
- `tests/unit/test_project_service.py`
- `tests/unit/test_project_service_deleted_state.py`
- `tests/unit/test_project_service_field_priorities.py`
- `tests/unit/test_task_service.py`
- `tests/unit/test_template_service.py`

## Repository Layer (Data Access)

- `tests/repositories/test_configuration_repository.py`
- `tests/repositories/test_product_memory_repository.py`
- `tests/repositories/test_statistics_repository.py`
- `tests/test_vision_document_repository.py`
- `tests/unit/test_project_closeout_repository.py`
- `tests/unit/test_vision_repository_async.py`

## Auth / Security

- `tests/unit/test_auth_manager_unified.py`
- `tests/unit/test_auth_manager_v3.py`
- `tests/unit/test_auth_models.py`
- `tests/unit/test_auth_middleware.py`
- `tests/unit/test_auth_hardening.py`
- `tests/integration/test_auth.py`
- `tests/integration/test_auth_endpoints.py`
- `tests/integration/test_auth_org_flow.py`
- `tests/services/test_authservice_org_integration.py`
- `tests/api/test_auth_org_endpoints.py`

## Shared Test Infrastructure (DO NOT DELETE)

- `tests/helpers/test_db_helper.py` (54 dependents)
- `tests/helpers/test_factories.py`
- `tests/helpers/async_helpers.py`
- `tests/helpers/mock_servers.py`
- `tests/helpers/websocket_test_utils.py`
- `tests/helpers/tenant_helpers.py`
- `tests/fixtures/base_fixtures.py`
- `tests/fixtures/e2e_closeout_fixtures.py`
- `tests/fixtures/mock_agent_simulator.py`
- `tests/fixtures/orchestrator_simulator.py`
- `tests/fixtures/vision_document_fixtures.py`
- `tests/conftest.py`
- `tests/pytest_postgresql_plugin.py`
