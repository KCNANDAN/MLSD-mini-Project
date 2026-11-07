# Academic Regulation and Student Petition Triage Service

A multi-agent, evidence-grounded system for processing academic petitions, retrieving university regulations, verifying eligibility claims, and recommending appropriate administrative action.

## Overview

The Academic Regulation and Student Petition Triage Service is designed to automate the initial assessment of student petitions using retrieval-augmented generation (RAG) and multi-agent orchestration.

Students can submit petitions through a web interface. The backend validates the request, queues it for asynchronous processing, retrieves relevant regulatory provisions, and verifies the evidence before producing a recommendation.

The system supports five petition categories:

- Attendance
- Re-evaluation
- Re-registration
- Medical leave
- Grade grievance

The service follows a fail-safe approach: when regulatory evidence is missing, conflicting, or insufficiently verified, the petition is referred for human or committee review instead of generating an unsupported eligibility decision.

## Key Features

- Multi-agent workflow orchestrated using LangGraph.
- Separate Research Agent and Verification Agent responsibilities.
- Tool-based regulatory retrieval.
- Semantic search using Sentence Transformers and ChromaDB.
- Exact clause lookup and condonation provision retrieval.
- Asynchronous petition processing using FastAPI, Redis and RQ.
- Evidence-backed recommendations with citation verification.
- Bounded agent execution, timeouts and retry configuration.
- SQLite persistence and audit records.
- Prompt-injection guardrails and input validation.
- Prometheus metrics and Grafana dashboards.
- Distributed tracing using OpenTelemetry and Jaeger.
- Synthetic evaluation dataset containing 22 test cases.
- Locust-based load testing with a deterministic stub LLM.
- Docker Compose deployment.

## Architecture

```text
                  STUDENT
                     |
                     v
                WEB FRONTEND
                     |
                     v
                  FASTAPI
                     |
              VALIDATION
                     |
                     v
                REDIS QUEUE
                     |
                     v
              BACKGROUND WORKER
                     |
                     v
              LANGGRAPH WORKFLOW
                     |
                     v
                RESEARCH AGENT
                     |
                     v
              REGULATION TOOLS
                     |
              +------+------+
              |             |
              v             v
           CHROMADB     CLAUSE LOOKUP
              |             |
              +------+------+
                     |
                     v
              VERIFICATION AGENT
                     |
                     v
                ROUTING NODE
                     |
           +---------+---------+
           |         |         |
           v         v         v
         GRANT     REFER     REJECT
                   TO
                COMMITTEE
                     |
                     v
                SQLITE DB
                     |
                     v
                 FRONTEND
```

### Observability Architecture

```text
Application Services
        |
        +------> Prometheus ------> Grafana
        |
        +------> OpenTelemetry --> Jaeger
```

## Technology Stack

| Component | Technology |
|---|---|
| Backend | Python 3.11, FastAPI |
| Validation | Pydantic |
| Agent orchestration | LangGraph |
| LLM integration | LangChain Core, Groq API |
| Embeddings | Sentence Transformers |
| Vector database | ChromaDB |
| Document parsing | PyPDF, python-docx |
| Relational database | SQLite, SQLAlchemy |
| Background processing | Redis, RQ |
| Frontend | HTML, CSS, JavaScript |
| Containerization | Docker, Docker Compose |
| Metrics | Prometheus |
| Dashboards | Grafana |
| Distributed tracing | OpenTelemetry, Jaeger |
| Unit and integration tests | Pytest |
| Load testing | Locust |

## Project Structure

