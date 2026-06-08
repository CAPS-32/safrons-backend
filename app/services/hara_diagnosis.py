from collections.abc import Sequence
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.schemas.diagnosis import (
    CropSuitability,
    DiagnosisFactor,
    DiagnosisRecommendation,
    HaraDiagnosisRead,
)
from app.schemas.hara import HaraFeature

RULE_SET_VERSION = "hara-general-v1"
NO_DATA_VALUE = -9999
NO_DATA_NAMES = {"water", "no data"}

NUTRIENT_THRESHOLDS = {
    "n_rata2": (1.989691, 2.450581, 4.158587, 5.5412572),
    "p_rata2": (6.672457, 7.790811, 8.022388, 8.970512),
    "k_rata2": (146.97696, 197.49262, 331.24494, 447.9228),
}

NUTRIENT_LABELS = {
    "n_rata2": "Nitrogen",
    "p_rata2": "Phosphorus",
    "k_rata2": "Potassium",
}

NUTRIENT_MESSAGES = {
    "very_low": "The value is in the lowest band compared with the current HARA dataset.",
    "low": "The value is below most comparable HARA areas.",
    "medium": "The value is near the middle of comparable HARA areas.",
    "high": "The value is above most comparable HARA areas.",
    "very_high": "The value is in the highest band compared with the current HARA dataset.",
}

STATUS_LABELS = {
    "very_acid": "Very acid",
    "acid": "Acid",
    "slightly_acid": "Slightly acid",
    "neutral": "Neutral",
    "slightly_alkaline": "Slightly alkaline",
    "alkaline": "Alkaline",
    "very_low": "Very low",
    "low": "Low",
    "medium": "Medium",
    "high": "High",
    "very_high": "Very high",
    "unknown": "Unknown",
    "flat": "Flat",
    "gentle": "Gentle",
    "moderate": "Moderate",
    "steep": "Steep",
    "very_steep": "Very steep",
}


def build_hara_diagnosis(area: HaraFeature, db: Session | None = None) -> HaraDiagnosisRead:
    if has_insufficient_data(area):
        return HaraDiagnosisRead(
            rule_set_version=RULE_SET_VERSION,
            status="insufficient_data",
            summary="Diagnosis cannot be generated because this polygon has no usable soil data.",
            area=area,
            factors=[],
            recommendations=[],
            crop_suitabilities=[],
        )

    factors = [
        classify_ph(area.properties.ph_rata2),
        classify_nutrient("n_rata2", area.properties.n_rata2),
        classify_nutrient("p_rata2", area.properties.p_rata2),
        classify_nutrient("k_rata2", area.properties.k_rata2),
        classify_slope(area.properties.slope__),
    ]
    recommendations = build_recommendations(factors)
    crop_suitabilities = get_crop_suitability(area, db=db)

    return HaraDiagnosisRead(
        rule_set_version=RULE_SET_VERSION,
        status="ready",
        summary=build_summary(factors),
        area=area,
        factors=factors,
        recommendations=recommendations,
        crop_suitabilities=crop_suitabilities,
    )


def has_insufficient_data(area: HaraFeature) -> bool:
    name = (area.properties.name or "").strip().lower()
    if name in NO_DATA_NAMES:
        return True

    values = [
        area.properties.ph_rata2,
        area.properties.n_rata2,
        area.properties.p_rata2,
        area.properties.k_rata2,
    ]
    return any(value is None or value <= NO_DATA_VALUE for value in values)


def classify_ph(value: float | None) -> DiagnosisFactor:
    if value is None:
        return unknown_factor("ph", "pH", None)

    if value < 4.5:
        status, severity = "very_acid", "critical"
    elif value < 5.6:
        status, severity = "acid", "attention"
    elif value < 6.6:
        status, severity = "slightly_acid", "watch"
    elif value < 7.6:
        status, severity = "neutral", "info"
    elif value < 8.6:
        status, severity = "slightly_alkaline", "watch"
    else:
        status, severity = "alkaline", "attention"

    return DiagnosisFactor(
        key="ph",
        label="pH",
        value=value,
        status=status,
        status_label=STATUS_LABELS[status],
        severity=severity,
        message=ph_message(status),
    )


def classify_nutrient(key: str, value: float | None) -> DiagnosisFactor:
    if value is None:
        return unknown_factor(key, NUTRIENT_LABELS[key], None)

    status = classify_by_thresholds(value, NUTRIENT_THRESHOLDS[key])
    severity = nutrient_severity(status)

    return DiagnosisFactor(
        key=key,
        label=NUTRIENT_LABELS[key],
        value=value,
        status=status,
        status_label=STATUS_LABELS[status],
        severity=severity,
        message=NUTRIENT_MESSAGES[status],
    )


