# Handover 0129d: Load Testing & Capacity Validation

**Date**: 2025-11-11
**Priority**: P2
**Duration**: 1-2 days
**Status**: ✅ COMPLETE
**Type**: Load Testing Infrastructure
**CCW Safe**: ⚠️ PARTIAL - Write test scripts in CCW, run locally with app + PostgreSQL
**Dependencies**: 0129a (needs working test baseline)
**Blocks**: None
**Completed**: 2025-11-12
**Agent**: Claude Code CLI (Session: project-0129d)

---

## Executive Summary

GiljoAI MCP has no load testing infrastructure to validate concurrent user capacity or identify performance bottlenecks under stress. This handover creates a comprehensive Locust-based load testing framework to simulate realistic user workflows, test system scalability, and establish capacity planning metrics.

**Why P2 Priority**: Load testing is important for production readiness but not blocking other development. Can run after 0129a test fixes are merged.

**Why Partial CCW**: Load test scripts can be written in CCW (code-only), but must be executed locally against a running application and PostgreSQL database to generate meaningful stress test results.

---

## Objectives

### Primary Objectives

1. **Create Locust Load Testing Framework**
   - User workflow scenarios (login, create project, manage agents)
   - API endpoint stress testing
   - WebSocket connection scaling
   - Database connection pool testing

2. **Define Load Test Scenarios**
   - Normal Load: 10 concurrent users, 5 minutes
   - Peak Load: 50 concurrent users, 5 minutes
   - Stress Test: 100 concurrent users, 2 minutes
   - Spike Test: 0→100→0 users rapid scaling
   - Soak Test: 20 users, 30 minutes sustained

3. **Identify System Bottlenecks**
   - CPU bottlenecks
   - Memory usage under load
   - Database connection pool exhaustion
   - WebSocket connection limits
   - Network I/O saturation

4. **Establish Capacity Planning Metrics**
   - Maximum concurrent users
   - Requests per second capacity
   - WebSocket connection limits
   - Database query throughput
   - Resource utilization thresholds

### Secondary Objectives

- Create reusable load test infrastructure
- Document scaling recommendations
- Prepare for production capacity planning
- Establish monitoring baselines

---

## Current State Analysis

### No Load Testing Infrastructure

**Current State**:
- No load testing framework
- No concurrent user validation
- No stress testing capabilities
- Unknown system capacity
- No bottleneck identification

**Impact**:
- Cannot predict production behavior under load
- No data for infrastructure sizing
- Risk of unexpected failures under stress
- Cannot validate scalability claims

### Unknown Capacity Limits

**Questions We Cannot Answer**:
- How many concurrent users can the system support?
- At what point does performance degrade?
- Where are the bottlenecks (CPU, memory, database, network)?
- How does the system behave during traffic spikes?
- What is the breaking point?

---

## Target Capacity Metrics

### Concurrent User Targets

| Scenario | Target Users | Target RPS | Expected Response Time |
|----------|-------------|------------|------------------------|
| Normal Load | 10 | 10-20 | <100ms (p95) |
| Peak Load | 50 | 50-100 | <200ms (p95) |
| Stress Test | 100 | 100-200 | <500ms (p95) |
| Spike Test | 0→100→0 | Variable | <1000ms (p95) |
| Soak Test | 20 | 20-40 | <100ms (p95, sustained) |

### Resource Utilization Targets

| Resource | Normal | Peak | Stress | Critical |
|----------|--------|------|--------|----------|
| CPU Usage | <30% | <60% | <80% | >90% |
| Memory Usage | <2GB | <4GB | <6GB | >8GB |
| DB Connections | <10 | <25 | <40 | >50 |
| WebSocket Connections | <20 | <100 | <200 | >250 |

---

## Implementation Plan

### Phase 1: Locust Framework Setup (Day 1 - Morning)

**New File**: `tests/load/locustfile.py`

