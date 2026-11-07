# System Architecture — Academic Regulation and Student Petition Triage Service

## 1. Project Overview

The Academic Regulation and Student Petition Triage Service is a multi-agent application that accepts student petitions, retrieves relevant university regulations, verifies evidence, and produces an eligibility position with a recommended routing decision.

The system supports five petition categories:

- Attendance
- Re-evaluation
- Re-registration
- Medical leave
- Grade grievance

The system is designed to avoid unsupported decisions. If the required regulation or evidence cannot be retrieved or verified, the petition is referred to the appropriate committee rather than receiving an invented eligibility decision.

## 2. Technology Stack

| Layer               | Technology                  |
| ------------------- | --------------------------- |
| Backend API         | FastAPI                     |
| Data validation     | Pydantic                    |
| Agent orchestration | LangGraph                   |
| LLM integration     | LangChain Core and Groq API |
| Retrieval           | Sentence Transformers       |
| Vector database     | ChromaDB                    |
| Document processing | PyPDF and python-docx       |
| Relational database | SQLite with SQLAlchemy      |
| Background queue    | Redis and RQ                |
| Frontend            | HTML, CSS and JavaScript    |
| Containerization    | Docker and Docker Compose   |
| Metrics             | Prometheus                  |
| Dashboards          | Grafana                     |
| Distributed tracing | OpenTelemetry and Jaeger    |
| Testing             | Pytest                      |
| Load testing        | Locust                      |

## 3. High-Level Architecture

```text
                    STUDENT
                       |
                       v
                WEB FRONTEND
                 (HTML/CSS/JS)
                       |
                       v
                  FASTAPI API
                       |
             +---------+---------+
             |                   |
             v                   v
        VALIDATION          SQLITE DATABASE
             |              (Petition/Run)
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
             | Selects retrieval tools
             v
       +-------------------+
       | REGULATION TOOLS  |
       +-------------------+
          |             |
          v             v
       CHROMADB     CLAUSE LOOKUP
          |             |
          +------+------+
                 |
                 v
        RETRIEVED PROVISIONS
                 |
                 v
        VERIFICATION AGENT
                 |
                 v
             ROUTING
                 |
        +--------+---------+
        |        |         |
        v        v         v
      GRANT    REFER     REJECT
        |     COMMITTEE    |
        +--------+---------+
                 |
                 v
          SQLITE DATABASE
             (Result)
                 |
                 v
          FRONTEND POLLING
                 |
                 v
          STUDENT RESULT


 OBSERVABILITY
      |
      +------> PROMETHEUS ------> GRAFANA
      |
      +------> OPENTELEMETRY --> JAEGER
```

## 4. Request Lifecycle

1. A student submits a petition through the web frontend.
2. FastAPI receives the request and validates it using Pydantic.
3. The petition and its processing run are stored in SQLite.
4. A background job is submitted to the Redis queue.
5. An RQ worker picks up the job and starts the LangGraph workflow.
6. The Research Agent classifies the petition and selects appropriate retrieval tools.
7. The retrieval tools search the regulation corpus in ChromaDB and perform exact clause lookups where required.
8. Retrieved provisions and findings are passed to the Verification Agent.
9. The Verification Agent checks whether the proposed claims are supported by retrieved evidence.
10. The routing node determines the final recommendation.
11. The result and audit information are persisted in SQLite.
12. The frontend polls the run endpoint and displays the processing status and result.

## 5. Multi-Agent Responsibilities

### Research Agent

The Research Agent is responsible for:

- Understanding and classifying the petition.
- Identifying relevant regulation topics.
- Selecting retrieval tools.
- Retrieving base provisions and applicable modifying or condonation provisions.
- Collecting evidence and clause references.
- Reporting missing or conflicting evidence.

### Verification Agent

The Verification Agent is responsible for:

- Checking whether proposed claims are supported by retrieved provisions.
- Checking citation references against the retrieved evidence.
- Identifying missing provisions and conflicting interpretations.
- Detecting when committee discretion is required.
- Preventing unsupported recommendations from reaching the final response.

### Routing Node

The routing node applies the verified outcome and determines whether the petition should be:

- Granted under an applicable provision.
- Referred to a committee.
- Rejected where the evidence supports that outcome.

If verification fails, evidence is missing, or escalation is required, the system defaults to committee referral.

## 6. Retrieval Architecture

The regulation retrieval pipeline consists of:

1. Document discovery from the corpus directories.
2. Parsing of supported PDF, DOCX, TXT and Markdown documents.
3. Splitting documents into manageable chunks.
4. Generating embeddings using Sentence Transformers.
5. Storing document chunks and metadata in ChromaDB.
6. Retrieving relevant provisions through semantic search.
7. Performing exact clause lookup when a specific reference is available.

The retrieval tools include:

- `search_regulation_provisions`
- `lookup_exact_clause`
- `search_condonation_provisions`

The ingestion pipeline uses document hashes and a manifest to avoid unnecessary reprocessing of unchanged documents.

## 7. Data Storage

### SQLite

SQLite stores:

- Petition records.
- Processing run status and results.
- Feedback records.
- Audit events.

### ChromaDB

ChromaDB stores embedded regulation chunks and associated metadata for semantic retrieval.

### Redis

Redis supports:

- Background job queuing.
- Worker communication.
- Job processing state.

### Persistent Storage

Docker volumes preserve application data, Redis data, Prometheus data and Grafana data across container restarts.

## 8. Observability

### Prometheus

Prometheus collects application metrics, including:

- Petition processing counts.
- Agent execution counts and durations.
- Tool call counts.
- LLM request and token usage.
- Active worker count.
- Processing latency.

### Grafana

Grafana provides dashboards for monitoring petition processing, agent activity, LLM usage, tool calls and worker activity.

### OpenTelemetry and Jaeger

OpenTelemetry instruments application operations and exports traces to Jaeger.

Tracing covers the petition processing workflow, agent execution, retrieval tools and LLM calls.

## 9. Deployment Architecture

Docker Compose runs the application as separate services:

- API service.
- Background worker service.
- Redis service.
- Frontend service.
- Jaeger service.
- Prometheus service.
- Grafana service.

The API and worker use the same application image and persistent application storage volume.

The frontend is served through Nginx.

## 10. Safety and Reliability

The system incorporates:

- Pydantic request validation.
- Input guardrails for suspicious prompt-injection patterns.
- Bounded agent steps and tool calls.
- Tool and LLM timeouts.
- Retry and backoff configuration.
- Failure handling in background jobs.
- Evidence verification before returning recommendations.
- Fail-safe committee referral when evidence is missing or verification fails.
- Structured logging and audit records.

The system must not fabricate university regulation clauses or present unverified claims as established policy.

## 11. Current Limitations

- The regulation corpus must contain the selected university's official, applicable regulations and examination bye-laws before real eligibility decisions can be validated.
- Semantic evaluation and groundedness metrics require a populated regulation corpus and representative evaluated cases.
- The current evaluation set includes synthetic test cases; it does not establish real-world regulatory accuracy.
- The toxicity and prompt-injection checks include heuristic components and are not exhaustive.
- Actual LLM cost estimation requires configured model pricing.

Until the official corpus is ingested and evaluated, the expected behavior for missing regulatory evidence is referral to the appropriate committee.
