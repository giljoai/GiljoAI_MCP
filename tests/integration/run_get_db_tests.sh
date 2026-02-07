#!/bin/bash
# Integration test runner for get_db() dependency fix validation
# Run this script after tdd-implementor completes the async fix

echo "=========================================="
echo "Testing get_db() Dependency Fix"
echo "=========================================="
echo ""

echo "1. Running integration tests for get_db() endpoints..."
pytest tests/integration/test_get_db_dependency_fix.py -v --tb=short

echo ""
echo "2. Checking for session leaks..."
pytest tests/integration/test_get_db_dependency_fix.py::TestGetDbDependency::test_database_session_cleanup -v

echo ""
echo "3. Testing concurrent access..."
pytest tests/integration/test_get_db_dependency_fix.py::TestGetDbDependency::test_concurrent_database_access -v

echo ""
echo "4. Spot-checking random endpoints for regression..."
pytest tests/integration/test_get_db_dependency_fix.py::TestGetDbDependency::test_regression_random_endpoints -v

echo ""
echo "=========================================="
echo "Test Summary"
echo "=========================================="
pytest tests/integration/test_get_db_dependency_fix.py --tb=no --quiet

echo ""
echo "If all tests pass, the get_db() fix is validated!"
