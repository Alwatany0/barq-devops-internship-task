# Troubleshooting journal

## Entry 1 — Initial Docker Compose setup

* **Symptom:** The starter Docker Compose setup did not match the required environment.
* **Hypothesis:** There were several configuration problems in the supplied Compose file, including the application binding, networking, restart settings, and service configuration.
* **Command or test:** I inspected `docker-compose.yml` and compared the services and settings with the task requirements.
* **Actual output:** The starter configuration had the Flask app bound to `127.0.0.1`, used `restart: "no"`, loaded the app configuration from `config/app.env`, and did not have the required application/database/Redis network setup.
* **Failed attempt and what changed your thinking:** I did not record a separate failed command for this step, so I am not claiming one.
* **Root cause:** The starter Compose configuration was not set up for the required container architecture.
* **Fix:** Updated the Compose file to use `0.0.0.0:8080`, service names for PostgreSQL and Redis, separate frontend/backend networks, health checks, restart policies, resource limits, and a named PostgreSQL volume. Only NGINX publishes a host port.
* **Retest evidence:** The environment was later started successfully and all five services became healthy. The runtime checks also showed that only NGINX had a published host port.
* **Related commit:** `7babf30` — `fix: repair initial compose configuration`
* **Remaining uncertainty:** I did not capture every error from the original starter environment, so this entry is based on the configuration inspection and the later successful retest.

## Entry 2 — NGINX was using the wrong backend port

* **Symptom:** NGINX was not correctly configured to reach both Flask instances.
* **Hypothesis:** The upstream configuration had an incorrect port for one of the applications.
* **Command or test:** I checked `nginx/nginx.conf` and compared the upstream ports with the port used by the Flask application.
* **Actual output:** The original configuration had:

  * `app-01:8081`
  * `app-02:8080`

  The Flask applications listen on port `8080`.
* **Failed attempt and what changed your thinking:** The config showed that `app-01` was pointing to a port where the application was not listening. This pointed to NGINX routing rather than a Flask application problem.
* **Root cause:** `app-01` was configured with port `8081` instead of `8080`.
* **Fix:** Changed both upstreams to port `8080` and added `max_fails=1` and `fail_timeout=5s`. NGINX was also configured to retry another upstream when appropriate.
* **Retest evidence:** Repeated `/instance` requests through NGINX returned both `app-01` and `app-02`, confirming that both backends were reachable.
* **Related commit:** `548e8dc` — `fix: repair nginx upstream routing`
* **Remaining uncertainty:** None for the tested routing requirement.

## Entry 3 — Secret handling and running as non-root

* **Symptom:** The starter setup used `config/app.env` for application configuration and the Docker image did not explicitly run the application as a non-root user.
* **Hypothesis:** Secrets should be supplied at runtime and the application container should use a dedicated unprivileged user.
* **Command or test:** I inspected the Dockerfile and configuration files before changing them.
* **Actual output:** `config/app.env` was part of the starter configuration, and the Dockerfile did not define a dedicated application user.
* **Failed attempt and what changed your thinking:** There was no separate failed command for this issue, so I did not add one to the journal.
* **Root cause:** Configuration containing credentials was being handled as part of the application setup, and the container had no explicit non-root user.
* **Fix:** Removed `config/app.env` from the working tree, added it to `.gitignore`, added `.env.example` with a placeholder password, and changed the Dockerfile to create and use the `app` user with UID `10001`.
* **Retest evidence:** A no-cache image build succeeded. Checking the running container showed `uid=10001(app) gid=10001(app)`. A separate test confirmed that the secret configuration file was not present in the built image.
* **Related commit:** `a5e7eff` — `fix: remove secrets from image and run app as non-root`
* **Remaining uncertainty:** The starter file exists in older Git history. It contained synthetic lab configuration, not a real production secret.

## Entry 4 — Environment validation

* **Symptom:** The environment needed a repeatable way to check whether the required services and networking were working.
* **Hypothesis:** A validation script should check the endpoints, service health, database/Redis readiness, networking, ports, and load balancing.
* **Command or test:** Added and ran `validate.py`.
* **Actual output:**

  * `PASS: 23`
  * `FAIL: 0`
  * `VALIDATION PASSED`
* **Failed attempt and what changed your thinking:** No failed validation run was recorded.
* **Root cause:** There was no complete automated validation script in the starter environment.
* **Fix:** Added checks for the six required endpoints, both application instances, container health, PostgreSQL, Redis, host port isolation, and frontend/backend network membership.
* **Retest evidence:** The full validation completed with 23 passes and zero failures.
* **Related commit:** `352eb86` — `test: add environment validation`
* **Remaining uncertainty:** The validator only proves the conditions that it checks. It does not prove production-level reliability.

## Entry 5 — Backend failure and recovery

* **Symptom:** The task required testing what happens when one Flask instance goes down.
* **Hypothesis:** NGINX should continue sending requests to the remaining healthy application instance.
* **Command or test:** Ran `failure_test.py`, which stopped `app-01` and sent 20 requests through NGINX.
* **Actual output:** All 20 requests succeeded and were served by `app-02`. After starting `app-01` again, requests were served by both instances.
* **Failed attempt and what changed your thinking:** No failed recovery test was recorded.
* **Root cause:** This was a resilience test rather than a newly discovered configuration problem.
* **Fix:** Added an automated failure/recovery test with bounded waits and health checks.
* **Retest evidence:** The test ended with:
  `=== FAILURE / RECOVERY TEST PASSED ===`
