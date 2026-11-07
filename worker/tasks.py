
import asyncio
from typing import Any

from sqlalchemy.orm import Session

from agents.graph import run_agent_graph
from config.logging_config import configure_logging, get_logger
from database.connection import SessionLocal
from database.repository import PetitionRepository
import time

from observability.metrics import record_petition
from observability.tracing import trace_span

configure_logging()
logger = get_logger(__name__)


def _serialise_graph_result(result: dict[str, Any]) -> dict[str, Any]:
    """Convert the graph result into JSON-compatible data."""

    return {
        "run_id": result.get("run_id"),
        "petition_id": result.get("petition_id"),
        "petition_category": result.get("petition_category"),
        "classification_confidence": result.get(
            "classification_confidence"
        ),
        "proposed_recommendation": result.get(
            "proposed_recommendation"
        ),
        "verified_recommendation": result.get(
            "verified_recommendation"
        ),
        "routing_recommendation": result.get(
            "routing_recommendation"
        ),
        "routing_reason": result.get("routing_reason"),
        "verification_passed": result.get(
            "verification_passed", False
        ),
        "requires_escalation": result.get(
            "requires_escalation", True
        ),
        "retrieved_provisions": result.get(
            "retrieved_provisions", []
        ),
        "verified_citations": result.get(
            "verified_citations", []
        ),
        "research_findings": result.get(
            "research_findings", ""
        ),
        "verification_findings": result.get(
            "verification_findings", ""
        ),
        "agent_steps": result.get("agent_steps", 0),
        "tool_calls": result.get("tool_calls", 0),
        "errors": result.get("errors", []),
    }


async def _process_petition_async_impl(
    run_id: str,
    petition_id: str,
) -> dict[str, Any]:
    """Execute the petition through the LangGraph workflow."""

    db: Session = SessionLocal()
    repository = PetitionRepository(db)

    try:
        run = repository.get_run(run_id)

        if run is None:
            raise ValueError(
                f"Processing run not found: {run_id}"
            )

        if run.petition_id != petition_id:
            raise ValueError(
                "The supplied petition ID does not match the run."
            )

        petition_record = run.petition

        if petition_record is None:
            raise ValueError(
                f"Petition not found for run: {run_id}"
            )

        repository.update_run(
            run_id=run_id,
            status="running",
        )

        logger.info(
            "petition_processing_started",
            run_id=run_id,
            petition_id=petition_id,
        )

        petition_data = {
            "student_reference": petition_record.student_reference,
            "petition_type": petition_record.petition_type,
            "admission_batch": petition_record.admission_batch,
            "semester": petition_record.semester,
            "description": petition_record.description,
            "additional_details": (
                petition_record.additional_details or {}
            ),
        }

        initial_state = {
            "run_id": run_id,
            "petition_id": petition_id,
            "petition": petition_data,
        }

        graph_result = await run_agent_graph(initial_state)

        serialised_result = _serialise_graph_result(
            graph_result
        )

        repository.update_run(
            run_id=run_id,
            status="completed",
            result=serialised_result,
        )

        repository.create_audit_event(
            event_type="petition_processing_completed",
            event_data={
                "routing_recommendation": (
                    serialised_result["routing_recommendation"]
                ),
                "requires_escalation": (
                    serialised_result["requires_escalation"]
                ),
            },
            run_id=run_id,
        )

        logger.info(
            "petition_processing_completed",
            run_id=run_id,
            recommendation=serialised_result[
                "routing_recommendation"
            ],
        )

        return serialised_result

    except Exception as exc:
        logger.exception(
            "petition_processing_failed",
            run_id=run_id,
            error=str(exc),
        )

        try:
            repository.update_run(
                run_id=run_id,
                status="failed",
                error=str(exc),
            )

            repository.create_audit_event(
                event_type="petition_processing_failed",
                event_data={"error": str(exc)},
                run_id=run_id,
            )

        except Exception:
            logger.exception(
                "petition_failure_persistence_failed",
                run_id=run_id,
            )

        raise

    finally:
        db.close()

async def _process_petition_async(
    run_id: str,
    petition_id: str,
) -> dict[str, Any]:
    """Execute petition processing with metrics and tracing."""

    start_time = time.perf_counter()
    status = "failed"

    with trace_span(
        "petition.process",
        {
            "petition.run_id": run_id,
            "petition.id": petition_id,
        },
    ) as span:

        try:
            result = await _process_petition_async_impl(
                run_id=run_id,
                petition_id=petition_id,
            )

            status = "completed"
            return result

        finally:
            duration = time.perf_counter() - start_time

            record_petition(
                status=status,
                duration=duration,
            )

            span.set_attribute(
                "petition.processing_status",
                status,
            )

            span.set_attribute(
                "petition.duration_seconds",
                duration,
            )

def process_petition(
    run_id: str,
    petition_id: str,
) -> dict[str, Any]:
    """
    RQ entry point.

    RQ executes this synchronous function in its worker process.
    The function runs the asynchronous LangGraph workflow.
    """

    if not run_id or not petition_id:
        raise ValueError(
            "Both run_id and petition_id are required."
        )

    return asyncio.run(
        _process_petition_async(
            run_id=run_id,
            petition_id=petition_id,
        )
    )
