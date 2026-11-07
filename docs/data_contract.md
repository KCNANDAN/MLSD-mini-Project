# Data Contract — Academic Regulation and Student Petition Triage Service

## 1. Purpose

This document defines the data exchanged between the frontend, FastAPI backend, background worker, multi-agent workflow, retrieval layer and persistence layer.

The contract establishes consistent request validation, processing status, result structure, citations and feedback handling.

## 2. Petition Submission Contract

**Endpoint:** `POST /api/v1/petitions`

**Content-Type:** `application/json`

### Request fields

| Field | Type | Required | Validation |
|---|---|---|---|
| `student_reference` | String | Yes | 3–40 characters; alphanumeric, underscore and hyphen |
| `petition_type` | String | Yes | Must be a supported petition category |
| `admission_batch` | String | Yes | 4–20 characters |
| `semester` | Integer | Yes | 1–12 |
| `description` | String | Yes | 10–5000 characters |
| `additional_details` | Object | No | String keys and string, integer, float or boolean values |

### Supported petition categories

- `attendance`
- `re_evaluation`
- `re_registration`
- `medical_leave`
- `grade_grievance`

### Example request

```json
{
  "student_reference": "TEST-STUDENT-001",
  "petition_type": "attendance",
  "admission_batch": "2024",
  "semester": 5,
  "description": "I was unable to meet the required attendance percentage due to medical circumstances.",
  "additional_details": {
    "subject": "Database Management Systems",
    "attendance_percentage": 72.5,
    "medical_document_available": true
  }
}
```

This example uses synthetic student information and is intended for testing only.

## 3. Petition Submission Response

A successfully accepted petition returns HTTP `202 Accepted`.

### Response structure

| Field | Type | Description |
|---|---|---|
| `run_id` | String | Unique identifier for the processing run |
| `status` | String | Initial processing status |
| `message` | String | Submission confirmation |

### Example response

```json
{
  "run_id": "example-run-uuid",
  "status": "queued",
  "message": "Petition accepted for processing."
}
```

The run ID is used to retrieve the processing status and final result.

## 4. Processing Run Contract

**Endpoint:** `GET /api/v1/runs/{run_id}`

### Run status values

| Status | Meaning |
|---|---|
| `queued` | The petition is waiting in the background queue |
| `running` | A worker is processing the petition |
| `completed` | Processing finished and a result was generated |
| `failed` | Processing failed |

### Response fields

| Field | Type | Description |
|---|---|---|
| `run_id` | String | Unique processing run identifier |
| `status` | String | Current run status |
| `result` | Object or null | Eligibility result, when available |
| `error` | String or null | Error information, when applicable |

### Example completed response

```json
{
  "run_id": "example-run-uuid",
  "status": "completed",
  "result": {
    "recommendation": "refer-to-committee",
    "basis": "The available regulatory evidence is insufficient to establish eligibility.",
    "eligibility_position": "Committee review is required.",
    "citations": [],
    "escalation_path": "Appropriate academic committee",
    "human_decision_required": true
  },
  "error": null
}
```

The example illustrates the fail-safe response when regulatory evidence is unavailable. It is not a real university eligibility decision.

## 5. Eligibility Result Contract

The eligibility result is generated after the agent workflow and verification stage.

### Recommendation values

| Value | Meaning |
|---|---|
| `grant-under-provision` | The evidence supports eligibility under an identified provision |
| `refer-to-committee` | Human or committee review is required |
| `reject` | The evidence supports rejection |

### Result fields

| Field | Type | Description |
|---|---|---|
| `recommendation` | String | Final routing recommendation |
| `basis` | String | Explanation supporting the recommendation |
| `eligibility_position` | String | Summary of the petition's eligibility position |
| `citations` | Array | Verified regulatory citations |
| `escalation_path` | String or null | Suggested committee or escalation route |
| `human_decision_required` | Boolean | Indicates whether human review is required |

### Citation contract

Each citation contains:

| Field | Type | Description |
|---|---|---|
| `document_name` | String | Name of the source regulation document |
| `chapter` | String | Chapter reference |
| `clause` | String | Clause or provision reference |
| `page` | Integer or null | Source page number, when available |
| `excerpt` | String | Relevant retrieved text |

Citations must correspond to retrieved evidence. Unsupported or fabricated citations must not be returned as verified evidence.

## 6. Feedback Contract

**Endpoint:** `POST /api/v1/feedback`

Feedback is associated with an existing processing run.

### Request fields

| Field | Type | Description |
|---|---|---|
| `run_id` | String | Identifier of the processing run |
| `rating` | Integer | User feedback rating |
| `comments` | String or null | Optional feedback comments |
| `reviewer_reference` | String or null | Optional synthetic reviewer reference |

### Example request

```json
{
  "run_id": "example-run-uuid",
  "rating": 4,
  "comments": "The explanation was clear, but the supporting provision needs review.",
  "reviewer_reference": "TEST-REVIEWER-001"
}
```

The backend validates the run reference before storing feedback.

## 7. Internal Processing Data

The background worker passes petition and processing information into the LangGraph workflow.

The agent state includes:

- `run_id`
- `petition_id`
- `petition`
- `petition_category`
- `classification_confidence`
- `research_query`
- `retrieved_provisions`
- `research_findings`
- `research_complete`
- `proposed_recommendation`
- `verified_recommendation`
- `evidence_found`
- `verification_passed`
- `verification_findings`
- `verification_complete`
- `verified_citations`
- `routing_recommendation`
- `routing_reason`
- `requires_escalation`
- `current_agent`
- `agent_steps`
- `tool_calls`
- `retry_count`
- `errors`
- `final_result`

The Research Agent produces findings and retrieved evidence. The Verification Agent checks the evidence and proposed claims. The routing node produces the final recommendation.

## 8. Data Validation and Safety Rules

1. Incoming petition payloads must pass Pydantic validation.
2. Unsupported petition categories must be rejected.
3. Suspicious input patterns are checked by the input guardrails.
4. Invalid or quarantined input must not silently enter the agent workflow.
5. Agent execution must respect configured step and tool-call limits.
6. Retrieval results must be checked before they are used as supporting evidence.
7. A recommendation must not be presented as verified when verification fails.
8. Missing regulatory evidence must result in safe escalation.
9. Synthetic test records must be used during development and evaluation.
10. Actual student identifiers and confidential academic records must not be placed in demonstration data.

## 9. Persistence and Identifiers

SQLite stores petition records, processing runs, feedback records and audit events.

ChromaDB stores regulation chunks and associated retrieval metadata.

Redis stores background processing jobs.

Processing run identifiers and petition identifiers are generated independently. The run identifier is exposed through the API for status polling.

## 10. Error Handling

The API uses HTTP error responses for invalid requests, missing runs and unavailable dependencies.

Background processing failures are recorded against the processing run. Failed jobs must not be represented as successfully completed eligibility decisions.

If evidence retrieval or verification is unsuccessful, the system must preserve the failure information and use the fail-safe committee referral behavior where a result can be returned.

## 11. Data Privacy

- Development and load testing use synthetic student references.
- API keys and other secrets are supplied through environment variables.
- The actual `.env` file must not be committed to version control.
- Logs should use correlation and run identifiers rather than exposing unnecessary student information.
- Regulatory documents and petition data should be stored only in their intended application storage locations.