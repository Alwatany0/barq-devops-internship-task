<img src="assets/barq-logo.svg" alt="BARQ Systems" width="180">

# BARQ Systems DevOps Internship Task

This repository contains my solution for the BARQ Systems DevOps internship task.

The task was to investigate the supplied environment, fix the broken parts, run the application with Docker Compose, add validation and failure testing, implement PostgreSQL backup/restore, and document the investigation.

I was also learning DevOps while doing this task, so I used the environment to understand Docker, Docker Compose, NGINX, networking, CI, persistence, and failure recovery in practice.

## Requirements

The setup uses:

* Docker and Docker Compose
* Python 3.12
* Flask
* NGINX
* PostgreSQL 16
* Redis 7
* Linux/WSL2 or Docker Desktop with Linux containers

The final public port is `8090`. The internal Flask application port remains `8080`.

## Project structure

```text
.
├── app/                    # Flask application
├── database/               # PostgreSQL initialization
├── nginx/                  # NGINX configuration
├── tests/                  # Application tests
├── logs/                   # Supplied historical logs
├── backups/                # Local PostgreSQL backups
├── .github/workflows/      # GitHub Actions CI
├── Dockerfile
├── docker-compose.yml
├── validate.py
├── failure_test.py
├── backup.sh
├── restore.sh
├── troubleshooting.md
├── log_analysis.md
├── decisions.md
├── security_review.md
├── AI_USAGE.md
└── docs/
```

## Configuration

Copy the example environment file:

```bash
cp .env.example .env
```

The default configuration uses:

```env
PUBLIC_PORT=8090
POSTGRES_PASSWORD=change-me
```

The `.env` file is local configuration and should not be committed.

## Build and start

From the repository root:

```bash
docker compose build
docker compose up -d
```

Check the containers:

```bash
docker compose ps
```

The expected services are:

```text
app-01
app-02
app-03
nginx
postgres
redis
```

Only NGINX publishes a host port:

```text
127.0.0.1:8090 -> nginx:80
```

The application, PostgreSQL, and Redis ports are not published to the host.

## Check the application

The public API is available at:

```text
http://127.0.0.1:8090
```

The available endpoints are:

```text
/
/health
/ready
/instance
/records
/counter
```

For example:

```bash
curl http://127.0.0.1:8090/
curl http://127.0.0.1:8090/health
curl http://127.0.0.1:8090/ready
curl http://127.0.0.1:8090/instance
curl http://127.0.0.1:8090/records
curl http://127.0.0.1:8090/counter
```

To check all endpoints at once:

```bash
for path in / /health /ready /instance /records /counter; do
    curl -s -o /dev/null -w "$path -> HTTP %{http_code}\n" \
        "http://127.0.0.1:8090$path"
done
```

## Load balancing

NGINX sends requests across all three application instances.

Run:

```bash
for i in {1..10}; do
    curl -s http://127.0.0.1:8090/instance
    echo
done
```

The responses should show all three:

```text
app-01
app-02
app-03
```

The application containers communicate with PostgreSQL and Redis using their Docker service names rather than container IP addresses.

## Request flow

The request flow is:

```text
Client
   |
   | HTTP :8090
   v
NGINX :80
   |
   +----> app-01:8080
   +----> app-02:8080
   +----> app-03:8080
              |
              +----> PostgreSQL:5432
              |
              +----> Redis:6379
```

NGINX is the only service exposed to the host. The application containers are connected to both the frontend and backend Docker networks. PostgreSQL and Redis are only connected to the backend network.

The backend network is marked as internal so it is not intended to be directly reachable from outside the Docker environment.

## Health and readiness

There are two application checks:

* `/health` checks that the application process is responding.
* `/ready` checks that the application can use its required PostgreSQL and Redis dependencies.

This prevents a running Flask process from being treated as ready when one of its dependencies is unavailable.

Docker health checks are also configured for the application, PostgreSQL, and Redis. Application startup waits for healthy PostgreSQL and Redis before starting the application instances.

## Validation

The main environment validation is:

```bash
python3 validate.py
```

It checks:

* HTTP endpoints
* application instances
* container health
* PostgreSQL readiness
* Redis readiness
* host port exposure
* frontend/backend network separation

A successful run ends with:

```text
VALIDATION PASSED
```

The validator uses bounded timeouts and returns a non-zero exit code if a required check fails.

Validation should fail when a required endpoint, service, dependency, container health check, port rule, or network rule does not meet the expected configuration.

## Failure and recovery test

The failure test stops one application instance and sends traffic through NGINX:

```bash
python3 failure_test.py
```

The test verifies that:

1. All three instances are healthy before the test.
2. One application instance is stopped.
3. Requests continue through the surviving instance.
4. The failed instance is started again.
5. All three instances receive traffic after recovery.

The test uses `docker compose stop/start` and does not remove the database volumes.

## PostgreSQL backup

Create a PostgreSQL backup with:

```bash
./backup.sh
```

The script creates a timestamped PostgreSQL custom-format dump under:

```text
backups/
```

Check the generated file with:

```bash
ls -lh backups/
```

The backup directory is ignored by Git.

## PostgreSQL restore

Restore a backup with:

```bash
./restore.sh backups/FILE_NAME.dump
```

For example:

```bash
./restore.sh backups/barq_tasks_20260916T192348Z.dump
```

