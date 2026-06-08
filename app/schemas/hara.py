from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class HaraProperties(BaseModel):
    id: int
    name: str | None
    ph_rata2: float | None
    n_rata2: float | None
    p_rata2: float | None
    k_rata2: float | None
    slope__: str | None = Field(alias="slope__")
    texture_of: str | None = Field(default=None)

    model_config = {"populate_by_name": True}


class HaraFeature(BaseModel):
    type: Literal["Feature"] = "Feature"
    geometry: dict[str, Any] | None
    properties: HaraProperties


class HaraFeatureCollection(BaseModel):
    type: Literal["FeatureCollection"] = "FeatureCollection"
    features: list[HaraFeature]


class HaraPropertiesWrite(BaseModel):
    name: str | None = Field(default=None, max_length=32)
    ph_rata2: float | None = Field(default=None, ge=0, le=14)
    n_rata2: float | None = Field(default=None, ge=0)
    p_rata2: float | None = Field(default=None, ge=0)
    k_rata2: float | None = Field(default=None, ge=0)
    slope__: str | None = Field(default=None, max_length=16)
    texture_of: str | None = Field(default=None, max_length=255)

    @field_validator("name", "slope__", "texture_of")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class HaraAreaUpdate(HaraPropertiesWrite):
    pass


class HaraAreaCreate(BaseModel):
    geometry: dict[str, Any]
    properties: HaraPropertiesWrite

    @field_validator("geometry")
    @classmethod
    def validate_geojson_geometry(cls, value: dict[str, Any]) -> dict[str, Any]:
        geometry_type = value.get("type")
        coordinates = value.get("coordinates")
        if geometry_type not in {"Polygon", "MultiPolygon"}:
            raise ValueError("geometry type must be Polygon or MultiPolygon")
        if not isinstance(coordinates, list) or not coordinates:
            raise ValueError("geometry coordinates are required")
        return value
