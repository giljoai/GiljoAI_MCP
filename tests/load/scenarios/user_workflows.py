"""
Realistic User Workflow Scenarios for GiljoAI MCP

Simulates complete user journeys through the application.
Tests end-to-end workflows that real users would follow.

Usage:
    # Run onboarding workflow
    locust -f tests/load/scenarios/user_workflows.py --host=http://localhost:7272 \
           --headless -u 10 -r 2 -t 5m
"""

import os
import sys

from locust import SequentialTaskSet, between, task


# Add parent directory to path to import locustfile
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
import random

from tests.load.locustfile import AuthenticatedUser


class NewUserOnboarding(SequentialTaskSet):
    """
    Simulates new user onboarding workflow.

    Complete user journey:
    1. Login
    2. Create first product
    3. Create first project
    4. View dashboard
    5. Browse templates
    6. Create agent job

    This is a sequential task set - tasks execute in order, not randomly.
    """

    @task
    def step1_login(self):
        """User logs in for the first time."""
        self.user.login()
        self.wait()

    @task
    def step2_create_first_product(self):
        """User creates their first product."""
        response = self.client.post(
            "/api/products",
            headers=self.user.get_headers(),
            json={"name": "My First Product", "description": "Getting started with GiljoAI MCP", "status": "active"},
            name="Onboarding: Create First Product",
            catch_response=True,
        )

        if response.status_code == 201:
            self.user.products.append(response.json())
            response.success()
        elif response.status_code == 409:
            # Product already exists, that's ok
            response.success()
        else:
            response.failure(f"Failed to create product: {response.status_code}")

        self.wait()

    @task
    def step3_create_first_project(self):
        """User creates their first project."""
        if not self.user.products:
            return

        product = self.user.products[0]
        response = self.client.post(
            "/api/projects",
            headers=self.user.get_headers(),
            json={
                "product_id": product["id"],
                "name": "My First Project",
                "description": "Learning the platform",
                "status": "active",
            },
            name="Onboarding: Create First Project",
            catch_response=True,
        )

        if response.status_code == 201:
            self.user.projects.append(response.json())
            response.success()
        elif response.status_code == 409:
            response.success()
        else:
            response.failure(f"Failed to create project: {response.status_code}")

        self.wait()

    @task
    def step4_view_dashboard(self):
        """User views the dashboard."""
        response = self.client.get(
            "/api/dashboard", headers=self.user.get_headers(), name="Onboarding: View Dashboard", catch_response=True
        )

        if response.status_code in [200, 404]:
            # 404 is ok if dashboard endpoint doesn't exist yet
            response.success()
        else:
            response.failure(f"Dashboard failed: {response.status_code}")

        self.wait()

    @task
    def step5_browse_templates(self):
        """User browses available templates."""
        response = self.client.get(
            "/api/templates", headers=self.user.get_headers(), name="Onboarding: Browse Templates", catch_response=True
        )

        if response.status_code == 200:
            response.success()
        else:
            response.failure(f"Failed to browse templates: {response.status_code}")

        self.wait()

    @task
    def step6_create_first_agent_job(self):
        """User creates their first agent job."""
        if not self.user.projects:
            return

        project = self.user.projects[0]
        response = self.client.post(
            "/api/agent-jobs",
            headers=self.user.get_headers(),
            json={
                "project_id": project["id"],
                "agent_name": "my_first_agent",
                "agent_display_name": "implementer",
                "mission": "Help me build something amazing",
            },
            name="Onboarding: Create First Agent Job",
            catch_response=True,
        )

        if response.status_code == 201:
            response.success()
        else:
            response.failure(f"Failed to create agent job: {response.status_code}")

        self.wait()


