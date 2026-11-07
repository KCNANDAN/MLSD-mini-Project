
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RunStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class RoutingRecommendation(str, Enum):
    GRANT = "grant-under-provision"
    REFER = "refer-to-committee"
    REJECT = "reject"


class Citation(BaseModel):
    """
    A citation must identify a provision in retrieved corpus text.
    """

    model_config = ConfigDict(extra="forbid")

    document_name: str

    chapter: str

    clause: str

    page: int | None = Field(default=None, ge=1)

    excerpt: str = Field(min_length=1)


class EligibilityResult(BaseModel):
    """
    Evidence-backed eligibility position.

    This is a recommendation, not a final academic decision.
    """

    model_config = ConfigDict(extra="forbid")

    recommendation: RoutingRecommendation

    basis: str

    eligibility_position: str

    citations: list[Citation] = Field(default_factory=list)

    escalation_path: str | None = None

    human_decision_required: bool = True


class RunResponse(BaseModel):
    """
    Complete response for an asynchronous petition run.
    """

    run_id: str

    status: RunStatus

    result: EligibilityResult | None = None

    error: str | None = None


class HealthResponse(BaseModel):
    status: str = "ok"

    service: str = "academic-petition-triage"


class APIError(BaseModel):
    detail: str

    error_code: str | None = None


class PaginatedResponse(BaseModel):
    items: list[dict[str, Any]]

    total: int = Field(ge=0)
