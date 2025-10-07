#!/bin/bash
# Quick test runner for Serena MCP integration tests

set -e

echo "=========================================="
echo "Serena MCP Integration Test Suite"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo -e "${YELLOW}pytest not found. Installing...${NC}"
    pip install pytest pytest-asyncio pytest-cov
fi

# Function to run test suite
run_suite() {
    local name=$1
    local path=$2

    echo -e "${BLUE}Running: ${name}${NC}"
    pytest "${path}" -v --tb=short
    echo ""
}

# Parse command line arguments
case "${1:-all}" in
    api)
        echo "Running API endpoint tests only..."
        run_suite "API Endpoint Tests" "tests/integration/test_setup_serena_api.py"
        ;;

    services)
        echo "Running service integration tests only..."
        run_suite "Service Integration Tests" "tests/integration/test_serena_services_integration.py"
        ;;

    platform)
        echo "Running cross-platform tests only..."
        run_suite "Cross-Platform Tests" "tests/integration/test_serena_cross_platform.py"
        ;;

    recovery)
        echo "Running error recovery tests only..."
        run_suite "Error Recovery Tests" "tests/integration/test_serena_error_recovery.py"
        ;;

    security)
        echo "Running security tests only..."
        run_suite "Security Tests" "tests/integration/test_serena_security.py"
        ;;

    coverage)
        echo "Running all tests with coverage report..."
        pytest tests/integration/test_serena*.py \
            --cov=src/giljo_mcp/services/serena_detector \
            --cov=src/giljo_mcp/services/claude_config_manager \
            --cov=src/giljo_mcp/services/config_service \
            --cov-report=html \
            --cov-report=term-missing \
            -v

        echo -e "${GREEN}Coverage report generated: htmlcov/index.html${NC}"
        ;;

    fast)
        echo "Running fast tests only (no slow tests)..."
        pytest tests/integration/test_serena*.py -m "not slow" -v
        ;;

    all)
        echo "Running complete Serena MCP test suite..."
        echo ""

        run_suite "1. API Endpoint Tests" "tests/integration/test_setup_serena_api.py"
        run_suite "2. Service Integration Tests" "tests/integration/test_serena_services_integration.py"
        run_suite "3. Cross-Platform Tests" "tests/integration/test_serena_cross_platform.py"
        run_suite "4. Error Recovery Tests" "tests/integration/test_serena_error_recovery.py"
        run_suite "5. Security Tests" "tests/integration/test_serena_security.py"

        echo -e "${GREEN}=========================================="
        echo "All Serena MCP tests completed!"
        echo -e "==========================================${NC}"
        ;;

    *)
        echo "Usage: $0 [api|services|platform|recovery|security|coverage|fast|all]"
        echo ""
        echo "Options:"
        echo "  api       - Run API endpoint tests only"
        echo "  services  - Run service integration tests only"
        echo "  platform  - Run cross-platform tests only"
        echo "  recovery  - Run error recovery tests only"
        echo "  security  - Run security tests only"
        echo "  coverage  - Run all tests with coverage report"
        echo "  fast      - Run fast tests only (skip slow tests)"
        echo "  all       - Run complete test suite (default)"
        exit 1
        ;;
esac
