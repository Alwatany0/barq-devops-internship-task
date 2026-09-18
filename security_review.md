# Security and production-readiness review

This review covers the security and production-readiness of the final solution. Some controls are implemented in the assessment environment, while others would need additional infrastructure or operational processes in a real production deployment.

## 1. Database password and application secrets

* **Risk and evidence:** The application needs a PostgreSQL password. Putting that password directly into the Dockerfile or application image would expose it to anyone who can inspect the image.
* **Impact:** An exposed database credential could allow unauthorized access to application data.
* **Implemented fix / commit:** The application image does not contain the starter `config/app.env`, and the database password is supplied through the runtime environment. `.gitignore` also prevents the local configuration file from being committed. Commit `a5e7eff`.
* **Production follow-up:** Use a proper secret manager and rotate credentials regularly. Do not use example or shared passwords in production.
* **How to verify:** Build the image and check that the old configuration file is not present inside it. Also check `git status` and `.gitignore` to confirm local secret files are not tracked.

## 2. Unnecessary host port exposure

* **Risk and evidence:** Publishing application, PostgreSQL, or Redis ports directly to the host would allow clients to bypass NGINX and access internal services directly.
* **Impact:** This increases the attack surface and could expose databases or internal application endpoints.
* **Implemented fix / commit:** Only NGINX publishes the public port. The application containers, PostgreSQL, and Redis have no host-published ports. Commit `7babf30`.
* **Production follow-up:** Keep databases and internal services on private networks and expose only the required public entry point.
* **How to verify:** Run `docker compose ps --format '{{.Name}}\t{{.Ports}}'` and confirm only NGINX has a host port.

## 3. Running the application as root

* **Risk and evidence:** A process running as root inside a container has more privileges if the application is compromised.
* **Impact:** A container compromise could have a larger impact inside the container and potentially increase the risk of container breakout depending on the runtime configuration.
* **Implemented fix / commit:** A dedicated `app` user with UID `10001` is created in the Dockerfile and the application runs as that user. Commit `a5e7eff`.
* **Production follow-up:** Keep containers non-root and use additional hardening such as dropping unnecessary Linux capabilities and using a read-only root filesystem where practical.
* **How to verify:** Run `docker compose exec app-01 id` and confirm the process is running as the `app` user rather than root.

## 4. Container image security

* **Risk and evidence:** Container images contain the operating system packages and Python dependencies used by the application. Vulnerable packages can therefore become part of the deployed application.
* **Impact:** A vulnerable package or base image could provide an entry point for an attacker.
* **Implemented fix / commit:** The Python base image is a slim Bookworm image and its digest is pinned in the Dockerfile. Commit `a5e7eff`.
* **Production follow-up:** Add automated vulnerability scanning for the base image and Python dependencies, rebuild regularly for security updates, and review image changes before deployment.
* **How to verify:** Inspect the Dockerfile for the pinned digest and run an image/dependency scanner as part of CI.

## 5. Network separation

* **Risk and evidence:** If all containers shared one unrestricted Docker network, NGINX could communicate directly with services it does not need.
* **Impact:** A compromised frontend component would have more opportunities to reach internal services.
* **Implemented fix / commit:** The solution uses separate frontend and backend networks. NGINX is only on the frontend network, while PostgreSQL and Redis are only on the backend network. The backend network is marked internal. Commit `7babf30`.
* **Production follow-up:** Keep the same separation in production and apply additional network policies or firewall rules where available.
* **How to verify:** Inspect both Docker networks and confirm:

  * frontend: NGINX + application instances
  * backend: application instances + PostgreSQL + Redis
  * NGINX is not on the backend network.

## 6. Persistent data and backups

* **Risk and evidence:** PostgreSQL contains application data that would be lost if the database storage were treated as disposable container storage.
* **Impact:** Container replacement could cause permanent data loss without persistent storage and backups.
* **Implemented fix / commit:** PostgreSQL uses a named volume, and backup/restore scripts were added. The backup was tested as a PostgreSQL custom-format dump and restore was tested successfully. Commits `fed0147` and `d395439`.
* **Production follow-up:** Store backups outside the Docker host, encrypt them, restrict access, define retention, and test restores regularly. A backup on the same machine as the database is not sufficient disaster recovery.
* **How to verify:** Create a database record, recreate the application and PostgreSQL containers while keeping the volume, and confirm the record remains available. Also run the backup and restore scripts.

