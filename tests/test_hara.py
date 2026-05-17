from collections.abc import Generator
from decimal import Decimal
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.db.session import get_db
from app.main import app


GEOMETRY = {
    "type": "MultiPolygon",
    "coordinates": [[[[106.8, -6.6], [106.9, -6.6], [106.9, -6.7], [106.8, -6.6]]]],
}

ROW = {
    "id": 1,
    "name": "Air Hitam Kanan",
    "ph_rata2": Decimal("5.016667"),
    "n_rata2": Decimal("4.565255"),
    "p_rata2": Decimal("8.626031"),
    "k_rata2": Decimal("126.83385"),
    "lithology": "Fine grained tephra shale",
    "soil_great": "Dystropepts",
    "slope__": "41-60",
    "geometry": GEOMETRY,
}


class FakeResult:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self.rows = rows

    def mappings(self) -> "FakeResult":
        return self

    def first(self) -> dict[str, Any] | None:
        return self.rows[0] if self.rows else None

    def __iter__(self) -> Any:
        return iter(self.rows)


class FakeDb:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self.rows = rows
        self.statements: list[str] = []
        self.params: list[dict[str, Any] | None] = []

    def execute(self, statement: Any, params: dict[str, Any] | None = None) -> FakeResult:
        self.statements.append(str(statement))
        self.params.append(params)
        return FakeResult(self.rows)


@pytest.fixture()
def fake_db() -> FakeDb:
    return FakeDb([ROW])


@pytest.fixture()
def client(fake_db: FakeDb) -> Generator[TestClient, None, None]:
    def override_get_db() -> FakeDb:
        return fake_db

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_hara_areas_returns_geojson_feature_collection(client: TestClient) -> None:
    response = client.get("/api/v1/hara/areas")

    assert response.status_code == 200
    body = response.json()
    assert body["type"] == "FeatureCollection"
    assert body["features"][0]["type"] == "Feature"
    assert body["features"][0]["geometry"] == GEOMETRY
    assert body["features"][0]["properties"]["ph_rata2"] == 5.016667


def test_hara_area_detail_returns_nutrient_fields(client: TestClient) -> None:
    response = client.get("/api/v1/hara/areas/1")

    assert response.status_code == 200
    properties = response.json()["properties"]
    assert properties["name"] == "Air Hitam Kanan"
    assert properties["n_rata2"] == 4.565255
    assert properties["p_rata2"] == 8.626031
    assert properties["k_rata2"] == 126.83385


def test_hara_point_uses_spatial_lookup(client: TestClient, fake_db: FakeDb) -> None:
    response = client.get("/api/v1/hara/point?lon=106.8&lat=-6.6")

    assert response.status_code == 200
    assert "ST_Contains" in fake_db.statements[0]
    assert fake_db.params[0] == {"lon": 106.8, "lat": -6.6}


def test_missing_hara_area_returns_404() -> None:
    fake_db = FakeDb([])

    def override_get_db() -> FakeDb:
        return fake_db

    app.dependency_overrides[get_db] = override_get_db
    try:
        response = TestClient(app).get("/api/v1/hara/areas/999")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
