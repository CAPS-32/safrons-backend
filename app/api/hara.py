import json
from decimal import Decimal
from typing import Any, Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.session import get_db
from app.models.hara import HaraArea
from app.models.hara_advisory import HaraAdvisory
from app.models.user import User
from app.schemas.advisory import AdvisoryRead
from app.schemas.hara import HaraFeature, HaraFeatureCollection

router = APIRouter(prefix="/api/v1/hara", tags=["hara"])

HARA_COLUMNS = """
    id,
    name,
    ph_rata2,
    n_rata2,
    p_rata2,
    k_rata2,
    slope__,
    texture_of,
    ST_AsGeoJSON(geom)::json AS geometry
"""


@router.get("/areas", response_model=HaraFeatureCollection)
def list_hara_areas(db: Annotated[Session, Depends(get_db)]) -> HaraFeatureCollection:
    rows = db.execute(
        text(
            f"""
            SELECT {HARA_COLUMNS}
            FROM hara_bogor
            ORDER BY id
            """
        )
    ).mappings()

    return HaraFeatureCollection(features=[row_to_feature(row) for row in rows])


@router.get("/areas/{area_id}", response_model=HaraFeature)
def get_hara_area(area_id: int, db: Annotated[Session, Depends(get_db)]) -> HaraFeature:
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

    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hara area not found")
    return row_to_feature(row)


@router.get("/areas/{area_id}/advisories", response_model=list[AdvisoryRead])
def list_hara_area_advisories(
    area_id: int,
    db: Annotated[Session, Depends(get_db)],
) -> list[HaraAdvisory]:
    ensure_hara_advisory_tables(db)
    if not hara_area_exists(db, area_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hara area not found")

    return list(
        db.scalars(
            select(HaraAdvisory)
            .where(HaraAdvisory.hara_area_id == area_id, HaraAdvisory.is_active.is_(True))
            .order_by(HaraAdvisory.created_at.desc(), HaraAdvisory.id.desc())
        ).all()
    )


@router.get("/point", response_model=HaraFeature)
def get_hara_area_by_point(
    db: Annotated[Session, Depends(get_db)],
    lon: float = Query(ge=-180, le=180),
    lat: float = Query(ge=-90, le=90),
) -> HaraFeature:
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

    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No hara area found")
    return row_to_feature(row)


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
        "slope__": row["slope__"],
        "texture_of": row["texture_of"],
    }
    return HaraFeature(geometry=geometry, properties=properties)


def numeric_to_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    return value


def hara_area_exists(db: Session, area_id: int) -> bool:
    if db.get_bind().dialect.name == "sqlite":
        return db.get(HaraArea, area_id) is not None

    exists = db.scalar(text("SELECT 1 FROM hara_bogor WHERE id = :area_id"), {"area_id": area_id})
    return exists is not None


def ensure_hara_advisory_tables(db: Session) -> None:
    Base.metadata.create_all(
        bind=db.get_bind(),
        tables=[User.__table__, HaraArea.__table__, HaraAdvisory.__table__],
    )
