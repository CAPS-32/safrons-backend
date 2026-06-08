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
    "slope__": "41-60",
    "texture_of": "Fine grained tephra shale",
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

    def get_bind(self) -> Any:
        class FakeDialect:
            name = "postgresql"

        class FakeBind:
            dialect = FakeDialect()

        return FakeBind()


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


def test_hara_area_diagnosis_returns_rule_output(client: TestClient) -> None:
    response = client.get("/api/v1/hara/areas/1/diagnosis")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["rule_set_version"] == "hara-general-v1"
    assert body["area"]["properties"]["id"] == 1
    assert body["factors"][0]["key"] == "ph"
    assert body["recommendations"][0]["priority"] == 1
    assert "crop_suitabilities" in body
    assert len(body["crop_suitabilities"]) == 3


def test_hara_point_diagnosis_uses_spatial_lookup(client: TestClient, fake_db: FakeDb) -> None:
    response = client.get("/api/v1/hara/point/diagnosis?lon=106.8&lat=-6.6")

    assert response.status_code == 200
    assert "ST_Contains" in fake_db.statements[0]
    assert fake_db.params[0] == {"lon": 106.8, "lat": -6.6}
    assert response.json()["status"] == "ready"


def test_hara_diagnosis_returns_insufficient_data_for_no_data_row() -> None:
    no_data_row = {
        **ROW,
        "name": "Water",
        "ph_rata2": Decimal("-9999"),
        "n_rata2": Decimal("-9999"),
        "p_rata2": Decimal("-9999"),
        "k_rata2": Decimal("-9999"),
        "slope__": "",
    }
    fake_db = FakeDb([no_data_row])

    def override_get_db() -> FakeDb:
        return fake_db

    app.dependency_overrides[get_db] = override_get_db
    try:
        response = TestClient(app).get("/api/v1/hara/areas/5/diagnosis")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["status"] == "insufficient_data"


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
