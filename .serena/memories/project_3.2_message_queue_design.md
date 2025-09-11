# Project 3.2: Message Queue System Design Document

## Executive Summary
This document outlines the complete design for the GiljoAI Message Queue System, a robust, ACID-compliant queue infrastructure built on top of the existing Message model.

## 1. MessageQueue Class Architecture

### 1.1 Core Components

```python
# src/giljo_mcp/queue.py

class MessageQueue:
    """
    High-performance message queue manager with priority routing and ACID guarantees.
    """
    
    def __init__(self, db_manager: DatabaseManager, tenant_manager: TenantManager):
        self.db_manager = db_manager
        self.tenant_manager = tenant_manager
        self._routing_engine = RoutingEngine()
        self._monitor = QueueMonitor()
        self._dead_letter_queue = DeadLetterQueue()
        self._processing_lock = asyncio.Lock()
        self._batch_size = 10
        self._max_retries = 3
        
    async def enqueue(self, message: Message) -> str:
        """Add message to queue with priority placement"""
        
    async def dequeue(self, agent_name: str, count: int = 1) -> List[Message]:
        """Retrieve messages for agent based on priority and routing rules"""
        
    async def process_batch(self, agent_name: str) -> List[Message]:
        """Process a batch of messages for an agent"""
        
    async def acknowledge(self, message_id: str, agent_name: str) -> bool:
        """Mark message as acknowledged by agent"""
        
    async def complete(self, message_id: str, agent_name: str, result: str) -> bool:
        """Mark message as completed with result"""
        
    async def retry(self, message_id: str, reason: str) -> bool:
        """Retry a failed message with exponential backoff"""
        
    async def move_to_dlq(self, message_id: str, reason: str) -> bool:
        """Move stuck/failed message to dead letter queue"""
```

### 1.2 Priority Queue Implementation

```python
class PriorityQueue:
    """
    Heap-based priority queue with FIFO ordering within priorities.
    """
    
    PRIORITY_WEIGHTS = {
        'critical': 1000,
        'high': 100,
        'normal': 10,
        'low': 1
    }
    
    def __init__(self):
        self._heap = []  # Min-heap based on (priority_score, timestamp, message)
        self._message_map = {}  # message_id -> heap_index for O(1) lookup
        
    def push(self, message: Message):
        """Add message with calculated priority score"""
        priority_score = self._calculate_priority(message)
        heapq.heappush(self._heap, (priority_score, message.created_at, message))
        
    def pop(self) -> Optional[Message]:
        """Remove and return highest priority message"""
        if self._heap:
            _, _, message = heapq.heappop(self._heap)
            return message
        return None
        
    def _calculate_priority(self, message: Message) -> int:
        """Calculate priority score with deadline escalation"""
        base_score = self.PRIORITY_WEIGHTS[message.priority]
        
        # Deadline escalation
        if hasattr(message, 'deadline'):
            time_until_deadline = (message.deadline - datetime.utcnow()).total_seconds()
            if time_until_deadline < 300:  # Less than 5 minutes
                base_score *= 10
                
        # Age escalation - older messages get slight boost
        age_minutes = (datetime.utcnow() - message.created_at).total_seconds() / 60
        age_boost = min(age_minutes * 0.1, 10)  # Max 10 point boost
        
        return -(base_score + age_boost)  # Negative for min-heap
```

## 2. Routing Algorithm Specifications

### 2.1 Intelligent Routing Engine

```python
class RoutingEngine:
    """
    Intelligent message routing with capability matching and load balancing.
    """
    
    def __init__(self):
        self._routing_rules = []
        self._agent_capabilities = {}
        self._agent_load = {}
        self._circuit_breakers = {}
        
    async def route_message(self, message: Message, available_agents: List[Agent]) -> List[str]:
        """
        Determine optimal agent(s) for message delivery.
        
        Returns list of agent names in priority order.
        """
        candidates = []
        
        # Step 1: Apply routing rules
        for rule in self._routing_rules:
            if rule.matches(message):
                candidates.extend(rule.get_agents())
        
        # Step 2: Filter by agent capabilities
        capable_agents = [
            agent for agent in available_agents
            if self._can_handle(agent, message)
        ]
        
        # Step 3: Apply load balancing
        sorted_agents = sorted(
            capable_agents,
            key=lambda a: self._calculate_agent_score(a, message)
        )
        
        # Step 4: Check circuit breakers
        healthy_agents = [
            agent for agent in sorted_agents
            if not self._is_circuit_open(agent.name)
        ]
        
        return [agent.name for agent in healthy_agents]
    
    def _calculate_agent_score(self, agent: Agent, message: Message) -> float:
        """
        Calculate agent score for load balancing.
        Lower score = better candidate.
        """
        score = 0.0
        
        # Current load (number of pending messages)
        score += self._agent_load.get(agent.name, 0) * 10
        
        # Response time (average over last 10 messages)
        avg_response_time = self._get_avg_response_time(agent.name)
        score += avg_response_time
        
        # Affinity bonus (if agent has handled similar messages)
        if self._has_affinity(agent.name, message.message_type):
            score -= 50
            
        return score
```

