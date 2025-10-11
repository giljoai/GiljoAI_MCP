"""
Health Check Integration Module

Shows how health checks integrate with installers and GUI
"""

import asyncio
from typing import Optional, Callable, Any
from dataclasses import dataclass

from health import HealthChecker, HealthStatus, HealthReport


@dataclass
class InstallationHealthCheck:
    """
    Unified health check for installation process
    """

    health_checker: HealthChecker
    gui_callback: Optional[Callable[[dict], None]] = None

    async def pre_installation_check(self) -> dict[str, Any]:
        """
        Check system before installation

        Returns:
            Dictionary with readiness status and details
        """
        report = await self.health_checker.check_installation_readiness()

        result = {"ready": report.overall_status == HealthStatus.HEALTHY, "warnings": [], "errors": [], "details": {}}

        for component in report.components:
            if component.status == HealthStatus.ERROR:
                result["errors"].append(f"{component.name}: {component.message}")
            elif component.status == HealthStatus.WARNING:
                result["warnings"].append(f"{component.name}: {component.message}")

            result["details"][component.name] = {
                "status": component.status.value,
                "message": component.message,
                "details": component.details,
            }

        # Update GUI if callback provided
        if self.gui_callback:
            self.gui_callback(
                {"phase": "pre_installation", "status": "ready" if result["ready"] else "not_ready", "report": result}
            )

        return result

    async def check_database_health(self) -> dict[str, Any]:
        """
        Check health of database services

        Returns:
            Dictionary with database status
        """
        report = await self.health_checker.check_database_services()

        postgresql_status = None
        redis_status = None

        for component in report.components:
            if component.name == "PostgreSQL":
                postgresql_status = component
            elif component.name == "Redis":
                redis_status = component

        result = {
            "postgresql": {
                "healthy": postgresql_status and postgresql_status.status == HealthStatus.HEALTHY,
                "status": postgresql_status.status.value if postgresql_status else "unknown",
                "message": postgresql_status.message if postgresql_status else "Not checked",
                "details": postgresql_status.details if postgresql_status else {},
            },
            "redis": {
                "healthy": redis_status and redis_status.status == HealthStatus.HEALTHY,
                "status": redis_status.status.value if redis_status else "unknown",
                "message": redis_status.message if redis_status else "Not checked",
                "details": redis_status.details if redis_status else {},
            },
            "both_healthy": (
                postgresql_status
                and postgresql_status.status == HealthStatus.HEALTHY
                and redis_status
                and redis_status.status == HealthStatus.HEALTHY
            ),
        }

        # Update GUI if callback provided
        if self.gui_callback:
            self.gui_callback(
                {
                    "phase": "database_check",
                    "postgresql": result["postgresql"]["healthy"],
                    "redis": result["redis"]["healthy"],
                    "report": result,
                }
            )

        return result

    async def post_installation_verification(self) -> dict[str, Any]:
        """
        Verify installation completed successfully

        Returns:
            Dictionary with verification results
        """
        # Check all components
        report = await self.health_checker.check_all()

        # Determine what was successfully installed
        installed_services = []
        failed_services = []

        for component in report.components:
            if component.name in ["PostgreSQL", "Redis", "Docker"]:
                if component.status == HealthStatus.HEALTHY:
                    installed_services.append(component.name)
                elif component.status != HealthStatus.NOT_INSTALLED:
                    failed_services.append(component.name)

        result = {
            "success": len(failed_services) == 0,
            "installed": installed_services,
            "failed": failed_services,
            "overall_status": report.overall_status.value,
            "report_summary": report.get_summary(),
        }

        # Update GUI if callback provided
        if self.gui_callback:
            self.gui_callback(
                {
                    "phase": "post_installation",
                    "success": result["success"],
                    "installed": result["installed"],
                    "failed": result["failed"],
                }
            )

        return result

    async def continuous_monitoring(self, interval: int = 5, duration: int = 60):
        """
        Monitor services continuously

        Args:
            interval: Seconds between checks
            duration: Total monitoring duration in seconds
        """
        start_time = asyncio.get_event_loop().time()
        check_count = 0

        while asyncio.get_event_loop().time() - start_time < duration:
            check_count += 1

            # Check database services
            db_health = await self.check_database_health()

            # Update GUI with monitoring data
            if self.gui_callback:
                self.gui_callback(
                    {
                        "phase": "monitoring",
                        "check_number": check_count,
                        "elapsed_time": asyncio.get_event_loop().time() - start_time,
                        "postgresql": db_health["postgresql"]["healthy"],
                        "redis": db_health["redis"]["healthy"],
                    }
                )

            # Wait for next check
            await asyncio.sleep(interval)

            # Break early if both services are healthy
            if db_health["both_healthy"]:
                return {"status": "success", "message": "All services healthy", "checks_performed": check_count}

        return {"status": "timeout", "message": "Monitoring period ended", "checks_performed": check_count}


