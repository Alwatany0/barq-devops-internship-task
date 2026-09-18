# Log analysis

I checked all three supplied logs without changing the original files:

* `logs/access.log`
* `logs/error.log`
* `logs/application.log`

The logs are synthetic and use UTC timestamps.

## 1. Log coverage and file checks

| Log               | Lines | Valid | Malformed | Duplicate lines |
| ----------------- | ----: | ----: | --------: | --------------: |
| `access.log`      |   726 |   725 |         1 |               5 |
| `error.log`       |    68 |    68 |         0 |               0 |
| `application.log` |   730 |   729 |         1 |               2 |

The access log had five duplicated request IDs:

* `lab-000121`
* `lab-000241`
* `lab-000361`
* `lab-000481`
* `lab-000601`

Each appeared twice.

The logs are from the incident on `2026-08-20`, covering roughly `11:00–11:30 UTC`.

## 2. Distinct requests and retries

I used `request_id` from the access log to count client requests.

I did not count every upstream attempt as a new request because NGINX can retry the same request against another backend.

For example:

```text
request_id:      lab-000124
upstream:        .12:8080, .11:8080
upstream_status: 502, 200
```

This is one client request with two backend attempts.

After removing the malformed access record and duplicate request IDs, there were:

```text
720 distinct client requests
```

## 3. Status counts and error rate

| Status    |   Count |
| --------- | ------: |
| 200       |     615 |
| 404       |      10 |
| 502       |      40 |
| 503       |      47 |
| 504       |       8 |
| **Total** | **720** |

There were 95 5xx responses.

I used the 720 distinct client requests as the denominator:

```text
95 / 720 × 100 = 13.19%
```

So the 5xx error rate was **13.19%**.

The 404 responses are not included in this calculation.

## 4. Where the failures happened

### By path

| Status | Path       | Count |
| ------ | ---------- | ----: |
| 502    | `/`        |    10 |
| 502    | `/counter` |    10 |
| 502    | `/health`  |    10 |
| 502    | `/records` |    10 |
| 503    | `/counter` |    16 |
| 503    | `/ready`   |    23 |
| 503    | `/records` |     8 |
| 504    | `/records` |     8 |

There were three clear patterns:

* 502s during the NGINX/backend connection problem.
* 503s during the Redis timeout periods.
* 504s on `/records` when NGINX waited too long for the upstream response.

### By time

| UTC minute | 5xx |
| ---------- | --: |
| 11:05      |   8 |
| 11:06      |   8 |
| 11:07      |   8 |
| 11:08      |   8 |
| 11:09      |   8 |
| 11:12      |   8 |
| 11:13      |   7 |
| 11:14      |   8 |
| 11:15      |   8 |
| 11:20      |   8 |
| 11:21      |   8 |
| 11:25      |   4 |
| 11:26      |   4 |

The NGINX logs show:

* `172.23.0.12:8080` = `app-02`
* `172.23.0.11:8080` = `app-01`

From 11:05 to 11:09, there were 60 connection-refused errors against `app-02`.

There were also 19 requests where NGINX retried another backend and the request eventually succeeded.

The application log later showed Redis timeouts on both applications:

* `app-01`: 23
* `app-02`: 24

So there were 47 Redis `TimeoutError` events in total.

At 11:25–11:26, `/records` had upstream response-header timeouts involving both application instances.

## 5. Latency

The `request_time` field from the access log was used for client latency.

Results:

```text
Median: 54 ms
p95:    2001 ms
```

The percentile calculation used linear interpolation:

```text
position = (n - 1) × p
```

The values are in milliseconds.

## 6. Upstream retries

There were 19 requests where NGINX tried more than one upstream.

All 19 eventually returned successfully.

Example:

```text
request_id:      lab-000124
upstream:        .12:8080, .11:8080
upstream_status: 502, 200
```

The first attempt failed against `app-02`, then NGINX retried `app-01`.

So:

```text
Requests with retries: 19
Successful after retry: 19
```

These are still counted as 19 client requests, not 38.

## 7. Incident timeline

### 11:05–11:09 UTC — app-02 connection failures

NGINX started getting connection-refused errors from `172.23.0.12:8080` (`app-02`).

