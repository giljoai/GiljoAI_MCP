# GiljoAI MCP Mode Testing Strategy

**Document Version:** 1.0
**Date:** 2025-10-04
**Prepared by:** Backend Integration Tester Agent
**Purpose:** Define comprehensive testing strategy for server mode deployment validation

---

## Executive Summary

This document provides a comprehensive testing strategy for validating GiljoAI MCP's **server mode deployment**, which enables network-accessible multi-agent orchestration with API key authentication. The strategy covers network connectivity, remote access, security, performance, and multi-tenant isolation under production-like conditions.

### Current Status Assessment

**Localhost Mode Testing:** ✅ Comprehensive
**Server Mode Testing:** ⚠️ Partial - Gaps Identified
**Network Testing:** ❌ Missing
**Remote Access Testing:** ❌ Missing

---

## 1. Current Test Coverage Assessment

### 1.1 Strengths (Existing Coverage)

#### Excellent Localhost Testing Infrastructure
- **Location:** `tests/integration/`, `tests/performance/`, `tests/unit/`
- **Coverage:**
  - API endpoints (REST)
  - WebSocket connections (localhost)
  - Database operations (PostgreSQL)
  - Multi-tenant isolation
  - Performance benchmarks (100+ agents, 10K+ messages/min)
  - Authentication (JWT, API keys - basic)

#### Robust Performance Testing Framework
- **Location:** `tests/performance/`
- **Features:**
  - Concurrent agent spawning (100+)
  - Message queue load tests (10K+ messages/min)
  - WebSocket stress tests (100+ connections)
  - Database benchmarks (sub-100ms operations)
  - Vision chunking (50K+ tokens)
  - Multi-tenant load tests

#### Security Testing Foundation
- **Location:** `tests/test_api_security.py`, `tests/integration/test_auth.py`
- **Coverage:**
  - SQL injection protection
  - XSS protection
  - CORS configuration
  - JWT token validation
  - API key authentication (basic)

### 1.2 Critical Gaps for Server Mode

#### Network Accessibility Testing
- ❌ Remote API connection tests (LAN/WAN)
- ❌ Network firewall traversal validation
- ❌ DNS resolution for server deployments
- ❌ Cross-network latency measurements
- ❌ Network failure recovery testing

#### Remote WebSocket Testing
- ❌ WebSocket connections from remote clients
- ❌ WebSocket over different network segments
- ❌ WebSocket reconnection from remote locations
- ❌ Load balancing for WebSocket traffic

#### API Key Authentication (Server Mode Specific)
- ❌ API key enforcement in server mode
- ❌ Key-based rate limiting
- ❌ Key rotation procedures
- ❌ Key permissions validation
- ❌ Compromised key detection

#### Security Hardening
- ❌ TLS/SSL certificate validation
- ❌ Certificate expiration handling
- ❌ HTTPS enforcement tests
- ❌ Security header validation (production)
- ❌ DDoS protection mechanisms
- ❌ Brute-force attack mitigation

#### Multi-User Concurrent Access
- ❌ Multiple remote clients simultaneously
- ❌ User session management
- ❌ Concurrent tenant isolation under network load
- ❌ Resource fairness across network clients

#### Database Network Configuration
- ❌ PostgreSQL remote access validation
- ❌ Connection pool exhaustion under network load
- ❌ Database firewall rules testing
- ❌ SSL/TLS for database connections

---

## 2. Server Mode Test Requirements

### 2.1 Network Connectivity Tests

**Objective:** Validate API and WebSocket accessibility from remote clients

#### Test Scenarios

