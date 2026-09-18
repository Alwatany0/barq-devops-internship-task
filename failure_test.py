#!/usr/bin/env python3
"""Test application failure, continued traffic, and recovery through NGINX."""
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

PUBLIC_PORT = int(os.getenv("PUBLIC_PORT", "8090"))
BASE_URL = f"http://127.0.0.1:{PUBLIC_PORT}"
TARGET = "app-01"
REQUESTS_DURING_FAILURE = 20
TIMEOUT = 5


def run_command(*args):
    return subprocess.run(
        args,
        capture_output=True,
        text=True,
        timeout=TIMEOUT,
    )


def container_healthy(name):
    result = run_command(
        "docker", "inspect", "--format",
        "{{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{end}}",
        name,
    )
    return result.returncode == 0 and result.stdout.strip() == "running healthy"


def wait_for_healthy(name, timeout=30):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if container_healthy(name):
            return True
        time.sleep(1)
    return False


def request_instance():
    try:
        with urllib.request.urlopen(
            f"{BASE_URL}/instance",
            timeout=TIMEOUT,
        ) as response:
            body = json.loads(response.read().decode())
            return response.status, body.get("instance_id")
    except urllib.error.HTTPError as exc:
        return exc.code, None
    except Exception as exc:
        print(f"request error: {type(exc).__name__}")
        return None, None


def main():
    print("=== BARQ FAILURE / RECOVERY TEST ===")
    print(f"Public URL: {BASE_URL}")
    print(f"Target backend: {TARGET}")

    if not all(container_healthy(name) for name in ("app-01", "app-02", "app-03")):
        print("FAIL: all three application instances must be healthy before the test")
        return 1

    print("PASS: all three application instances are healthy before failure")

    stopped = False

    try:
        print(f"Stopping {TARGET}...")
        result = run_command("docker", "compose", "stop", TARGET)

        if result.returncode != 0:
            print("FAIL: could not stop target backend")
            print(result.stderr.strip())
            return 1

        stopped = True
        print(f"PASS: {TARGET} stopped")

        success_count = 0
        error_count = 0
        instances = set()

        print(f"Sending {REQUESTS_DURING_FAILURE} requests through NGINX...")

        for number in range(1, REQUESTS_DURING_FAILURE + 1):
            status, instance = request_instance()

            if status == 200:
                success_count += 1
                if instance:
                    instances.add(instance)
                print(f"  {number:02d}: HTTP 200 from {instance}")
            else:
                error_count += 1
                print(f"  {number:02d}: HTTP {status if status else 'ERROR'}")

        print("--- Failure window ---")
        print(f"Successful requests: {success_count}")
        print(f"Errors: {error_count}")
        print(f"Instances observed: {sorted(instances)}")

        if success_count == 0:
            print("FAIL: no traffic was served while one backend was stopped")
            return 1

        if not ({"app-02", "app-03"} & instances):
            print("FAIL: neither surviving backend served traffic")
            return 1

        print("PASS: traffic continued through the surviving backend")

    finally:
        if stopped:
            print(f"Restoring {TARGET}...")
            result = run_command("docker", "compose", "start", TARGET)

            if result.returncode != 0:
                print("FAIL: could not restore target backend")
                print(result.stderr.strip())
                return_code = 1
            elif not wait_for_healthy(TARGET):
                print("FAIL: target backend did not become healthy")
                return_code = 1
            else:
                print(f"PASS: {TARGET} restored and healthy")
                return_code = 0
        else:
            return_code = 0

    if return_code != 0:
        return return_code

    time.sleep(2)

    recovered_instances = set()
    for _ in range(10):
        status, instance = request_instance()
        if status == 200 and instance:
            recovered_instances.add(instance)

    print("--- Recovery verification ---")
    print(f"Instances observed after recovery: {sorted(recovered_instances)}")

    if not {"app-01", "app-02", "app-03"}.issubset(recovered_instances):
        print("FAIL: all three application instances were not observed after recovery")
        return 1

    print("PASS: all three application instances serve traffic after recovery")
    print("=== FAILURE / RECOVERY TEST PASSED ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