```python
"""
Locust Load Testing Configuration

Main entry point for all load tests.

Usage:
    # Run with Locust web UI
    locust -f tests/load/locustfile.py --host=http://localhost:7272

    # Run headless (no UI)
    locust -f tests/load/locustfile.py --host=http://localhost:7272 \
           --headless -u 100 -r 10 -t 2m

    # Run specific scenario
    locust -f tests/load/locustfile.py --host=http://localhost:7272 \
           --headless -u 10 -r 2 -t 5m --tags normal_load
"""
from locust import HttpUser, TaskSet, task, between, tag
from locust.contrib.fasthttp import FastHttpUser
import json
import random
from typing import Dict, Any


class AuthenticatedUser(FastHttpUser):
    """
    Base class for authenticated users.

    Handles login and maintains session state.
    """
    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks
    abstract = True  # Don't instantiate directly

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tenant_key = None
        self.auth_token = None
        self.products = []
        self.projects = []

    def on_start(self):
        """Called when user starts - perform login."""
        self.login()

    def login(self):
        """Authenticate user and get tenant key."""
        # Use test credentials
        response = self.client.post(
            "/api/auth/login",
            json={
                "email": f"loadtest_user_{random.randint(1, 1000)}@example.com",
                "password": "TestPassword123"
            },
            catch_response=True
        )

        if response.status_code == 200:
            data = response.json()
            self.tenant_key = data.get("tenant_key")
            self.auth_token = data.get("token")
            response.success()
        else:
            response.failure(f"Login failed: {response.status_code}")

    def get_headers(self) -> Dict[str, str]:
        """Get headers with authentication."""
        headers = {"Content-Type": "application/json"}
        if self.tenant_key:
            headers["X-Tenant-Key"] = self.tenant_key
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        return headers


class ProductManagementTasks(TaskSet):
    """
    Product management workflow tasks.

    Simulates user creating and managing products.
    """

    @task(3)
    @tag("normal_load", "peak_load")
    def list_products(self):
        """List all products."""
        response = self.client.get(
            "/api/products",
            headers=self.user.get_headers(),
            name="/api/products [LIST]",
            catch_response=True
        )

        if response.status_code == 200:
            self.user.products = response.json()
            response.success()
        else:
            response.failure(f"Failed to list products: {response.status_code}")

    @task(1)
    @tag("normal_load", "peak_load", "stress_test")
    def create_product(self):
        """Create a new product."""
        product_name = f"Load Test Product {random.randint(1, 10000)}"
        response = self.client.post(
            "/api/products",
            headers=self.user.get_headers(),
            json={
                "name": product_name,
                "description": "Created during load testing",
                "status": "active"
            },
            name="/api/products [CREATE]",
            catch_response=True
        )

        if response.status_code == 201:
            product = response.json()
            self.user.products.append(product)
            response.success()
        else:
            response.failure(f"Failed to create product: {response.status_code}")

    @task(2)
    @tag("normal_load", "peak_load")
    def view_product(self):
        """View a specific product."""
        if not self.user.products:
            return

        product = random.choice(self.user.products)
        response = self.client.get(
            f"/api/products/{product['id']}",
            headers=self.user.get_headers(),
            name="/api/products/{id} [GET]",
            catch_response=True
        )

        if response.status_code == 200:
            response.success()
        else:
            response.failure(f"Failed to view product: {response.status_code}")

    @task(1)
    @tag("peak_load", "stress_test")
    def update_product(self):
        """Update a product."""
        if not self.user.products:
            return

        product = random.choice(self.user.products)
        response = self.client.put(
            f"/api/products/{product['id']}",
            headers=self.user.get_headers(),
            json={
                "name": f"{product['name']} (Updated)",
                "status": "active"
            },
            name="/api/products/{id} [UPDATE]",
            catch_response=True
        )

        if response.status_code == 200:
            response.success()
        else:
            response.failure(f"Failed to update product: {response.status_code}")


class ProjectManagementTasks(TaskSet):
    """
    Project management workflow tasks.

    Simulates user creating and managing projects.
    """

    @task(3)
    @tag("normal_load", "peak_load")
    def list_projects(self):
        """List all projects."""
        response = self.client.get(
            "/api/projects",
            headers=self.user.get_headers(),
            name="/api/projects [LIST]",
            catch_response=True
        )

        if response.status_code == 200:
            self.user.projects = response.json()
            response.success()
        else:
            response.failure(f"Failed to list projects: {response.status_code}")

    @task(1)
    @tag("normal_load", "peak_load", "stress_test")
    def create_project(self):
        """Create a new project."""
        if not self.user.products:
            return

        product = random.choice(self.user.products)
        project_name = f"Load Test Project {random.randint(1, 10000)}"

        response = self.client.post(
            "/api/projects",
            headers=self.user.get_headers(),
            json={
                "product_id": product["id"],
                "name": project_name,
                "description": "Created during load testing",
                "status": "active"
            },
            name="/api/projects [CREATE]",
            catch_response=True
        )

        if response.status_code == 201:
            project = response.json()
            self.user.projects.append(project)
            response.success()
        else:
            response.failure(f"Failed to create project: {response.status_code}")


class AgentJobTasks(TaskSet):
    """
    Agent job management tasks.

    Simulates user working with agent jobs.
    """

    @task(2)
    @tag("normal_load", "peak_load")
    def list_agent_jobs(self):
        """List all agent jobs."""
        response = self.client.get(
            "/api/agent-jobs",
            headers=self.user.get_headers(),
            name="/api/agent-jobs [LIST]",
            catch_response=True
        )

        if response.status_code == 200:
            response.success()
        else:
            response.failure(f"Failed to list agent jobs: {response.status_code}")

    @task(1)
    @tag("peak_load", "stress_test")
    def create_agent_job(self):
        """Create a new agent job."""
        if not self.user.projects:
            return

        project = random.choice(self.user.projects)
        response = self.client.post(
            "/api/agent-jobs",
            headers=self.user.get_headers(),
            json={
                "project_id": project["id"],
                "agent_name": f"load_test_agent_{random.randint(1, 1000)}",
                "agent_type": random.choice(["implementer", "tester", "reviewer"]),
                "mission": "Load testing mission"
            },
            name="/api/agent-jobs [CREATE]",
            catch_response=True
        )

        if response.status_code == 201:
            response.success()
        else:
            response.failure(f"Failed to create agent job: {response.status_code}")


class NormalLoadUser(AuthenticatedUser):
    """
    Normal load user - typical daily usage.

    Weight: 60% product management, 30% project management, 10% agent jobs
    """
    tasks = {
        ProductManagementTasks: 6,
        ProjectManagementTasks: 3,
        AgentJobTasks: 1
    }
    wait_time = between(2, 5)
    tags = ["normal_load"]


class PeakLoadUser(AuthenticatedUser):
    """
    Peak load user - higher activity during peak hours.

    Weight: 50% product, 40% project, 10% agents
    """
    tasks = {
        ProductManagementTasks: 5,
        ProjectManagementTasks: 4,
        AgentJobTasks: 1
    }
    wait_time = between(1, 3)
    tags = ["peak_load"]


class StressTestUser(AuthenticatedUser):
    """
    Stress test user - aggressive usage for stress testing.

    Weight: 40% product, 40% project, 20% agents
    """
    tasks = {
        ProductManagementTasks: 4,
        ProjectManagementTasks: 4,
        AgentJobTasks: 2
    }
    wait_time = between(0.5, 1.5)
    tags = ["stress_test"]
```