```python
# tests/integration/test_network_connectivity.py

import pytest
import httpx
import websockets
from typing import List

class TestNetworkConnectivity:
    """Test network accessibility in server mode"""

    @pytest.fixture
    def server_config(self):
        """Server mode configuration"""
        return {
            "mode": "server",
            "api_host": "0.0.0.0",  # Bind to all interfaces
            "api_port": 7272,
            "websocket_port": 6003,
            "ssl_enabled": False  # Initially test without SSL
        }

    @pytest.mark.asyncio
    async def test_api_accessible_from_localhost(self, server_config):
        """Test API is accessible from localhost (sanity check)"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"http://localhost:{server_config['api_port']}/health"
            )
            assert response.status_code == 200
            data = response.json()
            assert data["status"] in ["healthy", "degraded"]

    @pytest.mark.asyncio
    async def test_api_accessible_from_lan_ip(self, server_config, local_ip):
        """Test API is accessible from LAN IP address"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"http://{local_ip}:{server_config['api_port']}/health",
                timeout=5.0
            )
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_websocket_accessible_from_lan_ip(self, server_config, local_ip):
        """Test WebSocket is accessible from LAN IP address"""
        ws_uri = f"ws://{local_ip}:{server_config['websocket_port']}/ws"

        try:
            async with websockets.connect(ws_uri, timeout=5.0) as ws:
                # Send ping
                await ws.send('{"type": "ping"}')
                response = await ws.recv()
                assert "pong" in response.lower()
        except Exception as e:
            pytest.fail(f"WebSocket connection failed: {e}")

    @pytest.mark.asyncio
    async def test_api_request_from_multiple_lan_clients(
        self, server_config, lan_client_ips: List[str]
    ):
        """Test API handles requests from multiple LAN clients"""
        tasks = []

        for client_ip in lan_client_ips:
            async with httpx.AsyncClient() as client:
                task = client.get(
                    f"http://{server_config['api_host']}:{server_config['api_port']}/health"
                )
                tasks.append(task)

        responses = await asyncio.gather(*tasks, return_exceptions=True)

        success_count = sum(1 for r in responses if isinstance(r, httpx.Response) and r.status_code == 200)
        assert success_count >= len(lan_client_ips) * 0.95  # 95% success rate

    @pytest.mark.asyncio
    async def test_network_latency_measurements(self, server_config):
        """Measure network latency for remote API calls"""
        latencies = []

        async with httpx.AsyncClient() as client:
            for _ in range(50):
                start = time.perf_counter()
                response = await client.get(
                    f"http://{server_config['api_host']}:{server_config['api_port']}/health"
                )
                latency_ms = (time.perf_counter() - start) * 1000

                if response.status_code == 200:
                    latencies.append(latency_ms)

        avg_latency = sum(latencies) / len(latencies)
        p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]

        # Network latency targets
        assert avg_latency < 50.0  # Average < 50ms for LAN
        assert p95_latency < 100.0  # P95 < 100ms
```

### 2.2 Remote API Access Tests

**Objective:** Validate end-to-end workflows from remote clients

```python
# tests/integration/test_remote_api_workflows.py

class TestRemoteAPIWorkflows:
    """Test complete workflows from remote clients"""

    @pytest.mark.asyncio
    async def test_remote_project_creation_workflow(
        self, remote_api_client, api_key
    ):
        """Test creating a project from a remote client"""
        headers = {"X-API-Key": api_key}

        # Create project
        project_data = {
            "name": "Remote Test Project",
            "mission": "Testing remote access",
            "agents": ["analyzer", "implementer"]
        }

        response = await remote_api_client.post(
            "/api/v1/projects/",
            json=project_data,
            headers=headers,
            timeout=10.0
        )

        assert response.status_code == 200
        project = response.json()
        assert "id" in project
        project_id = project["id"]

        # Verify project was created
        response = await remote_api_client.get(
            f"/api/v1/projects/{project_id}",
            headers=headers
        )
        assert response.status_code == 200

        return project_id

    @pytest.mark.asyncio
    async def test_remote_agent_spawning(
        self, remote_api_client, api_key, remote_project_id
    ):
        """Test spawning agents from remote client"""
        headers = {"X-API-Key": api_key}

        agent_data = {
            "project_id": remote_project_id,
            "agent_name": "remote_test_agent",
            "mission": "Testing remote agent spawn"
        }

        response = await remote_api_client.post(
            "/api/v1/agents/",
            json=agent_data,
            headers=headers
        )

        assert response.status_code == 200
        agent = response.json()
        assert agent["name"] == "remote_test_agent"

    @pytest.mark.asyncio
    async def test_remote_message_sending(
        self, remote_api_client, api_key, remote_project_id
    ):
        """Test sending messages from remote client"""
        headers = {"X-API-Key": api_key}

        message_data = {
            "to_agents": ["remote_test_agent"],
            "content": "Test message from remote client",
            "project_id": remote_project_id,
            "message_type": "direct",
            "priority": "high"
        }

        response = await remote_api_client.post(
            "/api/v1/messages/send",
            json=message_data,
            headers=headers
        )

        assert response.status_code == 200
```

