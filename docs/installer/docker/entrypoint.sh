#!/bin/sh
# GiljoAI MCP Docker Entrypoint Script

set -e

echo "Starting GiljoAI MCP Container..."
echo "Environment: ${GILJO_ENV:-production}"
echo "Version: ${VERSION:-latest}"

# Function to wait for a service
wait_for_service() {
    local host="$1"
    local port="$2"
    local service="$3"
    local max_attempts=30
    local attempt=0
    
    echo "Waiting for $service at $host:$port..."
    
    while ! nc -z "$host" "$port" 2>/dev/null; do
        attempt=$((attempt + 1))
        if [ $attempt -ge $max_attempts ]; then
            echo "ERROR: $service failed to start after $max_attempts attempts"
            exit 1
        fi
        echo "  Attempt $attempt/$max_attempts - $service not ready, waiting..."
        sleep 2
    done
    
    echo "✓ $service is ready"
}

# Create required directories if they don't exist
mkdir -p "${GILJO_CONFIG_DIR:-/app/config}" \
         "${GILJO_DATA_DIR:-/app/data}" \
         "${GILJO_LOG_DIR:-/app/logs}" \
         "${GILJO_TEMP_DIR:-/app/temp}"

# Handle secrets if they exist (production mode)
if [ -f /run/secrets/database_url ]; then
    export DATABASE_URL=$(cat /run/secrets/database_url)
fi

if [ -f /run/secrets/redis_url ]; then
    export REDIS_URL=$(cat /run/secrets/redis_url)
fi

if [ -f /run/secrets/app_secret_key ]; then
    export GILJO_SECRET_KEY=$(cat /run/secrets/app_secret_key)
fi

if [ -f /run/secrets/api_key ]; then
    export GILJO_API_KEY=$(cat /run/secrets/api_key)
fi

# Wait for dependencies
if [ -n "${DATABASE_URL}" ]; then
    # Extract host and port from DATABASE_URL
    DB_HOST=$(echo "$DATABASE_URL" | sed -n 's/.*@\([^:]*\):.*/\1/p')
    DB_PORT=$(echo "$DATABASE_URL" | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')
    
    if [ -n "$DB_HOST" ] && [ -n "$DB_PORT" ]; then
        wait_for_service "$DB_HOST" "$DB_PORT" "PostgreSQL"
    fi
fi

if [ -n "${REDIS_URL}" ]; then
    # Extract host and port from REDIS_URL
    REDIS_HOST=$(echo "$REDIS_URL" | sed -n 's/.*@\([^:]*\):.*/\1/p')
    REDIS_PORT=$(echo "$REDIS_URL" | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')
    
    if [ -n "$REDIS_HOST" ] && [ -n "$REDIS_PORT" ]; then
        wait_for_service "$REDIS_HOST" "$REDIS_PORT" "Redis"
    fi
fi

# Run database migrations if needed
if [ "${RUN_MIGRATIONS:-true}" = "true" ] && [ -f "/app/scripts/migrate.py" ]; then
    echo "Running database migrations..."
    python /app/scripts/migrate.py || {
        echo "WARNING: Migration failed, continuing anyway"
    }
fi

# Generate configuration if it doesn't exist
if [ ! -f "${GILJO_CONFIG_DIR}/config.yaml" ] && [ -f "/app/scripts/generate_config.py" ]; then
    echo "Generating configuration file..."
    python /app/scripts/generate_config.py
fi

# Handle different run modes
case "${RUN_MODE:-server}" in
    server)
        echo "Starting GiljoAI MCP Server..."
        exec "$@"
        ;;
    worker)
        echo "Starting GiljoAI Worker..."
        exec python -m src.giljo_mcp.worker "$@"
        ;;
    migrate)
        echo "Running migrations only..."
        python /app/scripts/migrate.py
        ;;
    shell)
        echo "Starting interactive shell..."
        exec /bin/sh
        ;;
    test)
        echo "Running tests..."
        exec pytest tests/ "$@"
        ;;
    *)
        echo "Unknown RUN_MODE: ${RUN_MODE}"
        echo "Valid modes: server, worker, migrate, shell, test"
        exit 1
        ;;
esac