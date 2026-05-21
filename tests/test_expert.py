from collections.abc import Callable, Generator
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.hara import HaraArea
from app.models.hara_area_change import HaraAreaChange
from app.models.user import User


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
                lithology="Fine grained tephra shale",
                soil_great="Dystropepts",
                slope__="41-60",
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


def auth_headers(client: TestClient, email: str, role: str | None = None) -> dict[str, str]:
    password = "strong-password"
    client.post("/api/v1/auth/register", json={"email": email, "password": password})
    if role is not None:
        promote_user_in_test_db(email, role)
    login_response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return {"Authorization": f"Bearer {login_response.json()['access_token']}"}


def promote_user_in_test_db(email: str, role: str) -> None:
    db_override = app.dependency_overrides[get_db]
    db = next(db_override())
    try:
        user = db.scalar(select(User).where(User.email == email))
        assert user is not None
        user.role = role
        db.commit()
    finally:
        db.close()


def test_register_creates_normal_user(
    client_with_db: tuple[TestClient, Callable[[], Session]],
) -> None:
    client, _ = client_with_db

    response = client.post(
        "/api/v1/auth/register",
        json={"email": "user@example.com", "password": "strong-password"},
    )

    assert response.status_code == 201
    assert response.json()["role"] == "user"


def test_normal_user_cannot_access_expert_endpoint(
    client_with_db: tuple[TestClient, Callable[[], Session]],
) -> None:
    client, _ = client_with_db
    headers = auth_headers(client, "user@example.com")

    response = client.patch(
        "/api/v1/expert/hara/areas/1",
        json={"ph_rata2": 6.1},
        headers=headers,
    )

    assert response.status_code == 403


def test_admin_can_promote_user_to_expert(
    client_with_db: tuple[TestClient, Callable[[], Session]],
) -> None:
    client, _ = client_with_db
    auth_headers(client, "target@example.com")
    admin_headers = auth_headers(client, "admin@example.com", "admin")

    response = client.patch(
        "/api/v1/admin/users/1/role",
        json={"role": "expert"},
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert response.json()["role"] == "expert"


def test_expert_can_create_and_patch_advisory_visible_to_users(
    client_with_db: tuple[TestClient, Callable[[], Session]],
) -> None:
    client, _ = client_with_db
    expert_headers = auth_headers(client, "expert@example.com", "expert")

    create_response = client.post(
        "/api/v1/expert/hara/areas/1/advisories",
        json={
            "title": "Improve soil acidity",
            "content": "Apply dolomite based on field measurement.",
            "category": "soil",
        },
        headers=expert_headers,
    )
    advisory_id = create_response.json()["id"]

    patch_response = client.patch(
        f"/api/v1/expert/advisories/{advisory_id}",
        json={"title": "Correct soil acidity"},
        headers=expert_headers,
    )
    list_response = client.get("/api/v1/hara/areas/1/advisories")

    assert create_response.status_code == 201
    assert patch_response.status_code == 200
    assert patch_response.json()["title"] == "Correct soil acidity"
    assert list_response.status_code == 200
    assert list_response.json()[0]["title"] == "Correct soil acidity"


def test_expert_can_patch_hara_area_and_audit_change(
    client_with_db: tuple[TestClient, Callable[[], Session]],
) -> None:
    client, session_local = client_with_db
    expert_headers = auth_headers(client, "expert@example.com", "expert")

    response = client.patch(
        "/api/v1/expert/hara/areas/1",
        json={"ph_rata2": 6.2, "soil_great": "Updated soil"},
        headers=expert_headers,
    )

    assert response.status_code == 200
    assert response.json()["properties"]["ph_rata2"] == 6.2
    assert response.json()["properties"]["soil_great"] == "Updated soil"
    with session_local() as db:
        change = db.scalar(select(HaraAreaChange).where(HaraAreaChange.hara_area_id == 1))
        assert change is not None
        assert change.action == "update"


def test_expert_hara_patch_validates_values(
    client_with_db: tuple[TestClient, Callable[[], Session]],
) -> None:
    client, _ = client_with_db
    expert_headers = auth_headers(client, "expert@example.com", "expert")

    response = client.patch(
        "/api/v1/expert/hara/areas/1",
        json={"ph_rata2": 20},
        headers=expert_headers,
    )

    assert response.status_code == 422


def test_expert_can_create_hara_area(
    client_with_db: tuple[TestClient, Callable[[], Session]],
) -> None:
    client, _ = client_with_db
    expert_headers = auth_headers(client, "expert@example.com", "expert")

    response = client.post(
        "/api/v1/expert/hara/areas",
        json={
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [106.8, -6.6],
                    [106.9, -6.6],
                    [106.9, -6.7],
                    [106.8, -6.6],
                ]],
            },
            "properties": {
                "name": "Area Baru",
                "ph_rata2": 5.8,
                "n_rata2": 3.2,
                "p_rata2": 10.5,
                "k_rata2": 150.0,
                "lithology": "Alluvium",
                "soil_great": "Tropaquepts",
                "slope__": "<2",
            },
        },
        headers=expert_headers,
    )

    assert response.status_code == 201
    assert response.json()["properties"]["name"] == "Area Baru"
