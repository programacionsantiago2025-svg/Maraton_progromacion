"""Índice de Seguridad Nocturna (ISN).

Función pura y testeable: NO hace perfilamiento de personas, solo evalúa
condiciones de LUGARES a partir de reportes ciudadanos y puntos seguros
conocidos (ver docs/uso_ia.md para la discusión ética y de sesgo).
"""
from dataclasses import dataclass
from datetime import datetime, timezone

from app.services.geo import haversine_m, sample_polyline

RADIO_REPORTES_M = 50.0
TIPOS_CONSIDERADOS = {"acoso", "calle_sola", "poca_luz", "zona_segura"}


@dataclass
class ReporteLike:
    """Forma mínima que necesita un reporte para calcular el ISN."""

    type: str
    severity: int
    lat: float
    lng: float
    created_at: datetime


@dataclass
class PuntoSeguroLike:
    lat: float
    lng: float


def _age_hours(created_at: datetime, now: datetime) -> float:
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    return max(0.0, (now - created_at).total_seconds() / 3600)


def _decay(hours: float) -> float:
    return max(0.2, 1 - hours / 168)


def _build_explanation(n_riesgo: int, penal_luz: int, refugio_m: float, n_zona_segura: int) -> str:
    partes = []
    if n_riesgo > 0:
        palabra = "reporte" if n_riesgo == 1 else "reportes"
        partes.append(f"{n_riesgo} {palabra} de acoso o calle sola cerca de la ruta")
    if penal_luz > 0:
        palabra = "reporte" if penal_luz == 1 else "reportes"
        partes.append(f"{penal_luz} {palabra} de poca luz")
    if refugio_m > 300:
        partes.append("sin refugio (CAI, farmacia o tienda 24h) a menos de 300 m")
    else:
        partes.append(f"refugio cercano a ~{int(refugio_m)} m")
    if n_zona_segura > 0:
        palabra = "zona" if n_zona_segura == 1 else "zonas"
        partes.append(f"{n_zona_segura} {palabra} marcada(s) como segura por la comunidad")
    if not partes:
        partes.append("sin reportes recientes cerca de la ruta")
    return "; ".join(partes) + "."


def compute_isn(
    route_points: list[tuple[float, float]],
    reports: list,
    safe_points: list,
    now: datetime | None = None,
) -> dict:
    """route_points: lista de (lat, lng) de la polilínea de la ruta.
    reports: objetos con .type, .severity, .lat, .lng, .created_at.
    safe_points: objetos con .lat, .lng.
    Devuelve dict con isn, breakdown y explicación en español.
    """
    now = now or datetime.now(timezone.utc)
    sampled = sample_polyline(route_points, interval_m=50.0) or list(route_points)

    near_reports = []
    for r in reports:
        if r.type not in TIPOS_CONSIDERADOS:
            continue
        min_dist = min(haversine_m(p[0], p[1], r.lat, r.lng) for p in sampled)
        if min_dist <= RADIO_REPORTES_M:
            near_reports.append(r)

    riesgo_reportes = 0.0
    n_riesgo = 0
    for r in near_reports:
        if r.type in ("acoso", "calle_sola"):
            riesgo_reportes += (r.severity / 5) * _decay(_age_hours(r.created_at, now))
            n_riesgo += 1

    penal_luz = sum(1 for r in near_reports if r.type == "poca_luz")
    n_zona_segura = sum(1 for r in near_reports if r.type == "zona_segura")

    if safe_points:
        distancias = [
            min(haversine_m(p[0], p[1], sp.lat, sp.lng) for sp in safe_points) for p in sampled
        ]
        refugio_m = sum(distancias) / len(distancias)
    else:
        refugio_m = 2000.0

    isn = 100 - 4 * riesgo_reportes - 3 * penal_luz - min(25, refugio_m / 40) + 5 * n_zona_segura
    isn = max(0.0, min(100.0, isn))

    return {
        "isn": round(isn, 1),
        "breakdown": {
            "riesgo_reportes": round(riesgo_reportes, 2),
            "penal_luz": float(penal_luz),
            "refugio_m": round(refugio_m, 1),
            "zona_segura": n_zona_segura,
            "isn": round(isn, 1),
            "explicacion": _build_explanation(n_riesgo, penal_luz, refugio_m, n_zona_segura),
        },
    }
