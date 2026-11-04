"""Utilidades geométricas puras (sin PostGIS): haversine y muestreo de polilíneas."""
import math

EARTH_RADIUS_M = 6_371_000.0


def haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Distancia en metros entre dos puntos lat/lng (fórmula de Haversine)."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lng2 - lng1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(min(1.0, math.sqrt(a)))


def bbox_from_points(points: list[tuple[float, float]], margin_deg: float = 0.01) -> tuple[float, float, float, float]:
    """Devuelve (min_lat, max_lat, min_lng, max_lng) con margen, a partir de una lista de (lat, lng)."""
    lats = [p[0] for p in points]
    lngs = [p[1] for p in points]
    return min(lats) - margin_deg, max(lats) + margin_deg, min(lngs) - margin_deg, max(lngs) + margin_deg


def sample_polyline(points: list[tuple[float, float]], interval_m: float = 50.0) -> list[tuple[float, float]]:
    """Muestrea puntos (lat, lng) cada `interval_m` metros a lo largo de la polilínea."""
    if not points:
        return []
    if len(points) == 1:
        return [points[0]]

    sampled = [points[0]]
    carry = 0.0
    for (lat1, lng1), (lat2, lng2) in zip(points, points[1:]):
        seg_len = haversine_m(lat1, lng1, lat2, lng2)
        if seg_len == 0:
            continue
        pos = carry
        while pos < seg_len:
            t = pos / seg_len
            lat = lat1 + (lat2 - lat1) * t
            lng = lng1 + (lng2 - lng1) * t
            sampled.append((lat, lng))
            pos += interval_m
        carry = pos - seg_len
    sampled.append(points[-1])
    return sampled
