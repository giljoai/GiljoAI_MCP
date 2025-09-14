#!/bin/bash
# test_build.sh - Docker Build Validation Tests
# GiljoAI MCP Orchestrator Deployment Testing

set -e

echo "===================================="
echo "Docker Build Tests - GiljoAI MCP"
echo "===================================="

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test results directory
RESULTS_DIR="./test_results"
mkdir -p "$RESULTS_DIR"
TEST_LOG="$RESULTS_DIR/build_test_$(date +%Y%m%d_%H%M%S).log"

# Test counters
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Logging function
log_test() {
    local test_name=$1
    local status=$2
    local message=$3

    TOTAL_TESTS=$((TOTAL_TESTS + 1))

    if [ "$status" = "PASS" ]; then
        PASSED_TESTS=$((PASSED_TESTS + 1))
        echo -e "${GREEN}✓${NC} $test_name: $message" | tee -a "$TEST_LOG"
    else
        FAILED_TESTS=$((FAILED_TESTS + 1))
        echo -e "${RED}✗${NC} $test_name: $message" | tee -a "$TEST_LOG"
    fi
}

# Check Docker installation
check_docker() {
    echo -e "\n${YELLOW}Checking Docker installation...${NC}"

    if command -v docker &> /dev/null; then
        docker_version=$(docker --version)
        log_test "Docker Check" "PASS" "$docker_version"
    else
        log_test "Docker Check" "FAIL" "Docker not installed"
        exit 1
    fi

    if command -v docker-compose &> /dev/null || docker compose version &> /dev/null 2>&1; then
        log_test "Docker Compose Check" "PASS" "Docker Compose available"
    else
        log_test "Docker Compose Check" "FAIL" "Docker Compose not installed"
        exit 1
    fi
}

# Test Backend Build
test_backend_build() {
    echo -e "\n${YELLOW}Testing Backend Container Build...${NC}"

    # Check Dockerfile exists
    if [ -f "../Dockerfile.backend" ]; then
        log_test "Backend Dockerfile" "PASS" "Dockerfile.backend exists"
    else
        log_test "Backend Dockerfile" "FAIL" "Dockerfile.backend not found"
        return 1
    fi

    # Check .dockerignore
    if [ -f "../.dockerignore" ]; then
        log_test "Docker Ignore" "PASS" ".dockerignore exists"
    else
        log_test "Docker Ignore" "FAIL" ".dockerignore not found"
    fi

    # Build backend image
    echo "Building backend image..."
    if docker build -f ../Dockerfile.backend -t giljoai-backend:test .. > "$RESULTS_DIR/backend_build.log" 2>&1; then
        log_test "Backend Build" "PASS" "Build completed successfully"

        # Check image size
        size=$(docker images giljoai-backend:test --format "{{.Size}}")
        log_test "Backend Size" "INFO" "Image size: $size"

        # Verify multi-stage build
        if grep -q "FROM.*AS.*build" ../Dockerfile.backend; then
            log_test "Multi-stage Build" "PASS" "Multi-stage build detected"
        else
            log_test "Multi-stage Build" "FAIL" "Multi-stage build not implemented"
        fi

    else
        log_test "Backend Build" "FAIL" "Build failed - check $RESULTS_DIR/backend_build.log"
        return 1
    fi
}

# Test Frontend Build
test_frontend_build() {
    echo -e "\n${YELLOW}Testing Frontend Container Build...${NC}"

    # Check Dockerfile exists
    if [ -f "../Dockerfile.frontend" ]; then
        log_test "Frontend Dockerfile" "PASS" "Dockerfile.frontend exists"
    else
        log_test "Frontend Dockerfile" "FAIL" "Dockerfile.frontend not found"
        return 1
    fi

    # Build frontend image
    echo "Building frontend image..."
    if docker build -f ../Dockerfile.frontend -t giljoai-frontend:test .. > "$RESULTS_DIR/frontend_build.log" 2>&1; then
        log_test "Frontend Build" "PASS" "Build completed successfully"

        # Check image size
        size=$(docker images giljoai-frontend:test --format "{{.Size}}")
        log_test "Frontend Size" "INFO" "Image size: $size"

        # Verify nginx stage
        if grep -q "FROM.*nginx" ../Dockerfile.frontend; then
            log_test "Nginx Stage" "PASS" "Nginx production stage found"
        else
            log_test "Nginx Stage" "FAIL" "Nginx stage not found"
        fi

    else
        log_test "Frontend Build" "FAIL" "Build failed - check $RESULTS_DIR/frontend_build.log"
        return 1
    fi
}

# Test Build Performance
test_build_performance() {
    echo -e "\n${YELLOW}Testing Build Performance...${NC}"

    # Test backend rebuild with cache
    echo "Testing backend rebuild with cache..."
    start_time=$(date +%s)

    if docker build -f ../Dockerfile.backend -t giljoai-backend:test .. > /dev/null 2>&1; then
        end_time=$(date +%s)
        duration=$((end_time - start_time))

        if [ $duration -lt 30 ]; then
            log_test "Backend Cache" "PASS" "Rebuild took ${duration}s (< 30s)"
        else
            log_test "Backend Cache" "WARN" "Rebuild took ${duration}s (> 30s)"
        fi
    fi

    # Test frontend rebuild with cache
    echo "Testing frontend rebuild with cache..."
    start_time=$(date +%s)

    if docker build -f ../Dockerfile.frontend -t giljoai-frontend:test .. > /dev/null 2>&1; then
        end_time=$(date +%s)
        duration=$((end_time - start_time))

        if [ $duration -lt 30 ]; then
            log_test "Frontend Cache" "PASS" "Rebuild took ${duration}s (< 30s)"
        else
            log_test "Frontend Cache" "WARN" "Rebuild took ${duration}s (> 30s)"
        fi
    fi
}

# Cleanup test images
cleanup() {
    echo -e "\n${YELLOW}Cleaning up test images...${NC}"
    docker rmi giljoai-backend:test 2>/dev/null || true
    docker rmi giljoai-frontend:test 2>/dev/null || true
    echo "Cleanup complete"
}

# Main execution
main() {
    echo "Starting Docker Build Tests..."
    echo "Test results will be saved to: $TEST_LOG"
    echo ""

    # Change to docker directory
    cd "$(dirname "$0")/.."

    # Run tests
    check_docker
    test_backend_build
    test_frontend_build
    test_build_performance

    # Summary
    echo -e "\n===================================="
    echo "Test Summary"
    echo "===================================="
    echo -e "Total Tests: $TOTAL_TESTS"
    echo -e "${GREEN}Passed: $PASSED_TESTS${NC}"
    echo -e "${RED}Failed: $FAILED_TESTS${NC}"

    if [ $FAILED_TESTS -eq 0 ]; then
        echo -e "\n${GREEN}All build tests passed!${NC}"
        cleanup
        exit 0
    else
        echo -e "\n${RED}Some tests failed. Please review the logs.${NC}"
        cleanup
        exit 1
    fi
}

# Run main function
main "$@"