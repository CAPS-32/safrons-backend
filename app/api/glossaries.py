from typing import Annotated
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.base import Base
from app.db.session import get_db
from app.models.glossary import GlossaryTerm
from app.schemas.glossary import GlossaryRead

router = APIRouter(prefix="/api/v1/glossaries", tags=["glossaries"])

def ensure_glossary_tables(db: Session) -> None:
    Base.metadata.create_all(
        bind=db.get_bind(),
        tables=[GlossaryTerm.__table__],
    )
    if db.query(GlossaryTerm).count() == 0:
        seed_terms = [
            GlossaryTerm(
                term="Fosfor",
                definition="Fosfor berperan penting dalam pertumbuhan tanaman, seperti pembentukan sel pada pertumbuhan jaringan akar dan tunas, memperkuat batang, mempercepat pembentukan bunga, serta memperkuat ketahanan tanaman terhadap serangan hama dan penyakit. Tanaman harus memiliki unsur P yang cukup agar pertumbuhannya optimal. Tanaman yang kekurangan unsur P (fosfor) akan mengalami pertumbuhan yang lambat, lemah dan kerdil, berwarna hijau gelap, proses pematangan buah dan biji lambat, serta jumlah buah yang dihasilkan sedikit."
            ),
            GlossaryTerm(
                term="Hara",
                definition="Hara merupakan zat yang dibutuhkan oleh organisme untuk dapat hidup, tumbuh, dan berkembang. Pada tanaman, ketersediaan unsur hara mempengaruhi pertumbuhan dan perkembangan tanaman. Kekurangan unsur hara dan ketidakseimbangan kandungan unsur hara dalam tanaman dapat menyebabkan pertumbuhan tanaman tidak optimal."
            ),
            GlossaryTerm(
                term="Kalium",
                definition="Unsur kalium diperlukan tanaman untuk mengatur keseimbangan garam, air, dan tekanan osmotik sel tanaman, meningkatkan ketahanan tanaman terhadap penyakit, merangsang perkembangan akar, serta memperkuat tanaman. Kekurangan unsur K akan menyebabkan terhambatnya proses fotosintesis dan meningkatkan respirasi, daun tua mengerut tidak merata, timbul bercak berwarna coklat, mengering lalu mati."
            ),
            GlossaryTerm(
                term="Nitrogen",
                definition="Nitrogen dibutuhkan tanaman untuk merangsang pertumbuhan, terutama pada batang dan daun. Nitrogen berperan dalam pertumbuhan hijau daun (klorofil), protein, lemak, dan senyawa organik lainnya. Tanaman yang kekurangan unsur N dapat terhambat pertumbuhannya, daunnya menjadi kuning, pertumbuhan lambat."
            ),
            GlossaryTerm(
                term="pH",
                definition="pH merupakan tingkat keasaman suatu zat. Pada tanaman, pH tanah mempengaruhi ketersediaan fosfor dalam tanah. pH tanah yang terlalu tinggi (basa) atau terlalu rendah (asam) menyebabkan unsur fosfor tidak dapat bekerja dengan baik dalam menutrisi tanah."
            )
        ]
        db.add_all(seed_terms)
        db.commit()

@router.get("", response_model=list[GlossaryRead])
def list_glossaries(db: Annotated[Session, Depends(get_db)]) -> list[GlossaryTerm]:
    return list(
        db.scalars(
            select(GlossaryTerm).order_by(GlossaryTerm.term.asc())
        ).all()
    )

