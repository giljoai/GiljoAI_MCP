# GiljoAI MessageQueue System Guide

## Overview

The MessageQueue system provides a robust, ACID-compliant message queue infrastructure for the GiljoAI MCP orchestrator. It ensures reliable message delivery with priority routing, intelligent load balancing, crash recovery, and comprehensive monitoring.

## Key Features

### 1. Priority-Based Message Processing
- **Priority Levels**: Critical (1000), High (100), Normal (10), Low (1)
- **FIFO Within Priority**: Messages with same priority processed in order
- **Deadline Escalation**: Automatic priority boost for time-sensitive messages

### 2. Intelligent Routing
- **Capability Matching**: Routes messages to agents based on capabilities
- **Load Balancing**: Distributes work based on agent load and performance
- **Circuit Breaker**: Protects against cascading failures
- **Routing Rules**: Configurable rules for message type, priority, and content

### 3. ACID Compliance
- **Atomicity**: All operations wrapped in transactions
- **Consistency**: Validated state transitions
- **Isolation**: Row-level locking prevents conflicts
- **Durability**: Write-ahead logging ensures no message loss

### 4. Monitoring & Metrics
- **Queue Depth**: Messages per priority level
- **Processing Time**: Average time per agent
- **Throughput**: Messages per minute
- **Latency Percentiles**: P50, P95, P99
- **Stuck Detection**: Identifies messages processing too long

### 5. Fault Tolerance
- **Retry Mechanism**: Exponential backoff for failed messages
- **Dead Letter Queue**: Handles unprocessable messages
- **Crash Recovery**: Automatic recovery on restart
- **Circuit Breaker**: Prevents overloading failing agents

## Architecture

```
┌─────────────────────────────────────────┐
│           Message Tools API              │
├─────────────────────────────────────────┤
│            MessageQueue                  │
│  ┌─────────────┐  ┌─────────────────┐  │
│  │  Priority   │  │    Routing      │  │
│  │    Queue    │  │    Engine       │  │
│  └─────────────┘  └─────────────────┘  │
│  ┌─────────────┐  ┌─────────────────┐  │
│  │   Monitor   │  │  Stuck Detector │  │
│  └─────────────┘  └─────────────────┘  │
│  ┌─────────────┐  ┌─────────────────┐  │
│  │     DLQ     │  │   Durability    │  │
│  └─────────────┘  └─────────────────┘  │
├─────────────────────────────────────────┤
│           Database Layer                 │
│         (SQLAlchemy + Async)            │
└─────────────────────────────────────────┘
```

## Usage

### Basic Operations

```python
from giljo_mcp.queue import MessageQueue
from giljo_mcp.database import DatabaseManager
from giljo_mcp.tenant import TenantManager

# Initialize queue
db_manager = DatabaseManager()
tenant_manager = TenantManager()
queue = MessageQueue(db_manager, tenant_manager)

# Enqueue a message
message_id = await queue.enqueue(message)

# Dequeue messages for an agent
messages = await queue.dequeue("analyzer", batch_size=5)

# Process a message
success = await queue.process_message(message_id, "analyzer")

# Retry a failed message
retried = await queue.retry_message(message_id, "Temporary failure")

# Get queue statistics
stats = await queue.get_statistics()
```

### Routing Configuration

```python
from giljo_mcp.queue import (
    PriorityRoutingRule, 
    TypeRoutingRule, 
    ContentRoutingRule
)

# Route critical messages to orchestrator
queue._routing_engine._routing_rules.append(
    PriorityRoutingRule('critical', ['orchestrator'])
)

# Route error messages to error handler
queue._routing_engine._routing_rules.append(
    ContentRoutingRule(r'ERROR|EXCEPTION', ['error_handler'])
)

# Broadcast messages go to all agents
queue._routing_engine._routing_rules.append(
    TypeRoutingRule('broadcast', ['*'])
)
```

### Monitoring

```python
# Get real-time statistics
stats = await queue.get_statistics()
print(f"Queue Depth: {stats['queue_depth']}")
print(f"Throughput: {stats['throughput']['messages_per_minute']} msg/min")
print(f"P95 Latency: {stats['latency']['p95']} seconds")
print(f"Stuck Messages: {stats['stuck_count']}")
print(f"DLQ Size: {stats['dlq_count']}")

# Detect stuck messages
stuck = await queue.detect_stuck_messages(timeout_seconds=300)
for msg in stuck:
    print(f"Stuck message {msg.id} - processing for too long")
```

### Crash Recovery

```python
# On system startup
await queue.recover_from_crash()

# Create checkpoint for recovery
await queue.checkpoint()
```

### Dead Letter Queue

```python
# Reprocess a message from DLQ
success = await queue._dead_letter_queue.reprocess_message(message_id)

# Get DLQ size
dlq_count = await queue._dead_letter_queue.get_size()
```