class PowerUserWorkflow(SequentialTaskSet):
    """
    Simulates power user managing multiple products.

    Advanced user journey:
    1. Login
    2. List all products
    3. Create new product
    4. Create multiple projects
    5. Manage agent jobs
    6. Monitor progress
    7. Update project status
    """

    @task
    def step1_login(self):
        """Power user logs in."""
        self.user.login()
        self.wait()

    @task
    def step2_list_all_products(self):
        """List all existing products."""
        response = self.client.get(
            "/api/products", headers=self.user.get_headers(), name="Power User: List All Products", catch_response=True
        )

        if response.status_code == 200:
            self.user.products = response.json()
            response.success()
        else:
            response.failure(f"Failed to list products: {response.status_code}")

        self.wait()

    @task
    def step3_create_new_product(self):
        """Create a new product for a new initiative."""
        product_name = f"Product Initiative {random.randint(100, 999)}"
        response = self.client.post(
            "/api/products",
            headers=self.user.get_headers(),
            json={"name": product_name, "description": "New product initiative", "status": "active"},
            name="Power User: Create New Product",
            catch_response=True,
        )

        if response.status_code == 201:
            self.user.products.append(response.json())
            response.success()
        elif response.status_code == 409:
            response.success()
        else:
            response.failure(f"Failed to create product: {response.status_code}")

        self.wait()

    @task
    def step4_create_multiple_projects(self):
        """Create multiple projects for the product."""
        if not self.user.products:
            return

        product = self.user.products[0]

        # Create 3 projects
        for i in range(3):
            project_name = f"Sprint {i + 1} - {random.choice(['Backend', 'Frontend', 'Infrastructure'])}"
            response = self.client.post(
                "/api/projects",
                headers=self.user.get_headers(),
                json={
                    "product_id": product["id"],
                    "name": project_name,
                    "description": f"Sprint {i + 1} work",
                    "status": "active",
                },
                name="Power User: Create Project",
                catch_response=True,
            )

            if response.status_code == 201:
                self.user.projects.append(response.json())
                response.success()
            elif response.status_code == 409:
                response.success()
            else:
                response.failure(f"Failed to create project: {response.status_code}")

            self.wait()

    @task
    def step5_manage_agent_jobs(self):
        """Create and manage multiple agent jobs."""
        if not self.user.projects:
            return

        project = self.user.projects[0]

        # Create orchestrator
        response = self.client.post(
            "/api/agent-jobs",
            headers=self.user.get_headers(),
            json={
                "project_id": project["id"],
                "agent_name": "orchestrator_main",
                "agent_display_name": "orchestrator",
                "mission": "Coordinate development tasks",
            },
            name="Power User: Create Orchestrator",
            catch_response=True,
        )

        if response.status_code == 201:
            response.success()
        else:
            response.failure(f"Failed to create orchestrator: {response.status_code}")

        self.wait()

        # Create implementer agents
        for i in range(2):
            agent_name = f"implementer_{i + 1}"
            response = self.client.post(
                "/api/agent-jobs",
                headers=self.user.get_headers(),
                json={
                    "project_id": project["id"],
                    "agent_name": agent_name,
                    "agent_display_name": "implementer",
                    "mission": f"Implement feature {i + 1}",
                },
                name="Power User: Create Implementer",
                catch_response=True,
            )

            if response.status_code == 201:
                response.success()

            self.wait()

    @task
    def step6_monitor_progress(self):
        """Monitor job progress across projects."""
        # List all agent jobs
        response = self.client.get(
            "/api/agent-jobs", headers=self.user.get_headers(), name="Power User: Monitor All Jobs", catch_response=True
        )

        if response.status_code == 200:
            response.success()
        else:
            response.failure(f"Failed to monitor jobs: {response.status_code}")

        self.wait()

        # Check specific project status
        if self.user.projects:
            project = self.user.projects[0]
            self.client.get(
                f"/api/projects/{project['id']}",
                headers=self.user.get_headers(),
                name="Power User: Check Project Status",
            )

        self.wait()

    @task
    def step7_update_project_status(self):
        """Update project status based on progress."""
        if not self.user.projects:
            return

        project = self.user.projects[0]
        response = self.client.put(
            f"/api/projects/{project['id']}",
            headers=self.user.get_headers(),
            json={"name": project["name"], "status": random.choice(["active", "in_progress", "completed"])},
            name="Power User: Update Project Status",
            catch_response=True,
        )

        if response.status_code == 200:
            response.success()
        else:
            response.failure(f"Failed to update project: {response.status_code}")

        self.wait()


class TeamCollaborationWorkflow(SequentialTaskSet):
    """
    Simulates team member collaborating on shared project.

    Collaboration workflow:
    1. Login
    2. View shared products
    3. Select active project
    4. Review agent jobs
    5. Create new task
    6. Monitor team activity
    """

    @task
    def step1_login(self):
        """Team member logs in."""
        self.user.login()
        self.wait()

    @task
    def step2_view_shared_products(self):
        """View products shared with team."""
        response = self.client.get(
            "/api/products", headers=self.user.get_headers(), name="Team: View Shared Products", catch_response=True
        )

        if response.status_code == 200:
            self.user.products = response.json()
            response.success()
        else:
            response.failure(f"Failed to view products: {response.status_code}")

        self.wait()

    @task
    def step3_select_active_project(self):
        """Select and view active project."""
        response = self.client.get(
            "/api/projects", headers=self.user.get_headers(), name="Team: List Projects", catch_response=True
        )

        if response.status_code == 200:
            self.user.projects = response.json()
            response.success()

            # View first active project
            if self.user.projects:
                project = self.user.projects[0]
                self.client.get(
                    f"/api/projects/{project['id']}", headers=self.user.get_headers(), name="Team: View Project Details"
                )
        else:
            response.failure(f"Failed to list projects: {response.status_code}")

        self.wait()

    @task
    def step4_review_agent_jobs(self):
        """Review existing agent jobs."""
        response = self.client.get(
            "/api/agent-jobs", headers=self.user.get_headers(), name="Team: Review Agent Jobs", catch_response=True
        )

        if response.status_code == 200:
            self.user.agent_jobs = response.json()
            response.success()
        else:
            response.failure(f"Failed to review jobs: {response.status_code}")

        self.wait()

    @task
    def step5_create_task(self):
        """Create a new task/agent job."""
        if not self.user.projects:
            return

        project = self.user.projects[0]
        response = self.client.post(
            "/api/agent-jobs",
            headers=self.user.get_headers(),
            json={
                "project_id": project["id"],
                "agent_name": f"team_task_{random.randint(1, 100)}",
                "agent_display_name": random.choice(["implementer", "reviewer", "tester"]),
                "mission": "Team collaboration task",
            },
            name="Team: Create Task",
            catch_response=True,
        )

        if response.status_code == 201:
            response.success()

        self.wait()

    @task
    def step6_monitor_team_activity(self):
        """Monitor team activity and progress."""
        # Check project updates
        if self.user.projects:
            project = self.user.projects[0]
            self.client.get(
                f"/api/projects/{project['id']}", headers=self.user.get_headers(), name="Team: Monitor Activity"
            )

        self.wait()


# User classes for different workflows
class OnboardingUser(AuthenticatedUser):
    """User going through onboarding workflow."""

    tasks = [NewUserOnboarding]
    wait_time = between(2, 5)
    weight = 2


class PowerUser(AuthenticatedUser):
    """Power user with heavy usage."""

    tasks = [PowerUserWorkflow]
    wait_time = between(1, 3)
    weight = 3


class TeamMember(AuthenticatedUser):
    """Team member collaborating on projects."""

    tasks = [TeamCollaborationWorkflow]
    wait_time = between(2, 4)
    weight = 2
