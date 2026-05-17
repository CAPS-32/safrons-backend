from typing import Any, Literal

from pydantic import BaseModel, Field


class HaraProperties(BaseModel):
    id: int
    name: str | None
    ph_rata2: float | None
    n_rata2: float | None
    p_rata2: float | None
    k_rata2: float | None
    lithology: str | None
    soil_great: str | None
    slope__: str | None = Field(alias="slope__")

    model_config = {"populate_by_name": True}


class HaraFeature(BaseModel):
    type: Literal["Feature"] = "Feature"
    geometry: dict[str, Any] | None
    properties: HaraProperties


class HaraFeatureCollection(BaseModel):
    type: Literal["FeatureCollection"] = "FeatureCollection"
    features: list[HaraFeature]
