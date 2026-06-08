from collections.abc import Callable, Generator
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, delete
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


def auth_headers(client: TestClient, email: str = "user@example.com") -> dict[str, str]:
    password = "strong-password"
    client.post("/api/v1/auth/register", json={"email": email, "password": password})
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    return {"Authorization": f"Bearer {login_response.json()['access_token']}"}


def test_saved_region_requires_token(client_with_db: tuple[TestClient, Callable[[], Session]]) -> None:
    client, _ = client_with_db

    response = client.post(
        "/api/v1/saved-regions",
        json={"lon": 106.8, "lat": -6.6},
    )

    assert response.status_code == 401


def test_create_saved_region_resolves_area_from_point(
    client_with_db: tuple[TestClient, Callable[[], Session]],
) -> None:
    client, _ = client_with_db
    headers = auth_headers(client)

    response = client.post(
        "/api/v1/saved-regions",
        json={"lon": 106.8, "lat": -6.6, "label": "Farm plot"},
        headers=headers,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["hara_area_id"] == 1
    assert body["selected_point"] == {"type": "Point", "coordinates": [106.8, -6.6]}
    assert body["label"] == "Farm plot"
    assert body["area"]["properties"]["name"] == "Air Hitam Kanan"


def test_create_saved_region_returns_404_when_no_area_contains_point(
    client_with_db: tuple[TestClient, Callable[[], Session]],
) -> None:
    client, session_local = client_with_db
    headers = auth_headers(client)
    with session_local() as db:
        db.execute(delete(HaraArea))
        db.commit()

    response = client.post(
        "/api/v1/saved-regions",
        json={"lon": 106.8, "lat": -6.6},
        headers=headers,
    )

    assert response.status_code == 404


def test_duplicate_saved_region_returns_conflict(
    client_with_db: tuple[TestClient, Callable[[], Session]],
) -> None:
    client, _ = client_with_db
    headers = auth_headers(client)
    payload = {"lon": 106.8, "lat": -6.6}

    assert client.post("/api/v1/saved-regions", json=payload, headers=headers).status_code == 201
    response = client.post("/api/v1/saved-regions", json=payload, headers=headers)

    assert response.status_code == 409


def test_saved_regions_are_scoped_to_current_user(
    client_with_db: tuple[TestClient, Callable[[], Session]],
) -> None:
    client, _ = client_with_db
    owner_headers = auth_headers(client, "owner@example.com")
    other_headers = auth_headers(client, "other@example.com")

    create_response = client.post(
        "/api/v1/saved-regions",
        json={"lon": 106.8, "lat": -6.6},
        headers=owner_headers,
    )
    saved_region_id = create_response.json()["id"]

    list_response = client.get("/api/v1/saved-regions", headers=other_headers)
    get_response = client.get(f"/api/v1/saved-regions/{saved_region_id}", headers=other_headers)
    patch_response = client.patch(
        f"/api/v1/saved-regions/{saved_region_id}",
        json={"label": "Other label"},
        headers=other_headers,
    )
    delete_response = client.delete(
        f"/api/v1/saved-regions/{saved_region_id}",
        headers=other_headers,
    )

    assert list_response.status_code == 200
    assert list_response.json() == []
    assert get_response.status_code == 404
    assert patch_response.status_code == 404
    assert delete_response.status_code == 404


def test_update_and_delete_saved_region(
    client_with_db: tuple[TestClient, Callable[[], Session]],
) -> None:
    client, _ = client_with_db
    headers = auth_headers(client)

    create_response = client.post(
        "/api/v1/saved-regions",
        json={"lon": 106.8, "lat": -6.6},
        headers=headers,
    )
    saved_region_id = create_response.json()["id"]

    patch_response = client.patch(
        f"/api/v1/saved-regions/{saved_region_id}",
        json={"label": "Updated label"},
        headers=headers,
    )
    delete_response = client.delete(f"/api/v1/saved-regions/{saved_region_id}", headers=headers)
    get_response = client.get(f"/api/v1/saved-regions/{saved_region_id}", headers=headers)

    assert patch_response.status_code == 200
    assert patch_response.json()["label"] == "Updated label"
    assert delete_response.status_code == 204
    assert get_response.status_code == 404