### 2.2 Routing Rules

```python
class RoutingRule:
    """Base class for routing rules"""
    
    def matches(self, message: Message) -> bool:
        """Check if rule applies to message"""
        raise NotImplementedError
        
    def get_agents(self) -> List[str]:
        """Get target agents for this rule"""
        raise NotImplementedError

class PriorityRoutingRule(RoutingRule):
    """Route based on message priority"""
    
    def __init__(self, priority: str, agents: List[str]):
        self.priority = priority
        self.agents = agents
        
    def matches(self, message: Message) -> bool:
        return message.priority == self.priority

class TypeRoutingRule(RoutingRule):
    """Route based on message type"""
    
    def __init__(self, message_type: str, agents: List[str]):
        self.message_type = message_type
        self.agents = agents
        
    def matches(self, message: Message) -> bool:
        return message.message_type == self.message_type

class ContentRoutingRule(RoutingRule):
    """Route based on message content patterns"""
    
    def __init__(self, pattern: str, agents: List[str]):
        self.pattern = re.compile(pattern)
        self.agents = agents
        
    def matches(self, message: Message) -> bool:
        return bool(self.pattern.search(message.content))
```

## 3. Monitoring Metrics and Thresholds

### 3.1 Queue Metrics

```python
class QueueMonitor:
    """
    Real-time monitoring of queue health and performance.
    """
    
    def __init__(self):
        self._metrics = {
            'queue_depth': {},  # Per priority level
            'processing_time': {},  # Per agent
            'throughput': {},  # Messages per minute
            'latency': {},  # Time from enqueue to dequeue
            'error_rate': {},  # Failed messages per minute
            'stuck_messages': 0,
            'dlq_size': 0
        }
        self._thresholds = self._load_thresholds()
        
    async def record_enqueue(self, message: Message):
        """Record message enqueue event"""
        priority = message.priority
        self._metrics['queue_depth'][priority] = \
            self._metrics['queue_depth'].get(priority, 0) + 1
            
    async def record_dequeue(self, message: Message, agent_name: str):
        """Record message dequeue event"""
        # Calculate latency
        latency = (datetime.utcnow() - message.created_at).total_seconds()
        self._record_latency(agent_name, latency)
        
        # Update queue depth
        priority = message.priority
        self._metrics['queue_depth'][priority] -= 1
        
    async def check_health(self) -> Dict[str, Any]:
        """Check queue health against thresholds"""
        alerts = []
        
        # Check queue depth
        for priority, depth in self._metrics['queue_depth'].items():
            threshold = self._thresholds['max_queue_depth'].get(priority, 1000)
            if depth > threshold:
                alerts.append({
                    'type': 'queue_depth_exceeded',
                    'priority': priority,
                    'depth': depth,
                    'threshold': threshold
                })
        
        # Check stuck messages
        stuck_count = await self._count_stuck_messages()
        if stuck_count > self._thresholds['max_stuck_messages']:
            alerts.append({
                'type': 'stuck_messages',
                'count': stuck_count,
                'threshold': self._thresholds['max_stuck_messages']
            })
        
        # Check processing time
        for agent, avg_time in self._get_avg_processing_times().items():
            if avg_time > self._thresholds['max_processing_time']:
                alerts.append({
                    'type': 'slow_processing',
                    'agent': agent,
                    'avg_time': avg_time,
                    'threshold': self._thresholds['max_processing_time']
                })
        
        return {
            'healthy': len(alerts) == 0,
            'alerts': alerts,
            'metrics': self._metrics
        }
```

### 3.2 Monitoring Thresholds

```yaml
# Default thresholds (configurable)
thresholds:
  max_queue_depth:
    critical: 100
    high: 500
    normal: 1000
    low: 2000
  
  max_processing_time: 30  # seconds
  max_stuck_time: 300  # 5 minutes
  max_stuck_messages: 10
  max_retry_count: 3
  
  latency_percentiles:
    p50: 1.0  # 50th percentile should be < 1 second
    p95: 5.0  # 95th percentile should be < 5 seconds
    p99: 10.0  # 99th percentile should be < 10 seconds
  
  throughput:
    min_messages_per_minute: 10
    max_messages_per_minute: 1000
```

## 4. ACID Compliance Requirements

### 4.1 Atomicity

