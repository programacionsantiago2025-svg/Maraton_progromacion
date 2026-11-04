"""Cálculo de rutas a pie usando el servidor público de OSRM."""
import httpx

OSRM_URL = "https://router.project-osrm.org/route/v1/foot/{coords}"


class RoutingError(Exception):
    pass


async def get_routes(origin: tuple[float, float], destination: tuple[float, float]) -> list[dict]:
    """origin/destination son (lat, lng). Devuelve lista de rutas alternativas:
    [{"geometry": [(lat, lng), ...], "distance_m": float, "duration_s": float}, ...]
    """
    lat1, lng1 = origin
    lat2, lng2 = destination
    coords = f"{lng1},{lat1};{lng2},{lat2}"
    url = OSRM_URL.format(coords=coords)
    params = {"alternatives": "true", "overview": "full", "geometries": "geojson"}

    try:
        async with httpx.AsyncClient(timeout=8) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise RoutingError("No se pudo calcular la ruta: servicio de rutas no disponible") from exc

    if data.get("code") != "Ok" or not data.get("routes"):
        raise RoutingError("No se encontró una ruta a pie entre los puntos indicados")

    rutas = []
    for route in data["routes"]:
        coords_geojson = route["geometry"]["coordinates"]  # [[lng, lat], ...]
        geometry = [(lat, lng) for lng, lat in coords_geojson]
        rutas.append(
            {
                "geometry": geometry,
                "distance_m": route["distance"],
                "duration_s": route["duration"],
            }
        )
    return rutas
