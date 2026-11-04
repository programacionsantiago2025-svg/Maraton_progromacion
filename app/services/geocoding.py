"""Geocodificación de direcciones usando Nominatim (OpenStreetMap)."""
import re

import httpx

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
HEADERS = {"User-Agent": "RutaSegura/1.0"}
MAX_CACHE = 256

_COORDENADAS = re.compile(r"^\s*(-?\d{1,3}(?:\.\d+)?)\s*,\s*(-?\d{1,3}(?:\.\d+)?)\s*$")
_cache: dict[str, tuple[float, float]] = {}


class GeocodingError(Exception):
    pass


def parse_coordenadas(texto: str) -> tuple[float, float] | None:
    """Reconoce "lat,lng" (p. ej. el origen "Mi ubicación") y evita llamar a Nominatim."""
    m = _COORDENADAS.match(texto)
    if not m:
        return None
    lat, lng = float(m.group(1)), float(m.group(2))
    if -90 <= lat <= 90 and -180 <= lng <= 180:
        return lat, lng
    return None


async def geocode(query: str) -> tuple[float, float]:
    """Devuelve (lat, lng) para una dirección de texto libre. Lanza GeocodingError si falla."""
    coords = parse_coordenadas(query)
    if coords:
        return coords

    clave = " ".join(query.lower().split())
    if clave in _cache:
        return _cache[clave]

    params = {"format": "json", "q": query, "limit": 1}
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            resp = await client.get(NOMINATIM_URL, params=params, headers=HEADERS)
            resp.raise_for_status()
            data = resp.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise GeocodingError(f"No se pudo geocodificar '{query}': servicio de mapas no disponible") from exc

    if not data:
        raise GeocodingError(f"No se encontró la dirección: '{query}'")

    item = data[0]
    try:
        resultado = (float(item["lat"]), float(item["lon"]))
    except (KeyError, ValueError) as exc:
        raise GeocodingError(f"Respuesta de geocodificación inválida para '{query}'") from exc

    if len(_cache) >= MAX_CACHE:
        _cache.pop(next(iter(_cache)))
    _cache[clave] = resultado
    return resultado
