#!/bin/bash
# test_health.sh - Docker Health Check Validation Tests
# GiljoAI MCP Orchestrator Deployment Testing

set -e

echo "===================================="
echo "Docker Health Tests - GiljoAI MCP"
echo "===================================="

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test results directory
RESULTS_DIR="./test_results"
mkdir -p "$RESULTS_DIR"
TEST_LOG="$RESULTS_DIR/health_test_$(date +%Y%m%d_%H%M%S).log"

# Test counters
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Service ports
FRONTEND_PORT=6000
API_PORT=6002
WEBSOCKET_PORT=6003
DB_PORT=5432

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

# Wait for service with timeout
wait_for_service() {
    local service=$1
    local port=$2
    local timeout=${3:-30}
    local elapsed=0

    echo "Waiting for $service on port $port..."

    while [ $elapsed -lt $timeout ]; do
        if nc -z localhost $port 2>/dev/null; then
            return 0
        fi
        sleep 1
        elapsed=$((elapsed + 1))
    done

    return 1
}

# Check if stack is running
check_stack_running() {
    echo -e "\n${YELLOW}Checking Docker stack status...${NC}"

    # Check if docker-compose stack is running
    if docker-compose ps | grep -q "Up"; then
        log_test "Stack Status" "PASS" "Docker stack is running"
        return 0
    else
        log_test "Stack Status" "FAIL" "Docker stack not running - run docker-compose up -d first"
        return 1
    fi
}

# Test Database Health
test_database_health() {
    echo -e "\n${YELLOW}Testing Database Health...${NC}"

    # Check if PostgreSQL container is running
    if docker-compose ps | grep -q "postgres.*Up"; then
        log_test "PostgreSQL Container" "PASS" "Container is running"

        # Test database connection
        if docker-compose exec -T postgres pg_isready > /dev/null 2>&1; then
            log_test "Database Ready" "PASS" "PostgreSQL accepting connections"

            # Check database exists
            if docker-compose exec -T postgres psql -U postgres -c "\l" | grep -q "giljoai"; then
                log_test "Database Created" "PASS" "giljoai database exists"
            else
                log_test "Database Created" "FAIL" "giljoai database not found"
            fi

            # Check health check status
            health=$(docker inspect --format='{{.State.Health.Status}}' $(docker-compose ps -q postgres) 2>/dev/null)
            if [ "$health" = "healthy" ]; then
                log_test "DB Health Check" "PASS" "Container reports healthy"
            else
                log_test "DB Health Check" "WARN" "Health status: $health"
            fi

        else
            log_test "Database Ready" "FAIL" "PostgreSQL not accepting connections"
        fi
    else
        log_test "PostgreSQL Container" "FAIL" "Container not running"
    fi
}

# Test Backend Health
test_backend_health() {
    echo -e "\n${YELLOW}Testing Backend Health...${NC}"

    # Check if backend container is running
    if docker-compose ps | grep -q "backend.*Up"; then
        log_test "Backend Container" "PASS" "Container is running"

        # Wait for backend to be ready
        if wait_for_service "Backend API" $API_PORT; then
            log_test "Backend Port" "PASS" "API port $API_PORT is open"

            # Test health endpoint
            if curl -f -s http://localhost:$API_PORT/health > /dev/null 2>&1; then
                log_test "Health Endpoint" "PASS" "/health endpoint responding"

                # Test API docs
                if curl -f -s http://localhost:$API_PORT/docs > /dev/null 2>&1; then
                    log_test "API Documentation" "PASS" "/docs endpoint available"
                else
                    log_test "API Documentation" "FAIL" "/docs endpoint not responding"
                fi

            else
                log_test "Health Endpoint" "FAIL" "/health endpoint not responding"
            fi

            # Check WebSocket endpoint
            if wait_for_service "WebSocket" $WEBSOCKET_PORT 10; then
                log_test "WebSocket Port" "PASS" "WebSocket port $WEBSOCKET_PORT is open"
            else
                log_test "WebSocket Port" "FAIL" "WebSocket port $WEBSOCKET_PORT not accessible"
            fi

            # Check container health
            health=$(docker inspect --format='{{.State.Health.Status}}' $(docker-compose ps -q backend) 2>/dev/null)
            if [ "$health" = "healthy" ]; then
                log_test "Backend Health Check" "PASS" "Container reports healthy"
            else
                log_test "Backend Health Check" "WARN" "Health status: $health"
            fi

        else
            log_test "Backend Port" "FAIL" "API port $API_PORT not accessible"
        fi
    else
        log_test "Backend Container" "FAIL" "Container not running"
    fi
}

