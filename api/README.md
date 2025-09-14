# GiljoAI MCP Orchestrator REST API

## Overview

The GiljoAI MCP REST API provides comprehensive endpoints for managing multi-agent orchestration, enabling coordinated AI development teams to tackle projects of unlimited complexity.

## Quick Start

### Running the API Server

```bash
# Basic startup
python api/run_api.py

# Development mode with auto-reload
python api/run_api.py --reload --log-level debug

# Production mode with multiple workers
python api/run_api.py --workers 4 --host 0.0.0.0 --port 8000

# With SSL/TLS
python api/run_api.py --ssl-keyfile key.pem --ssl-certfile cert.pem
```

### API Documentation

Once running, access the interactive API documentation at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## API Endpoints

### Project Management (`/api/v1/projects`)

- `POST /` - Create new project
- `GET /` - List all projects
- `GET /{project_id}` - Get project details
- `PATCH /{project_id}` - Update project
- `DELETE /{project_id}` - Close project

### Agent Control (`/api/v1/agents`)

- `POST /` - Create new agent
- `GET /{agent_name}/health` - Get agent health status
- `DELETE /{agent_name}` - Decommission agent

### Message Queue (`/api/v1/messages`)

- `POST /` - Send message to agents
- `GET /agent/{agent_name}` - Get messages for agent
- `POST /{message_id}/acknowledge` - Acknowledge message receipt
- `POST /{message_id}/complete` - Mark message as completed

### Task Management (`/api/v1/tasks`)

- `POST /` - Create new task
- `GET /` - List tasks
- `PATCH /{task_id}` - Update task
- `POST /{task_id}/complete` - Complete task

### Context Management (`/api/v1/context`)

- `GET /vision` - Get vision document (supports chunking)
- `GET /index` - Get context index
- `GET /section/{section}` - Get specific context section

### Configuration (`/api/v1/config`)

- `GET /` - Get system configuration
- `GET /key/{key_path}` - Get specific config value
- `PUT /key/{key_path}` - Set config value
- `PATCH /` - Update multiple configs
- `POST /reload` - Reload configuration
- `GET /tenants` - List tenant configurations
- `GET /tenant/{tenant_key}` - Get tenant config
- `PUT /tenant/{tenant_key}` - Set tenant config
- `DELETE /tenant/{tenant_key}` - Delete tenant config

### Statistics & Monitoring (`/api/v1/stats`)

- `GET /system` - System-wide statistics
- `GET /projects` - Project statistics
- `GET /agents` - Agent statistics
- `GET /messages` - Message queue statistics
- `GET /performance` - Real-time performance metrics
- `GET /timeseries/{metric}` - Time series data
- `GET /health/detailed` - Detailed health check

## WebSocket Support

Connect to WebSocket for real-time updates:

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/client123');

// Subscribe to project updates
ws.send(JSON.stringify({
    type: 'subscribe',
    entity_type: 'project',
    entity_id: 'project-uuid'
}));

// Handle messages
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('Update received:', data);
};
```

## Authentication

Authentication can be enabled via configuration:

```yaml
security:
  auth_enabled: true
  auth_type: api_key  # or 'oauth'
```

When enabled, include API key in headers:
```bash
curl -H "X-API-Key: your-api-key" http://localhost:8000/api/v1/projects
```

## Rate Limiting

Rate limiting is configurable per tenant:

```yaml
security:
  rate_limiting_enabled: true
  max_requests_per_minute: 60
```

## Error Responses

All errors follow a consistent format:

```json
{
    "error": "Error message",
    "status_code": 404,
    "detail": "Additional details (if debug mode)"
}
```

## Example Usage

### Create a Project

```bash
curl -X POST http://localhost:8000/api/v1/projects \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My AI Project",
    "mission": "Build an amazing feature",
    "agents": ["analyzer", "implementer", "tester"]
  }'
```

### Send Message to Agent

```bash
curl -X POST http://localhost:8000/api/v1/messages \
  -H "Content-Type: application/json" \
  -d '{
    "to_agents": ["implementer"],
    "content": "Please implement the user authentication module",
    "project_id": "project-uuid",
    "priority": "high"
  }'
```

### Get System Statistics

```bash
curl http://localhost:8000/api/v1/stats/system
```

## Testing

Run the comprehensive test suite:

```bash
# Run all API tests
pytest tests/test_api_endpoints_comprehensive.py -v

# Run specific test
pytest tests/test_api_endpoints_comprehensive.py::TestAPIEndpoints::test_create_project -v

# Run with coverage
pytest tests/test_api_endpoints_comprehensive.py --cov=api --cov-report=html
```

## Performance Considerations

- Default connection pool: 5 connections (configurable)
- Default request timeout: 60 seconds
- Maximum request size: 10MB
- WebSocket ping interval: 30 seconds
- Message retention: 30 days (configurable)

## Deployment

### Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "api/run_api.py", "--host", "0.0.0.0"]
```

### Production Recommendations

1. Use PostgreSQL instead of SQLite for concurrent access
2. Enable SSL/TLS for secure communication
3. Configure authentication and rate limiting
4. Use multiple workers for better performance
5. Set up monitoring and alerting
6. Regular database backups
7. Log aggregation and analysis

## Environment Variables

- `GILJO_DB_URL` - Database connection URL
- `GILJO_API_KEY` - API authentication key
- `GILJO_LOG_LEVEL` - Logging level
- `GILJO_CORS_ORIGINS` - Allowed CORS origins
- `GILJO_MAX_WORKERS` - Maximum worker processes

## Support

For issues, questions, or contributions:
- GitHub: https://github.com/giljoai/mcp-orchestrator
- Documentation: http://localhost:8000/docs
- Email: support@giljoai.com