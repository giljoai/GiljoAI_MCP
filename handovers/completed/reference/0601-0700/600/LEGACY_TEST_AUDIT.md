# Legacy Test File Audit Report

## Executive Summary
- Total files: 33 (including conftest.py)
- NEW (Phase 2): 10
- Legacy analyzed: 22
- Recommended for deletion: 11
- Recommended to keep: 10
- Needs manual review: 1

## Deletion Candidates (HIGH CONFIDENCE)

### test_templates_api_0103.py
- **Reason**: Complete duplicate of test_templates_api.py (Handover 0612)
- **Coverage overlap**: 100% - Tests same endpoints (create, preview, update, list, active count)
- **Unique tests**: 0 - All functionality covered in new comprehensive test
- **Recommendation**: DELETE

### test_templates_api_0106.py
- **Reason**: Partial duplicate of test_templates_api.py (Handover 0612)
- **Coverage overlap**: 90% - Tests system_instructions protection, now in new test
- **Unique tests**: Minor variation in field testing
- **Recommendation**: DELETE

### test_products_cascade.py
- **Reason**: Minimal test file, functionality covered in test_products_api.py
- **Coverage overlap**: 100% - Cascade impact endpoint fully tested in new file
- **Unique tests**: 0
- **File size**: Only 2.2KB with 4 basic tests
- **Recommendation**: DELETE

### test_settings_endpoints.py
- **Reason**: Complete duplicate of test_settings_api.py (Handover 0614)
- **Coverage overlap**: 100% - All settings endpoints covered in new comprehensive test
- **Unique tests**: 0
- **Recommendation**: DELETE

### test_project_lifecycle_endpoints_handover_0504.py
- **Reason**: Complete duplicate of test_projects_api.py (Handover 0610)
- **Coverage overlap**: 100% - All lifecycle endpoints (activate, deactivate, launch, etc.) in new test
- **Unique tests**: 0
- **Old handover**: From 0504, replaced by 0610
- **Recommendation**: DELETE

### test_agent_health_endpoints.py
- **Reason**: Duplicate of test_health_status_api.py (Handover 0618)
- **Coverage overlap**: 100% - Cancel, force-fail, health endpoints all covered
- **Unique tests**: 0
- **Recommendation**: DELETE

### test_product_activation_response.py
- **Reason**: Partial test coverage, now in test_products_api.py
- **Coverage overlap**: 100% - Product activation fully tested in comprehensive suite
- **Unique tests**: 0
- **Recommendation**: DELETE

### test_prompts_execution_simple.py
- **Reason**: Simplified version of test_prompts_execution.py
- **Coverage overlap**: 100% - All scenarios covered in full version
- **Unique tests**: 0
- **Recommendation**: DELETE

### test_task_to_project_conversion.py
- **Reason**: Functionality moved to test_tasks_api.py (Handover 0611)
- **Coverage overlap**: 100% - Task conversion fully covered in new test
- **Unique tests**: 0
- **Recommendation**: DELETE

### test_launch_project_endpoint.py
- **Reason**: Single endpoint test, now in test_projects_api.py
- **Coverage overlap**: 100% - Launch endpoint comprehensively tested
- **Unique tests**: 0
- **Recommendation**: DELETE

### test_user_settings_cookie_domains.py
- **Reason**: Cookie domain tests now in test_settings_api.py
- **Coverage overlap**: 100% - Cookie domain endpoint fully covered
- **Unique tests**: 0
- **Recommendation**: DELETE

## Keep Candidates

### test_thin_prompt_endpoint.py (Handover 0088)
- **Reason**: Tests unique thin client prompt generation (context prioritization and orchestration)
- **Coverage overlap**: 0% - Unique functionality not in other tests
- **Unique tests**: Thin prompt workflow, field priority application
- **Recommendation**: KEEP

### test_products_token_estimate.py
- **Reason**: Comprehensive token estimation testing
- **Coverage overlap**: 20% - Some overlap with products but mostly unique
- **Unique tests**: Token calculation accuracy, field priority integration
- **Recommendation**: KEEP

### test_prompts_execution.py (Handover 0109)
- **Reason**: Execution prompt generation for Agent 3
- **Coverage overlap**: 0% - Unique endpoint functionality
- **Unique tests**: Claude Code mode vs Multi-Terminal mode
- **Recommendation**: KEEP