```text
academic-petition-triage/
│
├── agents/
│   ├── graph.py
│   ├── research_agent.py
│   ├── verification_agent.py
│   ├── routing.py
│   ├── state.py
│   └── tools.py
│
├── api/
│   ├── main.py
│   ├── dependencies.py
│   ├── routes/
│   └── schemas/
│
├── config/
│   ├── settings.py
│   ├── logging_config.py
│   └── prompts.yaml
│
├── database/
│   ├── connection.py
│   ├── models.py
│   └── repository.py
│
├── retrieval/
│   ├── document_loader.py
│   ├── parser.py
│   ├── chunker.py
│   ├── embeddings.py
│   ├── vector_store.py
│   ├── retriever.py
│   └── clause_lookup.py
│
├── ingestion/
│   └── ingest.py
│
├── services/
│   ├── llm_service.py
│   ├── queue_service.py
│   ├── petition_service.py
│   ├── run_service.py
│   └── feedback_service.py
│
├── validation/
│   ├── validators.py
│   ├── quarantine.py
│   └── guardrails.py
│
├── worker/
│   ├── worker.py
│   └── tasks.py
│
├── observability/
│   ├── metrics.py
│   ├── tracing.py
│   └── cost_tracker.py
│
├── evaluation/
│   ├── evaluation_set.json
│   ├── evaluator.py
│   └── evaluate.py
│
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── app.js
│
├── monitoring/
│   ├── prometheus.yml
│   └── grafana/
│
├── load_testing/
│   ├── locustfile.py
│   └── stub_llm.py
│
├── tests/
│   ├── test_api.py
│   ├── test_validation.py
│   ├── test_agents.py
│   ├── test_retrieval.py
│   └── test_integration.py
│
├── corpus/
│   ├── regulations/
│   └── examination_bylaws/
│
├── docs/
│   ├── architecture.md
│   ├── data_contract.md
│   ├── runbook.md
│   ├── incident_log.md
│   └── evaluation_report.md
│
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
├── .dockerignore
└── .gitignore
```

## Prerequisites

- Docker Desktop
- Docker Compose
- Python 3.11 for local development
- Groq API key for live LLM execution

## Configuration

Clone the repository and enter the project directory:

```bash
git clone <your-repository-url>
cd academic-petition-triage
```

Create the environment file:

```bash
cp .env.example .env
```

Configure the required environment variables in `.env`.

The actual API key must remain in `.env` and must never be committed to Git.

The `.env.example` file contains configuration placeholders for other developers.

## Running with Docker Compose

Validate the Compose configuration:

```bash
docker compose config --quiet
```

Build the application image:

```bash
docker compose build
```

Start the complete application:

```bash
docker compose up -d
```

Inspect service status:

```bash
docker compose ps
```

View application logs:

```bash
docker compose logs -f api
```

View worker logs:

```bash
docker compose logs -f worker
```

Stop the application:

```bash
docker compose down
```

Persistent volumes are retained when using the normal shutdown command.

## Application Access

| Service | Address |
|---|---|
| Web frontend | http://localhost:5500 |
| API health | http://localhost:8002/health |
| Swagger documentation | http://localhost:8002/docs |
| Prometheus metrics | http://localhost:8002/metrics |
| Prometheus UI | http://localhost:9090 |
| Grafana | http://localhost:3000 |
| Jaeger | http://localhost:16686 |

Grafana credentials are configured through environment variables. Do not publish deployment credentials.

## API Endpoints

The API uses the `/api/v1` prefix.

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/v1/petitions` | Submit a new petition |
| GET | `/api/v1/runs/{run_id}` | Retrieve processing status and result |
| POST | `/api/v1/feedback` | Submit feedback |
| GET | `/health` | Health check |
| GET | `/metrics` | Prometheus metrics |

### Petition Processing

A petition follows these processing states:

```text
QUEUED
   |
   v
RUNNING
   |
   +------> COMPLETED
   |
   +------> FAILED