## 7. Logging and monitoring

* **Risk and evidence:** Application and NGINX logs provide useful request IDs, status codes, upstream information, and dependency errors, but logs alone do not prove the underlying infrastructure cause of every failure.
* **Impact:** Without monitoring and alerting, repeated failures could continue without being detected quickly.
* **Implemented fix / commit:** NGINX uses structured JSON access logs with request IDs and upstream information. The application also records structured request/dependency information.
* **Production follow-up:** Send logs to a central logging system, add metrics and alerts for error rates, latency, dependency failures, restarts, CPU, and memory usage. Protect logs from unauthorized access and define retention.
* **How to verify:** Inspect NGINX and application logs during normal requests and during a backend failure. Correlate entries using the request ID.

## 8. Availability and single points of failure

* **Risk and evidence:** The application layer has two instances behind NGINX, but NGINX, PostgreSQL, and Redis are each represented by a single container in this assessment environment.
* **Impact:** Failure of one of the single-instance services can still affect the whole application.
* **Implemented fix / commit:** Two application instances and NGINX upstream failover were implemented. The failure test stopped `app-01` and verified that traffic continued through `app-02`. Commit `25bdd3d`.
* **Production follow-up:** Use redundant load balancers, highly available database infrastructure, and an appropriate Redis deployment if these components are required to remain available during individual failures.
* **How to verify:** Stop one application instance and send requests through NGINX. Confirm traffic continues and that the recovered instance receives traffic again.

## 9. Dependency timeouts and failure handling

* **Risk and evidence:** PostgreSQL and Redis are dependencies of the application. Requests that wait indefinitely for a dependency can consume application resources and reduce availability.
* **Impact:** A slow or unavailable dependency can cause request queues, increased latency, and eventually application failure.
* **Implemented fix / commit:** Database and Redis operations use bounded timeouts, and NGINX has bounded connect/read timeouts and upstream retry behavior. Commit `548e8dc`.
* **Production follow-up:** Tune timeout values using real traffic and latency measurements. Add circuit-breaking or backoff where appropriate and make sure retries are safe for the relevant HTTP methods.
* **How to verify:** Stop or isolate a dependency in a controlled test and confirm the application returns within the configured timeout instead of hanging indefinitely.

## 10. Runtime resource limits and restart behavior

* **Risk and evidence:** A container without resource limits can consume excessive CPU or memory and affect other services on the host.
* **Impact:** Resource exhaustion can reduce availability or cause unrelated containers to fail.
* **Implemented fix / commit:** CPU and memory limits are defined for the application, NGINX, PostgreSQL, and Redis. Services also use restart policies where appropriate. Commit `7babf30`.
* **Production follow-up:** Set limits based on measured production usage, monitor resource pressure, and alert on repeated restarts or memory exhaustion.
* **How to verify:** Inspect the Compose configuration and container configuration to confirm the configured CPU and memory limits.

## Completed controls vs production work

### Implemented in this assessment

* Runtime database password instead of putting the password in the application image.
* No host ports for application, PostgreSQL, or Redis.
* Non-root application container.
* Pinned Python base image digest.
* Frontend/backend network separation.
* PostgreSQL persistent volume.
* Redis AOF persistence.
* Backup and restore scripts.
* Structured NGINX/application logging.
* Request IDs for correlating requests.
* Application redundancy and NGINX upstream failover.
* Bounded dependency and proxy timeouts.
* CPU and memory limits.
* Restart policies.

### Still needed for a production deployment

* Dedicated secret manager and credential rotation.
* External encrypted backup storage and tested disaster recovery.
* Container and dependency vulnerability scanning in CI.
* Centralized logging, metrics, and alerting.
* High availability for NGINX/load balancing and stateful dependencies where required.
* Stronger container hardening such as capability restrictions and read-only filesystems where practical.
* Formal access control and audit procedures.
* Production-specific resource and timeout tuning based on observed traffic.
