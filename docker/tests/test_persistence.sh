#!/bin/bash
# test_persistence.sh - Docker Data Persistence Tests
# GiljoAI MCP Orchestrator Deployment Testing

set -e

echo "===================================="
echo "Docker Persistence Tests - GiljoAI MCP"
echo "===================================="

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test results directory
RESULTS_DIR="./test_results"
mkdir -p "$RESULTS_DIR"
TEST_LOG="$RESULTS_DIR/persistence_test_$(date +%Y%m%d_%H%M%S).log"

# Test counters
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# API endpoint
API_BASE="http://localhost:6002"

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

# Create test data
create_test_data() {
    echo -e "\n${YELLOW}Creating test data...${NC}"

    # Create a test project via API
    TEST_PROJECT_ID=$(curl -s -X POST "$API_BASE/api/projects" \
        -H "Content-Type: application/json" \
        -d '{"name":"Test Project","mission":"Testing persistence"}' \
        | grep -o '"id":"[^"]*' | cut -d'"' -f4)

    if [ -n "$TEST_PROJECT_ID" ]; then
        log_test "Create Test Project" "PASS" "Project ID: $TEST_PROJECT_ID"
        echo "$TEST_PROJECT_ID" > "$RESULTS_DIR/test_project_id.txt"
    else
        log_test "Create Test Project" "FAIL" "Failed to create project"
        return 1
    fi

    # Create test agent
    AGENT_RESPONSE=$(curl -s -X POST "$API_BASE/api/agents" \
        -H "Content-Type: application/json" \
        -d "{\"project_id\":\"$TEST_PROJECT_ID\",\"name\":\"test-agent\",\"role\":\"tester\"}")

    if echo "$AGENT_RESPONSE" | grep -q "test-agent"; then
        log_test "Create Test Agent" "PASS" "Agent created successfully"
    else
        log_test "Create Test Agent" "FAIL" "Failed to create agent"
    fi

    # Insert test data directly into database
    docker-compose exec -T postgres psql -U postgres -d giljoai <<EOF
    INSERT INTO messages (id, project_id, from_agent, to_agent, content, created_at)
    VALUES (
        gen_random_uuid(),
        '$TEST_PROJECT_ID',
        'test-agent',
        'orchestrator',
        'Test persistence message',
        NOW()
    );
EOF

    if [ $? -eq 0 ]; then
        log_test "Insert Test Data" "PASS" "Test message inserted"
    else
        log_test "Insert Test Data" "FAIL" "Failed to insert test data"
    fi
}

# Verify data exists
verify_data_exists() {
    echo -e "\n${YELLOW}Verifying test data...${NC}"

    # Check project exists
    PROJECT_CHECK=$(curl -s "$API_BASE/api/projects/$TEST_PROJECT_ID")
    if echo "$PROJECT_CHECK" | grep -q "Test Project"; then
        log_test "Verify Project" "PASS" "Project data exists"
    else
        log_test "Verify Project" "FAIL" "Project data not found"
    fi

    # Check database directly
    MESSAGE_COUNT=$(docker-compose exec -T postgres psql -U postgres -d giljoai -t -c \
        "SELECT COUNT(*) FROM messages WHERE project_id='$TEST_PROJECT_ID';" | tr -d ' ')

    if [ "$MESSAGE_COUNT" -gt 0 ]; then
        log_test "Verify Messages" "PASS" "$MESSAGE_COUNT messages found"
    else
        log_test "Verify Messages" "FAIL" "No messages found"
    fi
}

# Test container restart persistence
test_container_restart() {
    echo -e "\n${YELLOW}Testing container restart persistence...${NC}"

    # Restart backend container
    echo "Restarting backend container..."
    docker-compose restart backend > /dev/null 2>&1

    # Wait for backend to be ready
    sleep 10

    # Check if backend is healthy
    if curl -f -s "$API_BASE/health" > /dev/null 2>&1; then
        log_test "Backend Restart" "PASS" "Backend healthy after restart"

        # Verify data still exists
        PROJECT_CHECK=$(curl -s "$API_BASE/api/projects/$TEST_PROJECT_ID")
        if echo "$PROJECT_CHECK" | grep -q "Test Project"; then
            log_test "Data After Restart" "PASS" "Data persisted after container restart"
        else
            log_test "Data After Restart" "FAIL" "Data lost after container restart"
        fi
    else
        log_test "Backend Restart" "FAIL" "Backend not healthy after restart"
    fi
}

