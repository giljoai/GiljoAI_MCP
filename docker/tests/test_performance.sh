#!/bin/bash
# test_performance.sh - Docker Performance Tests
# GiljoAI MCP Orchestrator Deployment Testing

set -e

echo "===================================="
echo "Docker Performance Tests - GiljoAI MCP"
echo "===================================="

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test results directory
RESULTS_DIR="./test_results"
mkdir -p "$RESULTS_DIR"
TEST_LOG="$RESULTS_DIR/performance_test_$(date +%Y%m%d_%H%M%S).log"

# Test counters
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Performance thresholds
MAX_STARTUP_TIME=5
MAX_DB_STARTUP=2
MAX_BACKEND_STARTUP=3
MAX_FRONTEND_STARTUP=1
MAX_MEMORY_MB=2048
MAX_IMAGE_SIZE_BACKEND_MB=500
MAX_IMAGE_SIZE_FRONTEND_MB=100

# API endpoint
API_BASE="http://localhost:6002"
FRONTEND_BASE="http://localhost:6000"

# Logging function
log_test() {
    local test_name=$1
    local status=$2
    local message=$3

    TOTAL_TESTS=$((TOTAL_TESTS + 1))

    if [ "$status" = "PASS" ]; then
        PASSED_TESTS=$((PASSED_TESTS + 1))
        echo -e "${GREEN}✓${NC} $test_name: $message" | tee -a "$TEST_LOG"
    elif [ "$status" = "WARN" ]; then
        echo -e "${YELLOW}⚠${NC} $test_name: $message" | tee -a "$TEST_LOG"
    else
        FAILED_TESTS=$((FAILED_TESTS + 1))
        echo -e "${RED}✗${NC} $test_name: $message" | tee -a "$TEST_LOG"
    fi
}

# Measure service startup time
measure_startup_time() {
    local service=$1
    local port=$2
    local max_time=$3
    local start_time=$(date +%s)

    while true; do
        if nc -z localhost $port 2>/dev/null; then
            local end_time=$(date +%s)
            local duration=$((end_time - start_time))
            return $duration
        fi

        if [ $(($(date +%s) - start_time)) -gt 30 ]; then
            return 999  # Timeout
        fi

        sleep 0.5
    done
}

# Test startup performance
test_startup_performance() {
    echo -e "\n${YELLOW}Testing Startup Performance...${NC}"

    # Stop stack if running
    echo "Stopping current stack..."
    docker-compose down > /dev/null 2>&1

    # Record start time
    START_TIME=$(date +%s)

    # Start the stack
    echo "Starting Docker stack..."
    docker-compose up -d > /dev/null 2>&1

    # Measure database startup
    echo "Waiting for database..."
    DB_START=$(date +%s)
    while ! docker-compose exec -T postgres pg_isready > /dev/null 2>&1; do
        if [ $(($(date +%s) - DB_START)) -gt 30 ]; then
            break
        fi
        sleep 0.5
    done
    DB_DURATION=$(($(date +%s) - DB_START))

    if [ $DB_DURATION -le $MAX_DB_STARTUP ]; then
        log_test "Database Startup" "PASS" "${DB_DURATION}s (≤ ${MAX_DB_STARTUP}s)"
    else
        log_test "Database Startup" "FAIL" "${DB_DURATION}s (> ${MAX_DB_STARTUP}s)"
    fi

    # Measure backend startup
    echo "Waiting for backend..."
    BACKEND_START=$(date +%s)
    while ! curl -f -s "$API_BASE/health" > /dev/null 2>&1; do
        if [ $(($(date +%s) - BACKEND_START)) -gt 30 ]; then
            break
        fi
        sleep 0.5
    done
    BACKEND_DURATION=$(($(date +%s) - BACKEND_START))

    if [ $BACKEND_DURATION -le $MAX_BACKEND_STARTUP ]; then
        log_test "Backend Startup" "PASS" "${BACKEND_DURATION}s (≤ ${MAX_BACKEND_STARTUP}s)"
    else
        log_test "Backend Startup" "FAIL" "${BACKEND_DURATION}s (> ${MAX_BACKEND_STARTUP}s)"
    fi

    # Measure frontend startup
    echo "Waiting for frontend..."
    FRONTEND_START=$(date +%s)
    while ! curl -f -s "$FRONTEND_BASE" > /dev/null 2>&1; do
        if [ $(($(date +%s) - FRONTEND_START)) -gt 30 ]; then
            break
        fi
        sleep 0.5
    done
    FRONTEND_DURATION=$(($(date +%s) - FRONTEND_START))

    if [ $FRONTEND_DURATION -le $MAX_FRONTEND_STARTUP ]; then
        log_test "Frontend Startup" "PASS" "${FRONTEND_DURATION}s (≤ ${MAX_FRONTEND_STARTUP}s)"
    else
        log_test "Frontend Startup" "FAIL" "${FRONTEND_DURATION}s (> ${MAX_FRONTEND_STARTUP}s)"
    fi

    # Total startup time
    TOTAL_DURATION=$(($(date +%s) - START_TIME))
    if [ $TOTAL_DURATION -le $MAX_STARTUP_TIME ]; then
        log_test "Total Startup Time" "PASS" "${TOTAL_DURATION}s (≤ ${MAX_STARTUP_TIME}s)"
    else
        log_test "Total Startup Time" "FAIL" "${TOTAL_DURATION}s (> ${MAX_STARTUP_TIME}s)"
    fi
}

