from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.db.base import Base
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import UserRead, UserRoleUpdate

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


@router.patch("/users/{user_id}/role", response_model=UserRead)
def update_user_role(
    user_id: int,
    payload: UserRoleUpdate,
    _admin_user: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    ensure_admin_tables(db)

    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user.role = payload.role
    db.commit()
    db.refresh(user)
    return user


def ensure_admin_tables(db: Session) -> None:
    Base.metadata.create_all(bind=db.get_bind(), tables=[User.__table__])
