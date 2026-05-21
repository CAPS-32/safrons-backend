from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.hara import HaraArea
from app.models.user import User


class HaraAreaChange(Base):
    __tablename__ = "hara_area_changes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    hara_area_id: Mapped[int] = mapped_column(
        ForeignKey("hara_bogor.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    changed_fields: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    area: Mapped[HaraArea] = relationship(HaraArea)
    user: Mapped[User] = relationship(User)
