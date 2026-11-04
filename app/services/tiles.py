"""Proxy con caché para los tiles de OpenStreetMap.

El navegador pide los tiles a nuestro propio origen; así el mapa no depende de que el
dispositivo (o el túnel por el que entra) pueda llegar a servidores de terceros, el
proveedor nunca ve la IP de la usuaria y se cumple la política de OSM (User-Agent que
identifica la app y caché local).
"""
from collections import OrderedDict

import httpx

OSM_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
MAX_CACHE = 1000

_client = httpx.AsyncClient(
    timeout=8,
    headers={"User-Agent": "RutaSegura/1.0 (proyecto academico, maraton de programacion)"},
)
_cache: OrderedDict[str, bytes] = OrderedDict()


class TileError(Exception):
    pass


async def get_tile(z: int, x: int, y: int) -> bytes:
    key = f"{z}/{x}/{y}"
    if key in _cache:
        _cache.move_to_end(key)
        return _cache[key]

    try:
        resp = await _client.get(OSM_URL.format(z=z, x=x, y=y))
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        raise TileError("No se pudo obtener el mapa base") from exc

    _cache[key] = resp.content
    if len(_cache) > MAX_CACHE:
        _cache.popitem(last=False)
    return resp.content
