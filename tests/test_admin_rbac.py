"""
Integration tests for admin role-based access control (RBAC).
"""
from collections.abc import Callable, Generator
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
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


def test_user_cannot_access_list_users_endpoint(
    client_with_db: tuple[TestClient, Callable[[], Session]],
) -> None:
    """
    Ensure that a user with the 'user' role is blocked with a 403 status code
    when attempting to retrieve the user list.
    """
    client, _ = client_with_db
    headers = auth_headers(client, "user@example.com")

    response = client.get("/api/v1/admin/users", headers=headers)
    assert response.status_code == 403


def test_admin_can_access_list_users_endpoint(
    client_with_db: tuple[TestClient, Callable[[], Session]],
) -> None:
    """
    Ensure that a user with the 'admin' role can successfully hit the users list endpoint.
    """
    client, _ = client_with_db
    auth_headers(client, "user1@example.com")
    auth_headers(client, "user2@example.com")
    
    admin_headers = auth_headers(client, "admin@example.com", "admin")

    response = client.get("/api/v1/admin/users", headers=admin_headers)
    assert response.status_code == 200
    
    users = response.json()
    assert len(users) >= 3  # admin + user1 + user2
    emails = [u["email"] for u in users]
    assert "admin@example.com" in emails
    assert "user1@example.com" in emails
    assert "user2@example.com" in emails
