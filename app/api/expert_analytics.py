from typing import Annotated
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.api.deps import require_expert
from app.db.session import get_db
from app.models.user import User
from app.schemas.analytics import Averages, PhDistribution, CriticalArea, MacroAnalyticsRead

router = APIRouter(prefix="/api/v1/expert/analytics", tags=["expert_analytics"])

@router.get("", response_model=MacroAnalyticsRead)
def get_macro_analytics(
    expert_user: Annotated[User, Depends(require_expert)],
    db: Annotated[Session, Depends(get_db)],
) -> MacroAnalyticsRead:
    rows = db.execute(
        text("SELECT id, name, ph_rata2, n_rata2, p_rata2, k_rata2 FROM hara_bogor")
    ).mappings().all()

    if not rows:
        return MacroAnalyticsRead(
            averages=Averages(ph=0.0, n=0.0, p=0.0, k=0.0),
            ph_distribution=PhDistribution(
                sangat_masam=0,
                masam=0,
                sedikit_masam=0,
                netral=0,
                sedikit_alkalis=0,
                alkalis=0
            ),
            critical_areas=[]
        )

    ph_list = []
    n_list = []
    p_list = []
    k_list = []
    
    sangat_masam = 0
    masam = 0
    sedikit_masam = 0
    netral = 0
    sedikit_alkalis = 0
    alkalis = 0

    valid_areas = []

    for r in rows:
        ph = float(r["ph_rata2"]) if r["ph_rata2"] is not None else None
        n = float(r["n_rata2"]) if r["n_rata2"] is not None else None
        p = float(r["p_rata2"]) if r["p_rata2"] is not None else None
        k = float(r["k_rata2"]) if r["k_rata2"] is not None else None

        if ph == -9999.0: ph = None
        if n == -9999.0: n = None
        if p == -9999.0: p = None
        if k == -9999.0: k = None

        if ph is not None:
            ph_list.append(ph)
            if ph < 4.5:
                sangat_masam += 1
            elif ph <= 5.5:
                masam += 1
            elif ph <= 6.5:
                sedikit_masam += 1
            elif ph <= 7.5:
                netral += 1
            elif ph <= 8.5:
                sedikit_alkalis += 1
            else:
                alkalis += 1

        if n is not None: n_list.append(n)
        if p is not None: p_list.append(p)
        if k is not None: k_list.append(k)

        if n is not None or p is not None:
            vals = []
            if n is not None:
                vals.append((n, "N"))
            if p is not None:
                vals.append((p, "P"))
            
            if vals:
                min_val, min_param = min(vals, key=lambda x: x[0])
                name = r["name"] or f"Area #{r['id']}"
                
                if name.lower() not in ("water", "no data", "no_data"):
                    if name.lower() == "puting":
                        name = "Seri Puting"
                    elif not name.startswith("Seri ") and not name.startswith("Asosiasi "):
                        name = f"Seri {name}"
                    
                    valid_areas.append({
                        "id": r["id"],
                        "name": name,
                        "value": min_val,
                        "parameter": min_param
                    })

    avg_ph = sum(ph_list) / len(ph_list) if ph_list else 0.0
    avg_n = sum(n_list) / len(n_list) if n_list else 0.0
    avg_p = sum(p_list) / len(p_list) if p_list else 0.0
    avg_k = (sum(k_list) / len(k_list) / 10.0) if k_list else 0.0

    unique_areas = {}
    for area in valid_areas:
        name = area["name"]
        if name not in unique_areas or area["value"] < unique_areas[name]["value"]:
            unique_areas[name] = area

    critical_areas_data = sorted(unique_areas.values(), key=lambda x: x["value"])[:5]
    critical_areas = [
        CriticalArea(
            id=c["id"],
            name=c["name"],
            value=c["value"],
            parameter=c["parameter"]
        ) for c in critical_areas_data
    ]

    return MacroAnalyticsRead(
        averages=Averages(ph=avg_ph, n=avg_n, p=avg_p, k=avg_k),
        ph_distribution=PhDistribution(
            sangat_masam=sangat_masam,
            masam=masam,
            sedikit_masam=sedikit_masam,
            netral=netral,
            sedikit_alkalis=sedikit_alkalis,
            alkalis=alkalis
        ),
        critical_areas=critical_areas
    )