class HealthCheckOrchestrator:
    """
    Orchestrates health checks across multiple installers
    """

    def __init__(self, config: Optional[dict] = None):
        """Initialize orchestrator with optional config"""
        self.health_checker = HealthChecker(config)
        self.installation_checker = InstallationHealthCheck(self.health_checker)

    async def full_installation_workflow(self, gui_callback: Optional[Callable] = None):
        """
        Complete installation workflow with health checks

        Args:
            gui_callback: Optional callback for GUI updates
        """
        self.installation_checker.gui_callback = gui_callback

        # Step 1: Pre-installation check
        pre_check = await self.installation_checker.pre_installation_check()
        if not pre_check["ready"]:
            return {
                "status": "aborted",
                "reason": "System not ready",
                "errors": pre_check["errors"],
                "warnings": pre_check["warnings"],
            }

        # Step 2: Check if services already installed
        db_check = await self.installation_checker.check_database_health()

        needs_postgresql = not db_check["postgresql"]["healthy"]
        needs_redis = not db_check["redis"]["healthy"]

        if not needs_postgresql and not needs_redis:
            return {"status": "skipped", "reason": "Services already installed and healthy"}

        # Step 3: Return installation requirements
        return {
            "status": "ready",
            "needs_postgresql": needs_postgresql,
            "needs_redis": needs_redis,
            "current_state": db_check,
        }

    async def parallel_service_check(self) -> dict[str, Any]:
        """
        Check PostgreSQL and Redis in parallel

        Returns:
            Combined health status
        """
        # Create tasks for parallel execution
        tasks = [
            self.health_checker._check_postgresql(),
            self.health_checker._check_redis(),
            self.health_checker._check_ports(),
        ]

        # Execute in parallel
        await asyncio.gather(*tasks, return_exceptions=True)

        # Build report
        report = HealthReport(
            overall_status=self.health_checker._calculate_overall_status(),
            components=self.health_checker.components,
            total_check_time=sum(c.check_time for c in self.health_checker.components),
            system_info=self.health_checker._get_system_info(),
        )

        return {
            "report": report.to_dict(),
            "summary": report.get_summary(),
            "postgresql_ready": any(
                c.name == "PostgreSQL" and c.status == HealthStatus.HEALTHY for c in self.health_checker.components
            ),
            "redis_ready": any(
                c.name == "Redis" and c.status == HealthStatus.HEALTHY for c in self.health_checker.components
            ),
            "ports_available": any(
                c.name == "Ports" and c.status == HealthStatus.HEALTHY for c in self.health_checker.components
            ),
        }


# Example usage
async def example_integration():
    """
    Example showing health check integration
    """

    def gui_update(data: dict):
        """Mock GUI callback"""
        print(f"[GUI Update] Phase: {data.get('phase', 'unknown')}")
        if "postgresql" in data:
            print(f"  PostgreSQL: {'Ready' if data['postgresql'] else 'Not Ready'}")
        if "redis" in data:
            print(f"  Redis: {'Ready' if data['redis'] else 'Not Ready'}")

    # Create orchestrator
    orchestrator = HealthCheckOrchestrator({"postgresql": {"port": 5432}, "redis": {"port": 6379}})

    # Run full workflow
    result = await orchestrator.full_installation_workflow(gui_update)
    print(f"\nWorkflow Result: {result['status']}")

    if result["status"] == "ready":
        print(f"  Needs PostgreSQL: {result['needs_postgresql']}")
        print(f"  Needs Redis: {result['needs_redis']}")

    # Parallel service check
    parallel_result = await orchestrator.parallel_service_check()
    print(f"\nParallel Check Complete:")
    print(f"  PostgreSQL Ready: {parallel_result['postgresql_ready']}")
    print(f"  Redis Ready: {parallel_result['redis_ready']}")
    print(f"  Ports Available: {parallel_result['ports_available']}")


if __name__ == "__main__":
    # Run example
    asyncio.run(example_integration())