```

A completed petition can receive one of three routing recommendations:

- `grant-under-provision`
- `refer-to-committee`
- `reject`

## Regulation Corpus and Ingestion

Place official university regulations in:

```text
corpus/regulations/
```

Place official examination bye-laws in:

```text
corpus/examination_bylaws/
```

Supported document formats include PDF, DOCX, TXT and Markdown.

Run the ingestion pipeline:

```bash
python -m ingestion.ingest
```

The ingestion process parses documents, creates chunks, generates embeddings and stores them in ChromaDB.

Document hashes and an ingestion manifest are used to avoid unnecessary reprocessing of unchanged documents.

Only official, applicable university documents should be used for regulatory decisions.

## Running Tests

Install dependencies in a Python 3.11 virtual environment:

```bash
python -m pip install -r requirements.txt
```

Run the full test suite:

```bash
python -m pytest -q
```

Run an individual test module:

```bash
python -m pytest tests/test_agents.py -v
```

The implemented test suite previously passed **39 tests**.

## Evaluation

Run the evaluation framework:

```bash
python -m evaluation.evaluate
```

The evaluation dataset contains 22 synthetic cases.

### Observed Evaluation Results

| Metric | Result |
|---|---:|
| Total cases | 22 |
| Evaluated | 10 |
| Passed | 10 |
| Failed | 0 |
| Pending | 12 |
| Pass rate among evaluated cases | 100% |

The 12 pending cases require live retrieval or agent-generated outputs.

The observed pass rate applies only to the 10 evaluated static checks. It does not represent overall system accuracy or real-world regulatory correctness.

The generated report is stored at:

```text
storage/evaluation_report.json
```

## Load Testing

The project includes a Locust workload and deterministic stub LLM for load testing.

The stub can be enabled through environment configuration:

```text
USE_STUB_LLM=true
STUB_LLM_LATENCY_MS=100
```

Start the application with the corresponding configuration, then run:

```bash
locust -f load_testing/locustfile.py --host http://localhost:8002
```

Open the Locust interface at:

http://localhost:8089

The previously executed test recorded:

- 482 HTTP requests
- 152 petition submissions
- 330 run-status requests
- 0 HTTP failures
- Approximately 2.2 requests per second
- Aggregate HTTP p95 latency of approximately 15 ms

These are historical test results. The HTTP p95 value is not end-to-end petition-processing latency.

## Worker Scaling

Scale the background workers using:

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

## Monitoring and Observability

### Prometheus

Collects application metrics such as:

- Petition processing counts.
- Agent execution counts and durations.
- Tool call counts.
- LLM request and token usage.
- Active worker count.

### Grafana

Provides dashboards for inspecting application activity and operational metrics.

### Jaeger

Provides distributed traces for petition processing, agent execution, retrieval tools and LLM calls.

## Documentation

Additional project documentation:

- [System Architecture](docs/architecture.md)
- [Data Contract](docs/data_contract.md)
- [Operations Runbook](docs/runbook.md)
- [Incident Log](docs/incident_log.md)
- [Evaluation Report](docs/evaluation_report.md)

## Current Limitations

- The official university regulation corpus has not yet been populated.
- Real-world eligibility accuracy has not been established.
- Twelve evaluation cases remain pending live retrieval or agent evaluation.
- Semantic groundedness and faithfulness evaluation remain incomplete.
- Prompt-injection and toxicity checks include heuristic components.
- Actual model cost estimation requires configured model pricing.
- The previously recorded load test does not establish end-to-end processing p95 latency.

Until the official university regulations and examination bye-laws are ingested and evaluated, missing regulatory evidence must result in safe committee referral.

## Security Considerations

- Never commit `.env`.
- Do not expose API keys or deployment credentials.
- Use synthetic student references in development and load testing.
- Avoid storing unnecessary personal information in logs.
- Verify regulatory evidence before presenting eligibility recommendations.
- Preserve audit records and processing history.

## Project Status

The application includes the core API, multi-agent workflow, retrieval pipeline, asynchronous processing, database persistence, frontend, monitoring, evaluation framework, Docker deployment and automated tests.

The next major milestone is ingestion and evaluation against an official university regulation corpus.

---

**Academic Regulation and Student Petition Triage Service**  
Multi-Agent Systems | Retrieval-Augmented Generation | AgentOps | Observability | LLM Evaluation