The restore script copies the dump into the PostgreSQL container, restores it with `pg_restore`, and removes the temporary copy.

## Persistence test

PostgreSQL uses a named Docker volume.

A simple persistence test is:

```bash
curl -s -X POST http://127.0.0.1:8090/records \
    -H 'Content-Type: application/json' \
    -d '{"title":"Persistence verification record"}'
```

Then recreate the application and PostgreSQL containers without removing the volume:

```bash
docker compose up -d --force-recreate app-01 app-02 app-03 postgres
```

Wait for the services to become healthy and check:

```bash
curl http://127.0.0.1:8090/records
```

The previously created record should still exist.

Do not use `docker compose down -v` during this test because that removes the named volumes.

## Application tests

The Flask application also has unit tests:

```bash
python3 -m unittest discover -s tests -v
```

These tests are separate from the Docker/Compose environment validation.

## CI

GitHub Actions runs on pushes to `main` and pull requests.

The workflow:

1. Checks Python syntax.
2. Validates the Docker Compose configuration.
3. Builds the application image.
4. Starts the environment.
5. Waits for readiness.
6. Runs `validate.py`.
7. Collects Compose logs if a step fails.
8. Cleans up the CI environment.

The CI workflow is:

```text
.github/workflows/ci.yml
```

### What green CI proves

A green CI run proves that, in the GitHub Actions environment used by the workflow, the Compose configuration could be parsed, the application image could be built, the services could start, the readiness check could succeed, and the automated validation passed.

It does **not** prove that the system is production-ready or that every possible failure has been tested. The CI environment is different from a production environment, and the workflow does not test every dependency failure, backup recovery scenario, security issue, performance limit, or infrastructure failure.

The separate failure, persistence, backup/restore, and historical log analysis were used to test areas that are outside the normal CI run.

## Logs

The supplied historical logs are stored under:

```text
logs/
```

They were analyzed separately from the current Docker environment.

The analysis covers:

* malformed and duplicate records
* request IDs
* HTTP status codes
* 5xx failures
* upstream retries
* NGINX connection failures
* Redis timeout errors
* `/records` upstream timeouts
* timing statistics
* correlated examples
* limitations of what the logs can prove

The original supplied logs were not modified.

See:

```text
log_analysis.md
```

## What the logs showed

The historical logs showed several different failure periods rather than one single failure.

The main patterns were:

* NGINX connection refusals to the historical `app-02` address during the first failure period.
* Redis timeout errors from both application instances during later periods.
* `/records` requests that timed out while NGINX was waiting for an upstream response.

There were 720 distinct client requests after handling malformed records and duplicate request IDs. There were 95 final 5xx responses, giving a 13.19% 5xx rate using distinct client requests as the denominator.

Retries were not counted as new client requests. The analysis used request IDs and the upstream attempt information in the NGINX logs to distinguish retries from separate requests.

The logs prove the observed connection refusals, Redis timeout errors, and upstream response-header timeouts. They do not prove the underlying reason why the historical backend refused connections, why Redis timed out, or what system-level condition caused the slow `/records` responses.

## Troubleshooting

The investigation and fixes are recorded chronologically in:

```text
troubleshooting.md
```

The document includes the symptoms, investigation, failed attempts where applicable, fixes, retests, and related commits.

One useful failed attempt was running `pg_dump` manually without specifying the application database user. PostgreSQL attempted to use the current Linux user (`root`) as the database role. This helped identify that the backup command needed to explicitly use the configured PostgreSQL role.

## Technical decisions

The main implementation decisions are documented in:

```text
decisions.md
```

This covers the base image, health/readiness checks, networks, NGINX timeouts and retries, resource limits, persistence, and container security.

## Security review

The security and production-readiness review is in:

```text
security_review.md
```

It separates controls implemented in this assessment from improvements that would still be needed in a production environment.

The review covers secrets, host ports, the container user, image security, network isolation, persistence and backups, logging and monitoring, availability, dependency timeouts, and resource limits.

## AI usage

AI was used as part of the learning and troubleshooting process while completing the task.

The details of how it was used and how the results were independently verified are documented in:

```text
AI_USAGE.md
```

I used AI while learning DevOps concepts and applying them to the actual environment. Commands and configuration changes were run and checked against the real Docker Compose environment rather than being accepted without verification.

## Stopping the environment

To stop and remove the containers while keeping named volumes:

```bash
docker compose down
```

To start them again:

```bash
docker compose up -d
```

Do not use `-v` unless the intention is to remove the persistent data.

## Cleanup

If the environment is no longer needed:

```bash
docker compose down
```

If the PostgreSQL and Redis data is no longer needed and you intentionally want to remove it:

```bash
docker compose down -v
```

Do not use global Docker cleanup commands such as:

```bash
docker system prune
```

## Recorded challenge

The supplied `video_challenge.sh` is intended to be run **once during the final continuous video recording**.

It must not be run early as a test.

```bash
./video_challenge.sh
```

The challenge changes the runtime environment during the recording. The final video state is documented separately in the architecture and evidence documentation after the challenge has actually been completed.

Do not use `docker compose down` to reset the runtime during the challenge.

## Evidence

The evidence index links the main requirements to the relevant files, commits, and final video timestamps:

```text
docs/EVIDENCE_INDEX.md
```

The architecture documentation is in:

```text
docs/ARCHITECTURE.md
```