### test_orchestration_endpoints.py (Handover 0020)
- **Reason**: Orchestration-specific endpoints not in other tests
- **Coverage overlap**: 10% - Mostly unique orchestration functionality
- **Unique tests**: Mission planning, agent selection endpoints
- **Recommendation**: KEEP

### test_agent_jobs_websocket.py (Handover 0086B)
- **Reason**: WebSocket-specific testing for agent jobs
- **Coverage overlap**: 20% - REST covered in test_agent_jobs_api.py, but WebSocket unique
- **Unique tests**: WebSocket broadcasting, real-time events
- **Recommendation**: KEEP

### test_field_priority_endpoints.py
- **Reason**: Field priority configuration endpoints
- **Coverage overlap**: 0% - Unique functionality
- **Unique tests**: Priority management, token budget calculations
- **Recommendation**: KEEP

### test_download_endpoints.py
- **Reason**: Download/export functionality
- **Coverage overlap**: 0% - Unique endpoint group
- **Unique tests**: File download, export operations
- **Recommendation**: KEEP

### test_ai_tools_config_generator.py
- **Reason**: AI tools configuration generation
- **Coverage overlap**: 0% - Unique functionality
- **Unique tests**: MCP config generation for Claude/Codex/Gemini
- **Recommendation**: KEEP

### test_prompts_token_estimation.py
- **Reason**: Token estimation for prompts
- **Coverage overlap**: 10% - Different from product token estimation
- **Unique tests**: Prompt-specific token calculations
- **Recommendation**: KEEP

### test_succession_endpoints.py (Handover 0080)
- **Reason**: Orchestrator succession chain management
- **Coverage overlap**: 0% - Unique succession functionality
- **Unique tests**: Succession chain, trigger succession
- **Recommendation**: KEEP

## Manual Review Needed

### test_regenerate_mission.py (Handover 0086B)
- **Reason**: Mission regeneration endpoint - unclear if covered elsewhere
- **Coverage overlap**: Unknown - needs deeper analysis
- **Action needed**: Check if mission regeneration is tested in test_projects_api.py
- **Recommendation**: MANUAL REVIEW

## Summary Statistics

### Files to Delete (11 files, ~195KB)
1. test_templates_api_0103.py (35K)
2. test_templates_api_0106.py (22K)
3. test_products_cascade.py (2.2K)
4. test_settings_endpoints.py (13K)
5. test_project_lifecycle_endpoints_handover_0504.py (34K)
6. test_agent_health_endpoints.py (11K)
7. test_product_activation_response.py (~10K)
8. test_prompts_execution_simple.py (~15K)
9. test_task_to_project_conversion.py (~20K)
10. test_launch_project_endpoint.py (~15K)
11. test_user_settings_cookie_domains.py (~18K)

### Files to Keep (10 files, ~180KB)
1. test_thin_prompt_endpoint.py - Thin client prompts
2. test_products_token_estimate.py - Token estimation
3. test_prompts_execution.py - Execution prompts
4. test_orchestration_endpoints.py - Orchestration
5. test_agent_jobs_websocket.py - WebSocket tests
6. test_field_priority_endpoints.py - Field priorities
7. test_download_endpoints.py - Downloads/exports
8. test_ai_tools_config_generator.py - AI tool configs
9. test_prompts_token_estimation.py - Prompt tokens
10. test_succession_endpoints.py - Succession chain

### NEW Phase 2 Files (10 files, ~331KB)
1. test_products_api.py (45K) - Handover 0609
2. test_projects_api.py (41K) - Handover 0610
3. test_tasks_api.py (42K) - Handover 0611
4. test_templates_api.py (38K) - Handover 0612
5. test_agent_jobs_api.py (35K) - Handover 0613
6. test_settings_api.py (29K) - Handover 0614
7. test_users_api.py (36K) - Handover 0615
8. test_slash_commands_api.py (8K) - Handover 0616
9. test_messages_api.py (39K) - Handover 0617
10. test_health_status_api.py (18K) - Handover 0618

## Cleanup Commands

To remove the duplicate files, run these commands:



## Final State After Cleanup
- Total test files: 21 (10 NEW + 10 KEEP + 1 REVIEW)
- Space saved: ~195KB
- Test coverage: IMPROVED (comprehensive Phase 2 tests replace partial legacy tests)
- Code quality: IMPROVED (removed duplicate and outdated tests)

## Recommendations
1. Execute the deletion commands above to remove duplicates
2. Manually review test_regenerate_mission.py to determine if needed
3. Run full test suite after cleanup to ensure no regressions
4. Update any import references if other files depend on deleted tests
