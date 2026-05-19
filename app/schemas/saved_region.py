from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.hara import HaraFeature


class SavedRegionCreate(BaseModel):
    lon: float = Field(ge=-180, le=180)
    lat: float = Field(ge=-90, le=90)
    label: str | None = Field(default=None, max_length=255)

    @field_validator("label")
    @classmethod
    def normalize_label(cls, value: str | None) -> str | None:
        if value is None:
            return None
        label = value.strip()
        return label or None


class SavedRegionUpdate(BaseModel):
    label: str | None = Field(default=None, max_length=255)

    @field_validator("label")
    @classmethod
    def normalize_label(cls, value: str | None) -> str | None:
        if value is None:
            return None
        label = value.strip()
        return label or None


class SavedRegionPoint(BaseModel):
    type: Literal["Point"] = "Point"
    coordinates: tuple[float, float]


class SavedRegionRead(BaseModel):
    id: int
    hara_area_id: int
    selected_point: SavedRegionPoint
    label: str | None
    area: HaraFeature
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


def selected_point(lon: float, lat: float) -> dict[str, Any]:
    return {"type": "Point", "coordinates": (lon, lat)}