# Test stack restart persistence
test_stack_restart() {
    echo -e "\n${YELLOW}Testing full stack restart persistence...${NC}"

    # Stop the entire stack
    echo "Stopping Docker stack..."
    docker-compose down > /dev/null 2>&1

    # Start the stack again
    echo "Starting Docker stack..."
    docker-compose up -d > /dev/null 2>&1

    # Wait for services to be ready
    echo "Waiting for services to start..."
    sleep 20

    # Check if all services are running
    if docker-compose ps | grep -q "Up.*postgres" && \
       docker-compose ps | grep -q "Up.*backend" && \
       docker-compose ps | grep -q "Up.*frontend"; then
        log_test "Stack Restart" "PASS" "All services running after restart"

        # Verify data persistence
        MESSAGE_COUNT=$(docker-compose exec -T postgres psql -U postgres -d giljoai -t -c \
            "SELECT COUNT(*) FROM messages WHERE project_id='$TEST_PROJECT_ID';" 2>/dev/null | tr -d ' ')

        if [ "$MESSAGE_COUNT" -gt 0 ]; then
            log_test "Data After Stack Restart" "PASS" "Data persisted after stack restart"
        else
            log_test "Data After Stack Restart" "FAIL" "Data lost after stack restart"
        fi
    else
        log_test "Stack Restart" "FAIL" "Services failed to start"
    fi
}

# Test volume persistence
test_volume_persistence() {
    echo -e "\n${YELLOW}Testing volume persistence...${NC}"

    # Check if volumes exist
    if docker volume ls | grep -q "postgres_data"; then
        log_test "Database Volume" "PASS" "postgres_data volume exists"

        # Get volume info
        VOLUME_SIZE=$(docker system df -v | grep postgres_data | awk '{print $4}')
        echo "  Volume size: $VOLUME_SIZE" >> "$TEST_LOG"
    else
        log_test "Database Volume" "FAIL" "postgres_data volume not found"
    fi

    # Check for other persistent volumes
    if docker volume ls | grep -q "uploads"; then
        log_test "Uploads Volume" "PASS" "uploads volume exists"
    else
        log_test "Uploads Volume" "WARN" "uploads volume not found"
    fi

    if docker volume ls | grep -q "logs"; then
        log_test "Logs Volume" "PASS" "logs volume exists"
    else
        log_test "Logs Volume" "WARN" "logs volume not found"
    fi
}

# Test backup and restore
test_backup_restore() {
    echo -e "\n${YELLOW}Testing backup and restore...${NC}"

    # Create backup
    echo "Creating database backup..."
    docker-compose exec -T postgres pg_dump -U postgres giljoai > "$RESULTS_DIR/backup.sql" 2>/dev/null

    if [ -s "$RESULTS_DIR/backup.sql" ]; then
        log_test "Database Backup" "PASS" "Backup created successfully"

        # Count lines in backup
        BACKUP_LINES=$(wc -l < "$RESULTS_DIR/backup.sql")
        echo "  Backup size: $BACKUP_LINES lines" >> "$TEST_LOG"

        # Test restore (create test database)
        docker-compose exec -T postgres psql -U postgres <<EOF
CREATE DATABASE giljoai_test;
EOF

        # Restore to test database
        docker-compose exec -T postgres psql -U postgres giljoai_test < "$RESULTS_DIR/backup.sql" 2>/dev/null

        if [ $? -eq 0 ]; then
            log_test "Database Restore" "PASS" "Backup restored successfully"

            # Verify restored data
            RESTORED_COUNT=$(docker-compose exec -T postgres psql -U postgres -d giljoai_test -t -c \
                "SELECT COUNT(*) FROM messages;" 2>/dev/null | tr -d ' ')

            if [ "$RESTORED_COUNT" -gt 0 ]; then
                log_test "Restored Data" "PASS" "$RESTORED_COUNT messages in restored database"
            else
                log_test "Restored Data" "FAIL" "No data in restored database"
            fi

            # Cleanup test database
            docker-compose exec -T postgres psql -U postgres -c "DROP DATABASE giljoai_test;" 2>/dev/null
        else
            log_test "Database Restore" "FAIL" "Failed to restore backup"
        fi
    else
        log_test "Database Backup" "FAIL" "Failed to create backup"
    fi
}

