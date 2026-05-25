from decimal import Decimal

from sqlalchemy import Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class HaraArea(Base):
    __tablename__ = "hara_bogor"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str | None] = mapped_column(String(32), nullable=True)
    ph_rata2: Mapped[Decimal | None] = mapped_column(Numeric(18, 11), nullable=True)
    n_rata2: Mapped[Decimal | None] = mapped_column(Numeric(18, 11), nullable=True)
    p_rata2: Mapped[Decimal | None] = mapped_column(Numeric(18, 11), nullable=True)
    k_rata2: Mapped[Decimal | None] = mapped_column(Numeric(18, 11), nullable=True)
    lithology: Mapped[str | None] = mapped_column(String(128), nullable=True)
    soil_great: Mapped[str | None] = mapped_column(String(64), nullable=True)
    slope__: Mapped[str | None] = mapped_column(String(16), nullable=True)
    texture_of: Mapped[str | None] = mapped_column(String(255), nullable=True)
