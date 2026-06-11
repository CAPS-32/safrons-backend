from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.api.deps import require_expert
from app.db.base import Base
from app.db.session import get_db
from app.models.glossary import GlossaryTerm
from app.models.user import User
from app.schemas.glossary import GlossaryCreate, GlossaryUpdate, GlossaryRead
from app.api.glossaries import ensure_glossary_tables

router = APIRouter(prefix="/api/v1/expert/glossaries", tags=["expert_glossaries"])

@router.post("", response_model=GlossaryRead, status_code=status.HTTP_201_CREATED)
def create_glossary(
    payload: GlossaryCreate,
    expert_user: Annotated[User, Depends(require_expert)],
    db: Annotated[Session, Depends(get_db)],
) -> GlossaryTerm:
    ensure_glossary_tables(db)
    
    # Check if term already exists
    existing = db.scalars(
        select(GlossaryTerm).where(GlossaryTerm.term == payload.term)
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Glossary term already exists",
        )

    term = GlossaryTerm(
        term=payload.term,
        definition=payload.definition,
    )
    db.add(term)
    db.commit()
    db.refresh(term)
    return term

@router.put("/{term_id}", response_model=GlossaryRead)
def update_glossary(
    term_id: int,
    payload: GlossaryUpdate,
    expert_user: Annotated[User, Depends(require_expert)],
    db: Annotated[Session, Depends(get_db)],
) -> GlossaryTerm:
    ensure_glossary_tables(db)

    term = db.get(GlossaryTerm, term_id)
    if term is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Glossary term not found",
        )

    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No changes provided",
        )

    if "term" in changes:
        # Check if another term with the same name exists
        existing = db.scalars(
            select(GlossaryTerm).where(GlossaryTerm.term == changes["term"], GlossaryTerm.id != term_id)
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Glossary term with this name already exists",
            )

    for field, value in changes.items():
        setattr(term, field, value)

    db.commit()
    db.refresh(term)
    return term

@router.delete("/{term_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_glossary(
    term_id: int,
    expert_user: Annotated[User, Depends(require_expert)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    ensure_glossary_tables(db)

    term = db.get(GlossaryTerm, term_id)
    if term is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Glossary term not found",
        )

    db.delete(term)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