# Test file system persistence
test_filesystem_persistence() {
    echo -e "\n${YELLOW}Testing file system persistence...${NC}"

    # Create test file in mounted volume
    TEST_FILE="test_persistence_$(date +%s).txt"
    echo "Test content" | docker-compose exec -T backend sh -c "cat > /app/uploads/$TEST_FILE" 2>/dev/null

    # Restart container
    docker-compose restart backend > /dev/null 2>&1
    sleep 10

    # Check if file still exists
    if docker-compose exec -T backend test -f "/app/uploads/$TEST_FILE" 2>/dev/null; then
        log_test "File Persistence" "PASS" "Test file persisted after restart"

        # Clean up test file
        docker-compose exec -T backend rm "/app/uploads/$TEST_FILE" 2>/dev/null
    else
        log_test "File Persistence" "FAIL" "Test file lost after restart"
    fi

    # Check configuration persistence
    if docker-compose exec -T backend test -f "/app/config/config.yaml" 2>/dev/null; then
        log_test "Config Persistence" "PASS" "Configuration files persist"
    else
        log_test "Config Persistence" "WARN" "Configuration file not found"
    fi
}

# Cleanup test data
cleanup_test_data() {
    echo -e "\n${YELLOW}Cleaning up test data...${NC}"

    if [ -f "$RESULTS_DIR/test_project_id.txt" ]; then
        TEST_PROJECT_ID=$(cat "$RESULTS_DIR/test_project_id.txt")

        # Delete test project
        curl -X DELETE "$API_BASE/api/projects/$TEST_PROJECT_ID" > /dev/null 2>&1

        # Clean up database
        docker-compose exec -T postgres psql -U postgres -d giljoai <<EOF
DELETE FROM messages WHERE project_id='$TEST_PROJECT_ID';
DELETE FROM agents WHERE project_id='$TEST_PROJECT_ID';
DELETE FROM projects WHERE id='$TEST_PROJECT_ID';
EOF

        rm "$RESULTS_DIR/test_project_id.txt"
        echo "Test data cleaned up"
    fi
}

# Main execution
main() {
    echo "Starting Docker Persistence Tests..."
    echo "Test results will be saved to: $TEST_LOG"
    echo ""

    # Change to docker directory
    cd "$(dirname "$0")/.."

    # Check if stack is running
    if ! docker-compose ps | grep -q "Up"; then
        echo -e "\n${RED}Docker stack not running. Starting it now...${NC}"
        docker-compose up -d
        sleep 20
    fi

    # Get test project ID if it exists
    if [ -f "$RESULTS_DIR/test_project_id.txt" ]; then
        TEST_PROJECT_ID=$(cat "$RESULTS_DIR/test_project_id.txt")
        echo "Using existing test project: $TEST_PROJECT_ID"
    else
        create_test_data
    fi

    # Run tests
    verify_data_exists
    test_container_restart
    test_volume_persistence
    test_filesystem_persistence
    test_stack_restart
    test_backup_restore

    # Cleanup
    cleanup_test_data

    # Summary
    echo -e "\n===================================="
    echo "Test Summary"
    echo "===================================="
    echo -e "Total Tests: $TOTAL_TESTS"
    echo -e "${GREEN}Passed: $PASSED_TESTS${NC}"
    echo -e "${RED}Failed: $FAILED_TESTS${NC}"

    if [ $FAILED_TESTS -eq 0 ]; then
        echo -e "\n${GREEN}All persistence tests passed!${NC}"
        exit 0
    else
        echo -e "\n${RED}Some tests failed. Please review the logs.${NC}"
        exit 1
    fi
}

# Run main function
main "$@"