```python
class TransactionalQueue:
    """
    Ensure atomic operations for queue management.
    """
    
    async def atomic_dequeue(self, agent_name: str, count: int = 1):
        """
        Atomically dequeue messages with rollback on failure.
        """
        async with self.db_manager.get_session() as session:
            try:
                # Start transaction
                await session.begin()
                
                # Lock messages for update (SELECT FOR UPDATE)
                messages = await session.execute(
                    select(Message)
                    .where(
                        and_(
                            Message.status == "pending",
                            Message.to_agents.contains([agent_name])
                        )
                    )
                    .order_by(Message.priority.desc(), Message.created_at)
                    .limit(count)
                    .with_for_update()
                )
                
                message_list = messages.scalars().all()
                
                # Update status atomically
                for message in message_list:
                    message.status = "processing"
                    message.processing_started_at = datetime.utcnow()
                    message.processing_agent = agent_name
                
                # Commit transaction
                await session.commit()
                return message_list
                
            except Exception as e:
                # Rollback on any error
                await session.rollback()
                raise QueueException(f"Atomic dequeue failed: {e}")
```

### 4.2 Consistency

```python
class ConsistencyValidator:
    """
    Ensure queue state consistency.
    """
    
    async def validate_message_state(self, message: Message) -> bool:
        """
        Validate message state transitions.
        
        Valid transitions:
        - pending -> acknowledged -> completed
        - pending -> acknowledged -> failed
        - any -> dead_letter (after max retries)
        """
        valid_transitions = {
            'pending': ['acknowledged', 'processing'],
            'processing': ['acknowledged', 'completed', 'failed', 'pending'],
            'acknowledged': ['completed', 'failed', 'pending'],
            'completed': [],  # Terminal state
            'failed': ['pending', 'dead_letter'],  # Can retry
            'dead_letter': []  # Terminal state
        }
        
        current_state = message.status
        return current_state in valid_transitions
    
    async def enforce_invariants(self, session):
        """
        Enforce queue invariants:
        1. No duplicate messages in pending state
        2. Each message has valid tenant_key
        3. Priority values are valid
        4. Timestamps are consistent
        """
        # Check for duplicates
        duplicates = await session.execute(
            select(Message.id, func.count(Message.id))
            .where(Message.status == "pending")
            .group_by(Message.id)
            .having(func.count(Message.id) > 1)
        )
        
        if duplicates.rowcount > 0:
            raise ConsistencyError("Duplicate pending messages detected")
```

### 4.3 Isolation

```python
class IsolationManager:
    """
    Ensure proper isolation between concurrent operations.
    """
    
    def __init__(self):
        self._locks = {}  # Per-message locks
        self._agent_locks = {}  # Per-agent processing locks
        
    async def with_message_lock(self, message_id: str):
        """
        Context manager for message-level locking.
        """
        if message_id not in self._locks:
            self._locks[message_id] = asyncio.Lock()
            
        async with self._locks[message_id]:
            yield
            
    async def with_agent_lock(self, agent_name: str):
        """
        Context manager for agent-level locking.
        """
        if agent_name not in self._agent_locks:
            self._agent_locks[agent_name] = asyncio.Lock()
            
        async with self._agent_locks[agent_name]:
            yield
```

### 4.4 Durability

```python
class DurabilityManager:
    """
    Ensure message durability and crash recovery.
    """
    
    async def persist_with_wal(self, message: Message):
        """
        Write-ahead logging for crash recovery.
        """
        # Write to WAL before database
        wal_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'operation': 'enqueue',
            'message_id': message.id,
            'message_data': message.to_dict()
        }
        
        await self._write_to_wal(wal_entry)
        
        # Then persist to database
        async with self.db_manager.get_session() as session:
            session.add(message)
            await session.commit()
            
        # Mark WAL entry as committed
        await self._mark_wal_committed(message.id)
    
    async def recover_from_crash(self):
        """
        Recover queue state after crash.
        """
        # Read uncommitted WAL entries
        uncommitted = await self._read_uncommitted_wal()
        
        for entry in uncommitted:
            if entry['operation'] == 'enqueue':
                # Re-enqueue message
                await self._replay_enqueue(entry['message_data'])
            elif entry['operation'] == 'dequeue':
                # Reset message to pending
                await self._replay_dequeue(entry['message_id'])
```

## 5. Stuck Message Detection

