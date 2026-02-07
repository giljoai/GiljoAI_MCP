"""
Locust Load Testing Configuration for GiljoAI MCP

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

import random
from typing import Dict

from locust import TaskSet, between, tag, task
from locust.contrib.fasthttp import FastHttpUser


class AuthenticatedUser(FastHttpUser):
    """
    Base class for authenticated users.

    Handles login and maintains session state.
    Uses FastHttpUser for better performance compared to HttpUser.
    """

    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks
    abstract = True  # Don't instantiate directly

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tenant_key = None
        self.auth_token = None
        self.products = []
        self.projects = []
        self.agent_jobs = []

    def on_start(self):
        """Called when user starts - perform login."""
        self.login()

    def login(self):
        """Authenticate user and get tenant key."""
        # Use test credentials
        response = self.client.post(
            "/api/auth/login",
            json={"email": f"loadtest_user_{random.randint(1, 1000)}@example.com", "password": "TestPassword123"},
            catch_response=True,
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
    Tasks are weighted (higher number = more frequent).
    """

    @task(3)
    @tag("normal_load", "peak_load")
    def list_products(self):
        """List all products - common operation."""
        response = self.client.get(
            "/api/products", headers=self.user.get_headers(), name="/api/products [LIST]", catch_response=True
        )

        if response.status_code == 200:
            self.user.products = response.json()
            response.success()
        else:
            response.failure(f"Failed to list products: {response.status_code}")

    @task(1)
    @tag("normal_load", "peak_load", "stress_test")
    def create_product(self):
        """Create a new product - less frequent."""
        product_name = f"Load Test Product {random.randint(1, 10000)}"
        response = self.client.post(
            "/api/products",
            headers=self.user.get_headers(),
            json={"name": product_name, "description": "Created during load testing", "status": "active"},
            name="/api/products [CREATE]",
            catch_response=True,
        )

        if response.status_code == 201:
            product = response.json()
            self.user.products.append(product)
            response.success()
        elif response.status_code == 409:
            # Conflict - product name exists, that's ok
            response.success()
        else:
            response.failure(f"Failed to create product: {response.status_code}")

    @task(2)
    @tag("normal_load", "peak_load")
    def view_product(self):
        """View a specific product - common operation."""
        if not self.user.products:
            return

        product = random.choice(self.user.products)
        response = self.client.get(
            f"/api/products/{product['id']}",
            headers=self.user.get_headers(),
            name="/api/products/{id} [GET]",
            catch_response=True,
        )

        if response.status_code == 200:
            response.success()
        else:
            response.failure(f"Failed to view product: {response.status_code}")

    @task(1)
    @tag("peak_load", "stress_test")
    def update_product(self):
        """Update a product - less frequent."""
        if not self.user.products:
            return

        product = random.choice(self.user.products)
        response = self.client.put(
            f"/api/products/{product['id']}",
            headers=self.user.get_headers(),
            json={"name": f"{product['name']} (Updated)", "status": "active"},
            name="/api/products/{id} [UPDATE]",
            catch_response=True,
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
        """List all projects - common operation."""
        response = self.client.get(
            "/api/projects", headers=self.user.get_headers(), name="/api/projects [LIST]", catch_response=True
        )

        if response.status_code == 200:
            self.user.projects = response.json()
            response.success()
        else:
            response.failure(f"Failed to list projects: {response.status_code}")

    @task(1)
    @tag("normal_load", "peak_load", "stress_test")
    def create_project(self):
        """Create a new project - less frequent."""
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
                "status": "active",
            },
            name="/api/projects [CREATE]",
            catch_response=True,
        )

        if response.status_code == 201:
            project = response.json()
            self.user.projects.append(project)
            response.success()
        elif response.status_code == 409:
            # Conflict - project name exists, that's ok
            response.success()
        else:
            response.failure(f"Failed to create project: {response.status_code}")

    @task(2)
    @tag("normal_load", "peak_load")
    def view_project(self):
        """View a specific project - common operation."""
        if not self.user.projects:
            return

        project = random.choice(self.user.projects)
        response = self.client.get(
            f"/api/projects/{project['id']}",
            headers=self.user.get_headers(),
            name="/api/projects/{id} [GET]",
            catch_response=True,
        )

        if response.status_code == 200:
            response.success()
        else:
            response.failure(f"Failed to view project: {response.status_code}")