def classify_by_thresholds(value: float, thresholds: Sequence[float]) -> str:
    if value <= thresholds[0]:
        return "very_low"
    if value <= thresholds[1]:
        return "low"
    if value <= thresholds[2]:
        return "medium"
    if value <= thresholds[3]:
        return "high"
    return "very_high"


def nutrient_severity(status: str) -> str:
    if status == "very_low":
        return "critical"
    if status == "low":
        return "attention"
    if status in {"high", "very_high"}:
        return "watch"
    return "info"


def classify_slope(value: str | None) -> DiagnosisFactor:
    normalized = (value or "").strip()
    if not normalized:
        return unknown_factor("slope", "Slope", value)

    if normalized in {"<2"}:
        status, severity, message = (
            "flat",
            "info",
            "Slope is low; erosion risk from terrain is limited.",
        )
    elif normalized in {"0-8", "2-8"}:
        status, severity, message = (
            "gentle",
            "info",
            "Slope is gentle and suitable for standard soil-conservation practice.",
        )
    elif normalized == "9-15":
        status, severity, message = (
            "moderate",
            "watch",
            "Slope needs routine runoff and erosion control.",
        )
    elif normalized in {"16-25", "26-40"}:
        status, severity, message = (
            "steep",
            "attention",
            "Slope increases erosion risk and nutrient loss.",
        )
    elif normalized in {"41-60", ">60"}:
        status, severity, message = (
            "very_steep",
            "critical",
            "Very steep slope creates high erosion and nutrient-loss risk.",
        )
    else:
        return unknown_factor("slope", "Slope", value)

    return DiagnosisFactor(
        key="slope",
        label="Slope",
        value=normalized,
        status=status,
        status_label=STATUS_LABELS[status],
        severity=severity,
        message=message,
    )


def unknown_factor(key: str, label: str, value: float | str | None) -> DiagnosisFactor:
    return DiagnosisFactor(
        key=key,
        label=label,
        value=value,
        status="unknown",
        status_label=STATUS_LABELS["unknown"],
        severity="watch",
        message="No rule can be applied because the value is missing or unrecognized.",
    )


def ph_message(status: str) -> str:
    messages = {
        "very_acid": "Soil reaction is very acidic and can limit nutrient availability.",
        "acid": "Soil reaction is acidic and may limit nutrient availability.",
        "slightly_acid": "Soil reaction is slightly acidic and should be monitored.",
        "neutral": "Soil reaction is near the preferred general range.",
        "slightly_alkaline": "Soil reaction is slightly alkaline and should be monitored.",
        "alkaline": "Soil reaction is alkaline and can reduce availability of some nutrients.",
    }
    return messages[status]


def build_recommendations(factors: list[DiagnosisFactor]) -> list[DiagnosisRecommendation]:
    recommendations: list[DiagnosisRecommendation] = []
    factor_by_key = {factor.key: factor for factor in factors}

    slope = factor_by_key["slope"]
    if slope.status in {"steep", "very_steep"}:
        recommendations.append(
            recommendation(
                "terrain",
                "Prioritize erosion control",
                "Use contour planting, ground cover, terraces, or other local conservation measures before intensifying nutrient inputs.",
                slope.message,
            )
        )

    ph = factor_by_key["ph"]
    if ph.status in {"very_acid", "acid"}:
        recommendations.append(
            recommendation(
                "soil_reaction",
                "Correct soil acidity",
                "Consider agricultural lime or dolomite only after field confirmation and local extension guidance.",
                ph.message,
            )
        )
    elif ph.status in {"slightly_acid", "slightly_alkaline", "alkaline"}:
        recommendations.append(
            recommendation(
                "soil_reaction",
                "Monitor soil pH",
                "Confirm pH with field sampling before making pH correction decisions.",
                ph.message,
            )
        )

    for key, title in [
        ("n_rata2", "Improve nitrogen availability"),
        ("p_rata2", "Improve phosphorus availability"),
        ("k_rata2", "Improve potassium availability"),
    ]:
        factor = factor_by_key[key]
        if factor.status in {"very_low", "low"}:
            recommendations.append(
                recommendation(
                    "nutrient",
                    title,
                    "Use balanced fertilization and organic-matter management based on a current soil test.",
                    factor.message,
                )
            )
        elif factor.status in {"high", "very_high"}:
            recommendations.append(
                recommendation(
                    "nutrient",
                    f"Monitor {factor.label.lower()} inputs",
                    "Avoid unnecessary additions until field sampling confirms crop need.",
                    factor.message,
                )
            )

    return [
        DiagnosisRecommendation(priority=index + 1, **item.model_dump(exclude={"priority"}))
        for index, item in enumerate(recommendations)
    ]


