"""
Core Profile System for GiljoAI MCP Installer

This module defines and manages installation profiles that determine
how the GiljoAI MCP system is configured and deployed.
"""

import json
import tempfile
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any


class ProfileType(Enum):
    """Enumeration of available installation profile types."""

    LOCAL_DEVELOPMENT = "local_development"
    NETWORK_SHARED = "network_shared"
    HIGH_PERFORMANCE = "high_performance"
    CONTAINERIZED = "containerized"


@dataclass
class ProfileConfiguration:
    """Configuration settings for a profile."""

    database_type: str
    api_enabled: bool
    websocket_enabled: bool
    auth_method: str
    deployment_mode: str
    resource_limits: Dict[str, Any] = field(default_factory=dict)
    network_settings: Dict[str, Any] = field(default_factory=dict)
    storage_settings: Dict[str, Any] = field(default_factory=dict)
    performance_settings: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProfileConfiguration":
        """Create configuration from dictionary."""
        return cls(**data)


@dataclass
class ProfileDependencies:
    """System dependencies required for a profile."""

    python_version: str
    required_packages: List[str] = field(default_factory=list)
    optional_packages: List[str] = field(default_factory=list)
    system_requirements: Dict[str, Any] = field(default_factory=dict)
    external_services: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert dependencies to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProfileDependencies":
        """Create dependencies from dictionary."""
        return cls(**data)


