import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models import Report, SafePoint
from app.schemas import ISNBreakdown, RouteOut, RoutesResponse
from app.services.geo import bbox_from_points
from app.services.geocoding import GeocodingError, geocode
from app.services.routing import RoutingError, get_routes
from app.services.safety_score import compute_isn

router = APIRouter(prefix="/api/routes", tags=["routes"])


@router.get("", response_model=RoutesResponse)
async def buscar_rutas(
    origin: str = Query(..., min_length=1),
    destination: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
):
    try:
        origin_latlng, destination_latlng = await asyncio.gather(geocode(origin), geocode(destination))
    except GeocodingError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    try:
        rutas_osrm = await get_routes(origin_latlng, destination_latlng)
    except RoutingError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    # Una sola consulta a BD: bbox que cubre todas las alternativas de ruta
    todos_los_puntos = [p for ruta in rutas_osrm for p in ruta["geometry"]]
    min_lat, max_lat, min_lng, max_lng = bbox_from_points(todos_los_puntos, margin_deg=0.005)

    reports = (
        db.query(Report)
        .filter(Report.lat.between(min_lat, max_lat))
        .filter(Report.lng.between(min_lng, max_lng))
        .all()
    )
    safe_points = (
        db.query(SafePoint)
        .filter(SafePoint.lat.between(min_lat, max_lat))
        .filter(SafePoint.lng.between(min_lng, max_lng))
        .all()
    )

    now = datetime.now(timezone.utc)
    calculadas = []
    for ruta in rutas_osrm:
        resultado = compute_isn(ruta["geometry"], reports, safe_points, now=now)
        calculadas.append(
            {
                # 5 decimales (~1 m) bastan para dibujar y reducen el tamaño de la respuesta
                "geometry": [[round(lat, 5), round(lng, 5)] for lat, lng in ruta["geometry"]],
                "distance_m": ruta["distance_m"],
                "duration_s": ruta["duration_s"],
                "isn": resultado["isn"],
                "breakdown": resultado["breakdown"],
            }
        )

    calculadas.sort(key=lambda r: r["isn"], reverse=True)
    rutas_out = [
        RouteOut(
            geometry=r["geometry"],
            distance_m=r["distance_m"],
            duration_s=r["duration_s"],
            isn=r["isn"],
            breakdown=ISNBreakdown(**r["breakdown"]),
            es_mas_segura=(i == 0),
        )
        for i, r in enumerate(calculadas)
    ]

    return RoutesResponse(
        origin=[origin_latlng[0], origin_latlng[1]],
        destination=[destination_latlng[0], destination_latlng[1]],
        rutas=rutas_out,
    )