# Test resource usage
test_resource_usage() {
    echo -e "\n${YELLOW}Testing Resource Usage...${NC}"

    # Get container stats
    docker stats --no-stream --format "table {{.Container}}\t{{.MemUsage}}\t{{.CPUPerc}}" > "$RESULTS_DIR/container_stats.txt"

    # Check memory usage for each container
    for container in postgres backend frontend; do
        # Get memory usage in MB
        MEMORY=$(docker stats --no-stream --format "{{.MemUsage}}" $(docker-compose ps -q $container) | cut -d'/' -f1 | grep -o '[0-9.]*')
        UNIT=$(docker stats --no-stream --format "{{.MemUsage}}" $(docker-compose ps -q $container) | cut -d'/' -f1 | grep -o '[A-Za-z]*')

        # Convert to MB if necessary
        if [ "$UNIT" = "GiB" ]; then
            MEMORY=$(echo "$MEMORY * 1024" | bc)
        elif [ "$UNIT" = "KiB" ]; then
            MEMORY=$(echo "$MEMORY / 1024" | bc)
        fi

        echo "  $container: ${MEMORY}MB" >> "$TEST_LOG"

        # Check if within limits (per container)
        if (( $(echo "$MEMORY < 1024" | bc -l) )); then
            log_test "$container Memory" "PASS" "${MEMORY}MB (< 1GB)"
        else
            log_test "$container Memory" "WARN" "${MEMORY}MB (> 1GB)"
        fi
    done

    # Check CPU usage
    for container in postgres backend frontend; do
        CPU=$(docker stats --no-stream --format "{{.CPUPerc}}" $(docker-compose ps -q $container) | tr -d '%')
        echo "  $container CPU: ${CPU}%" >> "$TEST_LOG"

        if (( $(echo "$CPU < 50" | bc -l) )); then
            log_test "$container CPU" "PASS" "${CPU}% (< 50%)"
        else
            log_test "$container CPU" "WARN" "${CPU}% (> 50%)"
        fi
    done
}

