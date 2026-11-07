
from pydantic import BaseModel, ConfigDict, Field


class FeedbackCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str = Field(
        min_length=1,
        max_length=100,
    )

    satisfactory: bool

    reason: str = Field(
        min_length=3,
        max_length=1000,
    )


class FeedbackResponse(BaseModel):
    feedback_id: str

    run_id: str

    message: str = "Feedback recorded successfully."
