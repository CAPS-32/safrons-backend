from app.schemas.hara import HaraFeature, HaraProperties
from app.services.hara_diagnosis import build_hara_diagnosis, classify_nutrient, classify_ph


def feature(
    *,
    name: str = "Air Hitam Kanan",
    ph: float = 5.016667,
    n: float = 4.565255,
    p: float = 8.626031,
    k: float = 126.83385,
    slope: str = "41-60",
) -> HaraFeature:
    return HaraFeature(
        geometry=None,
        properties=HaraProperties(
            id=1,
            name=name,
            ph_rata2=ph,
            n_rata2=n,
            p_rata2=p,
            k_rata2=k,
            slope__=slope,
            texture_of="Fine grained tephra shale",
        ),
    )


def test_diagnosis_prioritizes_steep_acidic_area() -> None:
    diagnosis = build_hara_diagnosis(feature())

    assert diagnosis.status == "ready"
    assert diagnosis.rule_set_version == "hara-general-v1"
    assert diagnosis.factors[0].status == "acid"
    assert diagnosis.factors[-1].status == "very_steep"
    assert diagnosis.recommendations[0].category == "terrain"
    assert diagnosis.recommendations[1].category == "soil_reaction"


def test_diagnosis_returns_insufficient_data_for_sentinel_rows() -> None:
    diagnosis = build_hara_diagnosis(
        feature(name="Water", ph=-9999, n=-9999, p=-9999, k=-9999, slope="")
    )

    assert diagnosis.status == "insufficient_data"
    assert diagnosis.factors == []
    assert diagnosis.recommendations == []


def test_ph_uses_soil_reaction_classes() -> None:
    assert classify_ph(4.4).status == "very_acid"
    assert classify_ph(5.5).status == "acid"
    assert classify_ph(6.6).status == "neutral"
    assert classify_ph(8.6).status == "alkaline"


def test_nutrients_use_dataset_relative_bands() -> None:
    assert classify_nutrient("n_rata2", 1.0).status == "very_low"
    assert classify_nutrient("n_rata2", 2.2).status == "low"
    assert classify_nutrient("n_rata2", 3.0).status == "medium"
    assert classify_nutrient("n_rata2", 5.0).status == "high"
    assert classify_nutrient("n_rata2", 6.0).status == "very_high"

