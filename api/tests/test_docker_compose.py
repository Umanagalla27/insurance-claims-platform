"""
Automated Pytest Suite for Docker Compose Microservices Specification (ICIP-020).
Asserts that services, dependencies, memory limits, and network topology conform to production standards.
"""

from pathlib import Path
import pytest
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
COMPOSE_PATH = PROJECT_ROOT / "docker-compose.yml"


@pytest.fixture(scope="module")
def compose_config():
    """Load and parse docker-compose.yml."""
    assert COMPOSE_PATH.is_file(), "docker-compose.yml must exist"
    with open(COMPOSE_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


class TestDockerComposeArchitecture:
    """Test suite validating Docker Compose microservices orchestration."""

    def test_services_registered(self, compose_config):
        services = compose_config.get("services", {})
        assert "mysql" in services
        assert "redis" in services
        assert "api" in services

    def test_api_dependency_ordering_enforces_health(self, compose_config):
        api = compose_config["services"]["api"]
        deps = api.get("depends_on", {})
        assert deps.get("mysql", {}).get("condition") == "service_healthy"
        assert deps.get("redis", {}).get("condition") == "service_healthy"

    def test_resource_limits_protect_host_memory(self, compose_config):
        services = compose_config["services"]
        mysql_mem = services["mysql"]["deploy"]["resources"]["limits"]["memory"]
        redis_mem = services["redis"]["deploy"]["resources"]["limits"]["memory"]
        api_mem = services["api"]["deploy"]["resources"]["limits"]["memory"]

        assert mysql_mem == "1024M"
        assert redis_mem == "256M"
        assert api_mem == "1024M"

    def test_all_services_define_healthchecks(self, compose_config):
        for name, svc in compose_config["services"].items():
            assert "healthcheck" in svc, f"Service {name} must have a healthcheck defined"
            assert "interval" in svc["healthcheck"]
            assert "timeout" in svc["healthcheck"]

    def test_network_isolation_topology(self, compose_config):
        networks = compose_config.get("networks", {})
        assert "frontend_net" in networks
        assert "backend_net" in networks

        services = compose_config["services"]
        assert "backend_net" in services["mysql"]["networks"]
        assert "frontend_net" not in services["mysql"]["networks"]
        assert "backend_net" in services["redis"]["networks"]
        assert "frontend_net" not in services["redis"]["networks"]

        assert "frontend_net" in services["api"]["networks"]
        assert "backend_net" in services["api"]["networks"]

    def test_named_volumes_declared(self, compose_config):
        volumes = compose_config.get("volumes", {})
        assert "mysql_data" in volumes
        assert "redis_data" in volumes
