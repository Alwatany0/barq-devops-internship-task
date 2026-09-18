#!/usr/bin/env python3
"""Validate the BARQ assessment environment with bounded PASS/FAIL checks."""

import json
import os
import subprocess
import sys
import urllib.error
import urllib.request

PUBLIC_PORT = os.getenv("PUBLIC_PORT", "8090")
BASE_URL = f"http://127.0.0.1:{PUBLIC_PORT}"
TIMEOUT = 5

passed = 0
failed = 0


def check(name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"PASS  {name}")
        if detail:
            print(f"      {detail}")
    else:
        failed += 1
        print(f"FAIL  {name}")
        if detail:
            print(f"      {detail}")


def run_command(command):
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=TIMEOUT,
            check=False,
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return 124, "", "command timed out"


def http_get(path):
    try:
        with urllib.request.urlopen(
            f"{BASE_URL}{path}",
            timeout=TIMEOUT,
        ) as response:
            body = response.read().decode("utf-8")
            return response.status, body
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return None, str(exc)


print("=== BARQ ENVIRONMENT VALIDATION ===")
print(f"Public URL: {BASE_URL}")
print()

# 1. Public endpoint checks
print("--- HTTP endpoints ---")

for path in ("/", "/health", "/ready", "/instance", "/records", "/counter"):
    status, body = http_get(path)
    check(
        f"GET {path}",
        status == 200,
        f"HTTP {status}" if status is not None else body,
    )

# 2. Prove all application instances are reachable through NGINX.
print()
print("--- Load balancing ---")

instances = set()

for _ in range(10):
    status, body = http_get("/instance")
    if status == 200:
        try:
            payload = json.loads(body)
            instance_id = payload.get("instance_id")
            if instance_id:
                instances.add(instance_id)
        except json.JSONDecodeError:
            pass

check(
    "Both application instances receive traffic",
    {"app-01", "app-02", "app-03"}.issubset(instances),
    f"Observed instances: {sorted(instances)}",
)

# 3. Container health
print()
print("--- Container health ---")

returncode, stdout, stderr = run_command(
    ["docker", "compose", "ps", "--format", "{{.Name}}\t{{.Status}}"]
)

expected_containers = {"app-01", "app-02", "app-03", "nginx", "postgres", "redis"}

if returncode == 0:
    lines = stdout.splitlines()
    statuses = dict(
        line.split("\t", 1)
        for line in lines
        if "\t" in line
    )

    for container in sorted(expected_containers):
        status = statuses.get(container, "")
        healthy = (
            status.startswith("Up")
            and ("healthy" in status or container == "nginx")
        )
        check(
            f"{container} container is healthy/running",
            healthy,
            status or "container not found",
        )
else:
    check("Docker Compose status available", False, stderr or stdout)
# 4. Dependency readiness
print()
print("--- Dependency readiness ---")

returncode, stdout, stderr = run_command(
    ["docker", "exec", "postgres", "pg_isready", "-U", "barq_app", "-d", "barq_tasks"]
)

check(
    "PostgreSQL is ready",
    returncode == 0,
    stdout or stderr,
)

returncode, stdout, stderr = run_command(
    ["docker", "exec", "redis", "redis-cli", "ping"]
)

check(
    "Redis is ready",
    returncode == 0 and stdout == "PONG",
    stdout or stderr,
)
# 5. Host port isolation
print()
print("--- Host port isolation ---")

returncode, stdout, stderr = run_command(
    ["docker", "compose", "ps", "--format", "{{.Name}}\t{{.Ports}}"]
)

if returncode == 0:
    port_map = dict(
        line.split("\t", 1)
        for line in stdout.splitlines()
        if "\t" in line
    )

    nginx_ports = port_map.get("nginx", "")
    check(
        "NGINX publishes the public port",
        f"127.0.0.1:{PUBLIC_PORT}->80" in nginx_ports,
        nginx_ports or "no published port",
    )

    for container in ("app-01", "app-02", "app-03", "postgres", "redis"):
        ports = port_map.get(container, "")
        check(
            f"{container} has no host-published port",
            "->" not in ports,
            ports or "no published port",
        )
else:
    check("Docker Compose port status available", False, stderr or stdout)

# 6. Network isolation
print()
print("--- Network isolation ---")

returncode, stdout, stderr = run_command(
    [
        "docker",
        "network",
        "inspect",
        "barq-frontend",
        "--format",
        "{{range .Containers}}{{.Name}} {{end}}",
    ]
)

frontend_members = set(stdout.split()) if returncode == 0 else set()

check(
    "Frontend contains NGINX and both app instances",
    {"nginx", "app-01", "app-02", "app-03"}.issubset(frontend_members),
    f"Members: {sorted(frontend_members)}",
)

check(
    "Frontend excludes PostgreSQL and Redis",
    not ({"postgres", "redis"} & frontend_members),
    f"Members: {sorted(frontend_members)}",
)

returncode, stdout, stderr = run_command(
    [
        "docker",
        "network",
        "inspect",
        "barq-backend",
        "--format",
        "{{range .Containers}}{{.Name}} {{end}}",
    ]
)

backend_members = set(stdout.split()) if returncode == 0 else set()

check(
    "Backend contains both app instances, PostgreSQL and Redis",
    {"app-01", "app-02","app-03", "postgres", "redis"}.issubset(backend_members),
    f"Members: {sorted(backend_members)}",
)

check(
    "Backend excludes NGINX",
    "nginx" not in backend_members,
    f"Members: {sorted(backend_members)}",
)

# Summary
print()
print("=== SUMMARY ===")
print(f"PASS: {passed}")
print(f"FAIL: {failed}")

if failed:
    print("VALIDATION FAILED")
    sys.exit(1)

print("VALIDATION PASSED")
sys.exit(0)