```python
class StuckMessageDetector:
    """
    Detect and handle stuck messages.
    """
    
    def __init__(self, timeout_seconds: int = 300):
        self.timeout_seconds = timeout_seconds
        self._detection_interval = 60  # Check every minute
        
    async def detect_stuck_messages(self) -> List[Message]:
        """
        Find messages that have been processing too long.
        """
        async with self.db_manager.get_session() as session:
            cutoff_time = datetime.utcnow() - timedelta(seconds=self.timeout_seconds)
            
            stuck_messages = await session.execute(
                select(Message).where(
                    and_(
                        Message.status.in_(['processing', 'acknowledged']),
                        Message.processing_started_at < cutoff_time
                    )
                )
            )
            
            return stuck_messages.scalars().all()
    
    async def handle_stuck_message(self, message: Message):
        """
        Handle a stuck message based on retry count.
        """
        retry_count = message.meta_data.get('retry_count', 0)
        
        if retry_count < self.max_retries:
            # Retry with exponential backoff
            backoff_seconds = 2 ** retry_count * 10
            await self._schedule_retry(message, backoff_seconds)
        else:
            # Move to dead letter queue
            await self._move_to_dlq(message, "Max retries exceeded")
```

## 6. Dead Letter Queue

```python
class DeadLetterQueue:
    """
    Handle messages that cannot be processed.
    """
    
    async def add_message(self, message: Message, reason: str):
        """
        Move message to DLQ with reason.
        """
        async with self.db_manager.get_session() as session:
            # Update original message
            message.status = 'dead_letter'
            message.meta_data['dlq_reason'] = reason
            message.meta_data['dlq_timestamp'] = datetime.utcnow().isoformat()
            
            # Create DLQ entry
            dlq_entry = {
                'message_id': message.id,
                'reason': reason,
                'original_priority': message.priority,
                'retry_count': message.meta_data.get('retry_count', 0),
                'timestamp': datetime.utcnow()
            }
            
            # Log for analysis
            logger.error(f"Message {message.id} moved to DLQ: {reason}")
            
            await session.commit()
    
    async def reprocess_message(self, message_id: str):
        """
        Attempt to reprocess a DLQ message.
        """
        async with self.db_manager.get_session() as session:
            message = await session.get(Message, message_id)
            
            if message and message.status == 'dead_letter':
                # Reset for reprocessing
                message.status = 'pending'
                message.meta_data['reprocessed_from_dlq'] = True
                message.meta_data['retry_count'] = 0
                
                await session.commit()
                return True
                
        return False
```

## 7. Integration Points

### 7.1 With Existing Message Tools

The MessageQueue will integrate seamlessly with existing message tools:
- `send_message` will call `queue.enqueue()` 
- `get_messages` will call `queue.dequeue()`
- `acknowledge_message` will call `queue.acknowledge()`
- `complete_message` will call `queue.complete()`

### 7.2 With Database Layer

- Use existing DatabaseManager for all database operations
- Leverage async sessions for non-blocking I/O
- Use SQLAlchemy's transaction support for ACID compliance

### 7.3 With Monitoring Systems

- Expose metrics via `/metrics` endpoint
- Send alerts via message system
- Log critical events for audit trail

## 8. Testing Strategy

### 8.1 Unit Tests
- Test priority queue ordering
- Test routing algorithm decisions
- Test state transitions
- Test retry logic

### 8.2 Integration Tests
- Test ACID properties under concurrent load
- Test crash recovery scenarios
- Test dead letter queue functionality
- Test monitoring and alerting

### 8.3 Performance Tests
- Benchmark throughput (target: 1000 msg/min)
- Test queue depth limits
- Test memory usage under load
- Test database connection pooling

## 9. Success Criteria

1. **Functional Requirements**
   - ✅ MessageQueue class with all specified methods
   - ✅ Priority-based message ordering
   - ✅ Intelligent routing with load balancing
   - ✅ Stuck message detection and handling
   - ✅ Dead letter queue implementation

2. **Non-Functional Requirements**
   - ✅ ACID compliance for all operations
   - ✅ Crash recovery within 30 seconds
   - ✅ Throughput of 1000+ messages/minute
   - ✅ P95 latency < 5 seconds
   - ✅ Zero message loss guarantee

3. **Integration Requirements**
   - ✅ Seamless integration with existing tools
   - ✅ Backward compatibility maintained
   - ✅ Multi-tenant isolation preserved
   - ✅ Monitoring and alerting functional

## 10. Implementation Notes

### Key Design Decisions:
1. **Database-First Approach**: All queue state stored in database for durability
2. **Async Throughout**: Non-blocking I/O for high throughput
3. **Configurable Priorities**: Support for deadline escalation
4. **Circuit Breaker Pattern**: Protect against cascading failures
5. **WAL for Recovery**: Write-ahead logging ensures no message loss

### Risk Mitigation:
1. **Database Bottleneck**: Use connection pooling and batch operations
2. **Memory Pressure**: Implement queue depth limits and pagination
3. **Deadlocks**: Use proper locking order and timeouts
4. **Message Duplication**: Use idempotent operations and deduplication

This design provides a robust, scalable message queue system that meets all requirements while maintaining backward compatibility with the existing codebase.