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

The official university regulation corpus is populated with **PES University** regulations and examination bye-laws:

- `corpus/regulations/PES_University_Act_Official.txt`
- `corpus/regulations/PES_University_Profroma.pdf`
- `corpus/regulations/PESU_Calendar_of_Events_Aug_Dec_2026.pdf`
- `corpus/examination_bylaws/PESU_Learning_and_Assessment_Process.txt`
- `corpus/examination_bylaws/PESU_Current_Official_FAQ.txt`

Supported document formats include PDF, DOCX, TXT and Markdown, with native OCR page-marker tracking (`===== PAGE n =====`).

Run the ingestion pipeline:

```bash
python -m ingestion.ingest
```

The ingestion process parses documents, creates metadata-tagged chunks, generates embeddings with Sentence Transformers (`all-MiniLM-L6-v2`), and stores them in ChromaDB.

Document hashes and an ingestion manifest (`storage/ingestion_manifest.json`) are used to avoid unnecessary reprocessing of unchanged documents.

## Running Tests

Install dependencies in a Python 3.11 virtual environment:

```bash
python -m pip install -r requirements.txt
```

Run the full test suite:

```bash
python -m pytest -q
```

The automated test suite covers:
- `tests/test_validation.py` — Petition schemas, guardrails, and input sanitization.
- `tests/test_retrieval.py` — Document parsing, chunking, embeddings, and vector store retrieval.
- `tests/test_agents.py` — LangGraph orchestration, Research Agent, and routing logic.
- `tests/test_verification.py` — Citation verification, quotation checks, and JSON response extraction.
- `tests/test_reliability.py` — Circuit breaker states, timeout backoff, retry limits, and recovery.
- `tests/test_api.py` — FastAPI endpoints, health check, and petition submission.
- `tests/test_integration.py` — End-to-end database, queue, worker, and public run lookup.

**All 52 automated tests passed.**

## Evaluation

Run the evaluation framework:

```bash
python -m evaluation.evaluate --mode all
```

To run against live Groq LLM inference:

```bash
python -m evaluation.evaluate --mode all --live
```

The evaluation dataset contains 22 synthetic cases:
- 12 interactive multi-agent pipeline cases (EV001–EV012).
- 10 static guardrails, prompt-injection, toxicity, and safety self-test cases (EV013–EV022).

### Evaluation Results

| Metric | Result | Target | Status |
|---|---:|---:|---|
| Total test cases | 22 | 22 | Complete |
| Evaluated cases | 22 | 22 | Complete |
| Passed cases | 22 | 22 | Complete |
| Failed cases | 0 | 0 | Complete |
| **Overall Pass Rate** | **100%** | $\ge 90\%$ | **PASSED** |

### Semantic RAG Evaluation Metrics

| Metric | Observed Score | Target Threshold | Status |
|---|---:|---:|---|
| **Mean Groundedness** | **0.955** | $\ge 0.85$ | PASSED |
| **Mean Faithfulness** | **0.970** | $\ge 0.85$ | PASSED |
| **Mean Context Relevance** | **0.865** | $\ge 0.70$ | PASSED |
| **Hallucination Rate** | **0.000** | $\le 0.05$ | PASSED |

The full evaluation report is stored at:

```text
storage/evaluation_report.json
```

## Load Testing & End-to-End Processing SLO

### 1. HTTP Endpoint Load Test (Locust)

```bash
locust -f load_testing/locustfile.py --host http://localhost:8002
```

Recorded metrics:
- 482 HTTP requests
- 152 petition submissions
- 330 run-status requests
- 0 HTTP failures
- Aggregate HTTP p95 latency: ~15 ms

### 2. Multi-Worker End-to-End Processing Latency Benchmark

The project includes an end-to-end petition-processing benchmark measuring true system latency (from queue submission through multi-agent retrieval to completed database state):

```bash
python -m load_testing.measure_slo --count 30 --workers 3
```

Benchmark results (across 3 simultaneous workers):
- **Throughput:** 2.41 petitions/sec
- **Success rate:** 100.0% (30/30)
- **Median latency (p50):** 1.05s
- **p90 latency:** 1.82s
- **p95 latency:** **1.96s** (Target SLO: $\le 30.0$s)
- **p99 latency:** 2.11s

The benchmark report is stored at `storage/slo_benchmark_report.json`.

## Worker Scaling

Scale the background workers horizontally using Docker Compose:

```bash
docker compose up -d --scale worker=3
```

Inspect worker containers:

```bash
docker compose ps worker
```

Scale back to a single worker:

```bash
docker compose up -d --scale worker=1
```

## Reliability and Circuit Breaker

The system implements a 3-state Circuit Breaker (`CLOSED`, `OPEN`, `HALF_OPEN`) wrapping external LLM requests:
- **Failure Threshold:** Configurable (default: 5 consecutive failures trips circuit to `OPEN`).
- **Recovery Window:** 30 seconds before probing health in `HALF_OPEN`.
- **Exponential Backoff:** Retries transient failures with exponential backoff (`max_agent_retries=2`, `retry_backoff_seconds=0.5`).
- **Fail-Safe Fallback:** When circuit is open or downstream fails, the agent graph gracefully routes the petition to `refer-to-committee` with human escalation required.

## Frontend Feedback Interface

Students and staff can provide feedback directly on completed petition decisions:
- Interactive feedback card embedded below completed petition outcomes.
- Collects satisfaction rating and explanation.
- Persisted via `POST /api/v1/feedback`.

## Monitoring and Observability

### Prometheus

Collects application metrics:
- Petition processing counts and durations.
- Agent execution counts and durations.
- Tool call counts and latency.
- LLM request, token usage, and cost tracking.
- Active worker counts (`livesum`).

### Grafana

Provisioned with the **Academic Petition Triage - Operations** dashboard:
- Completed / Failed petition status gauges.
- Active workers gauge.
- **Histogram-based p95 and median processing latency panels**.
- Agent execution latency percentiles.
- Tool invocation breakdown and LLM token usage.

### Jaeger

Distributed tracing for every petition run:
- Trace `petition.process` spanning FastAPI submission, queue pickup, agent execution, retrieval tool calls, and verification.

## Documentation

Additional project documentation:

- [System Architecture](docs/architecture.md)
- [Data Contract](docs/data_contract.md)
- [Operations Runbook](docs/runbook.md)
- [Incident Log](docs/incident_log.md)
- [Evaluation Report](docs/evaluation_report.md)

## Security Considerations

- Never commit `.env`. Use `.env.example` as a template.
- Do not expose API keys or deployment credentials.
- Use synthetic student references in development and load testing.
- Input guardrails flag prompt-injection and adversarial overrides.
- Verify regulatory evidence before presenting eligibility recommendations.
- Preserve audit records and processing history.

## Project Status

All project milestones are complete:
- Official university regulation corpus (PES University) populated.
- Retrieval pipeline and ChromaDB indexing implemented.
- LangGraph Research and Verification agents with strict quotation validation.
- All 22 evaluation cases executed with 100% pass rate and semantic metrics.
- Circuit breaker resilience and retry backoff verified.
- 3-worker scaling and end-to-end p95 SLO measured and verified.
- Frontend feedback UI connected to feedback API.
- Grafana dashboard provisioned with histogram p95 panels.
- Automated tests passing.

---

**Academic Regulation and Student Petition Triage Service**  
Multi-Agent Systems | Retrieval-Augmented Generation | AgentOps | Observability | LLM Evaluation