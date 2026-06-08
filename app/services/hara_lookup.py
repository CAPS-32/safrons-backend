import json
from decimal import Decimal
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models.hara import HaraArea
from app.schemas.hara import HaraFeature

HARA_COLUMNS = """
    id,
    name,
    ph_rata2,
    n_rata2,
    p_rata2,
    k_rata2,
    lithology,
    soil_great,
    slope__,
    ST_AsGeoJSON(geom)::json AS geometry
"""


def row_to_feature(row: Any) -> HaraFeature:
    geometry = row["geometry"]
    if isinstance(geometry, str):
        geometry = json.loads(geometry)

    properties = {
        "id": row["id"],
        "name": row["name"],
        "ph_rata2": numeric_to_float(row["ph_rata2"]),
        "n_rata2": numeric_to_float(row["n_rata2"]),
        "p_rata2": numeric_to_float(row["p_rata2"]),
        "k_rata2": numeric_to_float(row["k_rata2"]),
        "lithology": row["lithology"],
        "soil_great": row["soil_great"],
        "slope__": row["slope__"],
    }
    return HaraFeature(geometry=geometry, properties=properties)


def numeric_to_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    return value


def hara_area_to_feature(area: HaraArea) -> HaraFeature:
    row = {
        "id": area.id,
        "name": area.name,
        "ph_rata2": area.ph_rata2,
        "n_rata2": area.n_rata2,
        "p_rata2": area.p_rata2,
        "k_rata2": area.k_rata2,
        "lithology": area.lithology,
        "soil_great": area.soil_great,
        "slope__": area.slope__,
        "geometry": None,
    }
    return row_to_feature(row)


def get_hara_feature_by_id(db: Session, area_id: int) -> HaraFeature | None:
    if db.get_bind().dialect.name == "sqlite":
        area = db.get(HaraArea, area_id)
        return hara_area_to_feature(area) if area is not None else None

    row = db.execute(
        text(
            f"""
            SELECT {HARA_COLUMNS}
            FROM hara_bogor
            WHERE id = :area_id
            """
        ),
        {"area_id": area_id},
    ).mappings().first()

    return row_to_feature(row) if row is not None else None


def require_hara_feature(db: Session, area_id: int) -> HaraFeature:
    area = get_hara_feature_by_id(db, area_id)
    if area is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hara area not found")
    return area


def find_hara_feature_by_point(db: Session, lon: float, lat: float) -> HaraFeature | None:
    if db.get_bind().dialect.name == "sqlite":
        area = db.scalar(select(HaraArea).order_by(HaraArea.id).limit(1))
        return hara_area_to_feature(area) if area is not None else None

    row = db.execute(
        text(
            f"""
            SELECT {HARA_COLUMNS}
            FROM hara_bogor
            WHERE ST_Contains(geom, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326))
            ORDER BY id
            LIMIT 1
            """
        ),
        {"lon": lon, "lat": lat},
    ).mappings().first()

    return row_to_feature(row) if row is not None else None


def hara_area_exists(db: Session, area_id: int) -> bool:
    if db.get_bind().dialect.name == "sqlite":
        return db.get(HaraArea, area_id) is not None

    exists = db.scalar(text("SELECT 1 FROM hara_bogor WHERE id = :area_id"), {"area_id": area_id})
    return exists is not None

