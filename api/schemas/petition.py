
from enum import Enum
from typing import Annotated

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
)


class PetitionType(str, Enum):
    ATTENDANCE = "attendance"
    RE_EVALUATION = "re_evaluation"
    RE_REGISTRATION = "re_registration"
    MEDICAL_LEAVE = "medical_leave"
    GRADE_GRIEVANCE = "grade_grievance"


StudentReference = Annotated[
    str,
    StringConstraints(
        min_length=3,
        max_length=40,
        pattern=r"^[A-Za-z0-9_-]+$",
    ),
]

AdmissionBatch = Annotated[
    str,
    StringConstraints(
        min_length=4,
        max_length=20,
    ),
]

PetitionDescription = Annotated[
    str,
    StringConstraints(
        min_length=10,
        max_length=5000,
        strip_whitespace=True,
    ),
]


class PetitionCreate(BaseModel):
    """
    Public request contract for submitting a student petition.

    Only synthetic student references and petition information
    should be submitted.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    student_reference: StudentReference

    petition_type: PetitionType

    admission_batch: AdmissionBatch

    semester: int = Field(
        ge=1,
        le=12,
        description="Academic semester number.",
    )

    description: PetitionDescription

    additional_details: dict[
        str,
        str | int | float | bool
    ] = Field(default_factory=dict)


class PetitionAccepted(BaseModel):
    """
    Response returned immediately after petition submission.
    """

    run_id: str

    status: str = "queued"

    message: str = (
        "Petition accepted for asynchronous processing."
    )
