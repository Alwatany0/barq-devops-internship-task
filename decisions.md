# Technical decisions

## 1. Python base image

* **Choice:** `python:3.12-slim-bookworm` with a pinned image digest.
* **Why:** The application uses Python 3.12, and the slim image keeps the application image smaller than a full Python image. Pinning the digest also avoids silently getting a different image later.
* **Alternative:** Use the normal `python:3.12` image or another Python base image.
* **Trade-off:** The slim image has fewer tools installed, so debugging inside the container can be less convenient.
* **Evidence / commit:** `a5e7eff` — Dockerfile changes.
* **Production improvement:** Keep the image pinned and use an image scanning process before deployment.

## 2. Health and readiness checks

* **Choice:** Use `/health` for the application process and `/ready` for PostgreSQL and Redis readiness.
* **Why:** A running Flask process does not necessarily mean the application can use its dependencies. Keeping the two checks separate makes that difference clear.
* **Alternative:** Use one endpoint that checks everything.
* **Trade-off:** There are two endpoints to maintain, but they give more useful information when something fails.
* **Evidence / commit:** `352eb86` — validation checks both endpoints; Compose also uses container health checks.
* **Production improvement:** Add more detailed dependency and startup metrics while keeping liveness and readiness separate.

## 3. Frontend and backend networks

* **Choice:** Use separate `barq-frontend` and `barq-backend` networks. NGINX is only on the frontend network, while PostgreSQL and Redis are only on the backend network.
* **Why:** The applications need to communicate with both sides, but NGINX does not need direct access to PostgreSQL or Redis.
* **Alternative:** Put every container on one Docker network.
* **Trade-off:** Two networks make the Compose configuration slightly more complicated, but they reduce unnecessary connectivity.
* **Evidence / commit:** `7babf30` — Compose networking changes.
* **Production improvement:** Keep the same separation and apply stricter network policies where supported by the platform.

## 4. NGINX timeouts and retries

* **Choice:** Use a 2-second proxy connect timeout, 3-second proxy read timeout, and retry another upstream for connection/timeout/502/503/504 failures.
* **Why:** The application is a small internal service, so long waits are not useful for this assessment. Retrying another healthy application instance also allows the service to continue when one backend fails.
* **Alternative:** Use longer timeouts or disable upstream retries.
* **Trade-off:** Short timeouts can reject genuinely slow requests, while retries can add another upstream attempt and extra load.
* **Evidence / commit:** `548e8dc` — NGINX upstream routing and failure handling.
* **Production improvement:** Tune the values using real latency and traffic data and make sure retrying is safe for each HTTP method.

## 5. Restart policies and resource limits

* **Choice:** Application and infrastructure containers use `restart: unless-stopped` with CPU and memory limits.
* **Why:** A temporary container failure should not leave the service stopped indefinitely, while resource limits prevent one service from consuming unlimited resources.
* **Alternative:** Disable automatic restarts or leave resources unlimited.
* **Trade-off:** Automatic restarts can hide repeated failures if there is no monitoring, and limits can cause failures if they are set too low.
* **Evidence / commit:** `7babf30` — Compose configuration.
* **Production improvement:** Add monitoring and alerts for restart loops, CPU throttling, and memory pressure, then tune limits from observed usage.

## 6. PostgreSQL and Redis persistence

* **Choice:** PostgreSQL uses a named Docker volume. Redis uses AOF persistence with a named volume.
* **Why:** PostgreSQL data needs to survive container recreation. Redis persistence was also enabled because the application uses Redis for its counter and the task asks for persistence where appropriate.
* **Alternative:** Store everything only inside the containers and recreate the data when containers are replaced.
* **Trade-off:** Persistent storage adds state that has to be backed up and managed, but losing the data whenever a container is recreated would be worse for this application.
* **Evidence / commit:** `7babf30`; persistence was later verified by recreating the application and PostgreSQL containers.
* **Production improvement:** Use managed persistent storage, regular backups, retention policies, and tested restore procedures.

## 7. Non-root application container and runtime secrets

* **Choice:** Run Flask as the dedicated `app` user with UID `10001` and keep the database password outside the image.
* **Why:** Running as a non-root user reduces the impact of a container compromise. Runtime configuration also avoids baking the database password into the image.
* **Alternative:** Run the container as root and store the configuration directly in the image.
* **Trade-off:** A non-root user can sometimes cause permission issues, and runtime secret handling needs to be configured correctly.
* **Evidence / commit:** `a5e7eff`.
* **Production improvement:** Use a proper secret manager instead of a local `.env` file and rotate credentials regularly.

## 8. Bounded validation

* **Choice:** `validate.py` uses bounded requests and exits with a non-zero status when a check fails.
* **Why:** A validation script should not hang forever and CI needs a clear pass/fail result.
* **Alternative:** Use manual curl commands or unlimited retry loops.
* **Trade-off:** A fixed timeout can fail when a system is temporarily slow, but it makes the test predictable.
* **Evidence / commit:** `352eb86`.
* **Production improvement:** Tune the timeout based on real service startup and response times and expose validation results through monitoring.