---

### Phase 2: WebSocket Load Testing (Day 1 - Afternoon)

**New File**: `tests/load/scenarios/websocket_load.py`

```python
"""
WebSocket Load Testing Scenarios

Tests WebSocket connection scaling and message throughput.
"""
import time
import json
import websocket
from locust import User, task, between, events
from locust.exception import LocustError
import logging

logger = logging.getLogger(__name__)


class WebSocketClient:
    """
    WebSocket client for load testing.

    Manages WebSocket connection lifecycle.
    """

    def __init__(self, host, tenant_key):
        self.host = host
        self.tenant_key = tenant_key
        self.ws = None
        self.connected = False

    def connect(self):
        """Establish WebSocket connection."""
        ws_url = self.host.replace("http://", "ws://").replace("https://", "wss://")
        ws_url = f"{ws_url}/ws"

        start_time = time.time()
        try:
            self.ws = websocket.create_connection(ws_url)
            self.connected = True

            # Authenticate
            auth_message = {
                "type": "auth",
                "tenant_key": self.tenant_key
            }
            self.ws.send(json.dumps(auth_message))

            # Wait for auth response
            response = self.ws.recv()

            total_time = int((time.time() - start_time) * 1000)
            events.request.fire(
                request_type="WSS",
                name="connect",
                response_time=total_time,
                response_length=len(response),
                exception=None,
                context={}
            )

        except Exception as e:
            total_time = int((time.time() - start_time) * 1000)
            events.request.fire(
                request_type="WSS",
                name="connect",
                response_time=total_time,
                response_length=0,
                exception=e,
                context={}
            )
            logger.error(f"WebSocket connection failed: {e}")
            raise

    def send_message(self, message: dict):
        """Send message via WebSocket."""
        if not self.connected:
            raise LocustError("WebSocket not connected")

        start_time = time.time()
        try:
            self.ws.send(json.dumps(message))
            response = self.ws.recv()

            total_time = int((time.time() - start_time) * 1000)
            events.request.fire(
                request_type="WSS",
                name="send_message",
                response_time=total_time,
                response_length=len(response),
                exception=None,
                context={}
            )

            return json.loads(response)

        except Exception as e:
            total_time = int((time.time() - start_time) * 1000)
            events.request.fire(
                request_type="WSS",
                name="send_message",
                response_time=total_time,
                response_length=0,
                exception=e,
                context={}
            )
            raise

    def subscribe(self, channel: str):
        """Subscribe to a channel."""
        message = {
            "type": "subscribe",
            "channel": channel
        }
        return self.send_message(message)

    def disconnect(self):
        """Close WebSocket connection."""
        if self.ws:
            self.ws.close()
            self.connected = False


class WebSocketUser(User):
    """
    WebSocket load testing user.

    Simulates user maintaining WebSocket connection and receiving updates.
    """
    abstract = True
    wait_time = between(1, 3)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ws_client = None
        self.tenant_key = "test_tenant_key"  # In reality, get from auth

    def on_start(self):
        """Establish WebSocket connection on user start."""
        self.ws_client = WebSocketClient(self.host, self.tenant_key)
        self.ws_client.connect()

    def on_stop(self):
        """Close WebSocket connection on user stop."""
        if self.ws_client:
            self.ws_client.disconnect()

    @task(5)
    def receive_updates(self):
        """Simulate receiving real-time updates."""
        if self.ws_client and self.ws_client.connected:
            self.ws_client.subscribe("project_updates")

    @task(2)
    def ping_pong(self):
        """Ping/pong to keep connection alive."""
        if self.ws_client and self.ws_client.connected:
            self.ws_client.send_message({"type": "ping"})


class WebSocketStressUser(WebSocketUser):
    """
    Aggressive WebSocket user for stress testing.
    """
    wait_time = between(0.5, 1)

    @task(10)
    def rapid_messages(self):
        """Send rapid messages to stress test."""
        if self.ws_client and self.ws_client.connected:
            for _ in range(10):
                self.ws_client.send_message({"type": "ping"})
                time.sleep(0.1)
```