def recommendation(
    category: str,
    title: str,
    action: str,
    reason: str,
) -> DiagnosisRecommendation:
    return DiagnosisRecommendation(
        priority=0,
        category=category,
        title=title,
        action=action,
        reason=reason,
    )


def build_summary(factors: list[DiagnosisFactor]) -> str:
    critical = [factor.label for factor in factors if factor.severity == "critical"]
    attention = [factor.label for factor in factors if factor.severity == "attention"]

    if critical:
        return f"High-priority constraints found for {', '.join(critical)}."
    if attention:
        return f"Management attention is recommended for {', '.join(attention)}."
    return "No high-priority soil constraints were detected by the current rule set."


CROP_CRITERIA = {
    "jagung": {
        "ph": (5.5, 7.0, 5.0, 5.5, 4.5, 5.0),
        "n": (5.0, None, 3.0, 5.0, 2.0, 3.0),
        "p": (16.0, None, 8.0, 16.0, 6.0, 8.0),
        "k": (300.0, None, 150.0, 300.0, 80.0, 150.0),
    },
    "kacang_tanah": {
        "ph": (5.5, 7.0, 5.0, 5.5, 4.5, 5.0),
        "n": (4.0, None, 2.5, 4.0, 1.5, 2.5),
        "p": (16.0, None, 8.0, 16.0, 6.0, 8.0),
        "k": (250.0, None, 120.0, 250.0, 70.0, 120.0),
    },
    "kakao": {
        "ph": (6.0, 7.0, 5.0, 6.0, 4.0, 5.0),
        "n": (3.0, None, 2.0, 3.0, 1.0, 2.0),
        "p": (12.0, None, 7.0, 12.0, 5.0, 7.0),
        "k": (200.0, None, 100.0, 200.0, 60.0, 100.0),
    },
}


def classify_crop_param(
    value: float | None,
    criteria: tuple[float | None, float | None, float | None, float | None, float | None, float | None],
) -> int:
    if value is None or value <= -9000:
        return 4

    s1_min, s1_max, s2_min, s2_max, s3_min, s3_max = criteria

    if (s1_min is None or value >= s1_min) and (s1_max is None or value <= s1_max):
        return 1
    if (s2_min is None or value >= s2_min) and (s2_max is None or value <= s2_max):
        return 2
    if (s3_min is None or value >= s3_min) and (s3_max is None or value <= s3_max):
        return 3

    return 4


def calculate_python_suitability(area: HaraFeature) -> list[CropSuitability]:
    results = []
    props = area.properties
    vals = {
        "ph": props.ph_rata2,
        "n": props.n_rata2,
        "p": props.p_rata2,
        "k": props.k_rata2,
    }

    classes_map = {1: "S1", 2: "S2", 3: "S3", 4: "N"}

    for crop, criteria_set in CROP_CRITERIA.items():
        ranks = {}
        for param, criteria in criteria_set.items():
            ranks[param] = classify_crop_param(vals[param], criteria)

        worst_rank = max(ranks.values())
        suitability_class = classes_map[worst_rank]
        limiting_factors = (
            []
            if worst_rank == 1
            else sorted([param for param, rank in ranks.items() if rank == worst_rank])
        )

        results.append(
            CropSuitability(
                crop=crop,
                suitability_class=suitability_class,
                limiting_factors=limiting_factors,
                ph_class=classes_map[ranks["ph"]],
                n_class=classes_map[ranks["n"]],
                p_class=classes_map[ranks["p"]],
                k_class=classes_map[ranks["k"]],
            )
        )

    return results


def get_crop_suitability(area: HaraFeature, db: Session | None = None) -> list[CropSuitability]:
    if db is not None:
        try:
            if db.get_bind().dialect.name == "postgresql":
                rows = db.execute(
                    text(
                        """
                        SELECT crop, class, limiting_factors, ph_class, n_class, p_class, k_class
                        FROM hara_crop_suitability
                        WHERE hara_area_id = :area_id
                        ORDER BY crop
                        """
                    ),
                    {"area_id": area.properties.id},
                ).mappings().all()
                return [
                    CropSuitability(
                        crop=row["crop"],
                        suitability_class=row["class"],
                        limiting_factors=row["limiting_factors"],
                        ph_class=row["ph_class"],
                        n_class=row["n_class"],
                        p_class=row["p_class"],
                        k_class=row["k_class"],
                    )
                    for row in rows
                ]
        except Exception:
            pass

    return calculate_python_suitability(area)

