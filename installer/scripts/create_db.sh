#!/bin/bash
# GiljoAI MCP Database Creation Script for Linux/macOS
# This is a TEMPLATE script - the installer will generate a customized version
# with pre-filled passwords and configuration.
#
# INSTRUCTIONS:
# 1. Make sure you have the PostgreSQL admin password
# 2. Run this script with: bash create_db.sh
#    (On Linux, you may need: sudo bash create_db.sh)
#
# This script will:
# - Create PostgreSQL roles (giljo_owner, giljo_user)
# - Create the giljo_mcp database
# - Set up all required permissions
# - Save credentials for the installer

set -euo pipefail

echo ""
echo "====================================================================="
echo "   GiljoAI MCP - PostgreSQL Database Creation Script"
echo "====================================================================="
echo ""

# Configuration (will be pre-filled by installer)
PG_HOST="localhost"
PG_PORT=5432
PG_USER="postgres"
DB_NAME="giljo_mcp"
OWNER_ROLE="giljo_owner"
USER_ROLE="giljo_user"
OWNER_PASSWORD="WILL_BE_GENERATED"
USER_PASSWORD="WILL_BE_GENERATED"

echo "Configuration:"
echo "  PostgreSQL Host: $PG_HOST"
echo "  PostgreSQL Port: $PG_PORT"
echo "  Database Name:   $DB_NAME"
echo ""

# Function to run psql command
run_psql() {
    local database="${1:-postgres}"
    local command="$2"
    local ignore_error="${3:-false}"

    if [ "$ignore_error" = "true" ]; then
        PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -d "$database" -c "$command" 2>/dev/null || true
    else
        PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -d "$database" -c "$command"
    fi
}

# Prompt for PostgreSQL admin password
echo "PostgreSQL Administration"
read -sp "Enter password for PostgreSQL user '$PG_USER': " POSTGRES_PASSWORD
echo ""
echo ""

echo "Testing PostgreSQL connection..."

if ! run_psql "postgres" "SELECT version();" "true" > /dev/null 2>&1; then
    echo "  ERROR: Cannot connect to PostgreSQL"
    echo ""
    echo "Please verify:"
    echo "  1. PostgreSQL is installed and running"
    echo "  2. The password is correct"
    echo "  3. PostgreSQL is accepting connections on port $PG_PORT"
    echo ""
    exit 1
fi

echo "  Connected successfully!"
echo ""

echo "Creating database roles..."

# Check if owner role exists
if run_psql "postgres" "SELECT 1 FROM pg_roles WHERE rolname='$OWNER_ROLE';" "true" | grep -q "1"; then
    echo "  Role '$OWNER_ROLE' exists, updating password..."
    run_psql "postgres" "ALTER ROLE $OWNER_ROLE WITH PASSWORD '$OWNER_PASSWORD';"
else
    echo "  Creating role '$OWNER_ROLE'..."
    run_psql "postgres" "CREATE ROLE $OWNER_ROLE LOGIN PASSWORD '$OWNER_PASSWORD';"
fi

# Check if user role exists
if run_psql "postgres" "SELECT 1 FROM pg_roles WHERE rolname='$USER_ROLE';" "true" | grep -q "1"; then
    echo "  Role '$USER_ROLE' exists, updating password..."
    run_psql "postgres" "ALTER ROLE $USER_ROLE WITH PASSWORD '$USER_PASSWORD';"
else
    echo "  Creating role '$USER_ROLE'..."
    run_psql "postgres" "CREATE ROLE $USER_ROLE LOGIN PASSWORD '$USER_PASSWORD';"
fi

echo "  Roles created successfully!"
echo ""

echo "Creating database..."

# Check if database exists
if run_psql "postgres" "SELECT 1 FROM pg_database WHERE datname='$DB_NAME';" "true" | grep -q "1"; then
    echo "  Database '$DB_NAME' already exists"
else
    echo "  Creating database '$DB_NAME'..."
    run_psql "postgres" "CREATE DATABASE $DB_NAME OWNER $OWNER_ROLE;"
    echo "  Database created successfully!"
fi

echo ""
echo "Setting up permissions..."

# Grant permissions (ignore errors if already granted)
run_psql "$DB_NAME" "GRANT CONNECT ON DATABASE $DB_NAME TO $USER_ROLE;" "true"
run_psql "$DB_NAME" "GRANT USAGE, CREATE ON SCHEMA public TO $OWNER_ROLE;" "true"
run_psql "$DB_NAME" "GRANT USAGE ON SCHEMA public TO $USER_ROLE;" "true"

# Grant default privileges
run_psql "$DB_NAME" "ALTER DEFAULT PRIVILEGES FOR ROLE $OWNER_ROLE IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO $USER_ROLE;" "true"
run_psql "$DB_NAME" "ALTER DEFAULT PRIVILEGES FOR ROLE $OWNER_ROLE IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO $USER_ROLE;" "true"

echo "  Permissions configured successfully!"
echo ""

# Clear password from environment
unset POSTGRES_PASSWORD

# Create verification flag for installer
echo "Creating verification flag..."
timestamp=$(date '+%Y-%m-%d %H:%M:%S')
echo "DATABASE_CREATED=$timestamp" > ../../database_created.flag

echo ""
echo "====================================================================="
echo "   Database Setup Complete!"
echo "====================================================================="
echo ""
echo "Database Details:"
echo "  Database: $DB_NAME"
echo "  Owner Role: $OWNER_ROLE"
echo "  User Role: $USER_ROLE"
echo ""
echo "Credentials have been saved to:"
echo "  installer/credentials/db_credentials_*.txt"
echo ""
echo "You can now return to the installer and press Enter to continue."
echo ""