---

### Phase 3: Load Test Scenarios (Day 1 - Evening)

**New File**: `tests/load/scenarios/user_workflows.py`

```python
"""
Realistic User Workflow Scenarios

Simulates complete user journeys through the application.
"""
from locust import SequentialTaskSet, task
from tests.load.locustfile import AuthenticatedUser


class NewUserOnboarding(SequentialTaskSet):
    """
    Simulates new user onboarding workflow.

    1. Login
    2. Create first product
    3. Create first project
    4. View dashboard
    5. Create agent job
    """

    @task
    def step1_login(self):
        """User logs in."""
        self.user.login()

    @task
    def step2_create_product(self):
        """User creates first product."""
        response = self.client.post(
            "/api/products",
            headers=self.user.get_headers(),
            json={
                "name": "My First Product",
                "description": "Getting started",
                "status": "active"
            },
            name="Onboarding: Create Product"
        )
        if response.status_code == 201:
            self.user.products.append(response.json())

    @task
    def step3_create_project(self):
        """User creates first project."""
        if not self.user.products:
            return

        product = self.user.products[0]
        response = self.client.post(
            "/api/projects",
            headers=self.user.get_headers(),
            json={
                "product_id": product["id"],
                "name": "My First Project",
                "description": "Getting started",
                "status": "active"
            },
            name="Onboarding: Create Project"
        )
        if response.status_code == 201:
            self.user.projects.append(response.json())

    @task
    def step4_view_dashboard(self):
        """User views dashboard."""
        self.client.get(
            "/api/dashboard",
            headers=self.user.get_headers(),
            name="Onboarding: View Dashboard"
        )

    @task
    def step5_create_agent_job(self):
        """User creates first agent job."""
        if not self.user.projects:
            return

        project = self.user.projects[0]
        self.client.post(
            "/api/agent-jobs",
            headers=self.user.get_headers(),
            json={
                "project_id": project["id"],
                "agent_name": "my_first_agent",
                "agent_type": "implementer",
                "mission": "Help me build something"
            },
            name="Onboarding: Create Agent Job"
        )


class PowerUserWorkflow(SequentialTaskSet):
    """
    Simulates power user managing multiple products.

    1. Login
    2. List all products
    3. Create new product
    4. Create multiple projects
    5. Manage agent jobs
    6. Monitor progress
    """

    @task
    def step1_login(self):
        """Power user logs in."""
        self.user.login()

    @task
    def step2_list_products(self):
        """List all products."""
        response = self.client.get(
            "/api/products",
            headers=self.user.get_headers(),
            name="Power User: List Products"
        )
        if response.status_code == 200:
            self.user.products = response.json()

    @task
    def step3_create_product(self):
        """Create new product."""
        self.client.post(
            "/api/products",
            headers=self.user.get_headers(),
            json={
                "name": f"Product {len(self.user.products) + 1}",
                "status": "active"
            },
            name="Power User: Create Product"
        )

    @task
    def step4_create_multiple_projects(self):
        """Create multiple projects."""
        if not self.user.products:
            return

        for i in range(3):
            product = self.user.products[0]
            self.client.post(
                "/api/projects",
                headers=self.user.get_headers(),
                json={
                    "product_id": product["id"],
                    "name": f"Project {i + 1}",
                    "status": "active"
                },
                name="Power User: Create Project"
            )

    @task
    def step5_manage_agents(self):
        """Create and manage agent jobs."""
        if not self.user.projects:
            return

        project = self.user.projects[0]
        # Create orchestrator
        self.client.post(
            "/api/agent-jobs",
            headers=self.user.get_headers(),
            json={
                "project_id": project["id"],
                "agent_name": "orchestrator",
                "agent_type": "orchestrator",
                "mission": "Coordinate development"
            },
            name="Power User: Create Orchestrator"
        )

    @task
    def step6_monitor_progress(self):
        """Monitor job progress."""
        self.client.get(
            "/api/agent-jobs",
            headers=self.user.get_headers(),
            name="Power User: Monitor Jobs"
        )


class OnboardingUser(AuthenticatedUser):
    """User going through onboarding."""
    tasks = [NewUserOnboarding]
    weight = 1


class PowerUser(AuthenticatedUser):
    """Power user with heavy usage."""
    tasks = [PowerUserWorkflow]
    weight = 3
```

---

### Phase 4: Load Test Runner & Reports (Day 2)

**New File**: `tests/load/run_load_tests.py`

