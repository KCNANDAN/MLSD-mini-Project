# Operations Runbook — Academic Regulation and Student Petition Triage Service

## 1. Purpose

This runbook describes how to start, stop, monitor and troubleshoot the Academic Regulation and Student Petition Triage Service.

The application is deployed using Docker Compose and consists of seven services:

- API
- Background worker
- Redis
- Frontend
- Jaeger
- Prometheus
- Grafana

## 2. Prerequisites

Before starting the application, ensure that:

- Docker Desktop is installed and running.
- Docker Compose is available.
- The project repository is available locally.
- The `.env` file exists in the project root.
- Required environment variables are configured.
- The Docker image can be built successfully.

Never commit the actual `.env` file or expose API keys in logs or screenshots.

## 3. Starting the Application

Open a terminal in the project root:

```bash
cd academic-petition-triage
```

Validate the Docker Compose configuration:

```bash
docker compose config --quiet
```

Build the application image:

```bash
docker compose build
```

Start all services:

```bash
docker compose up -d
```

Check service status:

```bash
docker compose ps
```

The API and Redis should report healthy status after their health checks succeed.

## 4. Application URLs

| Component | URL |
|---|---|
| Frontend | http://localhost:5500 |
| API health | http://localhost:8002/health |
| API documentation | http://localhost:8002/docs |
| Prometheus metrics | http://localhost:8002/metrics |
| Prometheus UI | http://localhost:9090 |
| Grafana | http://localhost:3000 |
| Jaeger UI | http://localhost:16686 |

The API is exposed on host port `8002` to avoid conflicts with other local development projects.

## 5. Submitting and Monitoring a Petition

1. Open the frontend.
2. Enter synthetic student reference information.
3. Select a petition category.
4. Provide the admission batch and semester.
5. Enter the petition description.
6. Submit the petition.
7. Record the returned run ID.
8. Wait for the frontend to poll the processing endpoint.
9. Inspect the completed result and its citations or escalation information.

The API endpoints are:

```text
POST /api/v1/petitions
GET  /api/v1/runs/{run_id}
POST /api/v1/feedback
```

A petition initially enters the `queued` state and may transition to `running`, followed by `completed` or `failed`.

## 6. Monitoring Services

### Docker service status

```bash
docker compose ps
```

### Application logs

View all service logs:

```bash
docker compose logs --tail=100
```

View API logs:

```bash
docker compose logs --tail=100 api
```

View worker logs:

```bash
docker compose logs --tail=100 worker
```

Follow worker logs continuously:

```bash
docker compose logs -f worker
```

### Prometheus

Open:

http://localhost:9090

Inspect application metrics through:

```bash
curl -s http://localhost:8002/metrics
```

### Grafana

Open:

http://localhost:3000

Use the provisioned Academic Petition Triage dashboard to inspect petition counts, worker activity, agent execution, LLM usage and tool calls.

### Jaeger

Open:

http://localhost:16686

Select the `academic-petition-triage` service and search for the `petition.process` operation to inspect distributed traces.

## 7. Common Troubleshooting Procedures

### 7.1 API is unavailable

Check API status:

```bash
docker compose ps api
```

Inspect API logs:

```bash
docker compose logs --tail=100 api
```

Restart the API:

```bash
docker compose restart api
```

Verify health:

```bash
curl -i http://localhost:8002/health
```

### 7.2 Worker is not processing jobs

Inspect worker status:

```bash
docker compose ps worker
```

Inspect worker logs:

```bash
docker compose logs --tail=100 worker
```

Check Redis:

```bash
docker compose exec redis redis-cli ping
```

Expected Redis response:

```text
PONG
```

Restart the worker if required:

```bash
docker compose restart worker
```

### 7.3 Redis is unavailable

Inspect Redis logs:

```bash
docker compose logs --tail=100 redis
```

Check Redis connectivity:

```bash
docker compose exec redis redis-cli ping
```

Restart Redis if required:

```bash
docker compose restart redis
```

### 7.4 Petition remains queued

1. Check whether the worker is running.
2. Inspect worker logs for job pickup and execution.
3. Check Redis connectivity.
4. Inspect the run status through the API.
5. Check for worker exceptions or failed jobs.

Do not manually delete queued jobs or modify database records without investigating the failure.

### 7.5 Petition is referred to the committee

A committee referral may be an expected fail-safe result.

Check:

- Whether the regulation corpus has been populated.
- Whether the relevant provisions were retrieved.
- Whether base and modifying provisions were both found.
- Whether verification passed.
- Whether committee discretion is required.

A missing citation must not be replaced with an invented regulation reference.

### 7.6 Prometheus metrics are missing

Check:

```bash
docker compose ps prometheus api
```

Inspect Prometheus targets at:

http://localhost:9090/targets

Verify the API metrics endpoint:

```bash
curl -s http://localhost:8002/metrics
```

### 7.7 Jaeger traces are missing

Check:

```bash
docker compose ps jaeger
docker compose logs --tail=100 jaeger
docker compose logs --tail=100 worker
```

Verify that the OTLP endpoint is configured for the Docker network:

```text
http://jaeger:4317
```

## 8. Restart and Shutdown Procedures

Restart all services:

```bash
docker compose restart
```

Stop the application while preserving persistent volumes:

```bash
docker compose down
```

Start it again:

```bash
docker compose up -d
```

Do not use `docker compose down -v` during routine shutdown. The `-v` option removes Compose-managed volumes and can delete persistent application data.

## 9. Scaling Background Workers

The worker service can be scaled using Docker Compose:

```bash
docker compose up -d --scale worker=3
```

Inspect worker containers:

```bash
docker compose ps worker
```

Return to one worker:

```bash
docker compose up -d --scale worker=1
```

Scaling should be tested with synthetic petitions and monitored for database contention, queue throughput and resource usage.

## 10. Data and Recovery Considerations

The application uses persistent Docker volumes for:

- Application storage, including SQLite and ChromaDB.
- Redis data.
- Prometheus time-series data.
- Grafana configuration and dashboards.

Before performing destructive maintenance:

1. Stop or quiesce application writes.
2. Create appropriate backups of persistent data.
3. Confirm backup files are readable.
4. Record the maintenance operation.
5. Restore only after validating the target environment.

Do not delete persistent volumes as a routine troubleshooting step.

## 11. Security and Operational Rules

- Never expose API keys or passwords.
- Never commit `.env`.
- Use synthetic student references for demonstrations and load testing.
- Do not use real student records in test data.
- Do not treat unverified LLM output as an official academic decision.
- Preserve logs and audit information during incident investigation.
- Escalate missing or conflicting regulatory evidence to a human committee.

## 12. Incident Recording

Every significant incident should be documented in `docs/incident_log.md`.

Record:

- Incident identifier.
- Date and time.
- Affected component.
- Observed symptoms.
- Root cause, if known.
- Corrective action.
- Verification performed.
- Current status.

This runbook should be updated whenever deployment procedures, service configuration or recovery steps change.