from pydantic import BaseModel, Field, field_validator


class CriterionScore(BaseModel):
    name: str = Field(min_length=1)
    score: int = Field(ge=0, le=100)
    justification: str = Field(min_length=3)


class AssessmentOutput(BaseModel):
    total_score: int = Field(ge=0, le=100)
    criteria: list[CriterionScore]
    strengths: list[str]
    improvement_axes: list[str]
    confidence: float = Field(ge=0, le=1)
    suspected_fraud: bool
    fraud_reasons: list[str] = Field(default_factory=list)

    @field_validator("criteria")
    @classmethod
    def at_least_one_criterion(cls, value):
        if not value:
            raise ValueError("Au moins un critère est requis.")
        return value