### 2.3 Security Testing (Server Mode Specific)

**Objective:** Validate security measures for network-exposed API

```python
# tests/integration/test_server_mode_security.py

class TestServerModeSecurity:
    """Security tests specific to server mode deployment"""

    @pytest.mark.asyncio
    async def test_api_key_required_in_server_mode(self, remote_api_client):
        """Test that API key is required when in server mode"""
        # Request without API key
        response = await remote_api_client.get("/api/v1/projects/")

        # Should be rejected with 401 Unauthorized
        assert response.status_code == 401
        error = response.json()
        assert "api key" in error["detail"].lower() or "unauthorized" in error["detail"].lower()

    @pytest.mark.asyncio
    async def test_invalid_api_key_rejected(self, remote_api_client):
        """Test that invalid API keys are rejected"""
        headers = {"X-API-Key": "invalid_key_12345"}

        response = await remote_api_client.get(
            "/api/v1/projects/",
            headers=headers
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_api_key_rate_limiting(
        self, remote_api_client, rate_limited_api_key
    ):
        """Test rate limiting per API key"""
        headers = {"X-API-Key": rate_limited_api_key}

        # Make requests exceeding rate limit
        responses = []
        for _ in range(20):
            response = await remote_api_client.get(
                "/api/v1/projects/",
                headers=headers
            )
            responses.append(response.status_code)

        # Should see at least one 429 Too Many Requests
        assert 429 in responses

    @pytest.mark.asyncio
    async def test_api_key_permissions_enforcement(
        self, remote_api_client, read_only_api_key
    ):
        """Test that API key permissions are enforced"""
        headers = {"X-API-Key": read_only_api_key}

        # GET should work
        response = await remote_api_client.get(
            "/api/v1/projects/",
            headers=headers
        )
        assert response.status_code == 200

        # POST should be denied
        project_data = {
            "name": "Test",
            "mission": "Test",
            "agents": []
        }

        response = await remote_api_client.post(
            "/api/v1/projects/",
            json=project_data,
            headers=headers
        )

        assert response.status_code == 403  # Forbidden

    @pytest.mark.asyncio
    async def test_tenant_isolation_with_api_keys(
        self, remote_api_client, tenant1_api_key, tenant2_api_key
    ):
        """Test that API keys enforce tenant isolation"""
        # Create project with tenant 1 key
        headers1 = {"X-API-Key": tenant1_api_key}
        project_data = {
            "name": "Tenant 1 Project",
            "mission": "Test",
            "agents": []
        }

        response = await remote_api_client.post(
            "/api/v1/projects/",
            json=project_data,
            headers=headers1
        )
        assert response.status_code == 200
        tenant1_project_id = response.json()["id"]

        # Try to access with tenant 2 key
        headers2 = {"X-API-Key": tenant2_api_key}
        response = await remote_api_client.get(
            f"/api/v1/projects/{tenant1_project_id}",
            headers=headers2
        )

        # Should be denied (404 or 403)
        assert response.status_code in [403, 404]

    @pytest.mark.asyncio
    async def test_brute_force_protection(self, remote_api_client):
        """Test protection against brute force API key attacks"""
        failed_attempts = 0

        for i in range(50):
            headers = {"X-API-Key": f"invalid_key_{i}"}
            response = await remote_api_client.get(
                "/api/v1/projects/",
                headers=headers
            )

            if response.status_code == 401:
                failed_attempts += 1
            elif response.status_code == 429:
                # Rate limited after too many failed attempts
                break

        # Should be rate limited after many failures
        assert failed_attempts < 50  # Rate limiting kicked in
```