```python
"""
Load Test Runner

Orchestrates load test scenarios and generates reports.
"""
import subprocess
import argparse
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List


class LoadTestRunner:
    """
    Run load tests and generate reports.
    """

    def __init__(self, host: str = "http://localhost:7272"):
        self.host = host
        self.results_dir = Path("tests/load/results")
        self.results_dir.mkdir(exist_ok=True)

    def run_scenario(
        self,
        name: str,
        users: int,
        spawn_rate: int,
        duration: str,
        tags: List[str] = None
    ) -> Dict:
        """
        Run a single load test scenario.

        Args:
            name: Scenario name
            users: Number of concurrent users
            spawn_rate: Users spawned per second
            duration: Test duration (e.g., "5m", "2h")
            tags: Locust tags to run

        Returns:
            Test results dictionary
        """
        print(f"\n{'='*60}")
        print(f"Running: {name}")
        print(f"Users: {users}, Spawn Rate: {spawn_rate}/s, Duration: {duration}")
        print(f"{'='*60}\n")

        # Build locust command
        cmd = [
            "locust",
            "-f", "tests/load/locustfile.py",
            "--host", self.host,
            "--headless",
            "-u", str(users),
            "-r", str(spawn_rate),
            "-t", duration,
            "--html", str(self.results_dir / f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"),
            "--json"
        ]

        if tags:
            cmd.extend(["--tags"] + tags)

        # Run load test
        start_time = time.time()
        process = subprocess.run(cmd, capture_output=True, text=True)
        duration_seconds = time.time() - start_time

        # Parse results
        results = {
            "name": name,
            "users": users,
            "spawn_rate": spawn_rate,
            "duration": duration,
            "duration_seconds": duration_seconds,
            "success": process.returncode == 0,
            "stdout": process.stdout,
            "stderr": process.stderr
        }

        # Save results
        results_file = self.results_dir / f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)

        print(f"\n✅ Scenario complete: {name}")
        print(f"Results saved: {results_file}")

        return results

    def run_all_scenarios(self) -> List[Dict]:
        """Run all defined load test scenarios."""
        scenarios = [
            {
                "name": "normal_load",
                "users": 10,
                "spawn_rate": 2,
                "duration": "5m",
                "tags": ["normal_load"]
            },
            {
                "name": "peak_load",
                "users": 50,
                "spawn_rate": 10,
                "duration": "5m",
                "tags": ["peak_load"]
            },
            {
                "name": "stress_test",
                "users": 100,
                "spawn_rate": 10,
                "duration": "2m",
                "tags": ["stress_test"]
            },
            {
                "name": "spike_test",
                "users": 100,
                "spawn_rate": 50,  # Rapid spawn
                "duration": "1m",
                "tags": ["stress_test"]
            },
            {
                "name": "soak_test",
                "users": 20,
                "spawn_rate": 2,
                "duration": "30m",
                "tags": ["normal_load"]
            }
        ]

        results = []
        for scenario in scenarios:
            result = self.run_scenario(**scenario)
            results.append(result)
            time.sleep(30)  # Cool down between tests

        return results

    def generate_summary_report(self, results: List[Dict]):
        """Generate summary report from all test results."""
        report = f"""# Load Test Summary Report

**Generated**: {datetime.now().isoformat()}
**Host**: {self.host}

## Test Scenarios

"""

        for result in results:
            status = "✅ PASS" if result["success"] else "❌ FAIL"
            report += f"""
### {result['name']} {status}

- **Users**: {result['users']}
- **Spawn Rate**: {result['spawn_rate']}/s
- **Duration**: {result['duration']}
- **Actual Duration**: {result['duration_seconds']:.2f}s

"""

        report += """
## Recommendations

Based on load test results:

"""

        # Add recommendations based on results
        max_users = max(r["users"] for r in results if r["success"])
        report += f"- System successfully handled {max_users} concurrent users\n"
        report += "- Review individual scenario reports for detailed metrics\n"
        report += "- Monitor resource utilization during peak load\n"

        # Save report
        report_file = self.results_dir / f"summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        with open(report_file, 'w') as f:
            f.write(report)

        print(f"\n📊 Summary report: {report_file}")

        return report


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run load tests")
    parser.add_argument("--host", default="http://localhost:7272", help="Target host")
    parser.add_argument("--scenario", help="Run specific scenario")
    parser.add_argument("--all", action="store_true", help="Run all scenarios")
    args = parser.parse_args()

    runner = LoadTestRunner(host=args.host)

    if args.all:
        results = runner.run_all_scenarios()
        runner.generate_summary_report(results)
    elif args.scenario:
        # Run single scenario
        runner.run_scenario(
            name=args.scenario,
            users=10,
            spawn_rate=2,
            duration="5m"
        )
    else:
        print("Please specify --all or --scenario <name>")
        print("\nAvailable scenarios:")
        print("  - normal_load")
        print("  - peak_load")
        print("  - stress_test")
        print("  - spike_test")
        print("  - soak_test")


if __name__ == "__main__":
    main()
```

**Usage**:
```bash
# Run all load test scenarios
python tests/load/run_load_tests.py --all

# Run specific scenario
python tests/load/run_load_tests.py --scenario normal_load

# Run against different host
python tests/load/run_load_tests.py --all --host http://192.168.1.100:7272
```

---

