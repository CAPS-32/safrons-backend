from typing import Literal

from pydantic import BaseModel

from app.schemas.hara import HaraFeature

DiagnosisStatus = Literal["ready", "insufficient_data"]
FactorSeverity = Literal["info", "watch", "attention", "critical"]


class DiagnosisFactor(BaseModel):
    key: str
    label: str
    value: float | str | None
    status: str
    status_label: str
    severity: FactorSeverity
    message: str


class DiagnosisRecommendation(BaseModel):
    priority: int
    category: str
    title: str
    action: str
    reason: str


class HaraDiagnosisRead(BaseModel):
    rule_set_version: str
    status: DiagnosisStatus
    summary: str
    area: HaraFeature
    factors: list[DiagnosisFactor]
    recommendations: list[DiagnosisRecommendation]

