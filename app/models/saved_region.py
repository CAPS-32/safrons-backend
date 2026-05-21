from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.hara import HaraArea
from app.models.user import User


class SavedRegion(Base):
    __tablename__ = "saved_regions"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "hara_area_id",
            "selected_lon",
            "selected_lat",
            name="uq_saved_regions_user_area_point",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    hara_area_id: Mapped[int] = mapped_column(
        ForeignKey("hara_bogor.id", ondelete="RESTRICT"),
        nullable=False,
    )
    selected_lon: Mapped[float] = mapped_column(Float, nullable=False)
    selected_lat: Mapped[float] = mapped_column(Float, nullable=False)
    label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    area: Mapped[HaraArea] = relationship(HaraArea)
    user: Mapped[User] = relationship(User)