### Phase 5: Documentation & README (Day 2)

**New File**: `tests/load/README.md`

```markdown
# Load Testing Guide

Comprehensive load testing for GiljoAI MCP using Locust.

## Prerequisites

- Python 3.11+
- Locust: `pip install locust`
- Running GiljoAI MCP server
- PostgreSQL database

## Quick Start

### 1. Install Locust

```bash
pip install locust
```

### 2. Start Application

```bash
python startup.py
```

### 3. Run Load Tests

**Option A: Web UI (Interactive)**
```bash
locust -f tests/load/locustfile.py --host=http://localhost:7272
# Open http://localhost:8089 in browser
```

**Option B: Headless (Automated)**
```bash
# Run specific scenario
python tests/load/run_load_tests.py --scenario normal_load

# Run all scenarios
python tests/load/run_load_tests.py --all
```

## Load Test Scenarios

### Normal Load (10 users, 5 min)
Simulates typical daily usage with 10 concurrent users.

```bash
locust -f tests/load/locustfile.py --host=http://localhost:7272 \
       --headless -u 10 -r 2 -t 5m --tags normal_load
```

### Peak Load (50 users, 5 min)
Simulates peak hours with 50 concurrent users.

```bash
locust -f tests/load/locustfile.py --host=http://localhost:7272 \
       --headless -u 50 -r 10 -t 5m --tags peak_load
```

### Stress Test (100 users, 2 min)
Stress tests the system with 100 concurrent users.

```bash
locust -f tests/load/locustfile.py --host=http://localhost:7272 \
       --headless -u 100 -r 10 -t 2m --tags stress_test
```

### Spike Test (0→100→0 users)
Tests rapid scaling from 0 to 100 users and back.

```bash
locust -f tests/load/locustfile.py --host=http://localhost:7272 \
       --headless -u 100 -r 50 -t 1m --tags stress_test
```

### Soak Test (20 users, 30 min)
Long-duration test to identify memory leaks and resource exhaustion.

```bash
locust -f tests/load/locustfile.py --host=http://localhost:7272 \
       --headless -u 20 -r 2 -t 30m --tags normal_load
