"""
Integration tests for the crop suitability / diagnosis endpoint.
"""
from collections.abc import Callable, Generator
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.hara import HaraArea


@pytest.fixture()
def client_with_db() -> Generator[tuple[TestClient, Callable[[], Session]], None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    with testing_session_local() as db:
        db.add(
            HaraArea(
                id=1,
                name="Air Hitam Kanan",
                ph_rata2=Decimal("5.016667"),
                n_rata2=Decimal("4.565255"),
                p_rata2=Decimal("8.626031"),
                k_rata2=Decimal("126.83385"),
                slope__="41-60",
                texture_of="Fine grained tephra shale",
            )
        )
        db.commit()

    def override_get_db() -> Generator[Session, None, None]:
        db = testing_session_local()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app), testing_session_local
    app.dependency_overrides.clear()


def test_get_diagnosis_returns_crop_suitability_array(
    client_with_db: tuple[TestClient, Callable[[], Session]],
) -> None:
    """
    Verify that the GET /api/v1/hara/areas/{id}/diagnosis endpoint returns a 200 OK
    and includes the 'crop_suitabilities' array with elements containing suitability classes.
    """
    client, _ = client_with_db

    response = client.get("/api/v1/hara/areas/1/diagnosis")
    assert response.status_code == 200
    
    data = response.json()
    assert "crop_suitabilities" in data
    
    crop_suitabilities = data["crop_suitabilities"]
    assert isinstance(crop_suitabilities, list)
    assert len(crop_suitabilities) == 3  # Maize, Peanut, Cocoa
    
    crops = [c["crop"] for c in crop_suitabilities]
    assert "jagung" in crops
    assert "kacang_tanah" in crops
    assert "kakao" in crops

    for cs in crop_suitabilities:
        assert "class" in cs
        assert cs["class"] in ("S1", "S2", "S3", "N")
        assert "limiting_factors" in cs
        assert isinstance(cs["limiting_factors"], list)