# Test image sizes
test_image_sizes() {
    echo -e "\n${YELLOW}Testing Image Sizes...${NC}"

    # Check backend image size
    BACKEND_SIZE=$(docker images --format "{{.Size}}" giljoai-backend:latest 2>/dev/null || echo "0MB")
    BACKEND_SIZE_MB=$(echo $BACKEND_SIZE | grep -o '[0-9.]*')
    BACKEND_UNIT=$(echo $BACKEND_SIZE | grep -o '[A-Za-z]*')

    if [ "$BACKEND_UNIT" = "GB" ]; then
        BACKEND_SIZE_MB=$(echo "$BACKEND_SIZE_MB * 1024" | bc)
    fi

    if (( $(echo "$BACKEND_SIZE_MB < $MAX_IMAGE_SIZE_BACKEND_MB" | bc -l) )); then
        log_test "Backend Image Size" "PASS" "${BACKEND_SIZE} (< ${MAX_IMAGE_SIZE_BACKEND_MB}MB)"
    else
        log_test "Backend Image Size" "FAIL" "${BACKEND_SIZE} (> ${MAX_IMAGE_SIZE_BACKEND_MB}MB)"
    fi

    # Check frontend image size
    FRONTEND_SIZE=$(docker images --format "{{.Size}}" giljoai-frontend:latest 2>/dev/null || echo "0MB")
    FRONTEND_SIZE_MB=$(echo $FRONTEND_SIZE | grep -o '[0-9.]*')
    FRONTEND_UNIT=$(echo $FRONTEND_SIZE | grep -o '[A-Za-z]*')

    if [ "$FRONTEND_UNIT" = "GB" ]; then
        FRONTEND_SIZE_MB=$(echo "$FRONTEND_SIZE_MB * 1024" | bc)
    fi

    if (( $(echo "$FRONTEND_SIZE_MB < $MAX_IMAGE_SIZE_FRONTEND_MB" | bc -l) )); then
        log_test "Frontend Image Size" "PASS" "${FRONTEND_SIZE} (< ${MAX_IMAGE_SIZE_FRONTEND_MB}MB)"
    else
        log_test "Frontend Image Size" "FAIL" "${FRONTEND_SIZE} (> ${MAX_IMAGE_SIZE_FRONTEND_MB}MB)"
    fi
}

# Test API response times
test_api_performance() {
    echo -e "\n${YELLOW}Testing API Performance...${NC}"

    # Test health endpoint response time
    RESPONSE_TIME=$(curl -o /dev/null -s -w "%{time_total}" "$API_BASE/health")
    RESPONSE_MS=$(echo "$RESPONSE_TIME * 1000" | bc)

    if (( $(echo "$RESPONSE_MS < 100" | bc -l) )); then
        log_test "Health Endpoint" "PASS" "${RESPONSE_MS}ms (< 100ms)"
    else
        log_test "Health Endpoint" "WARN" "${RESPONSE_MS}ms (> 100ms)"
    fi

    # Test API docs response time
    DOCS_TIME=$(curl -o /dev/null -s -w "%{time_total}" "$API_BASE/docs")
    DOCS_MS=$(echo "$DOCS_TIME * 1000" | bc)

    if (( $(echo "$DOCS_MS < 500" | bc -l) )); then
        log_test "API Docs" "PASS" "${DOCS_MS}ms (< 500ms)"
    else
        log_test "API Docs" "WARN" "${DOCS_MS}ms (> 500ms)"
    fi

    # Test frontend load time
    FRONTEND_TIME=$(curl -o /dev/null -s -w "%{time_total}" "$FRONTEND_BASE")
    FRONTEND_MS=$(echo "$FRONTEND_TIME * 1000" | bc)

    if (( $(echo "$FRONTEND_MS < 200" | bc -l) )); then
        log_test "Frontend Load" "PASS" "${FRONTEND_MS}ms (< 200ms)"
    else
        log_test "Frontend Load" "WARN" "${FRONTEND_MS}ms (> 200ms)"
    fi
}