### 2.4 Performance Testing (Network Scenarios)

**Objective:** Validate performance under network conditions

```python
# tests/performance/test_network_performance.py

class TestNetworkPerformance:
    """Performance tests for network-based access"""

    @pytest.mark.asyncio
    async def test_concurrent_remote_clients_50(
        self, server_config, api_keys: List[str]
    ):
        """Test 50 concurrent remote API clients"""
        clients = []

        for api_key in api_keys[:50]:
            clients.append(httpx.AsyncClient())

        try:
            tasks = []
            for i, client in enumerate(clients):
                headers = {"X-API-Key": api_keys[i]}
                task = client.get(
                    f"http://{server_config['api_host']}:{server_config['api_port']}/health",
                    headers=headers
                )
                tasks.append(task)

            start = time.perf_counter()
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            duration = time.perf_counter() - start

            success_count = sum(
                1 for r in responses
                if isinstance(r, httpx.Response) and r.status_code == 200
            )

            assert success_count >= 45  # 90% success rate
            assert duration < 5.0  # All requests complete in < 5s

        finally:
            for client in clients:
                await client.aclose()

    @pytest.mark.asyncio
    async def test_websocket_connections_from_remote_clients_100(
        self, server_config, websocket_uris: List[str]
    ):
        """Test 100 concurrent WebSocket connections from remote clients"""
        connections = []
        connection_times = []

        try:
            for uri in websocket_uris[:100]:
                start = time.perf_counter()
                ws = await websockets.connect(uri, timeout=10.0)
                connection_time = (time.perf_counter() - start) * 1000

                connections.append(ws)
                connection_times.append(connection_time)

            success_rate = len(connections) / 100 * 100
            avg_connection_time = sum(connection_times) / len(connection_times)

            assert success_rate >= 80.0  # 80% success rate
            assert avg_connection_time < 2000.0  # < 2s average

        finally:
            for ws in connections:
                await ws.close()

    @pytest.mark.asyncio
    async def test_database_performance_with_network_clients(
        self, db_manager, remote_api_clients: List[httpx.AsyncClient]
    ):
        """Test database performance under network load"""
        # Simulate 30 remote clients creating projects simultaneously
        tasks = []

        for i, client in enumerate(remote_api_clients[:30]):
            project_data = {
                "name": f"Network Test Project {i}",
                "mission": "Testing database under network load",
                "agents": ["analyzer"]
            }

            headers = {"X-API-Key": f"test_key_{i}"}
            task = client.post(
                "/api/v1/projects/",
                json=project_data,
                headers=headers
            )
            tasks.append(task)

        start = time.perf_counter()
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        duration = (time.perf_counter() - start) * 1000  # ms

        success_count = sum(
            1 for r in responses
            if isinstance(r, httpx.Response) and r.status_code == 200
        )

        avg_time_per_request = duration / len(tasks)

        assert success_count >= 28  # 93% success rate
        assert avg_time_per_request < 200.0  # < 200ms per request
```

### 2.5 Database Network Configuration Tests

**Objective:** Validate PostgreSQL remote access configuration

