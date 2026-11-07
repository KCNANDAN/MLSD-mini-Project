# Incident Log — Academic Regulation and Student Petition Triage Service

## 1. Purpose

This document records significant development, deployment and operational incidents encountered while implementing the Academic Regulation and Student Petition Triage Service.

The log captures symptoms, root causes, corrective actions and verification results to support debugging and future maintenance.

## 2. Incident Summary

| ID | Component | Incident | Status |
|---|---|---|---|
| INC-001 | Docker / Worker | Worker process crashed when using the default RQ worker on macOS | Resolved |
| INC-002 | Retrieval | Invalid `top_k=0` was not rejected | Resolved |
| INC-003 | Database / API | Petition submission failed because SQLite tables were missing in the Docker volume | Resolved |
| INC-004 | Frontend / API | Petition submission displayed a fetch failure due to the backend database initialization failure | Resolved |
| INC-005 | Observability | Jaeger initially showed API health and metrics traces but not the expected petition-processing trace | Resolved |
| INC-006 | Deployment | Docker build attempted to install unnecessary GPU-related PyTorch dependencies | Resolved |

## 3. Detailed Incident Records

### INC-001 — RQ Worker Process Crash on macOS

**Affected component:** Background worker

**Observed symptoms:**

The default RQ worker process terminated unexpectedly with a SIGABRT error while executing background jobs in the local macOS development environment.

**Root cause:**

The standard RQ worker uses a fork-based execution model. This caused compatibility problems in the local macOS environment with the application's Python and machine-learning dependencies.

**Corrective action:**

The worker implementation was changed to use RQ's `SimpleWorker`, which executes jobs without the same fork-based process model.

**Verification performed:**

- Worker startup completed successfully.
- The worker listened on the `petition-processing` queue.
- A synthetic petition job was picked up and processed.
- Job completion was visible in the worker logs.

**Status:** Resolved.

### INC-002 — Invalid Retrieval Top-K Value

**Affected component:** Retrieval layer

**Observed symptoms:**

A `top_k` value of zero was silently replaced by the configured default retrieval count instead of being rejected.

**Root cause:**

The original implementation used:

```python
result_count = top_k or settings.retrieval_top_k
```

In Python, zero is falsy, so the configured default was selected.

**Corrective action:**

The retrieval logic was changed to distinguish `None` from an explicitly supplied value:

```python
result_count = (
    settings.retrieval_top_k
    if top_k is None
    else top_k
)

if result_count < 1:
    raise ValueError("top_k must be at least 1")
```

**Verification performed:**

- Retrieval tests were executed.
- All 15 retrieval tests passed after the correction.
- Invalid zero values are now rejected.

**Status:** Resolved.

### INC-003 — SQLite Tables Missing in Docker Deployment

**Affected component:** API, database initialization and Docker deployment

**Observed symptoms:**

Petition submission through the Docker-hosted frontend failed.

The API logs showed a SQLAlchemy OperationalError:

```text
no such table: petitions
```

**Root cause:**

The fresh Docker application storage volume did not contain the SQLite tables. Database initialization was not being invoked during FastAPI application startup.

**Corrective action:**

Database initialization was added to the FastAPI lifespan startup procedure.

The database initialization function was also updated to import the registered models before creating tables:

```python
def initialize_database():
    """Create all registered database tables."""
    from database import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
```

The API and worker containers were rebuilt or recreated with the corrected application code.

**Verification performed:**

- Python compilation succeeded.
- The full test suite passed: 39 tests.
- SQLite inspection inside the API container confirmed the tables:
  - `audit_events`
  - `feedback`
  - `petitions`
  - `processing_runs`
- A synthetic petition was successfully submitted and processed through the Docker frontend.

**Status:** Resolved.

### INC-004 — Frontend Petition Submission Failure

**Affected component:** Frontend and API integration

**Observed symptoms:**

The frontend displayed a `Failed to fetch` message after a petition was submitted.

**Investigation:**

The API CORS preflight request was tested and returned the expected access-control headers.

Further inspection of the API logs identified the missing SQLite tables documented in INC-003.

**Root cause:**

The frontend submission failure was caused by the backend database initialization problem, not by the CORS configuration.

**Corrective action:**

The database initialization issue was corrected as documented in INC-003.

**Verification performed:**

- The frontend successfully submitted a synthetic petition.
- The API returned a run ID.
- The background worker processed the petition.
- The frontend displayed the completed result.

**Status:** Resolved.

### INC-005 — Petition Processing Trace Not Immediately Visible in Jaeger

**Affected component:** OpenTelemetry and Jaeger

**Observed symptoms:**

The initial Jaeger search displayed API health and metrics-related operations, but the expected petition-processing trace was not immediately visible.

**Investigation:**

The worker logs were inspected and the Jaeger service and OTLP endpoint configuration were checked.

The Jaeger search operation filter was changed to `petition.process`.

**Root cause:**

The expected trace was not visible in the initial search because the search was not filtered for the petition-processing operation.

**Corrective action:**

The Jaeger UI was queried using the correct service and operation.

**Verification performed:**

A petition-processing trace was located in Jaeger.

The trace showed the `academic-petition-triage` service, the `petition.process` operation and multiple child spans.

**Status:** Resolved.

### INC-006 — Unnecessary GPU Dependencies During Docker Build

**Affected component:** Docker image and PyTorch installation

**Observed symptoms:**

The initial Docker build attempted to download large GPU-related dependencies, increasing image build time and download size.

**Root cause:**

The default PyTorch installation dependency resolution included GPU-related packages that were unnecessary for this CPU-based application deployment.

**Corrective action:**

The Dockerfile was updated to install the CPU-only PyTorch build explicitly:

```dockerfile
RUN python -m pip install \
    --index-url https://download.pytorch.org/whl/cpu \
    --extra-index-url https://pypi.org/simple \
    "torch==2.15.0+cpu"
```

The remaining application requirements were installed afterward.

**Verification performed:**

- Docker image build completed successfully.
- The resulting image was tagged `academic-petition-triage:latest`.
- Docker Compose services started successfully using the image.

**Status:** Resolved.

## 4. Operational Notes

- The regulation corpus was empty during the initial end-to-end integration tests.
- Consequently, the system correctly referred petitions to a committee when no regulatory evidence was available.
- This behavior is an expected fail-safe outcome, not a processing failure.
- The system must not fabricate citations or eligibility decisions when evidence is missing.
- Synthetic student references were used during development and testing.

## 5. Current Incident Status

All six incidents documented above were resolved during implementation.

Future incidents should be added with a unique identifier and should include the observed symptoms, root cause, corrective action and verification evidence.

This document should be maintained throughout development, testing and deployment.