* **Related commit:** `25bdd3d` — `test: add backend failure recovery test`
* **Remaining uncertainty:** This only tests failure of one application instance. NGINX, PostgreSQL, and Redis are still possible single points of failure.

## Entry 6 — PostgreSQL backup

* **Symptom:** A repeatable PostgreSQL backup was required.
* **Hypothesis:** `pg_dump` using PostgreSQL custom format would provide a backup that could be checked and restored.
* **Command or test:** Added and ran `backup.sh`.
* **Actual output:** The script created a PostgreSQL custom-format dump successfully. The generated file was about `4.0K`, and `pg_restore --list` was able to read it.
* **Failed attempt and what changed your thinking:** My first manual `pg_dump` command did not specify `-U barq_app`. PostgreSQL therefore tried to use the `root` role and the command failed.
* **Root cause:** The PostgreSQL username was missing from the manual command.
* **Fix:** Added the database name and `barq_app` user explicitly to `backup.sh`.
* **Retest evidence:** The backup script created a valid PostgreSQL custom dump, which was successfully inspected using `pg_restore --list` inside the PostgreSQL container.
* **Related commit:** `fed0147` — `feat: add PostgreSQL backup script`
* **Remaining uncertainty:** This proves the backup procedure works locally. Production backups would need protected storage, retention, access control, and regular restore testing.

## Entry 7 — Restore and persistence

* **Symptom:** The database backup needed to be restored, and PostgreSQL data needed to survive container recreation.
* **Hypothesis:** The backup should restore successfully and the named PostgreSQL volume should keep the data when the containers are recreated.
* **Command or test:** Ran `restore.sh`, then created a record through `/records` and recreated `app-01`, `app-02`, and `postgres` without deleting the volume.
* **Actual output:** The restore completed successfully. The test record `Persistence verification record` was created with ID `3` and was still present after the containers were recreated.
* **Failed attempt and what changed your thinking:** `pg_restore` was not installed in the local WSL environment. I therefore used the `pg_restore` available inside the PostgreSQL container to inspect the backup.
* **Root cause:** The local environment did not have the PostgreSQL restore utility installed.
* **Fix:** Used the PostgreSQL container for PostgreSQL-specific backup inspection and restore operations.
* **Retest evidence:** `restore.sh` completed successfully and `/records` still returned record ID `3` after container recreation.
* **Related commit:** `d395439` — `feat: add PostgreSQL restore script`
* **Remaining uncertainty:** The test proves persistence when the volume is kept. It does not cover host failure or corrupted storage.

## Entry 8 — CI

* **Symptom:** The task required the environment validation to run automatically on pushes and pull requests.
* **Hypothesis:** GitHub Actions can reproduce the basic verification process on a clean runner.
* **Command or test:** Added `.github/workflows/ci.yml` and ran the workflow.
* **Actual output:** The GitHub Actions run completed successfully and is green.
* **Failed attempt and what changed your thinking:** No failed CI run was recorded for the final workflow.
* **Root cause:** The starter repository did not have the required CI validation workflow.
* **Fix:** Added a workflow that checks Python syntax, validates Compose, builds the image, starts the environment, waits for readiness, and runs `validate.py`. Docker logs are collected if a step fails.
* **Retest evidence:** The current CI run is green.
* **Related commit:** `efc76d1` — `ci: add automated environment validation`
* **Remaining uncertainty:** Green CI proves the checks passed on the GitHub runner. It does not prove production-scale reliability.

## Entry 9 — Final three-instance / 8090 state

* **Symptom:** After the recorded challenge attempt, the final assessment state had to match the required three-instance architecture on public port `8090`.
* **Investigation:** The running environment was inspected with `docker compose ps`, endpoint requests, repeated `/instance` requests, and the validation script.
* **Actual findings:** The final environment contained healthy `app-01`, `app-02`, `app-03`, `nginx`, `postgres`, and `redis`. NGINX published `127.0.0.1:8090 -> 80`. Repeated `/instance` requests through NGINX observed all three application instances.
* **Failed attempt and what changed my thinking:** The first final validation run passed the endpoint, health, port, and network checks but failed the load-balancing check because the running NGINX container had not yet loaded the new `app-03` upstream configuration. Recreating only NGINX loaded the updated configuration.
* **Additional configuration issue:** The Compose file used `PUBLIC_PORT=8090` as its default, but the local `.env` still explicitly contained `PUBLIC_PORT=8080`. Updating the local environment value to `8090` made the resolved Compose configuration match the final architecture.
* **Fix:** Added `app-03` to the Compose services and NGINX upstream, updated NGINX dependencies, changed the final public port to `8090`, and updated `validate.py` and `failure_test.py` for three application instances.
* **Retest evidence:** Final endpoint checks returned HTTP 200. Repeated `/instance` requests observed `app-01`, `app-02`, and `app-03`. `validate.py` completed successfully and `failure_test.py` completed successfully.
* **Challenge evidence limitation:** The recorded `./video_challenge.sh` attempt stopped during preflight before the runtime fault was injected, so no challenge receipt was generated. The challenge was not rerun or reset afterward.
* **Related changes:** Final working-tree changes to `docker-compose.yml`, `nginx/nginx.conf`, `validate.py`, and `failure_test.py`.
