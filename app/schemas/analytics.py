from pydantic import BaseModel

class Averages(BaseModel):
    ph: float
    n: float
    p: float
    k: float

class PhDistribution(BaseModel):
    sangat_masam: int
    masam: int
    sedikit_masam: int
    netral: int
    sedikit_alkalis: int
    alkalis: int

class CriticalArea(BaseModel):
    id: int
    name: str
    value: float
    parameter: str

class MacroAnalyticsRead(BaseModel):
    averages: Averages
    ph_distribution: PhDistribution
    critical_areas: list[CriticalArea]
