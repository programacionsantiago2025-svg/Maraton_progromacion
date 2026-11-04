"""Geocodificación de direcciones usando Nominatim (OpenStreetMap)."""
import httpx

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
HEADERS = {"User-Agent": "RutaSegura/1.0"}


class GeocodingError(Exception):
    pass


async def geocode(query: str) -> tuple[float, float]:
    """Devuelve (lat, lng) para una dirección de texto libre. Lanza GeocodingError si falla."""
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
        return float(item["lat"]), float(item["lon"])
    except (KeyError, ValueError) as exc:
        raise GeocodingError(f"Respuesta de geocodificación inválida para '{query}'") from exc
