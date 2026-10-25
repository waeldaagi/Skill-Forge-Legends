from typing import Literal

from pydantic import BaseModel, Field


class ModerationOutput(BaseModel):
    label: Literal["OK", "SPAM", "TOXIQUE", "HORS_SUJET"]
    confidence: float = Field(ge=0, le=1)
    reason: str = Field(min_length=1, max_length=500)
