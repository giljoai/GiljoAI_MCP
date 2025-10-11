# UI-Analyzer Message Monitor

This directory contains continuous monitoring scripts for the ui-analyzer agent messages from AKE-MCP.

## Files

### `monitor_ake_mcp.py` (Production Monitor)

The main production-ready monitor that:

- Checks for ui-analyzer messages every 10 seconds
- Integrates with real AKE-MCP tools via `mcp__ake-mcp-v2__get_messages`
- Processes messages by priority (normal, high, urgent)
- Acknowledges received messages using `mcp__ake-mcp-v2__acknowledge_message`
- Logs all activity with timestamps
- Provides session summaries on shutdown

### `monitor_simple.py` (Simple Demo)

A simplified version for testing and demonstration.

### `ui_analyzer_monitor_mcp.py` (Full-Featured)

Complete implementation with advanced logging and error handling.

### `continuous_ui_monitor.py` (Windows Version)

Windows-compatible version (had Unicode issues, replaced by monitor_ake_mcp.py).

## Usage

### Start Monitoring

```bash
python monitor_ake_mcp.py
```

### Background Monitoring

```bash
python monitor_ake_mcp.py &
```

### Stop Monitoring

Press `Ctrl+C` to stop gracefully.

## Features

### Message Priority Processing

- **URGENT**: Immediate escalation protocol
- **HIGH**: Priority processing queue
- **NORMAL**: Standard processing queue

### Real-time Logging

- Timestamped log entries
- Priority-based message formatting
- Session statistics
- Error handling and reporting

### MCP Integration

- Queries AKE-MCP server for messages
- Acknowledges processed messages
- Handles connection errors gracefully

## Monitor Output Example

```
[2025-09-14 02:45:05] INFO: AKE-MCP UI-Analyzer Message Monitor Started
[2025-09-14 02:45:05] INFO: Agent: ui-analyzer
[2025-09-14 02:45:05] INFO: Check interval: 10 seconds
======================================================================
[2025-09-14 02:45:05] INFO: Check #1: Querying AKE-MCP for ui-analyzer messages...
[2025-09-14 02:45:15] HIGH: HIGH PRIORITY [msg_12345] from analyzer
[2025-09-14 02:45:15] HIGH: Content: Check color contrast compliance
[2025-09-14 02:45:15] INFO: ACKNOWLEDGED: Message msg_12345
```

## Configuration

### Default Settings

- **Agent**: ui-analyzer
- **Check Interval**: 10 seconds
- **Priority Levels**: normal, high, urgent
- **Output**: Console with timestamps

### Customization

Edit the monitor script to modify:

- Check interval (`self.check_interval`)
- Agent name (`self.agent_name`)
- Priority handling logic
- Logging format

## Integration Points

### AKE-MCP Tools Used

1. `mcp__ake-mcp-v2__get_messages` - Retrieve pending messages
2. `mcp__ake-mcp-v2__acknowledge_message` - Acknowledge processed messages

### Message Processing Flow

1. Query AKE-MCP for messages
2. Filter for ui-analyzer agent
3. Process by priority level
4. Execute appropriate handling logic
5. Acknowledge message receipt
6. Log activity and continue monitoring

## Error Handling

The monitor includes comprehensive error handling for:

- MCP connection failures
- Message processing errors
- Acknowledgment failures
- Unexpected shutdowns

## Session Management

### Statistics Tracked

- Total checks performed
- Messages processed
- Session uptime
- Average checks per minute

### Graceful Shutdown

- Logs session summary
- Reports final statistics
- Handles Ctrl+C interruption
