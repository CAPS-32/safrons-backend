from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.hara import HARA_COLUMNS, row_to_feature
from app.db.base import Base
from app.db.session import get_db
from app.models.hara import HaraArea
from app.models.saved_region import SavedRegion
from app.models.user import User
from app.schemas.hara import HaraFeature
from app.schemas.saved_region import SavedRegionCreate, SavedRegionRead, SavedRegionUpdate
from app.schemas.saved_region import selected_point as selected_point_schema

router = APIRouter(prefix="/api/v1/saved-regions", tags=["saved-regions"])


@router.post("", response_model=SavedRegionRead, status_code=status.HTTP_201_CREATED)
def create_saved_region(
    payload: SavedRegionCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> SavedRegionRead:
    ensure_saved_region_tables(db)

    area = find_hara_feature_by_point(db, payload.lon, payload.lat)
    if area is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No hara area found")

    saved_region = SavedRegion(
        user_id=current_user.id,
        hara_area_id=area.properties.id,
        selected_lon=payload.lon,
        selected_lat=payload.lat,
        label=payload.label,
    )
    db.add(saved_region)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Region already saved for this selected point",
        ) from exc

    db.refresh(saved_region)
    return saved_region_to_read(saved_region, area)


@router.get("", response_model=list[SavedRegionRead])
def list_saved_regions(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[SavedRegionRead]:
    ensure_saved_region_tables(db)

    saved_regions = db.scalars(
        select(SavedRegion)
        .where(SavedRegion.user_id == current_user.id)
        .order_by(SavedRegion.created_at.desc(), SavedRegion.id.desc())
    ).all()

    return [
        saved_region_to_read(saved_region, require_hara_feature(db, saved_region.hara_area_id))
        for saved_region in saved_regions
    ]


@router.get("/{saved_region_id}", response_model=SavedRegionRead)
def get_saved_region(
    saved_region_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> SavedRegionRead:
    saved_region = get_owned_saved_region(db, current_user.id, saved_region_id)
    return saved_region_to_read(saved_region, require_hara_feature(db, saved_region.hara_area_id))


@router.patch("/{saved_region_id}", response_model=SavedRegionRead)
def update_saved_region(
    saved_region_id: int,
    payload: SavedRegionUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> SavedRegionRead:
    saved_region = get_owned_saved_region(db, current_user.id, saved_region_id)
    saved_region.label = payload.label
    db.commit()
    db.refresh(saved_region)
    return saved_region_to_read(saved_region, require_hara_feature(db, saved_region.hara_area_id))


@router.delete("/{saved_region_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_saved_region(
    saved_region_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    saved_region = get_owned_saved_region(db, current_user.id, saved_region_id)
    db.delete(saved_region)
    db.commit()


def get_owned_saved_region(db: Session, user_id: int, saved_region_id: int) -> SavedRegion:
    saved_region = db.scalar(
        select(SavedRegion).where(
            SavedRegion.id == saved_region_id,
            SavedRegion.user_id == user_id,
        )
    )
    if saved_region is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Saved region not found")
    return saved_region


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


def require_hara_feature(db: Session, area_id: int) -> HaraFeature:
    area = get_hara_feature_by_id(db, area_id)
    if area is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hara area not found")
    return area


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


def hara_area_to_feature(area: HaraArea) -> HaraFeature:
    row = {
        "id": area.id,
        "name": area.name,
        "ph_rata2": area.ph_rata2,
        "n_rata2": area.n_rata2,
        "p_rata2": area.p_rata2,
        "k_rata2": area.k_rata2,
        "slope__": area.slope__,
        "texture_of": area.texture_of,
        "geometry": None,
    }
    return row_to_feature(row)


def saved_region_to_read(saved_region: SavedRegion, area: HaraFeature) -> SavedRegionRead:
    return SavedRegionRead(
        id=saved_region.id,
        hara_area_id=saved_region.hara_area_id,
        selected_point=selected_point_schema(saved_region.selected_lon, saved_region.selected_lat),
        label=saved_region.label,
        area=area,
        created_at=saved_region.created_at,
        updated_at=saved_region.updated_at,
    )


def ensure_saved_region_tables(db: Session) -> None:
    Base.metadata.create_all(bind=db.get_bind(), tables=[User.__table__, SavedRegion.__table__])
