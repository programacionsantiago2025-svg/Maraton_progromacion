from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models import SafePoint
from app.schemas import SafePointOut
from app.services.geo import haversine_m

router = APIRouter(prefix="/api/safe-points", tags=["safe_points"])


@router.get("", response_model=list[SafePointOut])
def list_safe_points(
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180),
    radius: float = Query(1000, ge=1, le=20000),
    db: Session = Depends(get_db),
):
    # Prefiltro por bbox (sin PostGIS) y luego distancia exacta con haversine
    margin_deg = radius / 111_000 + 0.01
    candidates = (
        db.query(SafePoint)
        .filter(SafePoint.lat.between(lat - margin_deg, lat + margin_deg))
        .filter(SafePoint.lng.between(lng - margin_deg, lng + margin_deg))
        .all()
    )
    return [sp for sp in candidates if haversine_m(lat, lng, sp.lat, sp.lng) <= radius]