The access log contains the related 502 responses.

Some requests were retried against `app-01` and succeeded.

### 11:12–11:15 UTC — Redis timeouts

The application log started showing Redis `TimeoutError` events on both application instances.

The access log shows 503 responses for `/counter`, `/ready`, and `/records` during the same period.

### 11:20–11:21 UTC — Redis problem happens again

The same Redis timeout pattern appears again.

Both application instances are affected.

### 11:25–11:26 UTC — `/records` timeouts

NGINX reports upstream response-header timeouts for `/records`.

These requests ended as 504 responses.

Unlike the earlier connection-refused errors, NGINX had an upstream connection but did not receive the response headers in time.

### Around 11:30 UTC — log rotation

There is a log collector rotation notice around 11:30 UTC.

I did not treat this as an application failure.

## 8. Correlated requests

### Failed request

```text
Request ID: lab-000122
Timestamp:  2026-08-20T11:05:02.503Z
Method:     GET
Path:       /health
Status:     502
Upstream:   .12:8080
Time:       0.003
```

The same request ID appears in the NGINX error log with a connection-refused error.

There is no matching application request in the application log.

This means the request failed at the NGINX-to-backend connection stage and did not reach Flask.

### Successful retry

```text
Request ID: lab-000124
Timestamp:  2026-08-20T11:05:07.620Z
Method:     GET
Path:       /ready
Status:     200
Upstream:   .12:8080, .11:8080
Status:     502, 200
Time:       0.12
```

The first attempt to `.12` failed and NGINX retried `.11`.

The application log contains the same request ID and shows the successful request on `app-01`.

This is a good example of NGINX failing over to the other backend.

## 9. What type of errors were these?

### NGINX/backend connectivity

The 11:05–11:09 issue looks like a connection problem between NGINX and `app-02`.

The evidence is:

* NGINX reports `connection refused`.
* The access log shows 502 responses.
* The affected upstream is `.12:8080`.
* Some requests succeed after retrying `.11`.
* The failed request has no application log entry.

### Redis/dependency problem

The later 503s are related to Redis.

The application log contains:

```text
event=dependency_error
dependency=redis
error_type=TimeoutError
```

These errors occur on both application instances and match the 503 responses in the access log.

### `/records` timeout

The 11:25–11:26 errors are NGINX upstream response-header timeouts.

The logs show that NGINX was waiting for the application response.

They do not show exactly why the application took too long.

## 10. What the logs don't prove

The logs show where the failures happened, but not always why they happened.

They do not prove:

* why `app-02` refused connections;
* why Redis timed out;
* whether Redis had a resource problem;
* why `/records` became slow;
* CPU or memory usage;
* container restart history;
* host/network problems;
* whether PostgreSQL caused the `/records` timeout;
* why some log records were duplicated.

If I had the environment running during the incident, I would check:

```bash
docker compose ps
docker compose logs app-01 app-02 nginx postgres redis
docker inspect app-01 app-02 postgres redis
docker stats --no-stream
docker network inspect barq-frontend
docker network inspect barq-backend
```

Then check PostgreSQL:

```bash
docker exec postgres pg_isready -U barq_app -d barq_tasks
```

And Redis:

```bash
docker exec redis redis-cli ping
```

I would also compare container restarts and resource usage with the timestamps in the logs.

## Commands / scripts

The logs were processed with Bash/Python/Linux tools.

For example, the number of physical lines was checked with:

```bash
wc -l logs/access.log logs/error.log logs/application.log
```

The JSON records were then parsed to check malformed lines, duplicates, request IDs, statuses, upstream attempts, timestamps and latency.

The original log files were kept unchanged.

## Conclusions

The incident had three main failure periods:

1. `11:05–11:09` — NGINX could not connect to `app-02`.
2. `11:12–11:15` and `11:20–11:21` — Redis timed out on both application instances.
3. `11:25–11:26` — `/records` requests timed out waiting for the upstream response.

There were **720 distinct client requests** and **95 5xx responses**, giving a **13.19% 5xx rate**.

There were **19 upstream retries**, and all 19 eventually succeeded.

The logs are enough to identify and correlate the failures, but not enough to prove the underlying infrastructure cause in every case.