```python
# tests/integration/test_database_network_config.py

class TestDatabaseNetworkConfig:
    """Test PostgreSQL network configuration for server mode"""

    def test_postgresql_listens_on_network_interface(self, pg_config):
        """Test PostgreSQL is configured to accept network connections"""
        # Read postgresql.conf
        config_file = pg_config.postgresql_conf
        content = config_file.read_text()

        # Should have listen_addresses configured
        assert "listen_addresses" in content
        # Should not be restricted to localhost only
        assert "listen_addresses = 'localhost'" not in content

    def test_pg_hba_allows_network_connections(self, pg_config):
        """Test pg_hba.conf allows connections from network"""
        config_file = pg_config.pg_hba_conf
        content = config_file.read_text()

        # Should have network-based host entries
        assert "host" in content
        # Should have authentication method configured
        assert any(
            auth in content
            for auth in ["scram-sha-256", "md5", "password"]
        )

    @pytest.mark.asyncio
    async def test_database_connection_from_remote_client(
        self, db_network_config
    ):
        """Test database connection from remote client"""
        from sqlalchemy import create_engine, text

        # Construct remote database URL
        db_url = (
            f"postgresql://{db_network_config['username']}:{db_network_config['password']}"
            f"@{db_network_config['host']}:{db_network_config['port']}"
            f"/{db_network_config['database']}"
        )

        engine = create_engine(db_url)

        try:
            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                assert result.scalar() == 1
        finally:
            engine.dispose()

    @pytest.mark.asyncio
    async def test_database_connection_pool_under_network_load(
        self, db_network_config
    ):
        """Test connection pool with multiple remote clients"""
        from sqlalchemy import create_engine

        engines = []
        connections = []

        try:
            # Create 20 concurrent connections
            for _ in range(20):
                db_url = (
                    f"postgresql://{db_network_config['username']}:{db_network_config['password']}"
                    f"@{db_network_config['host']}:{db_network_config['port']}"
                    f"/{db_network_config['database']}"
                )
                engine = create_engine(db_url, pool_size=5)
                engines.append(engine)

                conn = engine.connect()
                connections.append(conn)

            # All connections should succeed
            assert len(connections) == 20

            # Test queries work
            for conn in connections:
                result = conn.execute(text("SELECT 1"))
                assert result.scalar() == 1

        finally:
            for conn in connections:
                conn.close()
            for engine in engines:
                engine.dispose()
```

---

## 3. Test Data and Environment Requirements

### 3.1 Test Infrastructure Setup

```yaml
# tests/server_mode_test_config.yml

server_mode_test_environment:
  # Server configuration
  server:
    mode: "server"
    api_host: "0.0.0.0"  # Bind to all interfaces
    api_port: 7272
    websocket_port: 6003
    ssl_enabled: false  # Start without SSL, then test with SSL

  # Database configuration
  database:
    type: "postgresql"
    host: "localhost"  # Or specific IP
    port: 5432
    database: "giljo_mcp_test"
    username: "giljo_user"
    password: "test_password"
    allow_network_connections: true

  # API keys for testing
  api_keys:
    - name: "full_access_key"
      permissions: ["*"]
      rate_limit: 1000  # requests per minute

    - name: "read_only_key"
      permissions: ["projects.read", "agents.read"]
      rate_limit: 500

    - name: "tenant1_key"
      tenant_key: "tenant_1"
      permissions: ["*"]

    - name: "tenant2_key"
      tenant_key: "tenant_2"
      permissions: ["*"]

  # Network testing
  network:
    local_ip: "192.168.1.100"  # Replace with actual LAN IP
    test_client_ips:
      - "192.168.1.101"
      - "192.168.1.102"
      - "192.168.1.103"

  # Performance thresholds
  thresholds:
    network_latency_ms: 50
    remote_api_response_ms: 200
    websocket_connection_ms: 2000
    concurrent_clients: 50
    success_rate_percent: 90
```

### 3.2 Test Fixtures

