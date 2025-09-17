"""
WebSocket Test Configuration
Central configuration for all WebSocket integration tests
"""

import os
from pathlib import Path
from typing import Any, Optional


# Environment-based configuration
ENV = os.getenv("TEST_ENV", "local")

# Base URLs
BASE_CONFIGS = {
    "local": {
        "ws_url": "ws://localhost:8000/ws",
        "api_url": "http://localhost:8000",
        "frontend_url": "http://localhost:6000",
        "mock_ws_port": 8001,
    },
    "ci": {
        "ws_url": "ws://localhost:8000/ws",
        "api_url": "http://localhost:8000",
        "frontend_url": "http://localhost:6000",
        "mock_ws_port": 8001,
    },
    "staging": {
        "ws_url": "ws://staging.giljoai.local:8000/ws",
        "api_url": "http://staging.giljoai.local:8000",
        "frontend_url": "http://staging.giljoai.local:6000",
        "mock_ws_port": 8001,
    },
}

# Get config for current environment
CONFIG = BASE_CONFIGS.get(ENV, BASE_CONFIGS["local"])

# Test timeouts (in seconds)
TIMEOUTS = {"connection": 5.0, "message": 1.0, "reconnect": 10.0, "operation": 30.0, "load_test": 60.0}

# Performance SLAs
PERFORMANCE_SLAS = {
    "max_latency_ms": 100,  # Agent status updates must be <100ms
    "p95_latency_ms": 50,  # 95% of messages under 50ms
    "reconnect_time_s": 5,  # Must reconnect within 5 seconds
    "throughput_msgs_per_sec": 500,  # Minimum throughput
    "connection_success_rate": 0.99,  # 99% connection success
}

# Reconnection settings
RECONNECT_CONFIG = {
    "initial_delay": 1.0,  # 1 second
    "backoff_multiplier": 2.0,
    "max_delay": 30.0,  # Cap at 30 seconds
    "max_attempts": 5,
    "jitter": 0.1,  # 10% jitter
}

# Test data
TEST_CLIENTS = {
    "client_1": {"id": "test_client_001", "api_key": "test_key_001", "role": "admin"},
    "client_2": {"id": "test_client_002", "api_key": "test_key_002", "role": "user"},
    "load_test": {"id_prefix": "load_client_", "count": 20, "api_key": "load_test_key"},
}

# Message templates
MESSAGE_TEMPLATES = {
    "agent_status": {
        "type": "agent_status_update",
        "agent_id": "{{agent_id}}",
        "old_status": "{{old_status}}",
        "new_status": "{{new_status}}",
        "timestamp": "{{timestamp}}",
    },
    "new_message": {
        "type": "new_message",
        "id": "{{message_id}}",
        "from": "{{from_agent}}",
        "to": "{{to_agent}}",
        "content": "{{content}}",
        "timestamp": "{{timestamp}}",
    },
    "progress": {
        "type": "progress",
        "operation_id": "{{operation_id}}",
        "percentage": "{{percentage}}",
        "message": "{{message}}",
        "timestamp": "{{timestamp}}",
    },
    "error": {
        "type": "error",
        "error_code": "{{error_code}}",
        "message": "{{message}}",
        "details": "{{details}}",
        "timestamp": "{{timestamp}}",
    },
    "broadcast": {
        "type": "broadcast",
        "channel": "{{channel}}",
        "content": "{{content}}",
        "timestamp": "{{timestamp}}",
    },
}

# Network simulation presets
NETWORK_PROFILES = {
    "perfect": {"latency_ms": 0, "jitter_ms": 0, "packet_loss": 0.0, "bandwidth_kbps": None},  # Unlimited
    "good": {"latency_ms": 20, "jitter_ms": 5, "packet_loss": 0.001, "bandwidth_kbps": 10000},  # 0.1%  # 10 Mbps
    "moderate": {"latency_ms": 100, "jitter_ms": 20, "packet_loss": 0.01, "bandwidth_kbps": 1000},  # 1%  # 1 Mbps
    "poor": {"latency_ms": 500, "jitter_ms": 100, "packet_loss": 0.05, "bandwidth_kbps": 100},  # 5%  # 100 kbps
    "unstable": {"latency_ms": 200, "jitter_ms": 150, "packet_loss": 0.10, "bandwidth_kbps": 500},  # 10%
}