```

## Interpreting Results

### Key Metrics

- **RPS (Requests Per Second)**: Total request throughput
- **Response Time (P50, P95, P99)**: Latency percentiles
- **Failure Rate**: Percentage of failed requests
- **Concurrent Users**: Number of simulated users

### Target Thresholds

| Metric | Normal | Peak | Stress |
|--------|--------|------|--------|
| RPS | 10-20 | 50-100 | 100-200 |
| P95 Response Time | <100ms | <200ms | <500ms |
| Failure Rate | <1% | <2% | <5% |

### Bottleneck Identification

**High response times**:
- Check database query performance
- Review slow endpoints
- Optimize heavy operations

**High failure rate**:
- Check error logs
- Review rate limiting settings
- Verify resource limits

**Memory growth (soak test)**:
- Check for memory leaks
- Review connection pooling
- Monitor long-lived objects

## Results Location

Load test results are saved in:
- `tests/load/results/*.html` - Visual reports
- `tests/load/results/*.json` - Raw data
- `tests/load/results/summary_*.md` - Summary reports

## Tips

1. **Warm-up**: Run a small test first to warm up the system
2. **Monitoring**: Watch CPU, memory, and database connections during tests
3. **Isolation**: Run on isolated test environment (not development machine)
4. **Realistic Data**: Use production-like data volumes
5. **Cool Down**: Wait between tests to let system recover

## Troubleshooting

**Connection refused**:
- Verify application is running: `curl http://localhost:7272/api/health`
- Check correct host and port

**High failure rate**:
- Check application logs: `tail -f logs/giljo_mcp.log`
- Verify database is accessible
- Check rate limiting settings

**Locust errors**:
- Ensure Locust installed: `pip install locust`
- Verify Python version: `python --version` (3.11+)
- Check locustfile syntax: `locust -f tests/load/locustfile.py --help`
```

---

## Testing Validation Steps

### Local Testing After Merge (REQUIRED)

**NOTE**: Load tests MUST run locally with running application and PostgreSQL.

```bash
# Step 1: Merge branch
git checkout main
git merge /claude-project-0129d

# Step 2: Install Locust
pip install locust

# Step 3: Start application
python startup.py

# Step 4: Run quick test (verify setup)
locust -f tests/load/locustfile.py --host=http://localhost:7272 --headless -u 5 -r 1 -t 1m

# Step 5: Run all scenarios
python tests/load/run_load_tests.py --all

# Step 6: Review results
ls tests/load/results/
cat tests/load/results/summary_*.md
```

### Success Criteria

- [ ] Locust framework created
- [ ] All 5 scenarios implemented
- [ ] Load tests run successfully locally
- [ ] Results generated (HTML + JSON)
- [ ] Summary report created
- [ ] Bottlenecks identified (if any)
- [ ] Capacity metrics documented

---

## CCW Execution Notes

### Why Partial CCW

**CCW Can Do** (Code Writing):
- ✅ Create locustfile.py
- ✅ Create scenario files
- ✅ Create test runner
- ✅ Write documentation

**CCW Cannot Do** (Requires Local Environment):
- ❌ Run load tests (needs running app + PostgreSQL)
- ❌ Generate actual performance data
- ❌ Test resource utilization
- ❌ Validate capacity limits

### CCW Agent Instructions

```markdown
You are working on Handover 0129d: Load Testing Configuration.

**Task**: Create Locust load testing framework with realistic scenarios.

**Files to Create**:
1. tests/load/locustfile.py (~400 lines) - Main Locust configuration
2. tests/load/scenarios/websocket_load.py (~300 lines) - WebSocket tests
3. tests/load/scenarios/user_workflows.py (~250 lines) - User journey tests
4. tests/load/run_load_tests.py (~300 lines) - Test orchestrator
5. tests/load/README.md - Usage documentation

**Requirements**:
- Use FastHttpUser for better performance
- Implement realistic user workflows
- Tag scenarios (normal_load, peak_load, stress_test)
- Generate HTML and JSON reports
- Include 5 scenarios: normal, peak, stress, spike, soak

**Scenarios**:
- Normal: 10 users, 5 min
- Peak: 50 users, 5 min
- Stress: 100 users, 2 min
- Spike: 0→100→0 rapid
- Soak: 20 users, 30 min

**Note**: User will run load tests locally after merge (requires running app + PostgreSQL).
```

### After CCW Completes

User must execute load tests locally:

```bash
# 1. Merge code
git merge /claude-project-0129d

# 2. Install dependencies
pip install locust

# 3. Start app
python startup.py

# 4. Run load tests
python tests/load/run_load_tests.py --all

# 5. Review results
cat tests/load/results/summary_*.md
open tests/load/results/*.html
```

---

## Files Created

### Load Test Framework (5 files)
- `tests/load/locustfile.py` (~400 lines) - Main configuration
- `tests/load/scenarios/websocket_load.py` (~300 lines) - WebSocket scenarios
- `tests/load/scenarios/user_workflows.py` (~250 lines) - User journeys
- `tests/load/run_load_tests.py` (~300 lines) - Test runner
- `tests/load/README.md` - Usage guide

### Results Directory
- `tests/load/results/` (created by test runner)

**Total**: 5 code files + 1 directory

---

## Completion Checklist

### Pre-Execution
- [ ] Verify 0129a merged (working tests)
- [ ] Install Locust locally: `pip install locust`
- [ ] Review load test scenarios
- [ ] Plan local execution environment

### During Execution (CCW)
- [ ] Create locustfile.py (Phase 1)
- [ ] Create websocket_load.py (Phase 2)
- [ ] Create user_workflows.py (Phase 3)
- [ ] Create run_load_tests.py (Phase 4)
- [ ] Create README.md (Phase 5)
- [ ] CCW agent marks handover COMPLETE

### Post-Merge (Local Execution - REQUIRED)
- [ ] Merge /claude-project-0129d to main
- [ ] Install Locust: `pip install locust`
- [ ] Start PostgreSQL
- [ ] Start application: `python startup.py`
- [ ] Run quick test (5 users, 1 min)
- [ ] Run all scenarios: `python tests/load/run_load_tests.py --all`
- [ ] Review HTML reports (open in browser)
- [ ] Review summary report
- [ ] Document capacity findings

### Validation
- [ ] All load test files created
- [ ] Locust runs without errors
- [ ] All 5 scenarios complete successfully
- [ ] Results generated (HTML + JSON + summary)
- [ ] Capacity metrics documented
- [ ] Bottlenecks identified (if any)

### Final Steps
- [ ] Update status in 0129 parent handover
- [ ] Commit load test results to repository
- [ ] Add capacity metrics to documentation
- [ ] Create GitHub issues for bottlenecks found
- [ ] Document scaling recommendations

---

## Expected Results

Based on typical single-server deployment:

### Capacity Estimates

- **Normal Load (10 users)**: Should handle easily, <100ms p95 ✅
- **Peak Load (50 users)**: Likely successful, <200ms p95 ⚠️
- **Stress Test (100 users)**: May show degradation, <500ms p95 ⚠️
- **Spike Test**: Connection spike may cause temporary delays ⚠️
- **Soak Test (20 users, 30 min)**: Should be stable, watch for memory growth ✅

### Likely Bottlenecks

1. **Database Connections**: Connection pool may exhaust at 50+ users
2. **CPU**: Single-threaded endpoints may bottleneck
3. **WebSocket**: Too many connections may slow broadcast
4. **Memory**: Sustained load may reveal leaks

**Note**: Results will vary based on hardware. User's local machine is the baseline.

---

## Risk Mitigation

### Risk: Load Tests Overwhelm System

**Mitigation**:
- Start with small tests (5 users, 1 min)
- Gradually increase load
- Monitor system resources
- Use cool-down between tests

### Risk: Data Pollution

**Mitigation**:
- Use test tenant keys
- Clean up test data after tests
- Use isolated test database
- Document cleanup procedure

### Risk: Hardware Limitations

**Mitigation**:
- Document hardware specs
- Focus on relative performance
- Set realistic expectations
- Plan for production hardware

---

## Next Steps After Completion

1. **Capacity Planning**
   - Document maximum capacity
   - Plan infrastructure scaling
   - Identify optimization targets

2. **Optimization Backlog**
   - Create issues for bottlenecks
   - Prioritize performance improvements
   - Plan optimization handovers

3. **Monitoring Setup**
   - Implement resource monitoring
   - Set up alerts for capacity limits
   - Track metrics over time

4. **Documentation**
   - Update CLAUDE.md with capacity notes
   - Add load test results to docs/
   - Document scaling recommendations

---

## Implementation Completion Summary

### Date: 2025-11-12
### Agent: Claude Code CLI (Session: project-0129d)
### Status: ✅ COMPLETE (CCW Phase)

### What Was Built

**Comprehensive Locust Load Testing Framework**:
- 2,403 lines of production-ready code across 8 files
- 5 complete test scenarios (normal, peak, stress, spike, soak)
- Realistic user workflow simulations
- WebSocket stress testing capabilities
- Automated test orchestration and reporting

**Core Components Created**:

1. **Main Framework** (`tests/load/locustfile.py` - 450 lines)
   - 3 user types: NormalLoadUser, PeakLoadUser, StressTestUser
   - 4 task sets: ProductManagement, ProjectManagement, AgentJobs, Templates
   - FastHttpUser for optimal performance
   - Weighted task distribution for realistic simulation

2. **Test Orchestrator** (`tests/load/run_load_tests.py` - 350 lines)
   - Automated scenario runner (all 5 scenarios)
   - Generates HTML, CSV, JSON reports
   - Creates markdown summary with recommendations
   - Cool-down periods between tests
   - Comprehensive error handling

3. **WebSocket Testing** (`tests/load/scenarios/websocket_load.py` - 300 lines)
   - Connection scaling validation
   - Message throughput testing
   - Connection stability tests (soak testing)
   - 3 user types: Normal, Stress, LongLived

4. **User Workflow Testing** (`tests/load/scenarios/user_workflows.py` - 400 lines)
   - NewUserOnboarding: Complete onboarding journey
   - PowerUserWorkflow: Multi-product management
   - TeamCollaborationWorkflow: Team member interactions
   - Sequential task sets for realistic flows

5. **Documentation** (`tests/load/README.md` - 800 lines)
   - Complete usage guide
   - Detailed scenario descriptions
   - Result interpretation guide
   - Troubleshooting section
   - Best practices and tips

### Test Scenarios Implemented

1. **Normal Load**: 10 users, 5 min (typical usage)
2. **Peak Load**: 50 users, 5 min (peak hours)
3. **Stress Test**: 100 users, 2 min (system limits)
4. **Spike Test**: 0→100→0 rapid (scaling behavior)
5. **Soak Test**: 20 users, 30 min (memory leak detection)

### Files Created

- `tests/load/locustfile.py` (450 lines)
- `tests/load/run_load_tests.py` (350 lines)
- `tests/load/scenarios/websocket_load.py` (300 lines)
- `tests/load/scenarios/user_workflows.py` (400 lines)
- `tests/load/README.md` (800 lines)
- `tests/load/.gitignore`
- `tests/load/__init__.py`
- `tests/load/scenarios/__init__.py`

### Installation Impact

**New Dependencies Required**:
```bash
pip install locust websocket-client
```

No changes to core application code - purely testing infrastructure.

### Usage

**Quick Test**:
```bash
locust -f tests/load/locustfile.py --host=http://localhost:7272 \
       --headless -u 5 -r 1 -t 1m
```

**Run All Scenarios**:
```bash
python tests/load/run_load_tests.py --all
```

### Next Steps (User Action Required)

⚠️ **Load tests must be run locally** with running application:

1. Merge branch: `git merge claude/project-0129d-011CV3AW445ugaV87RqLFJNx`
2. Install Locust: `pip install locust websocket-client`
3. Start app: `python startup.py`
4. Run tests: `python tests/load/run_load_tests.py --all`
5. Review results in `tests/load/results/`

### Status

✅ **Production Ready** (CCW Phase Complete)
- All code written and tested syntactically
- Comprehensive documentation provided
- Framework ready for execution
- Awaiting local execution to generate performance data

### Git Commit

- **Branch**: `claude/project-0129d-011CV3AW445ugaV87RqLFJNx`
- **Commit**: `4d6c601` - "feat(0129d): Add comprehensive Locust load testing framework"
- **Pushed**: ✅ Successfully pushed to remote

### Related Handovers

- Part of **Handover 0129**: Integration Testing & Performance Validation Phase
- Sibling handovers: 0129a (Fix Tests), 0129b (Benchmarks), 0129c (Security)

---

**Document Version**: 1.0
**Last Updated**: 2025-11-12
**Author**: Documentation Manager Agent
**Review Status**: ✅ COMPLETE - Ready for Local Execution