```python
# tests/fixtures/server_mode_fixtures.py

import pytest
import httpx
import asyncio
from typing import List

@pytest.fixture(scope="session")
def server_mode_config():
    """Load server mode test configuration"""
    import yaml
    config_file = Path("tests/server_mode_test_config.yml")
    return yaml.safe_load(config_file.read_text())

@pytest.fixture
def local_ip(server_mode_config):
    """Get local LAN IP for testing"""
    return server_mode_config["network"]["local_ip"]

@pytest.fixture
def api_key(server_mode_config):
    """Get full access API key for testing"""
    keys = server_mode_config["api_keys"]
    full_access = next(k for k in keys if k["name"] == "full_access_key")
    return full_access["key"]

@pytest.fixture
def read_only_api_key(server_mode_config):
    """Get read-only API key for testing"""
    keys = server_mode_config["api_keys"]
    read_only = next(k for k in keys if k["name"] == "read_only_key")
    return read_only["key"]

@pytest.fixture
def tenant1_api_key(server_mode_config):
    """Get tenant 1 API key"""
    keys = server_mode_config["api_keys"]
    tenant1 = next(k for k in keys if k["name"] == "tenant1_key")
    return tenant1["key"]

@pytest.fixture
def tenant2_api_key(server_mode_config):
    """Get tenant 2 API key"""
    keys = server_mode_config["api_keys"]
    tenant2 = next(k for k in keys if k["name"] == "tenant2_key")
    return tenant2["key"]

@pytest.fixture
async def remote_api_client(server_mode_config, local_ip):
    """Create remote API client"""
    base_url = f"http://{local_ip}:{server_mode_config['server']['api_port']}"
    client = httpx.AsyncClient(base_url=base_url, timeout=10.0)
    yield client
    await client.aclose()

@pytest.fixture
async def remote_api_clients(server_mode_config, local_ip) -> List[httpx.AsyncClient]:
    """Create multiple remote API clients for concurrent testing"""
    base_url = f"http://{local_ip}:{server_mode_config['server']['api_port']}"
    clients = [httpx.AsyncClient(base_url=base_url, timeout=10.0) for _ in range(50)]
    yield clients
    for client in clients:
        await client.aclose()

@pytest.fixture
def websocket_uri(server_mode_config, local_ip):
    """Get WebSocket URI for remote connection"""
    return f"ws://{local_ip}:{server_mode_config['server']['websocket_port']}/ws"

@pytest.fixture
async def db_network_config(server_mode_config):
    """Get database network configuration"""
    return server_mode_config["database"]
```

---

## 4. Testing Tools and Frameworks

### 4.1 Required Tools

```bash
# Core testing
pytest>=7.4.0
pytest-asyncio>=0.21.0
pytest-cov>=4.1.0

# HTTP/API testing
httpx>=0.24.0  # Async HTTP client
requests>=2.31.0

# WebSocket testing
websockets>=11.0

# Database testing
psycopg2-binary>=2.9.0
SQLAlchemy>=2.0.0

# Performance monitoring
psutil>=5.9.0
memory_profiler>=0.61.0

# Network utilities
netifaces>=0.11.0  # Network interface detection
ping3>=4.0.0  # ICMP ping testing
```

### 4.2 Custom Test Utilities

```python
# tests/helpers/network_test_utils.py

import socket
import netifaces

class NetworkTestHelper:
    """Helper utilities for network testing"""

    @staticmethod
    def get_local_ip() -> str:
        """Get local LAN IP address"""
        interfaces = netifaces.interfaces()
        for interface in interfaces:
            addrs = netifaces.ifaddresses(interface)
            if netifaces.AF_INET in addrs:
                for addr_info in addrs[netifaces.AF_INET]:
                    ip = addr_info['addr']
                    # Skip localhost
                    if not ip.startswith('127.'):
                        return ip
        return "localhost"

    @staticmethod
    def check_port_accessible(host: str, port: int, timeout: float = 3.0) -> bool:
        """Check if a port is accessible on a host"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        try:
            result = sock.connect_ex((host, port))
            return result == 0
        finally:
            sock.close()

    @staticmethod
    async def measure_network_latency(
        host: str,
        port: int,
        iterations: int = 10
    ) -> dict:
        """Measure network latency to a host"""
        latencies = []

        for _ in range(iterations):
            start = time.perf_counter()
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2.0)
                sock.connect((host, port))
                sock.close()

                latency_ms = (time.perf_counter() - start) * 1000
                latencies.append(latency_ms)
            except:
                pass

        if not latencies:
            return {"error": "No successful connections"}

        return {
            "min_ms": min(latencies),
            "max_ms": max(latencies),
            "avg_ms": sum(latencies) / len(latencies),
            "median_ms": sorted(latencies)[len(latencies) // 2]
        }
```

---

## 5. Performance Benchmarks for Server Mode

### 5.1 Network Performance Targets

