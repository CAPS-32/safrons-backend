import json
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.deps import require_expert
from app.db.base import Base
from app.db.session import get_db
from app.models.hara import HaraArea
from app.models.hara_advisory import HaraAdvisory
from app.models.hara_area_change import HaraAreaChange
from app.models.user import User
from app.schemas.advisory import AdvisoryCreate, AdvisoryRead, AdvisoryUpdate
from app.schemas.hara import HaraAreaCreate, HaraAreaUpdate, HaraFeature
from app.services.hara_lookup import get_hara_feature_by_id, hara_area_to_feature, require_hara_feature

router = APIRouter(prefix="/api/v1/expert", tags=["expert"])


@router.post(
    "/hara/areas/{area_id}/advisories",
    response_model=AdvisoryRead,
    status_code=status.HTTP_201_CREATED,
)
def create_hara_advisory(
    area_id: int,
    payload: AdvisoryCreate,
    expert_user: Annotated[User, Depends(require_expert)],
    db: Annotated[Session, Depends(get_db)],
) -> HaraAdvisory:
    ensure_expert_tables(db)
    require_hara_feature(db, area_id)

    advisory = HaraAdvisory(
        hara_area_id=area_id,
        title=payload.title,
        content=payload.content,
        category=payload.category,
        is_active=payload.is_active,
        created_by_user_id=expert_user.id,
    )
    db.add(advisory)
    db.commit()
    db.refresh(advisory)
    return advisory


@router.patch("/advisories/{advisory_id}", response_model=AdvisoryRead)
def update_hara_advisory(
    advisory_id: int,
    payload: AdvisoryUpdate,
    expert_user: Annotated[User, Depends(require_expert)],
    db: Annotated[Session, Depends(get_db)],
) -> HaraAdvisory:
    ensure_expert_tables(db)

    advisory = db.get(HaraAdvisory, advisory_id)
    if advisory is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Advisory not found")

    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No advisory fields provided",
        )

    for field, value in changes.items():
        setattr(advisory, field, value)
    advisory.updated_by_user_id = expert_user.id

    db.commit()
    db.refresh(advisory)
    return advisory


@router.patch("/hara/areas/{area_id}", response_model=HaraFeature)
def update_hara_area(
    area_id: int,
    payload: HaraAreaUpdate,
    expert_user: Annotated[User, Depends(require_expert)],
    db: Annotated[Session, Depends(get_db)],
) -> HaraFeature:
    ensure_expert_tables(db)

    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No hara fields provided",
        )

    if db.get_bind().dialect.name == "sqlite":
        area = db.get(HaraArea, area_id)
        if area is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hara area not found")
        for field, value in changes.items():
            setattr(area, field, value)
        add_hara_change(db, area_id, expert_user.id, "update", changes)
        db.commit()
        db.refresh(area)
        return hara_area_to_feature(area)

    if get_hara_feature_by_id(db, area_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hara area not found")

    assignments = ", ".join(f"{field} = :{field}" for field in changes)
    db.execute(
        text(f"UPDATE hara_bogor SET {assignments} WHERE id = :area_id"),
        {**changes, "area_id": area_id},
    )
    add_hara_change(db, area_id, expert_user.id, "update", changes)
    db.commit()
    return require_hara_feature(db, area_id)


@router.post("/hara/areas", response_model=HaraFeature, status_code=status.HTTP_201_CREATED)
def create_hara_area(
    payload: HaraAreaCreate,
    expert_user: Annotated[User, Depends(require_expert)],
    db: Annotated[Session, Depends(get_db)],
) -> HaraFeature:
    ensure_expert_tables(db)

    properties = payload.properties.model_dump()
    if db.get_bind().dialect.name == "sqlite":
        area = HaraArea(**properties)
        db.add(area)
        db.flush()
        add_hara_change(
            db,
            area.id,
            expert_user.id,
            "create",
            {"geometry_type": payload.geometry["type"], **properties},
        )
        db.commit()
        db.refresh(area)
        return hara_area_to_feature(area)

    params = {
        **properties,
        "geometry": json.dumps(payload.geometry, separators=(",", ":")),
    }
    try:
        area_id = db.scalar(
            text(
                """
                INSERT INTO hara_bogor (
                    geom,
                    name,
                    ph_rata2,
                    n_rata2,
                    p_rata2,
                    k_rata2,
                    slope__,
                    texture_of
                )
                SELECT
                    ST_SetSRID(ST_Multi(ST_GeomFromGeoJSON(:geometry)), 4326),
                    :name,
                    :ph_rata2,
                    :n_rata2,
                    :p_rata2,
                    :k_rata2,
                    :slope__,
                    :texture_of
                WHERE ST_IsValid(ST_SetSRID(ST_Multi(ST_GeomFromGeoJSON(:geometry)), 4326))
                RETURNING id
                """
            ),
            params,
        )
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid hara geometry",
        ) from exc

    if area_id is None:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid hara geometry",
        )

    add_hara_change(
        db,
        area_id,
        expert_user.id,
        "create",
        {"geometry_type": payload.geometry["type"], **properties},
    )
    db.commit()
    return require_hara_feature(db, area_id)


def add_hara_change(
    db: Session,
    area_id: int,
    user_id: int,
    action: str,
    changed_fields: dict[str, Any],
) -> None:
    db.add(
        HaraAreaChange(
            hara_area_id=area_id,
            user_id=user_id,
            action=action,
            changed_fields=changed_fields,
        )
    )


def ensure_expert_tables(db: Session) -> None:
    Base.metadata.create_all(
        bind=db.get_bind(),
        tables=[
            User.__table__,
            HaraArea.__table__,
            HaraAdvisory.__table__,
            HaraAreaChange.__table__,
        ],
    )