# Test concurrent operations
test_concurrent_operations() {
    echo -e "\n${YELLOW}Testing Concurrent Operations...${NC}"

    # Create multiple test projects concurrently
    echo "Creating 10 concurrent projects..."
    for i in {1..10}; do
        curl -s -X POST "$API_BASE/api/projects" \
            -H "Content-Type: application/json" \
            -d "{\"name\":\"Concurrent Test $i\",\"mission\":\"Performance test\"}" &
    done

    wait

    # Check if all projects were created
    PROJECT_COUNT=$(curl -s "$API_BASE/api/projects" | grep -o "Concurrent Test" | wc -l)

    if [ $PROJECT_COUNT -eq 10 ]; then
        log_test "Concurrent Creates" "PASS" "10 projects created successfully"
    else
        log_test "Concurrent Creates" "FAIL" "Only $PROJECT_COUNT/10 projects created"
    fi

    # Test WebSocket connections (simulate)
    echo "Testing WebSocket stability..."
    # This would require a WebSocket client, so we'll just check if the port is responsive
    for i in {1..5}; do
        if nc -z localhost 6003 2>/dev/null; then
            :
        else
            log_test "WebSocket Stability" "FAIL" "WebSocket port not responsive"
            break
        fi
    done
    log_test "WebSocket Stability" "PASS" "WebSocket port remains responsive"

    # Clean up test projects
    echo "Cleaning up test projects..."
    curl -s "$API_BASE/api/projects" | grep -o '"id":"[^"]*' | cut -d'"' -f4 | while read id; do
        curl -X DELETE "$API_BASE/api/projects/$id" > /dev/null 2>&1
    done
}

# Test memory leaks
test_memory_leaks() {
    echo -e "\n${YELLOW}Testing for Memory Leaks...${NC}"

    # Get initial memory usage
    INITIAL_MEM=$(docker stats --no-stream --format "{{.MemUsage}}" $(docker-compose ps -q backend) | cut -d'/' -f1 | grep -o '[0-9.]*')

    # Perform repeated operations
    echo "Performing 100 API calls..."
    for i in {1..100}; do
        curl -s "$API_BASE/health" > /dev/null 2>&1
    done

    # Wait a moment for garbage collection
    sleep 5

    # Get final memory usage
    FINAL_MEM=$(docker stats --no-stream --format "{{.MemUsage}}" $(docker-compose ps -q backend) | cut -d'/' -f1 | grep -o '[0-9.]*')

    # Calculate increase
    MEM_INCREASE=$(echo "$FINAL_MEM - $INITIAL_MEM" | bc)

    if (( $(echo "$MEM_INCREASE < 50" | bc -l) )); then
        log_test "Memory Leak Check" "PASS" "Memory increase: ${MEM_INCREASE}MB (< 50MB)"
    else
        log_test "Memory Leak Check" "WARN" "Memory increase: ${MEM_INCREASE}MB (> 50MB)"
    fi
}

# Main execution
main() {
    echo "Starting Docker Performance Tests..."
    echo "Test results will be saved to: $TEST_LOG"
    echo ""

    # Change to docker directory
    cd "$(dirname "$0")/.."

    # Run tests
    test_image_sizes
    test_startup_performance
    test_resource_usage
    test_api_performance
    test_concurrent_operations
    test_memory_leaks

    # Summary
    echo -e "\n===================================="
    echo "Test Summary"
    echo "===================================="
    echo -e "Total Tests: $TOTAL_TESTS"
    echo -e "${GREEN}Passed: $PASSED_TESTS${NC}"
    echo -e "${RED}Failed: $FAILED_TESTS${NC}"

    # Performance report
    echo -e "\n===================================="
    echo "Performance Metrics"
    echo "===================================="
    cat "$RESULTS_DIR/container_stats.txt" 2>/dev/null || echo "No stats available"

    if [ $FAILED_TESTS -eq 0 ]; then
        echo -e "\n${GREEN}All performance tests passed!${NC}"
        exit 0
    else
        echo -e "\n${RED}Some tests failed. Please review the logs.${NC}"
        exit 1
    fi
}

# Run main function
main "$@"