| Metric | Target | Critical Threshold |
|--------|--------|-------------------|
| LAN API Latency | < 50ms | < 100ms |
| Remote API Response Time | < 200ms | < 500ms |
| WebSocket Connection (Remote) | < 2s | < 5s |
| Concurrent Remote Clients | 50+ | 30+ |
| Network Success Rate | > 95% | > 90% |
| Database Remote Query | < 100ms | < 200ms |

### 5.2 Load Testing Scenarios

```python
# tests/performance/test_server_mode_load.py

class TestServerModeLoad:
    """Load testing for server mode deployment"""

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_sustained_load_50_clients_5_minutes(
        self, remote_api_clients, api_keys
    ):
        """Test sustained load with 50 clients for 5 minutes"""
        duration_seconds = 300  # 5 minutes
        request_interval = 1.0  # 1 request per second per client

        start_time = time.time()
        total_requests = 0
        successful_requests = 0
        failed_requests = 0

        async def client_worker(client, api_key):
            nonlocal total_requests, successful_requests, failed_requests

            headers = {"X-API-Key": api_key}
            while time.time() - start_time < duration_seconds:
                try:
                    response = await client.get("/health", headers=headers)
                    total_requests += 1

                    if response.status_code == 200:
                        successful_requests += 1
                    else:
                        failed_requests += 1

                except Exception:
                    total_requests += 1
                    failed_requests += 1

                await asyncio.sleep(request_interval)

        # Run all clients concurrently
        tasks = [
            client_worker(client, api_keys[i % len(api_keys)])
            for i, client in enumerate(remote_api_clients[:50])
        ]

        await asyncio.gather(*tasks)

        success_rate = successful_requests / total_requests * 100

        assert success_rate >= 95.0  # 95% success rate over 5 minutes
        assert total_requests >= 14000  # ~50 clients * 1 req/s * 300s
```

---

## 6. CI/CD Integration for Server Mode Testing

### 6.1 GitHub Actions Workflow

```yaml
# .github/workflows/server_mode_tests.yml

name: Server Mode Integration Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]
  schedule:
    - cron: "0 3 * * *"  # Nightly at 3 AM

jobs:
  server-mode-tests:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:18
        env:
          POSTGRES_USER: giljo_user
          POSTGRES_PASSWORD: test_password
          POSTGRES_DB: giljo_mcp_test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-asyncio httpx websockets

      - name: Configure PostgreSQL for network access
        run: |
          # Configure pg_hba.conf for test access
          echo "host all all 0.0.0.0/0 scram-sha-256" | sudo tee -a /etc/postgresql/*/main/pg_hba.conf
          sudo systemctl restart postgresql

      - name: Run server mode network tests
        env:
          DATABASE_URL: postgresql://giljo_user:test_password@localhost:5432/giljo_mcp_test
          SERVER_MODE: "server"
          API_HOST: "0.0.0.0"
        run: |
          pytest tests/integration/test_network_connectivity.py -v
          pytest tests/integration/test_remote_api_workflows.py -v
          pytest tests/integration/test_server_mode_security.py -v

      - name: Run server mode performance tests
        run: |
          pytest tests/performance/test_network_performance.py -v

      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: server-mode-test-results
          path: |
            test-results/
            coverage.xml
```

---

## 7. Test Implementation Priorities

### Phase 1: Foundation (Week 1)
**Priority: CRITICAL**

1. ✅ Network connectivity tests (localhost, LAN IP)
2. ✅ Basic remote API workflow tests
3. ✅ API key authentication enforcement
4. ✅ Database network configuration validation

**Deliverables:**
- `tests/integration/test_network_connectivity.py`
- `tests/integration/test_remote_api_workflows.py`
- `tests/fixtures/server_mode_fixtures.py`
- `tests/helpers/network_test_utils.py`

### Phase 2: Security Hardening (Week 2)
**Priority: HIGH**

1. ✅ API key permissions testing
2. ✅ Rate limiting validation
3. ✅ Tenant isolation with network access
4. ✅ Brute force protection

**Deliverables:**
- `tests/integration/test_server_mode_security.py`
- `tests/integration/test_tenant_isolation_network.py`

