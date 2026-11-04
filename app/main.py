import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text

from app.core.db import Base, engine
from app.core.limiter import limiter
from app.routers import auth, guardian, pages, reports, routes, safe_points, tiles
from scripts.seed import seed_if_empty


def _wait_for_db(retries: int = 4, delay: float = 1.0) -> None:
    import app.core.db as db_mod
    last_error = None
    for attempt in range(retries):
        try:
            with db_mod.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print("[DB] Conexión establecida exitosamente con la base de datos principal.")
            return
        except Exception as exc:  # noqa: BLE001 - reintentar ante fallo de conexión
            last_error = exc
            print(f"[DB] Intento {attempt + 1}/{retries} de conexión falló: {exc}")
            time.sleep(delay)

    # Fallback automático para despliegues en la nube sin PostgreSQL externo configurado
    print(f"[DB] No se pudo conectar a la base de datos principal ({last_error}).")
    print("[DB] Activando SQLite embebido de respaldo (./rutasegura.db)...")
    db_mod.switch_to_sqlite()
    print("[DB] Base de datos SQLite inicializada y activa.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    import app.core.db as db_mod
    _wait_for_db()
    Base.metadata.create_all(bind=db_mod.engine)
    seed_if_empty()
    yield


app = FastAPI(title="RutaSegura", lifespan=lifespan)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(pages.router)
app.include_router(auth.router)
app.include_router(auth.me_router)
app.include_router(reports.router)
app.include_router(safe_points.router)
app.include_router(routes.router)
app.include_router(guardian.router)
app.include_router(tiles.router)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' https://cdn.tailwindcss.com https://unpkg.com; "
        "style-src 'self' 'unsafe-inline' https://unpkg.com; "
        "img-src 'self' data: https://unpkg.com; "
        "connect-src 'self' https://nominatim.openstreetmap.org https://router.project-osrm.org; "
        "font-src 'self' data:;"
    )
    return response


@app.get("/health")
def health():
    return {"status": "ok"}