@dataclass
class Profile:
    """Installation profile definition."""

    name: str
    type: ProfileType
    description: str
    configuration: ProfileConfiguration
    dependencies: ProfileDependencies
    recommended_for: List[str] = field(default_factory=list)
    limitations: List[str] = field(default_factory=list)
    post_install_steps: List[str] = field(default_factory=list)

    def to_json(self) -> str:
        """Serialize profile to JSON string."""
        data = {
            "name": self.name,
            "type": self.type.value,
            "description": self.description,
            "configuration": self.configuration.to_dict(),
            "dependencies": self.dependencies.to_dict(),
            "recommended_for": self.recommended_for,
            "limitations": self.limitations,
            "post_install_steps": self.post_install_steps,
        }
        return json.dumps(data, indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> "Profile":
        """Deserialize profile from JSON string."""
        data = json.loads(json_str)
        return cls(
            name=data["name"],
            type=ProfileType(data["type"]),
            description=data["description"],
            configuration=ProfileConfiguration.from_dict(data["configuration"]),
            dependencies=ProfileDependencies.from_dict(data["dependencies"]),
            recommended_for=data.get("recommended_for", []),
            limitations=data.get("limitations", []),
            post_install_steps=data.get("post_install_steps", []),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert profile to dictionary."""
        return {
            "name": self.name,
            "type": self.type.value,
            "description": self.description,
            "configuration": self.configuration.to_dict(),
            "dependencies": self.dependencies.to_dict(),
            "recommended_for": self.recommended_for,
            "limitations": self.limitations,
            "post_install_steps": self.post_install_steps,
        }


class ProfileManager:
    """Manager class for handling installation profiles."""

    def __init__(self):
        """Initialize ProfileManager with default profiles."""
        self._profiles: Dict[ProfileType, Profile] = {}
        self._initialize_default_profiles()

    def _initialize_default_profiles(self):
        """Initialize default profiles for each ProfileType."""

        # Local Development Profile
        self._profiles[ProfileType.LOCAL_DEVELOPMENT] = Profile(
            name="Local Development",
            type=ProfileType.LOCAL_DEVELOPMENT,
            description="Ideal for individual developers working on local machines. Uses SQLite for simplicity and requires minimal configuration.",
            configuration=ProfileConfiguration(
                database_type="sqlite",
                api_enabled=True,
                websocket_enabled=True,
                auth_method="none",
                deployment_mode="local",
                resource_limits={"max_agents": 10, "max_concurrent_tasks": 5, "memory_limit_mb": 2048},
                network_settings={
                    "host": "localhost",
                    "api_port": 8000,
                    "websocket_port": 7273,
                    "allow_external": False,
                },
                storage_settings={
                    "database_path": "~/.giljo-mcp/data.db",
                    "log_path": "~/.giljo-mcp/logs",
                    "temp_path": "~/.giljo-mcp/temp",
                },
                performance_settings={"enable_caching": True, "cache_size_mb": 256, "connection_pool_size": 5},
            ),
            dependencies=ProfileDependencies(
                python_version=">=3.9",
                required_packages=["fastmcp", "fastapi", "sqlalchemy", "httpx", "websockets", "pyyaml"],
                optional_packages=["pytest", "black", "ruff"],
                system_requirements={"min_ram_mb": 1024, "min_disk_space_mb": 500, "os": ["windows", "macos", "linux"]},
                external_services=[],
            ),
            recommended_for=[
                "Individual developers",
                "Learning and experimentation",
                "Prototype development",
                "Small projects",
            ],
            limitations=["Not suitable for team collaboration", "Limited scalability", "No built-in backup/recovery"],
            post_install_steps=[
                "Run 'python quickstart.py' to start the system",
                "Access dashboard at http://localhost:8000",
                "Check logs in ~/.giljo-mcp/logs for troubleshooting",
            ],
        )

        # Network Shared Profile
        self._profiles[ProfileType.NETWORK_SHARED] = Profile(
            name="Network Shared",
            type=ProfileType.NETWORK_SHARED,
            description="Designed for small teams sharing resources on a local network. Uses PostgreSQL for multi-user support with API key authentication.",
            configuration=ProfileConfiguration(
                database_type="postgresql",
                api_enabled=True,
                websocket_enabled=True,
                auth_method="api_key",
                deployment_mode="lan",
                resource_limits={"max_agents": 50, "max_concurrent_tasks": 20, "memory_limit_mb": 8192},
                network_settings={
                    "host": "0.0.0.0",
                    "api_port": 8000,
                    "websocket_port": 7273,
                    "allow_external": True,
                    "cors_origins": ["*"],
                },
                storage_settings={
                    "database_url": "postgresql://giljo:password@localhost/giljo_mcp",
                    "log_path": "/var/log/giljo-mcp",
                    "temp_path": str(Path(tempfile.gettempdir()) / "giljo-mcp"),
                    "shared_storage_path": "/shared/giljo-mcp",
                },
                performance_settings={
                    "enable_caching": True,
                    "cache_size_mb": 1024,
                    "connection_pool_size": 20,
                    "enable_connection_pooling": True,
                },
            ),
            dependencies=ProfileDependencies(
                python_version=">=3.9",
                required_packages=[
                    "fastmcp",
                    "fastapi",
                    "sqlalchemy",
                    "psycopg2-binary",
                    "httpx",
                    "websockets",
                    "pyyaml",
                    "python-multipart",
                    "python-jose[cryptography]",
                ],
                optional_packages=["redis", "celery", "prometheus-client"],
                system_requirements={
                    "min_ram_mb": 4096,
                    "min_disk_space_mb": 5000,
                    "os": ["windows", "macos", "linux"],
                    "network": "lan",
                },
                external_services=["postgresql"],
            ),
            recommended_for=[
                "Small development teams",
                "Department-level deployments",
                "Shared development environments",
                "Internal tools and services",
            ],
            limitations=["Requires PostgreSQL setup", "Network configuration needed", "Basic authentication only"],
            post_install_steps=[
                "Configure PostgreSQL database",
                "Generate and distribute API keys",
                "Configure firewall rules for ports 8000-7273",
                "Set up shared storage permissions",
                "Test connectivity from client machines",
            ],
        )

        # High Performance Profile
        self._profiles[ProfileType.HIGH_PERFORMANCE] = Profile(
            name="High Performance",
            type=ProfileType.HIGH_PERFORMANCE,
            description="Optimized for production workloads with advanced caching, load balancing, and monitoring. Includes Redis for caching and Celery for task queuing.",
            configuration=ProfileConfiguration(
                database_type="postgresql",
                api_enabled=True,
                websocket_enabled=True,
                auth_method="oauth2",
                deployment_mode="wan",
                resource_limits={"max_agents": 500, "max_concurrent_tasks": 100, "memory_limit_mb": 32768},
                network_settings={
                    "host": "0.0.0.0",
                    "api_port": 443,
                    "websocket_port": 443,
                    "allow_external": True,
                    "cors_origins": ["https://*.yourdomain.com"],
                    "enable_tls": True,
                    "enable_rate_limiting": True,
                    "rate_limit_requests": 1000,
                    "rate_limit_period": 60,
                },
                storage_settings={
                    "database_url": "postgresql://giljo:password@db-cluster/giljo_mcp",
                    "redis_url": "redis://redis-cluster:6379/0",
                    "log_path": "/var/log/giljo-mcp",
                    "temp_path": str(Path(tempfile.gettempdir()) / "giljo-mcp"),
                    "s3_bucket": "giljo-mcp-storage",
                    "enable_backup": True,
                    "backup_schedule": "0 2 * * *",
                },
                performance_settings={
                    "enable_caching": True,
                    "cache_backend": "redis",
                    "cache_size_mb": 8192,
                    "connection_pool_size": 100,
                    "enable_connection_pooling": True,
                    "enable_query_optimization": True,
                    "enable_async_processing": True,
                    "worker_processes": 4,
                    "threads_per_worker": 4,
                },
            ),
            dependencies=ProfileDependencies(
                python_version=">=3.9",
                required_packages=[
                    "fastmcp",
                    "fastapi",
                    "sqlalchemy",
                    "psycopg2-binary",
                    "httpx",
                    "websockets",
                    "pyyaml",
                    "redis",
                    "celery[redis]",
                    "python-multipart",
                    "python-jose[cryptography]",
                    "prometheus-client",
                    "sentry-sdk",
                    "boto3",
                ],
                optional_packages=["gunicorn", "uvicorn[standard]", "nginx", "datadog"],
                system_requirements={
                    "min_ram_mb": 16384,
                    "min_disk_space_mb": 50000,
                    "os": ["linux"],
                    "network": "wan",
                    "cpu_cores": 4,
                },
                external_services=["postgresql", "redis", "s3-compatible-storage", "oauth2-provider"],
            ),
            recommended_for=[
                "Production deployments",
                "Enterprise environments",
                "High-traffic applications",
                "Mission-critical systems",
                "Multi-region deployments",
            ],
            limitations=[
                "Complex infrastructure requirements",
                "Higher operational overhead",
                "Requires experienced administrators",
            ],
            post_install_steps=[
                "Configure PostgreSQL cluster with replication",
                "Set up Redis cluster for caching",
                "Configure OAuth2 provider integration",
                "Set up TLS certificates",
                "Configure monitoring and alerting",
                "Set up backup and disaster recovery",
                "Configure CDN for static assets",
                "Implement log aggregation",
                "Set up CI/CD pipeline",
            ],
        )

        # Containerized Profile
        self._profiles[ProfileType.CONTAINERIZED] = Profile(
            name="Containerized",
            type=ProfileType.CONTAINERIZED,
            description="Docker-based deployment for easy scaling and management. Includes Docker Compose configuration and Kubernetes manifests for orchestration.",
            configuration=ProfileConfiguration(
                database_type="postgresql",
                api_enabled=True,
                websocket_enabled=True,
                auth_method="jwt",
                deployment_mode="container",
                resource_limits={
                    "max_agents": 200,
                    "max_concurrent_tasks": 50,
                    "memory_limit_mb": 16384,
                    "cpu_limit": "4000m",
                },
                network_settings={
                    "host": "0.0.0.0",
                    "api_port": 8000,
                    "websocket_port": 7273,
                    "allow_external": True,
                    "cors_origins": ["*"],
                    "service_mesh": "istio",
                },
                storage_settings={
                    "database_url": "postgresql://giljo:password@postgres:5432/giljo_mcp",
                    "redis_url": "redis://redis:6379/0",
                    "persistent_volume_path": "/data",
                    "persistent_volume_size": "100Gi",
                    "storage_class": "standard",
                },
                performance_settings={
                    "enable_caching": True,
                    "cache_backend": "redis",
                    "cache_size_mb": 2048,
                    "connection_pool_size": 50,
                    "enable_horizontal_scaling": True,
                    "min_replicas": 2,
                    "max_replicas": 10,
                    "target_cpu_utilization": 70,
                },
            ),
            dependencies=ProfileDependencies(
                python_version=">=3.9",
                required_packages=[
                    "fastmcp",
                    "fastapi",
                    "sqlalchemy",
                    "psycopg2-binary",
                    "httpx",
                    "websockets",
                    "pyyaml",
                    "redis",
                    "python-multipart",
                    "python-jose[cryptography]",
                    "prometheus-client",
                ],
                optional_packages=["kubernetes", "docker-compose", "helm"],
                system_requirements={
                    "min_ram_mb": 8192,
                    "min_disk_space_mb": 20000,
                    "os": ["linux", "macos", "windows"],
                    "container_runtime": ["docker", "containerd"],
                    "orchestrator": ["kubernetes", "docker-swarm", "docker-compose"],
                },
                external_services=["container-registry", "kubernetes-cluster"],
            ),
            recommended_for=[
                "Cloud deployments",
                "Microservices architecture",
                "DevOps teams",
                "Scalable applications",
                "Multi-environment deployments",
            ],
            limitations=["Requires container expertise", "Additional orchestration overhead", "Networking complexity"],
            post_install_steps=[
                "Build Docker images",
                "Push images to container registry",
                "Deploy using docker-compose or kubectl",
                "Configure persistent volumes",
                "Set up ingress/load balancer",
                "Configure service mesh if using",
                "Set up monitoring with Prometheus",
                "Configure auto-scaling policies",
            ],
        )

    def get_profile(self, profile_type: ProfileType) -> Optional[Profile]:
        """Get a specific profile by type."""
        return self._profiles.get(profile_type)

    def get_profiles(self) -> List[Profile]:
        """Get all available profiles."""
        return list(self._profiles.values())

    def get_profile_by_name(self, name: str) -> Optional[Profile]:
        """Get a profile by its display name."""
        for profile in self._profiles.values():
            if profile.name.lower() == name.lower():
                return profile
        return None

    def add_custom_profile(self, profile: Profile) -> bool:
        """Add a custom profile to the manager."""
        if profile.type in self._profiles:
            return False
        self._profiles[profile.type] = profile
        return True

    def update_profile(self, profile_type: ProfileType, profile: Profile) -> bool:
        """Update an existing profile."""
        if profile_type not in self._profiles:
            return False
        self._profiles[profile_type] = profile
        return True

    def export_profiles(self, file_path: Path) -> bool:
        """Export all profiles to a JSON file."""
        try:
            profiles_data = {pt.value: profile.to_dict() for pt, profile in self._profiles.items()}
            with open(file_path, "w") as f:
                json.dump(profiles_data, f, indent=2)
            return True
        except Exception:
            return False

    def import_profiles(self, file_path: Path) -> bool:
        """Import profiles from a JSON file."""
        try:
            with open(file_path, "r") as f:
                profiles_data = json.load(f)

            for profile_type_str, profile_data in profiles_data.items():
                profile_type = ProfileType(profile_type_str)
                profile = Profile(
                    name=profile_data["name"],
                    type=profile_type,
                    description=profile_data["description"],
                    configuration=ProfileConfiguration.from_dict(profile_data["configuration"]),
                    dependencies=ProfileDependencies.from_dict(profile_data["dependencies"]),
                    recommended_for=profile_data.get("recommended_for", []),
                    limitations=profile_data.get("limitations", []),
                    post_install_steps=profile_data.get("post_install_steps", []),
                )
                self._profiles[profile_type] = profile
            return True
        except Exception:
            return False

    def validate_system_requirements(self, profile: Profile) -> Dict[str, bool]:
        """Validate if current system meets profile requirements."""
        import sys
        import platform
        import shutil

        validation_results = {}

        # Check Python version
        current_version = f"{sys.version_info.major}.{sys.version_info.minor}"
        required_version = profile.dependencies.python_version.replace(">=", "")
        validation_results["python_version"] = current_version >= required_version

        # Check OS compatibility
        current_os = platform.system().lower()
        os_mapping = {"windows": "windows", "darwin": "macos", "linux": "linux"}
        required_os = profile.dependencies.system_requirements.get("os", [])
        validation_results["os_compatible"] = os_mapping.get(current_os, current_os) in required_os

        # Check disk space (simplified check)
        if "min_disk_space_mb" in profile.dependencies.system_requirements:
            total, used, free = shutil.disk_usage("/")
            free_mb = free // (1024 * 1024)
            required_mb = profile.dependencies.system_requirements["min_disk_space_mb"]
            validation_results["disk_space"] = free_mb >= required_mb

        # Check RAM (simplified - would need psutil for accurate check)
        validation_results["memory"] = True  # Placeholder

        return validation_results

    def get_profile_summary(self, profile_type: ProfileType) -> str:
        """Get a human-readable summary of a profile."""
        profile = self.get_profile(profile_type)
        if not profile:
            return "Profile not found"

        summary = f"Profile: {profile.name}\n"
        summary += f"Type: {profile.type.value}\n"
        summary += f"Description: {profile.description}\n"
        summary += f"Database: {profile.configuration.database_type}\n"
        summary += f"Deployment Mode: {profile.configuration.deployment_mode}\n"
        summary += f"Authentication: {profile.configuration.auth_method}\n"
        summary += f"Python Version: {profile.dependencies.python_version}\n"
        summary += f"Required Packages: {len(profile.dependencies.required_packages)}\n"

        if profile.recommended_for:
            summary += "\nRecommended for:\n"
            for item in profile.recommended_for:
                summary += f"  - {item}\n"

        if profile.limitations:
            summary += "\nLimitations:\n"
            for item in profile.limitations:
                summary += f"  - {item}\n"

        return summary


# Convenience function for external use
def create_profile_manager() -> ProfileManager:
    """Create and return a ProfileManager instance with default profiles."""
    return ProfileManager()
