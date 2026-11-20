"""
Verification and Audit Script for Docker Compose Microservices Orchestration (ICIP-020).
Validates multi-service topology, memory limits, healthcheck conditions, and network isolation.
"""

from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
COMPOSE_FILE = PROJECT_ROOT / "docker-compose.yml"


def parse_memory_mb(mem_str: str) -> int:
    """Parse Docker memory strings like '1024M' or '256M' into integer megabytes."""
    mem_str = mem_str.strip().upper()
    if mem_str.endswith("M"):
        return int(mem_str[:-1])
    elif mem_str.endswith("G"):
        return int(mem_str[:-1]) * 1024
    return int(mem_str)


def audit_docker_compose():
    print(
        "================================================================================"
    )
    print(
        "   Insurance Claims Intelligence Platform — Docker Compose Audit (ICIP-020)   "
    )
    print(
        "================================================================================"
    )

    # 1. File existence & YAML parse
    print("[1/6] Validating YAML syntax and compose file presence...")
    assert COMPOSE_FILE.is_file(), f"Missing {COMPOSE_FILE}"
    with open(COMPOSE_FILE, encoding="utf-8") as f:
        config = yaml.safe_load(f)
    assert "services" in config, "Missing 'services' root key"
    services = config["services"]
    print(f"  -> Valid YAML. Found {len(services)} services: {list(services.keys())}")

    # 2. Required Services
    print("[2/6] Verifying required microservices (mysql, redis, api)...")
    assert "mysql" in services, "Missing 'mysql' service"
    assert "redis" in services, "Missing 'redis' service"
    assert "api" in services, "Missing 'api' service"
    print("  -> All 3 core microservices present.")

    # 3. Service Dependencies and Health Ordering
    print("[3/6] Verifying service ordering and health conditions...")
    api_svc = services["api"]
    assert "depends_on" in api_svc, "API service must define 'depends_on'"
    depends = api_svc["depends_on"]
    assert "mysql" in depends, "API must depend on mysql"
    assert "redis" in depends, "API must depend on redis"
    assert depends["mysql"].get("condition") == "service_healthy", (
        "mysql dependency must require service_healthy"
    )
    assert depends["redis"].get("condition") == "service_healthy", (
        "redis dependency must require service_healthy"
    )
    print(
        "  -> API dependency order enforces 'service_healthy' for both mysql and redis."
    )

    # 4. Memory Guardrails for 8GB Host Machine
    print("[4/6] Verifying resource limits and 8GB RAM host guardrails...")
    total_mem_mb = 0
    for name, svc in services.items():
        limits = svc.get("deploy", {}).get("resources", {}).get("limits", {})
        assert "memory" in limits, f"Service '{name}' missing memory limit guardrail"
        mem_mb = parse_memory_mb(limits["memory"])
        total_mem_mb += mem_mb
        cpus = limits.get("cpus", "N/A")
        print(f"  -> Service '{name}': Memory Limit = {mem_mb} MB | CPUs = {cpus}")

    assert total_mem_mb <= 2500, (
        f"Total memory limit ({total_mem_mb} MB) exceeds 2.5 GB host safety cap!"
    )
    print(
        f"  -> Total stack memory limit: {total_mem_mb} MB (~{round(total_mem_mb / 1024, 2)} GB). Host safe!"
    )

    # 5. Active Healthchecks
    print("[5/6] Verifying active healthcheck probes across all containers...")
    for name, svc in services.items():
        assert "healthcheck" in svc, f"Service '{name}' missing healthcheck definition"
        hc = svc["healthcheck"]
        test_cmd = hc.get("test", [])
        test_str = " ".join(test_cmd) if isinstance(test_cmd, list) else str(test_cmd)
        print(f"  -> Service '{name}' Healthcheck: {test_str[:60]}...")
    print("  -> Healthcheck probes configured for all services.")

    # 6. Network Segmentation & Persistent Volumes
    print("[6/6] Verifying network segmentation and persistent named volumes...")
    assert "networks" in config, "Missing 'networks' root key"
    assert "frontend_net" in config["networks"], "Missing 'frontend_net' network"
    assert "backend_net" in config["networks"], "Missing 'backend_net' network"

    # API should touch both networks
    api_nets = api_svc.get("networks", [])
    assert "frontend_net" in api_nets and "backend_net" in api_nets, (
        "API must connect to frontend and backend networks"
    )

    # DB and Redis should be on backend network
    assert "backend_net" in services["mysql"].get("networks", []), (
        "mysql must be on backend_net"
    )
    assert "backend_net" in services["redis"].get("networks", []), (
        "redis must be on backend_net"
    )

    # Volumes
    assert "volumes" in config, "Missing 'volumes' root key"
    assert "mysql_data" in config["volumes"], "Missing 'mysql_data' named volume"
    assert "redis_data" in config["volumes"], "Missing 'redis_data' named volume"
    print(
        "  -> Network segmentation (frontend_net + backend_net) and named volumes verified."
    )

    print(
        "\n================================================================================"
    )
    print(
        f" [SUCCESS] Docker Compose specification verified successfully! (Total RAM: {total_mem_mb} MB)"
    )
    print(
        "================================================================================"
    )


if __name__ == "__main__":
    audit_docker_compose()