## Configuration

### Environment Variables

```bash
# Queue Configuration
QUEUE_BATCH_SIZE=10              # Messages per dequeue
QUEUE_MAX_RETRIES=3              # Max retry attempts
QUEUE_DEFAULT_TIMEOUT=300        # Stuck detection timeout (seconds)

# Circuit Breaker
CIRCUIT_FAILURE_THRESHOLD=5      # Failures before opening
CIRCUIT_TIMEOUT=60               # Seconds before retry

# Monitoring
MONITOR_LATENCY_SAMPLES=1000    # Samples for percentiles
MONITOR_THROUGHPUT_WINDOW=60    # Throughput window (seconds)
```

### Priority Weights

```python
# Customize priority weights
queue.priority_weights = {
    'critical': 10000,  # Ultra high priority
    'high': 1000,
    'normal': 100,
    'low': 10
}
```

## Database Schema

### New Message Fields

```sql
-- Added to messages table
processing_started_at TIMESTAMP WITH TIME ZONE
retry_count INTEGER DEFAULT 0
max_retries INTEGER DEFAULT 3
backoff_seconds INTEGER DEFAULT 60
circuit_breaker_status VARCHAR(20)

-- New indexes
CREATE INDEX idx_message_processing_started ON messages(processing_started_at)
CREATE INDEX idx_message_retry_count ON messages(retry_count)
CREATE INDEX idx_message_dead_letter ON messages(status) WHERE status = 'dead_letter'
```

## Migration

Run the migration to add queue fields:

```bash
# Upgrade database
python migrations/add_message_queue_fields.py sqlite:///giljo_mcp.db upgrade

# Rollback if needed
python migrations/add_message_queue_fields.py sqlite:///giljo_mcp.db downgrade
```

## Performance Targets

- **Throughput**: 1000+ messages/minute
- **P95 Latency**: < 5 seconds
- **P99 Latency**: < 10 seconds
- **Crash Recovery**: < 30 seconds
- **Zero Message Loss**: Guaranteed via WAL

## Testing

Run the comprehensive test suite:

```bash
# Run all queue tests
pytest tests/test_message_queue.py -v

# Run specific test categories
pytest tests/test_message_queue.py::TestMessageQueue -v
pytest tests/test_message_queue.py::TestRoutingEngine -v
pytest tests/test_message_queue.py::TestACIDCompliance -v

# Run performance benchmarks
pytest tests/test_message_queue.py::test_queue_performance -v
```

## Troubleshooting

### Common Issues

1. **High Queue Depth**
   - Check agent availability
   - Review routing rules
   - Increase batch size
   - Scale agents horizontally

2. **Stuck Messages**
   - Check processing timeout settings
   - Review agent health
   - Check for deadlocks
   - Enable debug logging

3. **Circuit Breaker Open**
   - Check agent logs for errors
   - Review failure threshold
   - Manual reset if needed
   - Check network connectivity

4. **DLQ Growing**
   - Review message content
   - Check agent capabilities
   - Review retry logic
   - Manual intervention may be needed

### Debug Logging

```python
import logging

# Enable debug logging
logging.getLogger('giljo_mcp.queue').setLevel(logging.DEBUG)

# Log all queue operations
queue_logger = logging.getLogger('giljo_mcp.queue')
queue_logger.addHandler(logging.FileHandler('queue.log'))
```

## Best Practices

1. **Message Design**
   - Keep messages small and focused
   - Use appropriate priority levels
   - Include deadline for time-sensitive messages
   - Avoid circular dependencies

2. **Agent Design**
   - Process messages quickly
   - Acknowledge immediately
   - Complete or retry explicitly
   - Handle failures gracefully

3. **Monitoring**
   - Set up alerts for queue depth
   - Monitor stuck messages
   - Track error rates
   - Review DLQ regularly

4. **Scaling**
   - Horizontal scaling via multiple agents
   - Increase batch size for high throughput
   - Use routing rules to distribute load
   - Consider message partitioning

## API Integration

The MessageQueue integrates seamlessly with existing message tools:

- `send_message()` → `queue.enqueue()`
- `get_messages()` → `queue.dequeue()`
- `acknowledge_message()` → Automatic on dequeue
- `complete_message()` → Updates queue metrics
- `broadcast()` → Routes to all agents

## Future Enhancements

- [ ] Message partitioning for horizontal scaling
- [ ] Redis backend option for distributed queues
- [ ] WebSocket notifications for real-time updates
- [ ] Prometheus metrics export
- [ ] Message compression for large payloads
- [ ] Priority inheritance for related messages
- [ ] Scheduled message delivery
- [ ] Message batching for efficiency

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review test cases for examples
3. Enable debug logging
4. Contact the orchestrator team

---

*Last Updated: Project 3.2 Implementation*
*Version: 1.0.0*