# Test scenarios
TEST_SCENARIOS = {
    "basic_connection": {"clients": 1, "duration": 10, "message_rate": 1, "network": "perfect"},  # msgs per second
    "multi_client": {"clients": 10, "duration": 30, "message_rate": 5, "network": "good"},
    "high_load": {"clients": 50, "duration": 60, "message_rate": 20, "network": "good"},
    "resilience": {
        "clients": 5,
        "duration": 120,
        "message_rate": 2,
        "network": "unstable",
        "disconnections": 3,  # Simulate 3 disconnections
    },
    "broadcast_storm": {
        "clients": 20,
        "duration": 30,
        "message_rate": 10,
        "broadcast_rate": 5,  # Broadcasts per second
        "network": "moderate",
    },
}

# Logging configuration
LOGGING = {
    "level": "INFO",  # DEBUG, INFO, WARNING, ERROR
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "file": "tests/logs/websocket_tests.log",
    "console": True,
}

# Validation rules
VALIDATION_RULES = {
    "message_size_limit": 65536,  # 64KB max message size
    "client_id_pattern": r"^[a-zA-Z0-9_-]+$",
    "api_key_length": 32,
    "max_reconnect_attempts": 10,
    "heartbeat_interval": 30,  # seconds
    "heartbeat_timeout": 60,  # seconds
}

# Test fixtures and mocks
MOCK_DATA = {
    "agents": [
        {"id": "agent_001", "name": "ws_implementer", "status": "pending"},
        {"id": "agent_002", "name": "frontend_implementer", "status": "pending"},
        {"id": "agent_003", "name": "integration_tester", "status": "in_progress"},
    ],
    "projects": [
        {"id": "proj_001", "name": "WebSocket Integration", "status": "active"},
        {"id": "proj_002", "name": "Real-time Dashboard", "status": "pending"},
    ],
    "messages": [
        {"id": "msg_001", "content": "Test message 1", "from": "agent_001", "to": "agent_002"},
        {"id": "msg_002", "content": "Test message 2", "from": "agent_002", "to": "agent_003"},
    ],
}


# Helper functions
def get_test_config(scenario: Optional[str] = None) -> dict[str, Any]:
    """Get configuration for a specific test scenario"""
    base_config = CONFIG.copy()

    if scenario and scenario in TEST_SCENARIOS:
        base_config.update(TEST_SCENARIOS[scenario])

    return base_config


def get_network_profile(profile: str = "perfect") -> dict[str, Any]:
    """Get network simulation profile"""
    return NETWORK_PROFILES.get(profile, NETWORK_PROFILES["perfect"])


def get_message_template(msg_type: str) -> dict[str, Any]:
    """Get message template by type"""
    return MESSAGE_TEMPLATES.get(msg_type, {})


def validate_client_id(client_id: str) -> bool:
    """Validate client ID format"""
    import re

    pattern = VALIDATION_RULES["client_id_pattern"]
    return bool(re.match(pattern, client_id))


def get_test_client_config(client_name: str = "client_1") -> dict[str, Any]:
    """Get test client configuration"""
    return TEST_CLIENTS.get(client_name, TEST_CLIENTS["client_1"])


# Environment setup
def setup_test_environment():
    """Setup test environment"""
    # Create log directory if needed
    log_dir = Path(LOGGING["file"]).parent
    log_dir.mkdir(parents=True, exist_ok=True)

    # Set up logging
    import logging

    logging.basicConfig(
        level=getattr(logging, LOGGING["level"]),
        format=LOGGING["format"],
        handlers=[
            logging.FileHandler(LOGGING["file"]),
            logging.StreamHandler() if LOGGING["console"] else logging.NullHandler(),
        ],
    )

    return True


# Export configuration
__all__ = [
    "CONFIG",
    "LOGGING",
    "MESSAGE_TEMPLATES",
    "MOCK_DATA",
    "NETWORK_PROFILES",
    "PERFORMANCE_SLAS",
    "RECONNECT_CONFIG",
    "TEST_CLIENTS",
    "TEST_SCENARIOS",
    "TIMEOUTS",
    "VALIDATION_RULES",
    "get_message_template",
    "get_network_profile",
    "get_test_client_config",
    "get_test_config",
    "setup_test_environment",
    "validate_client_id",
]