class AgentJobTasks(TaskSet):
    """
    Agent job management tasks.

    Simulates user working with agent jobs.
    """

    @task(2)
    @tag("normal_load", "peak_load")
    def list_agent_jobs(self):
        """List all agent jobs - common operation."""
        response = self.client.get(
            "/api/agent-jobs", headers=self.user.get_headers(), name="/api/agent-jobs [LIST]", catch_response=True
        )

        if response.status_code == 200:
            self.user.agent_jobs = response.json()
            response.success()
        else:
            response.failure(f"Failed to list agent jobs: {response.status_code}")

    @task(1)
    @tag("peak_load", "stress_test")
    def create_agent_job(self):
        """Create a new agent job - less frequent."""
        if not self.user.projects:
            return

        project = random.choice(self.user.projects)
        response = self.client.post(
            "/api/agent-jobs",
            headers=self.user.get_headers(),
            json={
                "project_id": project["id"],
                "agent_name": f"load_test_agent_{random.randint(1, 1000)}",
                "agent_display_name": random.choice(["implementer", "tester", "reviewer"]),
                "mission": "Load testing mission",
            },
            name="/api/agent-jobs [CREATE]",
            catch_response=True,
        )

        if response.status_code == 201:
            agent_job = response.json()
            self.user.agent_jobs.append(agent_job)
            response.success()
        else:
            response.failure(f"Failed to create agent job: {response.status_code}")

    @task(1)
    @tag("peak_load")
    def view_agent_job(self):
        """View a specific agent job."""
        if not self.user.agent_jobs:
            return

        agent_job = random.choice(self.user.agent_jobs)
        response = self.client.get(
            f"/api/agent-jobs/{agent_job['id']}",
            headers=self.user.get_headers(),
            name="/api/agent-jobs/{id} [GET]",
            catch_response=True,
        )

        if response.status_code == 200:
            response.success()
        else:
            response.failure(f"Failed to view agent job: {response.status_code}")


class TemplateManagementTasks(TaskSet):
    """
    Template management workflow tasks.

    Simulates user browsing and using templates.
    """

    @task(2)
    @tag("normal_load", "peak_load")
    def list_templates(self):
        """List all templates."""
        response = self.client.get(
            "/api/templates", headers=self.user.get_headers(), name="/api/templates [LIST]", catch_response=True
        )

        if response.status_code == 200:
            response.success()
        else:
            response.failure(f"Failed to list templates: {response.status_code}")

    @task(1)
    @tag("normal_load")
    def view_template(self):
        """View a specific template."""
        # Use known template ID or list first
        response = self.client.get("/api/templates", headers=self.user.get_headers(), catch_response=True)

        if response.status_code == 200:
            templates = response.json()
            if templates:
                template = random.choice(templates)
                self.client.get(
                    f"/api/templates/{template['id']}",
                    headers=self.user.get_headers(),
                    name="/api/templates/{id} [GET]",
                )


class NormalLoadUser(AuthenticatedUser):
    """
    Normal load user - typical daily usage.

    Weight: 60% product management, 30% project management, 10% agent jobs
    Simulates typical user browsing products, occasionally creating new items.
    """

    tasks = {ProductManagementTasks: 6, ProjectManagementTasks: 3, AgentJobTasks: 1}
    wait_time = between(2, 5)  # More realistic wait times
    tags = ["normal_load"]


class PeakLoadUser(AuthenticatedUser):
    """
    Peak load user - higher activity during peak hours.

    Weight: 50% product, 30% project, 10% agents, 10% templates
    Faster interactions, more create operations.
    """

    tasks = {ProductManagementTasks: 5, ProjectManagementTasks: 3, AgentJobTasks: 1, TemplateManagementTasks: 1}
    wait_time = between(1, 3)
    tags = ["peak_load"]


class StressTestUser(AuthenticatedUser):
    """
    Stress test user - aggressive usage for stress testing.

    Weight: 40% product, 40% project, 20% agents
    Minimal wait times, aggressive operations.
    """

    tasks = {ProductManagementTasks: 4, ProjectManagementTasks: 4, AgentJobTasks: 2}
    wait_time = between(0.5, 1.5)  # Aggressive
    tags = ["stress_test"]