# Test Frontend Health
test_frontend_health() {
    echo -e "\n${YELLOW}Testing Frontend Health...${NC}"

    # Check if frontend container is running
    if docker-compose ps | grep -q "frontend.*Up"; then
        log_test "Frontend Container" "PASS" "Container is running"

        # Wait for frontend to be ready
        if wait_for_service "Frontend" $FRONTEND_PORT; then
            log_test "Frontend Port" "PASS" "Frontend port $FRONTEND_PORT is open"

            # Test main page
            response_code=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:$FRONTEND_PORT/)
            if [ "$response_code" = "200" ]; then
                log_test "Frontend Main Page" "PASS" "Main page returns 200"

                # Check for Vue app
                if curl -s http://localhost:$FRONTEND_PORT/ | grep -q "app.js\|main.js"; then
                    log_test "Vue Application" "PASS" "Vue app detected"
                else
                    log_test "Vue Application" "WARN" "Vue app markers not found"
                fi

                # Test static assets
                if curl -f -s http://localhost:$FRONTEND_PORT/favicon.ico > /dev/null 2>&1; then
                    log_test "Static Assets" "PASS" "Favicon loads successfully"
                else
                    log_test "Static Assets" "WARN" "Favicon not accessible"
                fi

            else
                log_test "Frontend Main Page" "FAIL" "Main page returns $response_code"
            fi

            # Check container health
            health=$(docker inspect --format='{{.State.Health.Status}}' $(docker-compose ps -q frontend) 2>/dev/null)
            if [ "$health" = "healthy" ]; then
                log_test "Frontend Health Check" "PASS" "Container reports healthy"
            else
                log_test "Frontend Health Check" "WARN" "Health status: $health"
            fi

        else
            log_test "Frontend Port" "FAIL" "Frontend port $FRONTEND_PORT not accessible"
        fi
    else
        log_test "Frontend Container" "FAIL" "Container not running"
    fi
}

# Test Container Restart Policy
test_restart_policy() {
    echo -e "\n${YELLOW}Testing Container Restart Policies...${NC}"

    for service in postgres backend frontend; do
        policy=$(docker inspect --format='{{.HostConfig.RestartPolicy.Name}}' $(docker-compose ps -q $service) 2>/dev/null)

        if [ "$policy" = "always" ] || [ "$policy" = "unless-stopped" ]; then
            log_test "$service Restart Policy" "PASS" "Policy: $policy"
        else
            log_test "$service Restart Policy" "WARN" "Policy: $policy (should be 'always' or 'unless-stopped')"
        fi
    done
}

# Test Network Connectivity
test_network_connectivity() {
    echo -e "\n${YELLOW}Testing Network Connectivity...${NC}"

    # Check if custom network exists
    if docker network ls | grep -q "giljoai"; then
        log_test "Docker Network" "PASS" "Custom network exists"

        # Test backend can reach database
        if docker-compose exec -T backend ping -c 1 postgres > /dev/null 2>&1; then
            log_test "Backend->DB Connection" "PASS" "Backend can reach database"
        else
            log_test "Backend->DB Connection" "WARN" "Cannot verify backend->db connectivity"
        fi

    else
        log_test "Docker Network" "WARN" "Custom network not found"
    fi
}

# Test Health Check Commands
test_healthcheck_commands() {
    echo -e "\n${YELLOW}Testing Health Check Commands...${NC}"

    # Check if health checks are defined in docker-compose
    for service in postgres backend frontend; do
        if docker inspect $(docker-compose ps -q $service) | grep -q "Healthcheck"; then
            log_test "$service HEALTHCHECK" "PASS" "Health check defined"

            # Get health check details
            interval=$(docker inspect --format='{{.Config.Healthcheck.Interval}}' $(docker-compose ps -q $service) 2>/dev/null)
            timeout=$(docker inspect --format='{{.Config.Healthcheck.Timeout}}' $(docker-compose ps -q $service) 2>/dev/null)
            retries=$(docker inspect --format='{{.Config.Healthcheck.Retries}}' $(docker-compose ps -q $service) 2>/dev/null)

            echo "  - Interval: $interval, Timeout: $timeout, Retries: $retries" >> "$TEST_LOG"
        else
            log_test "$service HEALTHCHECK" "FAIL" "No health check defined"
        fi
    done
}

# Main execution
main() {
    echo "Starting Docker Health Tests..."
    echo "Test results will be saved to: $TEST_LOG"
    echo ""

    # Change to docker directory
    cd "$(dirname "$0")/.."

    # Check if stack is running
    if ! check_stack_running; then
        echo -e "\n${RED}Please start the Docker stack first:${NC}"
        echo "  cd docker && docker-compose up -d"
        exit 1
    fi

    # Run tests
    test_database_health
    test_backend_health
    test_frontend_health
    test_restart_policy
    test_network_connectivity
    test_healthcheck_commands

    # Summary
    echo -e "\n===================================="
    echo "Test Summary"
    echo "===================================="
    echo -e "Total Tests: $TOTAL_TESTS"
    echo -e "${GREEN}Passed: $PASSED_TESTS${NC}"
    echo -e "${RED}Failed: $FAILED_TESTS${NC}"

    if [ $FAILED_TESTS -eq 0 ]; then
        echo -e "\n${GREEN}All health tests passed!${NC}"
        exit 0
    else
        echo -e "\n${RED}Some tests failed. Please review the logs.${NC}"
        exit 1
    fi
}

# Run main function
main "$@"