"""Datos semilla de puntos seguros (CAI, farmacias 24h, tiendas, gasolineras)
para Bogotá, Soacha y Fusagasugá. No se consultan en vivo: se cargan una sola
vez al iniciar la aplicación, si la tabla `safe_points` está vacía.
"""
from app.core.db import SessionLocal
from app.models import SafePoint

SAFE_POINTS_DATA = [
    # Bogotá
    {"name": "CAI Chapinero", "kind": "cai", "lat": 4.6482, "lng": -74.0648, "open_24h": True},
    {"name": "CAI Usaquén", "kind": "cai", "lat": 4.6946, "lng": -74.0310, "open_24h": True},
    {"name": "CAI Candelaria", "kind": "cai", "lat": 4.5981, "lng": -74.0758, "open_24h": True},
    {"name": "CAI Restrepo", "kind": "cai", "lat": 4.5775, "lng": -74.1086, "open_24h": True},
    {"name": "Farmacia Cruz Verde Chapinero 24h", "kind": "farmacia", "lat": 4.6465, "lng": -74.0631, "open_24h": True},
    {"name": "Farmacia La Rebaja Cedritos", "kind": "farmacia", "lat": 4.7148, "lng": -74.0384, "open_24h": True},
    {"name": "Farmacia Cafam Kennedy", "kind": "farmacia", "lat": 4.6281, "lng": -74.1489, "open_24h": True},
    {"name": "Tienda D1 Calle 100", "kind": "tienda", "lat": 4.6867, "lng": -74.0535, "open_24h": False},
    {"name": "Estación de servicio Terpel Autopista Norte", "kind": "gasolinera", "lat": 4.7205, "lng": -74.0442, "open_24h": True},
    # Soacha
    {"name": "CAI Soacha Centro", "kind": "cai", "lat": 4.5794, "lng": -74.2167, "open_24h": True},
    {"name": "Farmacia Copidrogas Soacha", "kind": "farmacia", "lat": 4.5862, "lng": -74.2201, "open_24h": False},
    {"name": "Estación de servicio Soacha", "kind": "gasolinera", "lat": 4.5729, "lng": -74.2093, "open_24h": True},
    # Fusagasugá
    {"name": "CAI Fusagasugá Centro", "kind": "cai", "lat": 4.3417, "lng": -74.3644, "open_24h": True},
    {"name": "Farmacia La Rebaja Fusagasugá", "kind": "farmacia", "lat": 4.3389, "lng": -74.3661, "open_24h": True},
    {"name": "Tienda Ara Fusagasugá", "kind": "tienda", "lat": 4.3452, "lng": -74.3617, "open_24h": False},
]


def seed_if_empty() -> None:
    db = SessionLocal()
    try:
        if db.query(SafePoint).first() is not None:
            return
        db.bulk_insert_mappings(SafePoint, SAFE_POINTS_DATA)
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    seed_if_empty()
    print(f"Semilla aplicada: {len(SAFE_POINTS_DATA)} puntos seguros.")
