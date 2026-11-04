import time

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text

from app.core.db import Base, engine
from app.core.limiter import limiter
from app.routers import auth, pages, safe_points
from scripts.seed import seed_if_empty

app = FastAPI(title="RutaSegura")

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(pages.router)
app.include_router(auth.router)
app.include_router(auth.me_router)
app.include_router(safe_points.router)


@app.get("/health")
def health():
    return {"status": "ok"}


def _wait_for_db(retries: int = 10, delay: float = 1.5) -> None:
    last_error = None
    for _ in range(retries):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return
        except Exception as exc:  # noqa: BLE001 - queremos reintentar ante cualquier fallo de conexión
            last_error = exc
            time.sleep(delay)
    raise RuntimeError(f"No se pudo conectar a la base de datos tras {retries} intentos") from last_error


@app.on_event("startup")
def on_startup():
    _wait_for_db()
    Base.metadata.create_all(bind=engine)
    seed_if_empty()