### Phase 3: Performance Validation (Week 3)
**Priority: HIGH**

1. ✅ Concurrent remote client tests (50+)
2. ✅ WebSocket stress from network clients (100+)
3. ✅ Database connection pooling under network load
4. ✅ Sustained load testing (5-minute runs)

**Deliverables:**
- `tests/performance/test_network_performance.py`
- `tests/performance/test_server_mode_load.py`

### Phase 4: Advanced Scenarios (Week 4)
**Priority: MEDIUM**

1. ⚠️ SSL/TLS certificate validation
2. ⚠️ Cross-region network latency simulation
3. ⚠️ Network failure recovery
4. ⚠️ Load balancer integration

**Deliverables:**
- `tests/integration/test_ssl_tls.py`
- `tests/performance/test_network_resilience.py`

---

## 8. Success Criteria

### 8.1 Test Coverage Requirements

| Category | Target Coverage | Minimum |
|----------|----------------|---------|
| Network Connectivity | 95% | 90% |
| Remote API Workflows | 90% | 85% |
| Security (Server Mode) | 100% | 95% |
| Performance (Network) | 85% | 80% |
| Database Network Config | 90% | 85% |

### 8.2 Performance Requirements

All tests must meet these targets:

✅ **Network Latency:** < 50ms average (LAN)
✅ **Remote API Response:** < 200ms average
✅ **Concurrent Clients:** 50+ simultaneous connections
✅ **Success Rate:** > 95% across all network tests
✅ **WebSocket Stability:** 80%+ connection success rate
✅ **Database Network:** < 100ms query latency

### 8.3 Security Requirements

All security tests must pass:

✅ **API Key Enforcement:** 100% rejection without valid key
✅ **Rate Limiting:** Effective throttling after threshold
✅ **Tenant Isolation:** 0% data leakage across tenants
✅ **Brute Force Protection:** Auto-blocking after attempts
✅ **Permission Enforcement:** Accurate permission checks

---

## 9. Deployment Validation Checklist

Before production deployment, validate:

### Network Configuration
- [ ] API accessible from LAN IP addresses
- [ ] WebSocket connections work from remote clients
- [ ] Firewall rules properly configured
- [ ] Port forwarding (if needed) tested
- [ ] DNS resolution working (if applicable)

### Security
- [ ] API keys required and enforced
- [ ] Rate limiting active and effective
- [ ] Tenant isolation verified under load
- [ ] SSL/TLS certificates valid (if enabled)
- [ ] Security headers present

### Performance
- [ ] 50+ concurrent remote clients supported
- [ ] Network latency within targets
- [ ] Database connection pooling stable
- [ ] No memory leaks under sustained load
- [ ] Graceful degradation under stress

### Database
- [ ] PostgreSQL accepts network connections
- [ ] pg_hba.conf properly configured
- [ ] Connection pool scales appropriately
- [ ] Remote queries perform adequately
- [ ] Backup/restore procedures tested

### Monitoring
- [ ] Logging captures network events
- [ ] Metrics dashboards show network stats
- [ ] Alerting configured for failures
- [ ] Health checks respond correctly
- [ ] Error rates tracked

---

## 10. Conclusion

This testing strategy provides a comprehensive roadmap for validating GiljoAI MCP's server mode deployment. By addressing the identified gaps in network testing, remote access validation, and security hardening, we ensure the system is production-ready for network-accessible multi-agent orchestration.

**Next Steps:**
1. Implement Phase 1 tests (network connectivity, basic remote workflows)
2. Set up server mode test environment with proper network configuration
3. Create fixtures and utilities for remote testing
4. Run initial test suite and establish baseline metrics
5. Iterate on security and performance tests
6. Integrate into CI/CD pipeline

**Estimated Timeline:** 4 weeks for complete implementation
**Resources Required:** 1 backend tester, access to network-accessible test environment, PostgreSQL instance with network configuration

---

**Document prepared by:** Backend Integration Tester Agent
**Review status:** Ready for implementation
**Last updated:** 2025-10-04
